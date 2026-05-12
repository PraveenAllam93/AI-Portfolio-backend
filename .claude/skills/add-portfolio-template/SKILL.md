---
name: add-portfolio-template
description: >
  Implements a complete new portfolio template for the AI Portfolio Platform end-to-end —
  from a design input (screenshots or HTML) all the way through backend Python rendering,
  frontend JS preview, upload wizard registration, and edit-page inline editing with
  full bidirectional sync. Use this skill whenever the user says "add a new template",
  "implement this design as a template", "create a template from this screenshot/HTML",
  or provides any visual design and asks to wire it into the portfolio system. This skill
  touches every layer: backend Lambda, frontend SvelteKit, upload wizard, template dropdown,
  and the three-panel edit page (left section manager, center form, right preview).
---

# Add Portfolio Template — End-to-End Skill

## Overview

Adding a new template requires changes across **6 integration points**. This skill walks through every one. Always complete them in order — skipping any step will leave the template partially wired.

**Template ID convention:** lowercase, hyphen-separated, max 20 chars (e.g., `prisma`, `slate-pro`).

---

## Inputs You Receive

The user will provide one or more of:
- **Screenshots** — visual design reference (one or more viewport shots)
- **HTML/CSS file** — a static design mockup to adapt
- **Template ID + name** — what to call the new template
- **Target profession(s)** — optional, which categories it suits best

If the template ID or name is not provided, derive a sensible one from the design's visual character.

---

## Files to Create / Modify

| # | File | Action |
|---|------|--------|
| 1 | `src/backend/portfolio/templates/{id}.py` | **CREATE** — Python renderer |
| 2 | `src/backend/portfolio/handler.py` | **MODIFY** — register template dispatch |
| 3 | `src/lib/templates/index.ts` | **MODIFY** — add to template registry |
| 4 | `src/routes/app/resumes/upload/+page.svelte` | **MODIFY** — add card to Step 3 grid |
| 5 | `src/lib/templates/{id}.js` | **CREATE** — JS preview renderer |
| 6 | `src/routes/app/portfolio/[userId]/edit/+page.svelte` | **MODIFY** — template dropdown option |

Read `references/code-patterns.md` for exact code shapes before writing any file.

---

## Step 1 — Analyze the Design Input

Before writing any code, extract a **design spec** from the provided screenshots/HTML:

```
- Layout: single-column | two-column | sidebar | full-bleed hero | cards
- Color scheme: primary, secondary, background, text, accent
- Typography: font families, heading sizes, body size, weight usage
- Section order (default): how sections are visually arranged
- Hero/header style: how name, headline, photo are presented
- Section headers: style — underline, background band, icon, pill badge
- Card style (if any): border, shadow, radius, padding
- Special elements: timelines, skill bars, tag chips, dividers
- Dark/light: background tone
```

Use this spec as your source of truth for both the Python renderer (Step 2) and the JS preview (Step 5).

---

## Step 2 — Build the Backend Python Template

**File:** `src/backend/portfolio/templates/{id}.py`

Every template exports exactly two functions: `html(data: dict) -> str` and `css() -> str`.

```python
# Template data contract — always available in `data`:
# data["name"], data["headline"], data["bio"], data["email"]
# data["phone"], data["location"], data["profile_image"]
# data["linkedin_url"], data["github_url"], data["portfolio_url"], data["twitter_url"]
# data["skill_groups"]       → [{"category": str, "skills": [str]}]
# data["experience"]         → list of experience dicts
# data["projects"]           → list of project dicts
# data["education"]          → list of education dicts
# data["certifications"]     → list of dicts
# data["achievements"]       → list of dicts
# data["awards"]             → list of dicts  (Designer only)
# data["campaigns"]          → list of dicts  (Marketing only)
# data["financial_modeling"] → list of dicts  (Finance only)
# data["investment_portfolios"] → list of dicts (Finance only)
# data["design_philosophy"]  → str            (Designer only)
# data["software_proficiency"] → [str]         (Designer only)
# data["category"]           → "software_engineer"|"designer"|"marketing"|"finance"
# data["section_order"]      → [str]  ordered list of section keys
# data["hidden_sections"]    → [str]  sections to skip rendering
```

**Critical rules (never violate):**
- ALL user strings must pass through `_e()` (HTML-escape helper) before insertion into HTML
- ALL URLs must be validated: only `http://` and `https://` prefixes allowed
- Output is **static HTML + embedded CSS only** — zero JavaScript
- Import the shared helpers at the top: `from .utils import _e, _safe_url, render_section_in_order`

