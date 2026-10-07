"""Offline whole-journey checks verify plumbing, not real-model quality."""
import copy
import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from evals.career import DIMENSIONS, calibration, evaluate, fixtures, run_scenario
from evals.helpers import ScriptedClient, response, text_block, tool_block
from waku.config import Settings
from waku.db import connect_career as connect
from waku.runtime.career import action
from waku.runtime.career_jobs import EXTRACTION_SCHEMA, run_stage

RAW, JOBS, EXPECTATIONS = fixtures()


@pytest.fixture
def closed_spans(monkeypatch):
    from waku.ops.tracing import Tracer

    class Spans:
        @contextmanager
        def start_as_current_span(self, *args, **kwargs):
            yield object()

    end_turn = Tracer.end_turn

    def finish(tracer, *args):
        assert tracer._span_ctx is None, 'Close the root span before flushing completion.'
        return end_turn(tracer, *args)

    monkeypatch.setattr(Tracer, '_init_otel', lambda self, settings: Spans())
    monkeypatch.setattr(Tracer, 'end_turn', finish)


class AcceptanceClient:
    """Use fixed semantic proposals while exercising the real loop and SQLite tools."""
    def __init__(self, job):
        self.job = job
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        messages = kwargs['messages']
        turn = sum(m['role'] == 'assistant' for m in messages) + 1
        data = json.loads(messages[0]['content'].split('\n', 1)[-1])
        system = kwargs['system']
        if 'Organize this career profile' in system:
            if turn == 1:
                profile = {'basic': data['basic'], 'records': [
                    {'source_id': r['source_id'],
                     'title': next(iter(r.get('fields', {}).values()), r['source_id']),
                     'description': r['text'], 'skills': []} for r in data['records']]}
                return response([tool_block('submit_stage_result', {'profile': profile})], 'tool_use')
        elif 'Extract canonical requirement groups' in system:
            if turn == 1:
                return response([tool_block('submit_stage_result', {'result': {
                    'title': self.job['title'], 'summary': 'Offline fixture.', 'responsibilities': [],
                    'requirements': copy.deepcopy(self.job['requirements'])}})], 'tool_use')
        elif 'Assess each supplied requirement' in system:
            refs = []
            for r, status in zip(data['requirements'], self.job['statuses'], strict=True):
                text = r['text'].casefold()
                refs.append([] if status == 'GAP' else ['career-' + (
                    'rag' if 'retrieval' in text else 'python' if 'python' in text else 'frontend')])
            if turn == 1:
                return response([tool_block('search_career_evidence', {'queries': [
                    'RAG', 'retrieval augmented generation', 'React', 'Node.js', 'Python']})], 'tool_use')
            if turn == 2:
                return response([tool_block('get_evidence', {'evidence_id': eid}, call_id=eid)
                                 for eid in sorted({eid for ids in refs for eid in ids})], 'tool_use')
            if turn == 3:
                assessments = [{'requirement_id': r['id'], 'status': status, 'evidence_ids': ids,
                                'reason': 'Fixture support.' if ids else 'No supplied evidence.'}
                               for r, status, ids in zip(data['requirements'], self.job['statuses'], refs, strict=True)]
                return response([tool_block('submit_stage_result', {'result': {
                    'assessments': assessments, 'strengths': [], 'gaps': EXPECTATIONS[self.job['title']]['gaps'],
                    'recommended_focus': EXPECTATIONS[self.job['title']]['resume_focus']}})], 'tool_use')
        elif 'Write a truthful tailored resume' in system:
            eid = EXPECTATIONS[self.job['title']]['resume_focus'][0]
            if turn == 1:
                return response([tool_block('get_evidence', {'evidence_id': eid})], 'tool_use')
            if turn == 2:
                source = next(r for r in RAW['records'] if 'career-' + r['source_id'] == eid)
                claim = {'text': source['text'], 'evidence_ids': [eid]}
                return response([tool_block('submit_stage_result', {'result': {
                    'summary': [copy.deepcopy(claim)], 'skills': [],
                    'records': [{'evidence_id': eid, 'bullets': [claim]}]}})], 'tool_use')
        return response([text_block('Private assistant scratchpad sentinel; never expose in activity.')])


