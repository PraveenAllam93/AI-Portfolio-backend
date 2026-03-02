"""
Template: Nebula
Cyberpunk / dark-space aesthetic. Deep black canvas with neon purple
(#a855f7) and cyan (#22d3ee) dual accents.

Background: animated CSS dot-grid overlay + drifting radial glow orbs.
Typography: Space Grotesk (headings) + Inter (body).
Effects:
  - Gradient text on hero name (purple → cyan)
  - Pulsing cyan dots in eyebrow label
  - Drifting grid & floating blurred orbs
  - Shimmer animation on hero bottom border
  - Glassmorphism cards with gradient left-accent reveal on hover
  - Neon glow on skill tag hover
  - Staggered section fade-in-up
No JavaScript — 100% CSS animations.
"""

from .base import CSP

_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Space+Grotesk:wght@300;400;500;600;700"
    "&family=Inter:wght@300;400;500&display=swap"
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
    <div class="bg-grid" aria-hidden="true"></div>
    <div class="orb orb-a" aria-hidden="true"></div>
    <div class="orb orb-b" aria-hidden="true"></div>

    <header class="hero">
        <div class="container">
            <div class="eyebrow">
                <span class="eyebrow-dot"></span>
                <span class="eyebrow-label">Portfolio</span>
                <span class="eyebrow-dot eyebrow-dot--late"></span>
            </div>
            <p class="hero-greeting">Hello, I&rsquo;m</p>
            <h1 class="hero-name">{v['name']}</h1>
            <p class="hero-headline">{v['headline']}</p>
            {location_html}
            <div class="hero-links">
                {links_html}
                {email_link}
            </div>
        </div>
        <div class="hero-shimmer" aria-hidden="true"></div>
    </header>

    <main class="container">
        <section class="section s1">
            <h2><span class="snum">01</span> About</h2>
            <p class="bio">{v['bio']}</p>
        </section>

        <section class="section s2">
            <h2><span class="snum">02</span> Skills</h2>
            <div class="skills-grid">{skills_html}</div>
        </section>

        <section class="section s3">
            <h2><span class="snum">03</span> Experience</h2>
            {experience_html}
        </section>

        <section class="section s4">
            <h2><span class="snum">04</span> Education</h2>
            {education_html}
        </section>
    </main>

    <footer>
        <div class="container">
            <div class="footer-rule" aria-hidden="true"></div>
            <p class="footer-text">Built with AI Portfolio Builder</p>
        </div>
    </footer>
</body>
</html>"""


def css() -> str:
    return """
/* ── Nebula Template ─────────────────────────────────────────── */
/* Deep space: neon purple + cyan on near-black canvas            */

:root {
    --p:         #a855f7;
    --p-dim:     rgba(168,85,247,0.11);
    --p-glow:    rgba(168,85,247,0.45);
    --c:         #22d3ee;
    --c-dim:     rgba(34,211,238,0.10);
    --c-glow:    rgba(34,211,238,0.38);
    --bg:        #07070f;
    --card:      rgba(255,255,255,0.025);
    --cb:        rgba(168,85,247,0.14);
    --cbh:       rgba(168,85,247,0.42);
    --text:      #e2e8f0;
    --muted:     #94a3b8;
    --grid:      rgba(168,85,247,0.038);
}

*,*::before,*::after { margin:0; padding:0; box-sizing:border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.65;
    overflow-x: hidden;
    position: relative;
    min-height: 100vh;
}

/* ── Animated grid background ───────────────────────────────── */
.bg-grid {
    position: fixed; inset: 0;
    background-image:
        linear-gradient(var(--grid) 1px, transparent 1px),
        linear-gradient(90deg, var(--grid) 1px, transparent 1px);
    background-size: 64px 64px;
    z-index: 0; pointer-events: none;
    animation: grid-drift 28s linear infinite;
}
@keyframes grid-drift {
    0%   { background-position: 0 0; }
    100% { background-position: 64px 64px; }
}

