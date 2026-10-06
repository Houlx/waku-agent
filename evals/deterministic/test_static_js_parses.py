"""Career JavaScript must parse before any browser can render the workspace."""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

JS_DIR = pathlib.Path(__file__).resolve().parents[2] / "waku" / "ops" / "static" / "career"
SCRIPTS = sorted(JS_DIR.glob("*.js"))


def test_there_are_scripts_to_check():
    """A guard whose glob silently matches nothing passes forever and protects
    nothing. If the frontend moves, this fails and says so."""
    assert SCRIPTS, f"no .js found under {JS_DIR} — did the frontend move?"


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
@pytest.mark.parametrize("script", SCRIPTS, ids=[s.name for s in SCRIPTS])
def test_every_dashboard_script_parses(script: pathlib.Path):
    result = subprocess.run(  # noqa: S603 — fixed argv, path from our own glob
        [shutil.which("node"), "--check", str(script)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, (
        f"{script.name} does not parse — the dashboard will render nothing.\n"
        f"{result.stderr.strip()}"
    )
