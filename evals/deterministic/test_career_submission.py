"""Matching submission recovery preserves evidence, validation and the loop cap."""
import copy
import json
from types import SimpleNamespace as NS

import pytest

from evals.deterministic.test_career_matching_budget import FIXTURE, BudgetClient, budget_world
from evals.helpers import response, text_block, tool_block
from evals.matching_helpers import scripted_assessment
from waku.loop.agent import run_loop
from waku.loop.models import OpenAICompatClient, _OpenAIStream
from waku.runtime.career import action
from waku.runtime.career_jobs import saved_jobs
from waku.runtime.career_submission import RECOVERY_INSTRUCTION
from waku.tools.registry import ToolRegistry


def termination(raw, tools=()):
    calls = [NS(id='call', function=NS(name='submit_stage_result', arguments='{}'))] if tools else []
    return NS(choices=[NS(finish_reason=raw, message=NS(content='Visible answer.', tool_calls=calls))],
              usage=NS(prompt_tokens=100, completion_tokens=8192))


@pytest.mark.parametrize('raw,tools,expected', [
    ('stop', False, 'end_turn'), ('tool_calls', True, 'tool_use'),
    ('length', False, 'max_tokens'), ('provider_custom', False, 'end_turn'),
])
def test_adapter_retains_raw_termination_and_text(raw, tools, expected):
    client = OpenAICompatClient.__new__(OpenAICompatClient)
    client._call = lambda kwargs: termination(raw, tools)
    result = client._create(model='offline', messages=[], max_tokens=8192)
    assert result.raw_stop_reason == raw
    assert result.stop_reason == expected
    assert result.content[0].text == 'Visible answer.'
    assert result.usage.output_tokens == 8192


def test_stream_retains_length_termination():
    chunks = [NS(choices=[NS(finish_reason=None, delta=NS(content='Text', tool_calls=[]))], usage=None),
              NS(choices=[NS(finish_reason='length', delta=NS(content=None, tool_calls=[]))],
                 usage=NS(prompt_tokens=3, completion_tokens=8192))]
    stream = _OpenAIStream(NS(_call=lambda *a, **kw: iter(chunks)), {})
    assert list(stream.text_stream) == ['Text']
    result = stream.get_final_message()
    assert (result.raw_stop_reason, result.stop_reason) == ('length', 'max_tokens')
    assert result.content[0].text == 'Text'


class RecoverClient(BudgetClient):
    def __init__(self, raw='stop', repeat=False):
        super().__init__()
        self.raw = raw
        self.repeat = repeat

    def create(self, **kwargs):
        if not self.calls or self.repeat:
            self.calls.append(copy.deepcopy(kwargs))
            result = response([text_block('INVALID LONG COMPLETION ' + 'x' * 40000)])
            result.raw_stop_reason = self.raw
            result.stop_reason = 'max_tokens' if self.raw == 'length' else 'end_turn'
            return result
        return super().create(**kwargs)


@pytest.mark.parametrize('raw', ['stop', 'length', 'max_tokens'])
def test_one_correction_can_submit_without_carrying_invalid_prose(tmp_path, raw):
    conn, settings = budget_world(tmp_path)
    try:
        client = RecoverClient(raw)
        before = [tuple(r) for r in conn.execute('SELECT * FROM career_evidence')]
        result = action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, client)
        job = result['jobs'][0]
        assert job['status'] == 'complete' and job['coverage'] == 0
        assert len(client.calls) == 3
        initial, recovery, final = client.calls
        assert recovery['messages'] == [initial['messages'][0],
                                        {'role': 'user', 'content': RECOVERY_INSTRUCTION}]
        assert 'INVALID LONG COMPLETION' not in str(recovery)
        assert recovery['max_tokens'] == initial['max_tokens'] == 8192
        assert final['messages'][0] == initial['messages'][0]
        assert [tuple(r) for r in conn.execute('SELECT * FROM career_evidence')] == before
        events = [json.loads(line) for p in (tmp_path / 'traces').glob('*.jsonl')
                  for line in p.read_text().splitlines()]
        coverage = [e for e in events if e['type'] == 'career_matching_coverage']
        assert len({e['snapshot_id'] for e in coverage}) == 1
        assert all(e['delivered_evidence_count'] == 8 for e in coverage)
        assert len([e for e in events if e.get('event') == 'submit_only_recovery']) == 1
    finally:
        conn.close()


