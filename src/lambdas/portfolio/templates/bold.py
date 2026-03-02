"""
Template: Bold
Dark slate background, vibrant orange accents. High-impact design.
Heavy transitions: glowing skill tags, sliding left-border on experience,
animated hero heading. Large typography throughout.
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
            <div class="hero-badge">Portfolio</div>
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
            <h2><span class="h2-accent">//</span> About</h2>
            <p>{v['bio']}</p>
        </section>

        <section class="skills">
            <h2><span class="h2-accent">//</span> Skills</h2>
            <div class="skills-container">
                {skills_html}
            </div>
        </section>

        <section class="experience">
            <h2><span class="h2-accent">//</span> Experience</h2>
            {experience_html}
        </section>

        <section class="education">
            <h2><span class="h2-accent">//</span> Education</h2>
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
    --accent: #f97316;
    --accent-glow: rgba(249, 115, 22, 0.35);
    --bg: #0f172a;
    --bg-card: #1e293b;
    --bg-card-hover: #263348;
    --text: #f1f5f9;
    --text-muted: #94a3b8;
    --border: #334155;
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
    background: linear-gradient(160deg, #0f172a 0%, #1e293b 100%);
    padding: 5rem 0 4rem;
    border-bottom: 2px solid var(--accent);
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -80px; right: -80px;
    width: 360px; height: 360px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(249,115,22,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.hero-badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--accent);
    border: 1px solid var(--accent);
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    margin-bottom: 1.25rem;
}
.hero h1 {
    font-size: 3.25rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--text);
    margin-bottom: 0.6rem;
    line-height: 1.1;
}
.headline {
    font-size: 1.2rem;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
}
.location {
    font-size: 0.9rem;
    color: var(--text-muted);
    margin-bottom: 2rem;
}

.links { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.links a {
    color: var(--text);
    text-decoration: none;
    font-size: 0.875rem;
    font-weight: 500;
    padding: 0.5rem 1.1rem;
    border: 1px solid var(--border);
    border-radius: 6px;
    transition: all 0.25s;
}
.links a:hover {
    border-color: var(--accent);
    color: var(--accent);
    box-shadow: 0 0 16px var(--accent-glow);
    transform: translateY(-1px);
}

/* Content */
main { padding: 4rem 0; }
section { margin-bottom: 4rem; }

h2 {
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 1.75rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
h2::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}
.h2-accent {
    color: var(--accent);
    font-weight: 700;
    font-size: 1rem;
}

.about p {
    font-size: 1.05rem;
    color: var(--text-muted);
    line-height: 1.8;
}

/* Skills — bordered tags with glow on hover */
.skills-container { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.skill-tag {
    background: transparent;
    color: var(--accent);
    padding: 0.35rem 0.85rem;
    border-radius: 4px;
    font-size: 0.85rem;
    font-weight: 500;
    border: 1px solid var(--accent);
    cursor: default;
    transition: all 0.2s;
}
.skill-tag:hover {
    background: var(--accent);
    color: var(--bg);
    box-shadow: 0 0 14px var(--accent-glow);
}

/* Experience — card with sliding left-border on hover */
.experience-item, .education-item {
    background: var(--bg-card);
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1.25rem;
    border-left: 3px solid var(--border);
    transition: border-left-color 0.3s, background 0.3s, transform 0.2s;
}
.experience-item:hover, .education-item:hover {
    border-left-color: var(--accent);
    background: var(--bg-card-hover);
    transform: translateX(3px);
}
.experience-item h3, .education-item h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 0.3rem;
}
.duration {
    font-size: 0.8rem;
    color: var(--accent);
    font-weight: 500;
    margin-bottom: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.experience-item > p { color: var(--text-muted); font-size: 0.95rem; }
.experience-item ul { margin-top: 0.6rem; padding-left: 1.1rem; }
.experience-item li {
    color: var(--text-muted);
    font-size: 0.9rem;
    margin-bottom: 0.25rem;
}

footer {
    border-top: 1px solid var(--border);
    padding: 2.5rem 0;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.85rem;
}

@media (max-width: 640px) {
    .hero h1 { font-size: 2.25rem; }
    .headline { font-size: 1rem; }
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
            f'<h3>{exp["title"]} — {exp["company"]}</h3>'
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
