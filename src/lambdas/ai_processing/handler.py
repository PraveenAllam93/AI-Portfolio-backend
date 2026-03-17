"""
Lambda: AI Processing
Triggered by SQS queue. Calls OpenAI to parse resume and generate portfolio
content.

IMPORTANT: This Lambda only processes VALIDATED input from the
trusted pipeline.

Security notes:
  - Resume text is read from S3 (not SQS) — avoids 256 KB SQS limit and
    keeps PII out of queue traces and DLQ messages.
  - PII is detected using Microsoft Presidio (NER + pattern recognizers)
    BEFORE the text reaches OpenAI. The model receives a de-identified copy.
    Real values are stored in DynamoDB SK: PII#latest with restricted access.
  - Entities detected: EMAIL_ADDRESS, PHONE_NUMBER, US_SSN,
    and custom recognizers for LINKEDIN_URL and GITHUB_URL.
    PERSON/name is NOT masked — the portfolio is public-facing.
  - Section headings are extracted with regex before the AI API call to reduce
    token cost and guide accurate extraction.
  - Content hash deduplication record written after successful processing.
  - Raw exceptions logged to CloudWatch only — never stored in DynamoDB.
  - DynamoDB UpdateExpression always uses ExpressionAttributeNames.
"""

import json
import os
import re
import boto3
from datetime import datetime, timezone

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')
lambda_client = boto3.client('lambda')

MAIN_TABLE = os.environ.get('MAIN_TABLE')
PII_TABLE = os.environ.get('PII_TABLE')
OPENAI_SECRET_NAME = os.environ.get('OPENAI_SECRET_NAME')
PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET')
VALIDATED_BUCKET = os.environ.get('VALIDATED_BUCKET')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
PORTFOLIO_LAMBDA_NAME = os.environ.get('PORTFOLIO_LAMBDA_NAME')

# Cache across warm invocations
_openai_api_key = None
_presidio_analyzer = None
_presidio_anonymizer = None

# ---------------------------------------------------------------------------
# PII entity → token and storage key mapping
# ---------------------------------------------------------------------------

# Tokens embedded in the masked text sent to OpenAI.
# PERSON/name is intentionally excluded — the portfolio is public-facing
# and the person's name is meant to be displayed.
_ENTITY_TOKEN = {
    "EMAIL_ADDRESS": "{{EMAIL}}",
    "PHONE_NUMBER":  "{{PHONE}}",
    "US_SSN":        "{{SSN}}",
    "LINKEDIN_URL":  "{{LINKEDIN_URL}}",
    "GITHUB_URL":    "{{GITHUB_URL}}",
}

# Key used when storing PII values in DynamoDB PII#latest item
_ENTITY_PII_KEY = {
    "EMAIL_ADDRESS": "email",
    "PHONE_NUMBER":  "phone",
    "US_SSN":        "ssn",
    "LINKEDIN_URL":  "linkedin_url",
    "GITHUB_URL":    "github_url",
}

# ---------------------------------------------------------------------------
# Resume section heading detection (regex, no AI cost)
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(
    r'(?im)^\s*('
    r'SUMMARY|PROFESSIONAL SUMMARY|PROFILE|OBJECTIVE|ABOUT ME?'
    r'|WORK EXPERIENCE|PROFESSIONAL EXPERIENCE'
    r'|EXPERIENCE|EMPLOYMENT HISTORY|WORK HISTORY'
    r'|EDUCATION|ACADEMIC BACKGROUND|QUALIFICATIONS?'
    r'|TECHNICAL SKILLS?|SKILLS?|CORE COMPETENCIES|EXPERTISE|TECHNOLOGIES'
    r'|CERTIFICATIONS?|CERTIFICATES?|LICENSES?|CREDENTIALS'
    r'|PROJECTS?|PERSONAL PROJECTS?'
    r'|LANGUAGES?|SPOKEN LANGUAGES?'
    r'|CONTACT|CONTACT INFORMATION|CONTACT DETAILS'
    r')\s*$'
)

