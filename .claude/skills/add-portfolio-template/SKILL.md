---
name: add-portfolio-template
description: >
  Implements a complete new portfolio template for the AI Portfolio Platform end-to-end —
  from a design input (screenshots or HTML) all the way through a single unified TypeScript
  template (shared by the live editor preview AND the bundled portfolio-generator Lambda),
  upload-wizard registration, backend allowlists, and edit-page inline editing with
  full bidirectional sync. Use this skill whenever the user says "add a new template",
  "implement this design as a template", "create a template from this screenshot/HTML",
  or provides any visual design and asks to wire it into the portfolio system. This skill
  touches every layer: backend Lambda, frontend SvelteKit, upload wizard, template dropdown,
  and the three-panel edit page (left section manager, center form, right preview).
---

# Add Portfolio Template — End-to-End Skill

## Overview

The system uses **ONE unified TypeScript template per design**, shared by BOTH the live
editor preview and the published portfolio. There is no Python renderer and no separate
`.js` preview file. Adding a template is a handful of edits across the frontend + backend,
plus a bundle-and-deploy step. Complete them in order — skipping any leaves the template
partially wired.

**Template ID convention:** lowercase, hyphen-separated, max 20 chars (e.g., `prisma`, `slate-pro`).

**Before writing anything, verify the live layout** (it evolves): `ls src/lib/templates/`,
read `index.ts` and `base.ts`, and read the closest existing template (e.g. `circuit.ts` for
a dark software-engineer theme) end-to-end. Model your new file on it: copy its
section-renderer structure, editable bindings, section-ordering loop, and `EDITOR_SCRIPT`
placement verbatim, then swap in your design's CSS/markup.

---

## How the pieces fit (verified architecture)

- **Templates live ONLY in the frontend repo:** `AI-Portfolio-frontend/src/lib/templates/{id}.ts`.
  Each exports a single `html(v: NormalizedData): string` plus a local `css()`, importing
  helpers from `./base` (`_editable`, `_listEditable`, `_imgUpload`, `_rangeEditable`,
  `_pairEditable`, `statShown`, `EDITOR_SCRIPT`, `DEFAULT_SECTION_ORDER`).
- **`normalize()` in `base.ts` is the ONLY place user data is HTML-escaped.** Template
  functions receive pre-escaped values — **do not** re-escape. `normalize()` also filters
  `section_order` to sections allowed for the record's profession (`sectionAllowedForCategory`).
- **The backend portfolio generator is TypeScript** (`AI-Portfolio-backend/src/lambdas/portfolio/handler.ts`),
  NOT Python. It calls `renderPortfolio()` from the SAME frontend templates. They are bundled
  into the Lambda at deploy time by **`bash build-portfolio-lambda.sh`** (copies
  `frontend/src/lib/templates/*.ts`, esbuild-bundles, zips).
- **The edit-preview updates instantly; PUBLISHED portfolios only change after
  `build-portfolio-lambda.sh` + `terraform apply`** (and re-render on next publish — existing
  static HTML in S3 is not rewritten retroactively).
- **The edit page needs NO direct edits.** Its template picker, profession filter, stat
  panel, Portfolio Fields tab, image-upload handling, and custom-section controls are all
  data-driven from `index.ts` (`TEMPLATE_META`, `TEMPLATE_FIELDS`, the feature sets) and its
  own `SECTION_CONFIG`. Register the template in `index.ts` and it appears automatically.

## Files to create / modify (authoritative)

