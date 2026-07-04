# AI Portfolio Platform — Architecture Document

## Overview

This is a production-grade, serverless AI SaaS platform that converts user resumes into live, versioned portfolio websites. Users upload a resume (PDF or DOCX), an AI pipeline parses and structures the content, and a portfolio website is generated and served globally via CDN. The platform also includes an AI-powered interview practice module.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT (Browser)                         │
│                      SvelteKit Frontend                          │
│  Dashboard | Upload | Edit | Interview | Report | Auth           │
└─────────────────────┬───────────────────────────────────────────┘
                       │  HTTPS (Cognito JWT cookie)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AWS API GATEWAY (REST)                         │
│                  Cognito Authorizer on all routes                │
└────┬────────────────┬──────────────────┬────────────────────────┘
     │                │                  │
     ▼                ▼                  ▼
┌─────────┐    ┌─────────────┐    ┌────────────────┐
│  Auth   │    │  Portfolio  │    │   Interview    │
│ Lambdas │    │  Lambdas    │    │   Lambdas      │
└────┬────┘    └──────┬──────┘    └───────┬────────┘
     │                │                   │
     ▼                ▼                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                         DynamoDB (Single Table)                   │
│   PK: USER#{userId}  SK: UPLOAD# | PORTFOLIO# | SESSION# | VIEW# │
└──────────────────────────────────────────────────────────────────┘

RESUME PROCESSING PIPELINE (Async, Event-Driven):

Client
  │  PUT (pre-signed URL, no backend)
  ▼
S3 Quarantine Bucket (UNTRUSTED)
  │  S3:ObjectCreated event
  ▼
Validation Lambda ──── REJECTED ──→ S3 Rejected Bucket → DynamoDB: REJECTED
  │ VALIDATED
  ▼
S3 Validated Bucket
  │  S3:ObjectCreated event
  ▼
Ingestion Lambda → DynamoDB: EXTRACTING_TEXT → SQS
  │
  ▼
AI Processing Lambda (SQS trigger)
  │  OpenAI gpt-4o-mini
  ▼
DynamoDB: AI_COMPLETE (parsedData + portfolioContent saved)
  │  async Lambda invoke
  ▼
Portfolio Generator Lambda
  │  renders HTML template
  ▼
S3 Portfolio Bucket → {userId}/draft/index.html
  │  on publish:
  ▼
S3 Portfolio Bucket → {userId}/v{N}/index.html
  │
  ▼
CloudFront CDN → Public URL
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | SvelteKit (Svelte 5), Tailwind CSS, Vite |
| Auth | AWS Cognito (JWT, OAuth cookies) |
| API | AWS API Gateway (REST, Cognito authorizer) |
| Compute | AWS Lambda (Python 3.12) |
| Database | Amazon DynamoDB (single table design) |
| Queue | Amazon SQS + DLQ |
| Storage | Amazon S3 (quarantine, validated, rejected, portfolio buckets) |
| CDN | AWS CloudFront |
| AI | OpenAI gpt-4o-mini |
| Secrets | AWS Secrets Manager |
| Observability | CloudWatch Logs (structured JSON, correlation IDs) |
| IaC | Terraform |

---

## Backend Lambda Functions

### Auth / Portfolio Group

| Function | HTTP Route | Purpose |
|----------|-----------|---------|
| `get_status` | `GET /resume/status/{uploadId}` | Poll resume processing pipeline status |
| `get_portfolio` | `GET /portfolio/{userId}` | Fetch full portfolio data |
| `patch_portfolio` | `PATCH /portfolio/{userId}/content` | Edit scalar fields or entire sections |
| `publish_portfolio` | `POST /portfolio/{userId}/publish` | Promote draft to live versioned portfolio |
| `get_analytics` | `GET /portfolio/{userId}/analytics` | Aggregated portfolio view analytics |
| `get_image_upload_url` | `POST /portfolio/{userId}/image-upload-url` | Presigned URL for image upload |
| `ai_enhance_portfolio` | `POST /portfolio/{userId}/ai-enhance` | OpenAI-powered field/section/item suggestions |

### Interview Group

| Function | HTTP Route | Purpose |
|----------|-----------|---------|
| `start` | `POST /interview/start` | Create session, generate first question |
| `answer` | `POST /interview/answer` | Evaluate answer, return feedback + next question |
| `exit` | `POST /interview/exit` | Early exit, generate partial report |
| `report` | `GET /interview/{sessionId}/report` | Fetch final interview report |

