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
| `waku/tools/career.py` | Scoped stage submission and FTS5 evidence tools |
| `waku/db.py` | Connection mechanics and Career-only initialization |
| `waku/loop/agent.py`, `loop/models.py`, `tools/registry.py` | Shared loop, provider adapters and tool contract |
| `waku/ops/catalog.py`, `pricing.py`, `tracing.py` | Shared model catalogs, usage pricing and JSONL/optional OTel tracing |
| `waku/ops/static/career/`, `career.html` | Independent Career assets, routes and draft state |

Batch B1 removes hosted, upstream examples, lab topics, architecture boards and
teaching walkthroughs. No Elastic License 2.0 implementation enters the MIT runtime.
Batch C1 removes Session, conversational Memory, general tools, MCP, gateways,
voice, graph workflows and arenas. The tools package contains only Career tools
and the shared registry. The old app refuses general construction before touching
data. The old dashboard retains its static shell, Career delegation, provider
facades and trace/SQL/path debugging; retired feature routes return 404.
Browser-agent, command, connector, settings and integration facades remain for C2.
The integration registry contains only provider rows and optional OTel. General
DB initialization is retired; its transitional connector only opens existing data.
Batch B2 removes bundled skills, procedural build validation and general-agent eval construction. The environment template reads
the provider registry directly, and the release gate runs offline checks.

Retirement performs no schema migration, runtime-data deletion or stored configuration
rewrite. Career initialization preserves existing general rows. Provider/model
behavior and the Career schema and pipeline remain unchanged.
