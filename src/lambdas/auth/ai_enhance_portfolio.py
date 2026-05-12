"""
Lambda: AI Portfolio Field/Section Enhancer

POST /portfolio/{userId}/ai-enhance -- Cognito-authenticated.

Supports three body shapes:

Shape A -- scalar portfolioContent field (existing):
  { "field": "bio", "instruction": "Make it more concise" }

Shape B -- parsedData section item enhance:
  { "section": "experience", "itemIndex": 0, "enhanceField": "description", "instruction": "..." }

Shape C -- skills section enhance (full context):
  { "section": "skills", "instruction": "..." }

Responses:
  Shape A: { "field": "bio", "suggestedValue": "..." }
  Shape B: { "section": "experience", "itemIndex": 0, "enhanceField": "description", "suggestedValue": "..." }
  Shape C: { "section": "skills", "suggestedValue": [...skill_groups...] }

Security notes:
  - userId in path MUST match the Cognito token sub.
  - Only explicitly allowlisted fields/sections can be enhanced.
  - User instruction is capped at 300 chars to limit prompt injection surface.
  - AI response returned as suggestion only -- never stored without explicit user save.
"""

import json
import os
import urllib.request
import decimal
from urllib.parse import unquote

import boto3

dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')


class _DecimalEncoder(json.JSONEncoder):
    """DynamoDB returns numeric types as Decimal; convert to int/float for JSON."""
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
OPENAI_SECRET_NAME = os.environ.get('OPENAI_SECRET_NAME')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

# Shape A: scalar portfolioContent fields
_ALLOWED_FIELDS: set = {'bio', 'headline', 'uniqueValue'}

_MAX_INSTRUCTION_CHARS = 300

_FIELD_MAX_SEND_CHARS: dict = {
    'bio': 1000,
    'headline': 200,
    'uniqueValue': 500,
}

_FIELD_LABELS: dict = {
    'bio': 'professional bio (3-4 sentences for the About section of a portfolio website)',
    'headline': 'one-line professional headline',
    'uniqueValue': 'unique value proposition (2 sentences describing what makes this person stand out)',
}

# Shape B: array section item fields that can be AI-enhanced.
# Only fields where AI adds genuine value (narrative/impact text) are listed.
# Removed: education.grade_or_score (factual number), certifications.name
# (proper noun from issuing body), awards.title (org-assigned name),
# investment_portfolios.performance_return (factual metric).
_SECTION_ITEM_FIELDS: dict = {
    'experience':         ['description', 'key_points'],
    'projects':           ['description', 'responsibilities', 'measurable_outcomes'],
    'achievements':       ['description'],
    'campaigns':          ['performance_metrics'],
    'financial_modeling': ['outcome'],
}

# Shape C: context sections per category for skills enhancement
_SKILLS_CONTEXT_SECTIONS: dict = {
    'software_engineer': ['experience', 'projects', 'certifications'],
    'designer':          ['experience', 'projects', 'awards', 'certifications'],
    'marketing':         ['experience', 'campaigns', 'certifications'],
    'finance':           ['experience', 'financial_modeling', 'investment_portfolios', 'certifications'],
}
_SKILLS_CONTEXT_DEFAULT = ['experience', 'certifications']

_CONTEXT_MAX_CHARS = 2000

_openai_api_key = None


# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------


def _log(level, message, **kwargs):
    print(json.dumps({
        "level": level,
        "function": "ai_enhance_portfolio",
        "message": message,
        **kwargs,
    }))


# ---------------------------------------------------------------------------
# Response helper
# ---------------------------------------------------------------------------


def _response(status, body):
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'X-Content-Type-Options': 'nosniff',
        },
        'body': json.dumps(body, cls=_DecimalEncoder),
    }


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------


def _get_openai_key():
    global _openai_api_key
    if _openai_api_key:
        return _openai_api_key
    resp = secrets_client.get_secret_value(SecretId=OPENAI_SECRET_NAME)
    secret = json.loads(resp['SecretString'])
    _openai_api_key = (
        secret.get('api_key')
        or secret.get('OPENAI_API_KEY')
        or secret.get('openai_api_key')
    )
    return _openai_api_key


