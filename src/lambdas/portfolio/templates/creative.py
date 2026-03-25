"""
Template: Creative
Two-column layout — teal sidebar (contact + skills) + white main content.
Card lift hover effects. Mobile: sidebar stacks above content.

Renders all sections for all 4 categories (software_engineer, designer,
marketing, finance). Empty sections are skipped.
"""

from .base import CSP, FONTS_URL, DEFAULT_SECTION_ORDER


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def html(v: dict) -> str:
    """
    Generate Creative template HTML.
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
    main_sections = '\n'.join(filter(None, [about_html, content_sections]))

    sidebar_skills  = _sidebar_skills(v)
    sidebar_contact = _sidebar_contact(v)
    avatar_letter   = v['name'][0].upper() if v.get('name') else 'P'

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
            <div class="avatar">{avatar_letter}</div>
            <h1>{v['name']}</h1>
            {f'<p class="sidebar-title">{v["headline"]}</p>' if v.get('headline') else ''}
        </div>

        {sidebar_contact}
        {sidebar_skills}
    </aside>

    <!-- MAIN CONTENT -->
    <main class="content">
        {main_sections}
        <footer>
            <p>Generated with AI Portfolio Builder</p>
        </footer>
    </main>

</div>
</body>
</html>"""


def css() -> str:
    return """
/* ============================================================
   Creative Template — teal sidebar + white content area
   ============================================================ */

:root {
    --teal:         #0d9488;
    --teal-dark:    #0f766e;
    --teal-light:   #14b8a6;
    --teal-pale:    #ccfbf1;
    --text:         #1f2937;
    --text-mid:     #374151;
    --text-light:   #6b7280;
    --text-faint:   #9ca3af;
    --bg:           #f9fafb;
    --bg-card:      #ffffff;
    --border:       #e5e7eb;
    --border-dark:  #d1d5db;
    --sidebar-text: rgba(255,255,255,0.92);
    --sidebar-muted: rgba(255,255,255,0.65);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.65;
    background: var(--bg);
    color: var(--text);
}

a { color: inherit; text-decoration: none; }
a:focus-visible { outline: 2px solid var(--teal); outline-offset: 2px; }

/* ---- Two-column layout ---- */
.layout { display: flex; min-height: 100vh; }

/* ============================================================
   SIDEBAR
   ============================================================ */
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
    scrollbar-width: thin;
    scrollbar-color: rgba(255,255,255,0.2) transparent;
}

/* Avatar */
.sidebar-profile { margin-bottom: 2rem; }
.avatar {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: rgba(255,255,255,0.18);
    border: 2px solid rgba(255,255,255,0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.4rem;
    font-weight: 700;
    color: white;
    margin-bottom: 0.9rem;
}
.sidebar h1 {
    font-size: 1.25rem;
    font-weight: 700;
    color: white;
    margin-bottom: 0.25rem;
    line-height: 1.2;
}
.sidebar-title { font-size: 0.825rem; color: var(--sidebar-muted); line-height: 1.4; }

/* Sidebar section blocks */
.sidebar-section { margin-bottom: 1.75rem; }
.sidebar-heading {
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--teal-light);
    margin-bottom: 0.65rem;
}

/* Contact rows */
.contact-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.4rem;
    font-size: 0.82rem;
    color: var(--sidebar-text);
}
.contact-icon { font-size: 0.75rem; opacity: 0.7; flex-shrink: 0; }
.contact-row a {
    color: var(--sidebar-text);
    word-break: break-all;
    transition: color 0.15s;
}
.contact-row a:hover { color: white; }

/* Sidebar social links */
.sidebar-links { display: flex; flex-direction: column; gap: 0.35rem; margin-top: 0.25rem; }
.sidebar-link {
    color: var(--sidebar-text);
    font-size: 0.82rem;
    font-weight: 500;
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.15);
    display: flex;
    align-items: center;
    gap: 0.4rem;
    transition: color 0.15s, border-color 0.15s;
}
.sidebar-link:hover { color: white; border-bottom-color: rgba(255,255,255,0.5); }

/* Skills in sidebar */
.sidebar-skill-group { margin-bottom: 0.9rem; }
.sidebar-skill-group:last-child { margin-bottom: 0; }
.sidebar-skill-label {
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--teal-light);
    margin-bottom: 0.35rem;
}
.sidebar-tags { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.skill-tag {
    background: rgba(255,255,255,0.15);
    color: white;
    padding: 0.2rem 0.55rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 500;
    border: 1px solid rgba(255,255,255,0.2);
    transition: background 0.2s;
    cursor: default;
}
.skill-tag:hover { background: rgba(255,255,255,0.28); }

/* ============================================================
   MAIN CONTENT
   ============================================================ */
.content {
    flex: 1;
    padding: 3rem 2.5rem;
    overflow: auto;
    max-width: calc(100% - 280px);
}

section { margin-bottom: 2.75rem; }

h2 {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 1.25rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--teal);
}

/* ---- About ---- */
.about-text {
    font-size: 1rem;
    color: var(--text-light);
    line-height: 1.8;
}

/* ---- Experience & Education cards ---- */
.exp-card, .edu-card {
    background: var(--bg-card);
    border-radius: 10px;
    padding: 1.4rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border-top: 3px solid transparent;
    transition: border-top-color 0.25s, box-shadow 0.25s, transform 0.2s;
}
.exp-card:last-child, .edu-card:last-child { margin-bottom: 0; }
.exp-card:hover, .edu-card:hover {
    border-top-color: var(--teal);
    box-shadow: 0 6px 20px rgba(13,148,136,0.12);
    transform: translateY(-2px);
}
.card-header {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 0.2rem;
}
.card-header h3 { font-size: 1rem; font-weight: 600; color: var(--text); }
.card-company { font-size: 0.875rem; color: var(--text-light); }
.card-company::before { content: '·'; margin-right: 0.4rem; color: var(--text-faint); }
.card-meta {
    font-size: 0.78rem;
    color: var(--teal);
    font-weight: 500;
    margin-bottom: 0.5rem;
}
.card-desc { font-size: 0.92rem; color: var(--text-light); margin-bottom: 0.4rem; }
.card-points {
    margin-top: 0.4rem;
    padding-left: 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}
.card-points li { font-size: 0.875rem; color: var(--text-light); }
.card-extra { font-size: 0.82rem; color: var(--text-light); margin-top: 0.4rem; }
.card-extra strong { color: var(--text-mid); font-weight: 500; }

/* Education specific */
.edu-card h3 { font-size: 0.975rem; font-weight: 600; margin-bottom: 0.2rem; }
.edu-meta { font-size: 0.82rem; color: var(--teal); margin-bottom: 0.15rem; }
.edu-grade { font-size: 0.8rem; color: var(--text-faint); }

/* ---- Projects ---- */
.project-card {
    background: var(--bg-card);
    border-radius: 10px;
    padding: 1.4rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border-top: 3px solid transparent;
    transition: border-top-color 0.25s, box-shadow 0.25s, transform 0.2s;
}
.project-card:last-child { margin-bottom: 0; }
.project-card:hover {
    border-top-color: var(--teal);
    box-shadow: 0 6px 20px rgba(13,148,136,0.12);
    transform: translateY(-2px);
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
    font-size: 0.77rem;
    font-weight: 500;
    padding: 0.2rem 0.55rem;
    border: 1px solid var(--border-dark);
    border-radius: 4px;
    color: var(--text-mid);
    transition: all 0.15s;
}
.proj-link:hover { border-color: var(--teal); color: var(--teal); }
.proj-category {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--teal);
    margin-bottom: 0.35rem;
}
.design-concept {
    font-size: 0.9rem;
    color: var(--text-mid);
    font-style: italic;
    margin-bottom: 0.4rem;
}
.proj-desc { font-size: 0.9rem; color: var(--text-light); margin-bottom: 0.55rem; }
.tag-row { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.tech-tag {
    font-size: 0.775rem;
    color: var(--text-mid);
    padding: 0.2rem 0.5rem;
    border-radius: 3px;
    background: var(--bg);
    border: 1px solid var(--border);
}
.outcomes {
    margin-top: 0.5rem;
    padding-left: 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}
.outcomes li { font-size: 0.85rem; color: var(--text-light); }

/* ---- Design Philosophy ---- */
.philosophy {
    font-size: 1rem;
    color: var(--text-mid);
    font-style: italic;
    line-height: 1.8;
    padding-left: 1rem;
    border-left: 3px solid var(--teal);
}

/* ---- Campaigns (Marketing) ---- */
.campaign-card {
    background: var(--bg-card);
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border-top: 3px solid transparent;
    transition: border-top-color 0.25s, box-shadow 0.2s, transform 0.2s;
}
.campaign-card:last-child { margin-bottom: 0; }
.campaign-card:hover {
    border-top-color: var(--teal);
    box-shadow: 0 4px 16px rgba(13,148,136,0.1);
    transform: translateY(-2px);
}
.campaign-card h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.3rem; }
.camp-meta {
    font-size: 0.78rem;
    color: var(--teal);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.35rem;
}
.camp-channels { font-size: 0.875rem; color: var(--text-light); margin-bottom: 0.35rem; }
.camp-metrics {
    padding-left: 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    margin-top: 0.3rem;
}
.camp-metrics li { font-size: 0.85rem; color: var(--text-light); }

/* ---- Financial Modeling (Finance) ---- */
.fm-item {
    background: var(--bg-card);
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border-top: 3px solid transparent;
    transition: border-top-color 0.25s, box-shadow 0.2s, transform 0.2s;
}
.fm-item:last-child { margin-bottom: 0; }
.fm-item:hover {
    border-top-color: var(--teal);
    box-shadow: 0 4px 16px rgba(13,148,136,0.1);
    transform: translateY(-2px);
}
.fm-item h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.3rem; }
.fm-tools { font-size: 0.85rem; color: var(--text-light); margin-bottom: 0.25rem; }
.fm-outcome { font-size: 0.9rem; color: var(--text-mid); }

/* ---- Investment Portfolios (Finance) ---- */
.ip-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 0.75rem;
}
.ip-card {
    background: var(--bg-card);
    padding: 1rem 1.1rem;
    border-radius: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border-top: 3px solid transparent;
    transition: border-top-color 0.25s, box-shadow 0.2s;
}
.ip-card:hover { border-top-color: var(--teal); box-shadow: 0 4px 12px rgba(13,148,136,0.1); }
.ip-card h3 { font-size: 0.9rem; font-weight: 600; margin-bottom: 0.4rem; }
.ip-meta, .ip-return { font-size: 0.825rem; color: var(--text-light); margin-top: 0.2rem; }

/* ---- Achievements ---- */
.achievement-item {
    padding: 0.7rem 0;
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
.ach-header h3 { font-size: 0.95rem; font-weight: 600; }
.ach-header a { color: var(--teal); border-bottom: 1px solid transparent; transition: border-color 0.15s; }
.ach-header a:hover { border-bottom-color: var(--teal); }
.ach-year { font-size: 0.775rem; color: var(--text-faint); }
.ach-desc { font-size: 0.875rem; color: var(--text-light); }

/* ---- Awards (Designer) ---- */
.award-item {
    padding: 0.7rem 0;
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
.award-header h3 { font-size: 0.95rem; font-weight: 600; }
.award-header a { color: var(--teal); border-bottom: 1px solid transparent; transition: border-color 0.15s; }
.award-header a:hover { border-bottom-color: var(--teal); }
.award-year { font-size: 0.775rem; color: var(--text-faint); }
.award-body { font-size: 0.875rem; color: var(--text-light); }

/* ---- Certifications ---- */
.cert-item {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.6rem 0;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
}
.cert-item:last-child { border-bottom: none; }
.cert-item h3 { font-size: 0.925rem; font-weight: 500; }
.cert-item a { color: var(--teal); }
.cert-meta { font-size: 0.8rem; color: var(--text-faint); white-space: nowrap; }

/* ---- Footer ---- */
footer {
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
    text-align: center;
    color: var(--text-faint);
    font-size: 0.8rem;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
    .layout { flex-direction: column; }
    .sidebar {
        width: 100%;
        height: auto;
        position: static;
    }
    .content {
        max-width: 100%;
        padding: 2rem 1.25rem;
    }
    .ip-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
    .ip-grid { grid-template-columns: 1fr; }
    .proj-header { flex-direction: column; gap: 0.5rem; }
}
"""


