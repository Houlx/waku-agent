# Status

Career Agent is the sole supported product. This file describes the current code;
the [handoff](career-agent/HANDOFF.md) records verification and historical stages.

**Last updated:** 2026-10-06

## Current Career product

V1, runtime separation and Phase 2 product cutover are implemented. `waku`,
`waku career`, `make run` and `make dashboard` launch Career Agent. Its independent
plain JavaScript frontend supports addressable routes, profile review, saved jobs,
evidence inspection, explicit resume generation and provider Settings. The approved
post-v1 UI iteration adds English/Simplified Chinese UI preferences, responsive sidebar
navigation with Recent Jobs, permanent saved-Job deletion and contextual sticky actions.
This iteration is separate from the completed retirement project.

Career retains its runtime lifecycle, schema, FTS5, provenance, fixed coordinators,
MATCH/PARTIAL/GAP, deterministic coverage and resume grounding. Provider configuration,
model adapters/catalogs, the loop, ToolRegistry and tracing remain shared infrastructure.
Matching supplies all active evidence within a checked input budget. Larger profiles
receive a stable inventory and require complete inspection before GAP can validate.
Budget or incomplete-coverage failures preserve any previous report. Requirement
extraction and semantic judgments can still vary across model calls.

## Completed retirement

Phase 3 Batch A removes general-product CLI commands and Make shortcuts.
Batch B1 removes hosted, examples, lab and upstream teaching consumers. Batch B2
removes bundled skills, general judge suites and general-agent eval construction.
Batch C1 removes conversational Session/Memory, general tools, MCP, gateways,
voice, graph workflows, arenas/comparison/general judges and exclusive extras.

Batch C2 removes the old app, dashboard, browser-agent, integration/connect,
settings and command facades, plus transitional Career singleton coordination.
Standalone trace/SQL/path debugging remains in `ops/debug.py`. Batch D removes
general frontend assets, protected design/font files and dormant
configuration fields and unused pricing reports/cache. Catalog price metadata
remains. Career ships only its independent assets.

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

Career styling loads no protected design files, mark or bundled fonts. The upstream
MIT copyright and Waku names notice remain. No brand assets or
fonts ship. Phase 3 productization is complete.
