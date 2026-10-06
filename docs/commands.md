# Commands

Career Agent is the sole supported product. The installed `waku` command and
`python -m waku` use the same dispatcher.

## waku

| Command | Does |
|---|---|
| `waku` | launches Career at localhost:7777/#overview |
| `waku career` | launches the same Career workspace explicitly |
| `waku --help` or `waku -h` | lists supported commands without starting a server |
| `waku career --help` or `waku career -h` | shows the same help |

Unsupported commands and extra arguments exit with status 1 before runtime startup.
Phase 3 Batch A removes `dashboard`, `chat`, `connections`, `connect`, `voice`,
`telegram`, `discord`, `whatsapp`, `brief`, `gather`, `mcp` and all `skill`
installation/export dispatch. Their backend implementations remain for later
retirement batches, including hosted's direct dashboard consumer.

## make

| Command | Does |
|---|---|
| `make run` | launches Career through the default CLI |
| `make dashboard` | launches Career explicitly; restart after backend changes |
| `make eval` | runs deterministic evals offline |
| `make lint` | runs ruff over runtime, evals, scripts and hosted code |
| `make trace` | opens optional Phoenix trace waterfalls at localhost:6006 |
| `make eval-judge` | runs the retained general judge evals; requires provider calls |
| `make gate` | runs the retained release gate, including general judge evals |

Batch A removes `legacy-dashboard`, `legacy-chat`, `voice`, `telegram`, `discord`,
`whatsapp`, `brief`, `gather`, `shootout` and `shootout-coding`. Trace inspection
remains useful for Career. The existing judge/gate tooling awaits later retirement;
it does not replace the separately opt-in Career evaluation in [career.md](career.md).
Tests live in `evals/`, not `tests/`. [evals.md](evals.md) explains the eval tiers.
