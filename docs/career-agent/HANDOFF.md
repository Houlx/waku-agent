# Career Agent handoff

## Status

Days 1–4 are complete. Day 4 was explicitly approved on 2026-10-02 for
stabilization, evaluation, documentation and demo preparation. V1 feature development stops
here. Phase 1 runtime separation was subsequently approved on 2026-10-06;
Phase 2 — Career Product Cutover was separately approved and is implemented.
Phase 3 Batch A is approved and implemented. Career Agent is the sole supported
product. Phase 3 Batch B1 and Batch B2 consumer closure are implemented.
Batch C1 feature backend deletion and Batch C2 facade retirement are implemented.
Batch D final cleanup is implemented; final verification is recorded below.
The separately approved post-v1 UI polish iteration is recorded at the end of this file.
The approved matching correctness fix is recorded below the UI iteration.

Day 1 is committed in `838226b`, Day 2 in `8e7bac3`, and Day 3 in `e70ff0d`.
The [product specification](PRODUCT_SPEC.md) and
[implementation plan](IMPLEMENTATION_PLAN.md) record historical V1 intent. Actual
code and the approved [Career-only refactor plan](CAREER_ONLY_REFACTOR_PLAN.md)
govern runtime separation.

Career code remains MIT.

Batch B1 retires the Elastic License 2.0 hosted implementation; no code moved
across that boundary. Batch D removes unused brand assets and fonts; the upstream
MIT copyright and Waku names notice remain.
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
| `waku/runtime/career_requirements.py` | Canonical groups, eligibility, stable identity and exact-JD/policy extraction reuse |
| `waku/runtime/career_matching.py` | Evidence snapshots, matching input budgets and server-owned delivery coverage |
| `waku/runtime/career_resumes.py` | Generation gates, claim validation, current drafts and Markdown |
| `waku/tools/career.py` | Scoped submission, FTS5 search and evidence lookup |
| `waku/ops/static/career/`, `career.html` | Independent Career UI, routes, drafts, requests, Settings and print rules |
| `waku/ops/debug.py` | Standalone trace/SQL/path utilities without a dashboard server |
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
- `career_requirement_sets`: validated canonical extraction keyed by exact JD and policy.
- `job_requirements`: job-owned scoring groups, category, importance, keywords and JD excerpts;
  complete constraint/provenance/eligibility metadata lives in the saved report.
- `job_matches`: one assessment per SCORED group, status, evidence IDs and reason.
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

Coverage includes only SCORED groups, using required weight 2, preferred weight 1,
MATCH 1, PARTIAL 0.5 and GAP 0:
`100 × sum(weight × value) / sum(weight)`, rounded to one decimal. Empty
scored groups yield insufficient scoreable information and block generation. The UI calls
this JD Requirement Coverage and explicitly excludes hiring/interview probability.

## APIs, tools and tracing

`GET /api/career` returns profile/evidence and saved job/resume artifacts.
`POST /api/career` accepts `save_onboarding`, `normalize`, `save_profile`,
`confirm`, `analyze_job`, `generate_resume` and `delete_job`. Batch B1 removes the old hosted policy.

Normalization, extraction and full-evidence matching expose only `submit_stage_result`.
Inventory matching adds `search_career_evidence` and `get_evidence`; generation exposes
evidence lookup and submission. Search accepts bounded agent-authored query batches, safely
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

## Phase 3 Batch C2 facade retirement on 2026-10-06

Batch C2 removes the final general application assembly and compatibility facades.
Career remains the sole supported runtime. Batch D has not started. The changes
remain uncommitted for review; no user runtime data or configuration is changed.

### Removed assembly and compatibility

C2 deletes `waku/app.py`, `waku/ops/dashboard.py`, `waku/ops/browser_agent.py`,
`waku/integrations.py`, `waku/connect.py`, `waku/ops/settings_api.py` and
`waku/ops/commands.py`. No replacement general framework exists.

CareerRuntime loses only its transitional `_runtime` singleton, singleton lock,
`current_runtime`, `peek_runtime`, `close_runtime` and dual-runtime `before_swap`
hook. The existing owner, lazy client, execution lock, candidate replacement,
rollback and cleanup remain. The unused general `db.connect` wrapper retires;
`open_connection`, `connect_career` and CAREER_SCHEMA remain.

Standalone generic helpers move from the old dashboard to `waku/ops/debug.py`:
trace collection/cursors, read-only SQL and confined path reveal. They import no
facade, expose no HTTP route and assemble no assistant. Career's HTTP server,
allowlist, frontend, provider setup and coordinators retain their behavior.

### Retained runtime and tests

The supported path is CLI → CareerServer → CareerRuntime → Career coordinators
and scoped tools. Shared code consists of Settings/home/dotenv handling, provider
registry/model adapters/catalog/defaults, provider services, SQLite connection
mechanics, run_loop, ToolRegistry, tracing and standalone debugging. No retained
production import requires a removed assembly module.

Career profile/job/resume facade tests now call injected CareerRuntime instances.
Bind tests target Career HTTP directly. Trace encoding checks target standalone
trace helpers. Regional endpoint, scoped credential/model/label and pin/default
checks target provider_services, model adapters and catalog persistence directly.
The import-isolated complete Career journey now refuses every C2 facade import.

C2 retires Connections CLI/health/registry tests, dashboard-only OTel health probes,
general toggle UI tests, disabled-provider write APIs, pin-route/display tests,
chat composer and old dashboard polling/header tests. The removed OTel health
probe had no retained tracing consumer; optional OTel export stays unchanged.
Old handler/route/source assertions retire; deferred logo, design/font/brand,
license and syntax checks remain for the assets that still exist.

`test_c2_retirement.py` checks unavailable assembly modules and standalone SQL/path
confinement, including write CTEs, multiple statements and symlink escapes.
Career HTTP adds oversized/negative/malformed request-length rejection and an
allowlisted static symlink escape check. The HTML escaping test executes Career's
real helper and link renderer in Node instead of inspecting old JavaScript source.
Existing runtime/provider replacement, serialization, redaction, loop/tool bounds,
tracing and legacy-row/file/FTS preservation checks remain.

C2 removes no dependency and changes no dependency version or lockfile. The
remaining extras are eval, dev and tracing. Broad manifest reconciliation belongs
in Batch D.

### Verification and environment

