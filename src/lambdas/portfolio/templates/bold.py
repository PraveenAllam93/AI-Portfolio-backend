"""
Template: Bold
Dark slate background, vibrant orange accents. High-impact design.
Glowing skill tags, sliding left-border on experience cards, large typography.

Renders all sections for all 4 categories (software_engineer, designer,
marketing, finance). Empty sections are skipped.
"""

from .base import CSP, FONTS_URL, DEFAULT_SECTION_ORDER


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def html(v: dict) -> str:
    """
    Generate Bold template HTML.
    v is the pre-escaped, pre-validated dict from base.normalize().
    """
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
    {_hero(v)}
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
   Bold Template — dark slate, vibrant orange accent
   ============================================================ */

:root {
    --accent:       #f97316;
    --accent-glow:  rgba(249, 115, 22, 0.35);
    --bg:           #0f172a;
    --bg-card:      #1e293b;
    --bg-card-hov:  #263348;
    --text:         #f1f5f9;
    --text-mid:     #cbd5e1;
    --text-muted:   #94a3b8;
    --border:       #334155;
    --border-hov:   #475569;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.65;
    color: var(--text);
    background: var(--bg);
}

a { color: inherit; text-decoration: none; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.container { max-width: 820px; margin: 0 auto; padding: 0 1.5rem; }

/* ---- Hero ---- */
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
    margin-bottom: 0.5rem;
    line-height: 1.1;
}
.hero-headline {
    font-size: 1.15rem;
    color: var(--text-muted);
    margin-bottom: 1.25rem;
}
.hero-meta {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 2rem;
}
.hero-meta-text { font-size: 0.875rem; color: var(--text-muted); }
.social-links { display: flex; gap: 0.6rem; flex-wrap: wrap; }
.social-links a {
    color: var(--text);
    text-decoration: none;
    font-size: 0.8rem;
    font-weight: 500;
    padding: 0.35rem 0.9rem;
    border: 1px solid var(--border);
    border-radius: 5px;
    transition: all 0.25s;
}
.social-links a:hover {
    border-color: var(--accent);
    color: var(--accent);
    box-shadow: 0 0 12px var(--accent-glow);
    transform: translateY(-1px);
}

/* ---- Main ---- */
main { padding: 4rem 0; }
section { margin-bottom: 4rem; }

h2 {
    font-size: 1.1rem;
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
.h2-accent { color: var(--accent); font-weight: 700; font-size: 1rem; }

/* ---- About ---- */
.about-text {
    font-size: 1.05rem;
    color: var(--text-muted);
    line-height: 1.8;
    max-width: 680px;
}

/* ---- Skills ---- */
.skill-group { margin-bottom: 1.1rem; }
.skill-group:last-child { margin-bottom: 0; }
.skill-group-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
}
.tag-row { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.skill-tag {
    background: transparent;
    color: var(--accent);
    padding: 0.3rem 0.8rem;
    border-radius: 4px;
    font-size: 0.82rem;
    font-weight: 500;
    border: 1px solid var(--accent);
    transition: all 0.2s;
    cursor: default;
}
.skill-tag:hover {
    background: var(--accent);
    color: var(--bg);
    box-shadow: 0 0 14px var(--accent-glow);
}

/* ---- Experience ---- */
.timeline-item {
    background: var(--bg-card);
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    border-left: 3px solid var(--border);
    transition: border-left-color 0.3s, background 0.3s, transform 0.2s;
}
.timeline-item:last-child { margin-bottom: 0; }
.timeline-item:hover {
    border-left-color: var(--accent);
    background: var(--bg-card-hov);
    transform: translateX(3px);
}
.tl-header {
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-bottom: 0.25rem;
}
.tl-header h3 { font-size: 1rem; font-weight: 600; color: var(--text); }
.tl-company { font-size: 0.9rem; color: var(--text-muted); }
.tl-company::before { content: '·'; margin-right: 0.5rem; color: var(--border-hov); }
.tl-meta {
    font-size: 0.77rem;
    color: var(--accent);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
}
.tl-desc { font-size: 0.95rem; color: var(--text-muted); margin-bottom: 0.4rem; }
.tl-points {
    margin-top: 0.4rem;
    padding-left: 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}
.tl-points li { font-size: 0.875rem; color: var(--text-muted); }
.exp-extra { font-size: 0.82rem; color: var(--text-muted); margin-top: 0.4rem; }
.exp-extra strong { color: var(--text-mid); font-weight: 500; }

/* ---- Projects ---- */
.project-card {
    background: var(--bg-card);
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    border-left: 3px solid var(--border);
    transition: border-left-color 0.3s, background 0.3s, transform 0.2s;
}
.project-card:last-child { margin-bottom: 0; }
.project-card:hover {
    border-left-color: var(--accent);
    background: var(--bg-card-hov);
    transform: translateX(3px);
}
.proj-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
}
.proj-header h3 { font-size: 1rem; font-weight: 600; color: var(--text); }
.proj-links { display: flex; gap: 0.4rem; }
.proj-link {
    font-size: 0.775rem;
    font-weight: 500;
    padding: 0.2rem 0.55rem;
    border: 1px solid var(--border-hov);
    border-radius: 4px;
    color: var(--text-muted);
    transition: all 0.2s;
}
.proj-link:hover {
    border-color: var(--accent);
    color: var(--accent);
    box-shadow: 0 0 8px var(--accent-glow);
}
.proj-category {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 0.4rem;
}
.design-concept {
    font-size: 0.9rem;
    color: var(--text-muted);
    font-style: italic;
    margin-bottom: 0.4rem;
}
.proj-desc { font-size: 0.9rem; color: var(--text-muted); margin-bottom: 0.6rem; }
.tech-tag {
    font-size: 0.775rem;
    color: var(--text-muted);
    padding: 0.2rem 0.5rem;
    border-radius: 3px;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
}
.outcomes {
    margin-top: 0.5rem;
    padding-left: 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}
