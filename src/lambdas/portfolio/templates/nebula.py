"""
Template: Nebula
Cyberpunk / dark-space aesthetic. Deep black canvas with neon purple
(#a855f7) and cyan (#22d3ee) dual accents. Auto-numbered sections,
animated grid background, glassmorphism cards.
"""

from html import escape as _e
from .base import _safe_url as safe_url, DEFAULT_SECTION_ORDER


# ---------------------------------------------------------------------------
# Section helper — auto-numbered
# ---------------------------------------------------------------------------

def _section(title: str, content: str, counter: list) -> str:
    if not content:
        return ''
    counter[0] += 1
    num = str(counter[0]).zfill(2)
    return (
        f'<section>'
        f'<h2><span class="snum">{num}</span> {title}</h2>'
        f'{content}'
        f'</section>'
    )


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _about(v: dict) -> str:
    parts = []
    if v.get('bio'):
        parts.append(f'<p class="about-text">{v["bio"]}</p>')
    if v.get('headline'):
        parts.append(f'<p class="tagline">{v["headline"]}</p>')
    loc = v.get('location', '')
    email = v.get('email', '')
    phone = v.get('phone', '')
    meta = ' &bull; '.join(filter(None, [loc, email, phone]))
    if meta:
        parts.append(f'<p class="about-meta">{meta}</p>')
    return ''.join(parts)


def _skills(v: dict) -> str:
    groups = v.get('skill_groups') or []
    if not groups:
        return ''
    html = '<div class="skill-grid">'
    for g in groups:
        skills = g.get('skills') or []
        if not skills:
            continue
        tags = ''.join(f'<span class="tag">{t}</span>' for t in skills)
        label = g.get('category', '')
        html += (
            f'<div class="skill-group">'
            f'{"<span class=skill-label>" + label + "</span>" if label else ""}'
            f'<div class="tag-row">{tags}</div>'
            f'</div>'
        )
    html += '</div>'
    return html


def _experience(v: dict) -> str:
    items = v.get('experience', [])
    if not items:
        return ''
    html = '<div class="exp-list">'
    for exp in items:
        role    = _e(exp.get('role', ''))
        company = _e(exp.get('company', ''))
        loc     = _e(exp.get('location', ''))
        dur     = _e(exp.get('duration', ''))
        desc    = _e(exp.get('description', ''))
        meta_parts = list(filter(None, [loc, dur]))
        meta = ' &bull; '.join(meta_parts)

        pts = exp.get('key_points', [])
        pts_html = ''
        if pts:
            pts_html = '<ul class="card-list">' + ''.join(f'<li>{_e(p)}</li>' for p in pts) + '</ul>'

        html += (
            f'<div class="card exp-card">'
            f'<div class="exp-header">'
            f'<span class="exp-role">{role}</span>'
            f'<span class="exp-company">{company}</span>'
            f'</div>'
            f'{"<p class=exp-meta>" + meta + "</p>" if meta else ""}'
            f'{"<p class=exp-desc>" + desc + "</p>" if desc else ""}'
            f'{pts_html}'
            f'</div>'
        )
    html += '</div>'
    return html


def _education(v: dict) -> str:
    items = v.get('education', [])
    if not items:
        return ''
    html = '<div class="edu-list">'
    for edu in items:
        degree  = _e(edu.get('degree', ''))
        field   = _e(edu.get('field_of_study', ''))
        inst    = _e(edu.get('institution', ''))
        loc     = _e(edu.get('location', ''))
        yr      = _e(edu.get('year_range', ''))
        grade   = _e(edu.get('grade_or_score', ''))
        title_parts = list(filter(None, [degree, field]))
        title = ', '.join(title_parts) if title_parts else inst
        meta_parts = list(filter(None, [inst if title_parts else '', loc, yr]))
        meta = ' &bull; '.join(filter(None, meta_parts))
        html += (
            f'<div class="card">'
            f'<div class="card-title">{title}</div>'
            f'{"<div class=card-sub>" + meta + "</div>" if meta else ""}'
            f'{"<div class=card-grade>" + grade + "</div>" if grade else ""}'
            f'</div>'
        )
    html += '</div>'
    return html