The final offline gate passes **550 tests with 13 skips**, including all **148
executable Career checks** and the scripted Chromium journey. Twelve Make checks
skip because make is unavailable; the exact underlying command runs instead:
`python -m waku.ops.release_gate`. The remaining skip is the disabled live provider
probe. The gate records `judge: not run`; no paid/live evaluation runs.

Ruff, environment-template validation, all 23 retained JavaScript syntax checks,
rulebook/link/distribution/license/design checks and `git diff --check` pass.
Wheel and sdist builds pass; the sdist rebuilds a wheel. Both wheels install into
separate temporary targets. Each installation passes default and explicit Career
launches, all nine approved shell/assets against repository bytes, lazy client
initialization, Career state, general/static-route rejection and owned shutdown.
Installed module enumeration confirms all seven C2 facades are absent. Both wheels
preserve MIT, brand and the three OFL notices.

Two in-memory mutations replace Career escaping with identity output or remove
static confinement. Their regressions fail at escaped-output and symlink-route
assertions respectively. No mutation changes implementation files or user data.

The sandbox initially refuses local sockets; reviewed execution enables the
requested temporary HTTP/browser tests. Chromium initially lacks libnspr4 on its
loader path; existing libraries under `/tmp/career-phase1-browser-libs` supply it.
Builds use a temporary uv cache because the default cache is read-only. None of
these environment adjustments changes project dependencies or configuration.

### Batch D boundary and inventory discrepancies

Batch D still owns `static/index.html`, old `static/style.css`, `static/js/`, old
logos/mark, protected design/font files and their notices/tests; dormant Settings
fields and unused outbox creation; package descriptions/keywords/license manifest;
remaining dependency/config/environment-template reconciliation; pricing utility
consumer closure; and final documentation polish. Protected copied design files
remain untouched. Career serves none of the old frontend assets.

No general-product backend or application assembly remains. General-product
JavaScript implementations still exist only as dormant deferred assets. Generic
SQL/path/trace utilities remain because the approved batch retains debugging.
Provider platform/scoped rows and saved defaults remain shared provider contracts,
without hosted implementation or general integration behavior.

The C1 inventory matches the seven actual facade modules. Its base-URL test also
retains one old provider-view consumer, now migrated to Career provider status.
Its design/font/static tests include old server and frontend behavior assertions,
now retired or migrated while preserving asset/license checks. C1's suggested C2
asset deletion is superseded by this batch's explicit boundary reserving final
asset retirement for D. The older Phase 3 audit predates A/B/C1 consumer closure;
its historical consumers are not restored and no repository-wide audit repeats.

## Phase 3 Batch D final cleanup on 2026-10-06

Phase 3 and Career-only productization are complete. Career Agent is the sole
supported product. The unchanged supported execution path is CLI → CareerServer
→ CareerRuntime → Career coordinators → run_loop and scoped ToolRegistry tools.
Provider configuration/catalogs, SQLite mechanics, tracing and standalone debugging
remain shared Waku infrastructure. No post-Phase-3 feature work starts.

### Assets, configuration and pricing

D removes 57 old static files: the general shell and stylesheet, 16 general
JavaScript files, protected design copies, the mark, provider/integration logos,
three font binaries and their three OFL notices. The two `docs/brand/` mark variants
also retire. The copied design files are deleted as authorized; their contents
are never changed or incorporated into Career styling. The retained static tree
contains `career.html`, seven Career scripts, Career CSS and its README. Career
continues to use system fonts, CJK fallback, Markdown export and print isolation.

Settings removes these 17 dormant fields: `disabled_providers`, `history_turns`,
`consolidate_every`, `retrieval_top_k`, `semantic_store`, `episodic_store`,
`apple_calendar`, `google_calendar`, `google_calendar_id`, `apple_tools`, `gh_tool`,
`gh_repo`, `experimental`, `graph_workflows`, `telegram_token`, `whatsapp_token`
and `whatsapp_phone_number_id`. Obsolete environment values are ignored, including
malformed former numeric values. `ensure_home` stops creating an unused outbox;
existing outbox contents remain untouched.

Settings retains `provider`, `api_key`, `base_url`, `model`, `small_model`, `home`,
`max_iterations`, `max_tokens` and `otel_endpoint`. Timeout, HTTP binding/port,
scoped provider overrides and dotenv precedence retain their existing consumers.
The environment template already documents only those retained settings and needs
no regeneration. Legacy home startup notices now identify Career Agent.

Catalog parsing retains per-model input/output prices directly in response entries.
D deletes `ops/pricing.py`, including remember_price, unused price/cache/cutoff
reporting and spend aggregation. No retained code read that cache. Registry price
metadata and saved model pins/default resolution remain compatible.

### Dependencies, packaging and automation

No dependency or extra is removed in D: Anthropic/OpenAI supply the model adapters,
python-dotenv supplies configuration, and Rich supplies the standalone trace viewer.
`eval` retains pytest; `dev` retains pytest, pinned Ruff and Hatchling; `tracing`
retains Phoenix, OTel SDK and OTLP export. No version or lock pin changes. Offline
`uv lock --check` resolves the existing 155-package lock without changes.

Package description and keywords identify Career. Wheel/sdist exclusions reject
restored retired static assets, and distribution tests inspect actual Hatchling
members. The license expression becomes `MIT AND LicenseRef-Waku-Brand`, with
LICENSE and LICENSE-BRAND in both distributions. OFL files/globs retire with their
fonts. Upstream MIT copyright stays unchanged; LICENSE-BRAND still governs names.
No protected brand assets, font binaries or EL2 implementation ship.

Make's six targets already correspond to supported functionality: run, dashboard,
trace, eval, gate and lint. No target needs deletion. JavaScript syntax checks now
inspect only Career scripts. Old first-run/design/logo/disabled-provider/spend
contracts retire; Career security, browser, provider and shared-runtime guarantees
remain. New regressions enforce the exact static tree, retained Settings fields,
ignored obsolete values, preserved home files, absent outbox creation and build
exclusion of synthetically restored retired assets.

CI retains lint, environment validation and deterministic checks; release retains
build/artifact validation. The historical workflow filename `validate-skills.yml`
and job ID `skills-and-evals` remain for external branch-protection compatibility.
The local preview preset now launches Career. The obsolete general new-tool
maintenance skill and design sync script retire. Retained review/worktree/ship
skills use supported Career commands, temporary homes and offline gates.

