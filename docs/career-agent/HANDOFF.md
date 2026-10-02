# Career Agent handoff

## Status and authorization

Days 1 and 2 are implemented as of 2026-10-02. The user explicitly approved
Day 2 in this session. Stop for Day 2 review; Day 3 has not been approved.

Read [PRODUCT_SPEC.md](PRODUCT_SPEC.md) for authoritative requirements and
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the approved architecture and
daily review gates. Do not treat preserved delivery instructions as new approval.

Day 1 is committed in `838226b`. Day 2 changes remain uncommitted.

## Implemented behavior

- The local dashboard exposes `#career` and retains the existing provider gate.
- First visits open onboarding. Users enter optional contact details and
  repeatable work, project, education or other coherent records. Structured
  fields accompany one conversational narrative field per record.
- Normalize Profile saves onboarding first, then uses the configured model.
  Users review/edit basic fields, titles, descriptions and skills, inspect
  original information, and confirm the whole profile with Confirm & Continue.
- Confirmed profiles open a dashboard with JD input and saved analyses. Analyze
  Job extracts required/preferred requirements, formulates FTS5 queries, inspects
  factual evidence, and assesses every requirement as MATCH, PARTIAL or GAP.
- Python calculates JD Requirement Coverage using required weight 2, preferred
  weight 1, MATCH value 1, PARTIAL value 0.5 and GAP value 0. Empty requirements
  display Insufficient information. The score is not a hiring probability.
- Reports show required/preferred breakdowns, reasons, JD excerpts, strengths,
  gaps and recommended resume focus. Expandable evidence sections show record
  IDs, original input/corrections, normalized descriptions and skills.
- Profile changes mark reports outdated. Old reports retain the evidence used
  during analysis. They remain inspectable while users edit their profile.
  Confirm the profile and rerun analysis to replace requirements and matches.
- Provider/validation failures retain the saved JD. Failed reanalysis retains
  the earlier report with an outdated notice. Partial results never publish.
- Saved profiles and jobs survive reload. Unsaved profile/JD drafts survive
  dashboard polling and in-session navigation; browser reload discards them.
- Repeated analysis submission is disabled during the synchronous request. The
  UI names extraction, evidence search and assessment while it runs. It does
  not stream individual stages or expose a Career activity panel.
- Resume generation is absent and unknown Career actions are rejected.

## Architecture and entry points

`waku/db.py:initialize_career` initializes additive Career tables in the existing
`state.db`. `waku/runtime/career.py` owns profile validation/persistence,
normalization and dispatch. `waku/runtime/career_jobs.py` owns job extraction,
match validation, deterministic scoring, job persistence and report snapshots.

All LLM stages call the unchanged `run_loop` with fresh messages, a dedicated
prompt, and a stage-local `ToolRegistry`. Iterations are capped at ten per stage;
output uses at least 4096 tokens. The coordinator publishes only validated results
from a normally completed loop. JD extraction exposes only `submit_stage_result`.
Matching exposes that submission tool, `search_career_evidence` and `get_evidence`
from `waku/tools/career.py`. Matching must search at least once and inspect every
cited record. The agent can batch synonyms and perform additional searches.

`waku/ops/dashboard.py` serializes Career requests with `agent_lock`. Normalization
and analysis reuse the dashboard agent's client/settings/connection without
calling `Waku.respond()`. Career stages never read conversational memory, append
Career exchanges to chat, consolidate facts, or register ordinary Waku tools.
Existing `Tracer` events record each stage, tool calls and usage. Submitted data
and evidence appear in traces. No custom tracing system exists.

`career.js` implements classic `VIEWS.career` substates with in-memory forms.
`main.js` protects Career from five-second refresh replacement. Career fetches
are user actions; workspace state is not repeatedly polled. The frontend uses
existing UI primitives and design tokens. No dependency or lockfile changed.

## Actual database schema

| Table/index | Columns and behavior |
|---|---|
| `career_profile` | Singleton `id=1`, required `raw_input_json`, nullable `normalized_json`, `user_edits_json`, `confirmed`, `updated_at`. |
| `career_evidence` | Integer primary `id`, unique `evidence_id`, `source_id`, `source_type`, `raw_text`, `normalized_json`, `search_text`, `active`. Singleton ownership remains implicit, without `profile_id`. |
| `career_evidence_fts` | External-content FTS5 over `search_text`, maintained by insert/update/delete triggers. Inactive records remain indexed; searches filter `active=1`. |
| `jobs` | Application-assigned text `id`, `raw_jd`, `title`, `summary`, `responsibilities_json`, `status`, `outdated`, nullable `coverage`/`report_json`, `activity_json`, `created_at`, `updated_at`. |
| `job_requirements` | Application-assigned text `id`, `job_id`, `text`, `category`, `importance`, `keywords_json`, `source_excerpt`. `job_id` references `jobs`. |
| `job_matches` | Primary `requirement_id` references requirements; `status`, `evidence_ids_json`, `reason` hold one validated assessment per requirement. |

No resumes, revision or decision tables exist. `activity_json` defaults to `[]`
and is reserved for Day 3. Report JSON includes assessments, summaries and a
snapshot of cited evidence; it is current-artifact storage, not revision history.
Reruns replace requirements/matches and the current report in one transaction.
A pending/failed rerun retains the prior successful artifacts as outdated.