### Pipeline Group (Event-Driven)

| Function | Trigger | Purpose |
|----------|---------|---------|
| `validation/handler` | S3:ObjectCreated (quarantine bucket) | Validate + promote/reject file |
| `ingestion/handler` | S3:ObjectCreated (validated bucket) | Extract text, enqueue for AI |
| `ai_processing/handler` | SQS event | Parse resume with OpenAI, save structured data |
| `portfolio/handler` | Lambda invoke (async) | Render portfolio HTML from template |
| `process_access_logs/handler` | CloudFront logs / schedule | Parse view logs, write VIEW# analytics records |

---

## DynamoDB Single-Table Design

### Partition Key Pattern

```
PK = USER#{userId}
```

### Sort Key Patterns

| SK Pattern | Record Type | Description |
|-----------|------------|-------------|
| `UPLOAD#{uploadId}` | Upload | Resume upload + processing state |
| `PORTFOLIO#current` | Portfolio | Current portfolio content, template, sections |
| `SESSION#{sessionId}` | Interview | Interview session questions, history, report |
| `VIEW#{timestamp}#{visitorHash}` | Analytics | Individual portfolio view event |

### UPLOAD Record Schema

```
status         PENDING_UPLOAD | VALIDATING | VALIDATED | EXTRACTING_TEXT |
               QUEUED_FOR_AI | AI_PROCESSING | AI_COMPLETE | GENERATING |
               COMPLETE | REJECTED | AI_FAILED | FAILED
filename       original uploaded filename
category       software_engineer | designer | marketing | finance
templateId     template name (minimal, modern, bold, etc.)
parsedData     JSON string — structured resume data from OpenAI
portfolioContent JSON string — {headline, bio, uniqueValue}
portfolioPath  S3 key of rendered portfolio
version        integer — current version
reason         error message (only if failed)
createdAt      ISO 8601 timestamp
updatedAt      ISO 8601 timestamp
```

### PORTFOLIO#current Record Schema

```
status         PUBLISHED | DRAFT | IN_PROGRESS
parsedData     full structured portfolio data (JSON object)
portfolioContent {headline, bio, uniqueValue}
category       software_engineer | designer | marketing | finance
templateId     active template name
sectionOrder   [] custom section ordering
hiddenSections [] hidden section names
portfolioPath  S3 path of published portfolio
version        current published version number
createdAt      ISO 8601 timestamp
updatedAt      ISO 8601 timestamp
```

### SESSION Record Schema

```
sessionId      UUID
mode           non-follow-up | follow-up
difficulty     easy | medium | hard | mix
totalQuestions 7 | 15 | 25
questionsAsked integer counter
source         resume | role
roleInfo       custom role description (if source=role)
status         active | completed
topicPlan      [{topic, count, asked}, ...]
currentTopicIndex  integer
currentFollowUpCount integer
questions      [] pre-generated question strings (non-follow-up only)
currentQuestion string
currentTopic   string
history        [{question, answer, topic, score, strengths, weaknesses, idealAnswer}, ...]
skillScores    {topic: [scores], ...}
report         {} completed report object
userProfile    parsed resume data
createdAt / updatedAt timestamps
```

---

## Data Models (src/shared/resume_models.py)

### Category Registry

Four supported professions, each with a dedicated Pydantic model and OpenAI parsing schema:

| Category | Key | Extra Fields |
|----------|-----|-------------|
| Software Engineer | `software_engineer` | projects (tech_stack, github_repo, project_url) |
| Designer | `designer` | design_philosophy, software_proficiency, awards, DesignProject fields |
| Marketing | `marketing` | campaigns (campaign_name, type, channels, budget, metrics) |
| Finance | `finance` | financial_modeling, investment_portfolios |

### Shared Fields Across All Categories

```
Profile:        full_name, headline, email, phone, location, summary
                social_links: {linkedin, github, gitlab, portfolio, twitter}
                profile_image: URL string

SkillGroup:     category (string), skills[] (string array)

Experience:     company, role, location, start_date, end_date, is_current
                description, key_points[], images[]
                + marketing: channels_managed
                + finance: financial_metrics_managed

Education:      degree, field_of_study, institution, location
                start_year, end_year, grade_or_score

Certification:  name, issuer, year, certification_url

Achievement:    title, description, year, achievement_url
```

---

## Resume Processing Pipeline Detail

### Step 1 — Pre-Signed Upload URL