### Documentation and retained tree

Current README, Career guide, handoff, architecture, status, getting-started,
provider guide, docs index, ops/static READMEs, contributor/rulebook/conventions,
security and maintainer guidance describe Career. Commands/evals/integrations docs
already describe only supported commands and retained behavior. Their retirement
notes explain upstream ancestry. Historical V1 spec/plan, refactor plan, Phase 2
inspection and Phase 3 audit receive only a current-status banner.

| Retained area | Files and reason |
|---|---|
| Top-level Python | `__init__.py` owns version/identity; `__main__.py` owns Career dispatch; `config.py` owns compatible settings/home/dotenv; `db.py` owns connection mechanics and Career schema |
| `waku/loop` | `__init__.py`, `agent.py`, `models.py` retain run_loop and provider adapters |
| `waku/runtime` | `__init__.py`, `career_runtime.py`, `career.py`, `career_jobs.py`, `career_resumes.py` retain lifecycle and profile/job/resume stages |
| `waku/tools` | `__init__.py`, `registry.py`, `career.py` retain the tool contract and scoped Career tools |
| `waku/ops` | `__init__.py`, `career_dashboard.py`, `provider_services.py`, `catalog.py`, `tracing.py`, `show_trace.py`, `debug.py`, `release_gate.py` retain HTTP, providers, observability, standalone debugging and offline verification |
| Static | `career.html`; `career/ui.js`, `state.js`, `router.js`, `actions.js`, `render.js`, `settings.js`, `bootstrap.js`, `style.css`; `README.md` documents ownership |
| Data registry | `waku/providers.toml` retains provider defaults, scoped adapter contracts and compatible metadata |
| Extras | `eval`, `dev`, `tracing` retain current evaluation/build/debug consumers |
| Current docs | Root README, AGENTS, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT and licenses; docs README, career, architecture, status, getting-started, commands, evals, providers-registry, integrations; context conventions, design-system, writing-rules, gotchas, maintainers; proposal policy; Career handoff; ops/static READMEs |

No obvious general-product implementation or frontend artifact remains in the
retained tree. Waku-oriented package/module names remain to preserve stable imports
and installed commands. `WAKU_*`, `.waku`, `state.db`, provider adapter fields,
platform row and saved pins retain configuration/data compatibility. Standalone
trace/SQL/path utilities remain intentionally supported without debugging HTTP
pages. Legacy fixture SQL proves preservation rather than recreating old features.
Ignore patterns protect dormant user data and telemetry. Maintenance skills are
repository authoring tools, excluded from distributions; Career loads no skills.
Upstream URLs, LICENSE-BRAND and historical docs preserve attribution and ancestry.

### Final verification

The full offline release gate with Chromium enabled passes **475 tests with 13
skips**, with no deselections. Twelve Make checks skip because make is unavailable;
the exact supported underlying commands run directly. The remaining skip is the
disabled live-provider probe. All Career/profile/job/resume, grounding/provenance,
exact coverage, FTS5/database preservation, provider/model/lifecycle, loop/registry,
tracing, config/home/dotenv and HTTP/static-security regressions pass.

The scripted Chromium journey passes provider failure/recovery, profile editing,
routes/drafts/navigation, matching/evidence, explicit multilingual generation,
Markdown, themes, print isolation, stale artifacts and reload. Its network allowlist
rejects retired assets and APIs. The harness verifies checkout dotenv preservation.
Chromium/Playwright and missing loader libraries are installed only under `/tmp`.

Ruff, Career/fixture JavaScript syntax, environment-template validation, all 26
current/historical Markdown file-link scans, rulebook checks, retained notices,
lock consistency, maintenance-skill validation and `git diff --check` pass.
Wheel and sdist builds pass; isolated wheel installation and direct source archive
installation both pass default `waku` and explicit `waku career` dispatch, state
API, all nine approved shell/assets against checkout bytes, retired-route rejection,
lazy client initialization and owned connection shutdown. Installed module checks
confirm general backends/facades and pricing are absent. Both archives retain MIT
and the Waku names notice and distribute no fonts, marks or old styles/scripts.

Three mutations confined to temporary projects or patched functions restore an
extra static asset, unused outbox creation or retired-asset distribution inclusion.
Each corresponding regression fails. No mutation edits repository implementation.
The initial restricted suite cannot create sockets; reviewed socket-enabled runs
pass. An installed smoke harness initially assumed a new profile was truthy;
checking the valid empty profile contract resolves that harness error.

D modifies no user dotenv, credentials, runtime data, legacy rows/tables, schema,
SOUL files, chat/memory files, traces or usage. No paid/live evaluation runs.
Windows behavior, live provider availability and OTel exporter shutdown remain
outside this verification, as before. The Phase 3 Definition of Done is satisfied
for the retained project and its requested offline/build/browser/install checks.

## Post-v1 UI polish on 2026-10-06

This separately approved iteration covers UI localization, responsive sidebar navigation,
permanent saved-Job deletion and contextual sticky actions. It is not Phase 4 of retirement.
CareerRuntime ownership, schema, AI stages, retrieval, matching, deterministic coverage,
provenance, grounding and provider/model behavior remain unchanged. No dependency is added.

`career/i18n.js` owns stable English/Simplified Chinese translation keys, interpolation,
expected error labels and locale-aware counts/coverage. `career-locale` stores `en` or
`zh-CN` in browser storage. Saved preference wins; compatible Simplified Chinese browser
preferences otherwise select Chinese, with English as fallback. Storage failures retain
an in-memory preference. The shell updates HTML language. Locale changes render cached
state without requests or provider calls and preserve drafts, routes and resume-language
selections. Generated artifact prose, document headings and user-entered dates remain
in their original content language. Existing diagnostic activity and unknown redacted
error details remain untranslated. Activity persistence is unchanged.

The 260px desktop sidebar contains Overview, Career Profile, Settings, Analyze New Job,
five Recent Jobs and View All Jobs. It uses the existing snapshot and stable ID routes;
reports and resumes highlight the same job. Recent order retains the backend's creation
timestamp and ID ordering. Below 900px, a native disclosure supplies compact navigation
and closes after route selection. Long titles and translated labels wrap.