_HEADING_CANONICAL = {
    'SUMMARY': 'summary', 'PROFESSIONAL SUMMARY': 'summary',
    'PROFILE': 'summary', 'OBJECTIVE': 'summary',
    'ABOUT ME': 'summary', 'ABOUT': 'summary',
    'WORK EXPERIENCE': 'experience', 'PROFESSIONAL EXPERIENCE': 'experience',
    'EXPERIENCE': 'experience', 'EMPLOYMENT HISTORY': 'experience',
    'WORK HISTORY': 'experience',
    'EDUCATION': 'education', 'ACADEMIC BACKGROUND': 'education',
    'QUALIFICATIONS': 'education', 'QUALIFICATION': 'education',
    'TECHNICAL SKILLS': 'skills', 'SKILLS': 'skills', 'SKILL': 'skills',
    'CORE COMPETENCIES': 'skills', 'EXPERTISE': 'skills',
    'TECHNOLOGIES': 'skills',
    'CERTIFICATIONS': 'certifications', 'CERTIFICATION': 'certifications',
    'CERTIFICATES': 'certifications', 'CERTIFICATE': 'certifications',
    'LICENSES': 'certifications', 'LICENSE': 'certifications',
    'CREDENTIALS': 'certifications',
    'PROJECTS': 'projects', 'PERSONAL PROJECTS': 'projects',
    'PROJECT': 'projects',
    'LANGUAGES': 'languages', 'SPOKEN LANGUAGES': 'languages',
    'LANGUAGE': 'languages',
    'CONTACT': 'contact', 'CONTACT INFORMATION': 'contact',
    'CONTACT DETAILS': 'contact',
}

# ---------------------------------------------------------------------------
# Structured logger — outputs JSON, captured by CloudWatch Logs
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    entry = {"level": level, "function": "ai_processing", "message": message}
    entry.update(kwargs)
    print(json.dumps(entry))


def _log_info(message: str, **kwargs) -> None:
    _log("INFO", message, **kwargs)


def _log_error(message: str, **kwargs) -> None:
    _log("ERROR", message, **kwargs)


# ---------------------------------------------------------------------------
# Presidio engine initialisation (cached for warm invocations)
# ---------------------------------------------------------------------------


def _get_presidio_engines():
    """
    Initialise Presidio AnalyzerEngine and AnonymizerEngine.
    Loaded once per Lambda container and reused across warm invocations.

    Uses spaCy en_core_web_sm (bundled in the Lambda layer) for NER.
    Structured PII (email, phone, SSN, URLs) is handled by built-in
    and custom pattern recognizers.
    """
    global _presidio_analyzer, _presidio_anonymizer
    if _presidio_analyzer is not None:
        return _presidio_analyzer, _presidio_anonymizer

    from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
    from presidio_analyzer import RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine

    # Load small spaCy model (bundled in Lambda layer, ~12 MB)
    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
    provider = NlpEngineProvider(nlp_configuration=nlp_config)
    nlp_engine = provider.create_engine()

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(nlp_engine=nlp_engine)

    # Custom recognizer: LinkedIn profile URL
    registry.add_recognizer(PatternRecognizer(
        supported_entity="LINKEDIN_URL",
        patterns=[Pattern(
            "linkedin_url",
            r"https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?",
            score=0.95,
        )],
    ))

    # Custom recognizer: GitHub profile URL
    registry.add_recognizer(PatternRecognizer(
        supported_entity="GITHUB_URL",
        patterns=[Pattern(
            "github_url",
            r"https?://(?:www\.)?github\.com/[\w\-]+/?",
            score=0.95,
        )],
    ))

    _presidio_analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=registry,
    )
    _presidio_anonymizer = AnonymizerEngine()
    return _presidio_analyzer, _presidio_anonymizer


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------


