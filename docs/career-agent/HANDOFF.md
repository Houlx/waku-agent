# Career Agent handoff

## Status

Days 1–4 are complete. Day 4 was explicitly approved on 2026-10-02 for
stabilization, evaluation, documentation and demo preparation. V1 feature development stops
here. Phase 1 runtime separation was subsequently approved on 2026-10-06;
Phase 2 — Career Product Cutover was separately approved and is implemented.
Phase 3 Batch A is approved and implemented. Career Agent is the sole supported
product. Backend deletion and Batch B have not started.

Day 1 is committed in `838226b`, Day 2 in `8e7bac3`, and Day 3 in `e70ff0d`.
The [product specification](PRODUCT_SPEC.md) and
[implementation plan](IMPLEMENTATION_PLAN.md) record historical V1 intent. Actual
code and the approved [Career-only refactor plan](CAREER_ONLY_REFACTOR_PLAN.md)
govern runtime separation.

Career code remains MIT.

Hosted policy remains Elastic License 2.0; no code moved across that boundary.
No default dependencies or AI capabilities were added.

## Product and architecture

The local Career workspace at `#overview` supports onboarding, raw persistence, normalization,
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
| `waku/ops/static/career/`, `career.html` | Independent Career UI, routes, drafts, requests, Settings and print rules |
| `waku/ops/static/js/career.js`, `style.css` | Retained rollback dashboard workspace |
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
WAKU_HOME="$(mktemp -d /tmp/waku-career-demo.XXXXXX)" uv run waku
```

Open `http://localhost:7777/#overview`. Configure a provider through the Settings page if needed.
Use `evals/fixtures/career_profile.json` and the guide's RAG/PyTorch/production-Python
JD to demonstrate MATCH/PARTIAL/GAP, evidence inspection and explicit generation.

```bash
uv pip install -e '.[eval]'
uv run python -m pytest -q evals/deterministic/test_career_*.py
uv run python -m pytest -q evals/deterministic
uv run --with ruff ruff check waku evals scripts hosted
node --check waku/ops/static/career/render.js
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
At Phase 1 completion, Phase 2 navigation, styling and default-product cutover
had not started. The section below records the subsequent implementation.

## Phase 2 product cutover on 2026-10-06

The approved implementation keeps plain JavaScript and the completed Career
runtime, database schema, coordinators, tools, retrieval, matching, coverage and
resume validation. No AI architecture or licensing boundary changed.

The dedicated shell loads only `career/` assets. `ui.js` owns escaping, requests,
independent primitives and theme behavior. `state.js` separates saved artifacts,
editor drafts and request/provider progress. `router.js` owns addressable hash
routes and stable IDs. `actions.js` owns submissions and exports. `render.js`
owns screens, and `settings.js` owns provider configuration. Bootstrap performs
initial Career/readiness reads and starts no polling or AI action.

Routes are `#overview`, `#profile`, `#jobs`, `#jobs/<job-id>`,
`#jobs/<job-id>/resume` and `#settings`. `#career` redirects to Overview.
Missing jobs and resumes have explicit empty states. Rendering creates no drafts
and submits no work. Raw/profile/JD/language drafts stay in memory across
navigation; reload restores saved artifacts only. A navigation counter prevents
late responses from moving users away from their chosen screen. Busy requests
block duplicates and editor mutations while leaving navigation available.
Failures retain inputs and refresh persisted artifacts, including failed jobs.

Profile groups use existing source types and IDs. Job summaries derive status
counts from saved requirements. Reports retain evidence/source disclosures and
current/stale gates. Resume language changes require explicit generation.
Markdown cleanup, resume-only print isolation and CJK system-font fallback remain.
The independent CSS uses no protected design styles, mark, favicon or bundled
font files. About and the root README retain MIT upstream attribution.

After browser acceptance passed, `waku`, `waku career`, `make run` and
`make dashboard` became Career launches at `/#overview`. `waku dashboard` /
`make legacy-dashboard` retain the old dashboard; `waku chat` / `make legacy-chat`
retain terminal chat. Old backend modules, assets, hosted code and teaching
material remain in place. The Career HTTP handler serves an explicit allowlist
of its shell and eight assets; old shell/static pages return JSON 404 responses.

