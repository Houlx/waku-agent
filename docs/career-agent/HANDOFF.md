# Career Agent handoff

## Status

Days 1–4 are complete. Day 4 was explicitly approved on 2026-10-02 for
stabilization, evaluation, documentation and demo preparation. V1 feature development stops
here. Phase 1 runtime separation was subsequently approved on 2026-10-06;
Phase 2 remains unauthorized.

Day 1 is committed in `838226b`, Day 2 in `8e7bac3`, and Day 3 in `e70ff0d`.
The [product specification](PRODUCT_SPEC.md) and
[implementation plan](IMPLEMENTATION_PLAN.md) record historical V1 intent. Actual
code and the approved [Career-only refactor plan](CAREER_ONLY_REFACTOR_PLAN.md)
govern runtime separation.

Career code remains MIT.

Hosted policy remains Elastic License 2.0; no code moved across that boundary.
No default dependencies or AI capabilities were added.

## Product and architecture

The local `#career` workspace supports onboarding, raw persistence, normalization,
editable profile review, profile-level confirmation, JD analysis, agent-authored
FTS5 searches, evidence inspection, MATCH/PARTIAL/GAP, deterministic coverage,
explicit resume generation, cited review, Markdown export and browser printing.
Saved artifacts survive reload. Unsaved drafts survive polling and navigation,
but not reload. Failed stages retain inputs and earlier successful artifacts.

Career stages use a dedicated runtime's configured client and SQLite connection,
the unchanged `run_loop`, `ToolRegistry` and `Tracer`. The runtime execution lock
also serializes complete provider configuration/replacement transactions.
Each stage has fresh messages,
a dedicated prompt and at most ten iterations. Career runs bypass ordinary chat,
conversational memory, consolidation, retrieval gates, MCP and unrelated tools.
Profile, JD, report and evidence remain untrusted data.

| File | Responsibility |
|---|---|
| `waku/db.py` | Connection mechanics plus separate general/Career initialization |
| `waku/runtime/career_runtime.py` | Settings, lazy client, connection, serialization and owned cleanup |
| `waku/ops/career_dashboard.py` | Explicit Career HTTP launch without general startup |
| `waku/ops/provider_services.py` | Provider-only configuration, rollback and masked readiness |
| `waku/runtime/career.py` | Profile storage, normalization, confirmation and action dispatch |
| `waku/runtime/career_jobs.py` | Extraction, matching, scoring, activity and saved jobs |
| `waku/runtime/career_resumes.py` | Generation gates, claim validation, current drafts and Markdown |
| `waku/tools/career.py` | Scoped submission, FTS5 search and evidence lookup |
| `waku/ops/dashboard.py` | Transitional old shell; Career API delegates to its dedicated runtime |
| `waku/ops/static/js/career.js`, `style.css` | Workspace forms, reports, resume review and print rules |
| `evals/career.py` | Explicitly opt-in real-provider evaluation |
| `evals/fixtures/career_*.json` | Four JDs, varied synthetic profile and review expectations |
| `evals/deterministic/test_career_*.py` | Offline profile, job, resume and whole-journey regressions |

## Database and provenance

Career tables share the existing `state.db`:

- `career_profile`: singleton raw input, normalized JSON, explicit edits,
  confirmation and update timestamp.
- `career_evidence`: stable evidence/source IDs, type, original text, normalized
  JSON, search text and active flag. Singleton ownership is implicit; no `profile_id` exists.
- `career_evidence_fts`: external-content FTS5 over search text with insert,
  update and delete triggers.
- `jobs`: raw JD, extracted title/summary/responsibilities, status, outdated flag,
  coverage, report/evidence snapshots, activity and timestamps.
- `job_requirements`: job-owned atomic requirements, category, importance,
  keywords and verbatim JD excerpts.
- `job_matches`: one assessment per requirement, status, evidence IDs and reason.
- `resumes`: ID, unique job ID, language, structured content/evidence snapshots,
  outdated flag, activity and timestamps. Successful regeneration replaces one
  current draft; no version history exists.

Raw input remains separate from normalization and explicit user corrections.
Evidence IDs are `career-<source_id>` and remain attached to coherent source
records. Removed records become inactive. Unchanged confirmation does not convert
AI wording into user-authored facts. Profile changes invalidate analyses and
resumes; successful reanalysis leaves old drafts outdated until regeneration.

MATCH/PARTIAL need active, inspected evidence. Every substantive resume claim
needs unique inspected references; bullets must cite their own record. Validation
rejects unknown/inactive IDs, extra heading-field proposals and new numeric values.
Python supplies contact details, canonical titles and raw structured heading fields.
Evidence IDs establish traceability, not semantic proof.

