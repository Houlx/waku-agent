# Career Agent handoff

## Status

Days 1–4 are complete. Day 4 was explicitly approved on 2026-10-02 for
stabilization, evaluation, documentation and demo preparation. V1 feature development stops
here. Phase 1 runtime separation was subsequently approved on 2026-10-06;
Phase 2 — Career Product Cutover was separately approved and is implemented.
Phase 3 Batch A is approved and implemented. Career Agent is the sole supported
product. Phase 3 Batch B1 and Batch B2 consumer closure are implemented.
Batch C1 feature backend deletion is implemented. C2 and D have not started.

Day 1 is committed in `838226b`, Day 2 in `8e7bac3`, and Day 3 in `e70ff0d`.
The [product specification](PRODUCT_SPEC.md) and
[implementation plan](IMPLEMENTATION_PLAN.md) record historical V1 intent. Actual
code and the approved [Career-only refactor plan](CAREER_ONLY_REFACTOR_PLAN.md)
govern runtime separation.

Career code remains MIT.

Batch B1 retires the Elastic License 2.0 hosted implementation; no code moved
across that boundary. Retained brand assets and fonts keep their separate notices.
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
| `waku/db.py` | Connection mechanics and Career initialization; dormant legacy data stays untouched |
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
`confirm`, `analyze_job` and `generate_resume`. Batch B1 removes the old hosted policy.

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
uv run --with ruff ruff check waku evals scripts
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

## Phase 3 Batch B1 consumer closure on 2026-10-06

Batch B1 retires hosted and upstream-only teaching consumers. It does not delete
any general backend implementation or change Career runtime, server, UI, schema,
pipeline, FTS5, matching, scoring, provenance or resume behavior. Batch B2 and
Batch C remain unstarted. Pre-B1 HEAD is `2146a06`; reverting this batch restores
its source consumers without touching runtime data or stored configuration.

### Retired surfaces

- All 93 tracked files under `hosted/` are removed: core policy/quota/provisioning,
  gateway/auth/control store, proxy/metering, spawner, tenant templates, image
  builders/Dockerfiles/seccomp, deployment/firewall/network/backup scripts,
  sign-in assets and the hosted operator guide/license.
- All 48 tracked hosted eval/helper files under `evals/deterministic/hosted/`
  and `evals/hosted_docker/` are removed. Their route contract, Docker context,
  container isolation, disk-limit and deployment checks no longer apply.
- `examples/` is removed, including the conversational Memory agent and MCP
  configuration. `lab/` is removed, including Kimi K3, pi-agent/Pokedex,
  one-memory-every-agent, memory-native, Jev experiments and the topic template.
- `scripts/whiteboard/`, `docs/whiteboards/`, `docs/architecture.html` and
  `docs/architecture-whiteboard.png` are removed. The repo-local
  `.claude/skills/excalidraw/` authoring helper is removed because it requires
  the deleted board toolkit. It is not a bundled product skill under `skills/`.
- Upstream-only tour, roadmap, loop-vs-graph, graph design, Memory backend
  playbook and benchmark/video walkthroughs are removed. Architecture and
  getting-started now describe retained Career/shared-runtime entrypoints.
  The integration document records retirement while remaining a valid target
  for the retained MCP CLI's help text. Evals retain shared tracing instructions.

### CI, packaging and licenses

The hosted Docker workflow is removed. Validate/release install `[dev]` instead
of `[dev,hosted]`; Make and documentation lint commands omit `hosted`. The
`[hosted]` extra is removed after checking retained imports for aiohttp, jwt and
yarl. No other default dependency or extra changes. Lock refresh changes only
hosted extra metadata and leaves all 304 resolved packages pinned: other extras
still need transitive aiohttp/PyJWT dependencies.

The old hosted boundary suite is removed; its generally useful build enumeration
moves to `test_distribution_boundary.py`. The replacement checks wheel/sdist
members, Career assets, runtime-data exclusion and retained-runtime imports of
hosted. Rulebook checks no longer require hosted guides, lab topics or teaching
trees. They still reject product/eval imports from restored teaching trees.
Source exclusions retain retired-tree guards; obsolete Git-ignore entries vanish.
Skill validation, bundled-skill packaging, environment generation, provider,
security, brand/design, version and deterministic checks remain active.

