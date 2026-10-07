"""Full evidence delivery closes the diagnosed retrieval-to-false-GAP boundary."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from waku.config import Settings
from waku.db import connect_career
from waku.runtime import career_jobs
from waku.runtime.career import action, save_profile
from waku.runtime.career_matching import MatchingCoverage
from waku.tools.career import get_evidence, search_career_evidence

FIXTURE = json.loads((Path(__file__).parents[1] / 'fixtures/career_matching_diagnostic.json').read_text())


@pytest.fixture
def diagnostic_world(tmp_path):
    settings = Settings(home=tmp_path, model='offline', max_iterations=10, otel_endpoint='')
    (tmp_path / 'traces').mkdir()
    conn = connect_career(tmp_path)
    raw = FIXTURE['raw']
    profile = {'basic': raw['basic'], 'records': [
        {'source_id': r['source_id'], 'title': r['text'], 'description': r['text'], 'skills': []}
        for r in raw['records']]}
    action(conn, {'action': 'save_onboarding', 'raw': raw})
    save_profile(conn, profile)
    action(conn, {'action': 'confirm'})
    yield conn, settings
    conn.close()


def snapshot(conn):
    return {table: sorted([tuple(r) for r in conn.execute(f'SELECT * FROM {table}')], key=repr)
            for table in ('career_profile', 'career_evidence', 'career_evidence_fts_data',
                          'career_evidence_fts_idx', 'career_evidence_fts_docsize', 'career_evidence_fts_config')}


class DiagnosticClient:
    """Script tool choices and decisions; use the real coordinator, loop and SQLite."""

    def __init__(self, route, judge_delivered=False):
        self.route = route
        self.judge_delivered = judge_delivered
        self.calls = []
        self.turns = {'extract': 0, 'match': 0}
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        stage = 'extract' if 'Extract canonical requirement groups' in kwargs['system'] else 'match'
        self.turns[stage] += 1
        turn = self.turns[stage]
        data = json.loads(kwargs['messages'][0]['content'].split('\n', 1)[1])
        name, args = None, None
        if stage == 'extract' and turn == 1:
            name, args = 'submit_stage_result', {'result': {
                'title': 'Education diagnostic', 'summary': '', 'responsibilities': [],
                'requirements': [copy.deepcopy(FIXTURE['requirement'])]}}
        elif stage == 'match':
            if self.route.get('skip_search'):
                turn += 1
            if turn == 1:
                name, args = 'search_career_evidence', {'queries': self.route['queries']}
            elif turn <= 1 + len(self.route['inspect']):
                name, args = 'get_evidence', {'evidence_id': self.route['inspect'][turn - 2]}
            elif turn == 2 + len(self.route['inspect']):
                supporting = [r['evidence_id'] for r in data.get('evidence', [])
                              if r['source_type'] == 'education' and "Master's degree" in r['raw_text']]
                status, cite, reason = self.route['status'], self.route['cite'], self.route['reason']
                if self.judge_delivered and supporting:
                    status, cite, reason = 'MATCH', supporting, 'The supplied education record confirms a master degree.'
                name, args = 'submit_stage_result', {'result': {
                    'assessments': [{'requirement_id': data['requirements'][0]['id'],
                                     'status': status, 'evidence_ids': cite, 'reason': reason}],
                    'strengths': [], 'gaps': [], 'recommended_focus': []}}
        block = (SimpleNamespace(type='tool_use', id=f'{stage}-{turn}', name=name, input=args)
                 if name else SimpleNamespace(type='text', text='Completed.'))
        return SimpleNamespace(content=[block], stop_reason='tool_use' if name else 'end_turn',
                               usage=SimpleNamespace(input_tokens=0, output_tokens=0))


def run_diagnostic(conn, settings, route, job_id=None, judge_delivered=False):
    client = DiagnosticClient(route, judge_delivered)
    result = action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd'], 'job_id': job_id}, settings, client)
    job = next(j for j in result['jobs'] if j['id'] == result['job_id'])
    return job, client


def test_repeated_queries_cannot_hide_degrees_or_mutate_evidence(diagnostic_world, monkeypatch, tmp_path):
    conn, settings = diagnostic_world
    before = snapshot(conn)
    events = []
    real_loop = career_jobs.run_loop

    def observe_loop(*args, **kwargs):
        observer = kwargs['observer']

        def observe(kind, event):
            if kind == 'tool':
                events.append(copy.deepcopy(event))
            observer(kind, event)

        kwargs['observer'] = observe
        return real_loop(*args, **kwargs)

    monkeypatch.setattr(career_jobs, 'run_loop', observe_loop)
    captures = []
    job_id = None
    for _ in range(3):
        for route in FIXTURE['routes']:
            start = len(events)
            job, client = run_diagnostic(conn, settings, route, job_id, judge_delivered=True)
            job_id = job['id']
            assessment = job['requirements'][0]
            assert assessment['status'] == 'MATCH'
            assert assessment['evidence_ids'] == ['career-master']
            assert snapshot(conn) == before
            assert get_evidence(conn, 'career-master')['source_type'] == 'education'
            # Capture query-specific retrieval independently of the combined union.
            captures.append({'requirement': assessment, 'queries': route['queries'],
                             'per_query_ids': [[r['evidence_id'] for r in search_career_evidence(conn, [q])]
                                               for q in route['queries']],
                             'tool_events': events[start:]})
            match_calls = [c for c in client.calls if 'Assess each supplied' in c['system']]
            initial = json.loads(match_calls[0]['messages'][0]['content'].split('\n', 1)[1])
            assert initial['matching_coverage'] == {
                'mode': 'full', 'required_coverage_ids': ['career-bachelor', 'career-master', 'career-react']}
            assert [r['evidence_id'] for r in initial['evidence']] == ['career-bachelor', 'career-master', 'career-react']
            for record in initial['evidence']:
                assert set(record) == {'evidence_id', 'source_type', 'raw_text', 'normalized'}
                original = get_evidence(conn, record['evidence_id'])
                assert record == {k: original[k] for k in record}
            previous_results = []
            for call in match_calls:
                outputs = [b['content'] for m in call['messages'] if m['role'] == 'user'
                           and isinstance(m['content'], list) for b in m['content']]
                assert outputs[:len(previous_results)] == previous_results
                previous_results = outputs
    (tmp_path / 'diagnostic.json').write_text(json.dumps(captures, ensure_ascii=False, indent=2))


def test_fts_integrity_and_repeatability(diagnostic_world):
    conn, _ = diagnostic_world
    # rank=1 checks the actual index against external content, unlike SELECT * FROM FTS.
    conn.execute("INSERT INTO career_evidence_fts(career_evidence_fts,rank) VALUES('integrity-check',1)")
    for row in conn.execute('SELECT * FROM career_evidence'):
        assert row['evidence_id'] == 'career-' + row['source_id']
        assert row['active'] == 1
        assert row['search_text'] == row['raw_text'] + '\n' + row['normalized_json']
        assert json.loads(row['normalized_json'])['source_id'] == row['source_id']
    expected = {
        "Master's degree": ['career-master'], "Master's degree required": [],
        '硕士': ['career-master'], '大学': [], '示例大学': ['career-master'],
        'React': ['career-react'], 'degree': ['career-bachelor', 'career-master']}
    for query, ids in expected.items():
        for _ in range(20):
            assert [r['evidence_id'] for r in search_career_evidence(conn, [query])] == ids
    # Global Top-K can discard a unique category candidate after union/deduplication.
    queries = ['degree', 'Master', 'React']
    union = search_career_evidence(conn, queries, 20)
    limited = search_career_evidence(conn, queries, 1)
    assert {r['evidence_id'] for r in union} == {'career-bachelor', 'career-master', 'career-react'}
    assert len(limited) == 1
    assert search_career_evidence(conn, ['Master', 'Master']) == search_career_evidence(conn, ['Master'])
    assert search_career_evidence(conn, list(reversed(queries)), 20) == union
    with conn:
        conn.execute("UPDATE career_evidence SET active=0 WHERE evidence_id='career-master'")
    assert search_career_evidence(conn, ['Master', '硕士']) == []
    with conn:
        conn.execute("UPDATE career_evidence SET search_text='replacement',active=1 WHERE evidence_id='career-master'")
    assert search_career_evidence(conn, ['Master']) == []
    assert [r['evidence_id'] for r in search_career_evidence(conn, ['replacement'])] == ['career-master']
    with conn:
        conn.execute("DELETE FROM career_evidence WHERE evidence_id='career-master'")
    assert search_career_evidence(conn, ['replacement']) == []
    conn.execute("INSERT INTO career_evidence_fts(career_evidence_fts,rank) VALUES('integrity-check',1)")


@pytest.mark.parametrize('status', ['MATCH', 'PARTIAL'])
@pytest.mark.parametrize('source_type', ['project', 'work'])
def test_matching_validator_rejects_unrelated_project_as_education_support(diagnostic_world, status, source_type):
    conn, _ = diagnostic_world
    with conn:
        conn.execute("UPDATE career_evidence SET source_type=? WHERE evidence_id='career-react'", (source_type,))
    result = {'assessments': [{'requirement_id': 'education', 'status': status,
                             'evidence_ids': ['career-react'], 'reason': 'Incorrect education support.'}],
              'strengths': [], 'gaps': [], 'recommended_focus': []}
    with pytest.raises(ValueError, match='require education evidence'):
        career_jobs.validate_match(result, [{'id': 'education', 'eligibility': 'SCORED', 'category': 'education'}], conn,
                                   {'career-react': get_evidence(conn, 'career-react')}, [['React']])


def test_rank_ties_and_default_top_k_are_stable(diagnostic_world):
    conn, _ = diagnostic_world
    record = json.dumps({'source_id': 'tie', 'title': 'Tie', 'description': 'tieprobe', 'skills': []})
    with conn:
        for i in reversed(range(12)):
            conn.execute('INSERT INTO career_evidence(evidence_id,source_id,source_type,raw_text,'
                         'normalized_json,search_text) VALUES(?,?,?,?,?,?)',
                         (f'career-tie-{i:02}', f'tie-{i:02}', 'project', 'tieprobe', record, 'tieprobe'))
    ranks = [r[0] for r in conn.execute('SELECT bm25(career_evidence_fts) FROM career_evidence_fts '
                                       "WHERE career_evidence_fts MATCH 'tieprobe'")]
    assert len(ranks) == 12 and len(set(ranks)) == 1
    for _ in range(20):
        assert [r['evidence_id'] for r in search_career_evidence(conn, ['tieprobe'])] == [
            f'career-tie-{i:02}' for i in range(8)]
    assert len(search_career_evidence(conn, ['tieprobe'], 20)) == 12


def test_education_gap_requires_complete_education_coverage(diagnostic_world):
    conn, _ = diagnostic_world
    result = {'assessments': [{'requirement_id': 'education', 'status': 'GAP',
                             'evidence_ids': [], 'reason': 'The search returned nothing.'}],
              'strengths': [], 'gaps': [], 'recommended_focus': []}
    # No inspected education records means the coordinator must reject this claim.
    with pytest.raises(ValueError, match='server-owned Career evidence coverage'):
        career_jobs.validate_match(result, [{'id': 'education', 'eligibility': 'SCORED', 'category': 'education'}], conn,
                                   {}, [["Master's degree required"]])


def enlarge_profile(conn, padding=8500, masters=True):
    raw = copy.deepcopy(FIXTURE['raw'])
    if not masters:
        raw['records'][1]['text'] = 'Diploma in Information Systems.'
    for record in raw['records']:
        record['text'] += ' ' + 'x' * padding
    profile = {'basic': raw['basic'], 'records': [
        {'source_id': r['source_id'], 'title': r['source_id'], 'description': r['text'], 'skills': []}
        for r in raw['records']]}
    action(conn, {'action': 'save_onboarding', 'raw': raw})
    save_profile(conn, profile)
    action(conn, {'action': 'confirm'})


def gap_route(inspect=(), **extra):
    return dict(queries=["Master's degree required"], inspect=list(inspect), status='GAP', cite=[],
                reason='The complete evidence has no master degree support.', **extra)


def test_full_evidence_can_be_cited_without_search_or_duplicate_inspection(diagnostic_world):
    conn, settings = diagnostic_world
    route = dict(FIXTURE['routes'][3], inspect=[], skip_search=True)
    job, client = run_diagnostic(conn, settings, route)
    assert job['requirements'][0]['status'] == 'MATCH'
    assert job['report']['evidence']['career-master'] == get_evidence(conn, 'career-master')
    calls = [c for c in client.calls if 'Assess each supplied' in c['system']]
    assert len(calls) == 2
    assert all(len(c['messages']) in (1, 3) for c in calls)
    assert not any(a.get('tool') in {'get_evidence', 'search_career_evidence'} for a in job['activity'])


def test_complete_delivery_permits_genuine_gap_without_search(diagnostic_world):
    conn, settings = diagnostic_world
    enlarge_profile(conn, padding=0, masters=False)
    before = snapshot(conn)
    job, _ = run_diagnostic(conn, settings, gap_route(skip_search=True))
    assert job['requirements'][0]['status'] == 'GAP'
    assert job['coverage'] == 0
    assert snapshot(conn) == before


@pytest.mark.parametrize('category,text', [
    ('education', "Master's degree required"),
    ('unrecognized_category', "Master's degree required"),
    ('education', "Master's degree and work experience required"),
    ('education/experience', "Master's degree and work experience required"),
])
def test_inventory_requires_all_candidates_for_unknown_and_mixed_requirements(
        diagnostic_world, monkeypatch, category, text):
    conn, _ = diagnostic_world
    enlarge_profile(conn)
    monkeypatch.setitem(FIXTURE, 'jd', text)
    monkeypatch.setitem(FIXTURE['requirement'], 'text', text)
    monkeypatch.setitem(FIXTURE['requirement'], 'source_excerpt', text)
    monkeypatch.setitem(FIXTURE['requirement'], 'category', category)
    before = snapshot(conn)
    collected = {}
    coverage = MatchingCoverage(conn, collected)
    requirement = {'id': 'education', 'text': text, 'category': category, 'eligibility': 'SCORED'}
    messages = coverage.prepare('Match diagnostic', {'requirements': [requirement]}, [])
    data = json.loads(messages[0]['content'].split('\n', 1)[1])
    assert data['matching_coverage'] == {
        'mode': 'inventory', 'required_coverage_ids': ['career-bachelor', 'career-master', 'career-react']}
    assert 'evidence' not in data
    assert [r['evidence_id'] for r in data['evidence_inventory']] == ['career-bachelor', 'career-master', 'career-react']
    coverage.delivered_ids.add('career-bachelor')
    with pytest.raises(ValueError, match='GAP requires complete Career evidence coverage'):
        career_jobs.validate_match({'assessments': [{'requirement_id': 'education', 'status': 'GAP',
            'evidence_ids': [], 'reason': 'No relevant support.'}], 'strengths': [], 'gaps': [],
            'recommended_focus': []}, [requirement], conn, collected, [], coverage)
    assert snapshot(conn) == before


def test_inventory_can_complete_inspection_and_accept_genuine_gap(diagnostic_world):
    conn, settings = diagnostic_world
    enlarge_profile(conn, masters=False)
    before = snapshot(conn)
    job, _ = run_diagnostic(conn, settings, gap_route(['career-bachelor', 'career-master', 'career-react']))
    coverage = next(a for a in job['activity'] if a['stage'] == 'matching coverage')
    assert coverage['mode'] == 'inventory'
    assert coverage['active_evidence_count'] == coverage['delivered_evidence_count'] == 3
    assert coverage['deterministically_delivered_count'] == 0
    assert coverage['inspected_evidence_count'] == 3
    assert job['requirements'][0]['status'] == 'GAP'
    assert snapshot(conn) == before


def test_input_budget_never_truncates_or_overwrites_previous_report(diagnostic_world):
    conn, settings = diagnostic_world
    job, _ = run_diagnostic(conn, settings, FIXTURE['routes'][3])
    enlarge_profile(conn, padding=70000)
    before = snapshot(conn)
    with pytest.raises(ValueError, match='input budget exceeded during evidence inspection'):
        run_diagnostic(conn, settings, gap_route(['career-master']), job['id'])
    saved = career_jobs.saved_jobs(conn)[0]
    assert saved['report'] == job['report'] and saved['requirements'] == job['requirements']
    assert saved['status'] == 'failed' and saved['outdated']
    assert snapshot(conn) == before
    events = [json.loads(line) for p in (settings.home / 'traces').glob('*.jsonl') for line in p.read_text().splitlines()]
    assert events[-1]['type'] == 'turn_end' and events[-1]['reply'] == 'Career evidence matching failed'


def test_inventory_itself_must_fit_before_matching_provider_is_called(diagnostic_world):
    conn, settings = diagnostic_world
    with conn:
        for row in conn.execute('SELECT evidence_id,normalized_json FROM career_evidence').fetchall():
            record = json.loads(row['normalized_json'])
            record['title'] = '界' * 30000
            conn.execute('UPDATE career_evidence SET normalized_json=? WHERE evidence_id=?',
                         (json.dumps(record, ensure_ascii=False), row['evidence_id']))
    client = DiagnosticClient(gap_route())
    with pytest.raises(ValueError, match='inventory exceeds the input budget'):
        action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, client)
    assert client.turns == {'extract': 2, 'match': 0}


def test_coverage_activity_and_trace_metadata_do_not_duplicate_profile(diagnostic_world):
    conn, settings = diagnostic_world
    job, _ = run_diagnostic(conn, settings, FIXTURE['routes'][0], judge_delivered=True)
    coverage = next(a for a in job['activity'] if a['stage'] == 'matching coverage')
    assert coverage['mode'] == 'full'
    assert coverage['active_evidence_count'] == coverage['deterministically_delivered_count'] == 3
    assert coverage['delivered_evidence_count'] == 3
    citations = next(a for a in job['activity'] if a['stage'] == 'matching citations')
    assert citations['evidence_ids'] == ['career-master']
    assert any(a.get('tool') == 'search_career_evidence' and 'React' in a['result'] for a in job['activity'])
    events = [json.loads(line) for p in (settings.home / 'traces').glob('*.jsonl') for line in p.read_text().splitlines()]
    metadata = [e for e in events if e['type'] in {'career_matching_coverage', 'career_matching_citations'}]
    assert metadata and all(e['career_job_id'] == job['id'] for e in metadata)
    assert metadata[0]['mode'] == 'full' and metadata[0]['deterministically_delivered_count'] == 3
    assert metadata[-1]['evidence_ids'] == ['career-master']
    assert "Bachelor's degree" not in json.dumps(metadata)


def prepared_coverage(conn):
    coverage = MatchingCoverage(conn, {})
    messages = coverage.prepare('Matching test.', {'requirements': [{'id': 'degree'}]}, [])
    return coverage, {'system': 'Matching test.', 'messages': messages, 'tools': []}


def echo_client():
    return SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(content=[])))


def test_inventory_and_executed_tools_do_not_establish_delivery(diagnostic_world, monkeypatch):
    conn, _ = diagnostic_world
    enlarge_profile(conn, padding=12000)
    coverage, request = prepared_coverage(conn)
    assert coverage.mode == 'inventory'
    # Even a complete collected dictionary cannot substitute for delivered tool results.
    coverage.collected.update(coverage.records)
    coverage.client(echo_client(), lambda metadata: None).messages.create(**request)
    assert not coverage.delivered_ids
    with pytest.raises(ValueError, match='GAP requires complete Career evidence coverage'):
        coverage.require_complete()
    # A result appended after a provider call counts only on the next request.
    for record in coverage.records.values():
        request['messages'].append({'role': 'user', 'content': [
            {'type': 'tool_result', 'tool_use_id': record['evidence_id'], 'content': json.dumps(record)}]})
    assert not coverage.delivered_ids
    # Increase the test input cap so this test isolates delivery accounting.
    from waku.runtime import career_matching
    monkeypatch.setattr(career_matching, 'MATCHING_INPUT_BUDGET_BYTES', 100000)
    coverage.client(echo_client(), lambda metadata: None).messages.create(**request)
    assert coverage.delivered_ids == {'career-bachelor', 'career-master', 'career-react'}
    coverage.require_complete()


@pytest.mark.parametrize('mutation', ['raw', 'normalized', 'active', 'profile', 'unconfirmed'])
def test_coverage_is_bound_to_confirmed_snapshot(diagnostic_world, mutation):
    conn, _ = diagnostic_world
    coverage, request = prepared_coverage(conn)
    coverage.client(echo_client(), lambda metadata: None).messages.create(**request)
    with conn:
        if mutation == 'raw':
            conn.execute("UPDATE career_evidence SET raw_text='Changed original' WHERE evidence_id='career-master'")
        elif mutation == 'normalized':
            record = json.loads(conn.execute("SELECT normalized_json FROM career_evidence WHERE evidence_id='career-master'").fetchone()[0])
            record['description'] = 'Changed normalized facts'
            conn.execute("UPDATE career_evidence SET normalized_json=? WHERE evidence_id='career-master'", (json.dumps(record),))
        elif mutation == 'active':
            conn.execute("UPDATE career_evidence SET active=0 WHERE evidence_id='career-master'")
        elif mutation == 'profile':
            conn.execute("UPDATE career_profile SET user_edits_json='{} '")
        else:
            conn.execute('UPDATE career_profile SET confirmed=0')
    with pytest.raises(ValueError, match='changed during matching|Confirm your Career Profile'):
        coverage.require_complete()


def test_provider_failure_does_not_claim_delivery(diagnostic_world):
    conn, _ = diagnostic_world
    coverage, request = prepared_coverage(conn)

    def fail(**kwargs):
        raise RuntimeError('Offline simulated provider failure')

    client = SimpleNamespace(messages=SimpleNamespace(create=fail))
    with pytest.raises(RuntimeError, match='simulated provider failure'):
        coverage.client(client, lambda metadata: None).messages.create(**request)
    assert coverage.delivered_ids == set() and coverage.collected == {}


def test_input_budget_checks_utf8_bytes_and_exact_boundary(diagnostic_world, monkeypatch):
    from waku.runtime import career_matching

    conn, _ = diagnostic_world
    coverage, request = prepared_coverage(conn)
    request['system'] += ' 中文事实'
    size = career_matching.matching_input_bytes(**request)
    character_count = len(json.dumps(request, ensure_ascii=False))
    assert size > character_count
    calls = []
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: calls.append(kwargs)))
    monkeypatch.setattr(career_matching, 'MATCHING_INPUT_BUDGET_BYTES', size)
    coverage.client(client, lambda metadata: None).messages.create(**request)
    assert len(calls) == 1
    monkeypatch.setattr(career_matching, 'MATCHING_INPUT_BUDGET_BYTES', size - 1)
    with pytest.raises(ValueError, match='input budget exceeded'):
        coverage.client(client, lambda metadata: None).messages.create(**request)
    assert len(calls) == 1


def test_openai_adapter_preserves_full_context_and_successive_tool_results(diagnostic_world):
    from waku.loop.models import OpenAICompatClient

    conn, settings = diagnostic_world
    _, client = run_diagnostic(conn, settings, FIXTURE['routes'][0], judge_delivered=True)
    request = client.calls[-1]
    # Calling the conversion method requires no SDK client, keys or network.
    adapter = object.__new__(OpenAICompatClient)
    converted = adapter._to_openai(model='offline', system=request['system'], messages=request['messages'],
                                   tools=request['tools'], max_tokens=4096)
    expected = [b['content'] for m in request['messages'] if m['role'] == 'user'
                and isinstance(m['content'], list) for b in m['content']]
    assert len(expected) == 3  # supplemental search, evidence inspection, validated submission
    assert [m['content'] for m in converted['messages'] if m['role'] == 'tool'] == expected
    initial = next(m['content'] for m in converted['messages'] if m['role'] == 'user')
    assert 'career-master' in initial and "Master's degree" in initial


def test_education_guard_does_not_misclassify_social_work_degree():
    from waku.runtime.career_matching import pure_education_requirement

    assert pure_education_requirement({'category': 'education', 'text': "Master's degree in social work required"})
    assert not pure_education_requirement({'category': 'education', 'text': 'Degree or equivalent work experience'})
    assert not pure_education_requirement({'category': 'soft_skill', 'text': 'High degree of autonomy required'})


def test_same_response_inspection_cannot_approve_unseen_inventory_gap(diagnostic_world):
    conn, settings = diagnostic_world
    enlarge_profile(conn)

    class SameResponseClient(DiagnosticClient):
        def create(self, **kwargs):
            if 'Extract canonical requirement groups' in kwargs['system']:
                return super().create(**kwargs)
            self.calls.append(copy.deepcopy(kwargs))
            self.turns['match'] += 1
            if self.turns['match'] != 1:
                return SimpleNamespace(content=[SimpleNamespace(type='text', text='Completed.')],
                                       stop_reason='end_turn', usage=SimpleNamespace(input_tokens=0, output_tokens=0))
            data = json.loads(kwargs['messages'][0]['content'].split('\n', 1)[1])
            blocks = [SimpleNamespace(type='tool_use', id=eid, name='get_evidence', input={'evidence_id': eid})
                      for eid in ('career-bachelor', 'career-master', 'career-react')]
            blocks.append(SimpleNamespace(type='tool_use', id='submit', name='submit_stage_result', input={'result': {
                'assessments': [{'requirement_id': data['requirements'][0]['id'], 'status': 'GAP',
                                 'evidence_ids': [], 'reason': 'Unseen records cannot establish absence.'}],
                'strengths': [], 'gaps': [], 'recommended_focus': []}}))
            return SimpleNamespace(content=blocks, stop_reason='tool_use', usage=SimpleNamespace(input_tokens=0, output_tokens=0))

    client = SameResponseClient(gap_route())
    with pytest.raises(ValueError, match='did not finish with a valid result'):
        action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd']}, settings, client)
    results = client.calls[-1]['messages'][-1]['content']
    assert 'GAP requires complete Career evidence coverage' in results[-1]['content']


def test_snapshot_change_during_final_confirmation_never_publishes(diagnostic_world):
    conn, settings = diagnostic_world
    prior, _ = run_diagnostic(conn, settings, FIXTURE['routes'][3])

    class ChangingClient(DiagnosticClient):
        def create(self, **kwargs):
            response = super().create(**kwargs)
            if 'Assess each supplied' in kwargs['system'] and response.stop_reason == 'end_turn':
                with conn:
                    conn.execute("UPDATE career_evidence SET active=0 WHERE evidence_id='career-master'")
            return response

    with pytest.raises(ValueError, match='changed during matching'):
        action(conn, {'action': 'analyze_job', 'jd': FIXTURE['jd'], 'job_id': prior['id']}, settings,
               ChangingClient(FIXTURE['routes'][3]))
    saved = career_jobs.saved_jobs(conn)[0]
    assert saved['report'] == prior['report'] and saved['status'] == 'failed'


def test_snapshot_change_after_matching_never_publishes(diagnostic_world, monkeypatch):
    conn, settings = diagnostic_world
    prior, _ = run_diagnostic(conn, settings, FIXTURE['routes'][3])
    original = career_jobs.calculate_match_score

    def change_profile(requirements, assessments):
        with conn:
            conn.execute("UPDATE career_evidence SET raw_text='Changed after matching' WHERE evidence_id='career-master'")
        return original(requirements, assessments)

    monkeypatch.setattr(career_jobs, 'calculate_match_score', change_profile)
    with pytest.raises(ValueError, match='changed during matching'):
        run_diagnostic(conn, settings, FIXTURE['routes'][3], prior['id'])
    saved = career_jobs.saved_jobs(conn)[0]
    assert saved['report'] == prior['report'] and saved['requirements'] == prior['requirements']