def _call_openai(prompt, api_key, max_tokens=400):
    request_body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional portfolio content editor. "
                    "Follow user instructions precisely and return only the "
                    "requested text or JSON with no surrounding commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "max_tokens": max_tokens,
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=request_body,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
    )

    with urllib.request.urlopen(req, timeout=25) as resp:
        result = json.loads(resp.read().decode('utf-8'))

    return result['choices'][0]['message']['content'].strip()


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    path_user_id = unquote((event.get('pathParameters') or {}).get('userId', ''))
    token_sub = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub', '')
    )

    if not path_user_id or path_user_id != token_sub:
        _log('WARNING', 'AI enhance auth mismatch', correlationId=correlation_id)
        return _response(403, {'error': 'Forbidden'})

    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, ValueError):
        return _response(400, {'error': 'Invalid JSON body'})

    # Shape D: LLM-generated portfolio suggestions (no instruction needed)
    if body.get('action') == 'analyze_and_suggest':
        return _handle_analyze_and_suggest(body, path_user_id, correlation_id)

    instruction = str(body.get('instruction', '')).strip()
    if not instruction:
        return _response(400, {'error': 'instruction is required'})
    if len(instruction) > _MAX_INSTRUCTION_CHARS:
        return _response(400, {
            'error': f'instruction exceeds the {_MAX_INSTRUCTION_CHARS}-character limit'
        })

    if 'field' in body:
        return _handle_field_enhance(body, path_user_id, instruction, correlation_id)
    if 'section' in body:
        return _handle_section_enhance(body, path_user_id, instruction, correlation_id)

    return _response(400, {'error': 'Request must include either "field", "section", or action="analyze_and_suggest"'})


# ---------------------------------------------------------------------------
# Shape A: scalar field enhance
# ---------------------------------------------------------------------------


