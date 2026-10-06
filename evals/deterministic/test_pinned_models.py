"""Saved catalog pins preserve model defaults and provider switching."""

from __future__ import annotations

import json
import os

import pytest

from waku.ops import catalog

PROVIDER_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY",
                 "MINIMAX_API_KEY", "MOONSHOT_API_KEY", "ZHIPU_API_KEY", "OPENROUTER_API_KEY",
                 "XAI_API_KEY", "OPENCODE_ZEN_API_KEY", "OPENCODE_GO_API_KEY")


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Isolate catalog defaults and provider writes in a temporary home."""
    monkeypatch.setenv("WAKU_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("")
    for var in PROVIDER_KEYS:
        monkeypatch.delenv(var, raising=False)
    # Provider saves write process environment, so track the selected provider.
    monkeypatch.delenv("WAKU_PROVIDER", raising=False)
    return tmp_path


def test_default_model_for_reads_first_pinned(home):
    assert catalog.default_model_for("kimi") == ""          # nothing pinned yet
    catalog.save_pinned(["kimi:kimi-k3", "kimi:kimi-k2.6"])
    assert catalog.default_model_for("kimi") == "kimi-k3"   # the first one


def test_switching_provider_adopts_its_pinned_default(home, monkeypatch):
    """apply_provider on a provider change uses that provider's pinned default,
    never carrying the previous provider's model across endpoints (the live
    kimi->gemini 404)."""
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("MOONSHOT_API_KEY", "k")
    (home / "models.json").write_text(json.dumps({"pinned": ["kimi:kimi-k3"]}))
    from waku.ops import provider_services

    monkeypatch.setenv("WAKU_PROVIDER", "gemini")
    monkeypatch.setenv("WAKU_MODEL", "gemini-3.5-flash")
    result = provider_services.apply_provider("kimi", probe=lambda values: None)
    assert result.ok
    assert os.getenv("WAKU_PROVIDER") == "kimi"
    assert os.getenv("WAKU_MODEL") == "kimi-k3"  # not gemini's model


def test_no_pins_is_empty_not_error(home):
    assert catalog.pinned_specs() == []
    assert catalog.default_model_for("anthropic") == ""


def test_default_pair_is_flagship_then_fast(home):
    """Each provider ships a flagship + fast default pair for the switcher."""
    from waku.loop.models import PROVIDERS

    assert PROVIDERS["anthropic"].default_pair() == ["claude-opus-4-8", "claude-sonnet-5"]
    assert PROVIDERS["gemini"].default_pair() == ["gemini-3.1-pro-preview", "gemini-3.5-flash"]
    assert PROVIDERS["kimi"].default_pair() == ["kimi-k3", "kimi-k2.7-code-highspeed"]
    # a provider that never set flagship/fast falls back to model/small_model
    assert PROVIDERS["minimax"].default_pair() == ["MiniMax-M3", "MiniMax-M2"]


def test_defaults_apply_before_curation_and_only_for_keyed_providers(home, monkeypatch):
    """No models.json yet -> the switcher shows flagship+fast for providers that
    have a key set, flagship first (so it's the default). Providers without a
    key stay out (you can't use them)."""
    monkeypatch.setenv("MOONSHOT_API_KEY", "k")      # only kimi is keyed
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")     # and anthropic

    pairs = catalog.pinned_specs()
    assert pairs == [
        "anthropic:claude-opus-4-8", "anthropic:claude-sonnet-5",
        "kimi:kimi-k3", "kimi:kimi-k2.7-code-highspeed",
    ]
    assert catalog.default_model_for("kimi") == "kimi-k3"        # flagship is the default
    assert catalog.default_model_for("gemini") == ""            # unkeyed -> no default


def test_pinning_snapshots_defaults_then_diverges(home, monkeypatch):
    """The first pin action persists the computed defaults + the change, so
    later edits don't keep resurrecting defaults."""
    monkeypatch.setenv("MOONSHOT_API_KEY", "k")      # only kimi keyed -> 2 defaults
    catalog.save_pinned([s for s in catalog.pinned_specs() if s != "kimi:kimi-k2.7-code-highspeed"])
    assert (home / "models.json").exists()               # now materialized
    assert catalog.pinned_specs() == ["kimi:kimi-k3"]


def test_known_catalog_providers_can_list(home):
    """Guard against the 'only 2 models' bug: a provider lists models from an
    explicit catalog_url OR a {base_url}/models endpoint (openai-wire only).
    openai has no base_url by default, so it MUST set catalog_url — without it
    the picker fell back to just its 2 hardcoded defaults.

    glm is anthropic-wire with no verified public /models endpoint, so it
    intentionally shows its curated defaults until we wire and verify one."""
    from waku.loop.models import PROVIDERS

    CAN_LIST = {"anthropic", "openai", "openrouter", "gemini", "deepseek", "minimax",
                "kimi", "xai", "opencode_zen", "opencode_go"}
    for name in CAN_LIST:
        prov = PROVIDERS[name]
        can_list = bool(prov.catalog_url) or (prov.kind == "openai" and bool(prov.base_url))
        assert can_list, f"{name} lost its catalog source (add catalog_url)"


def test_list_models_honors_provider_override(home, monkeypatch):
    """The add-row picks a provider first, so list_models(provider) must list
    THAT provider's catalog, not the active one. Cache-seeded to avoid network."""
    import time

    from waku.loop.models import PROVIDERS

    monkeypatch.delenv("MOONSHOT_BASE_URL", raising=False)
    monkeypatch.delenv("WAKU_BASE_URL", raising=False)
    url = PROVIDERS["kimi"].catalog_url
    # cache tuple is (ts, models, error) — None error means a real listing
    monkeypatch.setattr(catalog, "_models_cache", {url: (time.time(), [{"id": "kimi-k3"}], None)})
    out = catalog.list_models("kimi")
    assert out["provider"] == "kimi"
    assert out["listed"] is True
    assert [m["id"] for m in out["models"]] == ["kimi-k3"]