def lambda_handler(event, context):
    """Process resume with OpenAI and generate portfolio data."""
    correlation_id = context.aws_request_id if context else 'local'

    for record in event['Records']:
        user_id = None
        upload_id = None
        try:
            message = json.loads(record['body'])
            user_id = message['userId']
            upload_id = message['uploadId']
            s3_text_key = message['s3TextKey']
            content_hash = message.get('contentHash', '')
            template_id = message.get('templateId', 'modern')

            _log_info(
                "AI processing started",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
                s3TextKey=s3_text_key,
            )

            _update_status(user_id, upload_id, 'AI_PROCESSING')

            # Read resume text from S3 — never from the SQS body
            resume_text = _read_text_from_s3(s3_text_key, correlation_id)
            if not resume_text:
                _update_status(user_id, upload_id, 'AI_FAILED', {
                    'aiError': 'Failed to read resume text from storage.',
                })
                continue

            # Pre-extract section headings (regex, zero cost)
            detected_sections = _extract_sections(resume_text)
            _log_info(
                "Sections detected",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
                sections=detected_sections,
            )

            # Mask PII with Presidio — AI never sees contact details
            masked_text, pii_map = _extract_and_mask_pii(
                resume_text, correlation_id
            )
            _log_info(
                "PII masked",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
                piiFields=list(pii_map.keys()),
            )

            # Store real PII before AI call — survives any AI failure
            _store_pii(user_id, upload_id, pii_map)

            api_key = _get_openai_key()

            parsed_data = _parse_resume_with_openai(
                masked_text, detected_sections, api_key, correlation_id
            )

            if not parsed_data:
                _log_error(
                    "OpenAI returned no parsed data",
                    correlationId=correlation_id,
                    userId=user_id,
                    uploadId=upload_id,
                )
                _update_status(user_id, upload_id, 'AI_FAILED', {
                    'aiError': 'Failed to parse resume with AI',
                })
                continue

            portfolio_content = _generate_portfolio_content(
                parsed_data, api_key, correlation_id
            )

            _update_status(user_id, upload_id, 'AI_COMPLETE', {
                'parsedData': json.dumps(parsed_data),
                'portfolioContent': json.dumps(portfolio_content),
            })

            _trigger_portfolio_generation(
                user_id, upload_id, parsed_data, portfolio_content,
                content_hash, template_id,
            )

            _log_info(
                "AI processing complete",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
            )

        except Exception as e:
            _log_error(
                "AI processing error",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
                error=str(e),
            )
            if user_id and upload_id:
                _update_status(user_id, upload_id, 'AI_FAILED', {
                    'aiError': 'AI processing failed. Please try again.',
                })
            raise

    return {'statusCode': 200, 'body': 'Processing complete'}


# ---------------------------------------------------------------------------
# S3 text reader
# ---------------------------------------------------------------------------


def _read_text_from_s3(s3_text_key: str, correlation_id: str) -> str:
    try:
        resp = s3_client.get_object(Bucket=VALIDATED_BUCKET, Key=s3_text_key)
        return resp['Body'].read().decode('utf-8')
    except Exception as e:
        _log_error(
            "Failed to read resume text from S3",
            correlationId=correlation_id,
            s3TextKey=s3_text_key,
            error=str(e),
        )
        return ''


# ---------------------------------------------------------------------------
# Section heading extractor
# ---------------------------------------------------------------------------


def _extract_sections(text: str) -> list[str]:
    """Return canonical section names found in the resume via regex."""
    seen: set[str] = set()
    detected: list[str] = []
    for m in _HEADING_RE.finditer(text):
        key = m.group(1).strip().upper()
        canonical = _HEADING_CANONICAL.get(key, key.lower())
        if canonical not in seen:
            seen.add(canonical)
            detected.append(canonical)
    return detected


# ---------------------------------------------------------------------------
# PII masking via Presidio
# ---------------------------------------------------------------------------


def _extract_and_mask_pii(
    text: str, correlation_id: str
) -> tuple[str, dict]:
    """
    Detect and replace PII using Presidio before the text reaches OpenAI.

    Detection:
      - EMAIL_ADDRESS, PHONE_NUMBER, US_SSN  — pattern recognizers
      - LINKEDIN_URL, GITHUB_URL              — custom pattern recognizers
      - PERSON/name is NOT masked — portfolio is public-facing

    Each entity type is replaced with a stable token ({{EMAIL}}, {{PHONE}},
    etc.) that the portfolio generator can substitute with real values from
    the PII#latest DynamoDB item.

    Returns (masked_text, pii_map) where pii_map stores the first occurrence
    of each entity type by storage key (email, phone, name, …).
    """
    from presidio_anonymizer.entities import OperatorConfig

    try:
        analyzer, anonymizer = _get_presidio_engines()

        entities = list(_ENTITY_TOKEN.keys())
        results = analyzer.analyze(text=text, entities=entities, language="en")

        # Extract first occurrence of each entity type for pii_map
        pii_map: dict[str, str] = {}
        seen_types: set[str] = set()
        for r in sorted(results, key=lambda x: x.start):
            if r.entity_type not in seen_types:
                seen_types.add(r.entity_type)
                key = _ENTITY_PII_KEY.get(r.entity_type)
                if key:
                    pii_map[key] = text[r.start:r.end]

        # Replace every detected span with its token
        operators = {
            entity: OperatorConfig("replace", {"new_value": token})
            for entity, token in _ENTITY_TOKEN.items()
        }
        anonymized = anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators,
        )
        return anonymized.text, pii_map

    except Exception as e:
        # Presidio failure is non-fatal in dev; block in prod
        _log_error(
            "Presidio PII masking error",
            correlationId=correlation_id,
            error=str(e),
        )
        if ENVIRONMENT == 'prod':
            raise
        # Dev/staging: return unmasked text (no PII stored)
        return text, {}


