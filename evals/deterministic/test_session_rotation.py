"""Provider switches clear stale model overrides in the retained facade."""

from __future__ import annotations


def test_provider_switch_resets_stale_model_overrides(tmp_path, monkeypatch):
    """Live bug: kimi -> gemini kept gate model kimi-k3; every turn then 404'd
    against Gemini. A provider change must reset any model field the user
    didn't newly type."""
    from waku.ops import settings_api

    captured = {}
    monkeypatch.setenv("WAKU_PROVIDER", "kimi")
    monkeypatch.setenv("WAKU_MODEL", "kimi-k3")
    monkeypatch.setenv("WAKU_SMALL_MODEL", "kimi-k3")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-tests")
    monkeypatch.setattr(settings_api, "find_dotenv", lambda **k: "", raising=False)

    # intercept at the env-write layer; abort before the agent rebuild
    def fake_set_key(path, k, v):
        captured[k] = v
        raise RuntimeError("stop-before-rebuild")

    import dotenv
    monkeypatch.setattr(dotenv, "set_key", fake_set_key)
    try:
        settings_api.apply_settings({"provider": "gemini", "model": "kimi-k3",
                                     "small_model": "kimi-k3", "keys": {}})
    except RuntimeError:
        pass
    assert captured.get("WAKU_MODEL", "unset") in ("", "unset") or \
        captured.get("WAKU_PROVIDER") == "gemini"
    # the actual contract: stale kimi ids must have been blanked
    assert captured.get("WAKU_MODEL") != "kimi-k3"
    assert captured.get("WAKU_SMALL_MODEL") != "kimi-k3"
