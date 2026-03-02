"""
Template: Aurora
Aurora borealis aesthetic. Deep multi-stop gradient background that slowly
cycles through midnight blue → teal → violet → indigo.

Typography: Syne (800w headings — ultra-wide geometric) + DM Sans (body).
Effects:
  - Body background: animated 400%-size gradient cycling (CSS @keyframes)
  - Glassmorphism cards: backdrop-filter blur(20px), frosted glass look
  - Floating translucent bubbles in background (CSS only, no JS)
  - Gradient text on section headings (emerald → cyan)
  - Large hero name with white glow text-shadow
  - Skill tags as frosted-glass pill badges with emerald hover
  - Staggered card entrance animations
  - Floating hero particles (pure CSS border-radius orbs)
No JavaScript — 100% CSS animations.
"""

from .base import CSP

_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Syne:wght@400;600;700;800"
    "&family=DM+Sans:wght@300;400;500&display=swap"
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
    <div class="bubble b1" aria-hidden="true"></div>
    <div class="bubble b2" aria-hidden="true"></div>
    <div class="bubble b3" aria-hidden="true"></div>
    <div class="bubble b4" aria-hidden="true"></div>

    <header class="hero">
        <div class="container">
            <div class="hero-tag">Open to Work</div>
            <h1 class="hero-name">{v['name']}</h1>
            <p class="hero-headline">{v['headline']}</p>
            {location_html}
            <div class="hero-links">
                {links_html}
                {email_link}
            </div>
        </div>
    </header>

    <div class="wave-sep" aria-hidden="true">
        <svg viewBox="0 0 1440 60" preserveAspectRatio="none"
             xmlns="http://www.w3.org/2000/svg">
            <path d="M0,30 C360,60 1080,0 1440,30 L1440,60 L0,60 Z"
                  fill="rgba(15,23,42,0.9)"/>
        </svg>
    </div>

    <main class="container">
        <section class="section s1">
            <h2>About</h2>
            <div class="glass-panel">
                <p class="bio">{v['bio']}</p>
            </div>
        </section>

        <section class="section s2">
            <h2>Skills</h2>
            <div class="skills-grid">{skills_html}</div>
        </section>

        <section class="section s3">
            <h2>Experience</h2>
            {experience_html}
        </section>

        <section class="section s4">
            <h2>Education</h2>
            {education_html}
        </section>
    </main>

    <footer>
        <div class="container">
            <p class="footer-text">Built with AI Portfolio Builder</p>
        </div>
    </footer>
</body>
</html>"""


def css() -> str:
    return """
/* ── Aurora Template ─────────────────────────────────────────── */
/* Aurora borealis: animated gradient bg + glassmorphism cards   */

:root {
    --em:       #4ade80;
    --em-dim:   rgba(74,222,128,0.12);
    --em-glow:  rgba(74,222,128,0.35);
    --cy:       #22d3ee;
    --cy-dim:   rgba(34,211,238,0.10);
    --glass:    rgba(255,255,255,0.07);
    --glass-b:  rgba(255,255,255,0.12);
    --glass-h:  rgba(255,255,255,0.12);
    --text:     #f0f9ff;
    --muted:    rgba(226,232,240,0.72);
    --dark-bg:  #0f172a;
}

*,*::before,*::after { margin:0; padding:0; box-sizing:border-box; }

