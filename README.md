# Career Agent

Career Agent turns your career history and a pasted job description into a
reviewable requirement report and a grounded tailored resume. It runs locally
and stores saved artifacts in SQLite.

Describe your experience, review the normalized profile, and confirm your facts.
Analyze a job to inspect MATCH, PARTIAL and GAP assessments with source evidence.
JD Requirement Coverage measures support from your confirmed profile; it does
not predict hiring or interviews. Generate a resume only when you choose, then
review its citations, download Markdown or print from your browser.

## Run from this checkout

Use Python 3.11 or later:

```bash
uv venv
uv pip install -e .
uv run waku
```

Open `http://localhost:7777/#overview`. Configure your provider and main model
in Settings. `waku career`, `make run` and `make dashboard` launch the same
Career product. The internal package and compatibility configuration names
remain `waku` and `WAKU_*`.

[The Career guide](docs/career.md) covers provider setup, the profile workflow,
scoring, evidence, exports, limitations and a synthetic demo. Saved profiles,
jobs and resumes survive reload. Unsaved drafts survive navigation within a tab
but do not persist across reload.

## Verify the product

```bash
uv pip install -e '.[dev]'
uv run python -m pytest -q evals/deterministic
```

The [browser regression instructions](docs/career.md#run-the-browser-regression)
use Chromium and scripted model responses with an isolated temporary home.
Real-provider evaluation remains separately opt-in.

## Retained implementation and attribution

Career Agent adapts MIT code from [Waku](https://github.com/ShenSeanChen/waku-agent)
by Sean Chen (ShenSeanChen). This independent Career interface does not imply
upstream endorsement. [LICENSE](LICENSE) retains the upstream copyright notice.
The Career frontend uses independent CSS and system fonts. It loads no Waku
marks, design files or general dashboard scripts.

Career Agent is the sole supported product. Phase 3 retirement is complete.
The repository retains Career code and the shared provider, loop, tool registry,
configuration, SQLite, tracing and debugging infrastructure it uses. Existing
runtime data and configuration remain intact.

[Architecture](docs/architecture.md), [the documentation index](docs/README.md),
[contribution rules](CONTRIBUTING.md) and [the handoff](docs/career-agent/HANDOFF.md)
provide maintenance context. [LICENSE-BRAND](LICENSE-BRAND) covers retained Waku
names; no protected marks, design copies or fonts ship. The retired hosted
Elastic License 2.0 implementation was never copied into the MIT runtime.