def _handle_field_enhance(body, path_user_id, instruction, correlation_id):
    field = body.get('field', '')

    if field not in _ALLOWED_FIELDS:
        return _response(400, {
            'error': f'field must be one of: {", ".join(sorted(_ALLOWED_FIELDS))}'
        })

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        result = table.get_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': 'PORTFOLIO#current'},
            ProjectionExpression='portfolioContent',
        )

        if 'Item' not in result:
            return _response(404, {'error': 'Portfolio not found. Generate a portfolio first.'})

        portfolio_content = result['Item'].get('portfolioContent') or {}
        current_value = str(portfolio_content.get(field) or '')

        max_chars = _FIELD_MAX_SEND_CHARS.get(field, 500)
        field_label = _FIELD_LABELS.get(field, field)

        # Determine length constraint by field type
        _field_length_guide = {
            'bio':         '3–4 sentences (60–120 words)',
            'headline':    '1 line, under 15 words',
            'uniqueValue': '2–3 sentences (40–80 words)',
        }
        length_guide = _field_length_guide.get(field, '2–3 sentences')

        prompt = (
            f"You are editing a portfolio website. "
            f"The current {field_label} reads:\n\n"
            f'"{current_value[:max_chars]}"\n\n'
            f"User instruction: {instruction}\n\n"
            f"Rewrite the {field_label} following the instruction precisely.\n\n"
            f"Output rules (STRICT):\n"
            f"- Length: {length_guide} — do not exceed this\n"
            f"- Plain prose only — no bullet points, no numbered lists\n"
            f"- No field labels or prefixes (do NOT start with \"{field_label}:\")\n"
            f"- No quotes around the output\n"
            f"- Start directly with the content"
        )

        api_key = _get_openai_key()
        suggested = _call_openai(prompt, api_key, max_tokens=400)

        _log('INFO', 'AI enhance field complete',
             correlationId=correlation_id,
             userId=path_user_id,
             field=field)

        return _response(200, {'field': field, 'suggestedValue': suggested})

    except Exception as e:
        _log('ERROR', 'AI enhance field error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})


# ---------------------------------------------------------------------------
# Shape B/C: section enhance
# ---------------------------------------------------------------------------


def _handle_section_enhance(body, path_user_id, instruction, correlation_id):
    section = body.get('section', '')

    if section != 'skills' and section not in _SECTION_ITEM_FIELDS:
        allowed = sorted(list(_SECTION_ITEM_FIELDS.keys()) + ['skills'])
        return _response(400, {'error': f'section must be one of: {", ".join(allowed)}'})

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        result = table.get_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': 'PORTFOLIO#current'},
            ProjectionExpression='parsedData, #cat',
            ExpressionAttributeNames={'#cat': 'category'},
        )

        if 'Item' not in result:
            return _response(404, {'error': 'Portfolio not found. Generate a portfolio first.'})

        parsed_data = result['Item'].get('parsedData') or {}
        category = result['Item'].get('category', 'software_engineer')

    except Exception as e:
        _log('ERROR', 'AI enhance fetch error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})

    if section == 'skills':
        return _enhance_skills(parsed_data, category, instruction, path_user_id, correlation_id)

    # Shape B: item field enhance
    enhance_field = body.get('enhanceField', '')
    if enhance_field not in _SECTION_ITEM_FIELDS[section]:
        allowed_fields = _SECTION_ITEM_FIELDS[section]
        return _response(400, {
            'error': f'enhanceField for "{section}" must be one of: {", ".join(allowed_fields)}'
        })

    item_index = body.get('itemIndex')
    if not isinstance(item_index, int) or item_index < 0:
        return _response(400, {'error': 'itemIndex must be a non-negative integer'})

    section_data = parsed_data.get(section, [])
    if not isinstance(section_data, list) or item_index >= len(section_data):
        return _response(400, {
            'error': f'itemIndex {item_index} is out of range for section "{section}"'
        })

    item = section_data[item_index]
    return _enhance_item(section, item, enhance_field, instruction, path_user_id, item_index, correlation_id)


# Human-readable labels for every item field shown as context to the LLM.
_ITEM_FIELD_LABELS = {
    # Experience
    'role':                      'Role / Job Title',
    'company':                   'Company',
    'location':                  'Location',
    'duration':                  'Duration',
    'description':               'Description',
    'key_points':                'Key Points',
    'channels_managed':          'Channels Managed',
    'financial_metrics_managed': 'Financial Metrics Managed',
    # Projects
    'title':                     'Project Title',
    'responsibilities':          'Responsibilities',
    'measurable_outcomes':       'Measurable Outcomes',
    'tech_stack':                'Tech Stack',
    'github_repo':               'GitHub Repo',
    'project_url':               'Project URL',
    'project_category':          'Project Category',
    'design_concept':            'Design Concept',
    'software_used':             'Software Used',
    # Education
    'degree':                    'Degree',
    'field_of_study':            'Field of Study',
    'institution':               'Institution',
    'year_range':                'Year Range',
    'grade_or_score':            'Grade / Score',
    # Certifications
    'name':                      'Name',
    'issuer':                    'Issuer',
    'year':                      'Year',
    # Achievements / Awards
    'awarding_body':             'Awarding Body',
    # Campaigns
    'campaign_name':             'Campaign Name',
    'campaign_type':             'Campaign Type',
    'channels_used':             'Channels Used',
    'budget':                    'Budget',
    'performance_metrics':       'Performance Metrics',
    # Finance
    'model_type':                'Model Type',
    'tools_used':                'Tools Used',
    'outcome':                   'Outcome',
    'portfolio_type':            'Portfolio Type',
    'assets_under_management':   'Assets Under Management',
    'performance_return':        'Performance / Return',
}

# Fields that are URLs or internal metadata — skip from context block
_SKIP_CONTEXT_KEYS = {'certification_url', 'achievement_url', 'award_url', 'github_repo', 'project_url', 'start_date', 'end_date', 'is_current', 'start_year', 'end_year'}


def _format_item_context(item, enhance_field):
    """Return a labelled multi-line string of all non-empty item fields.
    The field being enhanced is marked with >>> so the LLM knows what to update."""
    lines = []
    for key, value in item.items():
        if key in _SKIP_CONTEXT_KEYS:
            continue
        if value is None or value == '' or value == []:
            continue
        label = _ITEM_FIELD_LABELS.get(key, key.replace('_', ' ').title())
        if isinstance(value, list):
            text = '\n    '.join(str(v) for v in value if v)
            formatted = f"  {label}:\n    {text}"
        else:
            formatted = f"  {label}: {value}"
        if key == enhance_field:
            formatted = f">>> {formatted.lstrip()}"
        lines.append(formatted)
    return '\n'.join(lines)


def _enhance_item(section, item, enhance_field, instruction, path_user_id, item_index, correlation_id):
    current_value = item.get(enhance_field, '')
    is_list_field = isinstance(current_value, list)
    field_label = _ITEM_FIELD_LABELS.get(enhance_field, enhance_field.replace('_', ' ').title())

    # Full item context — every non-empty field labelled, target field prefixed with >>>
    item_context = _format_item_context(item, enhance_field)

    # Per-field length guidance
    _list_field_counts = {
        'key_points':           '4–6 points',
        'responsibilities':     '3–5 points',
        'measurable_outcomes':  '3–4 points',
        'performance_metrics':  '3–5 points',
    }
    _prose_field_lengths = {
        'description': '2–3 sentences (40–70 words maximum)',
        'outcome':     '2–3 sentences (40–70 words maximum)',
    }

    if is_list_field:
        count_guide = _list_field_counts.get(enhance_field, '3–5 points')
        prompt = (
            f"You are editing a portfolio website. "
            f"Below is the full {section} item. "
            f"The field marked with >>> is the one you must rewrite.\n\n"
            f"{item_context[:2500]}\n\n"
            f"User instruction: {instruction}\n\n"
            f"Task: Rewrite ONLY the \"{field_label}\" field using the rest of the item as context.\n\n"
            f"Output rules (STRICT):\n"
            f"- Return exactly {count_guide}, one per line, no blank lines between them\n"
            f"- No bullet symbols (no -, *, •), no numbers, no dashes at the start\n"
            f"- No field labels or prefixes (do NOT start with \"{field_label}:\" or similar)\n"
            f"- No surrounding explanation, commentary, or markdown\n"
            f"- Start directly with the first point"
        )
        max_tokens = 400
    else:
        length_guide = _prose_field_lengths.get(enhance_field, '2–3 sentences (under 60 words)')
        prompt = (
            f"You are editing a portfolio website. "
            f"Below is the full {section} item. "
            f"The field marked with >>> is the one you must rewrite.\n\n"
            f"{item_context[:2500]}\n\n"
            f"User instruction: {instruction}\n\n"
            f"Task: Rewrite ONLY the \"{field_label}\" field using the rest of the item as context.\n\n"
            f"Output rules (STRICT):\n"
            f"- Length: {length_guide} — do not exceed this\n"
            f"- Plain prose only — no bullet points, no numbered lists\n"
            f"- No field labels or prefixes (do NOT start with \"{field_label}:\" or similar)\n"
            f"- No quotes around the output\n"
            f"- No surrounding explanation, commentary, or markdown\n"
            f"- Start directly with the content"
        )
        max_tokens = 300

    try:
        api_key = _get_openai_key()
        suggested_text = _call_openai(prompt, api_key, max_tokens=max_tokens)

        if is_list_field:
            suggested_value = [line.strip() for line in suggested_text.split('\n') if line.strip()]
        else:
            suggested_value = suggested_text

        _log('INFO', 'AI enhance item complete',
             correlationId=correlation_id,
             userId=path_user_id,
             section=section,
             itemIndex=item_index,
             enhanceField=enhance_field)

        return _response(200, {
            'section': section,
            'itemIndex': item_index,
            'enhanceField': enhance_field,
            'suggestedValue': suggested_value,
        })

    except Exception as e:
        _log('ERROR', 'AI enhance item error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})


def _enhance_skills(parsed_data, category, instruction, path_user_id, correlation_id):
    current_skills = parsed_data.get('skills', [])
    current_skills_text = json.dumps(current_skills, ensure_ascii=False, cls=_DecimalEncoder)[:1500]

    context_sections = _SKILLS_CONTEXT_SECTIONS.get(category, _SKILLS_CONTEXT_DEFAULT)
    context_parts = []
    for ctx_section in context_sections:
        ctx_data = parsed_data.get(ctx_section)
        if ctx_data:
            ctx_text = json.dumps(ctx_data, ensure_ascii=False, cls=_DecimalEncoder)[:_CONTEXT_MAX_CHARS]
            context_parts.append(f"--- {ctx_section} ---\n{ctx_text}")

    context_block = '\n\n'.join(context_parts) if context_parts else 'No additional context.'

    prompt = (
        f"You are editing a portfolio website. The user wants to improve their skills section.\n\n"
        f"Current skills (JSON array of skill groups):\n{current_skills_text}\n\n"
        f"Context from other portfolio sections:\n{context_block}\n\n"
        f"User instruction: {instruction}\n\n"
        f"Return an improved skills section as a valid JSON array of skill group objects. "
        f'Each object must have "category" (string) and "skills" (array of strings). '
        f"Return ONLY the JSON array -- no explanation, no markdown code blocks."
    )

    try:
        api_key = _get_openai_key()
        suggested_text = _call_openai(prompt, api_key, max_tokens=800)

        clean = suggested_text.strip()
        if clean.startswith('```'):
            lines = clean.split('\n')
            clean = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
        suggested_groups = json.loads(clean)

        if not isinstance(suggested_groups, list):
            raise ValueError('Expected a JSON array')

        _log('INFO', 'AI enhance skills complete',
             correlationId=correlation_id,
             userId=path_user_id,
             category=category)

        return _response(200, {
            'section': 'skills',
            'suggestedValue': suggested_groups,
        })

    except (json.JSONDecodeError, ValueError) as parse_err:
        _log('ERROR', 'AI enhance skills JSON parse error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(parse_err))
        return _response(500, {'error': 'AI returned invalid skills format. Please try again.'})
    except Exception as e:
        _log('ERROR', 'AI enhance skills error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})


# ---------------------------------------------------------------------------
# Shape D: LLM-generated portfolio suggestions
# ---------------------------------------------------------------------------

_SUGGESTIONS_SYSTEM_PROMPT = (
    "You are a professional career coach and portfolio editor. "
    "Analyze the user's portfolio data and return actionable, personalized suggestions "
    "to improve it. Each suggestion must target a specific field in a specific section. "
    "Be direct, specific, and context-aware — reference the actual content when explaining "
    "what to fix. Return ONLY a valid JSON array — no explanation, no markdown."
)

# Maps section → the ONLY fields that can be AI-enhanced on the frontend.
# Suggestions MUST use one of these field values or the enhancement will not work.
_ENHANCEABLE_FIELDS = {
    'experience':         ['description', 'key_points'],
    'projects':           ['description', 'responsibilities', 'measurable_outcomes'],
    'achievements':       ['description'],
    'campaigns':          ['performance_metrics'],
    'financial_modeling': ['outcome'],
    # profile and skills are handled separately
}

_SUGGESTIONS_SCHEMA = (
    'Return a JSON array of suggestion objects. Each object must have these exact keys:\n'
    '  "id": unique string formatted as "<section>-<index>-<field>", e.g. "experience-0-key_points"\n'
    '  "section": one of "profile", "experience", "projects", "skills", "achievements", "campaigns", "financial_modeling"\n'
    '  "index": integer 0-based index within the section array. Omit (or null) only for profile and skills.\n'
    '  "field": MUST be one of the allowed fields below for each section — do not invent other field names:\n'
    '    - experience  → "description" or "key_points"\n'
    '    - projects    → "description", "responsibilities", or "measurable_outcomes"\n'
    '    - achievements → "description"\n'
    '    - campaigns   → "performance_metrics"\n'
    '    - financial_modeling → "outcome"\n'
    '    - profile     → omit "field"; use "profileKey" instead\n'
    '    - skills      → omit "field" and "index"\n'
    '  "profileKey": for profile section ONLY — must be one of "bio", "headline", "uniqueValue"\n'
    '  "label": short human-readable label, e.g. "Senior Engineer @ Acme" or "About"\n'
    '  "sublabel": one specific, actionable improvement referencing the actual content, e.g. '
    '"Your 3 key points lack metrics — add numbers to show impact"\n'
    '  "instruction": a ready-to-use prompt string the user will send directly to the AI enhancer. '
    'Make it specific to the actual content. Keep it under 200 characters.\n'
    '  "priority": "high" (empty or very weak), "medium" (present but improvable), or "low" (minor polish)\n\n'
    'Rules:\n'
    '- Return 3–8 suggestions total\n'
    '- Do not suggest improvements for fields that are already strong and detailed\n'
    '- Do not return more than 2 suggestions for the same section item\n'
    '- NEVER use a field name that is not in the allowed list above\n'
    '- The "id" must match the pattern "<section>-<index>-<field>" exactly\n'
    '- FIELD PURPOSE (critical — each field has a DIFFERENT purpose, do NOT suggest the same theme '
    'across multiple fields of the same item):\n'
    '    description: high-level "what/why/context" — the problem solved, scope, and overall role. '
    'Suggest improving clarity, narrative, or context here.\n'
    '    key_points (experience): specific achievements this person accomplished — suggest adding '
    'numbers, percentages, and impact metrics.\n'
    '    responsibilities (projects): specific technical actions taken — what was built, designed, '
    'or owned. Suggest making them more concrete and action-verb driven.\n'
    '    measurable_outcomes (projects): quantified results ONLY — % improvements, users impacted, '
    'time/cost saved. Suggest if these are missing or vague.\n'
    '- If an item already has description + responsibilities + measurable_outcomes, do NOT suggest '
    'the same "add metrics" theme to all three. Pick the weakest one and suggest only that.'
)


def _fmt_list(items, indent='  '):
    """Format a list field with each item on its own line for LLM readability."""
    if not isinstance(items, list) or not items:
        return f"{indent}(empty)"
    return '\n'.join(f"{indent}- {str(item)}" for item in items if item)


def _build_portfolio_summary(parsed_data, portfolio_content):
    """Build a detailed text summary of the portfolio for the LLM.

    Deliberately un-truncated for list fields so the LLM can judge quality
    (e.g. whether key_points contain metrics, whether outcomes are present).
    """
    parts = []

    profile = parsed_data.get('profile') or {}
    parts.append("=== PROFILE ===")
    parts.append(f"Name: {profile.get('full_name', '(missing)')}")
    parts.append(f"Headline: {profile.get('headline', '(missing)')}")
    parts.append(f"Email: {profile.get('email', '(missing)')}")
    parts.append(f"Profile image: {'yes' if profile.get('profile_image') else 'no'}")
    bio = (portfolio_content or {}).get('bio', '').strip()
    uv = (portfolio_content or {}).get('uniqueValue', '').strip()
    parts.append(f"Bio: {bio[:600] if bio else '(empty)'}")
    parts.append(f"Unique value: {uv[:400] if uv else '(empty)'}")

    for i, exp in enumerate((parsed_data.get('experience') or [])[:6]):
        parts.append(f"\n=== EXPERIENCE {i} ===")
        parts.append(f"Role: {exp.get('role', '')} @ {exp.get('company', '')}")
        parts.append(f"Duration: {exp.get('duration', '')}")
        desc = str(exp.get('description', '') or '')
        parts.append(f"Description: {desc[:500] if desc else '(empty)'}")
        kp = exp.get('key_points') or []
        parts.append(f"Key points ({len(kp) if isinstance(kp, list) else 0}):")
        parts.append(_fmt_list(kp))

    for i, proj in enumerate((parsed_data.get('projects') or [])[:6]):
        parts.append(f"\n=== PROJECT {i} ===")
        parts.append(f"Title: {proj.get('title', '')}")
        ts = proj.get('tech_stack') or []
        parts.append(f"Tech stack: {', '.join(str(t) for t in ts) if isinstance(ts, list) else str(ts)}")
        desc = str(proj.get('description', '') or '')
        parts.append(f"Description: {desc[:500] if desc else '(empty)'}")
        resp = proj.get('responsibilities') or []
        parts.append(f"Responsibilities ({len(resp) if isinstance(resp, list) else 0}):")
        parts.append(_fmt_list(resp))
        out = proj.get('measurable_outcomes') or []
        parts.append(f"Measurable outcomes ({len(out) if isinstance(out, list) else 0}):")
        parts.append(_fmt_list(out))

    skills = parsed_data.get('skills') or []
    parts.append(f"\n=== SKILLS ({len(skills)} groups) ===")
    for g in skills:
        cat = g.get('category', '')
        sk = g.get('skills') or []
        skill_names = ', '.join(str(s) for s in sk) if isinstance(sk, list) else ''
        parts.append(f"  {cat}: {skill_names if skill_names else '(empty)'}")

    ach = parsed_data.get('achievements') or []
    parts.append(f"\n=== ACHIEVEMENTS ({len(ach)} entries) ===")
    for i, a in enumerate(ach[:5]):
        parts.append(f"  [{i}] {a.get('title', '')} — {a.get('description', '')[:200]}")

    edu = parsed_data.get('education') or []
    parts.append(f"\n=== EDUCATION ({len(edu)} entries) ===")
    certs = parsed_data.get('certifications') or []
    parts.append(f"=== CERTIFICATIONS ({len(certs)} entries) ===")
    for c in certs[:6]:
        parts.append(f"  - {c.get('name', '')} ({c.get('issuer', '')})")

    return '\n'.join(parts)


# Profession-specific analysis guidance — focus only on sections relevant to each role.
_CATEGORY_GUIDANCE = {
    'software_engineer': (
        "This is a SOFTWARE ENGINEER portfolio. Focus suggestions on: experience (description, key_points), "
        "projects (description, responsibilities, measurable_outcomes), skills (technologies, frameworks, tools), "
        "and achievements. Do NOT suggest campaigns, financial modeling, or design-specific fields."
    ),
    'designer': (
        "This is a DESIGNER portfolio. Focus suggestions on: experience, projects (description, responsibilities, "
        "measurable_outcomes), skills (design tools, software), awards, and achievements. "
        "Do NOT suggest campaigns, financial modeling, or coding-heavy tech stacks."
    ),
    'marketing': (
        "This is a MARKETING professional portfolio. Focus suggestions on: experience, campaigns "
        "(performance_metrics), skills (marketing tools, platforms, channels), and achievements. "
        "Do NOT suggest software engineering projects or financial modeling."
    ),
    'finance': (
        "This is a FINANCE professional portfolio. Focus suggestions on: experience, financial_modeling "
        "(outcome), investment_portfolios, skills (financial tools, models), certifications, and achievements. "
        "Do NOT suggest software projects or marketing campaigns."
    ),
}
_CATEGORY_GUIDANCE_DEFAULT = (
    "Focus suggestions on experience, projects/work, skills, and achievements that are present in the data."
)


def _handle_analyze_and_suggest(body, path_user_id, correlation_id):
    # Prefer client-sent state (always reflects what the user currently sees,
    # even if auto-save hasn't flushed to DynamoDB yet). Fall back to DynamoDB.
    client_parsed_data = body.get('parsedData')
    client_portfolio_content = body.get('portfolioContent')
    client_category = body.get('category', '')

    if client_parsed_data and isinstance(client_parsed_data, dict):
        parsed_data = client_parsed_data
        portfolio_content = client_portfolio_content if isinstance(client_portfolio_content, dict) else {}
        category = client_category or 'software_engineer'
        _log('INFO', 'analyze_and_suggest using client-provided state',
             correlationId=correlation_id, userId=path_user_id)
    else:
        try:
            table = dynamodb.Table(DYNAMODB_TABLE)
            result = table.get_item(
                Key={'PK': f'USER#{path_user_id}', 'SK': 'PORTFOLIO#current'},
                ProjectionExpression='parsedData, portfolioContent, #cat',
                ExpressionAttributeNames={'#cat': 'category'},
            )
            if 'Item' not in result:
                return _response(404, {'error': 'Portfolio not found.'})

            parsed_data = result['Item'].get('parsedData') or {}
            portfolio_content = result['Item'].get('portfolioContent') or {}
            category = result['Item'].get('category', 'software_engineer')

        except Exception as e:
            _log('ERROR', 'analyze_and_suggest fetch error',
                 correlationId=correlation_id, userId=path_user_id, error=str(e))
            return _response(500, {'error': 'Internal server error'})

    profession_guidance = _CATEGORY_GUIDANCE.get(category, _CATEGORY_GUIDANCE_DEFAULT)
    summary = _build_portfolio_summary(parsed_data, portfolio_content)

    prompt = (
        f"Here is the user's complete portfolio data:\n\n"
        f"{summary[:6000]}\n\n"
        f"PROFESSION CONTEXT: {profession_guidance}\n\n"
        f"Analysis instructions:\n"
        f"1. CROSS-REFERENCE sections: Look for technologies, tools, frameworks, or skills that appear "
        f"in experience descriptions or project tech stacks / descriptions but are NOT listed in the "
        f"skills section. Suggest adding them to skills.\n"
        f"2. PER-ITEM COMPLETENESS: For each experience item, check if description AND key_points are "
        f"both present and substantive. For each project item, check if description, responsibilities, "
        f"AND measurable_outcomes are all present and non-empty. Suggest the specific missing or weak field.\n"
        f"3. CONTENT QUALITY: Read the actual text of key_points and responsibilities. If they lack "
        f"specific numbers, metrics, or measurable results, flag them. Vague points like 'Worked on X' "
        f"or 'Helped with Y' should be flagged for improvement.\n"
        f"4. PROFILE QUALITY: If bio is generic or short, or uniqueValue is weak, suggest improvements.\n"
        f"5. FIELD VARIETY: For any single section item, do NOT suggest the same improvement theme "
        f"(e.g., 'add metrics') for multiple different fields. Each field has a distinct purpose — "
        f"pick only the weakest or most missing field for each item.\n\n"
        f"{_SUGGESTIONS_SCHEMA}"
    )

    try:
        api_key = _get_openai_key()
        raw = _call_openai(prompt, api_key, max_tokens=1500)

        clean = raw.strip()
        if clean.startswith('```'):
            lines = clean.split('\n')
            clean = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])

        suggestions = json.loads(clean)
        if not isinstance(suggestions, list):
            raise ValueError('Expected JSON array')

        _log('INFO', 'analyze_and_suggest complete',
             correlationId=correlation_id, userId=path_user_id,
             count=len(suggestions))

        return _response(200, {'suggestions': suggestions})

    except (json.JSONDecodeError, ValueError) as parse_err:
        _log('ERROR', 'analyze_and_suggest parse error',
             correlationId=correlation_id, userId=path_user_id, error=str(parse_err))
        return _response(500, {'error': 'AI returned invalid format. Please try again.'})
    except Exception as e:
        _log('ERROR', 'analyze_and_suggest error',
             correlationId=correlation_id, userId=path_user_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})