# ---------------------------------------------------------------------------
# PII storage
# ---------------------------------------------------------------------------


def _store_pii(user_id: str, upload_id: str, pii_map: dict) -> None:
    """
    Store real PII values in a dedicated DynamoDB item.
    PK: USER#{userId}, SK: PII#latest

    Only the portfolio generator reads this item to unmask tokens when
    rendering HTML. No public API endpoint returns PII#latest items.
    SSN is stored but never rendered in the portfolio.
    """
    if not pii_map:
        return
    table = dynamodb.Table(PII_TABLE)
    table.put_item(Item={
        'PK': f'USER#{user_id}',
        'SK': 'PII#latest',
        'uploadId': upload_id,
        'updatedAt': datetime.now(timezone.utc).isoformat(),
        **pii_map,
    })


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------


def _get_openai_key():
    global _openai_api_key
    if _openai_api_key:
        return _openai_api_key
    response = secrets_client.get_secret_value(SecretId=OPENAI_SECRET_NAME)
    secret = json.loads(response['SecretString'])
    _openai_api_key = (
        secret.get('api_key')
        or secret.get('OPENAI_API_KEY')
        or secret.get('openai_api_key')
    )
    return _openai_api_key


def _parse_resume_with_openai(
    masked_text: str,
    detected_sections: list[str],
    api_key: str,
    correlation_id: str,
) -> dict:
    """
    Parse de-identified resume with OpenAI.
    Instructs the model to preserve {{TOKEN}} placeholders as-is in output.
    """
    try:
        import urllib.request

        sections_hint = (
            f"Detected sections: {', '.join(detected_sections)}."
            if detected_sections else
            "No explicit section headings detected."
        )

        # Build prompt lines individually so no Python source line > 79 chars.
        pii_note = (
            "IMPORTANT: PII has been redacted and replaced with tokens "
            "like {{EMAIL}}, {{PHONE}}, "
            "{{LINKEDIN_URL}}, {{GITHUB_URL}}, {{SSN}}. "
            "Preserve these tokens EXACTLY as-is in your JSON output. "
            "Do NOT substitute them with guessed or invented values."
        )
        json_schema = (
            '{{\n'
            '    "name": "Full Name",\n'
            '    "title": "Professional Title",\n'
            '    "email": "{{{{EMAIL}}}}",\n'
            '    "phone": "{{{{PHONE}}}}",\n'
            '    "location": "City, Country",\n'
            '    "summary": "Professional summary (2-3 sentences)",\n'
            '    "skills": ["skill1", "skill2"],\n'
            '    "experience": [{{\n'
            '        "company": "Company Name",\n'
            '        "title": "Job Title",\n'
            '        "duration": "Start - End",\n'
            '        "description": "Brief description",\n'
            '        "highlights": ["achievement1"]\n'
            '    }}],\n'
            '    "education": [{{\n'
            '        "institution": "University Name",\n'
            '        "degree": "Degree Name",\n'
            '        "field": "Field of Study",\n'
            '        "year": "Graduation Year"\n'
            '    }}],\n'
            '    "certifications": ["cert1"],\n'
            '    "languages": ["language1"],\n'
            '    "links": {{\n'
            '        "linkedin": "{{{{LINKEDIN_URL}}}}",\n'
            '        "github": "{{{{GITHUB_URL}}}}",\n'
            '        "portfolio": ""\n'
            '    }}\n'
            '}}'
        )
        prompt = (
            "Parse the following resume and extract structured information.\n"
            f"{sections_hint} Only populate sections that are present.\n\n"
            f"{pii_note}\n\n"
            f"Return a JSON object:\n{json_schema}\n\n"
            f"Resume text (PII redacted):\n{masked_text[:8000]}\n\n"
            "Return ONLY the JSON object, no additional text."
        )

        body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a resume parser. Return valid JSON only. "
                        "Preserve {{TOKEN}} placeholders exactly as-is."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=body,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        content = result['choices'][0]['message']['content']
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
        return json.loads(content.strip())

    except Exception as e:
        _log_error("OpenAI parsing error", correlationId=correlation_id,
                   error=str(e))
        return None