- Client calls `POST /api/upload/presigned-url` with `{filename, contentType, category, templateId}`
- Lambda generates a short-lived PUT presigned URL scoped to the quarantine bucket
- URL enforces: content-type header, max file size
- Client uploads **directly** to S3 (no file bytes ever pass through Lambda)

### Step 2 — Quarantine Validation (Security Gate)

Triggered by `S3:ObjectCreated` on quarantine bucket. Fail-fast layered validation:

1. Extension check — must be `.pdf` or `.docx`
2. File size check — max 10MB
3. Magic number check:
   - PDF: first bytes must be `%PDF-`
   - DOCX: must start with PK ZIP signature
4. DOCX zip bomb protection:
   - Max decompressed size: 50MB
   - Max compression ratio: 20x
   - Max file entries: 1000
5. XML integrity check (DOCX)

**On PASS:** Copy to validated bucket with metadata `{validated=true, scanVersion, validatedAt}`. Delete from quarantine. DynamoDB → `VALIDATED`.

**On FAIL:** Move to rejected bucket. DynamoDB → `REJECTED`. User notified.

### Step 3 — Ingestion

Triggered by `S3:ObjectCreated` on validated bucket.

- Extracts text: PyPDF2 (PDF) or python-docx (DOCX)
- DynamoDB → `EXTRACTING_TEXT` then `QUEUED_FOR_AI`
- Publishes SQS message: `{userId, uploadId, resumeText, category, templateId}`
- Resume text is NOT stored in DynamoDB (PII protection)

### Step 4 — AI Processing

Triggered by SQS.

- Fetches OpenAI API key from Secrets Manager
- Calls OpenAI `gpt-4o-mini` with:
  - Category-specific Pydantic JSON schema
  - Portfolio generation prompt
- Response shape:
  ```json
  {
    "parsed": { ... },
    "portfolio": {
      "headline": "...",
      "bio": "...",
      "skillCategories": {...},
      "experienceHighlights": [...],
      "uniqueValue": "..."
    }
  }
  ```
- Saves `parsedData` + `portfolioContent` to DynamoDB → `AI_COMPLETE`
- Asynchronously invokes Portfolio Generator Lambda
- On error: DynamoDB → `AI_FAILED` (generic user message, real error in CloudWatch)

### Step 5 — Portfolio Generation

Triggered by async Lambda invocation.

- Normalizes data: HTML-escapes all strings, validates URLs (http/https only)
- Dispatches to selected template module
- Template renders full static HTML + embedded CSS (no JS)
- CSP header: `script-src 'none'`
- Writes to S3:
  - Draft: `{userId}/draft/index.html`
  - Publish: `{userId}/v{version}/index.html`
- Invalidates CloudFront cache
- On error: DynamoDB → `FAILED`

---

## Portfolio Templates

Templates are **TypeScript modules** that live in the **frontend repo** at:

```
AI-Portfolio-frontend/src/lib/templates/
├── index.ts        # renderPortfolio() dispatcher + normalize()
├── base.ts         # shared helpers (_editable, _listEditable, EDITOR_SCRIPT)
├── aurora.ts
├── circuit.ts
├── codex.ts
├── cosmos.ts
├── galaxy.ts
├── luxe.ts
├── navy-gold.ts
├── nebula.ts
├── neon.ts
├── quantum.ts
└── retro.ts
```

Each template exports `html(v: NormalizedData): string` and produces a fully self-contained HTML file with embedded CSS.

### Where Templates Are Used

| Context | Path | Purpose |
|---------|------|---------|
| Edit page preview | `AI-Portfolio-frontend/src/lib/templates/` | Live in-browser re-render as user edits |
| Published portfolio | Same files, **bundled into Lambda zip** at build time | Generates static HTML written to S3 |

> **Critical:** Both contexts use the exact same TypeScript source. The edit preview and the published portfolio are pixel-identical by design. The only difference is `publishMode=true` on the Lambda side, which strips `EDITOR_SCRIPT` and `contenteditable` attributes, and injects a `CSP: script-src 'none'` meta tag.

### Shared Template Helpers (base.ts)

- `normalize(parsedData, portfolioContent, ...)` — HTML-escapes all strings, validates URLs, merges section data
- `_editable(path)` — renders `data-path` + `contenteditable` attrs (edit mode only)
- `_listEditable(path)` — same for list fields
- `EDITOR_SCRIPT` — inline JS that wires contenteditable → API PATCH calls (edit mode only, stripped on publish)

