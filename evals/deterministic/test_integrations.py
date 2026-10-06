"""Deterministic coverage for the shared Connections registry."""

from __future__ import annotations

import socket

import pytest

from waku import integrations
from waku.integrations import IntegrationState, IntegrationStatus
from waku.loop.models import PROVIDERS


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setenv("WAKU_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    integrations._HEALTH = None
    integrations._reset_import_cache()


def test_registry_contract():
    items = integrations.registry()
    # waku-platform is hidden_unless_env: it's in the registry only when its
    # WAKU_PLATFORM_BASE_URL is set (see test_platform_provider.py for the
    # row's own visibility contract) — so the expected count is DERIVED from
    # the live environment, not hardcoded. A hardcoded 24 passes on a laptop
    # and fails inside a tenant container, where the row is visible and the
    # true count is 25.
    visible_providers = {name for name, p in PROVIDERS.items() if p.is_visible()}
    assert len(items) == len(visible_providers) + len(integrations.INTEGRATIONS)
    assert len({item.key for item in items}) == len(items)
    assert {item.key for item in items if item.group == "AI Providers"} == visible_providers
    for item in items:
        assert callable(item.enabled)
        for field in item.env:
            if field.kind is integrations.FieldKind.CHOICE:
                assert field.options
            if field.secret:
                assert field.kind is integrations.FieldKind.TEXT


def test_status_masking_health_persistence_and_invalidation(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret-1234")
    view = next(view for view in integrations.list_integrations() if view.key == "openai")
    # A key is present and nothing required is missing, so this is CONFIGURED —
    # not INSTALLED_BUT_UNCONFIGURED, which the dashboard renders as "needs
    # setup". See test_configured_is_not_confused_with_needing_setup below.
    assert view.status.state is IntegrationState.CONFIGURED
    assert view.fields[0].value == ""
    assert view.fields[0].last4 == "1234"
    integrations.record_health("openai", IntegrationStatus(IntegrationState.CONNECTED))
    integrations._HEALTH = None
    assert next(view for view in integrations.list_integrations() if view.key == "openai").status.state is IntegrationState.CONNECTED
    integrations.invalidate_health("openai")
    after = next(view for view in integrations.list_integrations() if view.key == "openai")
    assert after.status.state is IntegrationState.CONFIGURED
    assert after.status.message == "configured — not tested yet"


def test_otel_probe_checks_configured_collector_tcp_port(monkeypatch):
    captured = {}

    class Connection:
        def close(self):
            captured["closed"] = True

    def connect(address, timeout):
        captured.update(address=address, timeout=timeout)
        return Connection()

    monkeypatch.setattr(socket, "create_connection", connect)

    integrations._otel_probe({"OTEL_EXPORTER_OTLP_ENDPOINT": "localhost:4317"})

    assert captured == {"address": ("localhost", 4317), "timeout": 3, "closed": True}


def test_otel_probe_rejects_endpoint_without_tcp_port():
    with pytest.raises(ValueError, match="host:port"):
        integrations._otel_probe({"OTEL_EXPORTER_OTLP_ENDPOINT": "localhost"})


def test_otel_probe_rejects_endpoint_with_a_signal_path(monkeypatch):
    monkeypatch.setattr(socket, "create_connection", lambda address, timeout: None)

    with pytest.raises(ValueError, match="host:port"):
        integrations._otel_probe({"OTEL_EXPORTER_OTLP_ENDPOINT": "localhost:4317/v1/traces"})


def test_otel_test_connection_records_connected_after_tcp_probe(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
    monkeypatch.setattr(integrations, "_extra_installed", lambda name: True)
    monkeypatch.setattr(integrations, "_otel_probe", lambda values: None)

    view = integrations.test_integration("otel")

    assert view.status.state is IntegrationState.CONNECTED
