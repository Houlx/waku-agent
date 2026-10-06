"""Shared loop guarantees need no general assistant or conversational memory."""
from evals.helpers import ScriptedClient, response, text_block, tool_block
from waku.loop.agent import run_loop
from waku.tools.registry import Tool, ToolRegistry


def test_plain_answer_ends_after_one_iteration(monkeypatch):
    monkeypatch.setenv("WAKU_GRAPH_WORKFLOWS", "1")
    client = ScriptedClient([response([text_block("Paris.")])])
    result = run_loop(client, "offline", "Answer directly.", [], ToolRegistry())
    assert result.reply == "Paris."
    assert result.iterations == 1
    assert result.tool_calls == []


def test_loop_executes_registered_tool_and_records_result():
    calls = []
    tools = ToolRegistry()
    tools.register(Tool("record", "Record a value", {"type": "object"},
                        lambda value: calls.append(value) or "Recorded."))
    client = ScriptedClient([
        response([tool_block("record", {"value": "example"})], "tool_use"),
        response([text_block("Done.")]),
    ])
    messages = []
    result = run_loop(client, "offline", "Use the tool.", messages, tools)
    assert calls == ["example"]
    assert result.reply == "Done." and result.iterations == 2
    assert result.tool_calls[0]["output"] == "Recorded."
    assert messages[1]["content"][0]["content"] == "Recorded."


def test_iteration_limit_bounds_tool_execution():
    calls = []
    tools = ToolRegistry()
    tools.register(Tool("record", "Record", {}, lambda: calls.append(1) or "ok"))
    client = ScriptedClient([
        response([tool_block("record", {}, f"tu_{i}")], "tool_use") for i in range(4)
    ])
    result = run_loop(client, "offline", "Use the tool.", [], tools, max_iterations=3)
    assert result.iterations == 3 and "iteration limit" in result.reply
    assert len(calls) == 3
    assert len(client._script) == 1


def test_multiple_tools_preserve_call_ids_and_emit_observer_events():
    """Keep loop/observer assertions formerly exercised through graph nodes."""
    tools = ToolRegistry()
    tools.register(Tool('record', 'Record', {}, lambda value: str(value)))
    client = ScriptedClient([
        response([tool_block('record', {'value': 2}, 'first'),
                  tool_block('missing', {}, 'second')], 'tool_use'),
        response([text_block('Finished.')]),
    ])
    messages, events = [], []
    result = run_loop(client, 'offline', 'Use tools.', messages, tools,
                      observer=lambda kind, event: events.append((kind, event)))
    assert result.reply == 'Finished.'
    assert messages[1]['content'] == [
        {'type': 'tool_result', 'tool_use_id': 'first', 'content': '2'},
        {'type': 'tool_result', 'tool_use_id': 'second',
         'content': "Error: unknown tool 'missing'"},
    ]
    assert [kind for kind, _ in events] == ['llm', 'tool', 'tool', 'llm']
    assert [event for kind, event in events if kind == 'tool'] == result.tool_calls