No EL2 implementation remains in the working tree or distributions, and none is
copied into MIT Career code. Hosted license/distribution references are removed.
`LICENSE` preserves Sean Chen's upstream MIT copyright. `LICENSE-BRAND` still
covers the retained Waku design system, mark, names and `docs/brand/`; only removed
hosted asset entries are dropped. All three retained font OFL notices remain.
The package expression stays `MIT AND OFL-1.1 AND LicenseRef-Waku-Brand`.
Removed boards' CC BY-NC-SA material is not republished as Career assets.
Historical Career plans/audits retain the license decisions they recorded.

The hidden `waku-platform` provider row and its scoped credential/catalog tests
remain to honor the provider compatibility constraint. Only its dead hosted-guide
key URL points to retained provider documentation instead; credentials, endpoint,
model resolution and visibility behavior are unchanged. It supplies no hosting.

### Retained material and remaining consumers

No examples, lab topics or whiteboards remain. The MCP server under
`evals/fixtures/` remains because retained MCP transport tests execute it; its
header no longer advertises the removed teaching configuration. Career documents,
V1 Product Spec/Implementation Plan, refactor plans, inspections and retirement
audit remain. Provider registry, configuration, runtime and tracing documentation
remain useful to retained infrastructure. Brand files, fonts/notices and protected
Waku design copies remain unchanged because the old dashboard assets still exist.

Backend deletion is still blocked by the procedural skill validator's import of
`waku.memory.procedural.loader._parse`, bundled `skills/` and wheel force-include,
skill loader/install/export/trigger/packaging tests, environment generator/CI
imports of `waku.integrations`, the general release gate and judge suite,
`evals.helpers.make_waku` and general deterministic fixtures, and mixed
provider/static/tracing tests. Retained general dashboard, tools, MCP, graph,
gateways, integrations and arenas still consume each other; Batch C must close
those imports with their removal. Shared provider/catalog/pricing/loop/registry,
config/database and tracing guarantees must survive that work.

Batch B2 should retire bundled product skills and their force-include coherently,
resolve validator/CI and packaging contracts that require procedural Memory,
remove or split skill-only evals and contributor instructions, and preserve
applicable community attribution. It must not touch user-installed skills.
General environment-generator/facade and mixed-suite closure still need assigned
work before Batch C deletes their implementations. B1 does not do that work.

### Verification and audit discrepancies

The full retained deterministic suite with the real scripted Chromium journey
passes: 1,145 passed, 75 skipped, with no deselections. Twelve Career Make contracts skip when Make is absent;
a subsequent focused run uses a temporary extracted Make binary and passes all
158 Career checks with Chromium enabled and no skips. This covers provider/model, runtime ownership/replacement, database
preservation/FTS5, HTTP/static security, browser routes/state, and applicable
packaging/import/license/design guards. Ruff passes across `waku evals scripts`;
all 25 retained JavaScript/ Career fixture files pass Node syntax checks. All six
bundled skills validate; the generated environment example matches its registry.
Lock consistency and `git diff --check` pass.

Wheel and sdist builds pass, including wheel rebuild from the extracted sdist.
Isolated installs of the direct wheel and the sdist-rebuilt wheel pass default
and explicit Career launch, all nine
shell/static assets matching repository bytes, state API, static/general-route
rejection, lazy provider initialization, absence of general app/dashboard imports
and owned connection shutdown. Both archives omit retired consumers and retain
MIT/brand/OFL notices and the existing license expression. Every member of the
sdist-rebuilt wheel matches the direct wheel byte for byte. All current
documentation file links resolve; historical Career plans remain unchanged.

Temporary-project mutations force-include a retired hosted path and synthetic
`.env`, and add a runtime import of hosted; the three new guards fail respectively.
No mutation changes repository implementation or real runtime data. The first
suite attempt lacked localhost socket permission and was stopped; the complete
socket-enabled run above passes. Package-harness corrections fixed an assumption
that a closed runtime retained its connection reference. No live/paid evaluation,
Docker check, demo reset, schema migration or credential write was performed.