def _projects(v: dict) -> str:
    items = v.get('projects', [])
    if not items:
        return ''
    html = '<div class="project-grid">'
    for proj in items:
        title   = _e(proj.get('title', ''))
        desc    = _e(proj.get('description', ''))
        stack    = proj.get('tech_stack') or proj.get('software_used') or []
        gh       = safe_url(proj.get('github_repo', ''))
        url      = safe_url(proj.get('project_url', ''))
        resp     = proj.get('responsibilities') or []
        outcomes = proj.get('measurable_outcomes') or []

        tags = ''.join(f'<span class="tag">{_e(t)}</span>' for t in stack)
        tag_row = f'<div class="tag-row">{tags}</div>' if tags else ''

        links = ''
        if gh:
            links += f'<a class="proj-link" href="{gh}" target="_blank" rel="noopener">GitHub</a>'
        if url:
            links += f'<a class="proj-link" href="{url}" target="_blank" rel="noopener">Live</a>'

        resp_html = ('<ul class="card-list">' + ''.join(f'<li>{_e(r)}</li>' for r in resp) + '</ul>') if resp else ''
        out_html  = ('<ul class="card-list">' + ''.join(f'<li>{_e(o)}</li>' for o in outcomes) + '</ul>') if outcomes else ''

        html += (
            f'<div class="card proj-card">'
            f'<div class="proj-header">'
            f'<span class="card-title">{title}</span>'
            f'{"<div class=proj-links>" + links + "</div>" if links else ""}'
            f'</div>'
            f'{"<p class=card-body>" + desc + "</p>" if desc else ""}'
            f'{tag_row}'
            f'{resp_html}'
            f'{out_html}'
            f'</div>'
        )
    html += '</div>'
    return html


def _certifications(v: dict) -> str:
    items = v.get('certifications', [])
    if not items:
        return ''
    html = '<div class="cert-list">'
    for cert in items:
        name   = _e(cert.get('name', ''))
        issuer = _e(cert.get('issuer', ''))
        year   = _e(str(cert.get('year', '')))
        url    = safe_url(cert.get('url', ''))
        meta = ' &bull; '.join(filter(None, [issuer, year]))
        label = f'<a class="cert-link" href="{url}" target="_blank" rel="noopener">{name}</a>' if url else f'<span class="cert-name">{name}</span>'
        html += (
            f'<div class="card cert-row">'
            f'{label}'
            f'{"<span class=cert-meta>" + meta + "</span>" if meta else ""}'
            f'</div>'
        )
    html += '</div>'
    return html


def _achievements(v: dict) -> str:
    items = v.get('achievements', [])
    if not items:
        return ''
    html = '<div class="ach-list">'
    for ach in items:
        title = _e(ach.get('title', ''))
        desc  = _e(ach.get('description', ''))
        year  = _e(str(ach.get('year', '')))
        html += (
            f'<div class="card">'
            f'<div class="card-title">{title}{"&nbsp;<span class=yr>" + year + "</span>" if year else ""}</div>'
            f'{"<p class=card-body>" + desc + "</p>" if desc else ""}'
            f'</div>'
        )
    html += '</div>'
    return html


def _awards(v: dict) -> str:
    items = v.get('awards', [])
    if not items:
        return ''
    html = '<div class="award-list">'
    for aw in items:
        title = _e(aw.get('title', ''))
        body  = _e(aw.get('awarding_body', ''))
        year  = _e(str(aw.get('year', '')))
        url   = safe_url(aw.get('url', ''))
        meta = ' &bull; '.join(filter(None, [body, year]))
        label = f'<a class="cert-link" href="{url}" target="_blank" rel="noopener">{title}</a>' if url else f'<span class="card-title">{title}</span>'
        html += (
            f'<div class="card">'
            f'{label}'
            f'{"<span class=cert-meta>" + meta + "</span>" if meta else ""}'
            f'</div>'
        )
    html += '</div>'
    return html


def _design_philosophy(v: dict) -> str:
    dp = v.get('design_philosophy', '')
    if not dp:
        return ''
    return f'<div class="card philosophy-card"><p>{_e(dp)}</p></div>'


def _software_proficiency(v: dict) -> str:
    items = v.get('software_proficiency', [])
    if not items:
        return ''
    tags = ''.join(f'<span class="tag">{_e(s)}</span>' for s in items)
    return f'<div class="tag-row sw-row">{tags}</div>'


