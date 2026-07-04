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

---

## Section Z — Editable-List Pitfalls (learned from marketing + designer + designer-2)

These bugs all shipped in the marketing/designer/designer-2 templates and had to be
fixed afterward. **Check every one of these before considering a new template done.**

### Z1. Never `.slice(0, N)` an editable list field

The right-side edit pane lets users add an unlimited number of items to any list field
(`key_points`, `responsibilities`, `measurable_outcomes`, `tech_stack`, `software_used`,
`performance_metrics`, `channels_used`, `channels_managed`, `skill_groups`, a skill
group's `skills`, custom-section `tags`, …). If the template renders only
`field.slice(0, 3).map(...)`, items beyond the cap are stored but never shown.

Classic symptom the user reports: *"I added 2 more points but only the first 3 show —
if I delete the 1st, then 2/3/4 appear."* That is a `.slice()` cap, not a data problem.

```js
// ❌ WRONG — truncates user content
${c.performance_metrics.slice(0, 3).map(m => `<div>${m}</div>`).join('')}
// ✅ RIGHT — render all
${c.performance_metrics.map(m => `<div>${m}</div>`).join('')}
```

**Exception — decorative/aggregate/teaser renders MAY keep a slice.** These are NOT the
canonical editable region (they carry no `le()` binding) and have a fixed visual budget:
name initials (`slice(0,2)`), project banner icons, hero bio ellipsis
(`bio.slice(0,120)+'…'`), a marquee "skill belt", an About-section "highlights" teaser,
image carousels. Removing those slices bloats the design and fixes nothing. Rule of
thumb: **if the region has an `le()`/`_listEditable()` binding, it must render ALL items;
if it's a no-binding decorative summary, a slice is fine.**

### Z2. One editable region ↔ exactly ONE field (never blend)

The inline list editor (`openListEditor` in the edit page) reads its items from
`data[field]`, where `field` is parsed from the region's `data-list-path`. Therefore a
region bound to `experience.${i}.X` can only ever edit field `X`. Two failure modes we hit:

- **marketing** rendered `key_points` *blended into* the `channels_managed` chips region
  (`le(experience.${i}.channels_managed)`). Result: key_points weren't inline-editable,
  and clicking the region opened the (usually empty) `channels_managed` editor → user saw
  **no points**. It was also capped at 2.
- **designer** rendered `[...tech_stack, ...software_used]` inside one region bound to
  `tech_stack`. `software_used` (a separate editable field) had no region of its own and
  was not editable; clicking showed only `tech_stack`.

```js
// ❌ WRONG — two fields in one region bound to just one of them
<div ${le(`experience.${i}.channels_managed`)}>${[...channels_managed, ...key_points].map(...)}</div>

// ✅ RIGHT — each field gets its OWN correctly-bound region, each rendering all items
${exp.channels_managed?.length ? `<div ${le(`experience.${i}.channels_managed`)}>${exp.channels_managed.map(...).join('')}</div>` : ''}
${exp.key_points?.length        ? `<div ${le(`experience.${i}.key_points`)}>${exp.key_points.map(...).join('')}</div>`        : ''}
```

### Z3. The `data-list-path` must match the field whose data you render

A region bound to field A but displaying field B's data means: the preview shows B, but
clicking edits A (and `openListEditor` reads A's array). Always verify
`le(\`section.${i}.FIELD\`)` uses the **same** `FIELD` as the `data.FIELD.map(...)` inside it.

### Z4. Every editable list field you DISPLAY needs its own `le()` region

If you show a list field's data but wrap it in a plain `<div>` (no `le()`), it renders
fine but is not click-to-edit in the preview, and right-pane edits can look like they
"don't take" inline. Either give it an `le()` region or intentionally leave it display-only
— but decide consciously. (It's fine for a template not to display a field at all; the bug
is displaying it bound to the *wrong* field.)

### Z5. Cross-check fields against the edit-page SECTION_CONFIG

Before finishing, open `…/edit/+page.svelte` `SECTION_CONFIG` and confirm: every list
field marked `inputType: 'list'` for the sections your template renders either (a) has its
own correctly-bound `le()` region rendering all items, or (b) is deliberately not shown.
`tech_stack`, `software_used`, `responsibilities`, `measurable_outcomes`, `key_points`,
`performance_metrics`, `channels_used` are all independent list fields — never merge them.

### Z6. Use the standard gating convention

Editable list regions follow `${item.field?.length ? \`<div ${le(path)}>…</div>\` : ''}`.
The `le` helper is usually `const le = (path) => em ? _listEditable(path) : '';` so the
`data-list-path` only appears in edit mode.

### Z7. Don't forget the deploy pipeline

Template edits live in the frontend repo but are bundled into the portfolio-generator
Lambda. The **edit-page preview updates instantly**, but **published** portfolios only
change after `bash build-portfolio-lambda.sh` + `terraform apply` (and they re-render on
next publish — existing static HTML in S3 is not rewritten retroactively). Always run the
build + apply after touching any template `.ts`.

### Z8. Reproduce the FULL design — all styling AND animations, not a subset

The most common complaint on these three templates: the structure/markup was copied but
**most animations and several styling details were dropped**, so the result looked flat
versus the source design and had to be revised. Do **not** port "just a few elements" —
carry the design over in full.

When implementing a template from a design/HTML source, port **every** visual layer:

- **All `@keyframes` and the elements that use them.** These templates animate heavily —
  `riseUp`, `floatIn`, `drift`, `floatBob`, `drip`, `widen`, etc. If you copy an element
  but omit its `animation:` rule (or the `@keyframes` block), it renders static. Copy the
  keyframes AND apply them to the matching elements.
- **Scroll-in reveals.** Elements use `class="reveal"` (often with stagger classes like
  `d1`/`d2`) plus an `opacity:0` start state that a runtime IntersectionObserver flips to
  visible. Every new section/element that should animate in needs the `reveal` class —
  and verify the observer actually targets it. ⚠️ An element left at `opacity:0` whose
  reveal never fires is **invisible**, not just un-animated. Check this in BOTH edit-preview
  and published mode.
- **Hover states & transitions.** `transition:` rules, hover color/transform effects,
  custom cursor behavior — apply them to the new elements too, matching sibling elements.
- **Decorative elements.** Orbs, gradients, marquees, floating shapes, dividers — these are
  part of the design, not optional filler. Port them.
- **Responsive `@media` breakpoints.** Every section needs its mobile/tablet rules or the
  layout breaks on small screens.

Rule: **structure + styling + animation are one deliverable.** After building, diff your
template against the source design and confirm each animation and decorative/style element
is present — a faithful clone, not a skeleton. When you reuse an existing CSS class for new
markup (e.g. reusing `.camp-metrics` for `key_points`), confirm that class actually carries
the intended look in that context.

---

## Section Z2 — Bugs shipped on the `glitch` template (fix these up front next time)

Every one of these was a real defect reported by the user *after* "done" on the glitch
software-engineer template. They are cheap to get right the first time — check each one.

### Z9. Bind editable scalars to REAL data-paths, never to computed display fields

`normalize()` synthesizes some display-only fields that have **no backing form input** and get
**recomputed on every re-render** — so any inline edit to them is silently reverted and never
reaches the center form.

- **`experience[i].duration`** is computed from `start_date`/`end_date`. ❌ Binding
  `_editable(\`experience.${i}.duration\`)` means typing a date does nothing (form pane doesn't
  update, value reverts). ✅ Render TWO editable spans bound to the real fields:
  ```js
  ${exp.duration ? `<span class="exp-period">${exp.start_date ? `<span ${_editable(`experience.${i}.start_date`)}>${exp.start_date}</span>` : ''}${exp.start_date && exp.end_date ? ' &ndash; ' : ''}${exp.end_date ? `<span ${_editable(`experience.${i}.end_date`)}>${exp.end_date}</span>` : ''}</span>` : ''}
  ```
  The edit page's `updateFieldFromIframe` maps `{section}.{i}.{field}` straight to the form item,
  so `start_date`/`end_date` round-trip and sync; `duration` does not exist as a field.
- General rule: a `data-path` is only valid if it names a key that exists in that section's
  `SECTION_CONFIG.fields` (or `profile.*` / `portfolio.*` / `template_overrides.*`). Cross-check
  before binding.

### Z10. There are TWO distinct "headline" fields — bind both, to the right paths

- **`profile.headline`** = the raw professional title (form label "Professional Title",
  element `rp-headline`). Exposed in `normalize` as `v.profile_headline`.
- **`portfolio.headline`** = the AI-written headline (form label "Professional Headline",
  element `pf-headline`). Exposed as `v.headline`.

If your hero shows a small "title/tag" line AND a larger headline, they are different fields:
bind the tag with `_editable('profile.headline')` and the headline with
`_editable('portfolio.headline')`. A common miss is rendering the title as a plain
(non-editable) decorative tag — users expect to edit it. Profile contact fields use
`profile.email` / `profile.phone` / `profile.location`; bio uses `portfolio.bio`.

### Z11. Render `images[]` for experience AND projects — they are real, uploadable fields

Both `experience` and `projects` carry an `images` array (`inputType: 'images'`, max 3),
uploaded via the form's image uploader and normalized to safe URLs in `v.*.images`. A template
that never renders them looks broken ("I uploaded an image but nothing shows"). Display them
where the **design** puts its project visual (don't invent a spot) — confirm placement against
the source/screenshot.

### Z12. Multiple images = a looping crossfade slideshow, not a vertical stack

When an item has >1 image, cycle through ALL of them on a timer (1→2→3→4→1…), don't stack them.
Overlay them in one fixed-aspect frame and crossfade via a tiny script in the template's own
`<script>` (runs in both edit-preview and published mode):
```css
.shots{position:relative;width:100%;aspect-ratio:4/3;overflow:hidden}
.shots img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .7s}
.shots img.active{opacity:1}
```
```js
document.querySelectorAll('.shots').forEach(function(box){
  var imgs=box.querySelectorAll('img'); if(imgs.length<2)return; var i=0;
  setInterval(function(){imgs[i].classList.remove('active');i=(i+1)%imgs.length;imgs[i].classList.add('active');},3000);
});
```
First image gets `.active`; add position dots for polish. Single image renders statically.

### Z13. Gate the custom cursor (and any `cursor:none`) to published mode only

If the design hides the native cursor (`body{cursor:none}` + a JS-driven custom cursor dot),
that makes inline editing unusable in the editor. Only emit the cursor markup and the
`cursor:none` rule when `!v.edit_mode`; pass `v.edit_mode` into `css()` and guard the cursor
`<div>`s. Any "fancy pointer" interaction gets the same treatment.

### Z14. One `<section id="{key}">` per orderable section — never merge two sections

Section reorder/visibility works by matching top-level `<section id>` against `section_order` /
`hidden_sections`. A source design that visually combines two of our sections (e.g.
Education + Certifications in one block) MUST still be split into separate `<section>` elements,
or reordering/hiding one of them breaks. Style them to look cohesive if needed, but keep them
as distinct sections wired through the `sectionMap` + ordered-render loop.

### Z15. Drop design features with no data backing; add sections our model needs

- A purely decorative interactive control that has no field behind it (e.g. a "bio length"
  slider switching between 5 hardcoded paragraphs) does NOT map to our single editable `bio` —
  drop it rather than ship a dead control.
- Conversely, render every section our data model expects even if the source design omits it
  (e.g. a software-engineer design with no Experience block — we still need `experience`,
  `skills`, `projects`, etc. all handled). Use the closest existing template as the section
  checklist.