The audit deferred hosted and recommended pinned upstream/teaching archives.
The new lifecycle approval resolves both in favor of deletion with Git history,
so B1 removes them instead. The audit grouped backend retirement as Batch B;
current approved sequencing is B1 consumer closure, B2 skills, then C backend.
The actual tree also contains a board-toolkit-dependent repo-local Excalidraw
helper and the hidden provider row's hosted-guide URL; both required closure.
The MCP test fixture and platform provider contracts remain real test/shared
consumers, so they are preserved. The status file's old claim that hosted did
not exist is removed. No repository-wide retirement audit was repeated.

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


## Phase 3 Batch B2 consumer closure on 2026-10-06

Batch B2 retires bundled general-product skills and their build/evaluation consumers.
Career runtime, HTTP/UI, schema, FTS5, extraction, matching, coverage, provenance,
resume generation and provider behavior are unchanged. Batch C has not started.
The general backend remains physically present. This batch performs no runtime
home cleanup, user-skill deletion, credential update or real `.env` write.

### Bundled skills and packaging

The six retired skills are `schedule-meeting`, `weekly-brief`, `waku-memory`,
`community/meeting-prep`, `community/interview-prep` and
`community/da-anomaly-analysis`. The bundled template and community README also
retire. Career loads none of them. Git history preserves the content and its
community attribution; no legacy archive is added. Runtime-home skills remain
user data, and the general backend's loader/installer/exporter implementations
remain for Batch C.

`scripts/validate_skills.py` and its procedural-parser import retire. Bundled
trigger, encoding, install/export and tracked-content shipping evals retire.
The wheel force-include disappears. Explicit wheel/sdist exclusions prevent a
local restoration of repository or package skills from shipping. Build enumeration
continues to check Career assets, provider/config files, retired consumers and
runtime-data exclusion. A temporary-project regression restores both skill trees
and verifies their exclusion through actual Hatchling file enumeration.

### Environment template and CI

The generator renders the complete `.env.example` from `waku/providers.toml`
and a small Career/shared-configuration list. It imports no Waku module, loads no
user configuration and creates no runtime home. Public provider keys and scoped
endpoints/model overrides follow registry rows automatically. Hidden provider
rows remain omitted from the committed public template, even when configured;
their runtime resolution and credentials remain compatible.

The template retains `WAKU_PROVIDER`, global key/endpoint/model overrides,
`WAKU_SMALL_MODEL`, `WAKU_HOME`, iteration/token bounds, LLM timeout, OTel endpoint,
Career bind/port and the compatible `PORT` fallback. General memory, calendar,
gateway, MCP and arena configuration no longer belongs to this Career template.
Their runtime environment reads remain unchanged pending backend retirement.

CI removes bundled-skill validation and checks the Career/provider template.
The historical `skills-and-evals` job ID remains for branch-protection compatibility.
Contributor, rulebook, provider, command, architecture, status and eval instructions
now describe the retained contracts and the offline gate. Repository authoring
skills under `.claude/` are separate from the retired bundled product skills.

### Evaluation helpers and release gate

`evals.helpers.make_waku` retires after its callers are closed. General history,
session resume, turn metadata and tool-trigger assembly suites retire. Mixed
delegate, gateway, calendar, GitHub and triage suites retain their independent
component tests while dropping general Waku construction. Scripted block/response
helpers, provider key detection, temporary-home isolation, Career journeys and
synthetic shared-component tests remain.

New direct `run_loop` regressions preserve plain-answer completion, tool execution
and recorded results, and bounded runaway iterations with a minimal ToolRegistry.
No general Memory, Session or app construction is needed for these guarantees.

General response/retrieval judge suites and their DeepEval adapter retire.
The standalone general `scripts/shootout.py` evaluator and its duplicate scorer/
report tests retire; existing `test_scoring.py` continues to cover the shared
scorer. `make eval-judge` disappears. `make gate` executes only the deterministic
suite and forces `WAKU_RUN_LIVE_EVALS=0` in its subprocess. Existing local report
fields remain compatible, with the judge recorded as "not run". Gate failure still
returns a failing exit status. Explicit Career live evaluation remains separate.

### Dependencies