See `references/code-patterns.md` → Section A for a full annotated Python template skeleton.

**Section rendering order:** Always iterate `data["section_order"]` and skip any key in `data["hidden_sections"]`. Use the helper:

```python
def html(data):
    sections_html = render_section_in_order(data, {
        "experience":           _render_experience,
        "projects":             _render_projects,
        "skills":               _render_skills,
        "education":            _render_education,
        "certifications":       _render_certifications,
        "achievements":         _render_achievements,
        "awards":               _render_awards,              # designer
        "campaigns":            _render_campaigns,           # marketing
        "financial_modeling":   _render_financial_modeling,  # finance
        "investment_portfolios":_render_investment_portfolios,
        "design_philosophy":    _render_design_philosophy,   # designer
        "software_proficiency": _render_software_proficiency,# designer
    }, data["section_order"], data["hidden_sections"])
    return f"""<!DOCTYPE html>..."""
```

---

## Step 3 — Register in Backend Dispatch

**File:** `src/backend/portfolio/handler.py`

Find the template dispatch block (a dict or if/elif chain) and add the new template:

```python
# Find the existing import block and add:
from .templates import {id} as tpl_{id}

# Find the TEMPLATE_MAP dict and add:
TEMPLATE_MAP = {
    "minimal": tpl_minimal,
    # ... existing templates ...
    "{id}": tpl_{id},   # ← ADD THIS LINE
}
```

---

## Step 4 — Add to Frontend Template Registry

**File:** `src/lib/templates/index.ts`

```typescript
export const TEMPLATES = [
  // ... existing entries ...
  {
    id: "{id}",
    name: "{Display Name}",
    tags: ["{Tag1}", "{Tag2}"],          // e.g. "Dark", "Creative", "Clean"
    thumbnail: "/thumbnails/{id}.png",   // add screenshot to static/thumbnails/
    bestFor: ["software_engineer"],      // which categories suit this best (optional hint)
  },
] as const;

export type TemplateId = typeof TEMPLATES[number]["id"];
```

**Also:** Drop the thumbnail screenshot (400×280px recommended) at `static/thumbnails/{id}.png`.

---

## Step 5 — Add Card to Upload Wizard Step 3

**File:** `src/routes/app/resumes/upload/+page.svelte`

Find the template grid section (Step 3). The TEMPLATES array from `index.ts` already drives the grid, so adding the entry in Step 4 is usually sufficient. Verify:

1. Import uses `TEMPLATES` from `$lib/templates/index.ts`
2. Grid renders `{#each TEMPLATES as template}` — if so, Step 4 is enough.
3. If templates are hardcoded, add a card manually following the existing pattern.

---

## Step 6 — Build the Frontend JS Preview Template

**File:** `src/lib/templates/{id}.js`

This is the **most critical frontend file**. It renders the same visual design as the Python template but in JavaScript for the live edit-page preview. It must:
- Accept the same normalized `data` object shape
- Mark every editable element with `data-field` and `data-section` attributes
- Support inline editing (contenteditable on hover/click)
- Emit `field-change` events that the edit page listens to

```javascript
// src/lib/templates/{id}.js

/**
 * Render the full template preview HTML string.
 * @param {Object} data - Normalized portfolio data (same shape as Python template)
 * @returns {string} - Full HTML document string
 */
export function render(data) {
  const sections = renderSectionsInOrder(data);
  return `
    <html>
      <head>
        <style>${css()}</style>
        <style>${editingOverlayCSS()}</style>
      </head>
      <body>
        ${renderHero(data)}
        <main>${sections}</main>
        <script>${inlineEditingScript()}</script>
      </body>
    </html>
  `;
}

export function css() {
  // Return the same CSS as the Python template's css() function (ported to a JS string)
  return `/* ... */`;
}
```

**Editable element markup pattern** — every editable text node must have these attributes:

```javascript
function renderHero(data) {
  return `
    <header>
      <h1
        data-field="name"
        data-section="profile"
        data-path="parsedData.profile.full_name"
        class="editable"
      >${esc(data.name)}</h1>
      <p
        data-field="headline"
        data-section="profile"
        data-path="portfolioContent.headline"
        class="editable"
      >${esc(data.headline)}</p>
      <p
        data-field="bio"
        data-section="profile"
        data-path="portfolioContent.bio"
        class="editable"
      >${esc(data.bio)}</p>
    </header>
  `;
}

// Experience items — note data-index for array items
function renderExperienceItem(item, index) {
  return `
    <div class="exp-item" data-section="experience" data-index="${index}">
      <p
        data-field="description"
        data-section="experience"
        data-index="${index}"
        data-path="parsedData.experience[${index}].description"
        class="editable"
      >${esc(item.description)}</p>
    </div>
  `;
}
```

