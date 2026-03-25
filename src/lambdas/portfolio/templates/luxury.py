"""
Template: Luxury
Ultra-premium editorial aesthetic. Deep midnight navy canvas with gold
(#c9a84c) accents throughout.

Typography: Cormorant Garamond (headings — luxury serif), Raleway (body).
Layout: Centered hero with "Hello, I am" greeting, timeline experience,
        generous whitespace, editorial feel.
Effects: gold shimmer on hero name, dot-pattern bg, animated underlines,
         timeline with gold dots.
Supports all 4 resume categories (SE, Designer, Marketing, Finance).
No JavaScript — 100% CSS animations.
"""

from .base import CSP, DEFAULT_SECTION_ORDER

_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600"
    "&family=Raleway:wght@300;400;500&display=swap"
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
    <div class="dot-grid" aria-hidden="true"></div>

    <header class="hero">
        <div class="container">
            <div class="hero-inner">
                <p class="hero-greeting">Hello, I am</p>
                <h1 class="hero-name">{v['name']}</h1>
                <p class="hero-headline">{v.get('headline', '')}</p>
                <div class="hero-rule" aria-hidden="true"></div>
                {location_html}
                <div class="hero-links">{links}</div>
            </div>
        </div>
    </header>

    <main class="container">
        {sections}
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

:root {
    --gold:      #c9a84c;
    --gold-lt:   #f0d080;
    --gold-dk:   #8b6914;
    --gold-dim:  rgba(201,168,76,0.12);
    --gold-glow: rgba(201,168,76,0.35);
    --bg:        #060c18;
    --bg-card:   rgba(255,255,255,0.03);
    --bg-card-h: rgba(201,168,76,0.05);
    --border:    rgba(201,168,76,0.18);
    --border-h:  rgba(201,168,76,0.45);
    --text:      #f0e8d8;
    --muted:     rgba(220,210,190,0.6);
    --dot:       rgba(201,168,76,0.06);
}

*,*::before,*::after { margin:0; padding:0; box-sizing:border-box; }

body {
    font-family: 'Raleway', -apple-system, sans-serif;
    background: var(--bg); color: var(--text);
    line-height: 1.7; overflow-x: hidden; min-height: 100vh;
}
.dot-grid {
    position: fixed; inset: 0;
    background-image: radial-gradient(var(--dot) 1px, transparent 1px);
    background-size: 28px 28px; pointer-events: none; z-index: 0;
}
.container { max-width: 820px; margin: 0 auto; padding: 0 1.75rem; position: relative; z-index: 1; }

/* ── Hero ─────────────────────────────────────────────────── */
.hero { padding: 7rem 0 5.5rem; text-align: center; position: relative; z-index: 1; border-bottom: 1px solid var(--border); }
.hero-inner { animation: fade-up 1s ease-out both; }
.hero-greeting {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: clamp(1.4rem,4vw,2rem); font-weight: 300; font-style: italic;
    color: var(--gold); letter-spacing: 0.08em; margin-bottom: 0.3rem;
}
.hero-name {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: clamp(3.2rem,9vw,6rem); font-weight: 600; letter-spacing: -0.01em; line-height: 1.0;
    background: linear-gradient(90deg,var(--gold-dk) 0%,var(--gold) 25%,var(--gold-lt) 45%,var(--gold) 55%,var(--gold-dk) 80%,var(--gold) 100%);
    background-size: 250% 100%;
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    animation: gold-sweep 6s linear infinite; margin-bottom: 1.1rem;
}
@keyframes gold-sweep { 0%{background-position:200% center} 100%{background-position:-200% center} }
.hero-headline {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: clamp(1.1rem,3vw,1.4rem); font-style: italic; font-weight: 400;
    color: rgba(240,232,216,0.75); margin-bottom: 0.4rem;
}
.hero-rule {
    width: 80px; height: 1px; background: var(--gold); margin: 1.5rem auto; opacity: 0.55;
    position: relative; animation: rule-expand 1.2s 0.4s ease-out both;
}
.hero-rule::before,.hero-rule::after {
    content:''; position:absolute; top:50%; transform:translateY(-50%);
    width:4px; height:4px; border-radius:50%; background:var(--gold);
}
.hero-rule::before{left:-8px} .hero-rule::after{right:-8px}
@keyframes rule-expand { from{width:0;opacity:0} to{width:80px;opacity:0.55} }
.hero-location { font-size:0.85rem; color:rgba(201,168,76,0.6); letter-spacing:0.12em; text-transform:uppercase; margin-bottom:2.25rem; }
.hero-links { display:flex; justify-content:center; gap:0.75rem; flex-wrap:wrap; }
.hero-links a {
    text-decoration:none; font-family:'Raleway',sans-serif;
    font-size:0.78rem; font-weight:500; letter-spacing:0.14em; text-transform:uppercase;
    padding:0.6rem 1.6rem; border-radius:2px; border:1px solid var(--border); color:var(--gold);
    transition: border-color 0.2s, background 0.2s, box-shadow 0.2s, transform 0.15s;
}
.hero-links a:hover { border-color:var(--gold); background:var(--gold-dim); box-shadow:0 0 20px var(--gold-glow); transform:translateY(-1px); }
@keyframes fade-up { from{opacity:0;transform:translateY(28px)} to{opacity:1;transform:translateY(0)} }