/* ── Floating glow orbs ─────────────────────────────────────── */
.orb {
    position: fixed; border-radius: 50%;
    pointer-events: none; z-index: 0;
    filter: blur(90px);
}
.orb-a {
    width: 600px; height: 600px; top: -180px; left: -120px;
    background: radial-gradient(
        circle, rgba(168,85,247,0.16), transparent 68%);
    animation: orb-float 20s ease-in-out infinite alternate;
}
.orb-b {
    width: 450px; height: 450px; bottom: -100px; right: -80px;
    background: radial-gradient(
        circle, rgba(34,211,238,0.12), transparent 68%);
    animation: orb-float 16s ease-in-out infinite alternate-reverse;
    animation-delay: -6s;
}
@keyframes orb-float {
    0%   { transform: translate(0,0) scale(1); }
    33%  { transform: translate(40px,-28px) scale(1.06); }
    66%  { transform: translate(-18px,22px) scale(0.97); }
    100% { transform: translate(28px,36px) scale(1.04); }
}

.container {
    max-width: 860px; margin: 0 auto; padding: 0 1.75rem;
    position: relative; z-index: 1;
}

/* ── Hero ───────────────────────────────────────────────────── */
.hero { padding: 6rem 0 4rem; position: relative; z-index: 1; }

.eyebrow {
    display: flex; align-items: center; gap: 0.55rem;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.68rem; font-weight: 600;
    letter-spacing: 0.28em; text-transform: uppercase;
    color: var(--c); margin-bottom: 1.75rem;
}
.eyebrow-dot {
    display: inline-block; width: 5px; height: 5px;
    border-radius: 50%; background: var(--c);
    animation: dot-blink 2.4s ease-in-out infinite;
}
.eyebrow-dot--late { animation-delay: 0.9s; }
@keyframes dot-blink {
    0%,100% { opacity: 1; transform: scale(1); }
    50%      { opacity: 0.25; transform: scale(0.55); }
}

/* "Hello, I'm" greeting line */
.hero-greeting {
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(1rem, 3vw, 1.3rem);
    font-weight: 300; letter-spacing: 0.12em;
    color: var(--c); opacity: 0.8;
    margin-bottom: 0.2rem;
    animation: rise 0.7s 0.04s cubic-bezier(0.22,1,0.36,1) both;
}

.hero-name {
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(2.6rem, 8vw, 4.75rem);
    font-weight: 700; letter-spacing: -0.035em; line-height: 1.04;
    background: linear-gradient(135deg, var(--p) 0%, var(--c) 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 1rem;
    animation: rise 0.7s cubic-bezier(0.22,1,0.36,1) both;
}
.hero-headline {
    font-size: 1.15rem; font-weight: 400; color: var(--muted);
    margin-bottom: 0.4rem;
    animation: rise 0.7s 0.12s cubic-bezier(0.22,1,0.36,1) both;
}
.hero-location {
    font-size: 0.875rem; color: var(--muted); margin-bottom: 2rem;
    animation: rise 0.7s 0.22s cubic-bezier(0.22,1,0.36,1) both;
}
@keyframes rise {
    from { opacity: 0; transform: translateY(22px); }
    to   { opacity: 1; transform: translateY(0); }
}

.hero-links {
    display: flex; gap: 0.75rem; flex-wrap: wrap;
    animation: rise 0.7s 0.32s cubic-bezier(0.22,1,0.36,1) both;
}
.hero-links a {
    text-decoration: none;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.85rem; font-weight: 500;
    padding: 0.55rem 1.25rem; border-radius: 6px;
    border: 1px solid var(--cb); color: var(--text);
    background: var(--card);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: border-color 0.22s, color 0.22s,
                box-shadow 0.22s, transform 0.18s;
}
.hero-links a:hover {
    border-color: var(--p); color: var(--p);
    box-shadow: 0 0 24px var(--p-glow), inset 0 0 16px var(--p-dim);
    transform: translateY(-2px);
}

/* shimmer line below hero */
.hero-shimmer {
    height: 1px; margin-top: 4rem;
    background: linear-gradient(90deg,
        transparent 0%, var(--p) 30%, var(--c) 65%, transparent 100%);
    background-size: 300% 100%;
    opacity: 0.55;
    animation: shimmer 4s linear infinite;
}
@keyframes shimmer {
    0%   { background-position: 200% center; }
    100% { background-position: -200% center; }
}

/* ── Sections ───────────────────────────────────────────────── */
main { padding: 4.5rem 0; }
.section { margin-bottom: 4rem; }
.s1 { animation: rise 0.6s 0.15s ease-out both; }
.s2 { animation: rise 0.6s 0.25s ease-out both; }
.s3 { animation: rise 0.6s 0.35s ease-out both; }
.s4 { animation: rise 0.6s 0.45s ease-out both; }

h2 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.05rem; font-weight: 600; color: var(--text);
    margin-bottom: 1.75rem;
    display: flex; align-items: center; gap: 0.85rem;
}
h2::after {
    content: ''; flex: 1; height: 1px;
    background: linear-gradient(90deg, var(--cb), transparent);
}
.snum {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em;
    color: var(--p); background: var(--p-dim);
    border: 1px solid rgba(168,85,247,0.25);
    padding: 0.22rem 0.6rem; border-radius: 4px;
    font-family: 'Space Grotesk', sans-serif;
}