def _generate_portfolio_content(
    parsed_data: dict, api_key: str, correlation_id: str,
) -> dict:
    """
    Generate portfolio copy using de-identified parsed data.
    AI writes third-person bio and headline without knowing the real name.
    """
    try:
        import urllib.request

        schema = (
            '{{\n'
            '    "headline": "One-line professional headline (no PII)",\n'
            '    "bio": "3-4 sentence third-person bio (no name, no PII)",\n'
            '    "skillCategories": {{"category": ["skill1"]}},\n'
            '    "experienceHighlights": [{{\n'
            '        "title": "Role at Company",\n'
            '        "impact": "Key achievement"\n'
            '    }}],\n'
            '    "uniqueValue": "What makes this person unique (no PII)"\n'
            '}}'
        )
        data_json = json.dumps(parsed_data, indent=2)
        prompt = (
            "Based on this parsed resume data, generate professional "
            "portfolio content.\n"
            "The person's PII has been redacted — write bio and headline "
            "in third person without using a name "
            "(e.g. 'This engineer...', 'A seasoned professional...').\n"
            "Do NOT include any {{TOKEN}} placeholders in your output.\n\n"
            f"Input:\n{data_json}\n\n"
            f"Return a JSON object:\n{schema}\n\n"
            "Return ONLY the JSON object."
        )

        body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a professional portfolio content writer. "
                        "Never include real names, emails, phone numbers, "
                        "URLs, or {{TOKEN}} placeholders in the content."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1500,
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=body,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        content = result['choices'][0]['message']['content']
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
        return json.loads(content.strip())

    except Exception as e:
        _log_error("Portfolio content generation error",
                   correlationId=correlation_id, error=str(e))
        return {}


# ---------------------------------------------------------------------------
# Portfolio trigger + dedup record
# ---------------------------------------------------------------------------


def _trigger_portfolio_generation(
    user_id: str,
    upload_id: str,
    parsed_data: dict,
    portfolio_content: dict,
    content_hash: str,
    template_id: str = 'modern',
) -> None:
    table = dynamodb.Table(MAIN_TABLE)

    # PORTFOLIO#current — masked parsedData, no raw PII.
    # contentHash stored here so the portfolio generator can update the
    # dedup record (CONTENT#{hash}) with the final portfolioPath on publish.
    # templateId stored so the generator uses the user's chosen template.
    table.put_item(Item={
        'PK': f'USER#{user_id}',
        'SK': 'PORTFOLIO#current',
        'userId': user_id,
        'uploadId': upload_id,
        'parsedData': parsed_data,
        'portfolioContent': portfolio_content,
        'contentHash': content_hash,
        'templateId': template_id,
        'version': 1,
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'status': 'GENERATING',
    })

    # Dedup record — future identical upload by same user skips AI
    if content_hash:
        table.put_item(Item={
            'PK': f'USER#{user_id}',
            'SK': f'CONTENT#{content_hash}',
            'uploadId': upload_id,
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'portfolioPath': '',  # filled in by portfolio generator
        })

    if PORTFOLIO_LAMBDA_NAME:
        lambda_client.invoke(
            FunctionName=PORTFOLIO_LAMBDA_NAME,
            InvocationType='Event',
            Payload=json.dumps({'userId': user_id, 'uploadId': upload_id}),
        )
        _log_info("Portfolio generation triggered",
                  userId=user_id, uploadId=upload_id)


# ---------------------------------------------------------------------------
# DynamoDB status updater
# ---------------------------------------------------------------------------


def _update_status(user_id, upload_id, status, extra_data=None):
    table = dynamodb.Table(MAIN_TABLE)

    update_expr = (
        "SET #status = :status, #updatedAt = :updatedAt, #gsi1pk = :gsi1pk"
    )
    expr_names = {
        '#status': 'status',
        '#updatedAt': 'updatedAt',
        '#gsi1pk': 'GSI1PK',
    }
    expr_values = {
        ':status': status,
        ':updatedAt': datetime.now(timezone.utc).isoformat(),
        ':gsi1pk': f'STATUS#{status}',
    }

    if extra_data:
        for k, v in extra_data.items():
            alias = f'#extra_{k}'
            update_expr += f", {alias} = :{k}"
            expr_names[alias] = k
            expr_values[f':{k}'] = v

    table.update_item(
        Key={
            'PK': f'USER#{user_id}',
            'SK': f'UPLOAD#{upload_id}',
        },
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )
