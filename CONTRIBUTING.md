# Contributing to Career Agent

Career Agent contributions must keep the code clear enough for a newcomer to follow.
[AGENTS.md](AGENTS.md) lists the rules and routes each change to its relevant guide.
The completed V1 product and approved retirement batches define the current scope.

## Code contributions

Career uses the shared provider registry, loop, tool registry, configuration,
database connector and tracing infrastructure. Provider changes belong in
`waku/providers.toml`; run `python scripts/generate_env_example.py --write`
after changing credential or scoped override fields. The
[provider guide](docs/providers-registry.md) documents those fields.

Bundled general-assistant skills are retired. Career does not install or load them.
User-installed skills in runtime homes remain user data and must never be deleted
as part of repository cleanup. Git history preserves retired bundled content.
General gateways, memory, dashboard and arena implementations remain pending
Batch C; their physical presence does not make them supported Career features.

Follow [conventions §2](docs/context/conventions.md#2-how-much-process-a-change-needs)
when deciding how much process a change needs. Behavior changes require offline
deterministic regressions. Keep Career matching, provenance and explicit generation
contracts intact.

## Sending a PR

Run `make gate` and `make lint` before you push. The gate runs offline deterministic
checks and disables live provider probes, even when credentials are configured.
CI checks lint, the Career/provider environment template and the deterministic suite.
[The Career guide](docs/career.md) documents the Chromium regression and explicit
live evaluation. Paid evaluation never replaces deterministic checks.
Packaging must preserve Career assets, installed startup, runtime-data exclusions
and MIT/brand/OFL notices. Describe the checks you ran in the PR.

## Attribution

Contributions retain the upstream MIT copyright in [LICENSE](LICENSE).
Retained brand assets remain under [LICENSE-BRAND](LICENSE-BRAND), and bundled
fonts retain their SIL OFL notices. Do not copy retired hosted implementation into
Career or restore teaching archives into product distributions.
