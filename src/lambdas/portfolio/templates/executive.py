"""
Template: Executive (Premium)
Dark green gradient hero. Gold H2 headings with sliding underline animation.
Timeline-style experience section. Warm off-white body. Formal, refined.
Supports all 4 resume categories (SE, Designer, Marketing, Finance).
"""

from .base import CSP, FONTS_URL, DEFAULT_SECTION_ORDER



def html(v: dict) -> str:
    contact_parts = []
    if v.get('location'): contact_parts.append(v['location'])
    if v.get('phone'):    contact_parts.append(v['phone'])
    contact = ' · '.join(contact_parts)

    links = ''
    if v.get('linkedin_url'):
        links += f'<a href="{v["linkedin_url"]}" target="_blank" rel="noopener noreferrer">LinkedIn</a>'
    if v.get('github_url'):
        links += f'<a href="{v["github_url"]}" target="_blank" rel="noopener noreferrer">GitHub</a>'
    if v.get('portfolio_url'):
        links += f'<a href="{v["portfolio_url"]}" target="_blank" rel="noopener noreferrer">Portfolio</a>'
    if v.get('email'):
        links += f'<a href="mailto:{v["email"]}">Email</a>'

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
    <link rel="stylesheet" href="styles.css">
    <link href="{FONTS_URL}" rel="stylesheet">
</head>
<body>
    <header class="hero">
        <div class="container">
            <p class="hero-label">Professional Portfolio</p>
            <h1>{v['name']}</h1>
            <p class="headline">{v.get('headline', '')}</p>
            <div class="hero-meta">
                <span class="location">{contact}</span>
                <div class="links">{links}</div>
            </div>
        </div>
    </header>

    <main class="container">
        {sections}
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
/* ============================================================
   Executive Template — dark green hero, gold accents, formal
   ============================================================ */

:root {
    --green:        #166534;
    --green-dark:   #14532d;
    --gold:         #b45309;
    --gold-light:   #d97706;
    --text:         #1c1917;
    --text-light:   #57534e;
    --bg:           #fafaf9;
    --bg-alt:       #f5f5f4;
    --border:       #d6d3d1;
    --border-light: #e7e5e4;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.65; color: var(--text); background: var(--bg);
}

.container { max-width: 820px; margin: 0 auto; padding: 0 1.75rem; }

