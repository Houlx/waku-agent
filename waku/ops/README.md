# Career operations and debugging

Career uses this package for HTTP serving, provider setup, model catalogs,
pricing and tracing. The offline release gate runs deterministic evals.
[static/README.md](static/README.md) maps the current Career assets and old shell.

| File | Responsibility |
|---|---|
| `career_dashboard.py` | Career HTTP bootstrap, static/API allowlist and owned shutdown |
| `provider_services.py` | Provider readiness, saves, rollback and caller-supplied reload |
| `catalog.py` | Provider model lists, saved pins and default model reads |
| `pricing.py` | Catalog price records and retained usage/pricing utilities |
| `tracing.py`, `show_trace.py` | JSONL/usage recording, optional OTel and terminal trace inspection |
| `release_gate.py` | Offline deterministic checks and local gate report |
| `debug.py` | Standalone trace inspection, read-only SQL and confined path reveal |

Batch C1 removes arenas, comparison history, general scoring/judges, coding eval,
brief/gather/triage and their feature consumers. Career live evaluation remains in
`evals/career.py`. Batch C2 removes the old server and facades. Old static assets await Batch D.
