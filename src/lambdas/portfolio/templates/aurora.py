"""
Template: Aurora
Aurora borealis aesthetic. Deep multi-stop gradient background that slowly
cycles through midnight blue → teal → violet → indigo.

Typography: Syne (800w headings) + DM Sans (body).
Effects: animated gradient bg, glassmorphism cards, floating bubbles,
         gradient text headings, skill tag hover glow, staggered fade-up.
Supports all 4 resume categories (SE, Designer, Marketing, Finance).
No JavaScript — 100% CSS animations.
"""

from .base import CSP, DEFAULT_SECTION_ORDER

_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Syne:wght@400;600;700;800"
    "&family=DM+Sans:wght@300;400;500&display=swap"
)



def html(v: dict) -> str:
    links = ''
    if v.get('linkedin_url'):
        links += f'<a href="{v["linkedin_url"]}" target="_blank" rel="noopener noreferrer">LinkedIn</a>'
    if v.get('github_url'):
        links += f'<a href="{v["github_url"]}" target="_blank" rel="noopener noreferrer">GitHub</a>'
    if v.get('portfolio_url'):
        links += f'<a href="{v["portfolio_url"]}" target="_blank" rel="noopener noreferrer">Portfolio</a>'
    if v.get('email'):
        links += f'<a href="mailto:{v["email"]}">Email</a>'
    location_html = f'<p class="hero-location">{v["location"]}</p>' if v.get('location') else ''

    order = v.get('section_order') or DEFAULT_SECTION_ORDER
    hidden = v.get('hidden_sections') or set()
    about_html = _section('About', _about(v))
    content_sections = '\n'.join(filter(None, [
        _section(label, renderer(v))
        for key in order
        if key not in hidden and key in _SECTION_RENDERERS
        for label, renderer in [_SECTION_RENDERERS[key]]
    ]))
    sections = '\n'.join(filter(None, [about_html, content_sections]))

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
            <div class="hero-tag">Portfolio</div>
            <h1 class="hero-name">{v['name']}</h1>
            <p class="hero-headline">{v.get('headline', '')}</p>
            {location_html}
            <div class="hero-links">{links}</div>
        </div>
    </header>

    <div class="wave-sep" aria-hidden="true">
        <svg viewBox="0 0 1440 60" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M0,30 C360,60 1080,0 1440,30 L1440,60 L0,60 Z" fill="rgba(15,23,42,0.9)"/>
        </svg>
    </div>

    <main class="container">
        {sections}
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

:root {
    --em:      #4ade80;
    --em-dim:  rgba(74,222,128,0.12);
    --em-glow: rgba(74,222,128,0.35);
    --cy:      #22d3ee;
    --cy-dim:  rgba(34,211,238,0.10);
    --glass:   rgba(255,255,255,0.07);
    --glass-b: rgba(255,255,255,0.12);
    --glass-h: rgba(255,255,255,0.12);
    --text:    #f0f9ff;
    --muted:   rgba(226,232,240,0.72);
    --dark-bg: #0f172a;
}

*,*::before,*::after { margin:0; padding:0; box-sizing:border-box; }

body {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    background: linear-gradient(-45deg, #0d1b2a, #0a4a4a, #1a0a3e, #0d2d5e, #063b2f, #1e1040);
    background-size: 400% 400%;
    color: var(--text); line-height: 1.65;
    overflow-x: hidden; position: relative; min-height: 100vh;
    animation: aurora-shift 14s ease infinite;
}
@keyframes aurora-shift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Floating bubbles */
.bubble {
    position: fixed; border-radius: 50%; pointer-events: none; z-index: 0;
    border: 1px solid rgba(255,255,255,0.06);
    backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px);
}
.b1 { width:380px; height:380px; top:-80px; right:10%; background:rgba(74,222,128,0.04); animation:bubble-drift 22s ease-in-out infinite alternate; }
.b2 { width:260px; height:260px; bottom:15%; left:-60px; background:rgba(34,211,238,0.05); animation:bubble-drift 18s ease-in-out infinite alternate-reverse; animation-delay:-5s; }
.b3 { width:160px; height:160px; top:40%; right:5%; background:rgba(139,92,246,0.06); animation:bubble-drift 14s ease-in-out infinite alternate; animation-delay:-9s; }
.b4 { width:90px; height:90px; top:20%; left:15%; background:rgba(74,222,128,0.05); animation:bubble-drift 10s ease-in-out infinite alternate-reverse; animation-delay:-3s; }
@keyframes bubble-drift {
    0%   { transform: translate(0,0) scale(1) rotate(0deg); }
    33%  { transform: translate(18px,-22px) scale(1.04) rotate(5deg); }
    66%  { transform: translate(-12px,14px) scale(0.97) rotate(-3deg); }
    100% { transform: translate(10px,20px) scale(1.02) rotate(2deg); }
}