/* ── Sections ─────────────────────────────────────────────── */
main { padding: 5rem 0; }
section { margin-bottom: 4.5rem; animation: fade-up 0.7s ease-out both; }
h2 {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.6rem; font-weight: 400; color: var(--text); letter-spacing: 0.06em;
    margin-bottom: 2rem; display: inline-block; position: relative;
}
h2::after {
    content:''; display:block; position:absolute; bottom:-6px; left:0;
    width:100%; height:1px; background:linear-gradient(90deg,var(--gold),transparent);
    transform-origin:left center; animation:underline-in 0.8s ease-out both;
}
@keyframes underline-in { from{transform:scaleX(0)} to{transform:scaleX(1)} }

.bio { font-size:1.05rem; font-weight:300; color:rgba(240,232,216,0.72); line-height:1.95; max-width:680px; }

/* Skills */
.skill-group { margin-bottom: 1rem; }
.skill-group-label { font-family:'Raleway',sans-serif; font-size:0.72rem; font-weight:500; letter-spacing:0.14em; text-transform:uppercase; color:rgba(201,168,76,0.75); margin-bottom:0.4rem; }
.tag-row { display:flex; flex-wrap:wrap; gap:0.5rem; }
.skill-tag {
    font-family:'Raleway',sans-serif; font-size:0.75rem; font-weight:500;
    letter-spacing:0.1em; text-transform:uppercase; padding:0.32rem 0.9rem; border-radius:2px;
    border:1px solid var(--border); color:rgba(201,168,76,0.75); background:transparent;
    transition: border-color 0.2s, color 0.2s, background 0.2s, box-shadow 0.2s;
}
.skill-tag:hover { border-color:var(--gold); color:var(--gold); background:var(--gold-dim); box-shadow:0 0 12px var(--gold-glow); }

/* Timeline */
.timeline { position:relative; padding-left:2.25rem; }
.timeline::before { content:''; position:absolute; left:0.4rem; top:0.6rem; bottom:0.6rem; width:1px; background:linear-gradient(180deg,var(--gold),transparent); }
.t-item { position:relative; margin-bottom:2.25rem; }
.t-item::before { content:''; position:absolute; left:-1.9rem; top:0.5rem; width:9px; height:9px; border-radius:50%; background:var(--gold); box-shadow:0 0 0 3px var(--bg),0 0 0 5px rgba(201,168,76,0.2); transition:box-shadow 0.2s; }
.t-item:hover::before { box-shadow:0 0 0 3px var(--bg),0 0 0 7px rgba(201,168,76,0.35),0 0 12px var(--gold-glow); }
.t-item-inner { background:var(--bg-card); border:1px solid var(--border); border-radius:4px; padding:1.4rem 1.5rem; transition:border-color 0.22s,background 0.22s,transform 0.18s; }
.t-item-inner:hover { border-color:var(--border-h); background:var(--bg-card-h); transform:translateX(4px); }
.t-title { font-family:'Cormorant Garamond',Georgia,serif; font-size:1.1rem; font-weight:600; color:var(--text); margin-bottom:0.1rem; }
.t-company { font-size:0.85rem; color:var(--gold); letter-spacing:0.04em; margin-bottom:0.25rem; }
.t-duration { font-size:0.75rem; letter-spacing:0.08em; color:rgba(201,168,76,0.5); text-transform:uppercase; margin-bottom:0.75rem; }
.t-desc { font-size:0.92rem; color:var(--muted); line-height:1.75; }
.t-list { margin-top:0.6rem; padding-left:0; list-style:none; }
.t-list li { font-size:0.88rem; color:var(--muted); margin-bottom:0.3rem; padding-left:1rem; position:relative; }
.t-list li::before { content:'◆'; position:absolute; left:0; color:var(--gold); font-size:0.45rem; top:0.3em; }

