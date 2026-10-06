---
name: pr-worktree
description: Inspect and test a Career Agent pull request in an isolated Git worktree without disturbing the main checkout or user runtime data.
---

Create a separate worktree for the requested revision. Never use `gh pr checkout`
when it would switch the user's active checkout. Keep temporary paths and cleanup
scoped to that worktree.

Use a fresh temporary `WAKU_HOME` for evaluation and browser previews. Do not link
real runtime homes or dotenv files into review worktrees. Synthetic clients and
credentials cover offline tests; real-provider evaluation requires explicit approval.

Start the Career preview on a second port:

```bash
WAKU_HOME="$(mktemp -d /tmp/career-pr-home.XXXXXX)" WAKU_DASHBOARD_PORT=7778 .venv/bin/python -m waku career
```

Install only the retained extras needed by the review: `dev`, `eval` or `tracing`.
Inspect symlinks and untracked files before removing the review worktree. Never
wipe `.waku` or credential files during review cleanup. Follow `AGENTS.md` and
`docs/context/maintainers.md` for checks and external publication boundaries.
