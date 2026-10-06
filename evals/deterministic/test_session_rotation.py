"""Provider switches clear stale model overrides without general assembly."""
import os

from waku.config import load_settings
from waku.loop.models import models_for
from waku.ops import provider_services


def test_provider_switch_resets_stale_model_overrides(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WAKU_PROVIDER", "kimi")
    monkeypatch.setenv("WAKU_MODEL", "kimi-k3")
    monkeypatch.setenv("WAKU_SMALL_MODEL", "kimi-k3")
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-key")
    result = provider_services.apply_provider("gemini", probe=lambda values: None)
    assert result.ok
    assert os.environ["WAKU_PROVIDER"] == "gemini"
    assert os.environ["WAKU_MODEL"] == "gemini-3.1-pro-preview"
    assert os.environ["WAKU_SMALL_MODEL"] == ""
    settings = load_settings()
    assert models_for(settings.provider, settings.model, settings.small_model) == (
        'gemini-3.1-pro-preview', 'gemini-3.1-flash-lite')