/* ── Animated aurora background ─────────────────────────────── */
body {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    background: linear-gradient(-45deg,
        #0d1b2a, #0a4a4a, #1a0a3e, #0d2d5e, #063b2f, #1e1040);
    background-size: 400% 400%;
    color: var(--text);
    line-height: 1.65;
    overflow-x: hidden;
    position: relative;
    min-height: 100vh;
    animation: aurora-shift 14s ease infinite;
}
@keyframes aurora-shift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* ── Floating background bubbles ────────────────────────────── */
.bubble {
    position: fixed; border-radius: 50%;
    pointer-events: none; z-index: 0;
    border: 1px solid rgba(255,255,255,0.06);
    backdrop-filter: blur(2px);
    -webkit-backdrop-filter: blur(2px);
}
.b1 {
    width: 380px; height: 380px; top: -80px; right: 10%;
    background: rgba(74,222,128,0.04);
    animation: bubble-drift 22s ease-in-out infinite alternate;
}
.b2 {
    width: 260px; height: 260px; bottom: 15%; left: -60px;
    background: rgba(34,211,238,0.05);
    animation: bubble-drift 18s ease-in-out infinite alternate-reverse;
    animation-delay: -5s;
}
.b3 {
    width: 160px; height: 160px; top: 40%; right: 5%;
    background: rgba(139,92,246,0.06);
    animation: bubble-drift 14s ease-in-out infinite alternate;
    animation-delay: -9s;
}
.b4 {
    width: 90px; height: 90px; top: 20%; left: 15%;
    background: rgba(74,222,128,0.05);
    animation: bubble-drift 10s ease-in-out infinite alternate-reverse;
    animation-delay: -3s;
}
@keyframes bubble-drift {
    0%   { transform: translate(0, 0) scale(1) rotate(0deg); }
    33%  { transform: translate(18px, -22px) scale(1.04) rotate(5deg); }
    66%  { transform: translate(-12px, 14px) scale(0.97) rotate(-3deg); }
    100% { transform: translate(10px, 20px) scale(1.02) rotate(2deg); }
}

.container {
    max-width: 860px; margin: 0 auto; padding: 0 1.75rem;
    position: relative; z-index: 1;
}

/* ── Hero ───────────────────────────────────────────────────── */
.hero {
    padding: 7rem 0 5rem; text-align: center;
    position: relative; z-index: 1;
}

.hero-tag {
    display: inline-flex; align-items: center; gap: 0.5rem;
    font-size: 0.72rem; font-weight: 500; letter-spacing: 0.18em;
    text-transform: uppercase; color: var(--em);
    background: rgba(74,222,128,0.1);
    border: 1px solid rgba(74,222,128,0.25);
    padding: 0.3rem 0.9rem; border-radius: 20px;
    margin-bottom: 1.75rem;
    animation: fade-up 0.7s ease-out both;
}
.hero-tag::before {
    content: '';
    display: inline-block; width: 6px; height: 6px;
    border-radius: 50%; background: var(--em);
    animation: live-dot 1.8s ease-in-out infinite;
}
@keyframes live-dot {
    0%,100% { opacity: 1; box-shadow: 0 0 0 0 rgba(74,222,128,0.5); }
    50%      { opacity: 0.7; box-shadow: 0 0 0 5px rgba(74,222,128,0); }
}

.hero-name {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2.8rem, 9vw, 5.5rem);
    font-weight: 800; letter-spacing: -0.03em; line-height: 1.0;
    color: #fff;
    text-shadow: 0 0 60px rgba(74,222,128,0.3),
                 0 0 120px rgba(34,211,238,0.15);
    margin-bottom: 1.1rem;
    animation: fade-up 0.7s 0.1s ease-out both;
}
.hero-headline {
    font-size: 1.2rem; font-weight: 300; color: var(--muted);
    margin-bottom: 0.5rem;
    animation: fade-up 0.7s 0.2s ease-out both;
}
.hero-location {
    font-size: 0.9rem; color: rgba(226,232,240,0.5);
    margin-bottom: 2.25rem;
    animation: fade-up 0.7s 0.28s ease-out both;
}
@keyframes fade-up {
    from { opacity: 0; transform: translateY(24px); }
    to   { opacity: 1; transform: translateY(0); }
}

.hero-links {
    display: flex; justify-content: center; gap: 0.75rem; flex-wrap: wrap;
    animation: fade-up 0.7s 0.38s ease-out both;
}
.hero-links a {
    text-decoration: none;
    font-family: 'Syne', sans-serif;
    font-size: 0.85rem; font-weight: 600;
    padding: 0.6rem 1.4rem; border-radius: 8px;
    border: 1px solid var(--glass-b); color: var(--text);
    background: var(--glass);
    backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    transition: border-color 0.22s, background 0.22s, transform 0.18s,
                box-shadow 0.22s;
}
.hero-links a:hover {
    border-color: var(--em); background: var(--em-dim);
    color: var(--em);
    box-shadow: 0 0 24px var(--em-glow);
    transform: translateY(-2px);
}

/* ── Wave separator ─────────────────────────────────────────── */
.wave-sep {
    width: 100%; line-height: 0;
    position: relative; z-index: 1;
    margin-top: -2px;
}
.wave-sep svg { width: 100%; height: 60px; display: block; }

/* ── Main content ───────────────────────────────────────────── */
main {
    background: var(--dark-bg);
    padding: 4rem 0 5rem;
    position: relative; z-index: 1;
    border-radius: 0 0 0 0;
}

