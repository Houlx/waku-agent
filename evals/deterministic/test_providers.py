"""Offline provider adapters and model catalogs use synthetic credentials."""
from __future__ import annotations

import anthropic
import pytest

from waku.config import Settings
from waku.loop.models import PROVIDERS, OpenAICompatClient, get_client


@pytest.fixture(autouse=True)
def fake_keys(monkeypatch):
    for provider in PROVIDERS.values():
        monkeypatch.setenv(provider.key_env, "fake-key-for-tests")
    # a stray custom-endpoint override must not leak into these checks
    monkeypatch.delenv("WAKU_API_KEY", raising=False)
    monkeypatch.delenv("WAKU_BASE_URL", raising=False)
    # waku-platform is hidden_unless_env — give it an endpoint so the
    # per-provider parametrized cases below can build it like any other row.
    # (Its own visibility/scoping contract is covered in
    # test_platform_provider.py.) Also clear its model overrides: on a machine
    # where WAKU_PLATFORM_MODEL happens to be set, test_get_client_builds_the_
    # right_wire's `settings.model == provider.model` would fail for exactly
    # the reason models_now() exists — the override IS meant to win there.
    monkeypatch.setenv("WAKU_PLATFORM_BASE_URL", "http://platform.test")
    monkeypatch.delenv("WAKU_PLATFORM_MODEL", raising=False)
    monkeypatch.delenv("WAKU_PLATFORM_SMALL_MODEL", raising=False)


@pytest.mark.parametrize("name", list(PROVIDERS))
def test_get_client_builds_the_right_wire(name):
    provider = PROVIDERS[name]
    settings = Settings(provider=name, model="", small_model="", api_key="", base_url=None)
    client = get_client(settings)
    expected = anthropic.Anthropic if provider.kind == "anthropic" else OpenAICompatClient
    assert isinstance(client, expected)
    # defaults must be filled in so the loop never sends model=""
    assert settings.model == provider.model
    assert settings.small_model == provider.small_model


@pytest.mark.parametrize("name", list(PROVIDERS))
def test_missing_key_exits_with_the_key_name(name, monkeypatch):
    monkeypatch.delenv(PROVIDERS[name].key_env, raising=False)
    settings = Settings(provider=name, model="", small_model="", api_key="", base_url=None)
    with pytest.raises(SystemExit, match=PROVIDERS[name].key_env):
        get_client(settings)


def test_unknown_provider_names_the_choices():
    settings = Settings(provider="not-a-provider", model="", small_model="",
                        api_key="", base_url=None)
    with pytest.raises(SystemExit, match="openrouter"):
        get_client(settings)



@pytest.mark.parametrize("name", [n for n, p in PROVIDERS.items()
                                  if p.catalog_url is None
                                  and not p.catalog_from_base_url
                                  and (p.kind == "anthropic" or not p.base_url)])
def test_model_listing_falls_back_without_a_catalog(name, monkeypatch):
    """Providers with no listable catalog still give the picker their defaults
    (and never make a network call to get them). waku-platform is excluded:
    catalog_from_base_url means it DOES have a listing endpoint (the proxy),
    covered instead by test_platform_provider.py's own listing test."""
    from waku.ops import catalog

    monkeypatch.setenv("WAKU_PROVIDER", name)
    monkeypatch.delenv("WAKU_MODEL", raising=False)
    monkeypatch.delenv("WAKU_SMALL_MODEL", raising=False)
    result = catalog.list_models()
    assert result["listed"] is False
    ids = [m["id"] for m in result["models"]]
    assert PROVIDERS[name].model in ids
    # the flagship (showcase) model is offered too, not just the loop default
    if PROVIDERS[name].flagship:
        assert PROVIDERS[name].flagship in ids


def test_bad_key_gives_a_fixable_error_not_a_codec_crash(monkeypatch):
    """A key with a stray non-latin-1 char (a mis-pasted arrow/smart-quote) must
    NOT crash the whole catalog with an opaque codec error — it should return a
    fixable message AND still offer the flagship so opus-4.8/fable-5 aren't lost.
    (Regression: a cloned repo whose ANTHROPIC_API_KEY had a '→' dropped the
    picker to two defaults with a 'latin-1 codec' error.)"""
    from waku.ops import catalog

    monkeypatch.setenv("WAKU_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-" + "x" * 100 + "→bad")
    monkeypatch.delenv("WAKU_MODEL", raising=False)
    catalog._models_cache.clear()
    result = catalog.list_models("anthropic")
    assert result["listed"] is False
    assert "ANTHROPIC_API_KEY" in result["error"] and "non-ASCII" in result["error"]
    assert "claude-opus-4-8" in [m["id"] for m in result["models"]]


