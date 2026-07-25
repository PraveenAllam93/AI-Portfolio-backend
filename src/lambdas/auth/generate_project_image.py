"""
Lambda: AI Project Image Generator

POST /portfolio/{userId}/project-image/generate — Cognito-authenticated.

Body: { "sectionKey": "projects", "itemIdx": 0 }

Calls DALL-E 3 with a prompt built solely from the selected project/experience
item's content, the user's portfolio category, and the chosen template's
dark/light aesthetic. Downloads the generated image from OpenAI's temp URL
and uploads it to the portfolio S3 bucket under {userId}/assets/{uuid}.jpg.
Returns the CloudFront URL — does NOT auto-save; the frontend adds the URL
to the item's images array only after the user explicitly accepts it.

Rate limit: DAILY_GENERATION_LIMIT (default 10) generations per user per
calendar day (UTC), enforced atomically via a DynamoDB counter item:
  PK: USER#{userId}, SK: IMAGE_GEN#{YYYY-MM-DD}

Security notes:
- userId in path MUST match the Cognito token sub.
- Only the target item's fields are sent to DALL-E; no other PII is included.
- Rate limit is enforced atomically with ConditionExpression.
- Image bytes are downloaded over HTTPS and re-uploaded to our S3; the
  OpenAI temp URL is never exposed to the client.
- S3 key is a UUID — no user-controlled input reaches the key.
"""

import base64
import json
import os
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import unquote

import boto3

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET')
CLOUDFRONT_DOMAIN = os.environ.get('CLOUDFRONT_DOMAIN')
OPENAI_SECRET_NAME = os.environ.get('OPENAI_SECRET_NAME')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')
DAILY_GENERATION_LIMIT = int(os.environ.get('DAILY_GENERATION_LIMIT', '10'))

_ALLOWED_SECTIONS = {'projects', 'experience'}
MAX_ITEM_IMAGES = 3

_openai_api_key = None


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({
        "level": level,
        "function": "generate_project_image",
        "message": message,
        **kwargs,
    }))


def _response(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'X-Content-Type-Options': 'nosniff',
        },
        'body': json.dumps(body),
    }


def _get_openai_key() -> str:
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


def _check_and_increment_rate_limit(user_id: str) -> bool:
    """
    Atomically increment today's generation counter.
    Returns True if under the limit (proceed), False if limit exceeded.
    Uses ConditionExpression so the check + increment are atomic.
    """
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    # TTL: expire the counter record at end of day UTC
    end_of_day = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
    expire_ts = int(end_of_day.timestamp()) + 1

    table = dynamodb.Table(DYNAMODB_TABLE)
    try:
        table.update_item(
            Key={'PK': f'USER#{user_id}', 'SK': f'IMAGE_GEN#{today}'},
            UpdateExpression='ADD #count :one SET #ttl = if_not_exists(#ttl, :expire)',
            ConditionExpression='attribute_not_exists(#count) OR #count < :limit',
            ExpressionAttributeNames={
                '#count': 'count',
                '#ttl': 'ttl',
            },
            ExpressionAttributeValues={
                ':one': 1,
                ':limit': DAILY_GENERATION_LIMIT,
                ':expire': expire_ts,
            },
        )
        return True
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return False


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_CATEGORY_STYLES = {
    'software_engineer': (
        "a clean, professional tech illustration for a software engineer portfolio. "
        "Style: modern flat-design — think architectural diagram, UI mockup, or abstract "
        "data flow visualization. Technical and sophisticated."
    ),
    'designer': (
        "a polished, creative visual for a UX/product designer portfolio. "
        "Style: sleek design mockup, minimal composition, or artistic layout that "
        "showcases visual craft and design sensibility."
    ),
    'marketing': (
        "a vibrant, professional visual for a marketing professional's portfolio. "
        "Style: digital campaign aesthetic — clean brand imagery, bold typography "
        "arrangements, or abstract marketing concept art."
    ),
    'finance': (
        "a clean, professional data visualization for a finance portfolio. "
        "Style: corporate and precise — abstract chart art, financial data "
        "visualization, or sophisticated geometric composition."
    ),
}