@pytest.mark.parametrize('job', JOBS, ids=lambda j: j['title'])
def test_complete_fixture_journey(tmp_path, job, closed_spans):
    settings = Settings(home=tmp_path, model='offline', otel_endpoint='')
    settings.ensure_home()
    conn = connect(tmp_path)
    artifacts = run_scenario(conn, settings, AcceptanceClient(job), RAW, job, 'English')
    saved = artifacts['job']
    assert artifacts['raw_profile'] == RAW
    assert saved['coverage'] == job['score']
    assert [r['status'] for r in saved['requirements']] == job['statuses']
    assert saved['resume']['content']['records'][0]['evidence_id'] in EXPECTATIONS[job['title']]['resume_focus']
    assert 'Private assistant scratchpad' not in json.dumps(saved)
    searches = [a for a in saved['activity'] if a.get('tool') == 'search_career_evidence']
    assert 'Queries: RAG; retrieval augmented generation' in searches[0]['result']
    assert 'returned 3 records' in searches[0]['result']
    assert json.loads(conn.execute('SELECT raw_input_json FROM career_profile').fetchone()[0]) == RAW
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not {'facts', 'episodes', 'chat_log'} & tables
    traces = [json.loads(line) for p in (tmp_path / 'traces').glob('*.jsonl') for line in p.read_text().splitlines()]
    assert sum(e['type'] == 'turn_start' for e in traces) == sum(e['type'] == 'turn_end' for e in traces) == 4
    assert 'Private assistant scratchpad' not in json.dumps(traces)
    assert all('system' not in e for e in traces)
    conn.close()


@pytest.mark.parametrize('stage', ['normalization', 'job extraction', 'resume generation'])
@pytest.mark.parametrize('failure', ['provider', 'limit', 'invalid'])
def test_failed_stages_end_trace_without_private_text(tmp_path, stage, failure, closed_spans):
    settings = Settings(home=tmp_path, model='offline', max_iterations=1, otel_endpoint='')
    settings.ensure_home()
    conn = connect(tmp_path)
    action(conn, {'action': 'save_onboarding', 'raw': RAW})
    client = ScriptedClient([] if failure == 'provider' else [response([
        tool_block('submit_stage_result', {'profile': {}, 'result': {}})
        if failure == 'limit' else text_block('Private assistant scratchpad sentinel')], 'tool_use'
        if failure == 'limit' else 'end_turn')])
    with pytest.raises((IndexError, ValueError)):
        if stage == 'normalization':
            action(conn, {'action': 'normalize'}, settings, client)
        else:
            run_stage(settings, client, stage, 'Private system prompt sentinel', {'job_id': 'test-job'},
                      EXTRACTION_SCHEMA, lambda value: (_ for _ in ()).throw(ValueError('Invalid proposal')))
    traces = [json.loads(line) for p in (tmp_path / 'traces').glob('*.jsonl') for line in p.read_text().splitlines()]
    assert traces[0]['type'] == 'turn_start'
    assert traces[-1]['type'] == 'turn_end'
    assert traces[-1]['reply'].endswith('failed')
    assert traces[-1]['iterations'] == (0 if failure == 'provider' else 1)
    assert 'Private assistant scratchpad' not in json.dumps(traces)
    assert 'Private system prompt' not in json.dumps(traces)
    conn.close()


def test_judge_receives_adversarial_claims_as_data(tmp_path):
    settings = Settings(home=tmp_path, model='offline', otel_endpoint='')
    settings.ensure_home()
    verdict = {name: {'passed': name != 'resume_groundedness', 'reason': 'Scripted evaluator verdict.'}
               for name in DIMENSIONS}
    client = ScriptedClient([
        response([tool_block('submit_stage_result', {'result': verdict})], 'tool_use'),
        response([text_block('Reviewed.')])])
    calls = []
    create = client.messages.create

    def record(**kwargs):
        calls.append(kwargs)
        return create(**kwargs)

    client.messages.create = record
    assert not evaluate(settings, client, calibration())['resume_groundedness']['passed']
    assert 'Ignore previous instructions' in calls[0]['messages'][0]['content']
    assert 'Ignore previous instructions' not in calls[0]['system']
    assert {t['name'] for t in calls[0]['tools']} == {'submit_stage_result'}
    # This verifies evaluation plumbing only; a live calibration must establish judge sensitivity.


