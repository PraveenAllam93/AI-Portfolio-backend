# Code Patterns Reference

> The template system is **unified TypeScript**: one `src/lib/templates/{id}.ts` per design,
> shared by the live editor preview AND the portfolio-generator Lambda. There is no Python
> renderer and no separate `.js` preview file. All editing plumbing (contenteditable,
> field-change/focus/blur messages, list editor, image upload, section scroll/reorder/hide) is
> already implemented in `base.ts`'s `EDITOR_JS`/`EDITOR_SCRIPT` and the edit page — your
> template only has to emit the right attributes via the `base.ts` helpers.

## Section A — TypeScript Template Skeleton (`src/lib/templates/{id}.ts`)

Model on the closest existing same-profession template (read it in full first). Skeleton:

```ts
/**
 * Template: {Name}
 * {one-line visual description: palette, fonts, signature animations}
 */
import type { NormalizedData } from './base';
import {
  _editable, _listEditable, _imgUpload, _rangeEditable, _pairEditable,
  statShown, EDITOR_SCRIPT,
} from './base';

const FONTS_URL = 'https://fonts.googleapis.com/css2?family=...&display=swap';

// `em` = edit mode. `le` only emits data-list-path in edit mode (see Z6).
function css(v: NormalizedData): string {
  const em = v.edit_mode;
  return `
    :root{ --bg:#0a0d14; --accent:#00d4ff; --text:#e8eaf0; /* … full palette … */ }
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'…',sans-serif;background:var(--bg);color:var(--text)}
    /* … PORT THE FULL DESIGN: @keyframes, .reveal states, hovers, decorative
         elements, and @media breakpoints. See Z8 — do not ship a skeleton. … */
    ${em ? '' : 'body{cursor:none}'}   /* gate cursor:none etc. to published only (Z13) */
  `;
}

export function html(v: NormalizedData): string {
  const em = v.edit_mode;
  const le = (path: string) => (em ? _listEditable(path) : '');

  // ONE renderer per orderable section this profession has (Section C).
  const sectionMap: Record<string, () => string> = {
    experience:      () => renderExperience(v, em, le),
    projects:        () => renderProjects(v, em, le),
    skills:          () => renderSkills(v, em, le),
    education:       () => renderEducation(v, em),
    certifications:  () => renderCerts(v, em),
    achievements:    () => renderAchievements(v, em),
    // designer-only: awards / design_philosophy / software_proficiency
    // marketing-only: campaigns   |   finance-only: financial_modeling / investment_portfolios
    custom_sections: () => renderCustomSections(v, em, le),
  };

  const sections = v.section_order
    .filter((k) => !v.hidden_sections.has(k) && sectionMap[k])
    .map((k) => sectionMap[k]())
    .join('');

  return `<!DOCTYPE html><html lang="en"><head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>${v.name}</title>
    <link href="${FONTS_URL}" rel="stylesheet">
    <style>${css(v)}</style>
  </head><body>
    ${renderHero(v, em)}
    <main>${sections}</main>
    ${renderContact(v, em)}
    <script>/* template's own runtime: nav, reveal observer, image slideshow (Z12) */</script>
    ${EDITOR_SCRIPT}
  </body></html>`;
}
```