`delete_job` uses the existing serialized non-AI action path. A localized native dialog
explains that job analysis and resume will be permanently removed while Profile and
Evidence remain. One SQLite transaction deletes matches, requirements, resume and job
in that order; no cascade or schema change is required. Malformed/missing IDs expose
stable `invalid_job_id`/`job_not_found` codes with safe error details. Failure rolls back
all rows. Shared profile/evidence/FTS, other jobs, traces and usage remain intact.

Deletion prevents duplicate submissions, retains unrelated JD drafts and clears only
the deleted job's reanalysis target and language selection. Deleting the viewed report
or resume replaces its current history entry with `#jobs`, unless navigation changed
while pending. Earlier deleted URLs show the existing unavailable state. Lost responses
are reconciled with a workspace read rather than a repeated delete.

Sticky bars contain profile save/normalize or save/confirm, job analysis, resume language
and generation/view controls, and resume Markdown/print controls. Existing gates remain.
Delete, evidence, record removal and back/edit controls remain contextual. Main content
continues to scroll as a document. Opaque theme-compatible bars wrap; print rules hide
the sidebar, dialogs and application controls for both native and explicit printing.

System CJK font availability and print pagination remain platform-dependent. The
headless test host has no Chinese system font, so screenshots show missing glyphs;
translation text and layout behavior are verified, but CJK glyph rendering on this
host is not. No fonts are bundled or installed into the product. Browser
verification covers Chromium; other browser engines and operating systems are not
independently verified. UI localization does not improve cross-language FTS retrieval.

### UI iteration files

| Area | Changed files |
|---|---|
| Shell and assets | `waku/ops/static/career.html`; `i18n.js`, `ui.js`, `state.js`, `router.js`, `actions.js`, `render.js`, `settings.js`, `bootstrap.js`, `style.css` under `waku/ops/static/career/` |
| Backend | `waku/ops/career_dashboard.py`; `waku/runtime/career.py`, `career_jobs.py` |
| Deterministic evals | `evals/deterministic/test_career_assets.py`, `test_career_browser.py`, `test_career_delete.py`, `test_career_polish.py` |
| Scripted fixtures | `evals/fixtures/career_browser.cjs`, `career_state.cjs`, `career_polish_browser.cjs`, `career_polish_state.cjs` |
| Documentation | This handoff; `docs/career.md`, `status.md`, `context/conventions.md`, `context/design-system.md`, `context/gotchas.md`; `waku/ops/static/README.md` |

### UI iteration verification

The full retained deterministic suite passes **495 tests with 13 skips**, including
the expanded scripted Chromium journey. Twelve skips require unavailable Make;
the remaining skip is the explicitly disabled live-provider probe. No live provider
is required or called. Verification uses synthetic profiles, scripted initial and
replacement clients, fresh SQLite homes and temporary provider configuration.

Browser coverage includes English/Chinese switching during idle and active requests,
locale persistence/defaults/storage failure, no translation requests, preserved profile/
JD/provider/language drafts, both locales on direct routes, selected sidebar jobs,
five-entry Recent Jobs refresh, same-route Analyze New Job, narrow navigation and
long Chinese titles, sticky visibility and focus clearance, native/explicit print
isolation, localized delete cancellation, other/viewed/resume deletion, failure,
duplicates, pending navigation, history and reload. Offline tests cover expected
delete codes, every transaction step's rollback, Profile/Evidence/FTS/file preservation,
foreign-key enforcement, existing/lazy clients and runtime serialization.

Ruff, all Career/fixture JavaScript syntax checks, environment-template validation,
offline lock consistency, local Markdown file links in all 26 documents, rulebook,
license/distribution checks and `git diff --check` pass. Wheel and source archive
builds and offline isolated installs pass. Both installed products pass default and
explicit Career startup, all ten shell/assets against checkout bytes, deletion API,
lazy AI client and owned shutdown. Both archives retain exact MIT/Waku-name notices.
No default dependency, version or lock file changes.

Two temporary mutations skip resume deletion or alter a language draft during locale
switching. Each corresponding regression fails. Neither mutation edits repository
implementation files. Screenshots for desktop/mobile Chinese UI and confirmation
remain under `/tmp`; the missing system-glyph limitation above applies.

The approved UI iteration ends here. No subsequent feature iteration starts.

## Matching correctness fix

The focused fix approved on 2026-10-07 closes the evidence-delivery failure in
the [historical diagnosis](MATCHING_CORRECTNESS_DIAGNOSIS.md). Job matching now
receives every active Career Evidence record before judgment when its initial
request fits 48,000 serialized UTF-8 bytes. Each record supplies evidence ID,
source type, raw content and normalized content. The payload omits database row
IDs, active flags, duplicate search text and redundant source IDs outside the
normalized content. The later context-budget fix removes supplemental retrieval from
full mode; inventory mode retains FTS and get_evidence.
Full records already supplied in context can support citations without another
search or redundant inspection.

`career_matching.py` owns a digest of the confirmed profile and sorted active
evidence snapshot. Server-owned required IDs include every active record for
every requirement. The server credits full context only after a successful
provider response. In inventory mode, the server credits a complete get_evidence
record only after its tool result has reached a subsequent provider request.
Calling search, receiving an empty result, listing IDs, or executing inspection
and submission in the same response does not establish complete coverage.
Validation rejects GAP until the required set has been delivered. It still
permits a genuine GAP after complete delivery; coverage does not force MATCH.

Profiles that exceed the initial budget receive a sorted inventory of all active
IDs, source types and titles. The common required ID set conservatively includes
all active records, even for unknown or mixed categories. This avoids introducing
category routing. Existing get_evidence can inspect candidates directly from
the inventory, with FTS available for prioritization. Each subsequent matching
request checks the complete accumulated system/messages/tool-schema input against
64,000 UTF-8 bytes. These application limits reserve 16,000 bytes for tool history
but do not estimate provider tokens or guarantee every model's context capacity.
An oversized inventory, oversized inspection history, incomplete coverage, or
iteration exhaustion stops analysis without evidence truncation or replacement
of a previous report. This conservative fallback does not promise successful
analysis of arbitrarily large profiles.

The snapshot digest must remain current at validation, after the final response,
and under SQLite's writer lock before publication. The narrow education guard
requires an education citation for pure education/degree MATCH or PARTIAL.
Project/work citations alone fail that guard. Mixed experience clauses retain
semantic judgment. The guard recognizes education categories and narrow degree
phrasing without treating “a high degree of autonomy” as an education requirement.