### Template Data Contract

All templates receive a `NormalizedData` object (from `normalize()`):

```typescript
{
  // Profile
  name, headline, bio, email, phone, location,
  profile_image,      // validated https URL or empty string
  linkedin_url, github_url, portfolio_url, twitter_url,

  // Sections
  skill_groups:           [{ category: string, skills: string[] }],
  experience:             [...],
  projects:               [...],
  education:              [...],
  certifications:         [...],
  achievements:           [...],
  awards:                 [...],
  campaigns:              [...],
  financial_modeling:     [...],
  investment_portfolios:  [...],
  design_philosophy:      string,
  software_proficiency:   string[],
  custom_sections:        [{ section_id, title, display_type, items: [...] }],

  // Metadata
  category:         string,
  section_order:    string[],   // custom display order
  hidden_sections:  Set<string>, // omitted from render
  edit_mode:        boolean,    // true in browser preview, false on Lambda publish
}
```

---

## Portfolio Generator Lambda — Build Process

> **This is the most important operational detail for template changes.**

The Portfolio Generator Lambda (`src/lambdas/portfolio/handler.ts`) is a **Node.js Lambda** that imports templates from `./templates/index`. That `templates/` folder does **not** exist in the backend repo — it is assembled at build time by copying from the frontend repo.

### Build Script

```
build-portfolio-lambda.sh
```

What it does:

```
AI-Portfolio-frontend/src/lib/templates/*.ts
            ↓  cp (copied verbatim)
dist/lambdas/portfolio_build/templates/
            ↓  esbuild (bundle + transpile to Node 22)
dist/lambdas/portfolio_build/index.js
            ↓  python3 zipfile
dist/lambdas/portfolio_generator.zip
            ↓  terraform apply (uploads zip to Lambda)
AWS Lambda: portfolio_generator
            ↓  invoked on upload complete / publish
S3: {userId}/{uploadId}/v{N}/index.html  ←  public portfolio
```

### When to Run the Build

| Change Made | Build Required? | Terraform Apply Required? |
|-------------|----------------|--------------------------|
| Edit any `src/lib/templates/*.ts` | **YES** | **YES** |
| Edit `src/lambdas/portfolio/handler.ts` | **YES** | **YES** |
| Edit any other Python Lambda | No | YES |
| Edit Terraform modules only | No | YES |
| Edit frontend SvelteKit routes/components | No | No (frontend deploy only) |

### Commands

```bash
# Always run these two together when templates or handler.ts change:
bash build-portfolio-lambda.sh
terraform apply
```

### What Breaks If You Skip the Build

- The **edit preview** will show the updated template (it runs in the browser directly from the frontend source).
- The **published portfolio** (what users share publicly) will use the **old Lambda zip** with the old templates — the changes are invisible on the live site.
- Already-published portfolios at `/v1/`, `/v2/` etc. are immutable snapshots. Users must re-publish to get updated template styling applied.

---

## AI Enhancement System

`ai_enhance_portfolio.py` supports four request shapes:

### Shape A — Scalar Field Enhancement

```json
{ "field": "bio|headline|uniqueValue", "instruction": "make it more impactful" }
```
Response: `{ "field": "bio", "suggestedValue": "..." }`

### Shape B — Section Item Field Enhancement

```json
{
  "section": "experience",
  "itemIndex": 0,
  "enhanceField": "description|key_points|...",
  "instruction": "quantify the impact"
}
```
Allowlisted enhanceable fields per section:
- `experience`: description, key_points
- `projects`: description, responsibilities, measurable_outcomes
- `achievements`: description
- `campaigns`: performance_metrics
- `financial_modeling`: outcome

Response: `{ "section": "...", "itemIndex": N, "enhanceField": "...", "suggestedValue": ... }`

### Shape C — Skills Enhancement

```json
{ "section": "skills", "instruction": "add more relevant skills" }
```
Response: `{ "section": "skills", "suggestedValue": [{category, skills[]}] }`

### Shape D — Portfolio Analysis + Suggestions

```json
{ "action": "analyze_and_suggest", "parsedData": {...}, "portfolioContent": {...}, "category": "..." }
```
Response: `{ "suggestions": [{ id, section, index, field, label, sublabel, instruction, priority }] }`
- Returns 3–8 actionable suggestions
- Used for the "Analyze & Suggest" sidebar feature in the edit page

**Security:** User instructions capped at 300 chars and sanitized with regex before passing to OpenAI.

---