Coverage uses required weight 2, preferred weight 1, MATCH 1, PARTIAL 0.5 and GAP 0:
`100 × sum(weight × value) / sum(weight)`, rounded to one decimal. Empty
requirements yield insufficient information and block generation. The UI calls
this JD Requirement Coverage and explicitly excludes hiring/interview probability.

## APIs, tools and tracing

`GET /api/career` returns profile/evidence and saved job/resume artifacts.
`POST /api/career` accepts `save_onboarding`, `normalize`, `save_profile`,
`confirm`, `analyze_job` and `generate_resume`. Hosted policy blocks Career access.

Normalization and extraction expose only `submit_stage_result`. Matching adds
`search_career_evidence` and `get_evidence`; generation exposes only evidence lookup
and submission. Search accepts bounded agent-authored query batches, safely
quotes literal tokens and deduplicates results. Resume generation requires an
explicit action, confirmed profile, completed current analysis and usable requirements.

Day 4 closes failed Career traces with terminal records and records search queries
and result counts in Career Activity. Activity shows tools, evidence IDs, status,
latency and tokens. Traces omit system prompts and assistant prose/reasoning, but
contain factual tool inputs/results. The permanent usage ledger remains unchanged.
Resume headings inherit the resume font stack for CJK fallback. The existing
Markdown blob cleanup timer is registered in the dashboard timer audit.

## Run and evaluation commands

Follow [the Career guide](../career.md) for clone/setup commands, the architecture
diagram and the exact demo. Start a fresh isolated demo without deleting data:

```bash
WAKU_HOME="$(mktemp -d /tmp/waku-career-demo.XXXXXX)" uv run waku career
```

Open `http://localhost:7777/#career`. Configure a provider through the Career setup button if needed.
Use `evals/fixtures/career_profile.json` and the guide's RAG/PyTorch/production-Python
JD to demonstrate MATCH/PARTIAL/GAP, evidence inspection and explicit generation.

```bash
uv pip install -e '.[eval]'
uv run python -m pytest -q evals/deterministic/test_career_*.py
uv run python -m pytest -q evals/deterministic
uv run --with ruff ruff check waku evals scripts hosted
node --check waku/ops/static/js/career.js
uv run python -m evals.career --live --output /tmp/career-evaluation.json
uv run python -m evals.career --live --scenario 'AI Engineer' --language Chinese --inject-jd --output /tmp/career-adversarial.json
```

Live evaluation uses synthetic facts in new temporary runtimes and the existing
provider client. It judges extraction, retrieval, match grounding, gap honesty,
resume grounding/relevance, profile grounding and language separately. A deliberately
false draft checks judge sensitivity to unsupported technology, metrics and fields.
Offline tests use scripted proposals and never claim to measure real-model quality.

## Phase 1 runtime separation on 2026-10-06

`waku career` serves the existing Career forms through a separate HTTP bootstrap.
It starts no general Waku agent, Memory, Session, MCP, graph or gateway services.
`waku dashboard` remains available for rollback; its Career actions also use the
new runtime. The Career pipeline and schema definitions remain unchanged.
The transitional page reuses the existing fork's styles without editing design
copies. Phase 2 must resolve visual-asset rights before product styling changes.

The runtime owns factory-created connections and clients. Injected resources
remain caller-owned. It constructs the model lazily on an AI action, preserves
`get_client` model resolution, and builds replacement resources before swapping.
Failed replacements release candidate resources and restore provider environment
and configuration while retaining the old runtime. Successful replacements close
old owned resources. Server shutdown waits for HTTP workers and closes its owned
runtime. SDK cleanup failures retain exception class names in `cleanup_errors`
and do not reverse a completed swap or prevent connection cleanup.

One runtime lock protects Career actions, its shared connection, complete provider
transactions and shutdown. Provider probes and temporary environment overrides
stay inside that boundary. The old provider facade coordinates an existing Career
runtime and chat runtime during saves. Locks are process-local; users should not
run both applications against the same home concurrently.

Career exposes `GET /api/provider-status`, `GET /api/models` and
`POST /api/providers` alongside its unchanged Career API. Readiness resolves the
same provider/model and scoped credentials as execution, reports masked status,
and makes no provider call. Explicit catalog requests and changed-key/endpoint
saves may make provider calls. The new provider services import no general
integration infrastructure; the old integrations facade retains its API and
health reporting. `Settings`, dotenv precedence, home resolution, provider registry
and catalog/default-pin mechanics remain shared for compatibility.