Rules the skeleton encodes:
- Exactly one top-level `<section id="{key}">` per orderable section — never merge two (Z14).
- `EDITOR_SCRIPT` is always emitted (it powers editing in edit AND published mode).
- Values in `v` are already HTML-escaped by `normalize()` — **do not re-escape**. Only pass
  URLs you build yourself through nothing (they are pre-`_safeUrl`'d too).

---

## Section B — Editable-binding cookbook

All helpers come from `base.ts`. `em = v.edit_mode`.

**Scalar text** — bind to a REAL field (Z9). `data-path` forms: `profile.*`, `portfolio.*`,
`{section}.{visibleIndex}.{field}`, `template_overrides.*`.
```ts
<h1 ${em ? _editable('profile.full_name') : ''}>${v.name}</h1>
<p  ${em ? _editable('portfolio.headline') : ''}>${v.headline}</p>      // AI headline
<span ${em ? _editable('profile.headline') : ''}>${v.profile_headline}</span> // raw title (Z10)
<p  ${em ? _editable('portfolio.bio', true) : ''}>${v.bio}</p>          // multiline=true
```

**Experience/education date range** — never bind computed `duration`/`year_range` (Z9):
```ts
${_rangeEditable(`experience.${i}.start_date`, exp.start_date,
                 `experience.${i}.end_date`,   exp.end_date, em)}
${_pairEditable(`education.${i}.degree`, edu.degree,
                `education.${i}.field_of_study`, edu.field_of_study, em, ' in ')}
```

**List field** — its OWN region, render ALL items, gate with `?.length` (Z1–Z6):
```ts
${exp.key_points?.length
  ? `<ul ${le(`experience.${i}.key_points`)}>${exp.key_points.map(p => `<li>${p}</li>`).join('')}</ul>`
  : ''}
```
Independent list fields — never merge two into one region: `key_points`, `responsibilities`,
`measurable_outcomes`, `tech_stack`, `software_used`, `performance_metrics`, `channels_used`,
`channels_managed`, a skill group's `skills`, custom-section `tags`.

**Images** — wrap the image container; renders an upload zone in edit mode, nothing published:
```ts
<div ${_imgUpload('profile.profile_image', em)}>${v.profile_image
  ? `<img src="${v.profile_image}" alt="">` : ''}</div>
// section item images (max 3) — put where the DESIGN shows a visual (Z11):
<div ${_imgUpload(`projects.${i}.images`, em)}>…</div>
// second about/summary image → also add {id} to SUMMARY_IMAGE_TEMPLATES in index.ts:
<div ${_imgUpload('profile.summary_image', em)}>…</div>
```
Multiple images = looping crossfade slideshow, not a stack (Z12).

**Stats** (hero/about numbers) — override-aware + auto-hide zeros:
```ts
const years = v.template_overrides.years_experience ?? computeYears(v.experience);
${statShown(v, 'years_experience', years) ? `<div class="stat">${years}+ Years</div>` : ''}
// register the keys in TEMPLATE_FIELDS[id] so the Portfolio Fields panel exposes them.
```

**Custom sections** — honor each item's `display_type`; register supported layouts in
`CUSTOM_DISPLAY_TYPES[id]`:
```ts
v.custom_sections.map((cs, ci) => `
  <section id="custom_sections">
    <h2 ${em ? _editable(`custom_sections.${ci}.title`) : ''}>${cs.title}</h2>
    ${cs.display_type === 'timeline' ? renderTimeline(cs, ci, le)
      : cs.display_type === 'list'   ? renderList(cs, ci, le)
      :                                renderCards(cs, ci, le)}
  </section>`).join('')
```

---

## Section C — `NormalizedData` field reference (per profession)

Shapes come from `base.ts`. Universal sections render for every profession; the rest are gated
by `SECTION_CATEGORIES` (base.ts) and mirrored by `SECTION_CONFIG.categories` (edit page).

```
Profile (always): v.name, v.headline (AI), v.profile_headline (raw title), v.bio,
  v.uniqueValue, v.email, v.phone, v.location, v.profile_image, v.summary_image,
  v.contact_tagline, v.core_expertise[], v.{linkedin,github,portfolio,twitter}_url

Universal sections: experience[], skills (v.skill_groups[]), education[],
  certifications[], achievements[], custom_sections[]

experience[i]: role, company, location, start_date, end_date, is_current, description,
  key_points[], channels_managed[]*, financial_metrics_managed[]*, images[]   (*marketing/finance)
projects[i]:   title, description, responsibilities[], measurable_outcomes[], tech_stack[],
  github_repo, project_url, project_category, design_concept, software_used[], images[]
education[i]:  degree, field_of_study, institution, location, start_year, end_year, grade_or_score
certifications[i]: name, issuer, year, url        achievements[i]: title, description, year, url

Profession-specific sections:
  software_engineer:  projects
  designer:           projects, awards[], design_philosophy (string), software_proficiency[]
  marketing:          campaigns[] {campaign_name, campaign_type, channels_used[], budget, performance_metrics[]}
  finance:            financial_modeling[] {model_type, tools_used[], outcome},
                      investment_portfolios[] {portfolio_type, assets_under_management, performance_return}
  civil_engineer:     projects, software_proficiency[]
  mechanical_engineer:projects, software_proficiency[]
  accountant:         engagements[] {client_name, engagement_type, industry, start_date, end_date,
                        description, responsibilities[], deliverables[], standards_applied[],
                        tools_used[], engagement_value, measurable_outcomes[], images[]},
                      software_proficiency[], compliance_expertise[]
  hr:                 hr_programs[] {program_name, program_type, organization, start_date, end_date,
                        description, scope, activities[], tools_used[], measurable_outcomes[]},
                      software_proficiency[], compliance_expertise[]

custom_sections[i]: section_id, title, display_type('cards'|'list'|'timeline'),
  items[] { label, value, subtitle, tags[], url }

Metadata: v.category, v.section_order[], v.hidden_sections(Set), v.edit_mode,
  v.template_overrides{}, v.field_visibility{}
```

Render **every** section the profession has (even if the source design omits it — Z15) and
**none** from other professions.

---

## Section D — Registration snippets

**`src/lib/templates/index.ts`:**
```ts
import { html as {id}Html } from './{id}';
const TEMPLATES = { /* … */  {id}: {id}Html };
export const TEMPLATE_META = { /* … */
  {id}: { name: '{Name}', accent: '#RRGGBB', profession: '{profession}' } };
// if it shows computed stats:
export const TEMPLATE_FIELDS = { /* … */
  {id}: [{ key: 'years_experience', label: 'Years of Experience', hint: '…' }] };
// opt-in feature sets, only if used:
export const CUSTOM_DISPLAY_TYPES = { /* … */ {id}: ['cards','list','timeline'] };
export const SUMMARY_IMAGE_TEMPLATES  = new Set([/* … */ '{id}']);
export const CORE_EXPERTISE_TEMPLATES = new Set([/* … */ '{id}']);
export const CONTACT_TAGLINE_TEMPLATES= new Set([/* … */ '{id}']);
export const DEFAULT_CONTACT_TAGLINE  = { /* … */ {id}: '…' };
```

**Upload wizard** `src/routes/app/resumes/upload/+page.svelte` — hardcoded grid, `{id,name,tag}`:
```ts
const TEMPLATES_BY_PROFESSION = { {profession}: [ /* … */ { id: '{id}', name: '{Name}', tag: '{Tag}' } ] };
```

**Backend allowlists (Python):**
```python
# src/lambdas/upload/handler.py
ALLOWED_TEMPLATES = { …, '{id}' }
# src/lambdas/auth/patch_portfolio.py
_VALID_TEMPLATE_IDS = frozenset({ …, '{id}' })
# src/lambdas/auth/generate_project_image.py  (only if dark theme)
_DARK_TEMPLATES = { …, '{id}' }
```

**Deploy:** `export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"; bash build-portfolio-lambda.sh`
then `cd terraform && terraform apply -auto-approve -lock=false`.

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

### Z16. NEVER render skill/tool proficiency bars, rings, meters, or percentages

Our data model has **no proficiency/level/percentage field** for skills or tools. A skill group
is just `{ category, skills[] }` and `software_proficiency` is a flat `string[]` — all names,
no numbers. Many source designs render skills as animated progress bars ("SolidWorks 95%",
`.skill-bar-fill` with `data-width`), radial rings, dot meters, or star ratings. Those numbers
are **hardcoded design filler with no field behind them** (same class of dead control as Z15).

**Always convert them to tag/pill chips instead** — one `<span>` per skill inside the field's
`_listEditable` region:
```js
// ❌ WRONG — invented proficiency with no backing data
<div class="skill-bar"><span>Excel</span><span>95%</span><div class="bar-fill" style="width:95%"></div></div>
// ✅ RIGHT — editable tag chips, render ALL items
<div class="skill-tags" ${le(`skills.${gi}.skills`)}>${g.skills.map(s => `<span class="tag">${s}</span>`).join('')}</div>
```
This applies to `skills.*.skills`, `software_proficiency`, `core_expertise`, a campaign's
`channels_used`, a project's `tech_stack`/`software_used`, and any custom-section `tags` — none
of them carry a level. Drop the bar CSS, the `data-width`/`--pct` attributes, and the
width-animation JS entirely. If a design's skills section is *only* bars, the whole section
becomes a tag-chip grid (see `precision`/`torque` skills, `sterling` expertise cards).