def test_catalog_url_is_used_with_both_auth_styles(monkeypatch):
    """kimi chats on the anthropic wire but LISTS models on its OpenAI-compat
    endpoint — catalog_url must win, carrying both auth header styles, so the
    picker offers the real menu instead of two hardcoded defaults."""
    import io
    import json
    import urllib.request

    from waku.ops import catalog

    captured = {}

    def fake_urlopen(req, timeout=10):
        captured["url"] = req.full_url
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        body = io.BytesIO(json.dumps(
            {"data": [{"id": "kimi-k3"}, {"id": "kimi-k2.7"}, {"id": "kimi-k1.5"}]}
        ).encode())
        body.__enter__ = lambda *a: body
        body.__exit__ = lambda *a: None
        return body

    monkeypatch.setenv("WAKU_PROVIDER", "kimi")
    monkeypatch.setenv("MOONSHOT_API_KEY", "fake-key-for-tests")
    monkeypatch.delenv("MOONSHOT_BASE_URL", raising=False)
    monkeypatch.delenv("WAKU_BASE_URL", raising=False)
    monkeypatch.delenv("WAKU_MODEL", raising=False)
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    catalog._models_cache.clear()

    result = catalog.list_models()
    assert captured["url"] == PROVIDERS["kimi"].catalog_url
    assert captured["headers"]["authorization"] == "Bearer fake-key-for-tests"
    assert captured["headers"]["x-api-key"] == "fake-key-for-tests"
    assert result["listed"] is True
    assert "kimi-k3" in [m["id"] for m in result["models"]]
    catalog._models_cache.clear()



# --- a model name belongs to the provider it was configured for --------------
# Found live: `.venv/bin/python examples/tiny_memory_agent.py` under
# WAKU_PROVIDER=xai printed "gate failed open (BadRequestError)". WAKU_SMALL_MODEL
# is global, so anthropic's gate model was sent to xAI, which 400s. The retrieval
# gate fails open on error BY DESIGN, so this did not surface as a failure — it
# surfaced as "retrieve", on every turn, for every non-anthropic model in the
# arena. These pin the rule that stops it.

def test_env_model_names_do_not_leak_into_another_provider(monkeypatch):
    from waku.config import Settings
    from waku.loop.models import get_client

    monkeypatch.setenv("WAKU_PROVIDER", "anthropic")
    monkeypatch.setenv("WAKU_MODEL", "claude-fable-5")
    monkeypatch.setenv("WAKU_SMALL_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.setenv("XAI_API_KEY", "test-key")

    settings = Settings(provider="xai")
    get_client(settings)

    assert settings.model == "grok-4", "anthropic's model was sent to xAI"
    assert settings.small_model == "grok-4-fast", (
        "anthropic's gate model was sent to xAI — the gate 400s and fails open, "
        "so this bug reports itself as a healthy 'retrieve' forever"
    )


def test_an_explicit_model_survives_the_provider_switch(monkeypatch):
    """The rule drops INHERITED env values, not deliberate ones. Without this
    the fix would quietly override the arena's own model picker."""
    from waku.config import Settings
    from waku.loop.models import get_client

    monkeypatch.setenv("WAKU_PROVIDER", "anthropic")
    monkeypatch.setenv("WAKU_MODEL", "claude-fable-5")
    monkeypatch.setenv("XAI_API_KEY", "test-key")

    settings = Settings(provider="xai", model="grok-4.3")
    get_client(settings)

    assert settings.model == "grok-4.3"


def test_the_env_still_wins_for_its_own_provider(monkeypatch):
    """The whole point of WAKU_MODEL is to override the default — the fix must
    not break the ordinary single-provider case."""
    from waku.config import Settings
    from waku.loop.models import get_client

    monkeypatch.setenv("WAKU_PROVIDER", "anthropic")
    monkeypatch.setenv("WAKU_MODEL", "claude-fable-5")
    monkeypatch.setenv("WAKU_SMALL_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    settings = Settings(provider="anthropic")
    get_client(settings)

    assert settings.model == "claude-fable-5"
    assert settings.small_model == "claude-haiku-4-5-20251001"


def test_a_foreign_gate_model_is_dropped_even_when_the_env_names_the_provider(monkeypatch):
    """The case that was actually live in Sean's .env: WAKU_PROVIDER=xai with
    WAKU_SMALL_MODEL still holding anthropic's gate model. Scoping by "did the
    caller switch provider" missed this one — the env agreed with itself and was
    still wrong."""
    from waku.config import Settings
    from waku.loop.models import get_client

    monkeypatch.setenv("WAKU_PROVIDER", "xai")
    monkeypatch.setenv("WAKU_SMALL_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.setenv("XAI_API_KEY", "test-key")

    settings = Settings(provider="xai")
    get_client(settings)

    assert settings.small_model == "grok-4-fast"


def test_an_unfamiliar_model_name_is_left_alone(monkeypatch):
    """The check asks "is this positively someone else's?", not "does it look
    like ours?". The second question would silently downgrade any id we don't
    recognise — a preview name, a model released after this code was written."""
    from waku.config import Settings
    from waku.loop.models import get_client

    monkeypatch.setenv("WAKU_PROVIDER", "kimi")
    monkeypatch.setenv("WAKU_SMALL_MODEL", "moonshot-v1-8k")
    monkeypatch.setenv("MOONSHOT_API_KEY", "test-key")

    settings = Settings(provider="kimi")
    get_client(settings)

    assert settings.small_model == "moonshot-v1-8k", "a deliberate choice was overridden"
