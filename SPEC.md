# AI Portfolio Platform — Feature Specification

## Overview

This document describes every user-facing feature of the AI Portfolio platform in complete detail, including all interactions, state transitions, edge cases, and UI behaviors. It is intended as the single source of truth for product, design, and engineering.

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Dashboard](#2-dashboard)
3. [Resume Upload Wizard](#3-resume-upload-wizard)
4. [Resume Processing Page](#4-resume-processing-page)
5. [Portfolio Edit Page](#5-portfolio-edit-page)
6. [Interview Setup](#6-interview-setup)
7. [Interview Session](#7-interview-session)
8. [Interview Report](#8-interview-report)
9. [Portfolio Analytics](#9-portfolio-analytics)
10. [Data Models Reference](#10-data-models-reference)
11. [Supported Categories](#11-supported-categories)
12. [Template System](#12-template-system)

---

## 1. Authentication

### 1.1 Sign Up

**Route:** `/signup`

**Form Fields:**
- Full Name (text input, required)
- Email (email input, required)
- Password (password input, required, min 8 chars)

**Flow:**
1. User submits the sign-up form.
2. System calls Cognito `signUp()` with email + password + name attribute.
3. If successful, user is redirected to the **Email Confirmation** page.
4. Cognito sends a 6-digit OTP to the email.

**Error Handling:**
- Email already in use → show inline error "An account with this email already exists."
- Weak password → show Cognito password policy error.

---

### 1.2 Email Confirmation

**Route:** `/confirm`

**Form Fields:**
- Confirmation Code (6-digit OTP, number input)

**Flow:**
1. User enters the OTP received by email.
2. System calls Cognito `confirmSignUp()`.
3. On success → redirect to `/login`.
4. "Resend Code" button available — calls Cognito `resendConfirmationCode()`.

**Error Handling:**
- Wrong code → "Invalid verification code. Please try again."
- Expired code → "Code expired. Please request a new one." + show resend prompt.

---

### 1.3 Login

**Route:** `/login`

**Form Fields:**
- Email
- Password

**Flow:**
1. System calls Cognito `signIn()`.
2. On success, Cognito tokens (`id_token`, `refresh_token`) are stored as HTTP-only cookies.
3. Redirect to `/app/dashboard`.

**Error Handling:**
- Wrong credentials → "Incorrect email or password."
- Unconfirmed account → "Please verify your email before logging in." + show "Resend Code" link.

---

### 1.4 Forgot / Reset Password

**Route:** `/forgot-password` → `/reset-password`

**Forgot Password:**
- User enters email.
- System calls Cognito `forgotPassword()`.
- Cognito sends a reset code to email.
- Redirect to Reset Password page.

**Reset Password:**
- Fields: Email, Reset Code (6-digit OTP), New Password, Confirm Password.
- System calls Cognito `confirmForgotPassword()`.
- On success → redirect to `/login`.

---

### 1.5 Logout

- Available in the dashboard top bar.
- Calls `/api/auth/logout` which clears auth cookies.
- Redirects to `/login`.

---

## 2. Dashboard

**Route:** `/app/dashboard`

The dashboard is the primary hub after login. It displays portfolio status, quick stats, and navigation to key features.

### 2.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Logo       Welcome, {Name}!               [Logout]             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Status   │  │ Template │  │   Views  │  │ Updated  │        │
│  │ LIVE     │  │ Modern   │  │   128    │  │ 2h ago   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                   │
│  ┌──────────────────────────────────────────┐                   │
│  │ Your Portfolio                  ● LIVE   │                   │
│  │ Version 3                                │                   │
│  │ [View Live] [Edit Portfolio] [Analytics] │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                   │
│  [Upload New Resume]        [Practice Interview]                 │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Stats Cards

| Card | Source | Description |
|------|--------|-------------|
| Status | `portfolioStatus` | LIVE (green badge) or IN_PROGRESS or DRAFT |
| Template | `templateId` | Currently active template name |
| Total Views | Analytics API | All-time portfolio views |
| Last Updated | `updatedAt` | Relative time (e.g., "2 hours ago") |

### 2.3 Portfolio Card

- Displays current live portfolio with version number and live badge.
- **[View Live]** — opens portfolio public URL in a new tab.
- **[Edit Portfolio]** — navigates to `/app/portfolio/{userId}/edit`.
- **[Analytics]** — navigates to the analytics section/page.

### 2.4 Action Buttons

- **[Upload New Resume]** — navigates to `/app/resumes/upload`.
- **[Practice Interview]** — navigates to `/app/interview/setup`.

### 2.5 Loading States

- Stats cards show skeleton loaders while data is being fetched.
- Portfolio card shows a placeholder if no portfolio exists yet (with a prompt to upload a resume).

---

## 3. Resume Upload Wizard

**Route:** `/app/resumes/upload`

A 3-step wizard that collects the resume file, profession category, and preferred template before starting the AI processing pipeline.

---

### Step 1: File Selection

**Purpose:** User selects a resume file.

**UI Elements:**
- Large drag-and-drop zone with dashed border.
  - Text: "Drag and drop your resume here" + "or click to browse"
  - Accepted formats label: "PDF or DOCX, max 10MB"
- Clicking the zone opens the system file picker (filtered to `.pdf, .docx`).
- Dragging a file over the zone highlights the border.
- After file selection:
  - File name displayed with a file icon.
  - File size displayed (e.g., "245 KB").
  - Format badge shown (PDF or DOCX).
  - Remove/change file button (×).
- **[Next →]** button activates only after a valid file is selected.

**Validation (client-side before upload):**
- File type must be `application/pdf` or `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
- File size must be ≤ 10MB.
- If validation fails: inline error message below the drop zone.

---

### Step 2: Role Selection

**Purpose:** User selects their profession category.

**UI Elements:**
- Section heading: "What is your profession?"
- Four large selectable cards:
  - **Software Engineer** — icon + label
  - **Designer** — icon + label
  - **Marketing** — icon + label
  - **Finance** — icon + label
- Selecting a card highlights it with an active state (border + background change).
- Only one card can be selected at a time.
- **[← Back]** returns to Step 1.
- **[Next →]** activates after a category is selected.

---

### Step 3: Template Selection

**Purpose:** User chooses a visual template for their portfolio.

**UI Elements:**
- Section heading: "Choose your template"
- Grid of template cards (11 total), each showing:
  - Template thumbnail/preview image.
  - Template name.
  - Style tag badges (e.g., "Clean", "Dark", "Creative", "Corporate").
- Hovering a card shows a subtle highlight.
- Clicking a card selects it (active border/checkmark).
- **[← Back]** returns to Step 2.
- **[Upload & Generate]** button (primary CTA):
  - Triggers the upload process.
  - Shows spinner + "Uploading..." while the presigned URL is being fetched and the file is being uploaded to S3.
  - Progress bar shows upload progress (based on XHR `onprogress`).
  - On success → navigate to `/app/resumes/{uploadId}/processing`.
  - On error → show error message with retry option.

**Templates Available:**

| ID | Name | Tags |
|----|------|------|
| `minimal` | Minimal | Clean, Professional |
| `modern` | Modern | Contemporary, Cards |
| `bold` | Bold | High Contrast, Statement |
| `creative` | Creative | Artistic, Unique |
| `aurora` | Aurora | Gradient, Vibrant |
| `executive` | Executive | Corporate, Formal |
| `luxury` | Luxury | Premium, Elegant |
| `nebula` | Nebula | Dark, Cosmic |
| `galaxy` | Galaxy | Purple, Dark |
| `codex` | Codex | Tech, Light |
| `neon` | Neon | Cyber, Green |

---

## 4. Resume Processing Page

**Route:** `/app/resumes/[uploadId]/processing`

This page displays the real-time status of the AI processing pipeline as the system validates, parses, and generates the portfolio.

### 4.1 Layout

```
┌──────────────────────────────────────────────┐
│  Processing Your Resume                       │
│                                               │
│  [═══════════════════░░░░░░░░] 62%            │
│                                               │
│  ✓ File uploaded                              │
│  ✓ Security validation passed                 │
│  ⟳ AI is analyzing your resume...            │
│    Portfolio generation pending               │
│                                               │
│  Estimated time: ~30 seconds remaining        │
└──────────────────────────────────────────────┘
```

### 4.2 Progress Steps

Each status maps to a visible stage:

| Status | Display |
|--------|---------|
| `PENDING_UPLOAD` | "Preparing upload..." |
| `VALIDATING` | "Validating file security..." |
| `VALIDATED` | "Security validation passed ✓" |
| `EXTRACTING_TEXT` | "Extracting resume content..." |
| `QUEUED_FOR_AI` | "Queued for AI processing..." |
| `AI_PROCESSING` | "AI is analyzing your resume..." |
| `AI_COMPLETE` | "AI analysis complete ✓" |
| `GENERATING` | "Generating your portfolio..." |
| `COMPLETE` | "Portfolio ready! ✓" |

### 4.3 Polling Behavior

- Polls `GET /api/resume/status/{uploadId}` every **2 seconds**.
- Progress bar animates based on current stage (each stage = incremental %).
- On `COMPLETE` → auto-navigate to `/app/portfolio/{userId}/edit`.
- On `REJECTED` → show error: "Your file did not pass our security checks. Please try again with a valid PDF or DOCX resume."
- On `AI_FAILED` → show error with retry button.
- On `FAILED` → show error with retry button.
- Stale detection (backend-side):
  - AI_PROCESSING > 360s → automatically marked `AI_FAILED`
  - GENERATING > 300s → automatically marked `FAILED`

### 4.4 Retry Behavior

- "Try Again" button re-navigates to `/app/resumes/upload`.
- The original uploadId is abandoned; a new upload is started.

---

## 5. Portfolio Edit Page

**Route:** `/app/portfolio/[userId]/edit`

This is the most complex and feature-rich page. It allows users to edit every aspect of their portfolio with real-time preview synchronization and AI assistance.

### 5.1 Overall Layout

The page is divided into three panels:

```
┌──────────────────┬────────────────────────────┬────────────────────┐
│   LEFT PANEL     │      CENTER PANEL           │   RIGHT PANEL      │
│   (~280px)       │      (flexible)             │   (~460px)         │
│                  │                             │                    │
│  Section List    │  Edit Form                  │  Live Preview      │
│  + Ordering      │  (fields, AI enhance)       │  (portfolio HTML)  │
│  + Visibility    │                             │  (iframe/rendered) │
│                  │                             │                    │
└──────────────────┴────────────────────────────┴────────────────────┘
```

Top bar spans all panels:
- Left: logo / back to dashboard
- Center: status indicator (Saving... | Saved | Error)
- Right: Template selector dropdown + **[Publish Portfolio]** button

---

### 5.2 Left Panel — Section Manager

#### 5.2.1 Section List

- Displays all sections applicable to the user's category as a vertical list.
- Each section is a card/row with:
  - **Drag handle** (⠿ icon on the left) — used for reordering.
  - **Section name** (e.g., "Experience", "Projects").
  - **Visibility toggle** (eye icon on the right) — toggles section visibility.
  - **Item count badge** (e.g., "3 items") for array sections.

**Available Sections by Category:**

| Section | Software | Designer | Marketing | Finance |
|---------|----------|----------|-----------|---------|
| Experience | ✓ | ✓ | ✓ | ✓ |
| Education | ✓ | ✓ | ✓ | ✓ |
| Certifications | ✓ | ✓ | ✓ | ✓ |
| Achievements | ✓ | ✓ | ✓ | ✓ |
| Skills | ✓ | ✓ | ✓ | ✓ |
| Projects | ✓ | ✓ | — | — |
| Awards | — | ✓ | — | — |
| Design Philosophy | — | ✓ | — | — |
| Software Proficiency | — | ✓ | — | — |
| Campaigns | — | — | ✓ | — |
| Financial Modeling | — | — | — | ✓ |
| Investment Portfolios | — | — | — | ✓ |

#### 5.2.2 Reordering Sections

- Sections can be dragged and dropped to any position using the drag handle.
- Dragging a row shows a placeholder gap indicating where it will be dropped.
- On drop: `sectionOrder` is updated immediately in local state, a PATCH request is sent to `/portfolio/{userId}/content` with `{ section: "config", data: { sectionOrder, hiddenSections } }`, and the portfolio draft is asynchronously regenerated.
- **The preview (right panel) updates instantly** to reflect the new section order — sections in the preview reflow to match.

#### 5.2.3 Visibility Toggle

- Clicking the eye icon on any section row toggles it between visible and hidden.
- Hidden sections appear with a strikethrough name and dimmed styling.
- `hiddenSections` array is updated in local state immediately.
- A PATCH request is sent to save `{ section: "config", data: { sectionOrder, hiddenSections } }`.
- **The preview (right panel) immediately hides or shows that section.**

#### 5.2.4 Section Click → Scroll in Preview

- Clicking on a section name in the left panel causes the **right panel preview to scroll** to that section.
- The section in the preview is briefly highlighted with a soft flash animation to draw attention.
- This works bidirectionally: clicking an element in the preview also highlights the corresponding section in the left panel.

#### 5.2.5 AI Suggestions Panel

- A collapsible "AI Suggestions" section at the bottom of the left panel.
- **[Analyze & Suggest]** button — sends the full portfolio data to `ai_enhance_portfolio` with `action: "analyze_and_suggest"`.
- While loading: spinner inside the button, "Analyzing your portfolio..."
- After loading: a list of 3–8 suggestion cards, each showing:
  - Priority indicator (🔥 High, ⚡ Medium, 💡 Low)
  - Label (e.g., "Strengthen your bio")
  - Sublabel (e.g., "Add quantified impact to make it stand out")
  - **[Apply]** button — clicking it:
    1. Scrolls the center panel to the relevant field.
    2. Pre-fills the AI enhancement instruction field with the suggestion's `instruction`.
    3. Automatically triggers the AI enhancement for that field/item/section.
- Clicking a suggestion card also scrolls the right panel preview to the section it relates to.

---

### 5.3 Center Panel — Edit Form

The center panel shows the editable form for the currently focused section or scrolls through all sections in order.

#### 5.3.1 Profile / Header Fields

At the top of the edit form are the three key portfolio-level fields:

**Headline** (`portfolioContent.headline`, max 200 chars)
- Text input with character counter.
- Auto-saves on blur (debounced 500ms).
- **[AI ✨]** button next to the field — opens an AI instruction popover:
  - "What would you like to change? (e.g., 'Make it more impactful')"
  - Text input for instruction (max 300 chars).
  - **[Get Suggestion]** — calls ai-enhance API, shows suggested value below.
  - **[Apply]** — replaces field value with suggestion, triggers auto-save.
  - **[Cancel]** — dismisses popover.
- **Bidirectional sync:** Any change in this field instantly updates the preview (right panel) headline.

**Bio / Summary** (`portfolioContent.bio`, max 1000 chars)
- Multiline textarea with character counter.
- Same AI enhancement flow as Headline.
- Auto-saves on blur.
- Updates preview bio/summary section in real time.

**Unique Value Proposition** (`portfolioContent.uniqueValue`, max 500 chars)
- Multiline textarea with character counter.
- Same AI enhancement flow.
- Auto-saves on blur.
- Updates corresponding section in preview.

#### 5.3.2 Profile Info Section

Sub-section within the edit form for raw profile data (`parsedData.profile`):

| Field | Input Type | Notes |
|-------|-----------|-------|
| Full Name | Text input | Updates preview name/heading |
| Email | Email input | Validated format |
| Phone | Text input | |
| Location | Text input | City, Country |
| LinkedIn URL | URL input | Validated https:// |
| GitHub URL | URL input | Validated https:// |
| Portfolio URL | URL input | Validated https:// |
| Twitter URL | URL input | Validated https:// |
| Profile Image | Image URL input + upload button | Accepts JPEG, PNG, WebP, GIF |

**Profile Image Upload:**
- Clicking the upload button calls `/portfolio/{userId}/image-upload-url` to get a presigned S3 PUT URL.
- File is uploaded client-side to S3 directly.
- After upload, the returned `imageUrl` is saved to `profile.profile_image`.
- Preview immediately updates to show the new profile image.

Auto-saves the entire `profile` object on field blur.

#### 5.3.3 Experience Section

Each experience item is displayed as a collapsible card.

**Per-Item Fields:**
| Field | Input Type | Notes |
|-------|-----------|-------|
| Role / Title | Text input | |
| Company | Text input | |
| Location | Text input | |
| Start Date | Month/Year picker or text | e.g., "Jan 2022" |
| End Date | Month/Year picker or text | Disabled if `is_current = true` |
| Currently Working Here | Checkbox | Sets `is_current`, disables End Date |
| Description | Multiline textarea | AI enhance available |
| Key Points | List editor (see below) | AI enhance available for whole list |

**Key Points List Editor:**
- Displayed as a vertical list of text inputs.
- Each item has a remove button (×) on the right.
- **[+ Add Key Point]** button at the bottom of the list.
- Items can be reordered via drag handle.
- AI enhance for key_points returns a new array, which replaces the list.

**AI Enhancement on Experience Items:**
- **[AI ✨]** button appears next to Description and Key Points fields.
- Sends: `{ section: "experience", itemIndex: N, enhanceField: "description"|"key_points", instruction: "..." }` with the **full item context** (role, company, all existing fields).
- Shows suggested value in a diff-style box (old greyed, new highlighted).
- **[Apply]** applies the suggestion and triggers save.

**Per-Item Actions:**
- **[+ Add Experience]** button at the bottom of the section.
- Each card has a **[Delete]** button (with confirmation dialog).
- Deleting an item removes it from local state and saves the full array.

**Editing → Preview Sync:**
- Any field change in an experience item immediately updates that item's display in the right panel preview.
- The updated item is briefly highlighted in the preview to indicate the change.

#### 5.3.4 Projects Section (Software Engineer + Designer)

Same structure as Experience with these differences:

**Software Engineer Project Fields:**
| Field | Notes |
|-------|-------|
| Title | |
| Description | AI enhance available |
| Tech Stack | Tag input — add/remove individual tech tags |
| GitHub Repo URL | Validated URL |
| Live Project URL | Validated URL |
| Responsibilities | List editor (like Key Points) |
| Measurable Outcomes | List editor |

**Designer Project Fields (additional):**
| Field | Notes |
|-------|-------|
| Design Concept | Textarea |
| Software Used | Tag/list input |
| Project Category | Text input |

#### 5.3.5 Skills Section

**Display:** Skill groups — each group has a category name and a list of individual skills.

**Edit Form:**
- Each group displayed as a card with:
  - Category name (text input, editable inline).
  - Skills as individual tags/chips with × to remove each.
  - **[+ Add Skill]** input at the end of the tag list.
- **[+ Add Skill Group]** button to add a new category.
- Each group has a delete button.

**AI Enhancement for Skills:**
- A single **[AI ✨ Enhance All Skills]** button at the section header.
- Instruction input: "e.g., 'Add more relevant backend skills'"
- Sends: `{ section: "skills", instruction: "..." }` with category context (experience + projects for software engineers).
- Returns a new array of skill groups.
- Shows suggested skills in a preview card — user can **[Apply All]** or dismiss.

**Preview Sync:** Tag additions/removals and group name changes immediately reflect in the preview's skills section.

#### 5.3.6 Education Section

Per-item fields: Degree, Field of Study, Institution, Location, Start Year, End Year, Grade/Score.
No AI enhancement for education (factual data).

#### 5.3.7 Certifications Section

Per-item fields: Name, Issuer, Year, Certification URL.
No AI enhancement.

#### 5.3.8 Achievements Section

Per-item fields: Title, Year, Description (AI enhance available), Achievement URL.

#### 5.3.9 Awards Section (Designer)

Per-item fields: Title, Awarding Body, Year, Award URL.

#### 5.3.10 Design Philosophy (Designer)

- Single multiline textarea (max 2000 chars).
- AI enhancement available.
- Auto-saves on blur.

#### 5.3.11 Software Proficiency (Designer)

- List editor for individual software tool names.
- Max 50 items, each max 200 chars.
- **[+ Add Tool]** button.
- No AI enhancement.

#### 5.3.12 Campaigns Section (Marketing)

Per-item fields:
| Field | Notes |
|-------|-------|
| Campaign Name | |
| Campaign Type | |
| Channels Used | Tag input (e.g., Email, LinkedIn, Instagram) |
| Budget | Text input |
| Performance Metrics | List editor — AI enhance available |

#### 5.3.13 Financial Modeling Section (Finance)

Per-item fields: Model Type, Tools Used (tags), Outcome (AI enhance available).

#### 5.3.14 Investment Portfolios Section (Finance)

Per-item fields: Portfolio Type, Assets Under Management, Performance Return.

---

### 5.4 Right Panel — Live Preview

The right panel shows a live rendered preview of the portfolio HTML.

#### 5.4.1 Rendering Mechanism

- The preview is rendered as an iframe (or iframe-equivalent) displaying the portfolio HTML.
- The portfolio draft HTML is fetched from `{userId}/draft/index.html` on the S3/CloudFront origin.
- After every save (auto-save or explicit), the backend asynchronously re-renders the draft.
- The preview auto-refreshes when the draft is updated (polls `draft-ready` endpoint or uses a timestamp check).

#### 5.4.2 Inline Editing in Preview

- Text elements in the preview that are editable have a subtle hover outline (dashed blue border appears on hover).
- **Clicking** on an editable element in the preview:
  1. Activates an inline text editor (contenteditable or floating input overlay) directly on the element.
  2. **Simultaneously scrolls the center panel** to the corresponding field in the edit form and focuses that field.
  3. The left panel highlights the section that element belongs to.
- **Typing** in the inline preview editor:
  1. Updates the text in real time (optimistic update in preview).
  2. Updates the corresponding field value in the center panel edit form (bidirectional sync).
- **Leaving the inline editor** (blur/click away):
  1. Triggers an auto-save of the changed field.
  2. Preview reflects the saved value.

**Editable elements in preview:**
- Portfolio headline
- Bio/summary text
- Unique value proposition text
- Experience item descriptions and key points
- Project descriptions
- Skills (individual tags — clicking a skill chip allows editing that skill)
- Section headings (mapped to section names)

**Non-editable in preview (edit via form only):**
- URLs (GitHub, LinkedIn, etc.)
- Structured date fields
- Image uploads

#### 5.4.3 Section Scrolling from Left Panel

- Clicking a section name in the left panel scrolls the preview to that section.
- The section in the preview briefly flashes a highlight animation (light blue overlay fades out over 1 second).

#### 5.4.4 Section Reorder Reflection

- When sections are reordered in the left panel, the preview immediately reorders the visible sections to match — no page reload required.
- This is achieved by updating the DOM order or re-rendering the preview iframe with updated `sectionOrder`.

#### 5.4.5 Section Visibility Reflection

- Toggling a section's visibility in the left panel immediately shows or hides that section in the preview.
- Hidden sections are either removed from the DOM or given `display: none` in the preview.

#### 5.4.6 Template Switching

- The top bar has a **Template** dropdown with all 11 templates listed.
- Selecting a new template:
  1. Updates `templateId` locally.
  2. Sends a PATCH request: `{ section: "config", data: { templateId } }`.
  3. Triggers an async portfolio re-render with the new template.
  4. The preview refreshes to show the new template once rendering is complete.
  5. While regenerating, the preview shows a loading overlay.

---

### 5.5 Save Behavior

- **Auto-save** fires 500ms after the user stops typing in any field (debounce).
- Save indicator in the top bar:
  - **"Saving..."** — gray spinner while PATCH request is in flight.
  - **"Saved ✓"** — green check after successful save.
  - **"Error saving"** — red text with retry option on failure.
- Each save triggers an async draft portfolio regeneration in the background.
- Multiple rapid saves are coalesced — only the latest value is sent.

---

### 5.6 Publish Flow

**[Publish Portfolio]** button in the top-right.

1. User clicks **[Publish]**.
2. A confirmation dialog appears:
   - "Your portfolio will be published live and visible to anyone with the link."
   - **[Confirm Publish]** / **[Cancel]**
3. On confirm:
   - API call: `POST /portfolio/{userId}/publish`.
   - Top bar shows "Publishing..." spinner.
   - Backend asynchronously renders the portfolio to `{userId}/v{version}/index.html`.
   - Polling `/api/portfolio/draft-ready` or the status endpoint until publish is confirmed.
4. On success:
   - "Published! ✓" green notification.
   - Version number increments (e.g., "v2 → v3").
   - **[View Live]** button appears/updates with the new live URL.
5. On failure:
   - "Publish failed. Please try again." error toast.

---

## 6. Interview Setup

**Route:** `/app/interview/setup`

Configures an AI-powered mock interview tailored to the user's resume and preferences.

### 6.1 Configuration Options

**Difficulty** (radio buttons, required):
- Easy — foundational concepts, broad questions
- Medium — standard interview depth
- Hard — deep technical, nuanced scenarios
- Mix — combination of all difficulties

**Number of Questions** (button grid, required):
- 7 questions — Quick practice (~10 min)
- 15 questions — Standard session (~25 min)
- 25 questions — Full interview (~45 min)

**Mode** (radio buttons, required):
- **Non-Follow-Up** — All questions are pre-generated upfront based on the topic plan. Predictable flow, good for systematic preparation.
- **Follow-Up (Adaptive)** — Questions adapt based on your answers. Follow-up questions are generated dynamically based on your responses. More realistic interview feel.

**Interview Source** (radio buttons, required):
- **From My Resume** — Questions are generated from the user's uploaded and parsed resume data.
- **Custom Role** — Allows specifying a target job role description.

**Role Description** (textarea, shown only if source = "Custom Role"):
- Placeholder: "Describe the role you're targeting (e.g., 'Senior Full Stack Engineer at a fintech startup, 5+ years required, React, Node.js, AWS')"
- Max 500 characters.
- Character counter shown.

### 6.2 Start Button

- **[Start Interview]** — primary CTA, disabled until all required options are selected.
- On click: calls `POST /api/interview/start` with configuration.
- Shows spinner while session is being created.
- On success: navigates to `/app/interview/{sessionId}`.
- On error: shows inline error message.

---

## 7. Interview Session

**Route:** `/app/interview/[sessionId]`

The interactive interview session page.

### 7.1 Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  [←] Interview    Question 4 of 15    [React]    [Exit Interview]│
│  ━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░░░░░░░░  27%                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Explain the difference between useMemo and useCallback in React, │
│  and describe a scenario where you would use each.                │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Type your answer here...                                   │  │
│  │                                                             │  │
│  │                                                             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                   Characters: 0 / 2000           │
│                                                                   │
│                                        [Submit Answer]           │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 Top Bar

- **Back arrow** + "Interview" label.
- **Question counter:** "Question X of Y" (e.g., "Question 4 of 15").
- **Topic badge:** Current topic name (e.g., "[React]", "[System Design]").
- **Progress bar:** Fills proportionally (questionsAsked / totalQuestions × 100%).
- **[Exit Interview]** button — exits early and generates a partial report.

### 7.3 Question Display

- Large, clear question text.
- No hints, no AI assistance during the session.
- Topic context shown via the topic badge in the top bar.

### 7.4 Answer Input

- Large multiline textarea with placeholder "Type your answer here..."
- Character counter: "X / 2000".
- Auto-resizes vertically as user types.
- Empty submission allowed — clicking Submit with an empty textarea shows a confirmation:
  - "You haven't entered an answer. Submit without an answer?"
  - **[Submit Anyway]** / **[Cancel]**

### 7.5 Submit Flow

1. User clicks **[Submit Answer]** (or confirms empty submission).
2. Button becomes disabled, spinner shown.
3. `POST /api/interview/answer` called with `{sessionId, answer}`.
4. While waiting: "Evaluating your answer..." text shown below the textarea.
5. Response received:
   - Feedback panel slides up from the bottom (or replaces the textarea area).
   - Next question is ready but not yet shown.

### 7.6 Feedback Panel

Shown immediately after answer submission:

```
┌────────────────────────────────────────────────────────────────┐
│  Score: 7 / 10   ████████░░                                    │
│                                                                  │
│  ✅ Strengths                                                   │
│    • Clear explanation of the difference                        │
│    • Good use of memoization concept                            │
│                                                                  │
│  ⚠️ Areas to Improve                                           │
│    • No concrete code example provided                          │
│    • Didn't mention dependency arrays                           │
│                                                                  │
│  💡 Ideal Answer                                                │
│    [Collapsed by default, click to expand]                      │
│    useMemo memoizes the result of a computation...              │
│                                                                  │
│                                         [Next Question →]       │
└────────────────────────────────────────────────────────────────┘
```

**Feedback Components:**
- **Score bar:** Numeric score (1–10) with a visual progress bar colored:
  - Green (8–10)
  - Yellow (5–7)
  - Red (1–4)
- **Strengths:** Bulleted list from evaluation.
- **Areas to Improve:** Bulleted list from evaluation.
- **Ideal Answer:** Collapsed by default. Expandable with a toggle. Shows what a strong answer would look like.

### 7.7 Next Question Flow

1. User clicks **[Next Question →]**.
2. Feedback panel collapses.
3. New question text replaces old question.
4. Textarea clears and re-enables.
5. Question counter and progress bar update.
6. Topic badge updates if the topic changes.

### 7.8 Session Completion

When `isComplete: true` is received from the answer API:
1. The feedback panel for the last question is shown as usual.
2. After user views feedback, the **[Next Question →]** button is replaced by **[View Your Report →]**.
3. Clicking it navigates to `/app/interview/{sessionId}/report`.

### 7.9 Exit Interview

Clicking **[Exit Interview]** in the top bar:
1. Confirmation dialog: "Are you sure you want to exit? A partial report will be generated from your completed answers."
2. **[Yes, Exit]** / **[Continue Interview]**
3. On confirm: `POST /api/interview/exit` called.
4. On success: navigate to `/app/interview/{sessionId}/report` with partial results.

### 7.10 Session Persistence

- The session is stored server-side in DynamoDB.
- If the user refreshes the page, the current question is reloaded from the session.
- Answer history is preserved server-side.

---

## 8. Interview Report

**Route:** `/app/interview/[sessionId]/report`

Displays the complete analysis of the interview session.

### 8.1 Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Interview Report                                                 │
│  [Difficulty: Medium]  [15 Questions]  [Follow-Up Mode]          │
│                                                                   │
│  Overall Score                                                    │
│  ┌──────────────────────────────────┐                           │
│  │      7.4 / 10       ████████░░   │                           │
│  │    15 questions answered         │                           │
│  └──────────────────────────────────┘                           │
│                                                                   │
│  Performance by Topic                                            │
│  ┌──────────────────────────────────┐                           │
│  │ React          8.2  ████████░░   │                           │
│  │ System Design  6.1  ██████░░░░   │                           │
│  │ Algorithms     7.8  ████████░░   │                           │
│  └──────────────────────────────────┘                           │
│                                                                   │
│  ✅ Key Strengths                    ⚠️ Areas to Improve        │
│  • Clear explanations               • Lacks depth in DS          │
│  • Good examples                    • No STAR format used        │
│                                                                   │
│  💡 Recommendations                                              │
│  • Study distributed systems        • Practice behavioral Qs    │
│                                                                   │
│  [Download Report PDF]   [Practice Again]                        │
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 Report Sections

**Session Info Bar:** Difficulty badge, question count, mode (Follow-Up/Non-Follow-Up).

**Overall Score Card:**
- Large number: `X.X / 10`
- Horizontal progress bar colored by score range.
- Sub-label: "X questions answered."

**Performance by Topic:**
- Each topic in the session listed with:
  - Topic name.
  - Average score for that topic (average of all answers in that topic).
  - Horizontal mini bar colored by score.

**Key Strengths:**
- Aggregated unique strengths from all answer feedback evaluations.
- Bullet list, deduplicated.

**Areas to Improve:**
- Aggregated weaknesses from all answer feedback evaluations.
- Bullet list, deduplicated.

**Recommendations:**
- Personalized suggestions generated by AI based on the overall performance pattern.
- Actionable bullet points.

### 8.3 Actions

- **[Download Report PDF]** — Generates a PDF version of the report (if implemented).
- **[Practice Again]** — Navigates to `/app/interview/setup` to start a new session.

---

## 9. Portfolio Analytics

**Route:** `/app/dashboard` (analytics section) or `/app/portfolio/[userId]/analytics`

### 9.1 Stats Summary Cards

| Metric | Description |
|--------|-------------|
| Total Views | All-time portfolio views |
| Last 7 Days | Views in the last 7 days |
| Last 30 Days | Views in the last 30 days |
| Unique Visitors | Distinct visitors (hashed) |
| Avg Load Time | Average TTFB in ms |
| Cache Hit Rate | % of requests from CloudFront cache |

### 9.2 Timeline Chart

- Line chart: views per day over the selected time range.
- Date range selector (7 days / 30 days / all time).

### 9.3 Breakdown Charts

- **By Country:** Bar chart or map — top countries sending traffic.
- **By Source:** Pie/donut — direct, LinkedIn, GitHub, Twitter, etc.
- **By Device:** Donut — desktop vs mobile vs tablet.
- **By Hour:** Bar chart — peak hour distribution.
- **By Day of Week:** Bar chart — which days get most traffic.
- **By Version:** Table — views per published version.

### 9.4 Best Time to Share

- Insight card showing the peak engagement window based on historical data.
- E.g., "Best time to share: Wednesday 2–4 PM"

---

## 10. Data Models Reference

### 10.1 ParsedData (Full Schema)

```typescript
interface ParsedData {
  profile: {
    full_name: string
    headline: string
    email: string
    phone: string
    location: string
    summary: string
    social_links: {
      linkedin?: string
      github?: string
      gitlab?: string
      portfolio?: string
      twitter?: string
    }
    profile_image?: string
  }

  skills: Array<{
    category: string
    skills: string[]
  }>

  experience: Array<{
    company: string
    role: string
    location: string
    start_date: string
    end_date: string
    is_current: boolean
    description: string
    key_points: string[]
    channels_managed?: string         // Marketing
    financial_metrics_managed?: string // Finance
    images?: string[]
  }>

  projects: Array<{
    title: string
    description: string
    tech_stack: string[]              // Software
    github_repo?: string
    project_url?: string
    responsibilities: string[]
    measurable_outcomes: string[]
    design_concept?: string           // Designer
    software_used?: string[]          // Designer
    project_category?: string         // Designer
    images?: string[]
  }>

  education: Array<{
    degree: string
    field_of_study: string
    institution: string
    location: string
    start_year: string
    end_year: string
    grade_or_score?: string
  }>

  certifications: Array<{
    name: string
    issuer: string
    year: string
    certification_url?: string
  }>

  achievements: Array<{
    title: string
    description: string
    year: string
    achievement_url?: string
  }>

  awards: Array<{                     // Designer
    title: string
    awarding_body: string
    year: string
    award_url?: string
  }>

  campaigns: Array<{                  // Marketing
    campaign_name: string
    campaign_type: string
    channels_used: string[]
    budget?: string
    performance_metrics: string[]
  }>

  financial_modeling: Array<{         // Finance
    model_type: string
    tools_used: string[]
    outcome: string
  }>

  investment_portfolios: Array<{      // Finance
    portfolio_type: string
    assets_under_management: string
    performance_return: string
  }>

  design_philosophy?: string          // Designer
  software_proficiency?: string[]     // Designer
}
```

### 10.2 PortfolioContent

```typescript
interface PortfolioContent {
  headline: string       // max 200 chars
  bio: string            // max 1000 chars
  uniqueValue: string    // max 500 chars
}
```

### 10.3 PortfolioConfig

```typescript
interface PortfolioConfig {
  sectionOrder: string[]    // ordered list of section names
  hiddenSections: string[]  // sections not rendered
  templateId: string        // active template
}
```

---

## 11. Supported Categories

| Category Key | Display Name | Unique Sections |
|-------------|-------------|----------------|
| `software_engineer` | Software Engineer | Projects (tech stack, GitHub) |
| `designer` | Designer | Design Philosophy, Software Proficiency, Awards, Design Projects |
| `marketing` | Marketing | Campaigns |
| `finance` | Finance | Financial Modeling, Investment Portfolios |

---

## 12. Template System

### Template IDs and Styles

| ID | Style | Best For |
|----|-------|---------|
| `minimal` | Clean whitespace, subtle typography | Any profession |
| `modern` | Cards, contemporary layout | Tech, Design |
| `bold` | Strong contrast, loud headers | Design, Marketing |
| `creative` | Unconventional layout | Designer |
| `aurora` | Vibrant gradients | Tech, Creative |
| `executive` | Formal, structured columns | Finance, Marketing |
| `luxury` | Refined serif typography | Finance, Executive |
| `nebula` | Dark, cosmic gradients | Tech, Gaming |
| `galaxy` | Deep purple dark theme | Tech, Gaming |
| `codex` | Light, code-aesthetic | Software Engineer |
| `neon` | Cyber green on dark | Software Engineer |

### Template Security

- All portfolio HTML is **static** — no JavaScript.
- CSP header: `Content-Security-Policy: script-src 'none'`
- All user-supplied strings are HTML-escaped before insertion.
- All URLs validated: must be `http://` or `https://` — `javascript:` and `data:` schemes blocked.
- Google Fonts (Inter family) loaded via standard stylesheet link.

### Template Selection in Upload Wizard

- All 11 templates shown in Step 3 of the upload wizard.
- Can be changed at any time from the edit page template dropdown.

### Template Switching Behavior (Edit Page)

1. User selects a new template from the dropdown.
2. Local `templateId` is updated immediately.
3. A PATCH request is sent with the new templateId.
4. Portfolio draft is asynchronously re-rendered with the new template.
5. Preview panel shows a loading overlay while regenerating.
6. Once the new draft is available, the preview reloads.

---

## Summary of All API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/auth/signup` | Register new user |
| POST | `/api/auth/login` | Authenticate user |
| POST | `/api/auth/confirm` | Confirm email OTP |
| POST | `/api/auth/resend-code` | Resend OTP |
| POST | `/api/auth/forgot-password` | Initiate password reset |
| POST | `/api/auth/reset-password` | Complete password reset |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/auth/logout` | Logout (clear cookies) |
| POST | `/api/upload/presigned-url` | Get S3 presigned URL for resume |
| GET | `/api/resume/status/[uploadId]` | Poll processing status |
| GET | `/api/portfolio/[userId]` | Get portfolio data |
| PATCH | `/api/portfolio/[userId]/content` | Save field or section |
| POST | `/api/portfolio/[userId]/publish` | Publish portfolio |
| POST | `/api/portfolio/[userId]/ai-enhance` | AI enhancement suggestion |
| GET | `/api/portfolio/[userId]/analytics` | Portfolio analytics |
| POST | `/api/portfolio/[userId]/image-upload-url` | Get presigned URL for image |
| GET | `/api/portfolio/url` | Get current portfolio URL |
| POST | `/api/portfolio/draft-ready` | Check if draft is regenerated |
| POST | `/api/interview/start` | Create interview session |
| POST | `/api/interview/answer` | Submit answer, get feedback |
| POST | `/api/interview/exit` | Exit early, generate report |
| GET | `/api/interview/[sessionId]/report` | Get interview report |
| GET | `/api/interview/[sessionId]` | Get session state |
