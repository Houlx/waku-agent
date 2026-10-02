# Career Agent handoff

## Status and authorization

Day 1 implementation and verification are complete as of 2026-10-02. The user
approved Day 1 only. No next implementation stage is approved. Do not begin Day 2
until the user explicitly approves it.

Read [PRODUCT_SPEC.md](PRODUCT_SPEC.md) for authoritative requirements and
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the approved architecture and
daily review gates. The current task ends after saving these documents.

## Implemented behavior

- The local dashboard exposes `#career` in its sidebar and retains the existing
  provider setup gate.
- First visits open onboarding. Users can enter optional contact details and
  repeatable work, project, education, or other records. Structured fields
  accompany one conversational narrative field per record.
- Normalize Profile saves onboarding first, then runs the configured model.
- Users can edit normalized basic fields, titles, descriptions, and skills.
  Expandable sections display original record fields and text.
- Confirm & Continue saves edits and confirms the whole profile. The dashboard
  then offers profile editing and original-input editing.
- Saved data survives reload. Unsaved frontend drafts survive dashboard polling
  and in-session navigation; browser reload does not preserve unsaved drafts.
- Career initialization adds only profile/evidence storage. The dashboard states
  that job analysis is not available yet.

## Architecture and entry points

`waku/db.py:initialize_career` initializes the opt-in Career schema in the existing
`state.db`. `waku/runtime/career.py` owns validation, persistence, normalization,
and action dispatch. It uses ordinary SQLite transactions.

Normalization calls the unchanged `run_loop` with fresh messages, a dedicated
system prompt, and a registry containing only `submit_stage_result` from
`waku/tools/career.py`. The configured iteration limit is capped at ten; output
uses at least 4096 tokens. The coordinator saves a validated submission only after
the loop completes normally. Invalid/unfinished proposals and provider failures
retain saved onboarding input.

`waku/ops/dashboard.py` serializes Career requests through the existing
`agent_lock`. Normalization reuses the dashboard agent's client, settings and
connection, but does not call `Waku.respond()` or its memory/session path.

Career does not read conversational memory, append Career exchanges to chat,
consolidate Career facts, or add tools to the ordinary registry. Existing `Tracer`
events record normalization, tool calls, and token usage. Tool events include
profile data. No Career activity panel or custom tracing system exists yet.

`career.js` implements a classic `VIEWS.career` view with in-memory form state.
`main.js` protects that view from five-second refresh replacement. Career fetches
are classified as user actions; the workspace state is not repeatedly polled.
The frontend uses existing UI primitives and design tokens.

## Actual database schema

| Table/index | Columns and behavior |
|---|---|
| `career_profile` | `id` is constrained to 1; `raw_input_json` is required; `normalized_json` is nullable; `user_edits_json` defaults to `{}`; `confirmed` defaults to 0; `updated_at` stores the latest save time. |
| `career_evidence` | `id` is the integer primary key; `evidence_id` is unique; `source_id`, `source_type`, `raw_text`, `normalized_json`, and `search_text` are required; `active` defaults to 1. The singleton profile owns records implicitly; no `profile_id` column or foreign key exists. |
| `career_evidence_fts` | External-content FTS5 indexes `search_text` using evidence integer IDs. Insert/update/delete triggers maintain the index. Inactive rows remain indexed; future retrieval must filter `active=1`. |

No jobs, requirements, matches, resumes, revision, or decision tables exist.

## Data and provenance

Raw input contains `basic` and `records`. Each raw record contains `source_id`,
`type`, `text`, and optional structured `fields`. Types are `work`, `project`,
`education`, and `other`; research/certifications can use coherent `other` records.
The application assigns missing source IDs with UUIDs.

Normalized input contains the same basic-field keys and one record per source.
Each normalized record contains exactly `source_id`, `title`, `description`, and
`skills`. Responsibilities/results currently live in descriptions rather than
separate arrays. The model must preserve basic values and source IDs.

Each source produces one evidence row with ID `career-<source_id>`. Updates reuse
that ID; removed/replaced records become inactive. Evidence raw text includes
original structured fields and narrative, plus an explicit correction when the
user actually changes a normalized record. `user_edits_json` stores basic-field
corrections and record corrections keyed by source ID. Confirmation of unchanged
AI wording does not fabricate a user edit.

Normalization never overwrites raw input. Explicitly saving onboarding replaces
the current raw input, clears normalized content/edits/confirmation, and deactivates
old evidence. This is current-state storage, not a history or revision system.
Saving profile edits leaves raw input intact and clears confirmation. Confirm
then sets `confirmed=1` after optionally saving submitted edits.

