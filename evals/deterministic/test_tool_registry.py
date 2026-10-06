"""Shared tool contracts use synthetic tools without general implementations."""
from waku.tools.registry import Tool, ToolRegistry


def test_schema_contains_only_model_arguments():
    registry = ToolRegistry()
    registry.register(Tool('record', 'Record a value', {
        'type': 'object', 'properties': {'value': {'type': 'string'}}},
        lambda value, _notify: value, wants_notify=True))
    assert registry.schemas() == [{'name': 'record', 'description': 'Record a value',
                                  'input_schema': {'type': 'object', 'properties': {
                                      'value': {'type': 'string'}}}}]


def test_unknown_tool_and_bad_arguments_are_observable_errors():
    registry = ToolRegistry()
    registry.register(Tool('double', 'Double', {}, lambda value: str(value * 2)))
    assert registry.execute('missing', {}) == "Error: unknown tool 'missing'"
    assert registry.execute('double', {'value': 3}) == '6'
    assert registry.execute('double', {}).startswith('Error running double:')


def test_tool_exception_does_not_prevent_a_later_call():
    registry = ToolRegistry()

    def record(value):
        if value == 'bad':
            raise ValueError('invalid value')
        return value

    registry.register(Tool('record', 'Record', {}, record))
    assert registry.execute('record', {'value': 'bad'}) == 'Error running record: invalid value'
    assert registry.execute('record', {'value': 'good'}) == 'good'


def test_progress_observer_is_forwarded_and_has_a_safe_default():
    registry = ToolRegistry()

    def record(value, _notify):
        _notify('progress', {'value': value})
        return 'done'

    registry.register(Tool('record', 'Record', {}, record, wants_notify=True))
    events = []
    assert registry.execute('record', {'value': 7},
                            notify=lambda kind, event: events.append((kind, event))) == 'done'
    assert events == [('progress', {'value': 7})]
    assert registry.execute('record', {'value': 8}) == 'done'
