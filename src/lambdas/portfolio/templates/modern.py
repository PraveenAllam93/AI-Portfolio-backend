"""
Template: Modern
Clean blue gradient header, Inter typography, single-column layout.
Smooth hover transitions on links and section cards.
"""

from .base import CSP, FONTS_URL


def html(v: dict) -> str:
    """Generate Modern template HTML. v is pre-escaped dict from _extract_vars."""
    links_html = _links(v)
    email_link = _email_link(v['email'])
    skills_html = _skills(v['skills'])
    experience_html = _experience(v['experience'])
    education_html = _education(v['education'])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="{CSP}">
    <title>{v['name']} - Portfolio</title>
    <link rel="stylesheet" href="styles.css">
    <link href="{FONTS_URL}" rel="stylesheet">
</head>
<body>
    <header class="hero">
        <div class="container">
            <h1>{v['name']}</h1>
            <p class="headline">{v['headline']}</p>
            <p class="location">{v['location']}</p>
            <div class="links">
                {links_html}
                {email_link}
            </div>
        </div>
    </header>

    <main class="container">
        <section class="about">
            <h2>About</h2>
            <p>{v['bio']}</p>
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


def css() -> str:
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

.container { max-width: 820px; margin: 0 auto; padding: 0 1.5rem; }

/* Hero */
.hero {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
    padding: 4.5rem 0;
    text-align: center;
}
.hero h1 {
    font-size: 2.75rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: 0.5rem;
}
.headline { font-size: 1.2rem; opacity: 0.9; margin-bottom: 0.4rem; }
.location { opacity: 0.75; margin-bottom: 1.75rem; font-size: 0.95rem; }

.links {
    display: flex;
    gap: 0.75rem;
    justify-content: center;
    flex-wrap: wrap;
}
.links a {
    color: white;
    text-decoration: none;
    padding: 0.45rem 1.1rem;
    border: 1px solid rgba(255,255,255,0.35);
    border-radius: 6px;
    font-size: 0.9rem;
    transition: background 0.2s, border-color 0.2s, transform 0.2s;
}
.links a:hover {
    background: rgba(255,255,255,0.15);
    border-color: rgba(255,255,255,0.6);
    transform: translateY(-1px);
}

/* Content */
main { padding: 3.5rem 0; }
section { margin-bottom: 3.5rem; }

h2 {
    font-size: 1.4rem;
    font-weight: 600;
    margin-bottom: 1.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--primary);
    color: var(--text);
}

.about p { font-size: 1.05rem; color: var(--text-light); line-height: 1.75; }

/* Skills */
.skills-container { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.skill-tag {
    background: var(--bg-alt);
    color: var(--text);
    padding: 0.4rem 0.9rem;
    border-radius: 20px;
    font-size: 0.875rem;
    border: 1px solid var(--border);
    transition: border-color 0.2s, background 0.2s;
}
.skill-tag:hover {
    border-color: var(--primary);
    background: #eff6ff;
}

/* Experience / Education */
.experience-item, .education-item {
    margin-bottom: 2rem;
    padding: 1.5rem;
    background: var(--bg-alt);
    border-radius: 8px;
    border-left: 3px solid var(--primary);
    transition: box-shadow 0.2s, transform 0.2s;
}
.experience-item:hover, .education-item:hover {
    box-shadow: 0 4px 16px rgba(37,99,235,0.1);
    transform: translateX(2px);
}
.experience-item h3, .education-item h3 {
    font-size: 1.05rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
}
.duration {
    color: var(--text-light);
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
}
.experience-item p { color: var(--text-light); font-size: 0.95rem; }
.experience-item ul { margin-top: 0.5rem; padding-left: 1.25rem; }
.experience-item li {
    margin-bottom: 0.25rem;
    color: var(--text-light);
    font-size: 0.9rem;
}

/* Footer */
footer {
    background: var(--bg-alt);
    padding: 2rem 0;
    text-align: center;
    color: var(--text-light);
    font-size: 0.85rem;
    border-top: 1px solid var(--border);
}

@media (max-width: 640px) {
    .hero h1 { font-size: 2rem; }
    .headline { font-size: 1.05rem; }
    h2 { font-size: 1.2rem; }
}
"""


# ---------------------------------------------------------------------------
# Internal HTML helpers — only called from html()
# ---------------------------------------------------------------------------

def _links(v: dict) -> str:
    out = ''
    if v['linkedin_url']:
        out += (
            f'<a href="{v["linkedin_url"]}" '
            'target="_blank" rel="noopener noreferrer">LinkedIn</a>'
        )
    if v['github_url']:
        out += (
            f'<a href="{v["github_url"]}" '
            'target="_blank" rel="noopener noreferrer">GitHub</a>'
        )
    return out


def _email_link(email: str) -> str:
    return f'<a href="mailto:{email}">Contact</a>' if email else ''


def _skills(skills: list) -> str:
    return ''.join(
        f'<span class="skill-tag">{s}</span>'
        for s in skills[:15]
    )


def _experience(items: list) -> str:
    out = ''
    for exp in items:
        highlights = ''.join(
            f'<li>{h}</li>' for h in exp['highlights']
        )
        out += (
            f'<div class="experience-item">'
            f'<h3>{exp["title"]} at {exp["company"]}</h3>'
            f'<p class="duration">{exp["duration"]}</p>'
            f'<p>{exp["description"]}</p>'
            f'<ul>{highlights}</ul>'
            f'</div>'
        )
    return out


def _education(items: list) -> str:
    out = ''
    for edu in items:
        out += (
            f'<div class="education-item">'
            f'<h3>{edu["degree"]} in {edu["field"]}</h3>'
            f'<p>{edu["institution"]} · {edu["year"]}</p>'
            f'</div>'
        )
    return out