.bio {
    font-size: 1.05rem; color: var(--muted);
    line-height: 1.88; max-width: 680px;
}

/* ── Skills ─────────────────────────────────────────────────── */
.skills-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.skill-tag {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8rem; font-weight: 500;
    padding: 0.35rem 0.9rem; border-radius: 20px;
    border: 1px solid var(--cb); color: var(--muted);
    background: var(--card);
    backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
    cursor: default;
    transition: border-color 0.2s, color 0.2s, background 0.2s,
                box-shadow 0.2s, transform 0.15s;
}
.skill-tag:hover {
    border-color: var(--c); color: var(--c);
    background: var(--c-dim); box-shadow: 0 0 14px var(--c-glow);
    transform: translateY(-2px);
}

/* ── Cards ──────────────────────────────────────────────────── */
.card {
    background: var(--card); border: 1px solid var(--cb);
    border-radius: 12px; padding: 1.6rem 1.75rem; margin-bottom: 1rem;
    position: relative; overflow: hidden;
    backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
    transition: border-color 0.25s, box-shadow 0.25s, transform 0.2s;
}
/* gradient left-accent reveals on hover */
.card::before {
    content: ''; position: absolute; top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, var(--p), var(--c));
    opacity: 0; transition: opacity 0.25s;
}
.card:hover {
    border-color: var(--cbh);
    box-shadow: 0 0 36px rgba(168,85,247,0.09);
    transform: translateX(5px);
}
.card:hover::before { opacity: 1; }

.card-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1rem; font-weight: 600; color: var(--text);
    margin-bottom: 0.2rem;
}
.card-company { opacity: 0.55; }
.card-meta {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.78rem; font-weight: 500;
    letter-spacing: 0.06em; color: var(--p); margin-bottom: 0.7rem;
}
.card-body {
    font-size: 0.92rem; color: var(--muted); line-height: 1.75;
}
.card-list {
    margin-top: 0.65rem; padding-left: 0; list-style: none;
}
.card-list li {
    font-size: 0.88rem; color: var(--muted); margin-bottom: 0.3rem;
    padding-left: 1.1rem; position: relative;
}
.card-list li::before {
    content: '›'; position: absolute; left: 0; color: var(--c);
}

/* ── Footer ─────────────────────────────────────────────────── */
footer { position: relative; z-index: 1; padding: 3rem 0; text-align: center; }
.footer-rule {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--cb), transparent);
    margin-bottom: 2rem;
}
.footer-text {
    font-size: 0.8rem; color: var(--muted); letter-spacing: 0.05em;
}

/* ── Responsive ─────────────────────────────────────────────── */
@media (max-width: 640px) {
    .hero { padding: 3.5rem 0 2.5rem; }
    .hero-name { font-size: 2.2rem; }
    .card { padding: 1.25rem; }
    .orb-a { width: 280px; height: 280px; }
    .orb-b { width: 220px; height: 220px; }
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
            f'<div class="card">'
            f'<p class="card-title">'
            f'{exp["title"]} '
            f'<span class="card-company">at {exp["company"]}</span>'
            f'</p>'
            f'<p class="card-meta">{exp["duration"]}</p>'
            f'<p class="card-body">{exp["description"]}</p>'
            f'<ul class="card-list">{highlights}</ul>'
            f'</div>'
        )
    return out


def _education(items: list) -> str:
    out = ''
    for edu in items:
        out += (
            f'<div class="card">'
            f'<p class="card-title">{edu["degree"]} in {edu["field"]}</p>'
            f'<p class="card-meta">'
            f'{edu["institution"]} &middot; {edu["year"]}'
            f'</p>'
            f'</div>'
        )
    return out