.section { margin-bottom: 4rem; }
.s1 { animation: fade-up 0.6s 0.1s ease-out both; }
.s2 { animation: fade-up 0.6s 0.2s ease-out both; }
.s3 { animation: fade-up 0.6s 0.3s ease-out both; }
.s4 { animation: fade-up 0.6s 0.4s ease-out both; }

/* ── Section headings — gradient text ──────────────────────── */
h2 {
    font-family: 'Syne', sans-serif;
    font-size: 1.5rem; font-weight: 700;
    background: linear-gradient(135deg, var(--em), var(--cy));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 0 16px rgba(74,222,128,0.25));
    margin-bottom: 1.5rem;
    display: flex; align-items: center; gap: 0.75rem;
}
h2::after {
    content: ''; flex: 1; height: 1px;
    background: linear-gradient(90deg,
        rgba(74,222,128,0.3), rgba(34,211,238,0.1), transparent);
}

/* ── Bio panel ──────────────────────────────────────────────── */
.glass-panel {
    background: var(--glass); border: 1px solid var(--glass-b);
    border-radius: 16px; padding: 1.75rem 2rem;
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
}
.bio {
    font-size: 1.05rem; color: var(--muted); line-height: 1.9;
    font-weight: 300;
}

/* ── Skills ─────────────────────────────────────────────────── */
.skills-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.skill-tag {
    font-family: 'Syne', sans-serif;
    font-size: 0.78rem; font-weight: 600;
    padding: 0.38rem 0.95rem; border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.1);
    color: rgba(226,232,240,0.7);
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
    cursor: default;
    transition: border-color 0.2s, color 0.2s, background 0.2s,
                box-shadow 0.2s, transform 0.15s;
}
.skill-tag:hover {
    border-color: var(--em); color: var(--em);
    background: var(--em-dim); box-shadow: 0 0 16px var(--em-glow);
    transform: translateY(-2px);
}

/* ── Cards ──────────────────────────────────────────────────── */
.card {
    background: var(--glass); border: 1px solid var(--glass-b);
    border-radius: 14px; padding: 1.6rem 1.8rem; margin-bottom: 1rem;
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    transition: background 0.25s, border-color 0.25s,
                transform 0.2s, box-shadow 0.25s;
}
.card:hover {
    background: var(--glass-h);
    border-color: rgba(74,222,128,0.3);
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.3), 0 0 20px var(--em-glow);
}
/* staggered card entrance */
.card:nth-child(1) { animation: fade-up 0.5s 0.05s ease-out both; }
.card:nth-child(2) { animation: fade-up 0.5s 0.12s ease-out both; }
.card:nth-child(3) { animation: fade-up 0.5s 0.19s ease-out both; }
.card:nth-child(4) { animation: fade-up 0.5s 0.26s ease-out both; }
.card:nth-child(5) { animation: fade-up 0.5s 0.33s ease-out both; }

.card-title {
    font-family: 'Syne', sans-serif;
    font-size: 1rem; font-weight: 700; color: var(--text);
    margin-bottom: 0.2rem;
}
.card-company { opacity: 0.55; font-weight: 400; }
.card-meta {
    font-size: 0.78rem; font-weight: 500;
    color: var(--em); letter-spacing: 0.04em;
    margin-bottom: 0.75rem;
}
.card-body {
    font-size: 0.92rem; color: var(--muted); line-height: 1.75;
    font-weight: 300;
}
.card-list { margin-top: 0.65rem; padding-left: 0; list-style: none; }
.card-list li {
    font-size: 0.88rem; color: var(--muted); margin-bottom: 0.3rem;
    padding-left: 1.1rem; position: relative; font-weight: 300;
}
.card-list li::before {
    content: '▸'; position: absolute; left: 0; color: var(--em);
    font-size: 0.7rem; top: 0.1em;
}

/* ── Footer ─────────────────────────────────────────────────── */
footer {
    background: var(--dark-bg); padding: 3rem 0;
    text-align: center; position: relative; z-index: 1;
    border-top: 1px solid rgba(255,255,255,0.06);
}
.footer-text { font-size: 0.8rem; color: rgba(226,232,240,0.35); letter-spacing: 0.05em; }

/* ── Responsive ─────────────────────────────────────────────── */
@media (max-width: 640px) {
    .hero { padding: 4rem 0 3rem; }
    .hero-name { font-size: 2.4rem; }
    .hero-links { justify-content: flex-start; }
    .card { padding: 1.25rem; }
    .b1, .b2, .b3, .b4 { display: none; }
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
