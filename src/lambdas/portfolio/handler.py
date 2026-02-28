"""
Lambda: Portfolio Generator
Generates static HTML/CSS portfolio website from parsed resume data.
Outputs to S3 portfolio bucket for CloudFront delivery.

Security notes:
  - All user-supplied strings are HTML-escaped before injection (XSS prevention)
  - Link URLs validated to http/https only (javascript: injection prevention)
  - Content-Security-Policy header added to generated pages (script-src 'none')
  - Arbitrary fields from AI output are never treated as raw HTML
"""

import html
import json
import os
import re
import boto3
from datetime import datetime, timezone

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Only allow http and https schemes in user-supplied URLs
_ALLOWED_URL_RE = re.compile(r'^https?://', re.IGNORECASE)

# ---------------------------------------------------------------------------
# Structured logger — outputs JSON, captured by CloudWatch Logs
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    entry = {
        "level": level,
        "function": "portfolio_generator",
        "message": message,
    }
    entry.update(kwargs)
    print(json.dumps(entry))


def _log_info(message: str, **kwargs) -> None:
    _log("INFO", message, **kwargs)


def _log_error(message: str, **kwargs) -> None:
    _log("ERROR", message, **kwargs)


def _safe_url(url: str) -> str:
    """
    Return the URL only if it uses http or https.
    Returns '' for javascript:, data:, vbscript:, or anything else.
    Prevents XSS via href injection.
    """
    if url and _ALLOWED_URL_RE.match(url.strip()):
        return url.strip()
    return ''


def lambda_handler(event, context):
    """Generate static portfolio website."""
    correlation_id = context.aws_request_id if context else 'local'
    user_id = None
    try:
        # Can be triggered by direct Lambda invocation or DynamoDB Stream
        user_id = event.get('userId')
        upload_id = event.get('uploadId')

        if not user_id:
            if 'Records' in event:
                record = event['Records'][0]
                if record.get('eventName') in ['INSERT', 'MODIFY']:
                    keys = record['dynamodb']['Keys']
                    user_id = keys['PK']['S'].replace('USER#', '')
            else:
                return {'statusCode': 400, 'body': 'Missing userId'}

        _log_info(
            "Portfolio generation started",
            correlationId=correlation_id,
            userId=user_id,
            uploadId=upload_id,
        )

        # Get portfolio data from DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.get_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PORTFOLIO#current',
            }
        )

        if 'Item' not in response:
            _log_error(
                "Portfolio data not found",
                correlationId=correlation_id,
                userId=user_id,
            )
            return {'statusCode': 404, 'body': 'Portfolio data not found'}

        item = response['Item']
        parsed_data = item.get('parsedData', {})
        portfolio_content = item.get('portfolioContent', {})

        # Generate HTML — all values HTML-escaped inside _generate_html
        portfolio_html = _generate_html(parsed_data, portfolio_content)
        css = _generate_css()

        # Upload to S3
        version = item.get('version', 1)
        base_path = f"{user_id}/v{version}"

        s3_client.put_object(
            Bucket=PORTFOLIO_BUCKET,
            Key=f"{base_path}/index.html",
            Body=portfolio_html.encode('utf-8'),
            ContentType='text/html',
            CacheControl='max-age=3600',
        )

        s3_client.put_object(
            Bucket=PORTFOLIO_BUCKET,
            Key=f"{base_path}/styles.css",
            Body=css.encode('utf-8'),
            ContentType='text/css',
            CacheControl='max-age=86400',
        )

        # Update portfolio status in DynamoDB
        now = datetime.now(timezone.utc).isoformat()
        table.update_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PORTFOLIO#current',
            },
            UpdateExpression=(
                'SET #status = :status, portfolioPath = :path, '
                'updatedAt = :updatedAt'
            ),
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'PUBLISHED',
                ':path': base_path,
                ':updatedAt': now,
            },
        )

        if upload_id:
            table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'UPLOAD#{upload_id}',
                },
                UpdateExpression=(
                    'SET #status = :status, portfolioPath = :path, '
                    'updatedAt = :updatedAt'
                ),
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'COMPLETE',
                    ':path': base_path,
                    ':updatedAt': now,
                },
            )

        _log_info(
            "Portfolio published",
            correlationId=correlation_id,
            userId=user_id,
            uploadId=upload_id,
            portfolioPath=base_path,
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'path': base_path, 'status': 'PUBLISHED'}),
        }

    except Exception as e:
        _log_error(
            "Portfolio generation error",
            correlationId=correlation_id,
            userId=user_id,
            error=str(e),
        )
        raise