The `[eval]` extra keeps pytest and drops DeepEval. The offline lock refresh removes
DeepEval and 13 exclusive transitive packages: execnet, nest-asyncio, prompt-toolkit,
pyfiglet, pytest-asyncio, pytest-repeat, pytest-rerunfailures, pytest-xdist,
questionary, sentry-sdk, tabulate, wcwidth and wheel. All 290 retained package pins
remain unchanged. The refresh uses the installed build backend and temporary uv
cache; it does not require a default dependency change.

Anthropic, OpenAI, python-dotenv and rich remain because retained consumers still
use them. Tracing and all general gateway/calendar/store/arena/MCP extras remain
until their last backend/component-test consumers retire in Batch C.

### Verification

The final full deterministic run passes **1,063 tests with 52 skips**, no
failures or deselections. Chromium is enabled with synthetic clients; temporary
Make and browser dependencies under `/tmp` enable the existing Career regression.
The suite preserves all Career checks, provider/model behavior, runtime ownership,
configuration/home resolution, FTS5/database preservation, generic loop/registry,
HTTP/static security, assets, documentation links and license/design contracts.
No paid or live model evaluation runs.

Ruff, all 25 retained JavaScript/fixture syntax checks, environment-template
validation, offline lock consistency and `git diff --check` pass. Direct wheel,
sdist and wheel rebuild from extracted sdist pass. Every rebuilt wheel member
matches the direct wheel byte for byte. Isolated installations of both wheels
pass default and explicit Career startup, all nine shell/static assets against
repository bytes, state API, rejected general/static routes, lazy provider
initialization, absence of app/general-dashboard imports and owned shutdown.
Both archives retain MIT, brand and all three OFL notices and omit bundled skills.

Removing skill exclusions in a temporary project makes the restored-content
packaging regression fail. Removing forced offline mode from an in-memory gate
function makes its live-probe regression fail. The template regression also
rejects a removed home variable and verifies repair touches only the requested
example, preserving a separate user-owned dotenv file. No mutation changes
repository implementation or user runtime files.

The initial restricted-socket run cannot exercise local HTTP. Socket-enabled
verification resolves that limitation. Its first full run finds a mixed memory
check reading the retired `waku-memory` skill; that reference is removed while
its retained general-tool documentation checks remain. Subsequent full runs pass.

### Remaining consumers and audit discrepancies

Batch C must still close imports among app, Session, Memory, general tools,
MCP, gateways, graph, integration/connect infrastructure, old dashboard/browser
and arenas. Independent general component evals remain with those implementations;
`test_memory_arena.py` still imports app for synthetic arena wiring. General
provider/settings facade tests and old frontend/design contracts need careful
separation from retained provider services and Career security checks.

General `evals/dataset.jsonl`, `coding.jsonl` and `memory_arena.json` remain because
retained scoring/coding/memory arenas and their component evals consume them.
The MCP demo fixture remains required by transport tests. General `ops/judge.py`,
scoring and arena modules still have consumers and remain physically present.
The old integrations environment renderer remains inside the backend but no
longer supplies the repository template; old installer template hints remain
part of the unsupported backend until its deletion. Shared provider/catalog/
pricing, config/database, tracing, loop and ToolRegistry must survive Batch C.

The audit's bundled-skill, validator, wheel, generator, helper and DeepEval coupling
matches actual code. Its scoring-dataset and general judge-module candidates
cannot be deleted in B2 because arena consumers remain. B1 has already removed
the hosted Docker skill consumer. Additional closure found in B2 includes the
standalone shootout script and the mixed fact-mirror skill reference. The hidden
provider template guarantee is retargeted to the new generator rather than lost.
No full repository retirement audit is repeated, and no Batch C work begins.

### Changed files

The following inventory includes additions, edits and deletions for this batch.
Retired paths appear as code rather than links because they no longer exist.