/* Education */
.edu-card { background:var(--bg-card); border:1px solid var(--border); border-radius:4px; padding:1.25rem 1.5rem; margin-bottom:1rem; transition:border-color 0.22s,background 0.22s; }
.edu-card:hover { border-color:var(--border-h); background:var(--bg-card-h); }
.edu-degree { font-family:'Cormorant Garamond',Georgia,serif; font-size:1.05rem; font-weight:600; color:var(--text); margin-bottom:0.25rem; }
.edu-meta { font-size:0.8rem; letter-spacing:0.05em; color:rgba(201,168,76,0.6); }
.edu-grade { font-size:0.8rem; color:var(--muted); margin-top:0.2rem; }

/* Lux cards */
.lux-card { background:var(--bg-card); border:1px solid var(--border); border-radius:4px; padding:1.25rem 1.5rem; margin-bottom:1rem; transition:border-color 0.22s,background 0.22s,transform 0.18s; }
.lux-card:hover { border-color:var(--border-h); background:var(--bg-card-h); transform:translateX(3px); }
.lux-card h3 { font-family:'Cormorant Garamond',Georgia,serif; font-size:1.1rem; font-weight:600; color:var(--text); margin-bottom:0.2rem; }
.lux-meta { font-size:0.78rem; letter-spacing:0.06em; color:rgba(201,168,76,0.6); text-transform:uppercase; margin-bottom:0.5rem; }
.lux-body { font-size:0.92rem; color:var(--muted); line-height:1.75; }
.lux-list { margin-top:0.5rem; padding-left:0; list-style:none; }
.lux-list li { font-size:0.88rem; color:var(--muted); margin-bottom:0.3rem; padding-left:1rem; position:relative; }
.lux-list li::before { content:'◆'; position:absolute; left:0; color:var(--gold); font-size:0.45rem; top:0.3em; }

.cert-row { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.25rem; padding:0.75rem 1.25rem; margin-bottom:0.5rem; background:var(--bg-card); border:1px solid var(--border); border-radius:4px; }
.cert-name { font-size:0.95rem; color:var(--text); }
.cert-meta { font-size:0.78rem; letter-spacing:0.06em; color:rgba(201,168,76,0.6); }

.tech-tag { font-size:0.72rem; padding:0.2rem 0.5rem; border-radius:2px; background:var(--gold-dim); color:var(--gold); border:1px solid rgba(201,168,76,0.2); letter-spacing:0.06em; }
.philosophy { font-size:1.05rem; font-weight:300; color:rgba(240,232,216,0.72); line-height:1.95; font-style:italic; }
.ip-stats { display:flex; gap:1.5rem; flex-wrap:wrap; margin-top:0.4rem; }
.ip-stat { font-size:0.85rem; color:var(--muted); }
.ip-stat strong { color:var(--gold); }

footer { padding:4rem 0; text-align:center; position:relative; z-index:1; }
.footer-rule { width:120px; height:1px; background:var(--gold); margin:0 auto 1.5rem; opacity:0.35; }
.footer-sig { font-family:'Cormorant Garamond',Georgia,serif; font-size:1.2rem; font-style:italic; font-weight:300; color:rgba(201,168,76,0.6); margin-bottom:0.4rem; }
.footer-text { font-size:0.75rem; letter-spacing:0.1em; color:var(--muted); opacity:0.5; }

@media (max-width:640px) {
    .hero { padding: 4rem 0 3.5rem; }
    .hero-name { font-size: 3rem; }
    .timeline { padding-left: 1.5rem; }
    .timeline::before { left: 0.3rem; }
    .t-item::before { left: -1.25rem; }
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
    return f'<p class="bio">{bio}</p>' if bio else ''


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
            f'<div class="t-item"><div class="t-item-inner">'
            f'<p class="t-title">{exp.get("role","")}</p>'
            f'<p class="t-company">{exp.get("company","")}</p>'
            f'<p class="t-duration">{meta}</p>'
            + (f'<p class="t-desc">{desc}</p>' if desc else '')
            + (f'<ul class="t-list">{points}</ul>' if points else '')
            + f'</div></div>'
        )
    return f'<div class="timeline">{out}</div>' if out else ''


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
            f'<div class="edu-card">'
            f'<p class="edu-degree">{degree}</p>'
            f'<p class="edu-meta">{meta}</p>'
            + (f'<p class="edu-grade">{grade}</p>' if grade else '')
            + f'</div>'
        )
    return out