Career Activity records matching mode, active record totals, deterministically
delivered totals, available records and final citation IDs. Trace coverage events
record those counts and the snapshot digest, including failures. Existing tool
events record supplemental FTS queries/results. The fix does not add full profile
copies, system prompts, or hidden reasoning to diagnostic metadata.

The minimal bachelor's/master's/React fixture remains synthetic. Its former
expected failure now passes. Repeated React-only, bachelor-only and restrictive
searches preserve both degrees in matching context and can MATCH the master's
requirement. Tests also verify genuine GAP, project/work-only positive rejection,
unknown/mixed requirements, inventory inspection, same-response rejection,
UTF-8 budget boundaries, oversized inventory/history, snapshot invalidation,
prior-report retention, accumulated tool context, OpenAI adapter conversion and
unchanged profile/evidence/FTS tables across analysis.

### Correctness verification

The diagnostic suite passes 31 tests. All Career deterministic tests pass within
the retained suite. The complete retained gate with Chromium enabled passes
526 tests with 13 skips and no expected failures. Twelve skips require unavailable
Make, and one skips the explicitly disabled live-provider probe. Because Make is
unavailable, verification invokes the Python commands from its targets directly.
The requested scripted Chromium journey passes reports, evidence, resumes,
settings, locales, navigation, deletion, printing and reload. Ruff and
`git diff --check` pass.

Wheel and source archives build and install offline into separate `/tmp` targets.
Both installed products run all four minimal-fixture query routes through the
real matching coordinator and retain MATCH with master's citations and unchanged
profile/evidence/FTS. Distribution boundary checks pass in the retained suite.
A temporary in-process mutation removes preloaded evidence while falsely claiming
full coverage; the repeated-query regression fails with GAP versus MATCH. The
mutation edits no production file. Gate reports, browser tooling, package targets
and diagnostic artifacts remain outside runtime user data. No paid/live provider
evaluation runs.

The fix changes no extraction prompt, atomicity, importance rules, evidence
persistence/IDs, SQLite/FTS schema, score formula, resume contract, shared loop,
provider architecture, default dependency, model or UI controls. Existing unrelated
UI edits remain intact. The diagnosis receives only a short implementation-status
note and preserves its original findings.

The remaining variability concerns semantic interpretation and requirement
extraction. Delivery coverage proves that facts were available, not that a model
understood or correctly judged every record. Major equivalence, compound clauses
and extraction consistency remain separate follow-up work. No extraction work
or general retrieval redesign begins in this fix.

## Canonical requirement groups and eligibility on 2026-10-07

The approved first Coverage stabilization stage implements the
[canonical requirement contract](REQUIREMENT_GROUPS.md). `career_requirements.py`
owns the closed extraction schema, shallow ALL/ANY constraints, optional education
alternative, source offsets, semantic identity, eligibility guards and reuse policy.
Degree and major share one education group. The bachelor's relaxation remains a
conditional route inside that group. Recognized technology alternatives require
one ANY group. Duplicate normalized subjects and overlapping material source spans
cannot create separate scoring opportunities, including category relabeling of the
same qualification. The validator preserves recognized policy-sensitive JD clauses.

The extraction schema closes category to education, experience, skill, certification,
language, demonstrated_capability, logistics, personal_trait and other. Every group
requires SCORED, NEEDS_CONFIRMATION or NON_SCORABLE before matching. Objective
qualifications and observable behavior/output criteria can be scored. Declarative
logistics and driver's-license requirements need confirmation. Generic health,
diligence, dedication, responsibility, moral character and undefined personality
wording remain non-scorable. A bare writing-ability label or generic teamwork spirit
remains excluded; observable writing outputs and collaboration tasks can be scored.
Domain terms such as travel software, dedicated GPU, character encoding and high
availability do not become personality or logistics claims.

An additive `career_requirement_sets` table stores the first validated extraction
for exact JD content and policy version `groups-v1`. Atomic first-writer publication
prevents candidate replacement. Matching failure retains the accepted set. Identical
new jobs, reanalysis, process restart, profile edits and provider/model changes reuse
that set. A changed JD or policy needs a new extraction. This stage exposes no explicit
re-extraction action or requirement-history UI. Old-policy reports retain their saved
scores and artifacts, appear outdated and block generation until reanalysis.
Job deletion prunes unreferenced cached JD versions within its existing transaction;
other jobs and reports retain their shared sets.

The matching request and validator accept only SCORED groups. The saved report retains
all groups and metadata; the existing requirement table columns remain compatible.
LEFT JOIN reads preserve excluded rows without assessments. English and Chinese
reports separate confirmation and non-scorable clauses from scored required/preferred
groups. Excluded clauses show source wording and reasons without match badges or
invented GAP. Zero scored groups produce insufficient scoreable information and
disable resume generation. Required/preferred weights, MATCH/PARTIAL/GAP values,
one-decimal arithmetic, evidence delivery, FTS, matching definitions and the matching
prompt remain unchanged. The resume addition only gates old-policy analyses.

### Stabilization evaluation

Reviewed synthetic fixtures cover degree/major, conditional fallback, technology OR,
health/attitudes, responsibility/morality, observable collaboration and writing,
undefined initiative, logistics, explicit importance and duplicate paraphrases.
The diagnosed Chinese JD equivalent contains invented Northstar Instruments/Cedar Labs
facts rather than private runtime profile data.

Six analyses of that equivalent reuse seven canonical groups, four SCORED groups,
three NON_SCORABLE groups and denominator 7. The previous 7/8/9 extraction-count
instability does not recur on reanalysis. Health/diligence/dedication never reaches
matching or arithmetic, and the education fallback never adds a preferred weight.
Six broader gold analyses reuse ten groups, six SCORED groups, one confirmation group,
three non-scorable groups and denominator 10. Both runs report 100% identity, source
coverage, importance, category and eligibility agreement, with zero changed-identity
merge/split and normalized-subject duplicate rates. The eval compares gold source
spans independently of matching and saves metrics under pytest's temporary directory.

These are offline real-coordinator/cache evaluations with scripted extraction and
assessment proposals. They prove reuse and structural enforcement, not fresh model
extraction accuracy or deterministic semantic grading. Unknown subject synonyms can
still require additional reviewed alias/gold coverage. Conservative provenance guards
can reject a broad excerpt rather than guess its grouping. Related-major equivalence,
threshold interpretation and evidence sufficiency remain semantic follow-up work.

