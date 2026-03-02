"""
Template: Luxury
Ultra-premium editorial aesthetic. Deep midnight navy canvas with gold
(#c9a84c) accents throughout.

Typography: Cormorant Garamond (headings — luxury serif), Raleway (body).
Layout: Centered hero with personal intro greeting ("Hello, I am"),
        Timeline experience, generous whitespace, editorial feel.
Effects:
  - Gold shimmer/shine sweep animation on hero name
  - "Hello, I am" in italic Cormorant Garamond above the name
  - Subtle CSS dot-pattern on the dark background
  - Gold horizontal rule decorators
  - Timeline experience: gold dots + vertical connecting line
  - Heading underline slide-in animation (gold bar grows left→right)
  - Skill tags: thin gold-bordered pill with refined hover
  - Elegant fade-in-up on all sections
No JavaScript — 100% CSS animations.
"""

from .base import CSP

_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600"
    "&family=Raleway:wght@300;400;500&display=swap"
)


def html(v: dict) -> str:
    links_html = _links(v)
    email_link = _email_link(v['email'])
    skills_html = _skills(v['skills'])
    experience_html = _experience(v['experience'])
    education_html = _education(v['education'])
    location_html = (
        f'<p class="hero-location">{v["location"]}</p>'
        if v['location'] else ''
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="{CSP}">
    <title>{v['name']} - Portfolio</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="{_FONTS}" rel="stylesheet">
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="dot-grid" aria-hidden="true"></div>

    <header class="hero">
        <div class="container">
            <div class="hero-inner">
                <p class="hero-greeting">Hello, I am</p>
                <h1 class="hero-name">{v['name']}</h1>
                <p class="hero-headline">{v['headline']}</p>
                <div class="hero-rule" aria-hidden="true"></div>
                {location_html}
                <div class="hero-links">
                    {links_html}
                    {email_link}
                </div>
            </div>
        </div>
    </header>

    <main class="container">
        <section class="section s1">
            <h2><span class="h2-inner">About</span></h2>
            <p class="bio">{v['bio']}</p>
        </section>

        <section class="section s2">
            <h2><span class="h2-inner">Expertise</span></h2>
            <div class="skills-grid">{skills_html}</div>
        </section>

        <section class="section s3">
            <h2><span class="h2-inner">Experience</span></h2>
            <div class="timeline">{experience_html}</div>
        </section>

        <section class="section s4">
            <h2><span class="h2-inner">Education</span></h2>
            <div class="edu-grid">{education_html}</div>
        </section>
    </main>

    <footer>
        <div class="container">
            <div class="footer-rule" aria-hidden="true"></div>
            <p class="footer-sig">{v['name']}</p>
            <p class="footer-text">Built with AI Portfolio Builder</p>
        </div>
    </footer>
</body>
</html>"""


def css() -> str:
    return """
/* ── Luxury Template ─────────────────────────────────────────── */
/* Premium editorial: Cormorant Garamond serif + Raleway body    */
/* Gold accents on deep midnight navy                             */

:root {
    --gold:       #c9a84c;
    --gold-lt:    #f0d080;
    --gold-dk:    #8b6914;
    --gold-dim:   rgba(201,168,76,0.12);
    --gold-glow:  rgba(201,168,76,0.35);
    --bg:         #060c18;
    --bg-card:    rgba(255,255,255,0.03);
    --bg-card-h:  rgba(201,168,76,0.05);
    --border:     rgba(201,168,76,0.18);
    --border-h:   rgba(201,168,76,0.45);
    --text:       #f0e8d8;
    --muted:      rgba(220,210,190,0.6);
    --dot:        rgba(201,168,76,0.06);
}

*,*::before,*::after { margin:0; padding:0; box-sizing:border-box; }

/* ── Dot-pattern background ─────────────────────────────────── */
body {
    font-family: 'Raleway', -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    overflow-x: hidden;
    position: relative;
    min-height: 100vh;
}
.dot-grid {
    position: fixed; inset: 0;
    background-image: radial-gradient(var(--dot) 1px, transparent 1px);
    background-size: 28px 28px;
    pointer-events: none; z-index: 0;
}

.container {
    max-width: 820px; margin: 0 auto; padding: 0 1.75rem;
    position: relative; z-index: 1;
}

/* ── Hero — centered editorial intro ────────────────────────── */
.hero {
    padding: 7rem 0 5.5rem; text-align: center;
    position: relative; z-index: 1;
    border-bottom: 1px solid var(--border);
}
.hero-inner { animation: fade-up 1s ease-out both; }

/* "Hello, I am" — italic greeting above the name */
.hero-greeting {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: clamp(1.4rem, 4vw, 2rem);
    font-weight: 300;
    font-style: italic;
    color: var(--gold);
    letter-spacing: 0.08em;
    margin-bottom: 0.3rem;
    opacity: 0.9;
}

/* Gold shimmer sweep across the name */
.hero-name {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: clamp(3.2rem, 9vw, 6rem);
    font-weight: 600; letter-spacing: -0.01em; line-height: 1.0;
    background: linear-gradient(
        90deg,
        var(--gold-dk) 0%,
        var(--gold) 25%,
        var(--gold-lt) 45%,
        var(--gold) 55%,
        var(--gold-dk) 80%,
        var(--gold) 100%
    );
    background-size: 250% 100%;
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gold-sweep 6s linear infinite;
    margin-bottom: 1.1rem;
}
@keyframes gold-sweep {
    0%   { background-position: 200% center; }
    100% { background-position: -200% center; }
}

/* Headline in elegant italic serif */
.hero-headline {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: clamp(1.1rem, 3vw, 1.4rem);
    font-style: italic; font-weight: 400;
    color: rgba(240,232,216,0.75);
    margin-bottom: 0.4rem;
}

/* Decorative thin gold rule */
.hero-rule {
    width: 80px; height: 1px; background: var(--gold);
    margin: 1.5rem auto;
    opacity: 0.55;
    position: relative;
    animation: rule-expand 1.2s 0.4s ease-out both;
}
.hero-rule::before, .hero-rule::after {
    content: '';
    position: absolute; top: 50%;
    transform: translateY(-50%);
    width: 4px; height: 4px;
    border-radius: 50%; background: var(--gold);
}
.hero-rule::before { left: -8px; }
.hero-rule::after  { right: -8px; }
@keyframes rule-expand {
    from { width: 0; opacity: 0; }
    to   { width: 80px; opacity: 0.55; }
}

.hero-location {
    font-size: 0.85rem; font-weight: 400;
    color: rgba(201,168,76,0.6); letter-spacing: 0.12em;
    text-transform: uppercase; margin-bottom: 2.25rem;
}
.hero-links {
    display: flex; justify-content: center; gap: 0.75rem; flex-wrap: wrap;
}
.hero-links a {
    text-decoration: none;
    font-family: 'Raleway', sans-serif;
    font-size: 0.78rem; font-weight: 500;
    letter-spacing: 0.14em; text-transform: uppercase;
    padding: 0.6rem 1.6rem; border-radius: 2px;
    border: 1px solid var(--border); color: var(--gold);
    background: transparent;
    transition: border-color 0.2s, background 0.2s,
                color 0.2s, box-shadow 0.2s, transform 0.15s;
}
.hero-links a:hover {
    border-color: var(--gold); background: var(--gold-dim);
    box-shadow: 0 0 20px var(--gold-glow);
    transform: translateY(-1px);
}

@keyframes fade-up {
    from { opacity: 0; transform: translateY(28px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Main sections ──────────────────────────────────────────── */
main { padding: 5rem 0; }
.section { margin-bottom: 4.5rem; }
.s1 { animation: fade-up 0.7s 0.1s ease-out both; }
.s2 { animation: fade-up 0.7s 0.2s ease-out both; }
.s3 { animation: fade-up 0.7s 0.3s ease-out both; }
.s4 { animation: fade-up 0.7s 0.4s ease-out both; }

/* ── Section headings — gold sliding underline ──────────────── */
h2 {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.6rem; font-weight: 400;
    color: var(--text); letter-spacing: 0.06em;
    margin-bottom: 2rem;
    display: inline-block;
    position: relative;
}
.h2-inner { display: block; }
/* Gold underline that slides left → right on section entry */
h2::after {
    content: ''; display: block;
    position: absolute; bottom: -6px; left: 0;
    width: 100%; height: 1px;
    background: linear-gradient(90deg, var(--gold), transparent);
    transform-origin: left center;
    animation: underline-in 0.8s ease-out both;
}
.s1 h2::after { animation-delay: 0.3s; }
.s2 h2::after { animation-delay: 0.4s; }
.s3 h2::after { animation-delay: 0.5s; }
.s4 h2::after { animation-delay: 0.6s; }
@keyframes underline-in {
    from { transform: scaleX(0); }
    to   { transform: scaleX(1); }
}

.bio {
    font-size: 1.05rem; font-weight: 300;
    color: rgba(240,232,216,0.72); line-height: 1.95;
    max-width: 680px;
}

/* ── Skills ─────────────────────────────────────────────────── */
.skills-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.skill-tag {
    font-family: 'Raleway', sans-serif;
    font-size: 0.75rem; font-weight: 500;
    letter-spacing: 0.1em; text-transform: uppercase;
    padding: 0.32rem 0.9rem; border-radius: 2px;
    border: 1px solid var(--border); color: rgba(201,168,76,0.75);
    background: transparent; cursor: default;
    transition: border-color 0.2s, color 0.2s,
                background 0.2s, box-shadow 0.2s;
}
.skill-tag:hover {
    border-color: var(--gold); color: var(--gold);
    background: var(--gold-dim); box-shadow: 0 0 12px var(--gold-glow);
}

/* ── Timeline experience ────────────────────────────────────── */
.timeline { position: relative; padding-left: 2.25rem; }
.timeline::before {
    content: ''; position: absolute;
    left: 0.4rem; top: 0.6rem; bottom: 0.6rem;
    width: 1px;
    background: linear-gradient(180deg, var(--gold), transparent);
}

.t-item { position: relative; margin-bottom: 2.25rem; }
/* Gold dot on timeline */
.t-item::before {
    content: ''; position: absolute;
    left: -1.9rem; top: 0.5rem;
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--gold);
    box-shadow: 0 0 0 3px var(--bg), 0 0 0 5px rgba(201,168,76,0.2);
    transition: box-shadow 0.2s;
}
.t-item:hover::before {
    box-shadow: 0 0 0 3px var(--bg), 0 0 0 7px rgba(201,168,76,0.35),
                0 0 12px var(--gold-glow);
}

.t-item-inner {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 4px; padding: 1.4rem 1.5rem;
    transition: border-color 0.22s, background 0.22s, transform 0.18s;
}
.t-item-inner:hover {
    border-color: var(--border-h); background: var(--bg-card-h);
    transform: translateX(4px);
}
.t-title {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.1rem; font-weight: 600; color: var(--text);
    margin-bottom: 0.15rem;
}
.t-company {
    font-size: 0.85rem; font-weight: 400;
    color: var(--gold); letter-spacing: 0.04em; margin-bottom: 0.65rem;
}
.t-duration {
    font-size: 0.75rem; letter-spacing: 0.08em;
    color: rgba(201,168,76,0.5); text-transform: uppercase;
    margin-bottom: 0.75rem;
}
.t-desc { font-size: 0.92rem; color: var(--muted); line-height: 1.75; }
.t-list { margin-top: 0.6rem; padding-left: 0; list-style: none; }
.t-list li {
    font-size: 0.88rem; color: var(--muted); margin-bottom: 0.3rem;
    padding-left: 1rem; position: relative;
}
.t-list li::before {
    content: '◆'; position: absolute; left: 0;
    color: var(--gold); font-size: 0.45rem; top: 0.3em;
}

/* ── Education ──────────────────────────────────────────────── */
.edu-grid { display: grid; grid-template-columns: 1fr; gap: 1rem; }
.edu-card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 4px; padding: 1.25rem 1.5rem;
    transition: border-color 0.22s, background 0.22s;
}
.edu-card:hover {
    border-color: var(--border-h); background: var(--bg-card-h);
}
.edu-degree {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.05rem; font-weight: 600; color: var(--text);
    margin-bottom: 0.25rem;
}
.edu-meta {
    font-size: 0.8rem; letter-spacing: 0.05em;
    color: rgba(201,168,76,0.6); font-weight: 400;
}

/* ── Footer ─────────────────────────────────────────────────── */
footer { padding: 4rem 0; text-align: center; }
.footer-rule {
    width: 120px; height: 1px; background: var(--gold);
    margin: 0 auto 1.5rem; opacity: 0.35;
}
.footer-sig {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.2rem; font-style: italic; font-weight: 300;
    color: rgba(201,168,76,0.6); margin-bottom: 0.4rem;
}
.footer-text { font-size: 0.75rem; letter-spacing: 0.1em; color: var(--muted); opacity: 0.5; }

/* ── Responsive ─────────────────────────────────────────────── */
@media (max-width: 640px) {
    .hero { padding: 4rem 0 3.5rem; }
    .hero-name { font-size: 3rem; }
    .timeline { padding-left: 1.5rem; }
    .timeline::before { left: 0.3rem; }
    .t-item::before { left: -1.25rem; }
    .edu-grid { grid-template-columns: 1fr; }
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
        for s in skills[:24]
    )


def _experience(items: list) -> str:
    out = ''
    for exp in items:
        highlights = ''.join(
            f'<li>{h}</li>' for h in exp['highlights']
        )
        out += (
            f'<div class="t-item">'
            f'<div class="t-item-inner">'
            f'<p class="t-title">{exp["title"]}</p>'
            f'<p class="t-company">{exp["company"]}</p>'
            f'<p class="t-duration">{exp["duration"]}</p>'
            f'<p class="t-desc">{exp["description"]}</p>'
            f'<ul class="t-list">{highlights}</ul>'
            f'</div>'
            f'</div>'
        )
    return out


def _education(items: list) -> str:
    out = ''
    for edu in items:
        out += (
            f'<div class="edu-card">'
            f'<p class="edu-degree">'
            f'{edu["degree"]} in {edu["field"]}'
            f'</p>'
            f'<p class="edu-meta">'
            f'{edu["institution"]} &middot; {edu["year"]}'
            f'</p>'
            f'</div>'
        )
    return out
