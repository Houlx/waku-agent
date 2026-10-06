# Status

**What is true right now.** Rewritten whole when it changes, never appended to
— a status file that grows is a changelog, and git already is one.

Read this before opening a PR or filing an issue: most of what is already
known-broken is below, and half of it already has a fix in flight.

**Last updated:** 2026-10-06

---

## Current Career product

V1, runtime separation and Phase 2 product cutover are implemented. `waku`,
`waku career`, `make run` and `make dashboard` launch Career Agent. Its independent
plain JavaScript frontend supports addressable routes, profile review, saved jobs,
evidence inspection, explicit resume generation and provider Settings.
Phase 3 Batch A removes all general-product CLI commands and their Make
shortcuts. `waku --help` lists the supported Career commands.

Phase 3 Batch A closes public CLI entrypoints and moves live Career evaluation
to Career-only database initialization. General modules and assets remain in place.
The retained general assistant status below records upstream context; its old
test count is historical. Current verification lives in the Career handoff.

## Retained general assistant

The retained backend contains the loop, memory, tools and both eval tiers.
Its general-product CLI commands no longer start. Batch B1 retires hosted,
examples, lab and upstream teaching consumers.
General backend implementations remain pending Batch C; bundled skills await Batch B2.

**950 deterministic evals pass offline**, with no API key; 60 more are live
evals that skip without one. CI runs the offline tier on every PR along with
ruff, the skills validator, and a check that `.env.example` still matches the
integrations registry.

**0.1.8 is on PyPI and on GitHub Releases.** Pushing a `v*` tag publishes to
both, so the repo's "Latest" release always matches `pip install waku-agent`.

**The dashboard uses the Waku Memory design system**, and
`test_design_system.py` keeps it from drifting. See
[context/design-system.md](context/design-system.md).

## Known broken

Nothing here is a surprise. If you hit one of these, the issue exists.

| What | Where | Fix in flight |
|---|---|---|
| The model picker offers OpenAI models that 404 on use | #137 | #178 |
| GPT-5.6 tool calls fail on Chat Completions | — | #146 |
| OpenCode Zen fails with a rate-limit error | #112 | #113 |
| Google Calendar sign-in has no bundled OAuth client, so `waku connect google` needs your own `~/.waku/credentials.json` | — | — |

**Providers are the recurring theme.** Three of the items above are one
provider or another, and there is no single place that says which providers
are known-good today. Until there is, treat the model picker as a list of
things that *might* work.

## Retirement limits

Batch B1 adds no Career feature or hosting replacement. Career keeps its schema,
pipeline, provider behavior, FTS5, provenance and independent frontend.
Protected Waku design copies and font notices remain with the old dashboard assets.
Git history preserves retired teaching and hosted implementation.

The judge evals remain opt-in and require a key. Chromium is an opt-in test-only
regression. Windows behavior and OTel exporter shutdown remain unverified here.
