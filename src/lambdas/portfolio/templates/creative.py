"""
Template: Creative
Two-column sidebar layout. Teal sidebar with contact + skills.
White content area with raised card sections. Card lift hover effects.
Mobile: sidebar stacks above content.
"""

from .base import CSP, FONTS_URL


def html(v: dict) -> str:
    sidebar_links = _sidebar_links(v)
    skills_html = _skills(v['skills'])
    experience_html = _experience(v['experience'])
    education_html = _education(v['education'])

    email_row = (
        f'<div class="contact-row">'
        f'<span class="contact-icon">✉</span>'
        f'<a href="mailto:{v["email"]}">{v["email"]}</a>'
        f'</div>'
    ) if v['email'] else ''

    location_row = (
        f'<div class="contact-row">'
        f'<span class="contact-icon">⌖</span>'
        f'<span>{v["location"]}</span>'
        f'</div>'
    ) if v['location'] else ''

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
    <div class="layout">
        <!-- SIDEBAR -->
        <aside class="sidebar">
            <div class="sidebar-profile">
                <div class="avatar">{v['name'][0].upper() if v['name'] else 'P'}</div>
                <h1>{v['name']}</h1>
                <p class="title">{v['headline']}</p>
            </div>

            <div class="sidebar-section">
                <h3 class="sidebar-heading">Contact</h3>
                {location_row}
                {email_row}
                {sidebar_links}
            </div>

            <div class="sidebar-section">
                <h3 class="sidebar-heading">Skills</h3>
                <div class="skills-container">
                    {skills_html}
                </div>
            </div>
        </aside>

        <!-- MAIN CONTENT -->
        <main class="content">
            <section class="about card">
                <h2>About Me</h2>
                <p>{v['bio']}</p>
            </section>

            <section class="experience">
                <h2>Experience</h2>
                {experience_html}
            </section>

            <section class="education">
                <h2>Education</h2>
                {education_html}
            </section>

            <footer>
                <p>Generated with AI Portfolio Builder</p>
            </footer>
        </main>
    </div>
</body>
</html>"""


def css() -> str:
    return """
:root {
    --teal: #0d9488;
    --teal-dark: #0f766e;
    --teal-light: #14b8a6;
    --text: #1f2937;
    --text-light: #6b7280;
    --bg: #f9fafb;
    --bg-card: #ffffff;
    --border: #e5e7eb;
    --sidebar-text: rgba(255,255,255,0.9);
    --sidebar-muted: rgba(255,255,255,0.65);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.6;
    background: var(--bg);
    color: var(--text);
}

/* Two-column layout */
.layout {
    display: flex;
    min-height: 100vh;
}

/* ---- SIDEBAR ---- */
.sidebar {
    width: 280px;
    flex-shrink: 0;
    background: linear-gradient(175deg, var(--teal) 0%, var(--teal-dark) 100%);
    color: white;
    padding: 2.5rem 1.75rem;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
}

.sidebar-profile { margin-bottom: 2rem; }

/* Avatar — first letter of name */
.avatar {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: rgba(255,255,255,0.2);
    border: 2px solid rgba(255,255,255,0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 1rem;
    color: white;
}

.sidebar h1 {
    font-size: 1.35rem;
    font-weight: 700;
    color: white;
    margin-bottom: 0.3rem;
    line-height: 1.2;
}
.title {
    font-size: 0.875rem;
    color: var(--sidebar-muted);
    line-height: 1.4;
}

.sidebar-section { margin-bottom: 1.75rem; }

.sidebar-heading {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--teal-light);
    margin-bottom: 0.75rem;
}

/* Contact rows */
.contact-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    font-size: 0.85rem;
    color: var(--sidebar-text);
}
.contact-icon {
    font-size: 0.8rem;
    opacity: 0.7;
    flex-shrink: 0;
}
.contact-row a {
    color: var(--sidebar-text);
    text-decoration: none;
    transition: color 0.2s;
    word-break: break-all;
}
.contact-row a:hover { color: white; }

/* Sidebar links */
.sidebar-links { display: flex; flex-direction: column; gap: 0.4rem; }
.sidebar-link {
    color: var(--sidebar-text);
    text-decoration: none;
    font-size: 0.85rem;
    font-weight: 500;
    padding: 0.35rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.15);
    display: flex;
    align-items: center;
    gap: 0.4rem;
    transition: color 0.2s, border-color 0.2s;
}
.sidebar-link:hover {
    color: white;
    border-bottom-color: rgba(255,255,255,0.5);
}

/* Skills in sidebar */
.skills-container { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.skill-tag {
    background: rgba(255,255,255,0.15);
    color: white;
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    font-size: 0.78rem;
    font-weight: 500;
    border: 1px solid rgba(255,255,255,0.2);
    transition: background 0.2s;
}
.skill-tag:hover { background: rgba(255,255,255,0.28); }

/* ---- MAIN CONTENT ---- */
.content {
    flex: 1;
    padding: 3rem 2.5rem;
    overflow: auto;
}

section { margin-bottom: 2.5rem; }

h2 {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 1.25rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--teal);
}

/* About card */
.about.card {
    background: var(--bg-card);
    border-radius: 10px;
    padding: 1.75rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    margin-bottom: 2.5rem;
}
.about p {
    font-size: 1rem;
    color: var(--text-light);
    line-height: 1.8;
}

/* Experience / Education cards */
.experience-item, .education-item {
    background: var(--bg-card);
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border-top: 3px solid transparent;
    transition: border-top-color 0.25s, box-shadow 0.25s, transform 0.2s;
}
.experience-item:hover, .education-item:hover {
    border-top-color: var(--teal);
    box-shadow: 0 6px 20px rgba(13,148,136,0.12);
    transform: translateY(-2px);
}
.experience-item h3, .education-item h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 0.2rem;
}
.duration {
    font-size: 0.8rem;
    color: var(--teal);
    font-weight: 500;
    margin-bottom: 0.5rem;
}
.experience-item > p { color: var(--text-light); font-size: 0.92rem; }
.experience-item ul { margin-top: 0.5rem; padding-left: 1.1rem; }
.experience-item li {
    color: var(--text-light);
    font-size: 0.88rem;
    margin-bottom: 0.2rem;
}

footer {
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
    text-align: center;
    color: var(--text-light);
    font-size: 0.8rem;
}

/* Mobile: sidebar stacks above content */
@media (max-width: 768px) {
    .layout { flex-direction: column; }
    .sidebar {
        width: 100%;
        height: auto;
        position: static;
    }
    .content { padding: 2rem 1.25rem; }
}
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sidebar_links(v: dict) -> str:
    out = '<div class="sidebar-links">'
    if v['linkedin_url']:
        out += (
            f'<a href="{v["linkedin_url"]}" class="sidebar-link" '
            'target="_blank" rel="noopener noreferrer">↗ LinkedIn</a>'
        )
    if v['github_url']:
        out += (
            f'<a href="{v["github_url"]}" class="sidebar-link" '
            'target="_blank" rel="noopener noreferrer">↗ GitHub</a>'
        )
    out += '</div>'
    return out


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
            f'<p class="duration">{edu["institution"]} · {edu["year"]}</p>'
            f'</div>'
        )
    return out
