"""
Template: Minimal
Ultra-clean monochrome design. White hero with bold black bottom border.
No gradients. Refined typography. Subtle underline animations on headings.

Renders all sections for all 4 categories (software_engineer, designer,
marketing, finance). Every section is skipped when its data is absent.
"""

from .base import CSP, FONTS_URL, DEFAULT_SECTION_ORDER


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def html(v: dict) -> str:
    """
    Generate Minimal template HTML.
    v is the pre-escaped, pre-validated dict from base.normalize().
    """
    order = v.get('section_order') or DEFAULT_SECTION_ORDER
    hidden = v.get('hidden_sections') or set()

    sections = '\n'.join(filter(None, [
        _section(label, renderer(v))
        for key in order
        if key not in hidden and key in _SECTION_RENDERERS
        for label, renderer in [_SECTION_RENDERERS[key]]
    ]))
    # Always prepend About (bio/headline) — not orderable
    about_html = _section('About', _about(v))
    sections = '\n'.join(filter(None, [about_html, sections]))

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
   Minimal Template — monochrome, no gradients, clean typography
   ============================================================ */

:root {
    --ink:        #111827;
    --ink-mid:    #374151;
    --ink-light:  #6b7280;
    --ink-faint:  #9ca3af;
    --bg:         #ffffff;
    --bg-alt:     #f9fafb;
    --border:     #e5e7eb;
    --border-dark: #d1d5db;
    --accent:     #111827;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.65;
    color: var(--ink);
    background: var(--bg);
}

a { color: inherit; text-decoration: none; }
a:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }

.container { max-width: 820px; margin: 0 auto; padding: 0 1.5rem; }

/* ---- Hero ---- */
.hero {
    background: var(--bg);
    padding: 4rem 0 3rem;
    border-bottom: 2.5px solid var(--ink);
}
.hero h1 {
    font-size: 2.75rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--ink);
    margin-bottom: 0.4rem;
}
.headline {
    font-size: 1.1rem;
    color: var(--ink-mid);
    font-weight: 400;
    margin-bottom: 1.25rem;
}
.hero-meta {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    flex-wrap: wrap;
}
.hero-meta-text {
    font-size: 0.875rem;
    color: var(--ink-light);
}
.social-links { display: flex; gap: 0.6rem; flex-wrap: wrap; }
.social-links a {
    font-size: 0.8rem;
    font-weight: 500;
    padding: 0.25rem 0.6rem;
    border: 1px solid var(--border-dark);
    border-radius: 4px;
    color: var(--ink-mid);
    transition: border-color 0.15s, color 0.15s;
}
.social-links a:hover { border-color: var(--ink); color: var(--ink); }

/* ---- Main content ---- */
main { padding: 3.5rem 0; }

section { margin-bottom: 3.5rem; }

h2 {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-light);
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
h2::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* ---- About ---- */
.about p {
    font-size: 1.05rem;
    color: var(--ink-mid);
    line-height: 1.8;
    max-width: 680px;
}

/* ---- Skills ---- */
.skill-group { margin-bottom: 1.25rem; }
.skill-group:last-child { margin-bottom: 0; }
.skill-group-label {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin-bottom: 0.5rem;
}
.tag-row { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.skill-tag {
    background: transparent;
    color: var(--ink-mid);
    padding: 0.25rem 0.65rem;
    border-radius: 4px;
    font-size: 0.825rem;
    border: 1px solid var(--border-dark);
    transition: background 0.15s, color 0.15s;
}
.skill-tag:hover { background: var(--ink); color: white; border-color: var(--ink); }

/* ---- Experience ---- */
.timeline-item {
    margin-bottom: 2.25rem;
    padding-bottom: 2.25rem;
    border-bottom: 1px solid var(--border);
}
.timeline-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.tl-header {
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-bottom: 0.2rem;
}
.tl-header h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--ink);
}
.tl-company {
    font-size: 0.9rem;
    color: var(--ink-mid);
}
.tl-company::before { content: '·'; margin-right: 0.6rem; color: var(--ink-faint); }
.tl-meta {
    font-size: 0.78rem;
    color: var(--ink-light);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.6rem;
}
.tl-desc {
    font-size: 0.95rem;
    color: var(--ink-mid);
    margin-bottom: 0.5rem;
}
.tl-points {
    margin-top: 0.5rem;
    padding-left: 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}
