"""Retained triage components classify safely and inspect synthetic calendars."""

from __future__ import annotations

from evals.helpers import ScriptedClient, response, text_block
from waku.graph.workflows.triage import classify_message, todays_events


class Boom:
    """A client whose every call explodes — for the fail-open cases."""

    def __init__(self):
        from types import SimpleNamespace
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        raise RuntimeError("boom")


def classify(reply_text: str):
    return classify_message(ScriptedClient([response([text_block(reply_text)])]),
                            "small-model", "hello")


def test_classifier_parses_routes_and_fails_open_on_garbage():
    assert classify('{"route": "quick", "reason": "just a greeting"}') == (
        "quick", "just a greeting")
    assert classify('{"route": "full", "reason": "needs calendar"}')[0] == "full"
    # every malformed shape falls open to full — capability over latency
    assert classify("no json here at all")[0] == "full"
    assert classify('{"route": "sideways"}')[0] == "full"
    assert classify_message(Boom(), "small-model", "hi")[0] == "full"


def test_todays_events_reads_the_ics(tmp_path):
    assert todays_events(tmp_path) == "(no calendar)"
    from datetime import datetime
    today = datetime.now().strftime("%Y%m%d")
    (tmp_path / "calendar.ics").write_text(
        "BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:swim\n"
        f"DTSTART:{today}T090000\nEND:VEVENT\nEND:VCALENDAR\n", encoding="utf-8")
    assert todays_events(tmp_path) == "swim"