@pytest.mark.parametrize('raw,message', [('stop', 'ended without a structured submission'),
                                        ('length', 'output was truncated')])
def test_repeated_no_submit_is_bounded_and_preserves_previous_report(tmp_path, raw, message):
    conn, settings = budget_world(tmp_path)
    try:
        prior = action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, BudgetClient())['jobs'][0]
        client = RecoverClient(raw, repeat=True)
        with pytest.raises(ValueError, match=message):
            action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd'], 'job_id': prior['id']}, settings, client)
        assert len(client.calls) == 2
        saved = saved_jobs(conn)[0]
        assert saved['status'] == 'failed'
        assert (saved['report'], saved['requirements'], saved['coverage']) == (
            prior['report'], prior['requirements'], prior['coverage'])
        assert 'INVALID LONG COMPLETION' not in json.dumps(saved['report'])
    finally:
        conn.close()


def test_recovery_does_not_increase_iteration_cap(tmp_path):
    conn, settings = budget_world(tmp_path)
    settings.max_iterations = 1
    try:
        client = RecoverClient('length')
        with pytest.raises(ValueError, match='output was truncated'):
            action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, client)
        assert len(client.calls) == 1
        assert saved_jobs(conn)[0]['report'] is None
    finally:
        conn.close()


def test_unknown_provider_stop_is_explicit_and_not_normal_completion(tmp_path):
    conn, settings = budget_world(tmp_path)
    try:
        client = RecoverClient('content_filter')
        with pytest.raises(ValueError, match='termination: content_filter'):
            action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, client)
        assert len(client.calls) == 1 and saved_jobs(conn)[0]['report'] is None
    finally:
        conn.close()


def test_generic_loop_still_returns_prose_without_recovery():
    client = NS(messages=NS(create=lambda **kw: NS(content=[text_block('Answer.')], stop_reason='max_tokens',
                                                  raw_stop_reason='length',
                                                  usage=NS(input_tokens=1, output_tokens=8192))))
    messages = []
    result = run_loop(client, 'offline', 'Answer.', messages, ToolRegistry())
    assert result.reply == 'Answer.' and result.iterations == 1
    assert len(messages) == 1


class ForcedClient(OpenAICompatClient):
    def __init__(self, reject=False, error_status=400, error_message='tool_choice not supported'):
        self.requests = []
        self.reject = reject
        self.error_status = error_status
        self.error_message = error_message
        self.messages = NS(create=self._create)

    def _call(self, kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        if self.reject and 'tool_choice' in kwargs:
            error = ValueError(self.error_message)
            error.status_code = self.error_status
            raise error
        user_data = kwargs['messages'][1]['content']
        data = json.loads(user_data.split('\n', 1)[1])
        if kwargs['messages'][-1]['role'] == 'tool':
            return termination('stop')
        report = {'assessments': [scripted_assessment(g, 'GAP', [], 'No relevant support.')
                                  for g in data['requirements']],
                  'strengths': [], 'gaps': [], 'recommended_focus': []}
        call = NS(id='call', function=NS(name='submit_stage_result', arguments=json.dumps({'result': report})))
        return NS(choices=[NS(finish_reason='tool_calls', message=NS(content=None, tool_calls=[call]))],
                  usage=NS(prompt_tokens=100, completion_tokens=500))


@pytest.mark.parametrize('reject', [False, True])
def test_full_mode_forces_only_submission_and_releases_confirmation(tmp_path, reject):
    conn, settings = budget_world(tmp_path)
    try:
        client = ForcedClient(reject)
        result = action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, client)
        assert result['jobs'][0]['status'] == 'complete'
        assert client.requests[0]['tool_choice'] == {
            'type': 'function', 'function': {'name': 'submit_stage_result'}}
        assert all('tool_choice' not in r for r in client.requests[1:])
        assert len(client.requests) == (3 if reject else 2)
    finally:
        conn.close()