.tl-points li { font-size: 0.875rem; color: var(--ink-light); }
.exp-extra {
    font-size: 0.825rem;
    color: var(--ink-light);
    margin-top: 0.4rem;
}
.exp-extra strong { color: var(--ink-mid); font-weight: 500; }

/* ---- Projects ---- */
.project-card {
    margin-bottom: 1.75rem;
    padding: 1.25rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    transition: border-color 0.2s;
}
.project-card:hover { border-color: var(--border-dark); }
.project-card:last-child { margin-bottom: 0; }
.proj-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
}
.proj-header h3 { font-size: 1rem; font-weight: 600; color: var(--ink); }
.proj-links { display: flex; gap: 0.4rem; }
.proj-link {
    font-size: 0.775rem;
    font-weight: 500;
    padding: 0.2rem 0.55rem;
    border: 1px solid var(--border-dark);
    border-radius: 4px;
    color: var(--ink-mid);
    transition: all 0.15s;
}
.proj-link:hover { border-color: var(--ink); color: var(--ink); }
.proj-category {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-light);
    margin-bottom: 0.4rem;
}
.design-concept {
    font-size: 0.9rem;
    color: var(--ink-mid);
    font-style: italic;
    margin-bottom: 0.5rem;
}
.proj-desc { font-size: 0.9rem; color: var(--ink-mid); margin-bottom: 0.6rem; }
.tech-tag {
    font-size: 0.775rem;
    color: var(--ink-mid);
    padding: 0.2rem 0.5rem;
    border-radius: 3px;
    background: var(--bg-alt);
    border: 1px solid var(--border);
}
.outcomes {
    margin-top: 0.6rem;
    padding-left: 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}
.outcomes li { font-size: 0.85rem; color: var(--ink-light); }

/* ---- Design Philosophy ---- */
.philosophy {
    font-size: 1.05rem;
    color: var(--ink-mid);
    font-style: italic;
    line-height: 1.8;
    max-width: 680px;
    padding-left: 1rem;
    border-left: 2px solid var(--border-dark);
}

/* ---- Campaigns (Marketing) ---- */
.campaign-card {
    margin-bottom: 1.5rem;
    padding: 1.25rem;
    border: 1px solid var(--border);
    border-radius: 8px;
}
.campaign-card:last-child { margin-bottom: 0; }
.campaign-card h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.3rem; }
.camp-meta {
    font-size: 0.8rem;
    color: var(--ink-light);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
}
.camp-channels { font-size: 0.875rem; color: var(--ink-mid); margin-bottom: 0.4rem; }
.camp-metrics {
    padding-left: 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    margin-top: 0.4rem;
}
.camp-metrics li { font-size: 0.85rem; color: var(--ink-light); }

/* ---- Financial Modeling (Finance) ---- */
.fm-item {
    margin-bottom: 1.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
}
.fm-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.fm-item h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.3rem; }
.fm-tools { font-size: 0.85rem; color: var(--ink-light); margin-bottom: 0.3rem; }
.fm-outcome { font-size: 0.9rem; color: var(--ink-mid); }

/* ---- Investment Portfolios (Finance) ---- */
.ip-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
}
.ip-card {
    padding: 1rem;
    border: 1px solid var(--border);
    border-radius: 8px;
}
.ip-card h3 { font-size: 0.9rem; font-weight: 600; margin-bottom: 0.4rem; }
.ip-meta, .ip-return { font-size: 0.825rem; color: var(--ink-mid); margin-top: 0.2rem; }

/* ---- Achievements ---- */
.achievement-item {
    margin-bottom: 1.25rem;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid var(--border);
}
.achievement-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.ach-header {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    margin-bottom: 0.25rem;
    flex-wrap: wrap;
}
.ach-header h3 { font-size: 0.95rem; font-weight: 600; }
.ach-header a { border-bottom: 1px solid var(--border-dark); transition: border-color 0.15s; }
.ach-header a:hover { border-color: var(--ink); }
.ach-year {
    font-size: 0.775rem;
    color: var(--ink-faint);
    font-variant-numeric: tabular-nums;
}
.ach-desc { font-size: 0.875rem; color: var(--ink-light); }