- `.env.example`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/workflows/validate-skills.yml`
- `AGENTS.md`
- `CONTRIBUTING.md`
- `Makefile`
- `README.md`
- `docs/architecture.md`
- `docs/career-agent/HANDOFF.md`
- `docs/commands.md`
- `docs/context/conventions.md`
- `docs/context/writing-rules.md`
- `docs/evals.md`
- `docs/providers-registry.md`
- `docs/status.md`
- `evals/deterministic/test_all_history.py`
- `evals/deterministic/test_consolidation.py`
- `evals/deterministic/test_delegate.py`
- `evals/deterministic/test_distribution_boundary.py`
- `evals/deterministic/test_env_example.py`
- `evals/deterministic/test_fact_mirror.py`
- `evals/deterministic/test_gateway_runner.py`
- `evals/deterministic/test_gh_tool.py`
- `evals/deterministic/test_google_calendar.py`
- `evals/deterministic/test_history_window.py`
- `evals/deterministic/test_loop_contract.py`
- `evals/deterministic/test_models.py`
- `evals/deterministic/test_only_tracked_skills_ship.py`
- `evals/deterministic/test_packaging.py`
- `evals/deterministic/test_platform_provider.py`
- `evals/deterministic/test_release_gate.py`
- `evals/deterministic/test_retrieval_gate.py`
- `evals/deterministic/test_scoring.py`
- `evals/deterministic/test_session_resume.py`
- `evals/deterministic/test_session_rotation.py`
- `evals/deterministic/test_shootout.py`
- `evals/deterministic/test_skill_encoding.py`
- `evals/deterministic/test_skill_export.py`
- `evals/deterministic/test_skill_triggers.py`
- `evals/deterministic/test_tool_trigger.py`
- `evals/deterministic/test_triage_workflow.py`
- `evals/deterministic/test_turn_meta.py`
- `evals/helpers.py`
- `evals/judge/anthropic_judge.py`
- `evals/judge/test_response_quality.py`
- `evals/judge/test_retrieval_gate_accuracy.py`
- `pyproject.toml`
- `scripts/generate_env_example.py`
- `scripts/shootout.py`
- `scripts/validate_skills.py`
- `skills/TEMPLATE.md`
- `skills/community/README.md`
- `skills/community/da-anomaly-analysis/SKILL.md`
- `skills/community/interview-prep/SKILL.md`
- `skills/community/meeting-prep/SKILL.md`
- `skills/schedule-meeting/SKILL.md`
- `skills/waku-memory/SKILL.md`
- `skills/weekly-brief/SKILL.md`
- `uv.lock`
- `waku/ops/README.md`
- `waku/ops/pricing.py`
- `waku/ops/release_gate.py`
- `waku/ops/scoring.py`

## Phase 3 Batch C1 feature retirement on 2026-10-06

Batch C1 retires the general feature backend from Batch B2 checkpoint `bd776cb`.
CareerRuntime, Career coordinators/tools, the Career HTTP/UI, provider services,
model adapters, run_loop, ToolRegistry and CAREER_SCHEMA remain byte-for-byte
unchanged. Only test fixtures and dependency/facade closure change their consumers.
C2 and D have not started. All changes remain uncommitted for review.

### Removed subsystems and data boundary

C1 removes conversational Session, Memory, consolidation/retrieval/slot gates,
semantic and episodic stores, procedural memory and general SOUL/personality
execution. C1 removes calendar/Google/Apple, messages, notes, search, GitHub,
workspace, memory-admin and experimental/delegation tools, plus their registry
factory and environment helpers. The tools initializer now loads no product tools.

C1 removes MCP client/CLI/OAuth/Memory bridge and their demo server fixture. C1
removes gateway workers/supervisor, Telegram, Discord, WhatsApp, voice/wake-word,
webhook behavior and dashboard transcription. C1 removes graph execution/nodes,
gather/triage/brief and graph command discovery. C1 removes model/memory/judgment
arenas, comparison history, coding eval, general judges/scoring and their datasets.
The general demo reset and arena cleaner scripts retire with their final consumers.

General schema creation/migration retires from db.py. Its transitional connect
function opens existing data without initialization; connect_career still initializes
only the unchanged Career SQL. A small test-only `evals/fixtures/legacy.sql` provides
pre-Career calendar/facts/episodes/chat and FTS structures for preservation checks.
No runtime data, legacy DB tables, chat logs, Memory/SOUL files, installed skills,
configuration, integration credentials, traces or usage ledger are deleted or migrated.

Preservation evals compare all legacy rows and FTS shadow tables before/after startup,
query legacy facts/episodes FTS, compare dormant file bytes, preserve older chat columns,
and retain the existing full Career provenance/artifact/FTS reopening check.
Verification uses temporary homes and synthetic credentials; no paid/live evaluation runs.

### Mixed tests and retained contracts

- Career profile/jobs/resumes/acceptance fixtures now use connect_career. Assertions
  require absent general tables rather than empty tables created by retired code.
  Stage-local tool allowlists, grounding, provenance, coverage and full journeys remain.
- Career runtime preservation uses the test-only legacy SQL. Its fresh-interpreter
  import isolation and complete Career journey still reject general imports.
- `test_loop_contract.py` adds direct multi-tool/call-ID and observer checks that
  formerly passed through graph nodes. `test_tool_registry.py` tests schemas,
  unknown tools, argument/handler errors, recovery and progress observers with
  synthetic tools. No general implementation is retained to serve these tests.
- `test_model_errors.py` retains stream refusal/fallback and error-text behavior;
  graph-specific assertions retire. Adoption, regional endpoint saves, pinned
  defaults and provider switching now call provider_services directly.
  `test_session_rotation.py` replaces a vacuous facade test with actual persistence
  and resolved-model assertions. Its filename remains historical.
- `test_integrations.py` retains provider masking, registry and OTel probe checks;
  calendar/Apple/Notion/search-specific assertions retire. Home/dotenv guarantees
  remain while MCP/demo reset assertions retire from the mixed home file.
- The old dashboard route file retains the model catalog response check. New
  `test_c1_retirement.py` verifies retired modules/extras, inert assembly, dormant
  data preservation, retired-route 404s and retained SQL/static/path confinement.
- Trace UTF-8, config, provider adapters/registry, HTTP security, distribution,
  license, design/brand and retained static asset contracts remain. Dormant
  general-toggle facade checks and old static checks remain for C2 closure.

### Dependencies

C1 removes the exclusive extras `telegram`, `discord`, `whatsapp`, `gcal`, `voice`,
`voice-neural`, `supabase`, `arena`, `notion` and `mcp`. The remaining extras are
`eval`, `dev` and `tracing`. Anthropic/OpenAI clients, dotenv and rich remain unchanged.
Provider catalogs, optional OTel/Phoenix and build/eval tooling remain supported.

The resolver regenerates uv.lock and removes 135 unreachable packages. It adds
no package and changes no retained package version. No transitive entry is pruned
manually. Offline resolution initially lacks cached metadata; successful resolution
uses the package index. Root project/lock extra metadata agrees.

### Verification

The final release gate passes 605 deterministic tests with 13 skips, including
146 Career checks and the opt-in Chromium journey. Twelve Career Make dry-run
checks skip because make is unavailable. One live provider probe stays disabled;
no paid evaluation runs.
The environment lacks make, so verification runs its exact gate target command,
`.venv/bin/python -m waku.ops.release_gate`, with a new temporary WAKU_HOME. The gate
forces live provider probes off and records `judge: not run`.

Ruff, environment-example validation, every current Career/old-dashboard JavaScript
syntax check, rulebook/document links, distribution/license/design checks and
`git diff --check` pass. Wheel and source archive builds pass. The source archive
rebuilds a wheel. Isolated installations of both wheels pass default and explicit
Career launches, all nine shell/static assets against repository bytes, Career state,
rejected general/static routes, lazy client initialization and owned shutdown.
Both wheels retain MIT, brand and all three OFL notices, and omit retired feature
modules. Installed smoke checks assert that app and old dashboard never import.

Four in-memory mutations disable tool execution, suppress loop observers, widen
the iteration bound or rewrite a legacy Memory row. Each regression rejects its
mutation. No mutation edits implementation files or user data.

The interruption recovery compares staged/unstaged/new/deleted paths against B2;
no changes are staged. Thirty focused checks pass before implementation resumes.
The last pre-interruption full run has 604 passes, 13 skips and one incorrect test
expectation for Gemini's secondary model. The expectation is already corrected in
the recovered tree. The installed smoke harness initially checks a runtime's cleared
connection attribute; the corrected harness retains the owned connection reference
and verifies it is closed. These are verification fixes, not Career behavior changes.

### Exact remaining general modules and consumers for C2

| Module | Remaining production consumer | Remaining eval consumers |
|---|---|---|
| `waku/app.py` | None; Waku constructor refuses before touching data | `test_c1_retirement.py` |
| `waku/ops/dashboard.py` | Direct module launch only; old static shell, provider/debug routes and Career delegates remain | Career profile/jobs/resumes facade checks; `test_c1_retirement.py`, `test_dashboard_bind.py`, `test_design_system.py`, `test_trace_encoding.py` |
| `waku/ops/browser_agent.py` | `waku/integrations.py` uses current/rebuild and the provider singleton seam | `test_c1_retirement.py`, `test_career_runtime.py` |
| `waku/integrations.py` | Old dashboard uses provider/OTel registry, masked health and apply operations | `test_career_runtime.py`, `test_connections_cli.py`, `test_integrations.py`, `test_platform_provider.py`, `test_provider_base_urls.py`, `test_provider_disabled.py`, `test_static_assets.py` |
| `waku/connect.py` | None; connector table is empty and calls report retirement | None |
| `waku/ops/commands.py` | None; discovery is empty and no runner imports occur | `test_c1_retirement.py` |
| `waku/ops/settings_api.py` | Old dashboard uses masked provider display, pin actions and dormant toggle saves | `test_experimental_toggle.py`, `test_graph_flag.py`, `test_pinned_models.py`, `test_platform_provider.py`, `test_provider_disabled.py` |

The old shell still ships `static/index.html`, `static/style.css`, `static/js/`,
logos/mark and protected design/font assets. Its retired feature controls are
unsupported. C2 must retire that shell and close its static, design, brand and
font-license consumers. Protected copied design files remain unchanged.

The transitional db.connect has no retained callsites. Config retains dormant
legacy dataclass fields, and ensure_home still creates the unused outbox folder.
The settings facade retains general toggle writes. These are C2/D closure items;
C1 does not simplify configuration/provider semantics. Pricing retains catalog
remember_price, price tables and aggregation utilities. `test_providers.py` still
checks price/cutoff contracts. C2/D must prove remaining
consumer closure before deleting shared price/default-pin support. The generic
trace viewer and retained debugging guarantees remain shared infrastructure.

### Scope closure and audit discrepancies

No blocker prevents C1 completion. Keeping the C2 files importable requires
removing their eager/feature imports, general construction bodies and feature
routes. The old dashboard therefore loses feature handlers and gateway startup;
its shell, HTTP server, provider facades and generic debugging remain. App and
browser-agent construction refuse explicitly. Connect and command facades become
inert. Integrations sheds feature registry rows/probes and gateway callbacks, but
retains provider/OTel behavior. This closes actual dependencies without a new facade
architecture or Career feature. Final facade/asset removal remains C2.

The audit's feature dependency inventory matches the deletion set after A/B
consumer closure. Additional test-only couplings are general DB initialization
and build_registry inside Career fixtures, the vacuous provider-switch assertion,
and MCP/demo reset assertions mixed with home tests. The old dashboard's eager
arena import and integrations' eager Notion normalization require transition edits.
General schema creation retires to a test fixture rather than dropping legacy tables.
No repository-wide audit is repeated. B1/B2 already closed hosted, teaching,
bundled-skill and release-judge consumers; their historical audit descriptions
remain historical. C1 does not begin C2 or D.

### Removed file inventory

The following 109 tracked files retire in C1. Deleted paths use code formatting
because they no longer exist. The entire memory, gateway and graph directories retire.

- `evals/coding.jsonl`
- `evals/dataset.jsonl`
- `evals/deterministic/test_apple_calendar.py`
- `evals/deterministic/test_apple_tools.py`
- `evals/deterministic/test_applescript_cold_start.py`
- `evals/deterministic/test_browser_agent.py`
- `evals/deterministic/test_cli_memory.py`
- `evals/deterministic/test_coding_eval.py`
- `evals/deterministic/test_compare_history.py`
- `evals/deterministic/test_connect_command.py`
- `evals/deterministic/test_consolidation.py`
- `evals/deterministic/test_delegate.py`
- `evals/deterministic/test_delegate_env.py`
- `evals/deterministic/test_discord_access.py`
- `evals/deterministic/test_episodic_store_switch.py`
- `evals/deterministic/test_fact_mirror.py`
- `evals/deterministic/test_fact_store_conformance.py`
- `evals/deterministic/test_gateway_runner.py`
- `evals/deterministic/test_gateway_supervisor.py`
- `evals/deterministic/test_gather_workflow.py`
- `evals/deterministic/test_gcal_oauth.py`
- `evals/deterministic/test_gh_tool.py`
- `evals/deterministic/test_google_calendar.py`
- `evals/deterministic/test_graph_engine.py`
- `evals/deterministic/test_graph_nodes.py`
- `evals/deterministic/test_graph_stream.py`
- `evals/deterministic/test_graph_topology_payload.py`
- `evals/deterministic/test_judge.py`
- `evals/deterministic/test_judgment_arena.py`
- `evals/deterministic/test_list_events.py`
- `evals/deterministic/test_mcp_cli.py`
- `evals/deterministic/test_mcp_transport.py`
- `evals/deterministic/test_memory_arena.py`
- `evals/deterministic/test_memory_search.py`
- `evals/deterministic/test_notion_episodes.py`
- `evals/deterministic/test_retrieval_gate.py`
- `evals/deterministic/test_scoring.py`
- `evals/deterministic/test_slash_commands.py`
- `evals/deterministic/test_slot_gate.py`
- `evals/deterministic/test_speakable.py`
- `evals/deterministic/test_triage_workflow.py`
- `evals/deterministic/test_wake_word.py`
- `evals/deterministic/test_waku_memory_connect.py`
- `evals/deterministic/test_working_memory.py`
- `evals/deterministic/test_workspace.py`
- `evals/fixtures/mcp_demo_server.py`
- `evals/memory_arena.json`
- `scripts/arena_clean.py`
- `scripts/demo_seed.py`
- `waku/gateway/__init__.py`
- `waku/gateway/cli.py`
- `waku/gateway/discord.py`
- `waku/gateway/runner.py`
- `waku/gateway/supervisor.py`
- `waku/gateway/telegram.py`
- `waku/gateway/voice.py`
- `waku/gateway/whatsapp.py`
- `waku/graph/__init__.py`
- `waku/graph/engine.py`
- `waku/graph/nodes.py`
- `waku/graph/workflows/__init__.py`
- `waku/graph/workflows/gather.py`
- `waku/graph/workflows/triage.py`
- `waku/memory/__init__.py`
- `waku/memory/consolidation.py`
- `waku/memory/episodic/__init__.py`
- `waku/memory/episodic/notion_store.py`
- `waku/memory/episodic/store.py`
- `waku/memory/jev.py`
- `waku/memory/procedural/__init__.py`
- `waku/memory/procedural/exporter.py`
- `waku/memory/procedural/installer.py`
- `waku/memory/procedural/loader.py`
- `waku/memory/retrieval_gate.py`
- `waku/memory/semantic/__init__.py`
- `waku/memory/semantic/base.py`
- `waku/memory/semantic/langmem_store.py`
- `waku/memory/semantic/mem0_store.py`
- `waku/memory/semantic/store.py`
- `waku/memory/semantic/supabase_store.py`
- `waku/memory/semantic/zep_store.py`
- `waku/memory/slot_gate.py`
- `waku/ops/arena.py`
- `waku/ops/brief.py`
- `waku/ops/coding_eval.py`
- `waku/ops/compare_history.py`
- `waku/ops/gather.py`
- `waku/ops/judge.py`
- `waku/ops/judgment_arena.py`
- `waku/ops/judgment_cases.py`
- `waku/ops/memory_arena.py`
- `waku/ops/scoring.py`
- `waku/ops/triage.py`
- `waku/runtime/session.py`
- `waku/tools/_env.py`
- `waku/tools/apple.py`
- `waku/tools/calendar.py`
- `waku/tools/experimental.py`
- `waku/tools/github.py`
- `waku/tools/google_calendar.py`
- `waku/tools/mcp_cli.py`
- `waku/tools/mcp_client.py`
- `waku/tools/mcp_oauth.py`
- `waku/tools/memory_admin.py`
- `waku/tools/messages.py`
- `waku/tools/notes.py`
- `waku/tools/search.py`
- `waku/tools/waku_memory.py`
- `waku/tools/workspace.py`