**Section visibility and ordering** — mirror the Python template's section_order logic:

```javascript
function renderSectionsInOrder(data) {
  const renderers = {
    experience:            () => renderExperience(data),
    projects:              () => renderProjects(data),
    skills:                () => renderSkills(data),
    education:             () => renderEducation(data),
    certifications:        () => renderCertifications(data),
    achievements:          () => renderAchievements(data),
    awards:                () => renderAwards(data),
    campaigns:             () => renderCampaigns(data),
    financial_modeling:    () => renderFinancialModeling(data),
    investment_portfolios: () => renderInvestmentPortfolios(data),
    design_philosophy:     () => renderDesignPhilosophy(data),
    software_proficiency:  () => renderSoftwareProficiency(data),
  };
  return (data.section_order || Object.keys(renderers))
    .filter(k => !(data.hidden_sections || []).includes(k) && renderers[k])
    .map(k => renderers[k]())
    .join('');
}
```

Read `references/code-patterns.md` → Section B for the full `inlineEditingScript()` and `editingOverlayCSS()` implementations which must be copied verbatim (they handle event delegation, contenteditable, and field-change dispatch).

---

## Step 7 — Wire Edit Page Integration

**File:** `src/routes/app/portfolio/[userId]/edit/+page.svelte`

### 7a — Add to Template Dropdown

```svelte
<!-- In the top bar template <select> -->
{#each TEMPLATES as tpl}
  <option value={tpl.id}>{tpl.name}</option>
{/each}
```

If hardcoded, add: `<option value="{id}">{Display Name}</option>`

### 7b — Import the JS Renderer

```typescript
// In the <script> block, add to the template renderer map:
import { render as render_{camelId} } from '$lib/templates/{id}.js';

const TEMPLATE_RENDERERS: Record<string, (data: any) => string> = {
  minimal:   render_minimal,
  // ... existing ...
  {id}:      render_{camelId},   // ← ADD
};
```

### 7c — Verify Bidirectional Sync

The edit page already has a universal sync system. Verify these hooks exist and your template's `data-field` / `data-path` attributes match what the sync system expects:

**Preview → Form (clicking in preview opens form field):**
The preview iframe dispatches `field-change` events. The edit page listens and scrolls the center panel to the matching field. Your `data-path` attribute must exactly match the field path used in the form.

**Form → Preview (typing in form updates preview):**
The edit page calls `TEMPLATE_RENDERERS[templateId](data)` and injects the result into the preview iframe whenever local state changes. No additional wiring needed — as long as your renderer is in the map.

**Left panel → Preview scroll:**
Clicking a section in the left panel posts a message to the preview iframe: `{ type: 'scroll-to-section', section: 'experience' }`. Your JS template's `inlineEditingScript()` must handle this message and scroll to the element with `data-section="experience"`. This is included in the shared script from `references/code-patterns.md`.

---

## Step 8 — Verification Checklist

After all files are written, run through this checklist:

```
□ Python template renders valid HTML for all 4 profession categories
□ All user strings are HTML-escaped (_e()) in the Python template
□ No <script> tags in the Python template output (CSP: script-src 'none')
□ Template appears in upload wizard Step 3 grid with thumbnail
□ Selecting template in upload wizard passes correct templateId to API
□ Template appears in edit page dropdown
□ Switching to template in edit page triggers re-render (loading overlay appears, preview updates)
□ All editable fields in JS template have correct data-field, data-section, data-path, data-index
□ Clicking an element in the preview scrolls the center form to that field
□ Typing in the center form updates the preview in real time
□ Typing in the preview (inline edit) updates the center form field value
□ Clicking a section in the left panel scrolls the preview to that section + flash highlight
□ Section reordering in left panel immediately reorders sections in preview
□ Toggling section visibility in left panel immediately shows/hides in preview
□ Template thumbnail exists at static/thumbnails/{id}.png
□ Template entry in TEMPLATES registry has correct tags and name
```

---

## Reference Files

- `references/code-patterns.md` — Full code skeletons for Python template, JS template, `inlineEditingScript()`, `editingOverlayCSS()`, and `render_section_in_order` utility. **Read this before writing any template code.**