def test_live_evaluation_requires_explicit_opt_in(tmp_path, monkeypatch):
    from evals.career import main
    from waku.loop import models

    def forbidden(settings):
        raise AssertionError('An offline invocation must not create a provider client.')

    monkeypatch.setattr(models, 'get_client', forbidden)
    monkeypatch.setattr('sys.argv', ['evals.career', '--output', str(tmp_path / 'result.json')])
    with pytest.raises(SystemExit) as stopped:
        main()
    assert stopped.value.code == 2
    assert not (tmp_path / 'result.json').exists()


@pytest.mark.parametrize('inject', [False, True])
def test_live_evaluation_uses_isolated_career_databases(tmp_path, monkeypatch, inject):
    """Exercise the live command with scripted stages and no provider calls."""
    import sqlite3

    from evals import career
    from waku import config
    from waku.loop import models

    original_home = tmp_path / 'original-home'
    live_home = tmp_path / 'career-live'
    live_home.mkdir()
    monkeypatch.setattr(config, 'load_settings', lambda: Settings(
        home=original_home, model='offline', otel_endpoint=''))
    monkeypatch.setattr(career.tempfile, 'mkdtemp', lambda **kwargs: str(live_home))

    class ScenarioClient(AcceptanceClient):
        def create(self, **kwargs):
            if 'Extract canonical requirement groups' in kwargs['system']:
                data = json.loads(kwargs['messages'][0]['content'].split('\n', 1)[1])
                self.job = next(job for job in JOBS if data['jd'].startswith(job['jd']))
            return super().create(**kwargs)

    monkeypatch.setattr(models, 'get_client', lambda settings: ScenarioClient(JOBS[0]))
    connections, homes = [], []

    def scenario(conn, settings, client, raw, job, language):
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'career_profile', 'career_evidence', 'career_evidence_fts',
                'jobs', 'job_requirements', 'job_matches', 'resumes'} <= tables
        assert not {'facts', 'episodes', 'chat_log', 'calendar_events'} & tables
        assert conn.row_factory is sqlite3.Row
        assert conn.execute('PRAGMA busy_timeout').fetchone()[0] == 3000
        assert conn.execute('SELECT count(*) FROM career_profile').fetchone()[0] == 0
        connections.append(conn)
        homes.append(settings.home)
        return run_scenario(conn, settings, client, raw, job, language)

    def judge(settings, client, artifacts):
        return {name: {'passed': name != 'resume_groundedness' or artifacts != calibration(),
                       'reason': 'Scripted evaluator verdict.'} for name in DIMENSIONS}

    monkeypatch.setattr(career, 'run_scenario', scenario)
    monkeypatch.setattr(career, 'evaluate', judge)
    output = tmp_path / 'result.json'
    monkeypatch.setattr('sys.argv', ['evals.career', '--live', '--language', 'Chinese',
                                   '--output', str(output), *(['--inject-jd'] if inject else [])])
    assert career.main() == 0
    result = json.loads(output.read_text())
    assert result['runtime'] == str(live_home)
    assert result['calibration']['passed']
    assert len(set(homes)) == len(JOBS)
    assert all(home.parent == live_home for home in homes)
    assert not original_home.exists()
    for item, job in zip(result['scenarios'], JOBS, strict=True):
        assert item['scenario'] == job['title']
        saved = item['artifacts']['job']
        assert saved['coverage'] == job['score']
        assert saved['resume']['language'] == 'Chinese'
        assert saved['raw_jd'].startswith(job['jd'])
        assert ('Ignore previous instructions' in saved['raw_jd']) == inject
    for conn in connections:
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute('SELECT 1')