def _campaigns(v: dict) -> str:
    items = v.get('campaigns', [])
    if not items:
        return ''
    html = '<div class="camp-list">'
    for c in items:
        name    = _e(c.get('campaign_name', ''))
        ctype   = _e(c.get('campaign_type', ''))
        budget  = _e(c.get('budget', ''))
        channels = c.get('channels_used', [])
        metrics  = c.get('performance_metrics', [])
        ch_tags = ''.join(f'<span class="tag">{_e(ch)}</span>' for ch in channels)
        m_items = ''.join(f'<li>{_e(m)}</li>' for m in metrics)
        html += (
            f'<div class="card">'
            f'<div class="card-title">{name}{"&nbsp;<span class=cert-meta>" + ctype + "</span>" if ctype else ""}</div>'
            f'{"<div class=tag-row>" + ch_tags + "</div>" if ch_tags else ""}'
            f'{"<p class=card-body>Budget: " + budget + "</p>" if budget else ""}'
            f'{"<ul class=card-list>" + m_items + "</ul>" if m_items else ""}'
            f'</div>'
        )
    html += '</div>'
    return html


def _financial_modeling(v: dict) -> str:
    items = v.get('financial_modeling', [])
    if not items:
        return ''
    html = '<div class="fm-list">'
    for fm in items:
        mtype   = _e(fm.get('model_type', ''))
        tools   = fm.get('tools_used', [])
        outcome = _e(fm.get('outcome', ''))
        tool_tags = ''.join(f'<span class="tag">{_e(t)}</span>' for t in tools)
        html += (
            f'<div class="card">'
            f'<div class="card-title">{mtype}</div>'
            f'{"<div class=tag-row>" + tool_tags + "</div>" if tool_tags else ""}'
            f'{"<p class=card-body>" + outcome + "</p>" if outcome else ""}'
            f'</div>'
        )
    html += '</div>'
    return html


def _investment_portfolios(v: dict) -> str:
    items = v.get('investment_portfolios', [])
    if not items:
        return ''
    html = '<div class="ip-list">'
    for ip in items:
        ptype  = _e(ip.get('portfolio_type', ''))
        aum    = _e(ip.get('assets_under_management', ''))
        ret    = _e(ip.get('performance_return', ''))
        html += (
            f'<div class="card">'
            f'<div class="card-title">{ptype}</div>'
            f'<div class="ip-stats">'
            f'{"<span><label>AUM</label>" + aum + "</span>" if aum else ""}'
            f'{"<span><label>Return</label>" + ret + "</span>" if ret else ""}'
            f'</div>'
            f'</div>'
        )
    html += '</div>'
    return html


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def html(v: dict) -> str:
    name     = v.get('name', 'Portfolio')
    title    = v.get('headline', '')
    li_html  = ''
    for key, label in (
        ('linkedin_url', 'LinkedIn'),
        ('github_url',   'GitHub'),
        ('portfolio_url','Portfolio'),
        ('twitter_url',  'Twitter'),
    ):
        u = v.get(key, '')
        if u:
            li_html += f'<a class="hero-link" href="{u}" target="_blank" rel="noopener">{label}</a>'

    _NEBULA_RENDERERS = {
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
    order = v.get('section_order') or DEFAULT_SECTION_ORDER
    hidden = v.get('hidden_sections') or set()
    counter = [0]
    about_sec = _section('About', _about(v), counter)
    content_sections = '\n'.join(filter(None, [
        _section(label, renderer(v), counter)
        for key in order
        if key not in hidden and key in _NEBULA_RENDERERS
        for label, renderer in [_NEBULA_RENDERERS[key]]
    ]))
    sections = '\n'.join(filter(None, [about_sec, content_sections]))

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{name} — Portfolio</title>
  <link rel="stylesheet" href="styles.css"/>
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src 'none'; img-src 'self' data:"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500&display=swap" rel="stylesheet"/>
</head>
<body>
  <!-- Animated background -->
  <div class="bg-grid" aria-hidden="true"></div>
  <div class="orb orb1" aria-hidden="true"></div>
  <div class="orb orb2" aria-hidden="true"></div>

  <header class="hero">
    <div class="hero-inner">
      <p class="eyebrow"><span class="eyebrow-dot"></span>Portfolio</p>
      <h1 class="hero-name">{name}</h1>
      {f'<p class="hero-title">{title}</p>' if title else ''}
      {f'<div class="hero-links">{li_html}</div>' if li_html else ''}
    </div>
    <div class="hero-shimmer" aria-hidden="true"></div>
  </header>

  <main class="container">
    {sections}
  </main>

  <footer class="footer">
    <span>Built with AI &bull; Nebula Theme</span>
  </footer>
</body>
</html>'''


def css() -> str:
    return '''
/* ============================================================
   Nebula — Cyberpunk dark-space portfolio theme
   ============================================================ */

@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500&display=swap');

/* ---- Reset & tokens ---- */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:       #07070f;
  --surface:  #0e0e1a;
  --card:     #13131f;
  --border:   rgba(168,85,247,.18);
  --purple:   #a855f7;
  --cyan:     #22d3ee;
  --text:     #e2e8f0;
  --muted:    #94a3b8;
  --radius:   12px;
  --font-h:   'Space Grotesk', sans-serif;
  --font-b:   'Inter', sans-serif;
}

