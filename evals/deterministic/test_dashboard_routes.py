"""Model catalog response remains compatible with provider pickers."""

def test_api_models_returns_picker_contract(monkeypatch):
    """The model picker depends on /api/models returning models and listed."""
    import io
    import json
    import urllib.request

    from waku.ops import catalog

    monkeypatch.setenv("WAKU_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    monkeypatch.delenv("WAKU_MODEL", raising=False)
    monkeypatch.delenv("WAKU_SMALL_MODEL", raising=False)

    def fake_urlopen(req, timeout=10):
        return io.BytesIO(json.dumps(
            {"data": [{"id": "vendor/model:free"}]}
        ).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    catalog._models_cache.clear()

    result = catalog.list_models("openrouter")
    assert result["listed"] is True
    assert isinstance(result["models"], list)
    assert result["models"][0]["id"] == "vendor/model:free"

    catalog._models_cache.clear()