`connect_career` opens the existing `state.db` with SQLite rows, a 3,000 ms busy
timeout and the appropriate thread setting. It initializes only Career SQL and
never runs general schema migrations. Preservation checks compare all stored
rows, including FTS shadow tables and legacy rows, before and after reopening.
An older chat table retains its original columns. No user runtime data was read,
deleted or migrated during implementation; verification used temporary homes.

Phase 1 verification used scripted clients and synthetic credentials. The focused
Career and shared-runtime checks passed, including the four fixture journeys,
import isolation, client injection, replacement failures, serialization, scoped
credentials, shutdown, profile/job/resume behavior, tracing and database
preservation. The final focused run passed 455 checks with 12 skips.
All 114 Career checks passed. Ruff, both Career JavaScript syntax checks, skill
validation, environment-example validation and `git diff --check` passed.

A broader sweep passed 2,609 checks with 73 skips and one failure in the existing
hosted concurrency assertion
`test_two_simultaneous_requests_at_the_cap_cannot_both_start`. The assertion passed
on an isolated retry; the V1 handoff already records this intermittent failure.
The first broad run also needed a temporary `jq` binary for hosted shell checks;
those checks passed once it was available. No default dependency changed.

The Chromium compatibility journey passed provider setup, synthetic onboarding,
normalization, confirmation, analysis, explicit generation, Markdown download and
reload with zero page errors. The page requested only Career/provider APIs.
Process-local mutations that restored general schema initialization, removed the
execution lock or disabled resource cleanup each made the new regressions fail.
No mutation edited repository files. Real-provider evaluation was not run.

Shared lifecycle limits remain outside Phase 1: stage-local OTel initialization
still uses the global provider API and has no explicit exporter shutdown;
general `Waku.close()` still only closes MCP. The new owner can close SDK adapters
that expose `close()` and leaves injected clients under caller ownership.
General frontend/modules, hosted code and teaching material remain in the repo.
The existing settings object still creates an unused `outbox` directory.
These limits do not require general assembly for the explicit Career launch.
Phase 2 navigation, styling and default-product cutover have not started.

## Verification on 2026-10-02

The full deterministic suite passed 2,585 checks with 73 skips. All 88 Career
checks passed; focused checks also cover print, timer and rulebook contracts.
Ruff, JavaScript syntax, skill validation and `git diff --check` passed.
The full suite needs localhost sockets and `jq` for existing hosted shell tests;
verification used a temporary extracted `jq`, without adding a project dependency.
A process-local mutation removed terminal tracing; all nine failure-trace cases
failed as expected. No mutation changed repository files or user runtime data.
Offline span stubs verify that terminal records flush after the root span closes.

A fresh isolated runtime and scripted model passed the complete Chromium journey:
first visit, adding/removing records, draft preservation, normalization/editing,
confirmation, analysis, three statuses, evidence inspection, explicit generation,
three language selections, both themes, Markdown, print visibility, outdated gates
and reload. The browser recorded zero page errors. Temporary Noto CJK fonts rendered
Chinese/Japanese headings; the real Japanese draft preview/print used Noto Sans CJK JP.
Browser artifacts remain under `/tmp/career-day4-*`.

Real-provider evaluation ran through GLM `glm-5.2`: AI Engineer in Japanese,
Frontend/Full Stack/Technical Support in English, and an injected AI Engineer JD
in Chinese. All eight evaluator dimensions passed on all five runs. Scores were
50.0, 83.3, 80.0, 16.7 and 50.0 respectively. Production PyTorch, Kubernetes and
customer support stayed unsupported. The injected run did not add five years of
PyTorch experience or a 70% SSR metric. Adversarial drafts were flagged as ungrounded.
Saved artifacts are `/tmp/career-day4-live.json`, `career-day4-live-remaining.json`
and `career-day4-live-adversarial.json`. These results cover one provider/model;
model judgments do not guarantee factual correctness or translation quality.
The evaluator uses the same configured model as generation.

## Limits and deferred maintenance

Users must review semantic matches, paraphrases, technologies and translations.
One Japanese output contained a small mixed-language phrase despite the evaluator's
passing language verdict. Language defaults are heuristic; mixed-language/kanji-only
JDs may need an override. FTS5 literal search has limited cross-language recall.
CJK rendering needs installed fonts, and browser defaults control pagination.
OpenTelemetry export and other providers were not independently exercised on Day 4.
An existing hosted concurrency assertion failed in one full run and passed an
isolated retry. Day 4 did not change hosted behavior.

Useful future maintenance includes broader provider/translation checks, additional
adversarial examples and print review on other browsers. No embeddings, scraping,
ATS/application tracking, authentication, SaaS, DOCX, PDF library, resume designer,
multi-agent execution or revision graph was added or authorized.
