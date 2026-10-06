# Status

Career Agent is the sole supported product. This file describes the current code;
the [handoff](career-agent/HANDOFF.md) records verification and historical stages.

**Last updated:** 2026-10-06

## Current Career product

V1, runtime separation and Phase 2 product cutover are implemented. `waku`,
`waku career`, `make run` and `make dashboard` launch Career Agent. Its independent
plain JavaScript frontend supports addressable routes, profile review, saved jobs,
evidence inspection, explicit resume generation and provider Settings.

Career retains its runtime lifecycle, schema, FTS5, provenance, fixed coordinators,
MATCH/PARTIAL/GAP, deterministic coverage and resume grounding. Provider configuration,
model adapters/catalogs, the loop, ToolRegistry and tracing remain shared infrastructure.

## Completed retirement

Phase 3 Batch A removes general-product CLI commands and Make shortcuts.
Batch B1 removes hosted, examples, lab and upstream teaching consumers. Batch B2
removes bundled skills, general judge suites and general-agent eval construction.
Batch C1 removes conversational Session/Memory, general tools, MCP, gateways,
voice, graph workflows, arenas/comparison/general judges and exclusive extras.

Batch C2 removes the old app, dashboard, browser-agent, integration/connect,
settings and command facades, plus transitional Career singleton coordination.
Standalone trace/SQL/path debugging remains in ops/debug.py. General frontend
assets, protected design/font files, dormant configuration fields and pricing
utilities remain for Batch D. Career serves only its independent assets.

Retirement deletes no user data, legacy DB tables, Memory/SOUL files, installed
skills, configuration, credentials, traces or usage ledger. Career-only initialization
leaves existing general rows and FTS tables untouched.

## Verification and limits

CI and `make gate` run retained deterministic evals offline with ruff and the
Career/provider environment-template check. Career live evaluation remains opt-in
and requires a key. Chromium is an opt-in test-only regression.

Windows behavior and OTel exporter shutdown remain unverified here. Historical
upstream provider incident reports remain in Git history; this retirement performs
no live model-availability audit. No new Career feature or hosting replacement is added.

Career styling loads no protected design files, mark or bundled fonts. Retained
brand assets and font notices retain their separate licenses. C2 is implemented; D has not started.
