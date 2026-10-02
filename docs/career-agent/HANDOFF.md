# Career Agent handoff

## Status and authorization

Days 1–3 are implemented. The user approved Day 3 on 2026-10-02. Stop for
Day 3 review; optional Day 4 has not been approved. The product requirements in
[PRODUCT_SPEC.md](PRODUCT_SPEC.md) and architecture in
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) remain authoritative.

Day 1 is committed in `838226b`; Day 2 is committed in `8e7bac3`. Day 3 changes
remain uncommitted.

Career code remains MIT.

Hosted policy remains Elastic License 2.0. No code moved across the license boundary.

## Implemented journey

The local `#career` workspace preserves the provider gate and existing dashboard
patterns. First visits open onboarding. Raw source records persist separately
from normalization and explicit edits. Users review and confirm the whole profile.
Career facts never enter ordinary chat or conversational memory.

Job analysis extracts required/preferred requirements, lets the agent formulate
bounded FTS5 searches, inspects cited records and validates MATCH/PARTIAL/GAP.
Python calculates coverage using required weight 2, preferred weight 1, MATCH 1,
PARTIAL 0.5 and GAP 0. Reports expose explanations, evidence snapshots, strengths,
gaps and recommended focus. Saved data survives reload; unsaved forms survive
polling and navigation but not reload. Failed reanalysis preserves earlier reports.

Job analysis never generates a resume. Users review the report, select English,
Chinese or Japanese and explicitly click Generate Tailored Resume. Generation
requires a confirmed profile, a completed current job analysis and usable
requirements. Backend gates reject unconfirmed, unknown, failed, outdated and
insufficient analyses before calling a model. Profile changes require reanalysis.

## Files and architecture

- `waku/db.py` adds the current-resume table without clearing runtime data.
- `waku/runtime/career.py` dispatches explicit generation and invalidates drafts
  when factual profile input changes.
- `waku/runtime/career_jobs.py` records observer-derived activity, exposes saved
  resumes and language defaults, and invalidates old drafts after reanalysis.
- `waku/runtime/career_resumes.py` validates, generates, persists and exports drafts.
- `waku/ops/dashboard.py` reuses the configured agent client and execution lock.
- `waku/ops/static/js/career.js` adds language selection, generation, cited review,
  downloads, printing and activity. `style.css` adds resume and print rules.
- `evals/deterministic/test_career_resumes.py` adds 22 focused cases. Existing
  profile/job evals now reject an unknown action and assert no automatic draft.
- `docs/career.md`, `docs/architecture.md`, the frontend README and the product
  specification's stage-status preamble reflect the completed behavior.

Resume generation calls the existing `run_stage` and unchanged `run_loop` with
fresh messages, a dedicated system prompt and only `get_evidence` and
`submit_stage_result`. Iterations remain capped at ten. Profile, JD, report and
evidence are labelled untrusted data. The coordinator saves only a valid result
from a completed stage. Failures retain the previous draft.

## Schema, provenance and language

Existing tables remain `career_profile`, `career_evidence`, `jobs`,
`job_requirements` and `job_matches`, with external-content `career_evidence_fts`.
Singleton evidence ownership remains implicit without `profile_id`.

`resumes` contains `id`, unique `job_id`, `language`, `content_json`, `outdated`,
`activity_json`, `created_at` and `updated_at`. Successful regeneration updates
one row per job. Profile changes and successful reanalysis mark old drafts
outdated; only successful regeneration clears that flag. No version history exists.

Model output contains `summary` and `skills` arrays of `{text, evidence_ids}`,
and `records` containing `{evidence_id, bullets}`. Every substantive claim needs
unique active evidence references inspected during that stage. Record bullets
must cite their own record. Unknown IDs, inactive records, uninspected citations,
extra protected-field proposals and new numeric values are rejected before saving.
Python attaches confirmed basic information, canonical record titles, raw structured
fields and evidence snapshots. Employers, positions, education fields and dates
in headings come from factual records; the model cannot replace those fields.

Evidence IDs remain `career-<source_id>`. Raw structured fields and narratives
remain available together with explicit corrections. Confirmation of unchanged
AI wording does not turn it into user-authored input.

Language defaults use a small script heuristic: Japanese kana selects Japanese;
Han-dominant text selects Chinese; otherwise English. Users override the default.
No new model call or language-detection dependency exists.

## Export and tracing

HTML review escapes all factual and generated text. Expandable citations show
source records. Markdown is derived deterministically from saved structured data,
with Markdown syntax escaped; it excludes citation/debug data.

Browser printing temporarily selects the light theme and hides dashboard chrome,
buttons, evidence and activity. Resume typography uses Chinese/Japanese system-font
fallbacks. No PDF library, DOCX export, template system or visual editor exists.

The stage observer forwards events to the existing Tracer, stamps job IDs, and
collects concise tool/stage activity without assistant prose or reasoning.
Activity includes evidence IDs, stage elapsed time, token usage and coverage.
JSONL, the permanent usage ledger and optional OpenTelemetry remain unchanged.
Older analyses without stored activity show an empty-activity message.

## Verification and limits

The focused Career and adjacent route, hosted-policy, design, static-asset and
rulebook group passed 140 checks. Ruff over `waku evals scripts hosted`, JavaScript
syntax checking and `git diff --check` passed. A process-local mutation disabled
numeric validation; the invented-70%-metric case failed as expected. No mutation
changed repository files or user runtime data.

An isolated temporary runtime and scripted model passed Chromium checks for
analysis without automatic generation, explicit Japanese selection, cited review,
light/dark themes, Markdown download, print visibility/PDF export and reload.
The browser recorded zero page errors. Browser artifacts remain under `/tmp`.

No live-provider generation, semantic groundedness or translation evaluation ran.
Citation and numeric validation cannot prove every paraphrase or inferred skill.
Users must review claims. The headless environment lacks CJK fonts, so its Japanese
labels show missing glyphs despite system-font fallbacks; glyph rendering needs a
machine with suitable fonts. Failed stages can still lack a terminal trace event.
Mixed-language or kanji-only JDs may need manual language override. Print pagination
uses browser defaults. The full deterministic suite was not rerun for Day 3.

## Remaining optional Day 4

Day 4 requires explicit approval. It can run a live-provider groundedness and
translation smoke check, verify CJK printing with installed fonts, check failed
trace completion, run the full essential gate and fix acceptance issues found.
Small usage/demo documentation and UI polish remain optional. Add no major
architecture, feature, deployment or application-tracking infrastructure.
