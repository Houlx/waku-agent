# docs — what is in here

Start with [AGENTS.md](../AGENTS.md) at the repo root: it routes every kind of
change to the one file that covers it. This folder holds those files, sorted
into four groups.

## Start here

- [getting-started.md](getting-started.md) — install, the first run, and
  provider configuration.
- [status.md](status.md) — what works, what is known-broken, what is
  deliberately not built. Rewritten whole rather than appended to, so it
  cannot become a changelog. Read it before opening a PR.

## The rulebook

| file | what it answers |
|---|---|
| [context/conventions.md](context/conventions.md) | how much process a change needs, where capability goes, testing, git, scope |
| [context/design-system.md](context/design-system.md) | how the dashboard looks, and which primitive to use |
| [context/writing-rules.md](context/writing-rules.md) | how we write docs, UI copy and commit messages |
| [context/gotchas.md](context/gotchas.md) | traps someone already stepped on |
| [context/maintainers.md](context/maintainers.md) | how maintainers review, merge and release; contributors can skip it |

## Reference — how the system works

| file | what it answers |
|---|---|
| [architecture.md](architecture.md) | Career runtime and the retained shared infrastructure |
| [providers-registry.md](providers-registry.md) | adding a model provider: one table in `waku/providers.toml` |
| [integrations.md](integrations.md) | retirement status of general integrations |
| [commands.md](commands.md) | every `waku` and `make` command |
| [evals.md](evals.md) | offline evals, the release gate, traces and spend |

- [career.md](career.md) explains Career setup, architecture, resumes, evaluation and a demo.

## Career Agent project

- [career-agent/PRODUCT_SPEC.md](career-agent/PRODUCT_SPEC.md) holds the approved
  complete product requirements.
- [career-agent/IMPLEMENTATION_PLAN.md](career-agent/IMPLEMENTATION_PLAN.md) holds
  the approved plan and final clarifications.
- [career-agent/HANDOFF.md](career-agent/HANDOFF.md) records current code,
  verification results, and stage authorization.
- [career-agent/CAREER_ONLY_REFACTOR_PLAN.md](career-agent/CAREER_ONLY_REFACTOR_PLAN.md)
  proposes Career-only runtime, backend and frontend cleanup after the MVP.
- [career-agent/PHASE3_RETIREMENT_AUDIT.md](career-agent/PHASE3_RETIREMENT_AUDIT.md)
  records verified consumers, retirement candidates and proposed deletion batches.

## Retired upstream material

Batch B1 removes the former hosted deployment, examples, lab topics, teaching
walkthroughs and architecture boards. Git history preserves their sources.
Retained runtime implementations and bundled skills await later retirement batches.
