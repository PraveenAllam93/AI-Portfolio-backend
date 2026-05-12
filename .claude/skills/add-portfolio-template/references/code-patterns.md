# Code Patterns Reference

## Section A — Python Template Skeleton

Full annotated skeleton for `src/backend/portfolio/templates/{id}.py`:

```python
"""
{TemplateName} template — {brief visual description}
"""
from .utils import _e, _safe_url, render_section_in_order


def css() -> str:
    return """
        /* Reset */
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: #ffffff;     /* ← use design spec colors */
            color: #1a1a1a;
            line-height: 1.6;
        }

        /* Hero / Header */
        .hero { ... }
        .hero h1 { ... }
        .hero .headline { ... }
        .hero .bio { ... }
        .hero .contact-links a { ... }

        /* Sections */
        .section { margin: 2rem 0; }
        .section-title { ... }

        /* Experience */
        .exp-item { ... }
        .exp-header { ... }
        .exp-description { ... }
        .key-points { list-style: disc; padding-left: 1.2em; }
        .key-points li { margin: 0.25rem 0; }

        /* Projects */
        .project-card { ... }
        .tech-tag { display: inline-block; ... }

        /* Skills */
        .skill-group { ... }
        .skill-tag { ... }

        /* Education, Certs, Achievements — shared card style */
        .list-card { ... }
    """


def html(data: dict) -> str:
    sections_html = render_section_in_order(data, {
        "experience":            _render_experience,
        "projects":              _render_projects,
        "skills":                _render_skills,
        "education":             _render_education,
        "certifications":        _render_certifications,
        "achievements":          _render_achievements,
        "awards":                _render_awards,
        "campaigns":             _render_campaigns,
        "financial_modeling":    _render_financial_modeling,
        "investment_portfolios": _render_investment_portfolios,
        "design_philosophy":     _render_design_philosophy,
        "software_proficiency":  _render_software_proficiency,
    })

    profile_image_html = ""
    if data.get("profile_image"):
        url = _safe_url(data["profile_image"])
        if url:
            profile_image_html = f'<img src="{url}" class="profile-img" alt="Profile photo">'

    social_links = _render_social_links(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_e(data.get("name", "Portfolio"))}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>{css()}</style>
</head>
<body>
  <header class="hero">
    {profile_image_html}
    <h1>{_e(data.get("name", ""))}</h1>
    <p class="headline">{_e(data.get("headline", ""))}</p>
    <p class="bio">{_e(data.get("bio", ""))}</p>
    {social_links}
  </header>
  <main>
    {sections_html}
  </main>
</body>
</html>"""


def _render_social_links(data: dict) -> str:
    links = []
    for key, label in [
        ("linkedin_url", "LinkedIn"),
        ("github_url", "GitHub"),
        ("portfolio_url", "Portfolio"),
        ("twitter_url", "Twitter"),
    ]:
        url = _safe_url(data.get(key, ""))
        if url:
            links.append(f'<a href="{url}" target="_blank" rel="noopener">{label}</a>')
    return f'<div class="social-links">{"".join(links)}</div>' if links else ""


def _render_experience(data: dict) -> str:
    items = data.get("experience", [])
    if not items:
        return ""
    rows = []
    for item in items:
        end = "Present" if item.get("is_current") else _e(item.get("end_date", ""))
        key_points = "".join(
            f"<li>{_e(kp)}</li>" for kp in item.get("key_points", [])
        )
        key_points_html = f"<ul class='key-points'>{key_points}</ul>" if key_points else ""
        rows.append(f"""
        <div class="exp-item">
          <div class="exp-header">
            <strong>{_e(item.get("role", ""))}</strong> at {_e(item.get("company", ""))}
            <span class="dates">{_e(item.get("start_date", ""))} – {end}</span>
          </div>
          <p class="exp-description">{_e(item.get("description", ""))}</p>
          {key_points_html}
        </div>""")
    return f'<section class="section" id="experience"><h2 class="section-title">Experience</h2>{"".join(rows)}</section>'


def _render_projects(data: dict) -> str:
    items = data.get("projects", [])
    if not items:
        return ""
    cards = []
    for item in items:
        tech = "".join(f'<span class="tech-tag">{_e(t)}</span>' for t in item.get("tech_stack", []))
        live_url = _safe_url(item.get("project_url", ""))
        github_url = _safe_url(item.get("github_repo", ""))
        links = ""
        if live_url:
            links += f'<a href="{live_url}" target="_blank">Live</a> '
        if github_url:
            links += f'<a href="{github_url}" target="_blank">GitHub</a>'
        cards.append(f"""
        <div class="project-card">
          <h3>{_e(item.get("title", ""))}</h3>
          <p>{_e(item.get("description", ""))}</p>
          <div class="tech-stack">{tech}</div>
          <div class="project-links">{links}</div>
        </div>""")
    return f'<section class="section" id="projects"><h2 class="section-title">Projects</h2>{"".join(cards)}</section>'


def _render_skills(data: dict) -> str:
    groups = data.get("skill_groups", [])
    if not groups:
        return ""
    html_parts = []
    for group in groups:
        tags = "".join(f'<span class="skill-tag">{_e(s)}</span>' for s in group.get("skills", []))
        html_parts.append(f'<div class="skill-group"><strong>{_e(group.get("category", ""))}</strong><div class="skill-tags">{tags}</div></div>')
    return f'<section class="section" id="skills"><h2 class="section-title">Skills</h2>{"".join(html_parts)}</section>'


def _render_education(data: dict) -> str:
    items = data.get("education", [])
    if not items:
        return ""
    rows = "".join(f"""
        <div class="list-card">
          <strong>{_e(item.get("degree", ""))} in {_e(item.get("field_of_study", ""))}</strong>
          <span>{_e(item.get("institution", ""))} · {_e(item.get("start_year", ""))}–{_e(item.get("end_year", ""))}</span>
        </div>""" for item in items)
    return f'<section class="section" id="education"><h2 class="section-title">Education</h2>{rows}</section>'


def _render_certifications(data: dict) -> str:
    items = data.get("certifications", [])
    if not items:
        return ""
    rows = "".join(f"""
        <div class="list-card">
          <strong>{_e(item.get("name", ""))}</strong>
          <span>{_e(item.get("issuer", ""))} · {_e(item.get("year", ""))}</span>
        </div>""" for item in items)
    return f'<section class="section" id="certifications"><h2 class="section-title">Certifications</h2>{rows}</section>'


def _render_achievements(data: dict) -> str:
    items = data.get("achievements", [])
    if not items:
        return ""
    rows = "".join(f"""
        <div class="list-card">
          <strong>{_e(item.get("title", ""))}</strong>
          <p>{_e(item.get("description", ""))}</p>
        </div>""" for item in items)
    return f'<section class="section" id="achievements"><h2 class="section-title">Achievements</h2>{rows}</section>'


def _render_awards(data: dict) -> str:
    items = data.get("awards", [])
    if not items:
        return ""
    rows = "".join(f"""
        <div class="list-card">
          <strong>{_e(item.get("title", ""))}</strong>
          <span>{_e(item.get("awarding_body", ""))} · {_e(item.get("year", ""))}</span>
        </div>""" for item in items)
    return f'<section class="section" id="awards"><h2 class="section-title">Awards</h2>{rows}</section>'


def _render_campaigns(data: dict) -> str:
    items = data.get("campaigns", [])
    if not items:
        return ""
    cards = []
    for item in items:
        channels = ", ".join(_e(c) for c in item.get("channels_used", []))
        metrics = "".join(f"<li>{_e(m)}</li>" for m in item.get("performance_metrics", []))
        cards.append(f"""
        <div class="list-card">
          <strong>{_e(item.get("campaign_name", ""))}</strong>
          <span>{_e(item.get("campaign_type", ""))} · {channels}</span>
          <ul>{metrics}</ul>
        </div>""")
    return f'<section class="section" id="campaigns"><h2 class="section-title">Campaigns</h2>{"".join(cards)}</section>'


def _render_financial_modeling(data: dict) -> str:
    items = data.get("financial_modeling", [])
    if not items:
        return ""
    rows = "".join(f"""
        <div class="list-card">
          <strong>{_e(item.get("model_type", ""))}</strong>
          <p>{_e(item.get("outcome", ""))}</p>
        </div>""" for item in items)
    return f'<section class="section" id="financial_modeling"><h2 class="section-title">Financial Modeling</h2>{rows}</section>'


def _render_investment_portfolios(data: dict) -> str:
    items = data.get("investment_portfolios", [])
    if not items:
        return ""
    rows = "".join(f"""
        <div class="list-card">
          <strong>{_e(item.get("portfolio_type", ""))}</strong>
          <span>AUM: {_e(item.get("assets_under_management", ""))} · Return: {_e(item.get("performance_return", ""))}</span>
        </div>""" for item in items)
    return f'<section class="section" id="investment_portfolios"><h2 class="section-title">Investment Portfolios</h2>{rows}</section>'


def _render_design_philosophy(data: dict) -> str:
    text = data.get("design_philosophy", "")
    if not text:
        return ""
    return f'<section class="section" id="design_philosophy"><h2 class="section-title">Design Philosophy</h2><p>{_e(text)}</p></section>'


def _render_software_proficiency(data: dict) -> str:
    tools = data.get("software_proficiency", [])
    if not tools:
        return ""
    tags = "".join(f'<span class="skill-tag">{_e(t)}</span>' for t in tools)
    return f'<section class="section" id="software_proficiency"><h2 class="section-title">Software Proficiency</h2><div class="skill-tags">{tags}</div></section>'
```