## Existing API

`GET /api/career` returns `profile` and active `evidence`. A first visit returns
`{"profile": null, "evidence": []}`. Profile state includes `raw`, `normalized`,
and `confirmed`; evidence state includes IDs, type, raw text, and normalized JSON
as a string.

`POST /api/career` accepts these actions and returns the same workspace state:

| Action | Additional payload |
|---|---|
| `save_onboarding` | `raw` contains basic information and source records. |
| `normalize` | The action uses previously saved raw input and the configured client. |
| `save_profile` | `profile` contains the editable normalized representation. |
| `confirm` | Optional `profile` saves current edits before confirmation. |

The dashboard follows its existing JSON `error` convention. All other Career
actions are rejected. Hosted policy explicitly blocks `/api/career`; policy
changes remain under hosted's Elastic License 2.0. No code crossed that boundary.

## Files in the Day 1 change

The implementation added:

- `waku/runtime/career.py`
- `waku/tools/career.py`
- `waku/ops/static/js/career.js`
- `evals/deterministic/test_career_profile.py`
- `docs/career.md`

The implementation modified:

- Storage/API: `waku/db.py`, `waku/ops/dashboard.py`.
- Frontend: `waku/ops/static/index.html`, `js/main.js`, `style.css`, and the static
  README.
- Documentation: root README, `docs/README.md`, and `docs/architecture.md`.
- Contract evals: `test_dashboard_routes.py`, `test_dashboard_background_header.py`,
  `test_design_system.py`, and `hosted/test_route_contract.py` under
  `evals/deterministic/`.
- Hosted policy: `hosted/core/policy.py`.

The documentation handoff adds the three files in this directory and links them
from `docs/README.md` and `docs/career.md`. No dependencies or lockfiles changed.
The work remains uncommitted.

## Verification and current limits

Day 1 verification produced these results:

- The focused deterministic group passed 102 checks, including 13 Career evals.
  It covers the journey, confirmation/edit provenance, raw persistence, FTS
  updates, isolation, invalid sources/numbers, provider failure, loop limits,
  structured fields, and dashboard handlers.
- `python -m ruff check waku evals scripts hosted` passed.
- `node --check waku/ops/static/js/career.js` and `git diff --check` passed.
- A numeric-grounding mutation was rejected by the matching Career eval.
- Chromium exercised onboarding, polling preservation, scripted normalization,
  confirmation saving edits, reload persistence, original-input inspection, and
  both themes. The journey produced zero page errors.
- The full deterministic suite finished with 2509 passed, 73 skipped, and one
  failure in `hosted/test_gateway.py::test_two_simultaneous_requests_at_the_cap_cannot_both_start`.
  That test passed in isolation. No hosted concurrency logic changed; investigate
  separately rather than expanding Career scope silently.

The focused command is:

```bash
.venv/bin/python -m pytest -q \
  evals/deterministic/test_career_profile.py \
  evals/deterministic/test_dashboard_routes.py \
  evals/deterministic/hosted/test_route_contract.py \
  evals/deterministic/test_static_assets.py \
  evals/deterministic/test_design_system.py \
  evals/deterministic/test_rulebook.py \
  evals/deterministic/test_dashboard_background_header.py
```

The full suite requires existing `[dev]` and `[hosted]` dependencies, `jq`, and
localhost socket access. Temporary browser tooling and screenshots under `/tmp`
are not durable project artifacts. Browser verification used an isolated runtime
and scripted model, not a live provider or real user data.

Validation checks structure, IDs and new numeric values. It cannot prove semantic
faithfulness, including technologies or responsibilities. Users must review the
profile. Normalization has not had a live-provider smoke test. Failed
normalization traces may lack a terminal turn event. The profile UI has not added
separate responsibility/achievement/metric editors.

## Deferred work and next stage

Day 2 is the next planned stage, but it is not approved for execution. After
explicit approval, add JD input/extraction, required/preferred requirements,
agent-authored FTS5 queries, `get_evidence`, MATCH/PARTIAL/GAP assessments,
deterministic coverage, a report, and an evidence viewer. Implement simple
outdated-analysis flags when job artifacts exist, then stop for review.

Day 3 owns explicit resume generation, JD-language detection/defaults, language
selection, cited claims, Markdown/HTML review, printing, and a Career activity
panel. Day 4 only owns essential evals, fixes, tracing verification, and polish.

The MVP excludes applications/ATS, scraping, vector infrastructure, another agent
framework, multi-user hosting/authentication, custom PDF/DOCX generation, granular
evidence confirmation, and generalized revision/recovery orchestration.
