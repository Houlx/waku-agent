# Evals and tracing

Career Agent has offline deterministic evals and an explicitly opt-in live evaluator.
[The Career guide](career.md) documents both, including the Chromium regression.
Run `make eval` or `python -m pytest -q evals/deterministic` for offline checks.
CI runs this suite without API keys.

Batch B1 removes hosted deterministic and Docker evals and their Docker workflow.
General backend evals and the existing judge/release-gate implementation remain
until later retirement batches. `make eval-judge` and `make gate` can call models;
do not run them as part of offline retirement verification.

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