# ---------------------------------------------------------------------------
# Sidebar helpers
# ---------------------------------------------------------------------------

def _sidebar_contact(v: dict) -> str:
    rows = ''
    if v.get('location'):
        rows += (
            f'<div class="contact-row">'
            f'<span class="contact-icon">⌖</span>'
            f'<span>{v["location"]}</span>'
            f'</div>'
        )
    if v.get('phone'):
        rows += (
            f'<div class="contact-row">'
            f'<span class="contact-icon">☎</span>'
            f'<span>{v["phone"]}</span>'
            f'</div>'
        )
    if v.get('email'):
        rows += (
            f'<div class="contact-row">'
            f'<span class="contact-icon">✉</span>'
            f'<a href="mailto:{v["email"]}">{v["email"]}</a>'
            f'</div>'
        )

    link_items = [
        ('linkedin_url',  'LinkedIn'),
        ('github_url',    'GitHub'),
        ('portfolio_url', 'Portfolio'),
        ('twitter_url',   'Twitter'),
    ]
    links = ''
    for key, label in link_items:
        if v.get(key):
            links += (
                f'<a href="{v[key]}" class="sidebar-link" '
                f'target="_blank" rel="noopener noreferrer">↗ {label}</a>'
            )
    if links:
        rows += f'<div class="sidebar-links">{links}</div>'

    if not rows:
        return ''
    return f'<div class="sidebar-section"><h3 class="sidebar-heading">Contact</h3>{rows}</div>'