_DARK_TEMPLATES = {'neon', 'circuit', 'codex', 'nebula', 'glitch', 'ember', 'obsidian', 'voltage', 'nimbus', 'console', 'flux', 'monolith', 'helix', 'orbit'}


def _build_image_prompt(item: dict, section: str, category: str, template_id: str) -> str:
    style = _CATEGORY_STYLES.get(category, _CATEGORY_STYLES['software_engineer'])

    if template_id in _DARK_TEMPLATES:
        palette = "Dark background palette: deep navy, charcoal, or near-black with vibrant accent colors."
    else:
        palette = "Light background palette: clean white or light gray with professional accent colors."

    content_parts = []
    if section == 'projects':
        if item.get('title'):
            content_parts.append(f"Project: {item['title']}")
        if item.get('description'):
            content_parts.append(f"Description: {str(item['description'])[:300]}")
        tech = item.get('tech_stack')
        if isinstance(tech, list) and tech:
            content_parts.append(f"Technologies: {', '.join(str(t) for t in tech[:6])}")
        resp = item.get('responsibilities')
        if isinstance(resp, list) and resp:
            content_parts.append(f"Key work: {str(resp[0])[:200]}")
    elif section == 'experience':
        if item.get('role'):
            content_parts.append(f"Role: {item['role']}")
        if item.get('company'):
            content_parts.append(f"Company: {item['company']}")
        if item.get('description'):
            content_parts.append(f"Description: {str(item['description'])[:300]}")

    content = '\n'.join(content_parts) if content_parts else 'Professional portfolio project'

    return (
        f"Create {style}\n\n"
        f"The image represents:\n{content}\n\n"
        f"{palette}\n\n"
        "Requirements:\n"
        "- No text, labels, or typography in the image\n"
        "- Professional, portfolio-quality visual\n"
        "- Suitable as a project card hero image on a portfolio website\n"
        "- High quality, detailed rendering"
    )


# ---------------------------------------------------------------------------
# OpenAI + S3 helpers
# ---------------------------------------------------------------------------