| # | File (repo) | Action |
|---|------|--------|
| 1 | `frontend: src/lib/templates/{id}.ts` | **CREATE** — the whole template (`html()` + `css()`) |
| 2 | `frontend: src/lib/templates/index.ts` | **MODIFY** — `import`; add to `TEMPLATES` map, `TEMPLATE_META` (name/accent/**profession**), and (as needed) `TEMPLATE_FIELDS`, `CUSTOM_DISPLAY_TYPES`, `SUMMARY_IMAGE_TEMPLATES`, `CORE_EXPERTISE_TEMPLATES`, `CONTACT_TAGLINE_TEMPLATES`, `DEFAULT_CONTACT_TAGLINE` |
| 3 | `frontend: src/routes/app/resumes/upload/+page.svelte` | **MODIFY** — add a `{ id, name, tag }` entry to the **hardcoded** `TEMPLATES_BY_PROFESSION` array for the target profession (this grid is NOT driven by `index.ts`) |
| 4 | `backend: src/lambdas/upload/handler.py` | **MODIFY** — add `'{id}'` to `ALLOWED_TEMPLATES` |
| 5 | `backend: src/lambdas/auth/patch_portfolio.py` | **MODIFY** — add `'{id}'` to `_VALID_TEMPLATE_IDS` |
| 6 | `backend: src/lambdas/auth/generate_project_image.py` | **MODIFY (if dark theme)** — add `'{id}'` to `_DARK_TEMPLATES` so AI project images get a dark background |
| 7 | `backend: build-portfolio-lambda.sh` + `terraform apply` | **RUN** — bundle templates into the Lambda and deploy |

> **Both backend allowlists (#4, #5) gate the template ID server-side** — miss either and the
> user gets "Invalid templateId" (upload = #4; changing template from the edit page = #5).
> The edit page (`[userId]/[uploadId]/edit`) itself needs no code change.

> **WSL note:** `node` is installed via nvm and is NOT on the non-interactive PATH — source it
> first: `export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"` before `bash build-portfolio-lambda.sh`.

**Read `references/code-patterns.md` before writing any code** — it has the accurate TypeScript
template skeleton (Section A), the editable-binding cookbook (Section B), the data-model field
reference per profession (Section C), and the hard-won pitfall checklist (Sections Z1–Z16).

---

## Step 1 — Analyze the design input

Extract a **design spec** from the screenshots/HTML before writing code:

```
- Layout: single-column | two-column | sidebar | full-bleed hero | cards
- Color scheme: primary, secondary, background, text, accent (+ dark/light variants)
- Typography: font families (Google Fonts URL), heading/body sizes, weights
- Hero/header: how name, professional title, headline, photo are presented
- Section order + section header style (underline, band, icon, pill, mono tag)
- Card style: border, shadow, radius, padding
- Animations: @keyframes, scroll reveals, hover transitions, decorative shapes/orbs
- Stats shown in hero/about (years, projects, certs…) → drives TEMPLATE_FIELDS
- Any second image (summary/about) → drives SUMMARY_IMAGE_TEMPLATES
- Dark or light background → drives _DARK_TEMPLATES (backend AI image bg)
```

This spec is the source of truth for both the `css()` and `html()` you write. **Reproduce it in
FULL** — see Step 5 and pitfall Z8. A skeleton that drops animations/decorative elements is the
single most common complaint and will be sent back.

## Step 2 — Fit the profession's data model

A template is built for one profession (`TEMPLATE_META[id].profession`). Which sections a
profession has is fixed by `SECTION_CATEGORIES` in `base.ts` and mirrored by
`SECTION_CONFIG[*].categories` in the edit page. Universal sections render for everyone;
profession-specific ones only for their category:

| Profession | Profession-specific sections (beyond universal experience/skills/education/certifications/achievements/custom_sections) |
|---|---|
| `software_engineer` | `projects` |
| `designer` | `projects`, `awards`, `design_philosophy`, `software_proficiency` |
| `marketing` | `campaigns` |
| `finance` | `financial_modeling`, `investment_portfolios` |
| `civil_engineer` | `projects`, `software_proficiency` |
| `mechanical_engineer` | `projects`, `software_proficiency` |

Rules:
- **Render every section the profession's model expects**, even if the source design omits it
  (use the closest existing same-profession template as your section checklist). See Z15.
- **Do not render foreign-profession sections.** `normalize()` filters them out of
  `section_order`, but don't hand-render e.g. `campaigns` in a software-engineer template.
- Field names and shapes per section come from `NormalizedData` (base.ts) — see
  `references/code-patterns.md` Section C. Bind only to fields that actually exist for that
  section in `SECTION_CONFIG` (Z9).

## Step 3 — Create `src/lib/templates/{id}.ts`

Structure (see Section A for the full skeleton):

```ts
import type { NormalizedData } from './base';
import { DEFAULT_SECTION_ORDER, _editable, _listEditable, _imgUpload,
         _rangeEditable, _pairEditable, statShown, EDITOR_SCRIPT } from './base';

function css(v: NormalizedData): string { /* full design CSS; take v for edit-mode gating */ }