.container { max-width: 860px; margin: 0 auto; padding: 0 1.75rem; position: relative; z-index: 1; }

/* Hero */
.hero { padding: 7rem 0 5rem; text-align: center; position: relative; z-index: 1; }
.hero-tag {
    display: inline-flex; align-items: center; gap: 0.5rem;
    font-size: 0.72rem; font-weight: 500; letter-spacing: 0.18em; text-transform: uppercase;
    color: var(--em); background: rgba(74,222,128,0.1);
    border: 1px solid rgba(74,222,128,0.25);
    padding: 0.3rem 0.9rem; border-radius: 20px; margin-bottom: 1.75rem;
}
.hero-name {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2.8rem,9vw,5.5rem); font-weight: 800;
    letter-spacing: -0.03em; line-height: 1.0; color: #fff;
    text-shadow: 0 0 60px rgba(74,222,128,0.3), 0 0 120px rgba(34,211,238,0.15);
    margin-bottom: 1.1rem;
}
.hero-headline { font-size: 1.2rem; font-weight: 300; color: var(--muted); margin-bottom: 0.5rem; }
.hero-location { font-size: 0.9rem; color: rgba(226,232,240,0.5); margin-bottom: 2.25rem; }
.hero-links { display: flex; justify-content: center; gap: 0.75rem; flex-wrap: wrap; }
.hero-links a {
    text-decoration: none; font-family: 'Syne', sans-serif;
    font-size: 0.85rem; font-weight: 600;
    padding: 0.6rem 1.4rem; border-radius: 8px;
    border: 1px solid var(--glass-b); color: var(--text);
    background: var(--glass); backdrop-filter: blur(16px);
    transition: border-color 0.22s, background 0.22s, transform 0.18s, box-shadow 0.22s;
}
.hero-links a:hover {
    border-color: var(--em); background: var(--em-dim); color: var(--em);
    box-shadow: 0 0 24px var(--em-glow); transform: translateY(-2px);
}

/* Wave */
.wave-sep { width: 100%; line-height: 0; position: relative; z-index: 1; margin-top: -2px; }
.wave-sep svg { width: 100%; height: 60px; display: block; }