## Interview System

### Session Lifecycle

```
POST /interview/start
  → Generate topic plan (3-5 topics summing to totalQuestions)
  → Non-follow-up mode: generate ALL questions upfront
  → Follow-up mode: generate ONLY first question
  → Return: {sessionId, question, questionNumber, totalQuestions, topic}

POST /interview/answer (repeat until isComplete)
  → Evaluate answer via OpenAI → {score 1-10, strengths[], weaknesses[], idealAnswer}
  → Record in history
  → Determine next question:
       Non-follow-up: pick from pre-generated list
       Follow-up: if topic quota filled → next topic else generate follow-up
  → If all questions done: compute_report() → isComplete=true
  → Return: {feedback, nextQuestion, isComplete, sessionId}

POST /interview/exit (optional early exit)
  → Immediately compute partial report from accumulated history
  → Return: {sessionId, report}

GET /interview/{sessionId}/report
  → Return cached report or compute on-the-fly
```

### Follow-Up Logic

- `MAX_FOLLOW_UPS_PER_TOPIC = 2`
- Each topic can have: 1 base question + up to 2 follow-ups = max 3 per topic
- Follow-ups are adaptive: generated based on the user's previous answer to that topic
- Once a topic is exhausted, session advances to `currentTopicIndex + 1`

### Report Structure

```json
{
  "overallScore": 7.4,
  "totalAnswered": 15,
  "topicScores": { "React": 8, "System Design": 6, "..."  },
  "strengths": ["Clear explanation", "Good examples"],
  "weaknesses": ["Lacks depth on X", "No quantified outcomes"],
  "suggestions": ["Practice STAR format", "Study distributed systems"]
}
```

---

## Analytics System

### Data Ingestion

`process_access_logs/handler.py` reads CloudFront access logs, parses each hit against portfolio URLs, and writes individual `VIEW#` records to DynamoDB:

```
PK: PORTFOLIO#{userId}
SK: VIEW#{timestamp}#{visitorHash}

Fields: country, source (utm_source), device, ttfb,
        cacheHit, version, timestamp
```

### Aggregation (get_analytics.py)

Queries all `VIEW#` records for a user and computes:

| Metric | Description |
|--------|-------------|
| `totalViews` | All-time view count |
| `last7Days` | Views in last 7 days |
| `last30Days` | Views in last 30 days |
| `byCountry` | `{US: 42, IN: 18, ...}` |
| `bySource` | `{direct: 50, linkedin: 20, ...}` |
| `byDevice` | `{desktop: 60, mobile: 40}` |
| `timeline` | `[{date, views}, ...]` |
| `uniqueVisitors` | Distinct visitor hashes |
| `avgTtfb` | Average time-to-first-byte |
| `cacheHitRate` | % of requests served from CloudFront cache |
| `byHour` | View distribution by hour of day |
| `byDayOfWeek` | View distribution by day |
| `byVersion` | Views per portfolio version |
| `bestTimeToShare` | Peak engagement window |

---

## Security Architecture

### Zero-Trust Ingestion

- ALL uploads go to quarantine bucket first
- No file is processed until it passes all validation layers
- AI is never invoked on unvalidated input (hard rule)

### Authorization Model

- All Lambda handlers verify JWT sub against path parameter userId
- API Gateway validates JWT via Cognito authorizer before any Lambda invocation
- IAM roles follow least-privilege — each Lambda only has permissions it needs

### Input Sanitization

| Layer | Protection |
|-------|-----------|
| File validation | Extension, MIME, magic bytes, zip bomb |
| AI inputs | Instructions capped 300 chars, sanitized with regex |
| Portfolio fields | Allowlist + string length caps |
| Portfolio HTML | All strings HTML-escaped (`_e()`), URLs validated |
| Rendered HTML | CSP header `script-src 'none'` — no JavaScript execution |
| Interview answers | 2000 char cap, control char removal |

### Secrets

- OpenAI API key stored in AWS Secrets Manager
- Fetched at Lambda cold start
- Never logged, never in DynamoDB

---

## Frontend Architecture

### Framework & Structure