def _projects(v: dict) -> str:
    items = v.get('projects') or []
    out = ''
    for p in items:
        url = p.get('project_url') or p.get('github_repo') or ''
        link_html = (
            f' <a href="{url}" target="_blank" rel="noopener noreferrer" '
            f'style="font-size:0.72rem;color:var(--gold);text-decoration:none;'
            f'border:1px solid rgba(201,168,76,0.3);padding:0.15rem 0.5rem;border-radius:2px;letter-spacing:0.08em;">Link</a>'
            if url else ''
        )
        tags     = p.get('tech_stack') or p.get('software_used') or []
        tech     = ''.join(f'<span class="tech-tag">{t}</span>' for t in tags)
        resp     = p.get('responsibilities') or []
        outcomes = p.get('measurable_outcomes') or []
        resp_lis    = ''.join(f'<li>{r}</li>' for r in resp)
        outcome_lis = ''.join(f'<li>{o}</li>' for o in outcomes)
        out += (
            f'<div class="lux-card">'
            f'<h3>{p.get("title","")}{link_html}</h3>'
            + (f'<p class="lux-body">{p.get("description","")}</p>' if p.get('description') else '')
            + (f'<div class="tag-row" style="margin-top:0.5rem">{tech}</div>' if tech else '')
            + (f'<ul class="lux-list">{resp_lis}</ul>' if resp_lis else '')
            + (f'<ul class="lux-list">{outcome_lis}</ul>' if outcome_lis else '')
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
            f'<div class="lux-card">'
            f'<h3>{a.get("title","")}</h3>'
            + (f'<p class="lux-body">{a.get("description","")}</p>' if a.get('description') else '')
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
            f'<div class="lux-card">'
            f'<h3>{a.get("title","")}</h3>'
            + (f'<p class="lux-meta">{meta}</p>' if meta else '')
            + f'</div>'
        )
    return out


def _design_philosophy(v: dict) -> str:
    text = v.get('design_philosophy', '')
    return f'<p class="philosophy">{text}</p>' if text else ''


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
        meta_parts = list(filter(None, [ctype,
                                        f'Budget: {budget}' if budget else '',
                                        f'Channels: {channels}' if channels else '']))
        meta = ' · '.join(meta_parts)
        metrics = ''.join(f'<li>{m}</li>' for m in c.get('performance_metrics', []))
        out += (
            f'<div class="lux-card">'
            f'<h3>{c.get("campaign_name","")}</h3>'
            + (f'<p class="lux-meta">{meta}</p>' if meta else '')
            + (f'<ul class="lux-list">{metrics}</ul>' if metrics else '')
            + f'</div>'
        )
    return out


def _financial_modeling(v: dict) -> str:
    items = v.get('financial_modeling') or []
    out = ''
    for fm in items:
        tools = ''.join(f'<span class="tech-tag">{t}</span>' for t in fm.get('tools_used', []))
        out += (
            f'<div class="lux-card">'
            f'<h3>{fm.get("model_type","")}</h3>'
            + (f'<div class="tag-row" style="margin:0.4rem 0">{tools}</div>' if tools else '')
            + (f'<p class="lux-body">{fm.get("outcome","")}</p>' if fm.get('outcome') else '')
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
            f'<div class="lux-card">'
            f'<h3>{ip.get("portfolio_type","")}</h3>'
            f'<div class="ip-stats">'
            + (f'<span class="ip-stat"><strong>AUM:</strong> {aum}</span>' if aum else '')
            + (f'<span class="ip-stat"><strong>Return:</strong> {ret}</span>' if ret else '')
            + f'</div></div>'
        )
    return out


_SECTION_RENDERERS = {
    'experience':            ('Experience',            _experience),
    'projects':              ('Projects',              _projects),
    'skills':                ('Expertise',             _skills),
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
