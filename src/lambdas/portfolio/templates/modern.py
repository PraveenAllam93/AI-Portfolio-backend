"""
Template: Modern
Clean blue gradient header, Inter typography, single-column layout.
Smooth hover transitions on links and section cards.
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
            <h1>{v['name']}</h1>
            <p class="headline">{v.get('headline', '')}</p>
            <p class="location">{contact}</p>
            <div class="links">{links}</div>
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
   Modern Template — blue gradient, Inter, single-column
   ============================================================ */

:root {
    --primary:      #2563eb;
    --primary-dark: #1d4ed8;
    --text:         #1f2937;
    --text-light:   #6b7280;
    --bg:           #ffffff;
    --bg-alt:       #f9fafb;
    --border:       #e5e7eb;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.6;
    color: var(--text);
    background: var(--bg);
}

.container { max-width: 820px; margin: 0 auto; padding: 0 1.5rem; }

/* ── Hero ─────────────────────────────────────────────────── */
.hero {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
    padding: 4.5rem 0;
    text-align: center;
}
.hero h1 {
    font-size: 2.75rem; font-weight: 700;
    letter-spacing: -0.02em; margin-bottom: 0.5rem;
}
.headline { font-size: 1.2rem; opacity: 0.9; margin-bottom: 0.4rem; }
.location { opacity: 0.75; margin-bottom: 1.75rem; font-size: 0.95rem; }
.links { display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; }
.links a {
    color: white; text-decoration: none;
    padding: 0.45rem 1.1rem;
    border: 1px solid rgba(255,255,255,0.35); border-radius: 6px;
    font-size: 0.9rem;
    transition: background 0.2s, border-color 0.2s, transform 0.2s;
}
.links a:hover {
    background: rgba(255,255,255,0.15); border-color: rgba(255,255,255,0.6);
    transform: translateY(-1px);
}

/* ── Sections ─────────────────────────────────────────────── */
main { padding: 3.5rem 0; }
section { margin-bottom: 3.5rem; }
h2 {
    font-size: 1.4rem; font-weight: 600; margin-bottom: 1.5rem;
    padding-bottom: 0.5rem; border-bottom: 2px solid var(--primary);
    color: var(--text);
}

/* About */
.about-text { font-size: 1.05rem; color: var(--text-light); line-height: 1.75; }

/* Skills */
.skill-group { margin-bottom: 1rem; }
.skill-group-label {
    font-size: 0.8rem; font-weight: 600; color: var(--primary);
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.4rem;
}
.tag-row { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.skill-tag {
    background: var(--bg-alt); color: var(--text);
    padding: 0.4rem 0.9rem; border-radius: 20px;
    font-size: 0.875rem; border: 1px solid var(--border);
    transition: border-color 0.2s, background 0.2s;
}
.skill-tag:hover { border-color: var(--primary); background: #eff6ff; }

/* Experience */
.exp-item {
    margin-bottom: 2rem; padding: 1.5rem;
    background: var(--bg-alt); border-radius: 8px;
    border-left: 3px solid var(--primary);
    transition: box-shadow 0.2s, transform 0.2s;
}
.exp-item:hover { box-shadow: 0 4px 16px rgba(37,99,235,0.1); transform: translateX(2px); }
.exp-header {
    display: flex; justify-content: space-between;
    align-items: baseline; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.2rem;
}
.exp-role { font-size: 1.05rem; font-weight: 600; }
.exp-company { font-size: 0.95rem; color: var(--primary); font-weight: 500; }
.exp-meta { color: var(--text-light); font-size: 0.85rem; margin-bottom: 0.5rem; }
.exp-desc { color: var(--text-light); font-size: 0.95rem; margin-bottom: 0.5rem; }
.exp-points { padding-left: 1.25rem; }
.exp-points li { margin-bottom: 0.25rem; color: var(--text-light); font-size: 0.9rem; }

/* Education */
.edu-item {
    background: var(--bg-alt); border-radius: 8px;
    padding: 1.25rem 1.5rem; margin-bottom: 1rem;
    border-left: 3px solid var(--primary);
}
.edu-item h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.2rem; }
.edu-meta { color: var(--text-light); font-size: 0.85rem; }
.edu-grade { color: var(--primary); font-size: 0.85rem; font-weight: 500; margin-top: 0.2rem; }

/* Projects */
.project-card {
    background: var(--bg-alt); border-radius: 8px;
    padding: 1.25rem 1.5rem; margin-bottom: 1rem;
    border-left: 3px solid var(--primary);
    transition: box-shadow 0.2s;
}
.project-card:hover { box-shadow: 0 4px 16px rgba(37,99,235,0.1); }
.proj-header {
    display: flex; justify-content: space-between;
    align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.4rem;
}
.proj-header h3 { font-size: 1rem; font-weight: 600; }
.proj-link {
    font-size: 0.8rem; color: var(--primary); text-decoration: none;
    border: 1px solid var(--primary); padding: 0.2rem 0.6rem; border-radius: 4px;
}
.proj-desc { font-size: 0.9rem; color: var(--text-light); margin-bottom: 0.5rem; }
.tech-tag {
    font-size: 0.75rem; padding: 0.25rem 0.6rem;
    background: #eff6ff; color: var(--primary);
    border-radius: 4px; border: 1px solid #bfdbfe;
}
.outcomes { padding-left: 1.25rem; margin-top: 0.4rem; }
.outcomes li { font-size: 0.85rem; color: var(--text-light); margin-bottom: 0.2rem; }

/* Certifications */
.cert-item {
    padding: 0.75rem 1rem; background: var(--bg-alt); border-radius: 6px;
    border-left: 3px solid var(--primary); margin-bottom: 0.5rem;
    display: flex; justify-content: space-between;
    align-items: center; flex-wrap: wrap; gap: 0.25rem;
}
.cert-name { font-size: 0.95rem; font-weight: 500; }
.cert-meta { font-size: 0.8rem; color: var(--text-light); }

/* Achievements & Awards */
.achievement-item, .award-item {
    padding: 1rem 1.25rem; background: var(--bg-alt);
    border-radius: 6px; border-left: 3px solid var(--primary); margin-bottom: 0.6rem;
}
.achievement-item h3, .award-item h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.2rem; }
.achievement-item p, .award-item p { font-size: 0.875rem; color: var(--text-light); }
.award-body { font-size: 0.8rem; color: var(--primary); font-weight: 500; margin-top: 0.1rem; }

/* Design Philosophy */
.philosophy {
    font-size: 1.05rem; color: var(--text-light); line-height: 1.85;
    padding: 1.25rem 1.5rem; background: var(--bg-alt);
    border-radius: 8px; border-left: 3px solid var(--primary);
}

/* Software Proficiency */
.proficiency-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.6rem 1rem; background: var(--bg-alt);
    border-radius: 6px; margin-bottom: 0.4rem;
}
.proficiency-tool { font-size: 0.95rem; font-weight: 500; }

/* Campaigns */
.campaign-card {
    background: var(--bg-alt); border-radius: 8px;
    padding: 1.25rem 1.5rem; margin-bottom: 1rem;
    border-left: 3px solid var(--primary);
}
.campaign-card h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem; }
.campaign-type { font-size: 0.8rem; color: var(--primary); font-weight: 500; margin-bottom: 0.4rem; }
.campaign-desc { font-size: 0.9rem; color: var(--text-light); margin-bottom: 0.4rem; }
.campaign-metrics { padding-left: 1.25rem; }
.campaign-metrics li { font-size: 0.85rem; color: var(--text-light); margin-bottom: 0.2rem; }

/* Financial Modeling */
.fm-item {
    background: var(--bg-alt); border-radius: 6px;
    padding: 1rem 1.25rem; border-left: 3px solid var(--primary); margin-bottom: 0.6rem;
}
.fm-item h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.3rem; }
.fm-tools { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.3rem; }
.fm-outcome { font-size: 0.875rem; color: var(--text-light); }

/* Investment Portfolios */
.ip-item {
    background: var(--bg-alt); border-radius: 6px;
    padding: 1rem 1.25rem; border-left: 3px solid var(--primary); margin-bottom: 0.6rem;
}
.ip-item h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.25rem; }
.ip-stats { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-top: 0.3rem; }
.ip-stat { font-size: 0.85rem; color: var(--text-light); }
.ip-stat strong { color: var(--primary); }

/* Footer */
footer {
    background: var(--bg-alt); padding: 2rem 0; text-align: center;
    color: var(--text-light); font-size: 0.85rem; border-top: 1px solid var(--border);
}

@media (max-width: 640px) {
    .hero h1 { font-size: 2rem; }
    .headline { font-size: 1.05rem; }
    h2 { font-size: 1.2rem; }
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
            f'<div class="exp-header">'
            f'<h3 class="exp-role">{exp.get("role","")}</h3>'
            f'<span class="exp-company">{exp.get("company","")}</span>'
            f'</div>'
            f'<p class="exp-meta">{meta}</p>'
            + (f'<p class="exp-desc">{desc}</p>' if desc else '')
            + (f'<ul class="exp-points">{points}</ul>' if points else '')
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
        link = (
            f'<a href="{url}" class="proj-link" target="_blank" rel="noopener noreferrer">Link</a>'
            if url else ''
        )
        tags     = p.get('tech_stack') or p.get('software_used') or []
        tech     = ''.join(f'<span class="tech-tag">{t}</span>' for t in tags)
        resp     = p.get('responsibilities') or []
        outcomes = p.get('measurable_outcomes') or []
        resp_lis    = ''.join(f'<li>{r}</li>' for r in resp)
        outcome_lis = ''.join(f'<li>{o}</li>' for o in outcomes)
        out += (
            f'<div class="project-card">'
            f'<div class="proj-header"><h3>{p.get("title","")}</h3>{link}</div>'
            + (f'<p class="proj-desc">{p.get("description","")}</p>' if p.get('description') else '')
            + (f'<div class="tag-row">{tech}</div>' if tech else '')
            + (f'<ul class="outcomes">{resp_lis}</ul>' if resp_lis else '')
            + (f'<ul class="outcomes">{outcome_lis}</ul>' if outcome_lis else '')
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
            f'<div class="achievement-item">'
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
            + (f'<p>{a.get("description","")}</p>' if a.get('description') else '')
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
        metrics = ''.join(f'<li>{m}</li>' for m in c.get('performance_metrics', []))
        channels = ', '.join(c.get('channels_used', []))
        desc_parts = []
        if channels:       desc_parts.append(f'Channels: {channels}')
        if c.get('budget'): desc_parts.append(f'Budget: {c["budget"]}')
        desc = ' · '.join(desc_parts)
        out += (
            f'<div class="campaign-card">'
            f'<h3>{c.get("campaign_name","")}</h3>'
            + (f'<p class="campaign-type">{ctype}</p>' if ctype else '')
            + (f'<p class="campaign-desc">{desc}</p>' if desc else '')
            + (f'<ul class="campaign-metrics">{metrics}</ul>' if metrics else '')
            + f'</div>'
        )
    return out


def _financial_modeling(v: dict) -> str:
    items = v.get('financial_modeling') or []
    out = ''
    for fm in items:
        tools = ''.join(f'<span class="tech-tag">{t}</span>' for t in fm.get('tools_used', []))
        out += (
            f'<div class="fm-item">'
            f'<h3>{fm.get("model_type","")}</h3>'
            + (f'<div class="fm-tools tag-row">{tools}</div>' if tools else '')
            + (f'<p class="fm-outcome">{fm.get("outcome","")}</p>' if fm.get('outcome') else '')
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
            f'<div class="ip-item">'
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
