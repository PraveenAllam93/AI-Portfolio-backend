"""
Lambda: AI Processing
Triggered by SQS queue. Calls OpenAI to parse resume and generate portfolio content.
IMPORTANT: This Lambda only processes VALIDATED input from the trusted pipeline.
"""

import json
import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')
lambda_client = boto3.client('lambda')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
OPENAI_SECRET_NAME = os.environ.get('OPENAI_SECRET_NAME')
PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
PORTFOLIO_LAMBDA_NAME = os.environ.get('PORTFOLIO_LAMBDA_NAME')

# Cache OpenAI API key
_openai_api_key = None


def lambda_handler(event, context):
    """Process resume with OpenAI and generate portfolio data."""
    try:
        for record in event['Records']:
            message = json.loads(record['body'])

            user_id = message['userId']
            upload_id = message['uploadId']
            resume_text = message['resumeText']

            print(f"AI Processing: {upload_id} for user {user_id}")

            # Update status
            _update_status(user_id, upload_id, 'AI_PROCESSING')

            # Get OpenAI API key
            api_key = _get_openai_key()

            # Parse resume with OpenAI
            parsed_data = _parse_resume_with_openai(resume_text, api_key)

            if not parsed_data:
                _update_status(user_id, upload_id, 'AI_FAILED', {
                    'error': 'Failed to parse resume with AI'
                })
                continue

            # Generate portfolio content
            portfolio_content = _generate_portfolio_content(parsed_data, api_key)

            # Store parsed data and portfolio content
            _update_status(user_id, upload_id, 'AI_COMPLETE', {
                'parsedData': parsed_data,
                'portfolioContent': portfolio_content
            })

            # Trigger portfolio generation
            _trigger_portfolio_generation(user_id, upload_id, parsed_data, portfolio_content)

            print(f"AI processing complete: {upload_id}")

        return {'statusCode': 200, 'body': 'Processing complete'}

    except Exception as e:
        print(f"AI processing error: {str(e)}")
        raise


def _get_openai_key():
    """Get OpenAI API key from Secrets Manager (cached)."""
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


def _parse_resume_with_openai(resume_text: str, api_key: str) -> dict:
    """Parse resume text using OpenAI API."""
    try:
        import urllib.request
        import urllib.error

        prompt = f"""Parse the following resume and extract structured information.
Return a JSON object with the following structure:
{{
    "name": "Full Name",
    "title": "Professional Title",
    "email": "email@example.com",
    "phone": "phone number",
    "location": "City, Country",
    "summary": "Professional summary (2-3 sentences)",
    "skills": ["skill1", "skill2", ...],
    "experience": [
        {{
            "company": "Company Name",
            "title": "Job Title",
            "duration": "Start - End",
            "description": "Brief description",
            "highlights": ["achievement1", "achievement2"]
        }}
    ],
    "education": [
        {{
            "institution": "University Name",
            "degree": "Degree Name",
            "field": "Field of Study",
            "year": "Graduation Year"
        }}
    ],
    "certifications": ["cert1", "cert2"],
    "languages": ["language1", "language2"],
    "links": {{
        "linkedin": "url",
        "github": "url",
        "portfolio": "url"
    }}
}}

Resume text:
{resume_text[:8000]}

Return ONLY the JSON object, no additional text."""

        request_body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a resume parser. Extract information accurately and return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }).encode('utf-8')

        request = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=request_body,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
        )

        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))

        content = result['choices'][0]['message']['content']

        # Clean up JSON if wrapped in markdown
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]

        return json.loads(content.strip())

    except Exception as e:
        print(f"OpenAI parsing error: {str(e)}")
        return None


def _generate_portfolio_content(parsed_data: dict, api_key: str) -> dict:
    """Generate enhanced portfolio content using OpenAI."""
    try:
        import urllib.request

        prompt = f"""Based on this parsed resume data, generate enhanced portfolio content.
Create engaging, professional descriptions suitable for a portfolio website.

Input data:
{json.dumps(parsed_data, indent=2)}

Return a JSON object with:
{{
    "headline": "A compelling one-line headline",
    "bio": "An engaging 3-4 sentence bio for the about section",
    "skillCategories": {{
        "category1": ["skill1", "skill2"],
        "category2": ["skill3", "skill4"]
    }},
    "experienceHighlights": [
        {{
            "title": "Role at Company",
            "impact": "Key achievement or impact statement"
        }}
    ],
    "uniqueValue": "What makes this person unique (2 sentences)"
}}

Return ONLY the JSON object."""

        request_body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a professional portfolio content writer."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1500
        }).encode('utf-8')

        request = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=request_body,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
        )

        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))

        content = result['choices'][0]['message']['content']

        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]

        return json.loads(content.strip())

    except Exception as e:
        print(f"Portfolio content generation error: {str(e)}")
        return {}


def _trigger_portfolio_generation(
    user_id: str,
    upload_id: str,
    parsed_data: dict,
    portfolio_content: dict
):
    """Trigger the portfolio generator Lambda."""
    # Store data for portfolio generator
    table = dynamodb.Table(DYNAMODB_TABLE)
    table.put_item(Item={
        'PK': f'USER#{user_id}',
        'SK': 'PORTFOLIO#current',
        'userId': user_id,
        'uploadId': upload_id,
        'parsedData': parsed_data,
        'portfolioContent': portfolio_content,
        'version': 1,
        'createdAt': datetime.utcnow().isoformat(),
        'status': 'GENERATING'
    })

    # Invoke portfolio generator Lambda asynchronously
    if PORTFOLIO_LAMBDA_NAME:
        lambda_client.invoke(
            FunctionName=PORTFOLIO_LAMBDA_NAME,
            InvocationType='Event',  # async
            Payload=json.dumps({
                'userId': user_id,
                'uploadId': upload_id
            })
        )
        print(f"Triggered portfolio generation for {upload_id}")


def _update_status(user_id, upload_id, status, extra_data=None):
    """Update upload status in DynamoDB."""
    table = dynamodb.Table(DYNAMODB_TABLE)

    update_expr = "SET #status = :status, updatedAt = :updatedAt, GSI1PK = :gsi1pk"
    expr_values = {
        ':status': status,
        ':updatedAt': datetime.utcnow().isoformat(),
        ':gsi1pk': f'STATUS#{status}'
    }

    if extra_data:
        for key, value in extra_data.items():
            if isinstance(value, dict):
                value = json.dumps(value)
            update_expr += f", {key} = :{key}"
            expr_values[f':{key}'] = value

    table.update_item(
        Key={
            'PK': f'USER#{user_id}',
            'SK': f'UPLOAD#{upload_id}'
        },
        UpdateExpression=update_expr,
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues=expr_values
    )