html { scroll-behavior: smooth; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-b);
  font-size: 16px;
  line-height: 1.65;
  overflow-x: hidden;
  position: relative;
}

/* ---- Animated grid background ---- */
.bg-grid {
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(168,85,247,.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(168,85,247,.06) 1px, transparent 1px);
  background-size: 48px 48px;
  animation: grid-drift 20s linear infinite;
  pointer-events: none;
  z-index: 0;
}
@keyframes grid-drift {
  0%   { background-position: 0 0; }
  100% { background-position: 48px 48px; }
}

/* ---- Drifting orbs ---- */
.orb {
  position: fixed;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
  z-index: 0;
  animation: orb-float 18s ease-in-out infinite alternate;
}
.orb1 {
  width: 500px; height: 500px;
  background: rgba(168,85,247,.18);
  top: -120px; left: -120px;
}
.orb2 {
  width: 400px; height: 400px;
  background: rgba(34,211,238,.14);
  bottom: -100px; right: -100px;
  animation-delay: -9s;
}
@keyframes orb-float {
  from { transform: translate(0,0) scale(1); }
  to   { transform: translate(40px,40px) scale(1.08); }
}

/* ---- Hero ---- */
.hero {
  position: relative;
  z-index: 1;
  padding: 100px 5vw 80px;
  text-align: center;
  border-bottom: 1px solid var(--border);
  overflow: hidden;
}
.hero-inner { position: relative; z-index: 2; }

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-h);
  font-size: .75rem;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: var(--cyan);
  margin-bottom: 20px;
}
.eyebrow-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--cyan);
  animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: .4; transform: scale(.7); }
}

.hero-name {
  font-family: var(--font-h);
  font-size: clamp(2.8rem, 7vw, 5.5rem);
  font-weight: 700;
  letter-spacing: -.02em;
  line-height: 1.05;
  background: linear-gradient(135deg, var(--purple) 0%, var(--cyan) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 16px;
}

.hero-title {
  font-family: var(--font-h);
  font-size: 1.15rem;
  color: var(--muted);
  font-weight: 400;
  margin-bottom: 24px;
}

.hero-links { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; }
.hero-link {
  display: inline-block;
  padding: 7px 18px;
  border-radius: 999px;
  border: 1px solid var(--border);
  color: var(--cyan);
  text-decoration: none;
  font-size: .85rem;
  font-family: var(--font-h);
  font-weight: 500;
  transition: border-color .2s, background .2s;
  background: rgba(34,211,238,.05);
}
.hero-link:hover { border-color: var(--cyan); background: rgba(34,211,238,.12); }

/* Shimmer line across bottom of hero */
.hero-shimmer {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--purple), var(--cyan), transparent);
  background-size: 200% 100%;
  animation: shimmer-slide 3s linear infinite;
}
@keyframes shimmer-slide {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* ---- Layout ---- */
.container {
  position: relative;
  z-index: 1;
  max-width: 860px;
  margin: 0 auto;
  padding: 60px 24px 100px;
}

/* ---- Sections ---- */
section {
  margin-bottom: 60px;
}
section h2 {
  display: flex;
  align-items: center;
  gap: 14px;
  font-family: var(--font-h);
  font-size: 1rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .12em;
  color: var(--muted);
  margin-bottom: 24px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.snum {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px; height: 20px;
  border-radius: 4px;
  background: linear-gradient(135deg, var(--purple), var(--cyan));
  color: #07070f;
  font-size: .7rem;
  font-weight: 700;
  letter-spacing: .04em;
  flex-shrink: 0;
}

/* ---- Card ---- */
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 22px;
  margin-bottom: 14px;
  position: relative;
  overflow: hidden;
  transition: border-color .25s, transform .2s;
}
.card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, var(--purple), var(--cyan));
  opacity: 0;
  transition: opacity .25s;
}
.card:hover { border-color: rgba(168,85,247,.4); transform: translateX(3px); }
.card:hover::before { opacity: 1; }

