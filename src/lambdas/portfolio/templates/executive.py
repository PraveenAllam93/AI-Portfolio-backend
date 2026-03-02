"""
Template: Executive (Premium)
Dark green gradient hero. Gold H2 headings with sliding underline animation.
Timeline-style experience section. Warm off-white body. Formal, refined.
"""

from .base import CSP, FONTS_URL


def html(v: dict) -> str:
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
            <p class="hero-label">Professional Portfolio</p>
            <h1>{v['name']}</h1>
            <p class="headline">{v['headline']}</p>
            <div class="hero-meta">
                <span class="location">{v['location']}</span>
                <div class="links">
                    {links_html}
                    {email_link}
                </div>
            </div>
        </div>
    </header>

    <main class="container">
        <section class="about">
            <h2>About</h2>
            <p>{v['bio']}</p>
        </section>

        <section class="skills">
            <h2>Core Competencies</h2>
            <div class="skills-container">
                {skills_html}
            </div>
        </section>

        <section class="experience">
            <h2>Professional Experience</h2>
            <div class="timeline">
                {experience_html}
            </div>
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
    --green: #166534;
    --green-dark: #14532d;
    --gold: #b45309;
    --gold-light: #d97706;
    --text: #1c1917;
    --text-light: #57534e;
    --bg: #fafaf9;
    --bg-alt: #f5f5f4;
    --border: #d6d3d1;
    --border-light: #e7e5e4;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.65;
    color: var(--text);
    background: var(--bg);
}

.container { max-width: 820px; margin: 0 auto; padding: 0 1.75rem; }

/* Hero */
.hero {
    background: linear-gradient(140deg, var(--green-dark) 0%, var(--green) 100%);
    color: white;
    padding: 5rem 0 4rem;
}
.hero-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.55);
    margin-bottom: 1rem;
}
.hero h1 {
    font-size: 2.75rem;
    font-weight: 700;
    letter-spacing: -0.025em;
    margin-bottom: 0.5rem;
    line-height: 1.15;
}
.headline {
    font-size: 1.1rem;
    color: rgba(255,255,255,0.8);
    margin-bottom: 2rem;
    font-weight: 300;
    letter-spacing: 0.01em;
}
.hero-meta {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    flex-wrap: wrap;
}
.location {
    font-size: 0.875rem;
    color: rgba(255,255,255,0.65);
}

.links { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.links a {
    color: white;
    text-decoration: none;
    font-size: 0.85rem;
    font-weight: 500;
    padding: 0.4rem 1rem;
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 4px;
    letter-spacing: 0.02em;
    transition: all 0.25s;
}
.links a:hover {
    background: rgba(255,255,255,0.12);
    border-color: rgba(255,255,255,0.6);
    transform: translateY(-1px);
}

/* Content */
main { padding: 4rem 0; }
section { margin-bottom: 4rem; }

/* H2 with gold sliding underline */
h2 {
    font-size: 1.3rem;
    font-weight: 600;
    color: var(--gold);
    margin-bottom: 1.75rem;
    position: relative;
    padding-bottom: 0.6rem;
    display: inline-block;
}
h2::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 0;
    height: 2px;
    background: var(--gold);
    transition: width 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
section:hover h2::after { width: 100%; }

/* Section divider under h2 */
section > h2 + * { margin-top: 0.5rem; }

.about p {
    font-size: 1.05rem;
    color: var(--text-light);
    line-height: 1.85;
    max-width: 700px;
}

/* Skills — formal chips */
.skills-container { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.skill-tag {
    background: var(--bg-alt);
    color: var(--text-light);
    padding: 0.35rem 0.85rem;
    border-radius: 4px;
    font-size: 0.85rem;
    border: 1px solid var(--border);
    transition: all 0.2s;
}
.skill-tag:hover {
    border-color: var(--gold);
    color: var(--gold);
    background: #fef3c7;
}

/* Timeline */
.timeline { position: relative; padding-left: 1.5rem; }
.timeline::before {
    content: '';
    position: absolute;
    left: 0;
    top: 6px;
    bottom: 0;
    width: 2px;
    background: var(--border-light);
}

.experience-item {
    position: relative;
    padding-left: 1.5rem;
    margin-bottom: 2.5rem;
    transition: padding-left 0.2s;
}
.experience-item::before {
    content: '';
    position: absolute;
    left: -1.5rem;
    top: 6px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--border);
    border: 2px solid var(--bg);
    transition: background 0.2s, box-shadow 0.2s;
}
.experience-item:hover::before {
    background: var(--gold);
    box-shadow: 0 0 0 3px rgba(180,83,9,0.15);
}

.experience-item h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 0.25rem;
}
.duration {
    font-size: 0.8rem;
    color: var(--gold);
    font-weight: 500;
    margin-bottom: 0.6rem;
    letter-spacing: 0.04em;
}
.experience-item > p { color: var(--text-light); font-size: 0.93rem; }
.experience-item ul { margin-top: 0.5rem; padding-left: 1.1rem; }
.experience-item li {
    color: var(--text-light);
    font-size: 0.88rem;
    margin-bottom: 0.2rem;
}

.education-item {
    background: var(--bg-alt);
    border-radius: 6px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    border-left: 3px solid var(--gold);
    transition: box-shadow 0.2s;
}
.education-item:hover {
    box-shadow: 0 4px 12px rgba(180,83,9,0.08);
}
.education-item h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 0.2rem;
}

footer {
    background: var(--bg-alt);
    border-top: 1px solid var(--border);
    padding: 2rem 0;
    text-align: center;
    color: var(--text-light);
    font-size: 0.8rem;
}

@media (max-width: 640px) {
    .hero h1 { font-size: 2rem; }
    .hero-meta { flex-direction: column; align-items: flex-start; gap: 0.75rem; }
    .timeline { padding-left: 1rem; }
}
"""


# ---------------------------------------------------------------------------
# Internal helpers
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
        for s in skills[:20]
    )


def _experience(items: list) -> str:
    out = ''
    for exp in items:
        highlights = ''.join(
            f'<li>{h}</li>' for h in exp['highlights']
        )
        out += (
            f'<div class="experience-item">'
            f'<h3>{exp["title"]} · {exp["company"]}</h3>'
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
            f'<p class="duration">{edu["institution"]} · {edu["year"]}</p>'
            f'</div>'
        )
    return out