def _generate_html(parsed_data: dict, portfolio_content: dict) -> str:
    """
    Generate portfolio HTML.

    EVERY value from parsed_data / portfolio_content is passed through
    html.escape() before interpolation — prevents stored XSS regardless
    of what OpenAI returns or what was in the resume text.
    """
    # --- Escape all scalar strings ---
    name = html.escape(str(parsed_data.get('name') or 'Portfolio'))
    title = html.escape(str(parsed_data.get('title') or ''))
    headline = html.escape(
        str(portfolio_content.get('headline') or title)
    )
    bio = html.escape(
        str(portfolio_content.get('bio')
            or parsed_data.get('summary') or '')
    )
    email = html.escape(str(parsed_data.get('email') or ''))
    location = html.escape(str(parsed_data.get('location') or ''))
    skills = [
        html.escape(str(s))
        for s in (parsed_data.get('skills') or [])
    ]
    experience = parsed_data.get('experience') or []
    education = parsed_data.get('education') or []
    links = parsed_data.get('links') or {}

    # --- Experience section ---
    experience_html = ""
    for exp in experience[:5]:
        exp_title = html.escape(str(exp.get('title') or ''))
        company = html.escape(str(exp.get('company') or ''))
        duration = html.escape(str(exp.get('duration') or ''))
        description = html.escape(str(exp.get('description') or ''))
        highlights_html = "".join(
            f"<li>{html.escape(str(h))}</li>"
            for h in (exp.get('highlights') or [])[:3]
        )
        experience_html += (
            f'<div class="experience-item">'
            f'<h3>{exp_title} at {company}</h3>'
            f'<p class="duration">{duration}</p>'
            f'<p>{description}</p>'
            f'<ul>{highlights_html}</ul>'
            f'</div>'
        )

    # --- Education section ---
    education_html = ""
    for edu in education[:3]:
        degree = html.escape(str(edu.get('degree') or ''))
        field = html.escape(str(edu.get('field') or ''))
        institution = html.escape(str(edu.get('institution') or ''))
        year = html.escape(str(edu.get('year') or ''))
        education_html += (
            f'<div class="education-item">'
            f'<h3>{degree} in {field}</h3>'
            f'<p>{institution} - {year}</p>'
            f'</div>'
        )

    # --- Skills ---
    skills_html = "".join(
        f'<span class="skill-tag">{skill}</span>'
        for skill in skills[:15]
    )

    # --- Links: validate scheme BEFORE escaping into href ---
    # _safe_url() rejects javascript:, data:, vbscript:, etc.
    links_html = ""
    linkedin_url = _safe_url(str(links.get('linkedin') or ''))
    github_url = _safe_url(str(links.get('github') or ''))

    if linkedin_url:
        links_html += (
            f'<a href="{html.escape(linkedin_url)}" '
            f'target="_blank" rel="noopener noreferrer">LinkedIn</a>'
        )
    if github_url:
        links_html += (
            f'<a href="{html.escape(github_url)}" '
            f'target="_blank" rel="noopener noreferrer">GitHub</a>'
        )

    email_link = ""
    if email:
        email_link = f'<a href="mailto:{email}">Contact</a>'

    # Content-Security-Policy: script-src 'none' ensures no inline or
    # external scripts can run even if XSS were somehow injected.
    csp = (
        "default-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "script-src 'none'; "
        "object-src 'none';"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="{csp}">
    <title>{name} - Portfolio</title>
    <link rel="stylesheet" href="styles.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <header class="hero">
        <div class="container">
            <h1>{name}</h1>
            <p class="headline">{headline}</p>
            <p class="location">{location}</p>
            <div class="links">
                {links_html}
                {email_link}
            </div>
        </div>
    </header>

    <main class="container">
        <section class="about">
            <h2>About</h2>
            <p>{bio}</p>
        </section>

        <section class="skills">
            <h2>Skills</h2>
            <div class="skills-container">
                {skills_html}
            </div>
        </section>

        <section class="experience">
            <h2>Experience</h2>
            {experience_html}
        </section>

        <section class="education">
            <h2>Education</h2>
            {education_html}
        </section>
    </main>

    <footer>
        <div class="container">
            <p>Generated with AI Portfolio Builder</p>
        </div>
    </footer>
</body>
</html>"""


def _generate_css() -> str:
    """Generate portfolio CSS."""
    return """
:root {
    --primary: #2563eb;
    --primary-dark: #1d4ed8;
    --text: #1f2937;
    --text-light: #6b7280;
    --bg: #ffffff;
    --bg-alt: #f9fafb;
    --border: #e5e7eb;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.6;
    color: var(--text);
    background: var(--bg);
}

.container { max-width: 800px; margin: 0 auto; padding: 0 1.5rem; }

.hero {
    background: linear-gradient(
        135deg, var(--primary) 0%, var(--primary-dark) 100%
    );
    color: white;
    padding: 4rem 0;
    text-align: center;
}

.hero h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem; }
.headline { font-size: 1.25rem; opacity: 0.9; margin-bottom: 0.5rem; }
.location { opacity: 0.8; margin-bottom: 1.5rem; }

.links {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex-wrap: wrap;
}

.links a {
    color: white;
    text-decoration: none;
    padding: 0.5rem 1rem;
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 6px;
    transition: all 0.2s;
}

.links a:hover {
    background: rgba(255,255,255,0.1);
    border-color: rgba(255,255,255,0.5);
}

main { padding: 3rem 0; }
section { margin-bottom: 3rem; }

h2 {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 1.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--primary);
}

.about p { font-size: 1.1rem; color: var(--text-light); }
.skills-container { display: flex; flex-wrap: wrap; gap: 0.5rem; }

.skill-tag {
    background: var(--bg-alt);
    color: var(--text);
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.9rem;
    border: 1px solid var(--border);
}

.experience-item, .education-item {
    margin-bottom: 2rem;
    padding-bottom: 2rem;
    border-bottom: 1px solid var(--border);
}

.experience-item:last-child, .education-item:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}

.experience-item h3, .education-item h3 {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
}

.duration { color: var(--text-light); font-size: 0.9rem; margin-bottom: 0.5rem; }
.experience-item ul { margin-top: 0.5rem; padding-left: 1.5rem; }
.experience-item li { margin-bottom: 0.25rem; color: var(--text-light); }

footer {
    background: var(--bg-alt);
    padding: 2rem 0;
    text-align: center;
    color: var(--text-light);
    font-size: 0.9rem;
    border-top: 1px solid var(--border);
}

@media (max-width: 640px) {
    .hero h1 { font-size: 2rem; }
    .headline { font-size: 1.1rem; }
    h2 { font-size: 1.25rem; }
}
"""
