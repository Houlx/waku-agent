"""Fresh extraction recovers missing submissions without publishing partial output."""
import copy
import json
from types import SimpleNamespace as NS

import pytest

from evals.career import run_scenario
from evals.deterministic.test_career_acceptance import JOBS, RAW, AcceptanceClient
from evals.deterministic.test_career_extraction_failure_diagnosis import JD
from evals.deterministic.test_career_submission import termination
from evals.extraction_helpers import executable_ir
from evals.helpers import response, text_block, tool_block
from waku.config import Settings
from waku.db import connect_career
from waku.loop.models import OpenAICompatClient
from waku.runtime.career_extraction_compiler import build_source_catalog, compile_extraction
from waku.runtime.career_jobs import analyze_job, fresh_extraction, saved_jobs
from waku.runtime.career_requirements import (
    cached_extraction,
)


class ExtractionClient:
    def __init__(self, reasons=('stop',), invalid_recovery=False):
        self.reasons = reasons
        self.invalid_recovery = invalid_recovery
        self.calls = []
        self.messages = NS(create=self.create)

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        n = len(self.calls)
        if n <= len(self.reasons):
            result = response([text_block('UNSUBMITTED ' + 'x' * 40000)])
            result.raw_stop_reason = self.reasons[n - 1]
            result.stop_reason = 'max_tokens' if result.raw_stop_reason in {'length', 'max_tokens'} else 'end_turn'
            result.usage.output_tokens = 8192
            return result
        if n == len(self.reasons) + 1 or self.invalid_recovery:
            return response([tool_block('submit_stage_result', {
                'result': {} if self.invalid_recovery else executable_ir(JD)})], 'tool_use')
        return response([text_block('Complete.')])


def stage(tmp_path, client, limit=10):
    settings = Settings(home=tmp_path, model='offline', max_iterations=limit, max_tokens=8192, otel_endpoint='')
    settings.ensure_home()
    return fresh_extraction(settings, client, JD)


@pytest.mark.parametrize('reason', ['stop', 'end_turn', 'stop_sequence', 'length', 'max_tokens'])
def test_missing_submit_recovers_once_from_stable_inputs(tmp_path, reason):
    client = ExtractionClient((reason,))
    actual = stage(tmp_path, client)
    assert actual == compile_extraction(build_source_catalog(JD), executable_ir(JD))
    assert len(client.calls) == 3
    initial, recovery, final = client.calls
    assert recovery['messages'] == [initial['messages'][0], {'role': 'user', 'content':
        'Submit the complete extraction result now using submit_stage_result. Do not return prose.'}]
    assert 'UNSUBMITTED' not in str(recovery)
    assert final['messages'][0] == initial['messages'][0]
    assert {r['max_tokens'] for r in client.calls} == {8192}
    events = [json.loads(line) for path in (tmp_path / 'traces').glob('*.jsonl')
              for line in path.read_text().splitlines()]
    assert len([e for e in events if e.get('event') == 'submit_only_recovery']) == 1
    first_llm = next(e for e in events if e['type'] == 'llm')
    assert first_llm['raw_stop_reason'] == reason
    assert first_llm['usage']['out'] == 8192
    assert 'UNSUBMITTED' not in json.dumps(events)


