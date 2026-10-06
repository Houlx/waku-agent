# Conventions

How changes get made in waku-agent, for humans and coding agents alike. A rule
that a test can enforce belongs in the test instead of here, and `AGENTS.md`
lists those under "What CI blocks".

## 1. Language

Everything written into the repo is English: code, comments, docs, commit
messages, and issue and PR titles. Conversation can be in any language.

## 2. How much process a change needs

Process scales with how much work is thrown away if the change is wrong, and
with whether it changes something other code depends on. Line count does not
decide it.

| Tier | Examples | What to do |
|---|---|---|
| **Direct** | a bug fix, a copy change, a provider row, a test | Open the PR. The eval and the review are the guardrails. |
| **Short plan** | a tool behind an extra, a gateway, a dashboard view | Comment a 5–10 line plan on the issue before writing code, so a maintainer can point at the right rung early. |
| **Proposal** | a new top-level package; a change to the loop, the memory interfaces, the graph engine or the tool-call contract; a new core tool; anything that adds to every prompt | Write a design doc in `docs/` and get a maintainer's yes before any code. [the Career refactor plan](../career-agent/CAREER_ONLY_REFACTOR_PLAN.md) is the precedent and shows the bar. |

If you are unsure which tier you are in, ask on the issue. That conversation
costs less than a rejected PR.

## 3. Where new capability goes: the footprint ladder

The core is a narrow waist, and capability belongs at the edges. Every tool
Waku registers is sent to the model on every call, so the bar for adding one
is deliberately high. Start at the top of this ladder and move down only when
the rung above cannot do the job:

1. **Extend something that already exists.** A new provider is one table in
   `waku/providers.toml` plus a logo — see
   [providers-registry.md](../providers-registry.md). Career evidence uses its
   existing persistence and retrieval contracts.
2. **Product-specific configuration or documentation.** Career does not load
   bundled general-assistant skills. User-installed runtime skills remain user data.
3. **A CLI and a README.** Waku can already run any program on your machine,
   and a command-line tool with docs beside it costs nothing until it is used.
4. **A tool behind an extra**: `waku/tools/`, with heavy dependencies gated by
   an extra and off by default.
5. **A product communication boundary** requires an approved proposal. Career
   uses its explicit HTTP server; general gateways retired in Batch C1.
6. **A new core tool, as a last resort.** It has to earn its place in every
   prompt.

The ladder has no rung for a new top-level package (like `waku/graph/`). That
is an architecture decision and needs a proposal (§2). The former hosted
deployment is retired from this fork.

## 4. Testing

- `evals/deterministic/` holds 0/1 tests that run offline with no API key.
  Career live evaluation requires an explicit `python -m evals.career --live`.
  General judge suites and hosted Docker evals are retired.
- Every behaviour change gets a deterministic eval. A bug fix adds the case
  that would have caught the bug.
- **Prove the test can fail.** Break the thing it guards, watch it go red, put
  it back. A test that has never failed has never been tested. Say in the PR
  what you broke.
- Three shapes that pass forever, all three found in this repo: comparing a
  value to the constant that sets it (`assert payload["X"] == module.X` holds
  for every value of `X`, zero included); resting on a number that happens to
  equal a library default; and a `pytest.raises(match=...)` needle that matches
  pytest's `tmp_path`, which spells the test's own name, rather than the
  message the code writes. Pin the literal, or assert the behaviour.
- Never assert that a string appears in source. A test that greps for a
  function's name passes whether or not the function works, and keeps passing
  after it is deleted and written again wrong. Import it and call it.
- Write a guard as a closed set: allow what is named, refuse the rest. A guard
  that enumerates the ways to go wrong is a guess about an open set.
- Career routes must preserve the explicit HTTP/static allowlist and rejection
  contracts in `evals/deterministic/test_career_http.py`.
- Run `make gate` and `make lint` before you push. Both the gate and CI run
  offline checks. The gate never enables live provider probes.
- The dashboard's JavaScript has no test runner. Verify a frontend change in a
  browser, as [waku/ops/static/README.md](../../waku/ops/static/README.md)
  describes.

## 5. Git, commits and PRs

- `main` is protected. Every change lands through a PR whose checks pass, and a
  maintainer squash-merges it.
- **A commit message is about the code, not the conversation.** The subject
  says what changed, in under about 70 characters. The body says why, in a few
  lines, and then stops. Leave out who asked for it, what you tried first and
  the story of the session: a stranger reading `git log` wants the change.
  Reasoning worth keeping goes in a code comment next to the code it explains.
- One logical change per commit. A `uv.lock` change only rides along with a
  `pyproject.toml` change.
- A PR says how it was tested: the commands, and what you saw.

## 6. Retired teaching material

Batch B1 removes upstream examples, lab topics, architecture boards and their
builders. Git history preserves this material; do not create a legacy archive.
Product code and evals must never import or read restored `examples/` or `lab/`
material. Distribution checks exclude those retired consumers.

## 7. Dependencies and extras

The default install is the stdlib plus the Anthropic and OpenAI clients. An
optional feature goes behind an extra in `pyproject.toml`, and it fails with an
install hint, not a crash, when the extra is missing. A new core dependency
needs a discussion on an issue first.

## 8. Scope and framing

Career Agent is the supported product. The completed V1 contract and approved
retirement batches govern current work. Batch C1 retires general feature backends.
The remaining general facades and static assets await C2. Preserve
Career behavior and the shared provider, loop, registry and tracing contracts.

Docs name providers neutrally (Anthropic, OpenAI, Gemini, DeepSeek, Kimi, GLM,
OpenRouter): no ranking, and no "open-source versus closed" framing.

## 9. The rulebook: what each file holds and how it grows

| File | Holds | How it grows |
|---|---|---|
| `AGENTS.md` | the routing table, hard rules, what CI blocks, commands | 100 lines at most (test). Push detail down into these files; never split it in two. |
| `docs/context/conventions.md` | process, testing, git, scope | Replace, never append. |
| `docs/architecture.md` | the system, and which file is which box | Present tense. A change that makes a sentence false fixes it in the same PR. |
| `docs/context/design-system.md` | how the dashboard looks, and which primitive to use | Changes with the design files. |
| `docs/context/writing-rules.md` | how we write English for a reader | A rule arrives with the Bad/Good pair that produced it. A rule that two others cover is deleted. |
| `docs/context/gotchas.md` | traps someone already stepped on | The only append-only file. Every entry has a date and a `Retire when:`; 40 entries at most (test). Anyone deletes an entry that no longer holds. |
| `docs/status.md` | what works, what is known-broken, what is deliberately not built | Rewritten whole, never appended; 120 lines at most (test). It holds no decisions. |
| `docs/context/maintainers.md` | how maintainers review, merge and release | Maintainers only. |

A rule that can become a test becomes one: write the test, add a row to "What
CI blocks" in `AGENTS.md`, and delete the sentence here.