.card-title {
  font-family: var(--font-h);
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}
.card-sub, .card-grade {
  font-size: .85rem;
  color: var(--muted);
  margin-bottom: 4px;
}
.card-body {
  font-size: .9rem;
  color: var(--muted);
  margin-top: 8px;
}
.card-list {
  margin: 8px 0 0 16px;
  font-size: .88rem;
  color: var(--muted);
}
.card-list li { margin-bottom: 4px; }

/* ---- About ---- */
.about-text { font-size: 1rem; color: var(--text); margin-bottom: 10px; }
.tagline    { font-size: .95rem; color: var(--cyan); font-style: italic; margin-bottom: 10px; }
.about-meta { font-size: .85rem; color: var(--muted); }

/* ---- Skills ---- */
.skill-grid  { display: flex; flex-direction: column; gap: 14px; }
.skill-group { display: flex; flex-direction: column; gap: 8px; }
.skill-label {
  font-family: var(--font-h);
  font-size: .75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: var(--purple);
}
.tag-row { display: flex; flex-wrap: wrap; gap: 8px; }
.tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(168,85,247,.1);
  border: 1px solid rgba(168,85,247,.25);
  color: var(--text);
  font-size: .8rem;
  font-family: var(--font-h);
  transition: background .2s, border-color .2s;
}
.tag:hover { background: rgba(168,85,247,.22); border-color: var(--purple); }

/* ---- Experience ---- */
.exp-list   { display: flex; flex-direction: column; gap: 0; }
.exp-card   { margin-bottom: 14px; }
.exp-header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 10px; margin-bottom: 4px; }
.exp-role   { font-family: var(--font-h); font-size: 1rem; font-weight: 600; color: var(--text); }
.exp-company { font-size: .9rem; color: var(--cyan); }
.exp-meta   { font-size: .82rem; color: var(--muted); margin-bottom: 6px; }
.exp-desc   { font-size: .9rem; color: var(--muted); margin-bottom: 6px; }

/* ---- Education ---- */
.edu-list { display: flex; flex-direction: column; gap: 0; }

/* ---- Projects ---- */
.project-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(280px,1fr)); gap: 14px; }
.proj-card    { margin-bottom: 0; }
.proj-header  { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 8px; }
.proj-links   { display: flex; gap: 8px; flex-shrink: 0; }
.proj-link {
  font-size: .75rem;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  color: var(--cyan);
  text-decoration: none;
  font-family: var(--font-h);
  transition: border-color .2s;
}
.proj-link:hover { border-color: var(--cyan); }

/* ---- Certs / Awards ---- */
.cert-list, .award-list { display: flex; flex-direction: column; gap: 10px; }
.cert-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 14px 18px;
}
.cert-name, .cert-link {
  font-family: var(--font-h);
  font-size: .95rem;
  font-weight: 500;
  color: var(--text);
}
.cert-link { color: var(--cyan); text-decoration: none; }
.cert-link:hover { text-decoration: underline; }
.cert-meta { font-size: .82rem; color: var(--muted); }
.yr { font-size: .8rem; color: var(--muted); }

/* ---- Achievements ---- */
.ach-list { display: flex; flex-direction: column; gap: 0; }

/* ---- Philosophy ---- */
.philosophy-card p { font-size: .95rem; color: var(--muted); font-style: italic; line-height: 1.75; }

/* ---- Software Proficiency ---- */
.sw-row { gap: 10px; }

/* ---- Campaigns ---- */
.camp-list { display: flex; flex-direction: column; gap: 0; }

/* ---- Financial Modeling ---- */
.fm-list { display: flex; flex-direction: column; gap: 0; }

/* ---- Investment Portfolios ---- */
.ip-list  { display: flex; flex-direction: column; gap: 0; }
.ip-stats { display: flex; gap: 24px; margin-top: 10px; flex-wrap: wrap; }
.ip-stats span { display: flex; flex-direction: column; }
.ip-stats label { font-size: .7rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-bottom: 2px; }

/* ---- Footer ---- */
.footer {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 32px;
  font-size: .78rem;
  color: var(--muted);
  border-top: 1px solid var(--border);
}

/* ---- Responsive ---- */
@media (max-width: 600px) {
  .hero { padding: 72px 20px 60px; }
  .container { padding: 40px 16px 60px; }
  .project-grid { grid-template-columns: 1fr; }
  .cert-row { flex-direction: column; align-items: flex-start; }
}
'''
