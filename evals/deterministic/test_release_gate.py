"""The release gate never opts into paid model evaluation."""
from types import SimpleNamespace

import pytest

from waku.ops import release_gate


def test_suite_execution_forces_live_provider_probes_off(monkeypatch):
    captured = {}
    monkeypatch.setenv("WAKU_RUN_LIVE_EVALS", "1")

    def run(argv, **kwargs):
        captured.update(argv=argv, **kwargs)
        return SimpleNamespace(returncode=0, stdout="7 passed, 1 skipped\n", stderr="")

    monkeypatch.setattr(release_gate.subprocess, "run", run)
    assert release_gate.run("deterministic") == (0, {"passed": 7, "failed": 0})
    assert captured["env"]["WAKU_RUN_LIVE_EVALS"] == "0"
    assert captured["argv"][-1].endswith("evals/deterministic")


@pytest.mark.parametrize("code", [0, 1])
def test_gate_runs_only_offline_suite_and_preserves_failure_status(monkeypatch, code):
    calls, records = [], []

    def run(suite):
        calls.append(suite)
        return code, {"passed": 0 if code else 7, "failed": code}

    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-configured-key")
    monkeypatch.setattr(release_gate, "run", run)
    monkeypatch.setattr(release_gate, "report", lambda *args: records.append(args))
    if code:
        with pytest.raises(SystemExit) as exc:
            release_gate.main()
        assert exc.value.code == 1
    else:
        release_gate.main()
    assert calls == ["deterministic"]
    assert records[0][:2] == ("fail" if code else "pass", "not run")