export function html(v: NormalizedData): string {
  const sectionMap: Record<string, () => string> = {
    experience: () => renderExperience(v),
    projects:   () => renderProjects(v),
    skills:     () => renderSkills(v),
    education:  () => renderEducation(v),
    certifications: () => renderCerts(v),
    achievements:   () => renderAchievements(v),
    // …only the sections this profession has…
    custom_sections: () => renderCustomSections(v),
  };
  const sections = v.section_order
    .filter((k) => !v.hidden_sections.has(k) && sectionMap[k])
    .map((k) => sectionMap[k]())
    .join('');
  return `<!DOCTYPE html><html>…<main>${sections}</main>${EDITOR_SCRIPT}</html>`;
}
```

Critical requirements while writing `html()`:

- **Section ordering/visibility:** exactly one top-level `<section id="{key}">` per orderable
  section — never merge two of our sections into one `<section>` (Z14). Iterate `v.section_order`
  and skip `v.hidden_sections`.
- **`EDITOR_SCRIPT`** must be included in the output (it powers inline editing in BOTH edit and
  published mode).
- **Every editable scalar** → `_editable('profile.full_name')`, `_editable('portfolio.headline')`,
  etc., bound to a REAL field (never a computed one like `duration`/`year_range` — use
  `_rangeEditable`/`_pairEditable`; Z9). Note the TWO headlines: `profile.headline` (raw title)
  vs `portfolio.headline` (AI headline) — Z10.
- **Every list field you display** gets its OWN `_listEditable('experience.0.key_points')` region
  rendering ALL items — never `.slice()` a bound list, never blend two fields into one region
  (Z1–Z6).
- **Images:** wrap the hero photo container with `_imgUpload('profile.profile_image', v.edit_mode)`;
  render `experience[i].images` and `projects[i].images` where the design puts a visual, each
  wrapped with `_imgUpload('projects.0.images', v.edit_mode)`; multiple images = crossfade
  slideshow (Z11–Z12). If the design has a second about/summary image, use
  `profile.summary_image` and register the template in `SUMMARY_IMAGE_TEMPLATES` (Step 4).
- **Stats** (years/projects/…): compute from data, but gate each with `statShown(v, key, value)`
  and read overrides from `v.template_overrides`; register the fields in `TEMPLATE_FIELDS`.
- **Custom sections:** render `v.custom_sections` honoring each item's `display_type`
  ('cards' | 'list' | 'timeline'); register the layouts you actually support in
  `CUSTOM_DISPLAY_TYPES`.
- **Edit-mode gating:** anything that breaks inline editing (custom `cursor:none`, pointer-lock
  overlays) must be emitted only when `!v.edit_mode` (Z13).

## Step 4 — Register in `index.ts`

- `import { html as {id}Html } from './{id}';` and add `{id}: {id}Html` to the `TEMPLATES` map.
- Add to `TEMPLATE_META`: `{ name, accent, profession }`. **`profession` drives both the upload
  wizard filter and the edit-page template picker** (edit page filters `TEMPLATE_META` by the
  record's category), so it must be one of the valid profession ids.
- If the template shows computed stats: add its fields to `TEMPLATE_FIELDS` (this renders the
  "Portfolio Fields" override panel on the edit page).
- If it uses any of these features, add the id to the matching set: `CUSTOM_DISPLAY_TYPES`
  (custom-section layouts offered), `SUMMARY_IMAGE_TEMPLATES` (second image),
  `CORE_EXPERTISE_TEMPLATES` + `CONTACT_TAGLINE_TEMPLATES` (+ `DEFAULT_CONTACT_TAGLINE`).

## Step 5 — Reproduce the FULL design (styling + animation)

Structure + styling + animation are ONE deliverable (Z8). Port **every** visual layer:
all `@keyframes` and the elements that use them; scroll-in reveals (and verify the
IntersectionObserver actually targets new elements — an element left at `opacity:0` whose reveal
never fires is invisible, not just static); hover states/transitions; decorative elements
(orbs, gradients, marquees, dividers); and responsive `@media` breakpoints for every section.
After building, diff against the source and confirm each animation/decorative element is present.

## Step 6 — Add the card to the upload wizard

In `src/routes/app/resumes/upload/+page.svelte`, add a `{ id, name, tag }` entry to
`TEMPLATES_BY_PROFESSION[<profession>]`. This grid is hardcoded (NOT driven by `index.ts`). The
wizard renders a LIVE preview via `renderPortfolio()` using the **per-profession mock data** that
already exists — so no new mock is needed when adding to an existing profession. (Only a brand-new
profession would need new mock data + a new profession entry.)

## Step 7 — Backend allowlists + dark flag

- `src/lambdas/upload/handler.py` → add `'{id}'` to `ALLOWED_TEMPLATES`.
- `src/lambdas/auth/patch_portfolio.py` → add `'{id}'` to `_VALID_TEMPLATE_IDS`.
- If the theme is dark: `src/lambdas/auth/generate_project_image.py` → add `'{id}'` to
  `_DARK_TEMPLATES` (so AI-generated project images use a dark background).

## Step 8 — Build + deploy

```bash
export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"      # WSL: put node on PATH
cd /home/prudvi/projects/AI-Portfolio-backend
bash build-portfolio-lambda.sh
cd terraform && terraform apply -auto-approve -lock=false
```

The edit preview reflects `{id}.ts` immediately, but published portfolios only change after this.

---

## Step 9 — Verification checklist

```
Registration / selection
□ Template appears in the upload wizard grid for the target profession, with live preview
□ Selecting it in the wizard passes {id} to the API without "Invalid templateId"
□ It appears in the edit-page template picker for that profession (TEMPLATE_META.profession)
□ Switching to it on the edit page re-renders the preview