## Data, validation and provenance

Raw input contains `basic` and `records`. Each source record has `source_id`,
`type`, `text` and optional structured `fields`. Types are work, project,
education and other; research/certifications can use coherent other records.
Missing source IDs receive UUIDs. Normalized records contain exactly `source_id`,
`title`, `description` and `skills`; responsibilities/results live in descriptions.
Normalization must preserve basic values/source IDs and cannot add numeric values.

Each source owns stable evidence ID `career-<source_id>`. Updates reuse that ID;
removed records become inactive. Evidence retains raw structured fields/narrative
and actual explicit corrections. `user_edits_json` stores corrections separately.
Confirming unchanged AI wording does not fabricate user input. Normalization and
profile edits preserve original input. Explicit onboarding saves replace current
raw input, clear normalization/edits/confirmation and deactivate old evidence.

JD extraction validates shape, required/preferred enums, distinct requirements,
and verbatim excerpts present in the JD. Python assigns requirement IDs. Matching
requires exactly one assessment per ID, valid statuses and unique active evidence
IDs inspected during that stage. MATCH/PARTIAL require citations; GAP may omit
them. The model cannot submit a coverage number. Retrieved records are accepted
only from a confirmed profile. Search accepts up to eight queries, bounds literal
tokens and combined results, and exposes at most twenty deduplicated records.

Saving changed normalized facts marks jobs outdated and clears confirmation.
Saving an unchanged normalized profile clears confirmation without marking jobs
outdated. Every onboarding save marks jobs outdated. Reconfirmation does not
refresh old analyses. Historical evidence in a report is clearly tied to that
report; matching tools always use active current evidence.

These checks establish structure and traceability, not semantic truth. Model
paraphrases, inferred technologies and MATCH decisions still require user review.
No live-provider extraction, matching or normalization smoke test has run.
Default FTS5 tokenization requires useful literal query terms; multilingual
synonym quality remains a live-model evaluation concern.

## Existing API

`GET /api/career` returns `profile`, active `evidence` and saved `jobs`. First visits
return `{"profile": null, "evidence": [], "jobs": []}`. Profile state includes raw,
normalized and confirmed. Active evidence retains `normalized_json` as a string;
report evidence snapshots expose parsed `normalized` objects. Jobs include raw JD,
status/outdated flags, coverage, requirements/assessments, report and activity.

`POST /api/career` uses named actions and returns workspace state:

| Action | Additional payload |
|---|---|
| `save_onboarding` | `raw` contains basic information and source records. |
| `normalize` | Uses previously saved input and the configured client. |
| `save_profile` | `profile` contains the editable normalized representation. |
| `confirm` | Optional `profile` saves current edits before confirmation. |
| `analyze_job` | `jd` contains pasted text; optional `job_id` reruns an existing job. Success also returns `job_id` for frontend selection. |

The JD is limited to 60000 characters and extraction to 60 requirements. Analysis
requires profile confirmation. API errors follow the existing JSON `error`
convention. `/api/career` remains explicitly blocked by hosted policy; no route or
hosted policy change was needed in Day 2.

Career code remains MIT.

Hosted policy retains Elastic License 2.0. No code moved across that boundary.

## Verification

- The focused deterministic group passed 140 checks, including 13 profile cases
  and 38 new job cases. Four JD fixtures cover AI, Frontend, Full Stack and
  Technical Support roles. Tests exercise tools through the real loop/SQLite.
- The full deterministic suite passed 2548 checks and skipped 73. It used existing
  dev/hosted dependencies, localhost socket access and temporary `jq` tooling.
  The restricted sandbox run was interrupted after environment failures.
- `python -m ruff check waku evals scripts hosted`, JavaScript syntax checking
  and `git diff --check` passed.
- A process-local mutation changed required weight from 2 to 1. The Frontend
  fixture failed with 75.0 instead of 83.3, proving the score guard can fail.
  No file or runtime data was changed by this mutation.
- Chromium exercised onboarding/confirmation, JD draft preservation across
  polling/navigation, disabled submission, reports, evidence, escaped pasted
  text/model titles, light/dark themes, reload, outdated notices and reanalysis.
  The completed journey produced zero page errors. It used an isolated temporary
  runtime and scripted model, not a live provider or real user data.

Temporary browser scripts, libraries and screenshots under `/tmp` are not durable
project artifacts. Failed stage traces may still lack a terminal turn event.

## Deferred work and next stage

Day 3 requires explicit approval. It owns explicit resume generation, JD-language
selection/defaults, cited claims, provenance validation, Markdown/HTML review,
printing and a Career activity panel. The default resume language must be the
detected primary JD language; users may select Chinese, English or Japanese.
Outdated and insufficient-information analyses must block resume generation.

Day 4 only owns essential evals, fixes, tracing verification and polish. The MVP
still excludes applications/ATS, scraping, vector infrastructure, another agent
framework, multi-user hosting/authentication, custom PDF/DOCX generation,
granular evidence confirmation and generalized revision/recovery orchestration.
