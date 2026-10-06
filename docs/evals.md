# Evals and tracing

Career Agent has offline deterministic evals and an explicitly opt-in live evaluator.
[The Career guide](career.md) documents both, including the Chromium regression.
Run `make eval` or `python -m pytest -q evals/deterministic` for offline checks.
CI runs this suite without API keys.

Batch B2 removes general judge suites and general-assistant eval construction.
`make gate` runs the remaining deterministic suite offline and forces live provider
probes off. It preserves the existing local report format with the judge marked
"not run". General component checks remain until Batch C retires their backend.
Career live evaluation remains explicitly opt-in; the gate never runs it.

## Shared tracing and usage

Career stages write JSONL traces under the configured home's `traces/` directory.
The permanent `usage.jsonl` ledger records token usage. Career Activity shows stage
status, tool activity, evidence IDs, latency and tokens. Traces omit system prompts
and assistant prose but contain factual tool inputs and results.

Optional OpenTelemetry exporters remain shared infrastructure:

```bash
pip install -e '.[tracing]'
make trace
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 make run
```

Phoenix serves trace waterfalls at localhost:6006. The OTel exporter lifecycle
remains a known limitation recorded in the Career handoff.
