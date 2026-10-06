"""Dormant disabled-provider configuration and deferred logo assets remain readable."""

from __future__ import annotations

from pathlib import Path

from waku.config import Settings
from waku.loop.models import PROVIDERS


def test_disabled_providers_parsing(monkeypatch):
    monkeypatch.setenv("WAKU_DISABLED_PROVIDERS", "openai, minimax,,xai")
    assert Settings().disabled_providers == frozenset({"openai", "minimax", "xai"})
    monkeypatch.delenv("WAKU_DISABLED_PROVIDERS")
    assert Settings().disabled_providers == frozenset()


def test_every_provider_has_a_logo():
    logos = Path(__file__).resolve().parents[2] / "waku" / "ops" / "static" / "logos"
    missing = [name for name in PROVIDERS if not (logos / f"{name}.svg").is_file()]
    assert not missing, f"providers without a logo: {missing}"