/* ---- Awards (Designer) ---- */
.award-item {
    margin-bottom: 1.25rem;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid var(--border);
}
.award-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.award-header {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    margin-bottom: 0.2rem;
    flex-wrap: wrap;
}
.award-header h3 { font-size: 0.95rem; font-weight: 600; }
.award-header a { border-bottom: 1px solid var(--border-dark); transition: border-color 0.15s; }
.award-header a:hover { border-color: var(--ink); }
.award-year { font-size: 0.775rem; color: var(--ink-faint); }
.award-body { font-size: 0.875rem; color: var(--ink-light); }

/* ---- Education ---- */
.edu-item {
    margin-bottom: 1.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
}
.edu-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.edu-item h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.2rem; }
.edu-meta { font-size: 0.85rem; color: var(--ink-light); margin-bottom: 0.2rem; }
.edu-grade { font-size: 0.825rem; color: var(--ink-faint); }

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
.cert-item a { border-bottom: 1px solid var(--border-dark); transition: border-color 0.15s; }
.cert-item a:hover { border-color: var(--ink); }
.cert-meta { font-size: 0.8rem; color: var(--ink-faint); white-space: nowrap; }

/* ---- Footer ---- */
footer {
    border-top: 1px solid var(--border);
    padding: 2rem 0;
    text-align: center;
    color: var(--ink-faint);
    font-size: 0.8rem;
}

