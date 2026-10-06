"""Retained general dashboard connector checks; its public CLI has retired.

Hosted still consumes the dashboard. Sign-in uses a stub and opens no browser.
"""

from __future__ import annotations

import pytest

from waku.tools import google_calendar


@pytest.fixture
def signed_in(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(google_calendar, "connect", lambda home: calls.append(home) or "stub: connected")
    monkeypatch.setenv("WAKU_HOME", str(tmp_path / "home"))
    return calls


def test_chat_connect_google_runs_in_the_dashboard(signed_in):
    from waku.ops import commands, dashboard

    events = []
    dashboard._run_command(commands.parse("/connect google"), lambda kind, ev: events.append((kind, ev)))
    assert signed_in, "`/connect google` in the chat never reached google_calendar.connect"
    kind, ev = events[-1]
    assert kind == "done" and "stub: connected" in ev["reply"]


def test_retained_calendar_setup_hint():
    hint = google_calendar._SETUP_HINT
    assert "/connect google" in hint and "waku connect google" in hint
    assert "Connections tab" not in hint, "the Connections pop-up has Save and Test, no Connect"