`test_career_browser.py` launches real Chromium against a temporary Career server
and SQLite home with scripted initial/replacement clients. Provider writes are
explicitly redirected to the temporary home's `.env`, and provider credentials
are removed from the test environment. `career_browser.cjs` covers onboarding,
Settings failure/recovery, profile edits/confirmation, all routes/history,
draft retention, delayed actions, duplicate prevention, failed reanalysis with
retained reports, all statuses/evidence, three explicit language generations,
Markdown, themes, print isolation, CJK heading fallback, stale gates and reload.
It rejects page errors and non-Career API/static requests. The browser dependency
is test-only and opt-in; setup lives in the Career guide. Career-specific asset
checks inspect the actual loaded scripts, handlers, network routes and timer.

All 122 Career checks passed with the committed Chromium journey enabled.
The final remaining broad suite passed 2,618 checks with 74 skips and one
explicit deselection. The deselected hosted concurrency assertion failed in the
preceding full run and on isolated retry, matching the known handoff failure.
The preceding full run also exposed the old README-logo assertion; that contract
now checks independent Career identity and attribution while retaining the
unchanged mark-geometry/ink checks. Hosted code was not changed.

Ruff, JavaScript syntax, loaded-asset/handler/network/timer contracts, shared
static/design/rulebook checks, skill validation, environment-example validation
and `git diff --check` passed. Wheel and source archive builds passed; the wheel
was installed into an isolated target, served every approved Career asset and
passed default launch/owned shutdown without importing `waku.app`. Final packaged
Career files matched repository bytes. A browser-only intercepted mutation
removed the late-response navigation guard and made the regression fail at its
Overview-route assertion. No mutation changed repository implementation files.

New files are the eight `waku/ops/static/career/` assets,
`evals/deterministic/test_career_assets.py`, `test_career_browser.py`, and
`evals/fixtures/career_browser.cjs` / `career_state.cjs`. Modified product files
are `career.html`, `career_dashboard.py`, `waku/__main__.py` and `Makefile`.
The Career HTTP and README brand contracts changed with them. Current README,
Career guide, frontend map, architecture, status, retained getting-started guide,
handoff and inspection status now describe the cutover. Historical V1 Product
Spec and Implementation Plan, the refactor plan, runtime/schema/pipeline code,
old frontend assets and protected design copies remain unchanged.

An early browser harness failed to redirect provider writes and persisted
`WAKU_MODEL=offline` in the ignored checkout `.env`. The original value, including
whether the variable was absent, cannot be recovered reliably: the file has no
entry in HEAD, the Phase 1 checkpoint, Git history or a stash, and no checkout
configuration backup was found. The inherited process has no model override,
and the resolved runtime home has no `.env`; neither proves the prior checkout
state. The Phase 1 browser dotenv belongs to a separate test runtime and cannot
establish the user's configuration. The commented example override does not
establish it either. No restoration or model selection was performed.

The provider-save path could also have persisted its effective endpoint when a
scoped endpoint was previously absent. The checkout currently contains
`ZHIPU_BASE_URL=https://api.z.ai/api/anthropic`; without an earlier snapshot,
that field's prior presence cannot be established. The harness omitted credentials
and did not switch providers; those fields were not submitted as changes.
The test process's environment and runtime replacements were transient.

The corrected browser harness redirects provider writes to the temporary home,
clears provider credentials and the inherited model from its test environment,
and now verifies both actual temporary model persistence and byte-for-byte
preservation of the checkout dotenv file. The minimal rerun passed one Chromium
journey; focused lint and diff checks passed. The checkout `.env` remains unchanged
from the start of the recovery investigation.
Real-provider evaluation was not run. System fonts and browser pagination remain
platform-dependent. Physical retirement requires separate Phase 3 approval;
shared modules, the rollback shell and package/configuration cleanup still await
that phase. Career needs no old frontend script or protected visual asset.

## Phase 3 Batch A on 2026-10-06

Batch A closes the general public CLI surface and the remaining live Career
evaluation database coupling. Default `waku` and explicit `waku career` still
launch the unchanged Career server. Help accepts `--help`, `-h` and their
`career` forms without startup. Every other invocation exits with status 1,
prints a supported-command hint and imports no product runtime. Extra arguments
to `career` no longer silently launch Career.