/* ── Hero ─────────────────────────────────────────────────── */
.hero {
    background: linear-gradient(140deg, var(--green-dark) 0%, var(--green) 100%);
    color: white; padding: 5rem 0 4rem;
}
.hero-label {
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.2em;
    text-transform: uppercase; color: rgba(255,255,255,0.55); margin-bottom: 1rem;
}
.hero h1 {
    font-size: 2.75rem; font-weight: 700; letter-spacing: -0.025em;
    margin-bottom: 0.5rem; line-height: 1.15;
}
.headline { font-size: 1.1rem; color: rgba(255,255,255,0.8); margin-bottom: 2rem; font-weight: 300; }
.hero-meta { display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; }
.location { font-size: 0.875rem; color: rgba(255,255,255,0.65); }
.links { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.links a {
    color: white; text-decoration: none; font-size: 0.85rem; font-weight: 500;
    padding: 0.4rem 1rem; border: 1px solid rgba(255,255,255,0.3); border-radius: 4px;
    letter-spacing: 0.02em; transition: all 0.25s;
}
.links a:hover { background: rgba(255,255,255,0.12); border-color: rgba(255,255,255,0.6); transform: translateY(-1px); }

/* ── Sections ─────────────────────────────────────────────── */
main { padding: 4rem 0; }
section { margin-bottom: 4rem; }

h2 {
    font-size: 1.3rem; font-weight: 600; color: var(--gold);
    margin-bottom: 1.75rem; position: relative; padding-bottom: 0.6rem;
    display: inline-block;
}
h2::after {
    content: ''; position: absolute; bottom: 0; left: 0;
    width: 0; height: 2px; background: var(--gold);
    transition: width 0.4s cubic-bezier(0.25,0.46,0.45,0.94);
}
section:hover h2::after { width: 100%; }

/* About */
.about-text { font-size: 1.05rem; color: var(--text-light); line-height: 1.85; max-width: 700px; }

/* Skills */
.skill-group { margin-bottom: 1rem; }
.skill-group-label {
    font-size: 0.78rem; font-weight: 600; color: var(--gold);
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.4rem;
}
.tag-row { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.skill-tag {
    background: var(--bg-alt); color: var(--text-light);
    padding: 0.35rem 0.85rem; border-radius: 4px;
    font-size: 0.85rem; border: 1px solid var(--border); transition: all 0.2s;
}
.skill-tag:hover { border-color: var(--gold); color: var(--gold); background: #fef3c7; }

/* Experience — timeline */
.timeline { position: relative; padding-left: 1.5rem; }
.timeline::before {
    content: ''; position: absolute; left: 0; top: 6px; bottom: 0;
    width: 2px; background: var(--border-light);
}
.exp-item { position: relative; padding-left: 1.5rem; margin-bottom: 2.5rem; transition: padding-left 0.2s; }
.exp-item::before {
    content: ''; position: absolute; left: -1.5rem; top: 6px;
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--border); border: 2px solid var(--bg);
    transition: background 0.2s, box-shadow 0.2s;
}
.exp-item:hover::before { background: var(--gold); box-shadow: 0 0 0 3px rgba(180,83,9,0.15); }
.exp-role { font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 0.1rem; }
.exp-company { font-size: 0.9rem; color: var(--gold); font-weight: 500; }
.exp-meta { font-size: 0.8rem; color: var(--gold); font-weight: 500; margin-bottom: 0.6rem; letter-spacing: 0.04em; }
.exp-desc { color: var(--text-light); font-size: 0.93rem; margin-bottom: 0.4rem; }
.exp-points { padding-left: 1.1rem; }
.exp-points li { color: var(--text-light); font-size: 0.88rem; margin-bottom: 0.2rem; }

/* Education */
.edu-item {
    background: var(--bg-alt); border-radius: 6px; padding: 1.25rem 1.5rem;
    margin-bottom: 1rem; border-left: 3px solid var(--gold); transition: box-shadow 0.2s;
}
.edu-item:hover { box-shadow: 0 4px 12px rgba(180,83,9,0.08); }
.edu-item h3 { font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 0.2rem; }
.edu-meta { font-size: 0.85rem; color: var(--gold); font-weight: 500; }
.edu-grade { font-size: 0.85rem; color: var(--text-light); margin-top: 0.2rem; }

/* Content card — used for projects, campaigns, etc. */
.content-card {
    background: var(--bg-alt); border-radius: 6px; padding: 1.25rem 1.5rem;
    margin-bottom: 1rem; border-left: 3px solid var(--gold); transition: box-shadow 0.2s;
}
.content-card:hover { box-shadow: 0 4px 12px rgba(180,83,9,0.08); }
.content-card h3 { font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 0.25rem; }
.card-meta { font-size: 0.82rem; color: var(--gold); font-weight: 500; margin-bottom: 0.4rem; }
.card-body { font-size: 0.9rem; color: var(--text-light); line-height: 1.7; }
.card-list { padding-left: 1.1rem; margin-top: 0.4rem; }
.card-list li { font-size: 0.875rem; color: var(--text-light); margin-bottom: 0.2rem; }

/* Tech tags */
.tech-tag {
    font-size: 0.75rem; padding: 0.2rem 0.55rem; border-radius: 3px;
    background: #fef3c7; color: var(--gold); border: 1px solid #fde68a;
}

/* Cert rows */
.cert-item {
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 0.25rem;
    padding: 0.75rem 1rem; margin-bottom: 0.5rem;
    background: var(--bg-alt); border-left: 3px solid var(--gold); border-radius: 4px;
}
.cert-name { font-size: 0.95rem; font-weight: 500; color: var(--text); }
.cert-meta { font-size: 0.8rem; color: var(--text-light); }

/* Achievement / Award items */
.ach-item, .award-item {
    padding: 1rem 1.25rem; background: var(--bg-alt); border-radius: 6px;
    border-left: 3px solid var(--gold); margin-bottom: 0.6rem;
}
.ach-item h3, .award-item h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.2rem; }
.ach-item p, .award-item p { font-size: 0.875rem; color: var(--text-light); }
.award-body { font-size: 0.8rem; color: var(--gold); font-weight: 500; margin-bottom: 0.1rem; }

/* Design philosophy */
.philosophy { font-size: 1.05rem; color: var(--text-light); line-height: 1.85; }

/* IP stats */
.ip-stats { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-top: 0.4rem; }
.ip-stat { font-size: 0.85rem; color: var(--text-light); }
.ip-stat strong { color: var(--gold); }

/* Footer */
footer {
    background: var(--bg-alt); border-top: 1px solid var(--border);
    padding: 2rem 0; text-align: center; color: var(--text-light); font-size: 0.8rem;
}

@media (max-width: 640px) {
    .hero h1 { font-size: 2rem; }
    .hero-meta { flex-direction: column; align-items: flex-start; gap: 0.75rem; }
    .timeline { padding-left: 1rem; }
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
    return f'<p class="about-text">{bio}</p>' if bio else ''


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
            f'<div class="exp-item">'
            f'<p class="exp-role">{exp.get("role","")}</p>'
            f'<p class="exp-company">{exp.get("company","")}</p>'
            f'<p class="exp-meta">{meta}</p>'
            + (f'<p class="exp-desc">{desc}</p>' if desc else '')
            + (f'<ul class="exp-points">{points}</ul>' if points else '')
            + f'</div>'
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
            f'<div class="edu-item">'
            f'<h3>{degree}</h3>'
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
            f'style="font-size:0.78rem;color:var(--gold);text-decoration:none;'
            f'border:1px solid var(--gold);padding:0.15rem 0.5rem;border-radius:3px;">Link</a>'
            if url else ''
        )
        tags     = p.get('tech_stack') or p.get('software_used') or []
        tech     = ''.join(f'<span class="tech-tag">{t}</span>' for t in tags)
        resp     = p.get('responsibilities') or []
        outcomes = p.get('measurable_outcomes') or []
        resp_lis    = ''.join(f'<li>{r}</li>' for r in resp)
        outcome_lis = ''.join(f'<li>{o}</li>' for o in outcomes)
        out += (
            f'<div class="content-card">'
            f'<h3>{p.get("title","")}{link_html}</h3>'
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
            f'<div class="cert-item">'
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
            f'<div class="ach-item">'
            f'<h3>{a.get("title","")}</h3>'
            + (f'<p>{a.get("description","")}</p>' if a.get('description') else '')
            + f'</div>'
        )
    return out


def _awards(v: dict) -> str:
    items = v.get('awards') or []
    out = ''
    for a in items:
        body = a.get('awarding_body', '')
        year = a.get('year', '')
        out += (
            f'<div class="award-item">'
            f'<h3>{a.get("title","")}</h3>'
            + (f'<p class="award-body">{body}' + (f' · {year}' if year else '') + '</p>' if body or year else '')
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
        meta_parts = filter(None, [ctype, f'Budget: {budget}' if budget else '', f'Channels: {channels}' if channels else ''])
        meta = ' · '.join(meta_parts)
        metrics = ''.join(f'<li>{m}</li>' for m in c.get('performance_metrics', []))
        out += (
            f'<div class="content-card">'
            f'<h3>{c.get("campaign_name","")}</h3>'
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
            f'<div class="content-card">'
            f'<h3>{fm.get("model_type","")}</h3>'
            + (f'<div class="tag-row" style="margin:0.4rem 0">{tools}</div>' if tools else '')
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
            f'<div class="content-card">'
            f'<h3>{ip.get("portfolio_type","")}</h3>'
            f'<div class="ip-stats">'
            + (f'<span class="ip-stat"><strong>AUM:</strong> {aum}</span>' if aum else '')
            + (f'<span class="ip-stat"><strong>Return:</strong> {ret}</span>' if ret else '')
            + f'</div></div>'
        )
    return out


_SECTION_RENDERERS = {
    'experience':            ('Professional Experience', _experience),
    'projects':              ('Projects',                _projects),
    'skills':                ('Core Competencies',       _skills),
    'education':             ('Education',               _education),
    'certifications':        ('Certifications',          _certifications),
    'achievements':          ('Achievements',            _achievements),
    'awards':                ('Awards',                  _awards),
    'campaigns':             ('Campaigns',               _campaigns),
    'financial_modeling':    ('Financial Modeling',      _financial_modeling),
    'investment_portfolios': ('Investment Portfolios',   _investment_portfolios),
    'design_philosophy':     ('Design Philosophy',       _design_philosophy),
    'software_proficiency':  ('Software Proficiency',    _software_proficiency),
}