---

## Section B — JS Template: `inlineEditingScript()` and `editingOverlayCSS()`

Copy these verbatim into your JS template file. They implement the full editing protocol.

```javascript
export function editingOverlayCSS() {
  return `
    .editable { cursor: text; border-radius: 3px; transition: outline 0.15s; }
    .editable:hover { outline: 2px dashed #3b82f6; outline-offset: 2px; }
    .editable:focus { outline: 2px solid #2563eb; outline-offset: 2px; }
    .section-highlight { animation: section-flash 1s ease-out; }
    @keyframes section-flash {
      0%   { background: rgba(59,130,246,0.18); }
      100% { background: transparent; }
    }
  `;
}

export function inlineEditingScript() {
  return `
    (function() {
      // Make all .editable elements contenteditable
      document.querySelectorAll('.editable').forEach(function(el) {
        el.setAttribute('contenteditable', 'true');
        el.setAttribute('spellcheck', 'false');

        // On focus: tell the parent frame which field is active
        el.addEventListener('focus', function() {
          window.parent.postMessage({
            type: 'field-focus',
            field:   el.dataset.field,
            section: el.dataset.section,
            index:   el.dataset.index !== undefined ? parseInt(el.dataset.index) : null,
            path:    el.dataset.path,
          }, '*');
        });

        // On input: sync value to parent frame in real time
        el.addEventListener('input', function() {
          window.parent.postMessage({
            type:    'field-change',
            field:   el.dataset.field,
            section: el.dataset.section,
            index:   el.dataset.index !== undefined ? parseInt(el.dataset.index) : null,
            path:    el.dataset.path,
            value:   el.innerText,
          }, '*');
        });

        // On blur: trigger save
        el.addEventListener('blur', function() {
          window.parent.postMessage({
            type:    'field-blur',
            field:   el.dataset.field,
            section: el.dataset.section,
            index:   el.dataset.index !== undefined ? parseInt(el.dataset.index) : null,
            path:    el.dataset.path,
            value:   el.innerText,
          }, '*');
        });
      });

      // Listen for messages FROM the parent frame
      window.addEventListener('message', function(event) {
        var msg = event.data;

        // Parent updated a field — update the matching element
        if (msg.type === 'field-update') {
          var el = document.querySelector(
            '[data-path="' + msg.path + '"]'
          );
          if (el && document.activeElement !== el) {
            el.innerText = msg.value;
          }
        }

        // Scroll to a section (left panel click)
        if (msg.type === 'scroll-to-section') {
          var target = document.getElementById(msg.section)
                    || document.querySelector('[data-section="' + msg.section + '"]');
          if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            target.classList.add('section-highlight');
            setTimeout(function() { target.classList.remove('section-highlight'); }, 1000);
          }
        }

        // Section reorder: reorder DOM elements inside <main>
        if (msg.type === 'reorder-sections') {
          var main = document.querySelector('main');
          if (main) {
            msg.order.forEach(function(sectionId) {
              var sec = document.getElementById(sectionId);
              if (sec) main.appendChild(sec);
            });
          }
        }

        // Section visibility: show/hide
        if (msg.type === 'toggle-section') {
          var sec = document.getElementById(msg.section);
          if (sec) sec.style.display = msg.visible ? '' : 'none';
        }
      });
    })();
  `;
}
```

---

## Section C — JS Template: Escaping Utility

```javascript
function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function safeUrl(url) {
  if (!url) return '';
  url = String(url).trim();
  return (url.startsWith('http://') || url.startsWith('https://')) ? esc(url) : '';
}
```

---

## Section D — Edit Page: Handling Preview Messages (SvelteKit)

In `src/routes/app/portfolio/[userId]/edit/+page.svelte`, the message handler listens to the preview iframe. Verify this block exists and handles all message types:

```typescript
function handlePreviewMessage(event: MessageEvent) {
  const msg = event.data;

  if (msg.type === 'field-focus') {
    // Scroll center panel to the matching field and focus it
    scrollCenterPanelToField(msg.section, msg.field, msg.index);
    highlightLeftPanelSection(msg.section);
  }

  if (msg.type === 'field-change') {
    // Update local state with the new value (optimistic, no save yet)
    setNestedValue(portfolioData, msg.path, msg.value);
  }

  if (msg.type === 'field-blur') {
    // Commit the value and trigger auto-save
    setNestedValue(portfolioData, msg.path, msg.value);
    triggerAutoSave(msg.section, msg.field, msg.index);
  }
}

// Send updates from form → preview
function syncFieldToPreview(path: string, value: string) {
  previewIframe?.contentWindow?.postMessage({
    type: 'field-update',
    path,
    value,
  }, '*');
}

// Send section scroll request from left panel → preview  
function scrollPreviewToSection(sectionId: string) {
  previewIframe?.contentWindow?.postMessage({
    type: 'scroll-to-section',
    section: sectionId,
  }, '*');
}
```

---

## Section E — `render_section_in_order` Python Utility

If this utility doesn't exist in `src/backend/portfolio/utils.py`, add it:

```python
def render_section_in_order(
    data: dict,
    renderers: dict,
    section_order: list = None,
    hidden_sections: list = None,
) -> str:
    order = section_order or data.get("section_order") or list(renderers.keys())
    hidden = set(hidden_sections or data.get("hidden_sections") or [])
    parts = []
    for key in order:
        if key in hidden or key not in renderers:
            continue
        result = renderers[key](data)
        if result:
            parts.append(result)
    return "\n".join(parts)
```