@pytest.mark.parametrize('reasons,message', [
    (('stop', 'stop'), 'ended without a valid structured submission'),
    (('length', 'length'), 'output was truncated'),
    (('length', 'stop'), 'output was truncated'),
    (('stop', 'length'), 'output was truncated'),
    (('content_filter',), 'termination: content_filter'),
    (('provider_custom',), 'termination: provider_custom'),
])
def test_repeated_failure_is_explicit_and_keeps_prior_career_data(tmp_path, reasons, message):
    settings = Settings(home=tmp_path, model='offline', max_tokens=8192, otel_endpoint='')
    settings.ensure_home()
    conn = connect_career(tmp_path)
    try:
        run_scenario(conn, settings, AcceptanceClient(JOBS[0]), RAW, JOBS[0], 'English')
        before = saved_jobs(conn)[0]
        profile = [tuple(r) for r in conn.execute('SELECT * FROM career_profile')]
        client = ExtractionClient(reasons)
        with pytest.raises(ValueError, match=message):
            analyze_job(conn, JD, settings, client, before['id'])
        assert len(client.calls) == len(reasons)
        after = saved_jobs(conn)[0]
        for key in ('title', 'report', 'coverage', 'requirements', 'resume'):
            assert after[key] == before[key]
        assert after['status'] == 'failed'
        assert cached_extraction(conn, JD) is None
        assert [tuple(r) for r in conn.execute('SELECT * FROM career_profile')] == profile
        assert 'UNSUBMITTED' not in json.dumps(after)
    finally:
        conn.close()


def test_one_turn_cap_prevents_recovery(tmp_path):
    client = ExtractionClient(('length',))
    with pytest.raises(ValueError, match='output was truncated'):
        stage(tmp_path, client, limit=1)
    assert len(client.calls) == 1


def test_truncation_followed_by_invalid_tools_retains_truncation_error(tmp_path):
    client = ExtractionClient(('length',), invalid_recovery=True)
    with pytest.raises(ValueError, match='output was truncated'):
        stage(tmp_path, client, limit=3)
    assert len(client.calls) == 3


class ForcedExtraction(OpenAICompatClient):
    def __init__(self, reject=False):
        self.requests = []
        self.reject = reject
        self.messages = NS(create=self._create)

    def _call(self, kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        if self.reject and 'tool_choice' in kwargs:
            exc = ValueError('tool_choice not supported')
            exc.status_code = 400
            raise exc
        if kwargs['messages'][-1]['role'] == 'tool':
            return termination('stop')
        result = termination('tool_calls', True)
        result.choices[0].message.tool_calls[0].function.arguments = json.dumps({'result': executable_ir(JD)})
        return result


@pytest.mark.parametrize('reject', [False, True])
def test_extraction_forces_named_submission_with_capability_fallback(tmp_path, reject):
    client = ForcedExtraction(reject)
    assert stage(tmp_path, client)['requirements']
    assert client.requests[0]['tool_choice'] == {
        'type': 'function', 'function': {'name': 'submit_stage_result'}}
    assert all('tool_choice' not in r for r in client.requests[1:])
    assert len(client.requests) == (3 if reject else 2)


def test_native_anthropic_choice_releases_after_acceptance():
    import anthropic

    from waku.runtime.career_submission import ExtractionSubmission

    client = anthropic.Anthropic.__new__(anthropic.Anthropic)
    calls = []
    client.messages = NS(create=lambda **kw: calls.append(kw))
    accepted = []
    submission = ExtractionSubmission(client, lambda: bool(accepted), lambda event: None)
    submission.messages.create(model='offline')
    assert calls[-1]['tool_choice'] == {'type': 'tool', 'name': 'submit_stage_result'}
    accepted.append(True)
    submission.messages.create(model='offline')
    assert calls[-1] == {'model': 'offline'}


def test_recovery_retains_prior_validator_feedback(tmp_path):
    class RepairClient(ExtractionClient):
        def create(self, **kwargs):
            if not self.calls:
                self.calls.append(copy.deepcopy(kwargs))
                return response([tool_block('submit_stage_result', {'result': {}})], 'tool_use')
            return super().create(**kwargs)

    client = RepairClient(('unused', 'length'))
    assert stage(tmp_path, client)['requirements']
    assert len(client.calls) == 4
    before = client.calls[1]['messages']
    recovery = client.calls[2]['messages']
    assert recovery[:-1] == before
    assert recovery[2]['content'][0]['content'].startswith('Error running submit_stage_result:')
    assert 'UNSUBMITTED' not in str(recovery)