/* Main */
main { background: var(--dark-bg); padding: 4rem 0 5rem; position: relative; z-index: 1; }
section { margin-bottom: 4rem; animation: fade-up 0.6s ease-out both; }
@keyframes fade-up {
    from { opacity: 0; transform: translateY(24px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* H2 — gradient text */
h2 {
    font-family: 'Syne', sans-serif; font-size: 1.5rem; font-weight: 700;
    background: linear-gradient(135deg, var(--em), var(--cy));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    filter: drop-shadow(0 0 16px rgba(74,222,128,0.25));
    margin-bottom: 1.5rem;
    display: flex; align-items: center; gap: 0.75rem;
}
h2::after {
    content: ''; flex: 1; height: 1px;
    background: linear-gradient(90deg, rgba(74,222,128,0.3), rgba(34,211,238,0.1), transparent);
}

/* Bio */
.bio { font-size: 1.05rem; color: var(--muted); line-height: 1.9; font-weight: 300; }
.glass-panel {
    background: var(--glass); border: 1px solid var(--glass-b);
    border-radius: 16px; padding: 1.75rem 2rem;
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
}

/* Skills */
.skill-group { margin-bottom: 1rem; }
.skill-group-label {
    font-family: 'Syne', sans-serif; font-size: 0.75rem; font-weight: 600;
    color: var(--em); letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.4rem;
}
.tag-row { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.skill-tag {
    font-family: 'Syne', sans-serif; font-size: 0.78rem; font-weight: 600;
    padding: 0.38rem 0.95rem; border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.1); color: rgba(226,232,240,0.7);
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
    cursor: default;
    transition: border-color 0.2s, color 0.2s, background 0.2s, box-shadow 0.2s, transform 0.15s;
}
.skill-tag:hover {
    border-color: var(--em); color: var(--em);
    background: var(--em-dim); box-shadow: 0 0 16px var(--em-glow); transform: translateY(-2px);
}

/* Cards — used for exp, edu, projects, campaigns, etc. */
.card {
    background: var(--glass); border: 1px solid var(--glass-b);
    border-radius: 14px; padding: 1.6rem 1.8rem; margin-bottom: 1rem;
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    transition: background 0.25s, border-color 0.25s, transform 0.2s, box-shadow 0.25s;
}
.card:hover {
    background: var(--glass-h); border-color: rgba(74,222,128,0.3);
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.3), 0 0 20px var(--em-glow);
}
.card-title {
    font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700;
    color: var(--text); margin-bottom: 0.2rem;
}
.card-sub { opacity: 0.55; font-weight: 400; }
.card-meta {
    font-size: 0.78rem; font-weight: 500; color: var(--em);
    letter-spacing: 0.04em; margin-bottom: 0.75rem;
}
.card-body { font-size: 0.92rem; color: var(--muted); line-height: 1.75; font-weight: 300; }
.card-list { margin-top: 0.65rem; padding-left: 0; list-style: none; }
.card-list li {
    font-size: 0.88rem; color: var(--muted); margin-bottom: 0.3rem;
    padding-left: 1.1rem; position: relative; font-weight: 300;
}
.card-list li::before { content: '▸'; position: absolute; left: 0; color: var(--em); font-size: 0.7rem; top: 0.1em; }

/* Tech tags */
.tech-tag {
    font-size: 0.75rem; padding: 0.25rem 0.6rem; border-radius: 4px;
    background: rgba(74,222,128,0.1); color: var(--em);
    border: 1px solid rgba(74,222,128,0.2);
}

/* Cert / Achievement / Award rows */
.cert-row {
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 0.25rem;
    padding: 0.75rem 1.25rem; margin-bottom: 0.5rem;
    background: var(--glass); border: 1px solid var(--glass-b); border-radius: 8px;
    backdrop-filter: blur(12px);
}
.cert-name { font-size: 0.95rem; font-weight: 500; }
.cert-meta { font-size: 0.8rem; color: var(--em); }

/* Philosophy */
.philosophy { font-size: 1.05rem; color: var(--muted); line-height: 1.85; font-weight: 300; }

/* IP stats */
.ip-stats { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-top: 0.4rem; }
.ip-stat { font-size: 0.85rem; color: var(--muted); }
.ip-stat strong { color: var(--em); }

/* Footer */
footer { background: var(--dark-bg); padding: 3rem 0; text-align: center; position: relative; z-index: 1; border-top: 1px solid rgba(255,255,255,0.06); }
.footer-text { font-size: 0.8rem; color: rgba(226,232,240,0.35); letter-spacing: 0.05em; }

@media (max-width: 640px) {
    .hero { padding: 4rem 0 3rem; }
    .hero-name { font-size: 2.4rem; }
    .card { padding: 1.25rem; }
    .b1, .b2, .b3, .b4 { display: none; }
}
"""


# ---------------------------------------------------------------------------
# Section renderer
# ---------------------------------------------------------------------------

def _section(title: str, content: str) -> str:
    if not content:
        return ''
    return f'<section><h2>{title}</h2>{content}</section>'


# ---------------------------------------------------------------------------
# Content renderers
# ---------------------------------------------------------------------------

def _about(v: dict) -> str:
    bio = v.get('bio', '')
    if not bio:
        return ''
    return f'<div class="glass-panel"><p class="bio">{bio}</p></div>'


def _skills(v: dict) -> str:
    groups = v.get('skill_groups') or []
    out = ''
    for g in groups:
        tags = ''.join(f'<span class="skill-tag">{s}</span>' for s in g.get('skills', []))
        if tags:
            out += (
                f'<div class="skill-group">'
                f'<p class="skill-group-label">{g.get("category","")}</p>'
                f'<div class="tag-row">{tags}</div>'
                f'</div>'
            )
    return out


def _experience(v: dict) -> str:
    items = v.get('experience') or []
    out = ''
    for exp in items:
        meta_parts = []
        if exp.get('duration'):  meta_parts.append(exp['duration'])
        if exp.get('location'):  meta_parts.append(exp['location'])
        meta = ' · '.join(meta_parts)
        points = ''.join(f'<li>{p}</li>' for p in exp.get('key_points', []))
        desc = exp.get('description', '')
        out += (
            f'<div class="card">'
            f'<p class="card-title">{exp.get("role","")}'
            f' <span class="card-sub">at {exp.get("company","")}</span></p>'
            f'<p class="card-meta">{meta}</p>'
            + (f'<p class="card-body">{desc}</p>' if desc else '')
            + (f'<ul class="card-list">{points}</ul>' if points else '')
            + f'</div>'
        )
    return out


def _education(v: dict) -> str:
    items = v.get('education') or []
    out = ''
    for edu in items:
        degree = edu.get('degree', '')
        if edu.get('field_of_study'):
            degree = f'{degree} in {edu["field_of_study"]}'
        meta_parts = []
        if edu.get('institution'): meta_parts.append(edu['institution'])
        if edu.get('year_range'):  meta_parts.append(edu['year_range'])
        meta = ' · '.join(meta_parts)
        grade = edu.get('grade_or_score', '')
        out += (
            f'<div class="card">'
            f'<p class="card-title">{degree}</p>'
            f'<p class="card-meta">{meta}</p>'
            + (f'<p class="card-body">{grade}</p>' if grade else '')
            + f'</div>'
        )
    return out


def _projects(v: dict) -> str:
    items = v.get('projects') or []
    out = ''
    for p in items:
        url = p.get('project_url') or p.get('github_repo') or ''
        link = (
            f' <a href="{url}" target="_blank" rel="noopener noreferrer" '
            f'style="font-size:0.78rem;color:var(--em);text-decoration:none;'
            f'border:1px solid rgba(74,222,128,0.35);padding:0.15rem 0.55rem;border-radius:4px;">Link</a>'
            if url else ''
        )
        tags     = p.get('tech_stack') or p.get('software_used') or []
        tech     = ''.join(f'<span class="tech-tag">{t}</span>' for t in tags)
        resp     = p.get('responsibilities') or []
        outcomes = p.get('measurable_outcomes') or []
        resp_lis    = ''.join(f'<li>{r}</li>' for r in resp)
        outcome_lis = ''.join(f'<li>{o}</li>' for o in outcomes)
        out += (
            f'<div class="card">'
            f'<p class="card-title">{p.get("title","")}{link}</p>'
            + (f'<p class="card-body">{p.get("description","")}</p>' if p.get('description') else '')
            + (f'<div class="tag-row" style="margin-top:0.5rem">{tech}</div>' if tech else '')
            + (f'<ul class="card-list">{resp_lis}</ul>' if resp_lis else '')
            + (f'<ul class="card-list">{outcome_lis}</ul>' if outcome_lis else '')
            + f'</div>'
        )
    return out


def _certifications(v: dict) -> str:
    items = v.get('certifications') or []
    out = ''
    for c in items:
        meta_parts = []
        if c.get('issuer'): meta_parts.append(c['issuer'])
        if c.get('year'):   meta_parts.append(c['year'])
        meta = ' · '.join(meta_parts)
        out += (
            f'<div class="cert-row">'
            f'<span class="cert-name">{c.get("name","")}</span>'
            + (f'<span class="cert-meta">{meta}</span>' if meta else '')
            + f'</div>'
        )
    return out


def _achievements(v: dict) -> str:
    items = v.get('achievements') or []
    out = ''
    for a in items:
        out += (
            f'<div class="card">'
            f'<p class="card-title">{a.get("title","")}</p>'
            + (f'<p class="card-body">{a.get("description","")}</p>' if a.get('description') else '')
            + f'</div>'
        )
    return out


def _awards(v: dict) -> str:
    items = v.get('awards') or []
    out = ''
    for a in items:
        body = a.get('awarding_body', '')
        year = a.get('year', '')
        meta = ' · '.join(filter(None, [body, year]))
        out += (
            f'<div class="card">'
            f'<p class="card-title">{a.get("title","")}</p>'
            + (f'<p class="card-meta">{meta}</p>' if meta else '')
            + f'</div>'
        )
    return out


def _design_philosophy(v: dict) -> str:
    text = v.get('design_philosophy', '')
    return f'<div class="glass-panel"><p class="philosophy">{text}</p></div>' if text else ''


def _software_proficiency(v: dict) -> str:
    items = v.get('software_proficiency') or []
    if not items:
        return ''
    tags = ''.join(f'<span class="skill-tag">{s}</span>' for s in items)
    return f'<div class="tag-row">{tags}</div>'


def _campaigns(v: dict) -> str:
    items = v.get('campaigns') or []
    out = ''
    for c in items:
        ctype = c.get('campaign_type', '')
        channels = ', '.join(c.get('channels_used', []))
        budget = c.get('budget', '')
        meta_parts = filter(None, [ctype, f'Budget: {budget}' if budget else '', f'Channels: {channels}' if channels else ''])
        meta = ' · '.join(meta_parts)
        metrics = ''.join(f'<li>{m}</li>' for m in c.get('performance_metrics', []))
        out += (
            f'<div class="card">'
            f'<p class="card-title">{c.get("campaign_name","")}</p>'
            + (f'<p class="card-meta">{meta}</p>' if meta else '')
            + (f'<ul class="card-list">{metrics}</ul>' if metrics else '')
            + f'</div>'
        )
    return out


def _financial_modeling(v: dict) -> str:
    items = v.get('financial_modeling') or []
    out = ''
    for fm in items:
        tools = ''.join(f'<span class="tech-tag">{t}</span>' for t in fm.get('tools_used', []))
        out += (
            f'<div class="card">'
            f'<p class="card-title">{fm.get("model_type","")}</p>'
            + (f'<div class="tag-row" style="margin:0.5rem 0">{tools}</div>' if tools else '')
            + (f'<p class="card-body">{fm.get("outcome","")}</p>' if fm.get('outcome') else '')
            + f'</div>'
        )
    return out


def _investment_portfolios(v: dict) -> str:
    items = v.get('investment_portfolios') or []
    out = ''
    for ip in items:
        aum = ip.get('assets_under_management', '')
        ret = ip.get('performance_return', '')
        out += (
            f'<div class="card">'
            f'<p class="card-title">{ip.get("portfolio_type","")}</p>'
            f'<div class="ip-stats">'
            + (f'<span class="ip-stat"><strong>AUM:</strong> {aum}</span>' if aum else '')
            + (f'<span class="ip-stat"><strong>Return:</strong> {ret}</span>' if ret else '')
            + f'</div></div>'
        )
    return out


_SECTION_RENDERERS = {
    'experience':            ('Experience',            _experience),
    'projects':              ('Projects',              _projects),
    'skills':                ('Skills',                _skills),
    'education':             ('Education',             _education),
    'certifications':        ('Certifications',        _certifications),
    'achievements':          ('Achievements',          _achievements),
    'awards':                ('Awards',                _awards),
    'campaigns':             ('Campaigns',             _campaigns),
    'financial_modeling':    ('Financial Modeling',    _financial_modeling),
    'investment_portfolios': ('Investment Portfolios', _investment_portfolios),
    'design_philosophy':     ('Design Philosophy',     _design_philosophy),
    'software_proficiency':  ('Software Proficiency',  _software_proficiency),
}