The removed commands are `dashboard`, `chat`, `connections`, `connect`, `voice`,
`telegram`, `discord`, `whatsapp`, `brief`, `gather`, `mcp` and all `skill`
installation/export dispatch. Make removes `legacy-dashboard`, `legacy-chat`,
`voice`, `telegram`, `discord`, `whatsapp`, `brief`, `gather`, `shootout` and
`shootout-coding`. Make retains `run` and `dashboard` for Career, `trace` for
optional generic tracing, and `eval`, `lint`, `eval-judge` and `gate` for the
existing verification infrastructure. The general judge/gate implementation
awaits later retirement and remains separate from Career live evaluation.

`evals/career.py` now opens each temporary scenario with `connect_career`.
Its scenarios, client configuration, judge, opt-in gate, injection option,
language selection, result writing and connection cleanup remain unchanged.
Two new offline command-runner regressions exercise all four scenarios with
scripted clients, both plain and injected JDs, Chinese resumes, separate homes,
Career tables/FTS retrieval, SQLite row/busy-timeout settings and closed connections.
They forbid general migrations and verify that the configured original home
remains absent. Production runtime, schema, stages, provider behavior and UI
remain unchanged.

The positive legacy dispatch tests retire; the retained backend keeps its own
connector/dashboard tests. The skill export destination guarantee now calls
the retained exporter directly. Console encoding still exercises real CLI output.
Negative dispatch checks cover every removed family, malformed arguments, no
runtime imports and no home creation. Make dry-run regressions verify both Career
shortcuts and the absence of all ten retired shortcuts.

Modified implementation/configuration files are `waku/__main__.py`,
`evals/career.py`, `Makefile` and the CLI comment in `pyproject.toml`.
Modified deterministic evals are `test_career_acceptance.py`,
`test_career_http.py`, `test_connect_command.py`, `test_console_encoding.py`,
`test_skill_export.py` and `test_waku_memory_connect.py`.
Modified documentation is `README.md`, `AGENTS.md`, `docs/architecture.md`,
`docs/career.md`, `docs/commands.md`, `docs/getting-started.md`, `docs/status.md`
and this handoff. The old getting-started instructions are explicitly historical;
full documentation cleanup remains deferred.

Verification passed the full deterministic suite with Chromium enabled:
2,641 passed and 73 skipped, with no deselections. This run includes all Career,
provider/model, home/dotenv, HTTP/static security, packaging, hosted boundary,
route/image and remaining hosted contracts. The known hosted concurrency test
passed this run. Twelve subsequently added Make dry-run checks also passed with
a test-only Make binary extracted under `/tmp`. The final focused run passed
201 Career, command and rulebook checks, including all 158 Career tests with
Chromium enabled. The final handoff-only rulebook rerun passed 17 checks.

Wheel and source archive builds passed. The wheel installed into an isolated
`/tmp` target. Both default and explicit Career launches served the shell and
eight assets with bytes matching the checkout, avoided general app/dashboard
imports, constructed no provider client and closed owned connections. The
installed command's help and all removed command families passed negative checks.
Ruff, all seven Career JavaScript syntax checks and `git diff --check` passed.
The initial restricted socket checks failed because of sandbox permissions;
the subsequent socket-enabled suite passed. No real-provider evaluation ran.

Process-local mutations restored the general database connector and permissive
`career` argument dispatch. The corresponding new regressions failed in both
cases. No mutation changed repository files or user runtime data.

The audited command inventory and evaluation coupling matched actual code.
The command reference additionally still described default `waku` as terminal
chat; Batch A corrects it. The Makefile also had duplicate obsolete PHONY lists;
Batch A consolidates them. Pre-Batch-A HEAD is `ebe337f`; reverting the Batch A
changes restores the prior code without a schema/configuration migration.

Batch B must resolve hosted's direct `waku.ops.dashboard` dependency before
removing general assembly, gateways and static assets. The approved direction
is eventual general hosted retirement, not Career hosting. General deterministic
fixtures/helpers, the procedural skill validator and wheel/hosted skill packaging,
plus teaching references, remain consumers for later closure. Git history is
sufficient for historical teaching recovery. Stable Career provider/catalog,
pricing, tracing, configuration, loop, registry and database infrastructure stays.
Batch A deletes no backend implementation, assets, skills, hosted, examples or lab
material. It migrates or deletes no user runtime data and changes no credentials.
Batch B has not started.

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