.outcomes li { font-size: 0.85rem; color: var(--text-muted); }

/* ---- Design Philosophy ---- */
.philosophy {
    font-size: 1.05rem;
    color: var(--text-muted);
    font-style: italic;
    line-height: 1.8;
    max-width: 680px;
    padding-left: 1rem;
    border-left: 2px solid var(--accent);
}

/* ---- Education ---- */
.edu-item {
    background: var(--bg-card);
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
    border-left: 3px solid var(--border);
    transition: border-left-color 0.3s, transform 0.2s;
}
.edu-item:last-child { margin-bottom: 0; }
.edu-item:hover { border-left-color: var(--accent); transform: translateX(3px); }
.edu-item h3 { font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 0.25rem; }
.edu-meta { font-size: 0.82rem; color: var(--accent); margin-bottom: 0.2rem; }
.edu-grade { font-size: 0.8rem; color: var(--text-muted); }

/* ---- Certifications ---- */
.cert-item {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
}
.cert-item:last-child { border-bottom: none; }
.cert-item h3 { font-size: 0.925rem; font-weight: 500; color: var(--text); }
.cert-item a { color: var(--accent); transition: opacity 0.15s; }
.cert-item a:hover { opacity: 0.75; }
.cert-meta { font-size: 0.8rem; color: var(--text-muted); white-space: nowrap; }

/* ---- Achievements ---- */
.achievement-item {
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
}
.achievement-item:last-child { border-bottom: none; }
.ach-header {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-bottom: 0.2rem;
}
.ach-header h3 { font-size: 0.95rem; font-weight: 600; color: var(--text); }
.ach-header a { color: var(--accent); }
.ach-year { font-size: 0.775rem; color: var(--text-muted); }
.ach-desc { font-size: 0.875rem; color: var(--text-muted); }

/* ---- Awards (Designer) ---- */
.award-item {
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
}
.award-item:last-child { border-bottom: none; }
.award-header {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-bottom: 0.2rem;
}
.award-header h3 { font-size: 0.95rem; font-weight: 600; color: var(--text); }
.award-header a { color: var(--accent); }
.award-year { font-size: 0.775rem; color: var(--text-muted); }
.award-body { font-size: 0.875rem; color: var(--text-muted); }

/* ---- Campaigns (Marketing) ---- */
.campaign-card {
    background: var(--bg-card);
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
    border-left: 3px solid var(--border);
    transition: border-left-color 0.3s, transform 0.2s;
}
.campaign-card:last-child { margin-bottom: 0; }
.campaign-card:hover { border-left-color: var(--accent); transform: translateX(3px); }
.campaign-card h3 { font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 0.3rem; }
.camp-meta {
    font-size: 0.77rem;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
}
.camp-channels { font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.4rem; }
.camp-metrics {
    padding-left: 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    margin-top: 0.3rem;
}
.camp-metrics li { font-size: 0.85rem; color: var(--text-muted); }