@pytest.mark.parametrize('status,message', [(401, 'tool_choice not supported'),
                                          (400, 'invalid tool arguments'),
                                          (429, 'tool_choice rate limit')])
def test_force_fallback_does_not_mask_other_provider_errors(tmp_path, status, message):
    conn, settings = budget_world(tmp_path)
    try:
        client = ForcedClient(True, status, message)
        with pytest.raises(ValueError, match=message):
            action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, client)
        assert len(client.requests) == 1
    finally:
        conn.close()


class RepairClient(BudgetClient):
    """Freeze the observed repair shapes using invented records and runtime IDs."""

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        data = json.loads(kwargs['messages'][0]['content'].split('\n', 1)[1])
        assessments = [scripted_assessment(g, 'GAP', [], 'No supporting evidence.') for g in data['requirements']]
        # A positive education assessment supplies a legitimate namespace test.
        assessments[0] = scripted_assessment(data['requirements'][0], 'PARTIAL', ['career-archive-0'],
                                             'A lower degree supplies partial support; major is unmet.')
        report = {'assessments': assessments, 'strengths': [], 'gaps': [], 'recommended_focus': []}
        n = len(self.calls)
        if n == 1:
            value = json.dumps(report) + '\n}'
        elif n == 2:
            value = '{"assessments": [...], "strengths": [...], "gaps": [...], "recommended_focus": [...]}'
        elif n == 3:
            value = dict(report, assessments=assessments[:1])
        elif n == 4:
            value = copy.deepcopy(report)
            for a in value['assessments']:
                a['evidence_ids'] = [e.removeprefix('career-') for e in a['evidence_ids']]
                for c in a['constraint_results']:
                    c['evidence_ids'] = [e.removeprefix('career-') for e in c['evidence_ids']]
        elif n == 5:
            value = report
        else:
            return response([text_block('Completed.')])
        return response([tool_block('submit_stage_result', {'result': value})], 'tool_use')


def test_observed_repair_shapes_receive_actionable_feedback_then_validate(tmp_path):
    conn, settings = budget_world(tmp_path)
    try:
        # Keep synthetic identities and make the cited record education evidence.
        conn.execute("UPDATE career_evidence SET source_type='education' WHERE evidence_id='career-archive-0'")
        conn.commit()
        client = RepairClient()
        result = action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, client)
        assert result['jobs'][0]['status'] == 'complete'
        assert len(client.calls) == 6
        outputs = [m['content'][0]['content'] for m in client.calls[-1]['messages']
                   if m['role'] == 'user' and isinstance(m['content'], list)]
        assert outputs[:2] == [
            ('Error running submit_stage_result: Match report requires an object; received str. '
             'Pass result as an object, not a JSON string.')] * 2
        missing = [g['id'] for g in json.loads(client.calls[0]['messages'][0]['content'].split('\n', 1)[1])['requirements'][1:]]
        assert outputs[2] == ('Error running submit_stage_result: Assess every extracted requirement exactly once. '
                              f'Missing requirement IDs: {sorted(missing)}. Submit all SCORED groups together.')
        assert outputs[3] == ("Error running submit_stage_result: Invalid Career evidence ID 'archive-0'. "
                              'Use exact delivered evidence IDs, including the career- prefix; '
                              'source IDs are not evidence IDs.')
        assert outputs[4].startswith('Career proposal validated.')
    finally:
        conn.close()


