# Career architecture and retained runtime

Career Agent is the sole supported product. `waku` and `waku career` launch its
HTTP server without assembling the general Waku assistant. The
[Career guide](career.md#architecture) describes the stage pipeline; the
[handoff](career-agent/HANDOFF.md) records lifecycle and preservation guarantees.

| File | Responsibility |
|---|---|
| `waku/runtime/career_runtime.py` | Settings, lazy provider client, SQLite connection, execution lock and owned cleanup |
| `waku/ops/career_dashboard.py` | Career HTTP bootstrap and explicit static/API allowlist |
| `waku/ops/provider_services.py` | Provider configuration, masked readiness, replacement and rollback |
| `waku/runtime/career.py`, `career_jobs.py`, `career_resumes.py` | Profile, evidence, requirements, coverage, provenance and resumes |
| `waku/runtime/career_requirements.py` | Canonical scoring groups, eligibility guards, provenance, stable identity and extraction reuse |
| `waku/runtime/career_rubric.py` | Matching-only constraint support, route algebra, reviewed semantic rules and rubric version |
| `waku/runtime/career_submission.py` | Matching-only forced submission and one bounded missing-submit recovery |
| `waku/runtime/career_matching.py` | Checked matching context, confirmed evidence snapshots and server-owned delivery coverage |
| `waku/tools/career.py` | Scoped stage submission and FTS5 evidence tools |
| `waku/db.py` | Connection mechanics and Career-only initialization |
| `waku/loop/agent.py`, `loop/models.py`, `tools/registry.py` | Shared loop, provider adapters and tool contract |
| `waku/ops/catalog.py`, `tracing.py` | Shared model catalogs with price metadata and JSONL/optional OTel tracing |
| `waku/ops/static/career/`, `career.html` | Independent Career assets, routes and draft state |

Phase 3 retirement is complete. Batch D removes dormant configuration and all
general frontend assets. Catalogs preserve returned prices without the unused
pricing cache or spend reporting.

Batch B1 removes hosted, upstream examples, lab topics, architecture boards and
teaching walkthroughs. No Elastic License 2.0 implementation enters the MIT runtime.
Batch C1 removes Session, conversational Memory, general tools, MCP, gateways,
voice, graph workflows and arenas. The tools package contains only Career tools
and the shared registry. Batch C2 removes general application assembly, the old dashboard/browser-agent,
command, connector, settings and integration facades. CareerRuntime has no
transitional singleton or dual-runtime reload hook. Standalone trace/SQL/path
debugging remains in `waku/ops/debug.py`; Career adds no debugging HTTP routes.
General DB initialization and its unused compatibility connector are retired.
Batch B2 removes bundled skills, procedural build validation and general-agent eval construction. The environment template reads
the provider registry directly, and the release gate runs offline checks.

Retirement performs no schema migration, runtime-data deletion or stored configuration
rewrite. Career initialization preserves existing general rows. Provider/model
architecture remains unchanged. An additive `career_requirement_sets` table caches
validated canonical groups by exact JD and policy version. Reports retain excluded
and confirmation clauses, while matching/scoring receive only SCORED groups.
Career matching delivers
all active evidence within its input budget and otherwise requires complete
inspection of an active evidence inventory before accepting GAP.
Full-evidence matching exposes only submission because every active record is already
supplied. Inventory matching retains search, complete-record lookup and submission.

Matching overlays local constraint IDs without changing cached canonical groups.
Reports retain per-constraint support and the matching policy version. Python checks
route completeness and citation consistency before applying the unchanged Coverage formula.

Matching uses an optional no-tool continuation callback within the existing loop cap.
One corrective request removes only the unsubmitted assistant completion, preserving
initial inputs, earlier tools and delivery state. Full mode requests named submission
until validation succeeds; final confirmation releases that requirement. The provider
adapter retains raw termination metadata alongside normalized stop reasons. Ordinary
loop callers retain their existing completion behavior.