Data model
□ Renders every section the profession's data model expects (Z15)
□ Renders NO foreign-profession sections
□ One <section id="{key}"> per orderable section; reorder + hide each works (Z14)

Editability (edit page)
□ Every text field is inline-editable, bound to a REAL data-path (Z9)
□ Both headlines bound correctly: profile.headline vs portfolio.headline (Z10)
□ Every displayed list field has its OWN _listEditable region rendering ALL items (Z1–Z6)
□ Skills/tools rendered as editable tag chips — NO proficiency bars/rings/meters/% (Z16)
□ Typing in the center form updates the preview; inline edits update the form (both directions)
□ Clicking a preview element focuses the matching form field; left-panel section click scrolls
□ Add/delete item in a section works from the preview and the form

Images
□ Profile photo uploadable via _imgUpload('profile.profile_image', …)
□ project/experience images render + uploadable; multiple images crossfade (Z11–Z12)
□ (if applicable) summary_image works and template is in SUMMARY_IMAGE_TEMPLATES

Portfolio Fields / custom sections
□ Stat overrides show in the Portfolio Fields tab (TEMPLATE_FIELDS) and drive the preview
□ statShown() hides zero/empty stats; visibility toggles honored
□ (if applicable) core_expertise / contact_tagline panels work
□ Custom sections render in all display_types the template registers in CUSTOM_DISPLAY_TYPES

Styling / deploy
□ Full design reproduced: all @keyframes, reveals, hovers, decorative elements, @media (Z8)
□ No element stuck at opacity:0 (reveal never firing) in edit OR published mode
□ Custom cursor / pointer-lock gated to !edit_mode (Z13)
□ Backend allowlists updated (ALLOWED_TEMPLATES + _VALID_TEMPLATE_IDS); _DARK_TEMPLATES if dark
□ bash build-portfolio-lambda.sh + terraform apply run; published portfolio matches preview
```

## Reference

- `references/code-patterns.md` — **Read before writing any code.**
  - Section A: accurate TypeScript template skeleton (`{id}.ts`)
  - Section B: editable-binding cookbook (scalar / list / image / range / pair / stats / custom)
  - Section C: `NormalizedData` field reference per profession
  - Section D: `index.ts` + wizard + backend allowlist snippets
  - Sections Z1–Z16: the pitfall checklist — every item is a real bug that shipped and had to
    be fixed afterward. Check every one before calling a template done.