def _sidebar_skills(v: dict) -> str:
    groups = v.get('skill_groups') or []
    if not groups:
        return ''
    parts = []
    for g in groups:
        tags = ''.join(f'<span class="skill-tag">{s}</span>' for s in g['skills'])
        label = f'<p class="sidebar-skill-label">{g["category"]}</p>' if g.get('category') else ''
        parts.append(f'<div class="sidebar-skill-group">{label}<div class="sidebar-tags">{tags}</div></div>')
    return (
        f'<div class="sidebar-section">'
        f'<h3 class="sidebar-heading">Skills</h3>'
        f'{"".join(parts)}'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Section wrapper
# ---------------------------------------------------------------------------

def _section(title: str, content: str) -> str:
    if not content:
        return ''
    return f'<section><h2>{title}</h2>{content}</section>'


# ---------------------------------------------------------------------------
# Common section renderers
# ---------------------------------------------------------------------------

def _about(v: dict) -> str:
    return f'<p class="about-text">{v["bio"]}</p>' if v.get('bio') else ''


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
            extra += f'<p class="card-extra"><strong>Channels:</strong> {channels}</p>'
        if exp.get('financial_metrics_managed'):
            metrics = ', '.join(exp['financial_metrics_managed'])
            extra += f'<p class="card-extra"><strong>Key metrics:</strong> {metrics}</p>'

        company_html = f'<span class="card-company">{exp["company"]}</span>' if exp.get('company') else ''
        meta_html    = f'<p class="card-meta">{" · ".join(meta_parts)}</p>' if meta_parts else ''
        desc_html    = f'<p class="card-desc">{exp["description"]}</p>' if exp.get('description') else ''
        kp_list_html = f'<ul class="card-points">{kp_html}</ul>' if kp_html else ''

        parts.append(
            f'<div class="exp-card">'
            f'<div class="card-header"><h3>{exp["role"]}</h3>{company_html}</div>'
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
            f'<div class="edu-card">'
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
        tag_source    = p.get('tech_stack') or p.get('software_used') or []
        tags_html     = ''.join(f'<span class="tech-tag">{t}</span>' for t in tag_source)
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
    tags = ''.join(f'<span class="tech-tag">{s}</span>' for s in items)
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

        camp_meta_html     = f'<p class="camp-meta">{" · ".join(meta_parts)}</p>' if meta_parts else ''
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
        tools        = ', '.join(fm.get('tools_used') or [])
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
    # 'skills' is intentionally omitted — rendered in sidebar, not main column
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