### Stabilization verification

The full retained offline gate passes **562 tests with 13 skips**, including both
Chromium journeys. Twelve skips require unavailable Make; the last skip disables the
live-provider probe. The equivalent Python gate and lint commands ran directly.
The 35 focused canonical-group regressions pass. Chromium verifies the existing
Career journey and new scored/excluded/confirmation reports in both locales,
zero-score display and disabled generation. No live provider evaluation ran.

Ruff, environment-template validation, JavaScript syntax and `git diff --check` pass.
Temporary in-process mutations bypass eligibility filtering or disable extraction
reuse; each relevant regression fails. Neither mutation edits production files.
Wheel and source archives build and install offline into separate `/tmp` targets.
Both installed products pass default/explicit startup, static/API checks, lazy-client
shutdown, canonical schema/eligibility, three diagnosed-equivalent analyses with
one extraction, stable identities, and source-byte comparisons for changed runtime
and frontend files. Distribution/license checks pass in the retained gate.

The first sandboxed full run could not create localhost sockets. Reviewed runs use
socket access and synthetic data only. An initial Chromium retry used the wrong
library path; the successful runs use the existing libraries under `/tmp`.
All diagnostic artifacts, package targets, traces and usage remain under `/tmp`.
This stage does not modify the user's live database, dotenv, credentials,
profile, evidence, traces or spend ledger. No dependency, provider/model setting,
version or lock file changes. The matching-rubric stage has not begun.

## Matching Rubric Stabilization on 2026-10-07

The approved [matching-v1 rubric](MATCHING_RUBRIC.md) evaluates material constraints
before assigning one MATCH/PARTIAL/GAP result per SCORED group. A matching-only overlay
adds local constraint IDs and existing primary/alternative routes to copied groups.
Alternative conditions receive explicit assessments, including conditions stronger
than abbreviated route items. Cached groups-v1 extraction, provenance, semantic identity,
eligibility, denominator membership, evidence delivery, FTS and Coverage arithmetic
remain unchanged. No extraction prompt, provider/model, dependency or UI changed.

Every constraint result records SATISFIED/PARTIALLY_SUPPORTED/UNSUPPORTED, delivered
supporting evidence IDs and a factual reason. Group assessments retain their existing
fields and add `constraint_results` and `satisfied_routes`. MATCH requires a complete
ALL/ANY route. An alternative must also satisfy its condition. PARTIAL requires genuine
positive material support without a complete route and must explain weaker/unmet
material. GAP requires no positive support and complete applicable evidence delivery.
Python rejects inconsistent statuses, route mixing, duplicate/foreign/missing constraint
IDs, invalid citations and citation-union mismatches. Degree/major constraints require
education evidence individually; the existing group-level education guard remains.
Saved reports record `matching_policy_version: matching-v1`. Historical reports remain
inspectable, and failed reanalysis retains its previous report and Coverage.

The semantic policy separates degree level from major, permits only exact/confirmed
field mappings and the reviewed computing-to-computer-science/software-engineering
related-field set, and disallows arbitrary academic equivalence. Higher degrees cannot
substitute for unmet field constraints. Relevant evidence below explicit thresholds
supplies partial support; unrelated tenure and overlapping intervals cannot manufacture
skill years. Named technologies need actual support, with no approved adjacent-stack
relationships. Observable coordination, communication, reviews and writing outputs
can support demonstrated capabilities without literal personality slogans. Project
success cannot prove a broad trait, and matching cannot strengthen writing criteria.
Existing NON_SCORABLE clauses remain outside matching.

### Frozen-input evaluation

The new fixture freezes 25 reviewed synthetic canonical group/evidence pairs with
invented identities. Education cases cover exact/related/unsupported majors, lower and
higher degrees, valid/incomplete alternatives and cross-route mixing. Skill cases cover
exact technology, either OR side and an unrelated stack. Threshold cases cover exact,
above, below, absent, ambiguous and overlapping experience. Collaboration and writing
each cover explicit, limited/indirect and absent support. Matching tests invoke no
extraction. Six fresh scripted stages per pair produce 150 accepted reports.

`evals.career_matching` freezes one confirmed evidence snapshot and group set, stamps
policy, records a requirement fingerprint and measures per-group pairwise agreement,
full-vector pairwise agreement, status frequencies, reviewed unsupported-inference rate
and Coverage spread separately. The gold oracle measures material/status/citation
overclaims; it does not judge arbitrary explanation prose. Without gold, inference
rate remains null. These six-trial scripted experiments report 100% group/vector
agreement, zero gold overclaims and zero Coverage spread. A deliberately stronger,
varying proposal produces disagreement, overclaims and score spread in the metric test.
These results prove deterministic enforcement and experiment wiring, not real-model
semantic stability. No paid/live provider evaluation ran.

### Verification and limits

The 45 focused rubric tests pass. All Career deterministic checks pass with both
Chromium journeys: **279 passed, 12 skipped**. The skips require unavailable Make.
The final retained offline gate passes **607 tests with 13 skips**, including both
Chromium journeys; the additional skip disables the live-provider probe. This environment
uses the equivalent Python gate/lint commands because Make is unavailable.
The gate includes prior matching-correctness, canonical-group, distribution and
rulebook regressions. Ruff, environment-template validation and `git diff --check` pass.
An in-process mutation bypassing material validation makes the new report-preservation
regression fail; it edits no production file.

Wheel and source builds install offline into separate temporary targets. Both installed
products pass default/explicit startup, HTTP/static boundaries, lazy-client shutdown,
all 25 gold structural checks, report policy/constraint persistence and three analyses
with one reused extraction. Changed runtime files match repository bytes in both
installs. Sandbox socket restrictions required reviewed localhost access for synthetic
HTTP/browser/package checks. All experiment artifacts, homes, traces and usage remain
under `/tmp`; the user's runtime, dotenv, credentials and evidence were not changed.

Structural validation cannot decide whether a model's SATISFIED claim is semantically
true. Related-major boundaries outside the reviewed set, exceptional alternative
conditions, ambiguous skill durations and indirect behavior/writing support still need
semantic review and optional live repeated trials. This stage stops at Matching Rubric
Stabilization and does not begin fresh-extraction accuracy work.