/* ---- Financial Modeling (Finance) ---- */
.fm-item {
    background: var(--bg-card);
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
    border-left: 3px solid var(--border);
    transition: border-left-color 0.3s, transform 0.2s;
}
.fm-item:last-child { margin-bottom: 0; }
.fm-item:hover { border-left-color: var(--accent); transform: translateX(3px); }
.fm-item h3 { font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 0.3rem; }
.fm-tools { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem; }
.fm-outcome { font-size: 0.9rem; color: var(--text-mid); }

/* ---- Investment Portfolios (Finance) ---- */
.ip-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 0.75rem;
}
.ip-card {
    background: var(--bg-card);
    padding: 1.1rem;
    border-radius: 8px;
    border: 1px solid var(--border);
    transition: border-color 0.2s;
}
.ip-card:hover { border-color: var(--accent); }
.ip-card h3 { font-size: 0.9rem; font-weight: 600; color: var(--text); margin-bottom: 0.4rem; }
.ip-meta, .ip-return { font-size: 0.825rem; color: var(--text-muted); margin-top: 0.2rem; }

/* ---- Footer ---- */
footer {
    border-top: 1px solid var(--border);
    padding: 2.5rem 0;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.85rem;
}

/* ---- Responsive ---- */
@media (max-width: 640px) {
    .hero h1 { font-size: 2.25rem; }
    .hero-headline { font-size: 1rem; }
    .hero-meta { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
    .proj-header { flex-direction: column; gap: 0.5rem; }
    .tl-header { flex-direction: column; gap: 0.1rem; }
    .tl-company::before { display: none; }
    .ip-grid { grid-template-columns: 1fr; }
}
"""


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

def _hero(v: dict) -> str:
    headline_html = f'<p class="hero-headline">{v["headline"]}</p>' if v.get('headline') else ''

    meta_parts = list(filter(None, [v.get('location'), v.get('phone')]))
    meta_html = (
        f'<span class="hero-meta-text">{" · ".join(meta_parts)}</span>'
        if meta_parts else ''
    )
    links_html = _social_links(v)
    social_html = f'<div class="social-links">{links_html}</div>' if links_html else ''
    meta_row = f'<div class="hero-meta">{meta_html}{social_html}</div>' if (meta_html or social_html) else ''

    return (
        f'<header class="hero">'
        f'<div class="container">'
        f'<div class="hero-badge">Portfolio</div>'
        f'<h1>{v["name"]}</h1>'
        f'{headline_html}'
        f'{meta_row}'
        f'</div>'
        f'</header>'
    )


def _social_links(v: dict) -> str:
    items = [
        ('linkedin_url',  'LinkedIn'),
        ('github_url',    'GitHub'),
        ('portfolio_url', 'Portfolio'),
        ('twitter_url',   'Twitter'),
    ]
    links = ''
    for key, label in items:
        if v.get(key):
            links += f'<a href="{v[key]}" target="_blank" rel="noopener noreferrer">{label}</a>'
    if v.get('email'):
        links += f'<a href="mailto:{v["email"]}">Email</a>'
    return links


# ---------------------------------------------------------------------------
# Section wrapper
# ---------------------------------------------------------------------------

def _section(title: str, content: str) -> str:
    if not content:
        return ''
    return (
        f'<section>'
        f'<h2><span class="h2-accent">//</span> {title}</h2>'
        f'{content}'
        f'</section>'
    )


# ---------------------------------------------------------------------------
# Common section renderers
# ---------------------------------------------------------------------------

def _about(v: dict) -> str:
    return f'<p class="about-text">{v["bio"]}</p>' if v.get('bio') else ''


def _skills(v: dict) -> str:
    groups = v.get('skill_groups') or []
    if not groups:
        return ''
    parts = []
    for g in groups:
        tags = ''.join(f'<span class="skill-tag">{s}</span>' for s in g['skills'])
        label = f'<p class="skill-group-label">{g["category"]}</p>' if g.get('category') else ''
        parts.append(f'<div class="skill-group">{label}<div class="tag-row">{tags}</div></div>')
    return ''.join(parts)


def _experience(v: dict) -> str:
    items = v.get('experience') or []
    if not items:
        return ''
    parts = []
    for exp in items:
        meta_parts = list(filter(None, [exp.get('duration'), exp.get('location')]))
        kp_html = ''.join(f'<li>{k}</li>' for k in (exp.get('key_points') or []))

        extra = ''
        if exp.get('channels_managed'):
            channels = ', '.join(exp['channels_managed'])
            extra += f'<p class="exp-extra"><strong>Channels:</strong> {channels}</p>'
        if exp.get('financial_metrics_managed'):
            metrics = ', '.join(exp['financial_metrics_managed'])
            extra += f'<p class="exp-extra"><strong>Key metrics:</strong> {metrics}</p>'

        company_html = f'<span class="tl-company">{exp["company"]}</span>' if exp.get('company') else ''
        meta_html    = f'<p class="tl-meta">{" · ".join(meta_parts)}</p>' if meta_parts else ''
        desc_html    = f'<p class="tl-desc">{exp["description"]}</p>' if exp.get('description') else ''
        kp_list_html = f'<ul class="tl-points">{kp_html}</ul>' if kp_html else ''

        parts.append(
            f'<div class="timeline-item">'
            f'<div class="tl-header"><h3>{exp["role"]}</h3>{company_html}</div>'
            f'{meta_html}{desc_html}{kp_list_html}{extra}'
            f'</div>'
        )
    return ''.join(parts)


def _education(v: dict) -> str:
    items = v.get('education') or []
    if not items:
        return ''
    parts = []
    for edu in items:
        degree_field = ' in '.join(filter(None, [edu.get('degree'), edu.get('field_of_study')]))
        inst_parts   = list(filter(None, [edu.get('institution'), edu.get('year_range')]))
        grade_html   = f'<p class="edu-grade">{edu["grade_or_score"]}</p>' if edu.get('grade_or_score') else ''
        meta_html    = f'<p class="edu-meta">{" · ".join(inst_parts)}</p>' if inst_parts else ''

        parts.append(
            f'<div class="edu-item">'
            f'<h3>{degree_field or edu.get("institution", "")}</h3>'
            f'{meta_html}{grade_html}'
            f'</div>'
        )
    return ''.join(parts)


def _certifications(v: dict) -> str:
    items = v.get('certifications') or []
    if not items:
        return ''
    parts = []
    for c in items:
        name = (
            f'<a href="{c["url"]}" target="_blank" rel="noopener noreferrer">{c["name"]}</a>'
            if c.get('url') else c['name']
        )
        meta = ' · '.join(filter(None, [c.get('issuer'), c.get('year')]))
        cert_meta_html = f'<span class="cert-meta">{meta}</span>' if meta else ''
        parts.append(f'<div class="cert-item"><h3>{name}</h3>{cert_meta_html}</div>')
    return ''.join(parts)


def _achievements(v: dict) -> str:
    items = v.get('achievements') or []
    if not items:
        return ''
    parts = []
    for a in items:
        title    = (
            f'<a href="{a["url"]}" target="_blank" rel="noopener noreferrer">{a["title"]}</a>'
            if a.get('url') else a['title']
        )
        year_html = f'<span class="ach-year">{a["year"]}</span>' if a.get('year') else ''
        desc_html = f'<p class="ach-desc">{a["description"]}</p>' if a.get('description') else ''
        parts.append(
            f'<div class="achievement-item">'
            f'<div class="ach-header"><h3>{title}</h3>{year_html}</div>'
            f'{desc_html}'
            f'</div>'
        )
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Software Engineer section renderers
# ---------------------------------------------------------------------------

def _projects(v: dict) -> str:
    items = v.get('projects') or []
    if not items:
        return ''
    parts = []
    for p in items:
        link_items = [(p.get('github_repo'), 'GitHub'), (p.get('project_url'), 'Live')]
        links_html = ''.join(
            f'<a href="{url}" class="proj-link" target="_blank" rel="noopener noreferrer">{label}</a>'
            for url, label in link_items if url
        )
        tag_source   = p.get('tech_stack') or p.get('software_used') or []
        tags_html    = ''.join(f'<span class="tech-tag">{t}</span>' for t in tag_source)
        category_html = f'<span class="proj-category">{p["project_category"]}</span>' if p.get('project_category') else ''
        concept_html  = f'<p class="design-concept">{p["design_concept"]}</p>' if p.get('design_concept') else ''
        resp_html     = ''.join(f'<li>{r}</li>' for r in (p.get('responsibilities') or []))
        outcomes_html = ''.join(f'<li>{o}</li>' for o in (p.get('measurable_outcomes') or []))

        proj_links_div = f'<div class="proj-links">{links_html}</div>' if links_html else ''
        proj_desc_html = f'<p class="proj-desc">{p["description"]}</p>' if p.get('description') else ''
        tags_row_html  = f'<div class="tag-row">{tags_html}</div>' if tags_html else ''
        resp_list      = f'<ul class="outcomes">{resp_html}</ul>' if resp_html else ''
        outcomes_list  = f'<ul class="outcomes">{outcomes_html}</ul>' if outcomes_html else ''

        parts.append(
            f'<div class="project-card">'
            f'<div class="proj-header"><h3>{p["title"]}</h3>{proj_links_div}</div>'
            f'{category_html}{concept_html}{proj_desc_html}{tags_row_html}{resp_list}{outcomes_list}'
            f'</div>'
        )
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Designer section renderers
# ---------------------------------------------------------------------------

def _design_philosophy(v: dict) -> str:
    ph = v.get('design_philosophy') or ''
    return f'<p class="philosophy">{ph}</p>' if ph else ''


def _software_proficiency(v: dict) -> str:
    items = v.get('software_proficiency') or []
    if not items:
        return ''
    tags = ''.join(f'<span class="skill-tag">{s}</span>' for s in items)
    return f'<div class="tag-row">{tags}</div>'


def _awards(v: dict) -> str:
    items = v.get('awards') or []
    if not items:
        return ''
    parts = []
    for a in items:
        title    = (
            f'<a href="{a["url"]}" target="_blank" rel="noopener noreferrer">{a["title"]}</a>'
            if a.get('url') else a['title']
        )
        year_html = f'<span class="award-year">{a["year"]}</span>' if a.get('year') else ''
        body_html = f'<p class="award-body">{a["awarding_body"]}</p>' if a.get('awarding_body') else ''
        parts.append(
            f'<div class="award-item">'
            f'<div class="award-header"><h3>{title}</h3>{year_html}</div>'
            f'{body_html}'
            f'</div>'
        )
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Marketing section renderers
# ---------------------------------------------------------------------------

def _campaigns(v: dict) -> str:
    items = v.get('campaigns') or []
    if not items:
        return ''
    parts = []
    for c in items:
        meta_parts = list(filter(None, [
            c.get('campaign_type'),
            f'Budget: {c["budget"]}' if c.get('budget') else '',
        ]))
        channels     = ', '.join(c.get('channels_used') or [])
        metrics_html = ''.join(f'<li>{m}</li>' for m in (c.get('performance_metrics') or []))

        camp_meta_html    = f'<p class="camp-meta">{" · ".join(meta_parts)}</p>' if meta_parts else ''
        camp_channels_html = f'<p class="camp-channels">Channels: {channels}</p>' if channels else ''
        camp_metrics_html  = f'<ul class="camp-metrics">{metrics_html}</ul>' if metrics_html else ''

        parts.append(
            f'<div class="campaign-card">'
            f'<h3>{c["campaign_name"]}</h3>'
            f'{camp_meta_html}{camp_channels_html}{camp_metrics_html}'
            f'</div>'
        )
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Finance section renderers
# ---------------------------------------------------------------------------

def _financial_modeling(v: dict) -> str:
    items = v.get('financial_modeling') or []
    if not items:
        return ''
    parts = []
    for fm in items:
        tools      = ', '.join(fm.get('tools_used') or [])
        tools_html   = f'<p class="fm-tools">Tools: {tools}</p>' if tools else ''
        outcome_html = f'<p class="fm-outcome">{fm["outcome"]}</p>' if fm.get('outcome') else ''
        parts.append(
            f'<div class="fm-item">'
            f'<h3>{fm["model_type"]}</h3>'
            f'{tools_html}{outcome_html}'
            f'</div>'
        )
    return ''.join(parts)


def _investment_portfolios(v: dict) -> str:
    items = v.get('investment_portfolios') or []
    if not items:
        return ''

    def _card(ip: dict) -> str:
        aum_html = f'<p class="ip-meta">AUM: {ip["assets_under_management"]}</p>' if ip.get('assets_under_management') else ''
        ret_html = f'<p class="ip-return">Return: {ip["performance_return"]}</p>' if ip.get('performance_return') else ''
        return f'<div class="ip-card"><h3>{ip["portfolio_type"]}</h3>{aum_html}{ret_html}</div>'

    return f'<div class="ip-grid">{"".join(_card(ip) for ip in items)}</div>'


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