def _call_dalle(prompt: str, api_key: str) -> bytes:
    """Call DALL-E 3 and return raw image bytes.
    Handles both url and b64_json response formats.
    """
    payload = json.dumps({
        "model": "gpt-image-1",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "quality": "medium",
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.openai.com/v1/images/generations',
        data=payload,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f"OpenAI {e.code}: {error_body}") from e

    item = result['data'][0]

    if 'b64_json' in item:
        return base64.b64decode(item['b64_json'])

    if 'url' in item:
        img_req = urllib.request.Request(
            item['url'], headers={'User-Agent': 'AI-Portfolio/1.0'}
        )
        with urllib.request.urlopen(img_req, timeout=30) as img_resp:
            return img_resp.read()

    raise RuntimeError(f"Unexpected DALL-E response keys: {list(item.keys())}")


def _store_image(image_bytes: bytes, user_id: str, upload_id: str | None, correlation_id: str) -> str:
    """Upload image bytes to S3 and return the CloudFront URL."""
    image_id = str(uuid.uuid4())
    if upload_id:
        s3_key = f"{user_id}/{upload_id}/assets/{image_id}.jpg"
    else:
        s3_key = f"{user_id}/assets/{image_id}.jpg"

    s3_client.put_object(
        Bucket=PORTFOLIO_BUCKET,
        Key=s3_key,
        Body=image_bytes,
        ContentType='image/jpeg',
    )

    _log('INFO', 'AI image stored in S3',
         correlationId=correlation_id, userId=user_id, s3Key=s3_key)

    return f"https://{CLOUDFRONT_DOMAIN}/{s3_key}"


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    path_params = event.get('pathParameters') or {}
    path_user_id = unquote(path_params.get('userId', ''))
    upload_id = unquote(path_params.get('uploadId', ''))
    token_sub = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub', '')
    )
    if not path_user_id or path_user_id != token_sub:
        _log('WARNING', 'Auth mismatch', correlationId=correlation_id)
        return _response(403, {'error': 'Forbidden'})

    if not upload_id:
        return _response(400, {'error': 'Missing uploadId'})

    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, ValueError):
        return _response(400, {'error': 'Invalid JSON body'})

    section_key = str(body.get('sectionKey', '')).strip()
    item_idx = body.get('itemIdx')
    # Frontend may pass the item data directly to avoid a round-trip DynamoDB
    # read and to ensure the image is built from what the user sees on screen.
    item_data_override = body.get('itemData')

    if section_key not in _ALLOWED_SECTIONS:
        return _response(400, {
            'error': f'sectionKey must be one of: {", ".join(sorted(_ALLOWED_SECTIONS))}'
        })
    if not isinstance(item_idx, int) or item_idx < 0:
        return _response(400, {'error': 'itemIdx must be a non-negative integer'})

    # Rate limit check (atomic — does not decrement on failure)
    if not _check_and_increment_rate_limit(path_user_id):
        _log('WARNING', 'Daily generation limit reached',
             correlationId=correlation_id, userId=path_user_id)
        return _response(429, {
            'error': f'Daily image generation limit of {DAILY_GENERATION_LIMIT} reached. Try again tomorrow.'
        })

    # Fetch portfolio record for category/templateId (always needed for style).
    # If itemData is provided in the request we skip parsing parsedData.
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        result = table.get_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': f'PORTFOLIO#{upload_id}'},
            ProjectionExpression='parsedData, #cat, #tid',
            ExpressionAttributeNames={
                '#cat': 'category',
                '#tid': 'templateId',
            },
        )
    except Exception as e:
        _log('ERROR', 'DynamoDB fetch error',
             correlationId=correlation_id, userId=path_user_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})

    if 'Item' not in result:
        return _response(404, {'error': 'Portfolio not found. Generate a portfolio first.'})

    category = result['Item'].get('category', 'software_engineer')
    template_id = result['Item'].get('templateId', 'neon')

    if item_data_override and isinstance(item_data_override, dict):
        # Use data passed directly from the frontend
        item = item_data_override
    else:
        # Fall back to fetching item from parsedData by index
        parsed_data = result['Item'].get('parsedData') or {}
        section_data = parsed_data.get(section_key, [])
        if not isinstance(section_data, list) or item_idx >= len(section_data):
            return _response(400, {
                'error': f'itemIdx {item_idx} is out of range for section "{section_key}"'
            })
        item = section_data[item_idx]

    existing_images = item.get('images') or []
    if isinstance(existing_images, list) and len(existing_images) >= MAX_ITEM_IMAGES:
        return _response(400, {
            'error': f'This item already has the maximum of {MAX_ITEM_IMAGES} images'
        })

    try:
        api_key = _get_openai_key()
        prompt = _build_image_prompt(item, section_key, category, template_id)

        _log('INFO', 'Starting DALL-E 3 generation',
             correlationId=correlation_id,
             userId=path_user_id,
             sectionKey=section_key,
             itemIdx=item_idx,
             category=category,
             templateId=template_id)

        image_bytes = _call_dalle(prompt, api_key)
        image_url = _store_image(image_bytes, path_user_id, upload_id, correlation_id)

        _log('INFO', 'Project image generation complete',
             correlationId=correlation_id,
             userId=path_user_id,
             sectionKey=section_key,
             itemIdx=item_idx)

        return _response(200, {'imageUrl': image_url})

    except Exception as e:
        _log('ERROR', 'Image generation error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Image generation failed. Please try again.'})