## Fresh Extraction Executability Fix on 2026-10-07

The accepted fresh-extraction diagnosis remains historical evidence: 53 submissions
failed across six sessions before matching. The local diagnosis and structured trace
audit remain outside repository fixtures. This implementation fixes qualification
coverage and explains existing groups-v1 rules without changing matching-v1, evidence
delivery, eligibility policy, Coverage arithmetic, HTTP status handling or cache identity.

Python now derives candidate qualification clauses from recognized English/Chinese
sections and conservative unheaded-clause prefixes. Every recognized sensitive occurrence
in qualification clauses still needs group provenance, including repeated genuine
qualifications. Responsibility and descriptive occurrences create no obligation or
additional scoring opportunity. Constraint provenance cannot come exclusively from duties.
Technology-alternative detection uses qualification occurrences too. The
[requirement contract](REQUIREMENT_GROUPS.md#qualification-coverage-invariant) records
the exact invariant and lexical-parser limits.

The extraction prompt and schema descriptions explain nested group/route containment,
degree AND major, one ANY technology group, conditional education routes and independent
scoring opportunities. Canonical wording uses the existing `text` field; literal subjects
and verbatim excerpts preserve typos, punctuation and spacing. A bachelor's exception
cannot become independent preferred credit or jointly required primary/fallback degrees.
Recognized alternative majors cannot become multiple jointly required ALL constraints.
Broad coordination excerpts cannot promote a bare writing label into SCORED material.
Existing duplicate, overlap, enum and eligibility guards remain active.

Scoped validator messages identify fields, stable error identifiers and repair guidance.
The unchanged loop/tool registry returns those messages to the next attempt. Python
retains offset derivation, semantic identity, policy checks and first-accepted-set storage.
The iteration cap and `groups-v1` exact-JD key remain unchanged; no reports are backfilled.

The 13 diagnosis cases now cover the corrected acceptance boundary and preserved
rejections. Additional synthetic cases cover responsibility-only mentions, omitted and
repeated qualifications, original numbered formatting, typo-preserving source identity,
semantic ALL/ANY errors, strict health/writing eligibility, actionable repair and fresh
cache publication. Restoring the old occurrence-coverage function in memory makes the
acceptance regression fail. No runtime file was changed for that mutation check.

Five independent extraction-only GLM/glm-5.2 trials started with empty temporary canonical
caches and all validated. Submissions until acceptance were 1, 4, 1, 1 and 2; total loop
iterations were 2, 5, 2, 2 and 3, including final confirmation. All accepted sets revalidated
unchanged with the final Python guards. Every trial retained four SCORED groups and
denominator 7. Reference material-source coverage and source eligibility agreement were
100%, and normalized-subject duplicate rates were zero. Total groups varied from six
to seven. Exact semantic-ID agreement against the reference was 16.7–18.2%, and changed
identity rates were 81.8–83.3%. Exact-ID eligibility agreement was 28.6%; source-aligned
eligibility agreement was 100%. Different literal subjects and excluded-clause groupings
remain observable. These results show executability for one synthetic JD, not stable
fresh canonical semantics or general extraction accuracy. No matching ran in the experiment.

The focused extraction/canonical checks passed 72 tests. The retained offline gate passed
642 tests with 15 skips. Both opt-in Chromium journeys passed. Ruff and environment-template
checks passed. Wheel and source builds installed offline into separate temporary targets;
installed extraction validation and exact runtime-byte comparisons passed. `git diff --check`
passed. All provider trials, caches, usage and build/install artifacts remain under `/tmp`.

Remaining failures can include unrecognized section headings, ambiguous mixed prose,
unsupported semantic inheritance, subject/category variation, malformed submissions and
iteration exhaustion. The lexical guards cannot prove arbitrary textual entailment.
The implementation stops at extraction executability and begins no matching or score work.

## Full-evidence matching context-budget fix on 2026-10-07

Full-evidence matching now exposes only `submit_stage_result`. The coordinator keeps
its existing conservative mode selection, then removes search and inspection from
that stage's registry after selecting full mode. Every active compact evidence record
remains in the initial context. Inventory mode retains its existing retrieval tools.
The underlying search and evidence functions remain available to inventory matching,
resume generation and internal validation.

Delivery accounting remains unchanged. A successful provider response establishes
availability of preloaded records, so their stable IDs can support direct citations.
Failed provider calls establish no coverage. Snapshot continuity, active/delivered
citation checks, education guards, complete GAP coverage and matching-v1 route algebra
remain enforced. Extraction, Coverage arithmetic, evidence persistence and both copies
of matching groups remain unchanged. Initial selection still uses 48,000 bytes and
every provider request still uses the 64,000-byte cap. The generic budget error now
says analysis could not complete, rather than attributing every failure to inspection.

### Accepted diagnosis and replay

The two diagnosed live failures used full mode with eight active evidence records.
Both fetched all eight preloaded records again and submitted reports that validated.
The first failed before provider request three; the second made an empty search and
failed before request four. The failure prevented final loop confirmation and saving.
Recorded lookup results contain 16,934 raw bytes, including 16,542 bytes of already
preloaded record content. Matching-v1 added 7,646 initial bytes against the preceding
contract, but redundant lookup history caused the demonstrated avoidable overflow.

The original offline reconstruction measured 39,015 initial bytes and 68,122/68,123
bytes before rejected confirmation requests. Traces do not retain complete assistant
messages or tool-call IDs, so these values describe the reconstruction rather than
exact historical wire payloads. The diagnostic script and original audit remain at
`/tmp/career_budget_diagnosis.py` and `/tmp/career-budget-diagnosis/audit.json`.
The fixed offline replay skips retrieval, retains original submitted reports and
completes at 47,834/47,412 bytes, starting at 38,289 bytes with submission-only schemas.
Its separate audit is `/tmp/career-budget-fixed-replay/audit.json`. No live provider
call or hidden reasoning collection occurred during this fix.

### Regression coverage and inventory limitation

A synthetic eight-record regression uses four SCORED groups and a substantial
matching-v1 report. It completes submission and final confirmation at 38,563 and
49,157 bytes. Restoring full-mode retrieval in memory makes this regression fail
after successful report validation, reproducing the diagnosed failure without editing
production files. Additional checks reject unregistered retrieval without returning
records, preserve a previous report after an oversized validated submission, verify
direct preloaded citations and retain inventory inspection and incomplete-GAP guards.

Inventory inspection remains functionally unchanged. Repeated lookups can still append
duplicate full records until the request budget or iteration cap stops the stage.
Deduplicating its tool results safely must retain successful-delivery accounting and
complete grounding; this fix introduces no inventory context compaction. Arbitrarily
large profiles can still fail explicitly without truncation or report replacement.

### Verification

The matching, rubric, canonical, job and acceptance checks passed 168 tests before
the additional report-preservation case; all three context-budget regressions passed.
All Career deterministic checks passed 319 tests with 12 Make-dependent skips,
including both scripted Chromium journeys. The full retained offline gate passed
647 tests with 13 skips; the additional skip disables the live-provider probe.
Ruff, environment-template validation and `git diff --check` passed.

Wheel and source builds installed offline into separate temporary targets. Both
installed products passed default/explicit startup, HTTP/static boundaries, lazy-client
shutdown, 25 rubric gold cases, cached extraction reuse and all three budget regressions.
Installed matching runtime files matched repository bytes. Sandboxed HTTP tests required
reviewed localhost socket access; synthetic homes, gate reports, builds and replay
artifacts remain under `/tmp`. No user runtime data, credentials, provider settings,
dependencies or limits changed. This stage stops at the full-mode context-budget fix.

## Matching Submission Reliability Fix on 2026-10-07

Matching now distinguishes an unsubmitted normal completion from output truncation.
The OpenAI-compatible adapter retains the original `finish_reason` as `raw_stop_reason`
for ordinary and streamed responses. Length termination without tool calls normalizes
to `max_tokens`; normal completion and tool use retain their existing normalized forms.
Unknown raw reasons remain observable. Native Anthropic reasons already arrive through
`stop_reason`. Loop traces record both reasons without collecting assistant prose or
hidden reasoning. Generic loop response text and completion behavior remain unchanged.

### Accepted intermittent diagnosis

The historical successful matching stage ran from 15:34:55 to 15:37:09 Asia/Shanghai.
The following failed stages started at 15:40:16 and 15:41:34. All three used the same
exact-JD/groups-v1 key, matching-v1 policy and evidence snapshot, full mode and eight
active/delivered records through OpenRouter's `nvidia/nemotron-3-super-120b-a12b:free`.
Each failure made one provider call, zero submit calls and reported 8192 output tokens.
Neither failure reached validation or exhausted ten iterations. Raw termination reasons
were not retained, so output exhaustion remains a hypothesis for those historical calls.
The adapter previously mapped a synthetic raw `length` response to `end_turn`.

The successful stage received four rejections: two string-valued result arguments,
one education-only report and one report using bare source UUIDs as citations. It then
submitted a valid object with exact evidence IDs and confirmed completion in five turns.
No rejection came solely from satisfied routes or group statuses. Its accepted major
judgment also missed a confirmed user edit; structural acceptance did not prove semantic
accuracy. The original audit remains at `/tmp/career-live-matching-diagnosis/REPORT.md`
and `audit.json`. The preceding context-budget diagnosis remains a separate incident.

### Submission protocol and repair feedback

`career_submission.py` owns one matching-only correction after a no-tool completion
without captured valid state. The optional loop continuation stays within the existing
ten-iteration cap. Recovery removes only that invalid assistant response, adds a concise
submit-only instruction and preserves initial canonical/evidence inputs, prior tool
calls/results, server-owned coverage and snapshot checks. Recovery also checks its input
budget before another provider request. Repeated no-submit responses return an explicit
submission error. Length termination, repeated truncation or an unsafe truncation recovery
returns an actionable output-truncation error. Missing reports never become GAP.

Full mode requests named `submit_stage_result` through OpenAI-compatible or Anthropic SDK
clients until a valid report is captured. Final confirmation releases forced choice.
Inventory mode retains retrieval autonomy. Explicit unsupported tool-choice HTTP 400/422
responses disable enforcement for that stage and retry without the option; unrelated
provider errors propagate. Injected clients retain their existing signature. Silently
ignored choices still reach the bounded corrective fallback. Provider/model restrictions
remain endpoint-specific, as the [adapter contract](../providers-registry.md#termination-and-stage-scoped-tool-choice)
records. Rejected capability requests add an HTTP request without raising the loop cap.

Validator feedback now names the received result type, missing requirement IDs and an
invalid evidence ID, including guidance to use exact delivered `career-` IDs. Constraint
validation, education/citation guards, complete GAP delivery, snapshot continuity,
route algebra, matching-v1, groups-v1 and Coverage arithmetic retain their contracts.
The fix performs no route/status derivation or semantic-equivalence change.

### Verification and pending live trials

The final offline gate passed 670 checks with 13 skips, including both opt-in scripted
Chromium journeys. Twelve skips require unavailable Make; the other disables live-provider
probing. Ruff, environment-template validation and whitespace checks passed. The new
23-case deterministic suite covers adapter reasons and streaming, normal/truncated
recovery, repeated failure, unchanged iteration limits, report preservation, forced
choice and unsupported-choice fallback, native Anthropic scope, generic-loop behavior,
the historical repair shapes, inventory delivery, snapshot mutation and unsafe recovery.
Existing failure tests now assert the specific missing-submission error and preserve
inspection-result assertions across the additional corrective request.

In-memory mutations that disable recovery or restore old length normalization make the
new regressions fail. No production files were edited for those mutations. Wheel and
source archives build and install offline into temporary targets. Runtime byte checks
verify the packaged adapter, loop, coordinator, evidence, rubric and submission files.
Both installed products pass the same 75 submission, budget, rubric and loop regressions.
The final documentation/distribution checks pass 17 tests.
All local artifacts remain under `/tmp`; this fix deletes or replaces no runtime data,
credentials, provider settings, dependencies or reports.

Five matching-only live trials are prepared with the same fixed profile, JD, canonical
groups, evidence digest, matching-v1 policy and configured OpenRouter model. Automatic
approval review rejected execution because it would send private profile/JD/evidence to
OpenRouter and requires explicit confirmation of that payload and destination in chat.
No trial executed and no user evidence was transmitted. Live structured-submission rate,
provider turns, validator repairs, raw reasons, output tokens and semantic agreement
remain unmeasured pending that confirmation. The prepared runner is
`/tmp/career_submission_live.py`; its results and traces will stay under `/tmp`.