/* ---- Responsive ---- */
@media (max-width: 640px) {
    .hero h1 { font-size: 2rem; }
    .hero-meta { flex-direction: column; align-items: flex-start; gap: 0.75rem; }
    .proj-header { flex-direction: column; gap: 0.5rem; }
    .tl-header { flex-direction: column; gap: 0.15rem; }
    .tl-company::before { display: none; }
    .ip-grid { grid-template-columns: 1fr; }
}
"""


# ---------------------------------------------------------------------------
# Hero section
# ---------------------------------------------------------------------------

def _hero(v: dict) -> str:
    headline_html = f'<p class="headline">{v["headline"]}</p>' if v.get('headline') else ''

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
# Section wrapper — skips rendering when content is empty
# ---------------------------------------------------------------------------

def _section(title: str, content: str) -> str:
    if not content:
        return ''
    return (
        f'<section>'
        f'<h2><span>{title}</span></h2>'
        f'{content}'
        f'</section>'
    )


# ---------------------------------------------------------------------------
# Common section renderers
# ---------------------------------------------------------------------------

def _about(v: dict) -> str:
    return f'<p>{v["bio"]}</p>' if v.get('bio') else ''


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

        company_html = f'<span class="tl-company">{exp["company"]}</span>' if exp.get("company") else ""
        meta_html = f'<p class="tl-meta">{" · ".join(meta_parts)}</p>' if meta_parts else ""
        desc_html = f'<p class="tl-desc">{exp["description"]}</p>' if exp.get("description") else ""
        kp_list_html = f'<ul class="tl-points">{kp_html}</ul>' if kp_html else ""
        parts.append(
            f'<div class="timeline-item">'
            f'<div class="tl-header">'
            f'<h3>{exp["role"]}</h3>'
            f'{company_html}'
            f'</div>'
            f'{meta_html}'
            f'{desc_html}'
            f'{kp_list_html}'
            f'{extra}'
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
        inst_parts = list(filter(None, [edu.get('institution'), edu.get('year_range')]))
        grade_html = f'<p class="edu-grade">{edu["grade_or_score"]}</p>' if edu.get('grade_or_score') else ''

        inst_meta_html = f'<p class="edu-meta">{" · ".join(inst_parts)}</p>' if inst_parts else ""
        parts.append(
            f'<div class="edu-item">'
            f'<h3>{degree_field or edu.get("institution", "")}</h3>'
            f'{inst_meta_html}'
            f'{grade_html}'
            f'</div>'
        )
    return ''.join(parts)


def _certifications(v: dict) -> str:
    items = v.get('certifications') or []
    if not items:
        return ''
    parts = []
    for c in items:
        name = f'<a href="{c["url"]}" target="_blank" rel="noopener noreferrer">{c["name"]}</a>' if c.get('url') else c['name']
        meta = ' · '.join(filter(None, [c.get('issuer'), c.get('year')]))
        cert_meta_html = f'<span class="cert-meta">{meta}</span>' if meta else ""
        parts.append(
            f'<div class="cert-item">'
            f'<h3>{name}</h3>'
            f'{cert_meta_html}'
            f'</div>'
        )
    return ''.join(parts)


def _achievements(v: dict) -> str:
    items = v.get('achievements') or []
    if not items:
        return ''
    parts = []
    for a in items:
        title = f'<a href="{a["url"]}" target="_blank" rel="noopener noreferrer">{a["title"]}</a>' if a.get('url') else a['title']
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
        # Links
        link_items = [
            (p.get('github_repo'), 'GitHub'),
            (p.get('project_url'), 'Live'),
        ]
        links_html = ''.join(
            f'<a href="{url}" class="proj-link" target="_blank" rel="noopener noreferrer">{label}</a>'
            for url, label in link_items if url
        )

        # Tags — tech_stack for SE, software_used for Designer
        tag_source = p.get('tech_stack') or p.get('software_used') or []
        tags_html = ''.join(f'<span class="tech-tag">{t}</span>' for t in tag_source)

        # Designer-specific meta
        category_html = f'<span class="proj-category">{p["project_category"]}</span>' if p.get('project_category') else ''
        concept_html = f'<p class="design-concept">{p["design_concept"]}</p>' if p.get('design_concept') else ''

        resp_html     = ''.join(f'<li>{r}</li>' for r in (p.get('responsibilities') or []))
        outcomes_html = ''.join(f'<li>{o}</li>' for o in (p.get('measurable_outcomes') or []))

        proj_links_div   = f'<div class="proj-links">{links_html}</div>' if links_html else ""
        proj_desc_html   = f'<p class="proj-desc">{p["description"]}</p>' if p.get("description") else ""
        tags_row_html    = f'<div class="tag-row">{tags_html}</div>' if tags_html else ""
        resp_list_html   = f'<ul class="outcomes">{resp_html}</ul>' if resp_html else ""
        outcomes_list_html = f'<ul class="outcomes">{outcomes_html}</ul>' if outcomes_html else ""
        parts.append(
            f'<div class="project-card">'
            f'<div class="proj-header">'
            f'<h3>{p["title"]}</h3>'
            f'{proj_links_div}'
            f'</div>'
            f'{category_html}'
            f'{concept_html}'
            f'{proj_desc_html}'
            f'{tags_row_html}'
            f'{resp_list_html}'
            f'{outcomes_list_html}'
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
        title = f'<a href="{a["url"]}" target="_blank" rel="noopener noreferrer">{a["title"]}</a>' if a.get('url') else a['title']
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
        meta_parts = list(filter(None, [c.get('campaign_type'),
                                        f'Budget: {c["budget"]}' if c.get('budget') else '']))
        channels = ', '.join(c.get('channels_used') or [])
        metrics_html = ''.join(f'<li>{m}</li>' for m in (c.get('performance_metrics') or []))

        camp_meta_html = f'<p class="camp-meta">{" · ".join(meta_parts)}</p>' if meta_parts else ""
        camp_channels_html = f'<p class="camp-channels">Channels: {channels}</p>' if channels else ""
        camp_metrics_html = f'<ul class="camp-metrics">{metrics_html}</ul>' if metrics_html else ""
        parts.append(
            f'<div class="campaign-card">'
            f'<h3>{c["campaign_name"]}</h3>'
            f'{camp_meta_html}'
            f'{camp_channels_html}'
            f'{camp_metrics_html}'
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
        tools = ', '.join(fm.get('tools_used') or [])
        fm_tools_html = f'<p class="fm-tools">Tools: {tools}</p>' if tools else ""
        fm_outcome_html = f'<p class="fm-outcome">{fm["outcome"]}</p>' if fm.get("outcome") else ""
        parts.append(
            f'<div class="fm-item">'
            f'<h3>{fm["model_type"]}</h3>'
            f'{fm_tools_html}'
            f'{fm_outcome_html}'
            f'</div>'
        )
    return ''.join(parts)


def _investment_portfolios(v: dict) -> str:
    items = v.get('investment_portfolios') or []
    if not items:
        return ''
    def _ip_card(ip: dict) -> str:
        aum_html = f'<p class="ip-meta">AUM: {ip["assets_under_management"]}</p>' if ip.get("assets_under_management") else ""
        ret_html = f'<p class="ip-return">Return: {ip["performance_return"]}</p>' if ip.get("performance_return") else ""
        return f'<div class="ip-card"><h3>{ip["portfolio_type"]}</h3>{aum_html}{ret_html}</div>'
    cards = ''.join(_ip_card(ip) for ip in items)
    return f'<div class="ip-grid">{cards}</div>'


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
