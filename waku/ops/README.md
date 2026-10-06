# Career operations and retained facades

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
| `dashboard.py` | Transitional old shell, Career delegates, provider facades and trace/SQL/path debugging |
| `browser_agent.py` | Inert singleton facade; general construction refuses |
| `settings_api.py` | Transitional provider display, pins and dormant general toggle settings |
| `commands.py` | Empty workflow discovery and retired command replies |

Batch C1 removes arenas, comparison history, general scoring/judges, coding eval,
brief/gather/triage and their feature consumers. Career live evaluation remains in
`evals/career.py`. The old shell and facades remain isolated for Batch C2.
