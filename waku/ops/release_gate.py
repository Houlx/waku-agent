"""Offline release gate for Career and retained shared components.

Live Career evaluation remains an explicit `python -m evals.career --live` action.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import UTC
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def run(suite: str) -> tuple[int, dict]:
    """Run a pytest suite; return (exit_code, {passed, failed}). Counts come
    from the -q summary line — zero extra deps; 0/0 on a miss is honest."""
    print(f"\n=== {suite} ===")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(REPO / "evals" / suite)],
        cwd=REPO, capture_output=True, text=True, check=False,
        env={**os.environ, "WAKU_RUN_LIVE_EVALS": "0"},
    )
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    counts = {k: (int(m.group(1)) if (m := re.search(rf"(\d+) {k}", proc.stdout)) else 0)
              for k in ("passed", "failed")}
    return proc.returncode, counts


def report(deterministic: str, judge: str, suites: dict | None = None) -> None:
    """Persist the latest verdict AND append it to the run history."""
    import json
    from datetime import datetime

    from waku.config import load_settings

    settings = load_settings()
    settings.ensure_home()
    record = {
        "deterministic": deterministic,
        "judge": judge,
        "suites": suites or {},
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (settings.home / "eval_report.json").write_text(json.dumps(record), encoding="utf-8")
    with (settings.home / "eval_runs.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def main() -> None:
    suites = {}
    code, suites["deterministic"] = run("deterministic")
    if code:
        report("fail", "not run", suites)
        print("\nGATE CLOSED — deterministic evals failed. Fix before releasing.")
        sys.exit(1)

    report("pass", "not run", suites)

    print("\nGATE OPEN — offline checks passed.")


if __name__ == "__main__":
    main()
