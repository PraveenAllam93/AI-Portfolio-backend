"""
Template: Minimal
Ultra-clean monochrome design. White hero with a bold black bottom border.
No gradients. Refined typography. Subtle underline animations on headings.
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
            <h1>{v['name']}</h1>
            <p class="headline">{v['headline']}</p>
            <div class="meta">
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
            <h2><span>About</span></h2>
            <p>{v['bio']}</p>
        </section>

        <section class="skills">
            <h2><span>Skills</span></h2>
            <div class="skills-container">
                {skills_html}
            </div>
        </section>

        <section class="experience">
            <h2><span>Experience</span></h2>
            {experience_html}
        </section>

        <section class="education">
            <h2><span>Education</span></h2>
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
    --ink: #111827;
    --ink-mid: #374151;
    --ink-light: #6b7280;
    --bg: #ffffff;
    --bg-alt: #f9fafb;
    --border: #e5e7eb;
    --border-dark: #d1d5db;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.65;
    color: var(--ink);
    background: var(--bg);
}

.container { max-width: 820px; margin: 0 auto; padding: 0 1.5rem; }

/* Hero — white, strong border bottom */
.hero {
    background: var(--bg);
    padding: 4rem 0 3rem;
    border-bottom: 2.5px solid var(--ink);
}
.hero h1 {
    font-size: 2.75rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--ink);
    margin-bottom: 0.4rem;
}
.headline {
    font-size: 1.1rem;
    color: var(--ink-mid);
    font-weight: 400;
    margin-bottom: 1.25rem;
}
.meta {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    flex-wrap: wrap;
}
.location {
    font-size: 0.9rem;
    color: var(--ink-light);
}

.links { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.links a {
    color: var(--ink);
    text-decoration: none;
    font-size: 0.875rem;
    font-weight: 500;
    padding-bottom: 1px;
    border-bottom: 1.5px solid var(--border-dark);
    transition: border-color 0.2s;
}
.links a:hover { border-bottom-color: var(--ink); }

/* Content */
main { padding: 3.5rem 0; }
section { margin-bottom: 3.5rem; }

/* H2 with animated underline */
h2 {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-light);
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
h2::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

.about p {
    font-size: 1.05rem;
    color: var(--ink-mid);
    line-height: 1.8;
    max-width: 680px;
}

/* Skills — minimal chips */
.skills-container { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.skill-tag {
    background: transparent;
    color: var(--ink-mid);
    padding: 0.3rem 0.75rem;
    border-radius: 4px;
    font-size: 0.85rem;
    border: 1px solid var(--border-dark);
    transition: background 0.15s, color 0.15s;
}
.skill-tag:hover {
    background: var(--ink);
    color: white;
    border-color: var(--ink);
}

/* Experience / Education */
.experience-item, .education-item {
    margin-bottom: 2.25rem;
    padding-bottom: 2.25rem;
    border-bottom: 1px solid var(--border);
}
.experience-item:last-child, .education-item:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}
.experience-item h3, .education-item h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--ink);
    margin-bottom: 0.2rem;
}
.duration {
    font-size: 0.8rem;
    color: var(--ink-light);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.6rem;
}
.experience-item p { color: var(--ink-mid); font-size: 0.95rem; }
.experience-item ul { margin-top: 0.6rem; padding-left: 1.1rem; }
.experience-item li {
    color: var(--ink-light);
    font-size: 0.9rem;
    margin-bottom: 0.2rem;
}

footer {
    border-top: 1px solid var(--border);
    padding: 2rem 0;
    text-align: center;
    color: var(--ink-light);
    font-size: 0.8rem;
}

@media (max-width: 640px) {
    .hero h1 { font-size: 2rem; }
    .meta { flex-direction: column; align-items: flex-start; gap: 0.75rem; }
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