```
SvelteKit (Svelte 5) + Tailwind CSS + Vite

src/
├── routes/
│   ├── app/              # Protected pages (require auth)
│   │   ├── dashboard/
│   │   ├── resumes/upload/
│   │   ├── resumes/[uploadId]/processing/
│   │   ├── portfolio/[userId]/edit/
│   │   ├── interview/setup/
│   │   ├── interview/[sessionId]/
│   │   └── interview/[sessionId]/report/
│   ├── api/              # SvelteKit server routes (backend proxy)
│   │   ├── upload/
│   │   ├── resume/
│   │   ├── portfolio/
│   │   ├── interview/
│   │   └── auth/
│   └── (auth)/           # Public auth pages (login, signup, etc.)
├── lib/
│   ├── services/         # API call abstractions
│   ├── types/            # TypeScript interfaces
│   ├── templates/        # Client-side template previews
│   ├── server/           # Server-only utilities (Cognito session)
│   └── stores/           # Svelte writable stores (auth state)
```

### Auth Pattern

- Cognito issues `id_token` and `refresh_token` stored as HTTP-only cookies
- SvelteKit server routes (`+server.ts`) proxy all backend calls, attaching the token from cookies
- The browser never directly calls the backend API or handles the JWT
- `src/lib/server/cognito.ts` → `getSessionUser(cookies)` extracts and verifies the session

### API Proxy Pattern

All `src/routes/api/**` routes act as a secure proxy:

```
Browser → SvelteKit API Route (+server.ts) → AWS API Gateway → Lambda
                ↑ attaches JWT from cookie
```

This pattern ensures:
- The backend API base URL is never exposed to the browser
- The JWT is never accessible to client-side JavaScript
- All auth is handled server-side

### State Management

- `src/lib/stores/auth.ts` — global auth state `{user, loading}`
- Edit page uses local Svelte `$state` for fine-grained reactivity
- No global state for portfolio data — loaded fresh per route

---

## Infrastructure (Terraform)

### Module Structure

```
terraform/
├── main.tf                     # Root composition
├── modules/
│   ├── cognito/                # User pool, app client, custom flows
│   ├── api-gateway/            # REST API, Cognito authorizer, CORS, logging
│   ├── lambda/                 # Functions, layers, IAM roles, env vars
│   ├── dynamodb/               # Single table, GSIs, TTL
│   ├── s3/                     # Quarantine, validated, rejected, portfolio buckets
│   ├── sqs/                    # Resume processing queue + DLQ
│   └── cloudfront/             # CDN distribution, behaviors, cache policies
```

### Lambda Layers

- `pdf_processing` layer: PyPDF2, python-docx (packaged in `src/layers/`)
- Shared across validation, ingestion, and AI processing functions

### Environment Variables Per Lambda

All sensitive config (bucket names, DynamoDB table, SQS queue URL, Secrets Manager ARN) injected via Terraform as Lambda environment variables.

---

## Deployment Flow

```
1. Build portfolio Lambda (REQUIRED whenever templates or handler.ts change)
   bash build-portfolio-lambda.sh
   → Copies frontend templates into build dir
   → Bundles with esbuild → dist/lambdas/portfolio_generator.zip

2. terraform apply
   → Creates/updates all AWS resources
   → Uploads portfolio_generator.zip to Lambda
   → Outputs: API Gateway URL, CloudFront domain, Cognito pool IDs

3. Frontend deployment
   → Set VITE_API_BASE_URL, VITE_COGNITO_* env vars
   → npm run build → deploy to hosting (Vercel / Amplify / S3+CloudFront)

4. Portfolio CDN
   → S3 bucket as CloudFront origin
   → Portfolios served at: https://{cloudfront-domain}/{userId}/v{N}/
```

> **Rule:** Any change to `AI-Portfolio-frontend/src/lib/templates/*.ts` requires steps 1 + 2 to take effect on published portfolios. The edit preview updates immediately (it runs in the browser), but the Lambda that writes the public S3 HTML is only updated after build + deploy.

---

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Quarantine-first uploads | Users never upload directly to a trusted bucket |
| Async AI pipeline | AI is slow and expensive; never blocks UX |
| SQS decoupling | Ingestion and AI processing are independently scalable |
| Single-table DynamoDB | All entities in one table for efficient, predictable access patterns |
| Static HTML portfolios | No runtime server needed for portfolio serving; pure CDN delivery |
| CSP `script-src 'none'` | Portfolios contain user-generated content; no JS execution allowed |
| Allowlist for editable fields | Prevents arbitrary data injection via PATCH endpoint |
| Interview answers not re-fed to LLM | Prevents indirect prompt injection via crafted answers |
| JWT in HTTP-only cookies | Prevents XSS from accessing auth tokens |
| SvelteKit API proxy | Backend URL and JWT never exposed to browser JS |
