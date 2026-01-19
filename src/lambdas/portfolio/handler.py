"""
Lambda: Portfolio Generator
Generates static HTML/CSS portfolio website from parsed resume data.
Outputs to S3 portfolio bucket for CloudFront delivery.
"""

import json
import os
import boto3
from datetime import datetime

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')


def lambda_handler(event, context):
    """Generate static portfolio website."""
    try:
        # This can be triggered by DynamoDB Stream or directly invoked
        user_id = event.get('userId')
        upload_id = event.get('uploadId')

        if not user_id:
            # Try to get from DynamoDB stream record
            if 'Records' in event:
                record = event['Records'][0]
                if record.get('eventName') in ['INSERT', 'MODIFY']:
                    keys = record['dynamodb']['Keys']
                    user_id = keys['PK']['S'].replace('USER#', '')
            else:
                return {'statusCode': 400, 'body': 'Missing userId'}

        print(f"Generating portfolio for user: {user_id}")

        # Get portfolio data from DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.get_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PORTFOLIO#current'
            }
        )

        if 'Item' not in response:
            return {'statusCode': 404, 'body': 'Portfolio data not found'}

        item = response['Item']
        parsed_data = item.get('parsedData', {})
        portfolio_content = item.get('portfolioContent', {})

        # Generate HTML
        html = _generate_html(parsed_data, portfolio_content, user_id)

        # Generate CSS
        css = _generate_css()

        # Upload to S3
        version = item.get('version', 1)
        base_path = f"{user_id}/v{version}"

        # Upload index.html
        s3_client.put_object(
            Bucket=PORTFOLIO_BUCKET,
            Key=f"{base_path}/index.html",
            Body=html.encode('utf-8'),
            ContentType='text/html',
            CacheControl='max-age=3600'
        )

        # Upload styles.css
        s3_client.put_object(
            Bucket=PORTFOLIO_BUCKET,
            Key=f"{base_path}/styles.css",
            Body=css.encode('utf-8'),
            ContentType='text/css',
            CacheControl='max-age=86400'
        )

        # Update portfolio status
        table.update_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PORTFOLIO#current'
            },
            UpdateExpression='SET #status = :status, portfolioPath = :path, updatedAt = :updatedAt',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'PUBLISHED',
                ':path': base_path,
                ':updatedAt': datetime.utcnow().isoformat()
            }
        )

        # Update upload status if we have upload_id
        if upload_id:
            table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'UPLOAD#{upload_id}'
                },
                UpdateExpression='SET #status = :status, portfolioPath = :path, updatedAt = :updatedAt',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'COMPLETE',
                    ':path': base_path,
                    ':updatedAt': datetime.utcnow().isoformat()
                }
            )

        print(f"Portfolio generated: {base_path}")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'path': base_path,
                'status': 'PUBLISHED'
            })
        }

    except Exception as e:
        print(f"Portfolio generation error: {str(e)}")
        raise


def _generate_html(parsed_data: dict, portfolio_content: dict, user_id: str) -> str:
    """Generate portfolio HTML."""
    name = parsed_data.get('name', 'Portfolio')
    title = parsed_data.get('title', '')
    headline = portfolio_content.get('headline', title)
    bio = portfolio_content.get('bio', parsed_data.get('summary', ''))
    email = parsed_data.get('email', '')
    location = parsed_data.get('location', '')
    skills = parsed_data.get('skills', [])
    experience = parsed_data.get('experience', [])
    education = parsed_data.get('education', [])
    links = parsed_data.get('links', {})

    # Build experience HTML
    experience_html = ""
    for exp in experience[:5]:  # Limit to 5 entries
        highlights = "".join([f"<li>{h}</li>" for h in exp.get('highlights', [])[:3]])
        experience_html += f"""
        <div class="experience-item">
            <h3>{exp.get('title', '')} at {exp.get('company', '')}</h3>
            <p class="duration">{exp.get('duration', '')}</p>
            <p>{exp.get('description', '')}</p>
            <ul>{highlights}</ul>
        </div>
        """

    # Build education HTML
    education_html = ""
    for edu in education[:3]:
        education_html += f"""
        <div class="education-item">
            <h3>{edu.get('degree', '')} in {edu.get('field', '')}</h3>
            <p>{edu.get('institution', '')} - {edu.get('year', '')}</p>
        </div>
        """

    # Build skills HTML
    skills_html = "".join([f'<span class="skill-tag">{skill}</span>' for skill in skills[:15]])

    # Build links HTML
    links_html = ""
    if links.get('linkedin'):
        links_html += f'<a href="{links["linkedin"]}" target="_blank">LinkedIn</a>'
    if links.get('github'):
        links_html += f'<a href="{links["github"]}" target="_blank">GitHub</a>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
                {f'<a href="mailto:{email}">Contact</a>' if email else ''}
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

    return html


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

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.6;
    color: var(--text);
    background: var(--bg);
}

.container {
    max-width: 800px;
    margin: 0 auto;
    padding: 0 1.5rem;
}

.hero {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
    padding: 4rem 0;
    text-align: center;
}

.hero h1 {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}

.headline {
    font-size: 1.25rem;
    opacity: 0.9;
    margin-bottom: 0.5rem;
}

.location {
    opacity: 0.8;
    margin-bottom: 1.5rem;
}

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

main {
    padding: 3rem 0;
}

section {
    margin-bottom: 3rem;
}

h2 {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 1.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--primary);
}

.about p {
    font-size: 1.1rem;
    color: var(--text-light);
}

.skills-container {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

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

.duration {
    color: var(--text-light);
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
}

.experience-item ul {
    margin-top: 0.5rem;
    padding-left: 1.5rem;
}

.experience-item li {
    margin-bottom: 0.25rem;
    color: var(--text-light);
}

footer {
    background: var(--bg-alt);
    padding: 2rem 0;
    text-align: center;
    color: var(--text-light);
    font-size: 0.9rem;
    border-top: 1px solid var(--border);
}

@media (max-width: 640px) {
    .hero h1 {
        font-size: 2rem;
    }

    .headline {
        font-size: 1.1rem;
    }

    h2 {
        font-size: 1.25rem;
    }
}
"""
