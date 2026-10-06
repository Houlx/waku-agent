# AGENTS.md — read this first

Career Agent is a local-first workspace for evidence-grounded job analysis and
tailored resumes. It retains Waku provider, loop and tracing infrastructure.
Every change must keep clear, honest code a newcomer can follow.

This file is for everyone who changes the repo, human or coding agent. A test
caps it at 100 lines, so the detail lives in the files it points to.

## Before you… read…

| Before you | Read |
|---|---|
| run Career Agent for the first time | [docs/getting-started.md](docs/getting-started.md) |
| start anything non-trivial | [docs/status.md](docs/status.md): what works and what is known-broken |
| decide how much process a change needs | [conventions §2](docs/context/conventions.md#2-how-much-process-a-change-needs) |
| add Career or provider capability | [conventions §3](docs/context/conventions.md#3-where-new-capability-goes-the-footprint-ladder), the footprint ladder |
| inspect retained general integrations | [docs/integrations.md](docs/integrations.md) |
| touch the loop, runtime or a tool contract | [docs/architecture.md](docs/architecture.md), then conventions §2: it may need a proposal |
| change how the dashboard looks | [docs/context/design-system.md](docs/context/design-system.md) |
| change dashboard JavaScript or CSS | [waku/ops/static/README.md](waku/ops/static/README.md) |
| write a doc, UI copy, a commit message or a SKILL.md | [docs/context/writing-rules.md](docs/context/writing-rules.md) |
| hit something surprising | [docs/context/gotchas.md](docs/context/gotchas.md), and add it if it is missing |

## Hard rules

1. **Never wipe runtime data without asking.** Anything that clears `.waku/`
   (memory, calendar, chat log, traces, the `usage.jsonl` spend ledger),
   including any reset script, needs the user's explicit yes right before
   each run. A yes never carries over to the next run.
2. **Never touch secrets in `waku/`,** the code that runs on a person's own
   machine: no hidden network calls, nothing reads or sends `.env` or keys, and
   nothing runs at install time.
3. **No new default dependency.** Retained defaults are the provider SDKs,
   python-dotenv and Rich. Tracing and test tooling stay behind their existing extras.
4. **Every behaviour change gets a deterministic eval** in `evals/deterministic/`
   (0/1, offline). A bug fix adds the case that would have caught it.
5. **Nothing under `waku/` or `evals/` imports from `examples/` or `lab/`,** and
   `lab/` never ships to PyPI.
6. **No emojis** in the dashboard, CLI output or docs prose.
7. **Waku names retain their separate notice.** `LICENSE-BRAND` still applies.
   Career ships no protected design files, marks or bundled fonts.
   Hosted EL2 implementation is retired. Never copy it into the MIT runtime.
8. **Keep Career styling independent.** Do not restore protected Waku marks,
   copied design files or bundled fonts.
9. **Fix the doc your change makes false,** in the same PR.

## What CI blocks

The `validate` workflow runs on every PR. Each of these fails it:

| Blocked | Checked by |
|---|---|
| a `uv.lock` change without a `pyproject.toml` change | a step in `.github/workflows/validate-skills.yml` |
| a lint error in `waku/`, `evals/`, or `scripts/` | `ruff check` |
| `.env.example` out of step with Career/provider configuration | `scripts/generate_env_example.py` |
| retired static assets or dormant settings | `evals/deterministic/test_d_retirement.py` |
| retired consumers or runtime data in a distribution | `evals/deterministic/test_distribution_boundary.py` |
| a second version number | `evals/deterministic/test_version.py` |
| this file over 100 lines, a broken rulebook link, an unindexed doc, an import from `examples/` or `lab/`, an emoji in the rulebook or README, a module-level name defined twice | `evals/deterministic/test_rulebook.py` |
| any other failing deterministic eval | `pytest evals/deterministic` |

Everything else in the rulebook is checked in review. `make gate` runs offline
checks. Career live evaluation requires an explicit `python -m evals.career --live`.

## Commands

`make run` · `make dashboard` (localhost:7777) · `make trace` (Phoenix, 6006)
`make eval` · `make gate` (offline deterministic) · `make lint` · tests live in `evals/`, not `tests/`

## Maintainers

How maintainers review, merge and release is in
[docs/context/maintainers.md](docs/context/maintainers.md). Contributors can skip it.