def test_inventory_recovery_preserves_tools_and_inspected_delivery(tmp_path, monkeypatch):
    from waku.runtime import career_matching

    conn, settings = budget_world(tmp_path)
    # Force inventory selection while retaining enough room for inspection history.
    monkeypatch.setattr(career_matching, 'MATCHING_TOOL_RESERVE_BYTES', 39000)

    class InventoryClient(BudgetClient):
        def create(self, **kwargs):
            self.calls.append(copy.deepcopy(kwargs))
            data = json.loads(kwargs['messages'][0]['content'].split('\n', 1)[1])
            n = len(self.calls)
            if n == 1:
                assert data['matching_coverage']['mode'] == 'inventory'
                assert 'tool_choice' not in kwargs
                return response([tool_block('get_evidence', {'evidence_id': r['evidence_id']}, r['evidence_id'])
                                 for r in data['evidence_inventory']], 'tool_use')
            if n == 2:
                return response([text_block('Discard this unsubmitted answer.')])
            if n == 3:
                assert 'Discard this' not in str(kwargs)
                tool_messages = [m for m in kwargs['messages'] if isinstance(m['content'], list)]
                assert len(tool_messages) == 2  # Keep lookup calls and their complete records.
                assert len(tool_messages[-1]['content']) == 8
                report = {'assessments': [scripted_assessment(g, 'GAP', [], 'No relevant support.')
                                          for g in data['requirements']],
                          'strengths': [], 'gaps': [], 'recommended_focus': []}
                return response([tool_block('submit_stage_result', {'result': report})], 'tool_use')
            return response([text_block('Complete.')])

    try:
        result = action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, InventoryClient())
        job = result['jobs'][0]
        assert job['status'] == 'complete'
        coverage = next(e for e in job['activity'] if e['stage'] == 'matching coverage')
        assert coverage['delivered_evidence_count'] == coverage['inspected_evidence_count'] == 8
    finally:
        conn.close()


def test_recovery_rejects_changed_evidence_snapshot(tmp_path):
    conn, settings = budget_world(tmp_path)

    class ChangedClient(RecoverClient):
        def create(self, **kwargs):
            result = super().create(**kwargs)
            conn.execute("UPDATE career_evidence SET raw_text='Changed' WHERE evidence_id='career-archive-0'")
            conn.commit()
            return result

    try:
        client = ChangedClient()
        with pytest.raises(ValueError, match='evidence changed during matching'):
            action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, client)
        assert len(client.calls) == 1 and saved_jobs(conn)[0]['report'] is None
    finally:
        conn.close()


def test_native_anthropic_forces_named_tool_only_in_full_mode():
    import anthropic

    from waku.runtime.career_submission import MatchingSubmission

    client = anthropic.Anthropic.__new__(anthropic.Anthropic)
    calls = []
    client.messages = NS(create=lambda **kw: calls.append(kw) or response([text_block('Done.')]))
    captured = []
    coverage = NS(mode='full')
    submission = MatchingSubmission(client, coverage, lambda: bool(captured), lambda event: None)
    submission.messages.create(model='offline')
    assert calls[-1]['tool_choice'] == {'type': 'tool', 'name': 'submit_stage_result'}
    captured.append(True)
    submission.messages.create(model='offline')
    assert calls[-1] == {'model': 'offline'}
    captured.clear()
    coverage.mode = 'inventory'
    submission.messages.create(model='offline')
    assert calls[-1] == {'model': 'offline'}


def test_truncation_recovery_refuses_context_overflow_without_another_call(monkeypatch):
    from waku.runtime import career_submission

    monkeypatch.setattr(career_submission, 'MATCHING_INPUT_BUDGET_BYTES', 1)
    submission = career_submission.MatchingSubmission(
        NS(messages=NS(create=lambda **kw: None)), NS(assert_current=lambda: None),
        lambda: False, lambda event: None)
    submission.system = 'System.'
    submission.tools = []
    messages = [{'role': 'user', 'content': 'Stable inputs.'},
                {'role': 'assistant', 'content': [text_block('Invalid completion.')]}]
    with pytest.raises(ValueError, match='output was truncated'):
        submission.on_no_tools(NS(stop_reason='max_tokens', raw_stop_reason='length'), messages, 9)
    assert not submission.recovered
    assert 'Invalid completion.' not in str(messages)
