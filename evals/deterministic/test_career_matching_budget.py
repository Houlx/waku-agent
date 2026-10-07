"""Full matching must leave room for validated output and final confirmation."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from evals.helpers import response, text_block, tool_block
from evals.matching_helpers import scripted_assessment
from waku.config import Settings
from waku.db import connect_career
from waku.runtime.career import action, save_profile
from waku.runtime.career_matching import matching_input_bytes
from waku.runtime.career_requirements import cache_extraction, validate_extraction

FIXTURE = json.loads((Path(__file__).parents[1] / 'fixtures/career_requirement_stability.json').read_text())


class BudgetClient:
    """Reproduce the old lookup-all behavior only when inspection is exposed."""

    def __init__(self, unexpected_tool=None):
        self.calls = []
        self.messages = SimpleNamespace(create=self.create)
        self.unexpected_tool = unexpected_tool

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        data = json.loads(kwargs['messages'][0]['content'].split('\n', 1)[1])
        names = {t['name'] for t in kwargs['tools']}
        if len(self.calls) == 1:
            if self.unexpected_tool:
                args = ({'evidence_id': data['evidence'][0]['evidence_id']}
                        if self.unexpected_tool == 'get_evidence' else {'queries': ['archival']})
                return response([tool_block(self.unexpected_tool, args)], 'tool_use')
            if 'get_evidence' in names:
                return response([tool_block('get_evidence', {'evidence_id': r['evidence_id']},
                                            call_id=r['evidence_id']) for r in data['evidence']], 'tool_use')
        if not any(getattr(b, 'name', None) == 'submit_stage_result'
                   for m in kwargs['messages'] if m['role'] == 'assistant' for b in m['content']):
            reason = 'The confirmed archival record does not establish this material criterion. ' + 'a' * 600
            report = {'assessments': [scripted_assessment(g, 'GAP', [], reason) for g in data['requirements']],
                      'strengths': [], 'gaps': [], 'recommended_focus': []}
            return response([tool_block('submit_stage_result', {'result': report})], 'tool_use')
        return response([text_block('Completed.')])


def budget_world(tmp_path):
    settings = Settings(home=tmp_path, model='offline', otel_endpoint='')
    settings.ensure_home()
    conn = connect_career(tmp_path)
    raw = {'basic': {'Name': 'Morgan Vale'}, 'records': [
        {'source_id': f'archive-{i}', 'type': 'project',
         'text': f'Archival entry {i}. ' + 'x' * 1100} for i in range(8)]}
    action(conn, {'action': 'save_onboarding', 'raw': raw})
    save_profile(conn, {'basic': raw['basic'], 'records': [
        {'source_id': r['source_id'], 'title': r['source_id'], 'description': r['text'], 'skills': []}
        for r in raw['records']]})
    action(conn, {'action': 'confirm'})
    cache_extraction(conn, FIXTURE['jd'], validate_extraction(FIXTURE['extraction'], FIXTURE['jd']))
    return conn, settings


def test_eight_preloaded_records_complete_final_confirmation_under_original_budget(tmp_path):
    conn, settings = budget_world(tmp_path)
    try:
        before = [tuple(r) for r in conn.execute('SELECT * FROM career_evidence ORDER BY evidence_id')]
        client = BudgetClient()
        result = action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, client)
        job = next(j for j in result['jobs'] if j['id'] == result['job_id'])
        assert job['status'] == 'complete' and job['coverage'] == 0
        assert len(client.calls) == 2  # Submission followed by successful final confirmation.
        initial, final = client.calls
        data = json.loads(initial['messages'][0]['content'].split('\n', 1)[1])
        assert data['matching_coverage']['mode'] == 'full'
        expected = {f'career-archive-{i}' for i in range(8)}
        assert {r['evidence_id'] for r in data['evidence']} == expected
        assert all(set(r) == {'evidence_id', 'source_type', 'raw_text', 'normalized'} for r in data['evidence'])
        assert all({t['name'] for t in c['tools']} == {'submit_stage_result'} for c in client.calls)
        sizes = [matching_input_bytes(c['system'], c['messages'], c['tools']) for c in client.calls]
        assert 35000 < sizes[0] <= 48000
        assert sizes[0] < sizes[1] <= 64000
        assert final['messages'][0] == initial['messages'][0]
        outputs = [b['content'] for m in final['messages'] if m['role'] == 'user'
                   and isinstance(m['content'], list) for b in m['content']]
        assert outputs == ['Career proposal validated. The coordinator saves it only after the stage finishes.']
        assert [tuple(r) for r in conn.execute('SELECT * FROM career_evidence ORDER BY evidence_id')] == before
        (tmp_path / 'context-sizes.json').write_text(json.dumps(sizes))
    finally:
        conn.close()


def test_full_mode_refuses_unregistered_retrieval_without_delivering_records(tmp_path):
    for tool in ('get_evidence', 'search_career_evidence'):
        conn, settings = budget_world(tmp_path / tool)
        try:
            client = BudgetClient(unexpected_tool=tool)
            result = action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, client)
            assert result['jobs'][0]['status'] == 'complete'
            second = client.calls[1]['messages'][-1]['content']
            assert [b['content'] for b in second] == [f"Error: unknown tool '{tool}'"]
        finally:
            conn.close()


def test_budget_failure_after_valid_full_submission_preserves_previous_report(tmp_path):
    conn, settings = budget_world(tmp_path)
    try:
        prior = action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, BudgetClient())['jobs'][0]

        class LargeReportClient(BudgetClient):
            def create(self, **kwargs):
                reply = super().create(**kwargs)
                for block in reply.content:
                    if getattr(block, 'name', None) == 'submit_stage_result':
                        block.input['result']['strengths'] = ['a' * 15000, 'b' * 15000]
                return reply

        client = LargeReportClient()
        with pytest.raises(ValueError, match='input budget was exceeded before analysis could complete'):
            action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd'], 'job_id': prior['id']}, settings, client)
        assert len(client.calls) == 1  # The oversized confirmation request never reaches the provider.
        from waku.runtime.career_jobs import saved_jobs

        saved = saved_jobs(conn)[0]
        assert saved['status'] == 'failed'
        assert (saved['report'], saved['requirements'], saved['coverage']) == (
            prior['report'], prior['requirements'], prior['coverage'])
        events = [json.loads(line) for p in (tmp_path / 'traces').glob('*.jsonl') for line in p.read_text().splitlines()]
        submissions = [e for e in events if e['type'] == 'tool' and e['tool'] == 'submit_stage_result']
        assert submissions[-1]['output'].startswith('Career proposal validated.')
    finally:
        conn.close()
