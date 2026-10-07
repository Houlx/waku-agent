"""Reviewed frozen semantic examples and deterministic matching enforcement."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from evals.career_matching import matching_stability, repeated_matching
from evals.helpers import response, text_block, tool_block
from waku.config import Settings
from waku.db import connect_career
from waku.runtime.career import action, save_profile
from waku.runtime.career_jobs import validate_match
from waku.runtime.career_matching import MatchingCoverage
from waku.runtime.career_rubric import matching_groups, matching_routes, validate_material_support

GOLD = json.loads((Path(__file__).parents[1] / 'fixtures/career_matching_rubric.json').read_text())
CASES = GOLD['cases']


def report(case):
    return {'assessments': [copy.deepcopy(case['assessment'])], 'strengths': [], 'gaps': [],
            'recommended_focus': [], 'matching_policy_version': 'matching-v1'}


def setup_world(tmp_path, case):
    settings = Settings(home=tmp_path, model='offline', otel_endpoint='')
    settings.ensure_home()
    conn = connect_career(tmp_path)
    records = case['evidence']
    action(conn, {'action': 'save_onboarding', 'raw': {
        'basic': {'Name': 'Morgan Vale'}, 'records': [
            {'source_id': r['source_id'], 'type': r['source_type'], 'text': r['raw_text']} for r in records]}})
    save_profile(conn, {'basic': {'Name': 'Morgan Vale'}, 'records': [r['normalized'] for r in records]})
    action(conn, {'action': 'confirm'})
    return conn, settings


class FrozenClient:
    def __init__(self, case):
        self.case = case
        self.requests = []
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        data = json.loads(kwargs['messages'][0]['content'].split('\n', 1)[1])
        # Closed matching-only boundary: extraction cannot hide in the experiment.
        assert 'jd' not in data and 'matching_routes' in data['requirements'][0]
        assert data['matching_policy_version'] == 'matching-v1'
        if len(kwargs['messages']) == 1:
            proposal = report(self.case)
            proposal.pop('matching_policy_version')
            return response([tool_block('submit_stage_result', {'result': proposal})], 'tool_use')
        return response([text_block('Complete.')])


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['name'])
def test_frozen_gold_routes_and_six_trial_experiment(tmp_path, case):
    conn, settings = setup_world(tmp_path, case)
    try:
        before = copy.deepcopy(case['group'])
        client = FrozenClient(case)
        result = repeated_matching(conn, settings, client, [case['group']], reference=report(case))
        metrics = result['metrics']
        assert case['group'] == before
        assert len(client.requests) == 12
        assert all(r['assessments'][0]['status'] == case['expected_status'] for r in result['reports'])
        assert metrics['full_status_vector_agreement'] == 1.0
        assert list(metrics['per_group_status_agreement'].values()) == [1.0]
        assert metrics['status_frequencies'][case['group']['id']][case['expected_status']] == 6
        assert metrics['unsupported_inference_rate'] == 0.0
        assert metrics['coverage_spread'] == 0.0
        expected = {'MATCH': 100.0, 'PARTIAL': 50.0, 'GAP': 0.0}[case['expected_status']]
        assert metrics['coverages'] == [expected] * 6
        assert conn.execute('SELECT count(*) FROM career_requirement_sets').fetchone()[0] == 0
        (tmp_path / 'matching-stability.json').write_text(json.dumps(result, indent=2))
    finally:
        conn.close()


def case_named(name):
    return copy.deepcopy(next(c for c in CASES if c['name'] == name))


@pytest.mark.parametrize('mutation', [
    lambda a: a.update(status='MATCH'),
    lambda a: a.update(satisfied_routes=['primary']),
    lambda a: a['constraint_results'].pop(),
    lambda a: a['constraint_results'].append(copy.deepcopy(a['constraint_results'][0])),
    lambda a: a['constraint_results'][0].update(constraint_id='other-group:0'),
    lambda a: a['constraint_results'][0].update(evidence_ids=['unseen']),
    lambda a: a['constraint_results'][0].update(evidence_ids=[]),
    lambda a: a['constraint_results'][1].update(evidence_ids=['career-gold']),
    lambda a: a['constraint_results'][0].update(reason=''),
    lambda a: a['constraint_results'][0].update(status='LIKELY'),
    lambda a: a.update(evidence_ids=[]),
])
def test_invalid_material_proposals_are_rejected(mutation):
    case = case_named('masters-unsupported-major')
    mutation(case['assessment'])
    with pytest.raises(ValueError):
        validate_material_support(case['assessment'], case['group'],
                                  {r['evidence_id']: r for r in case['evidence']})


def test_cross_route_mixing_cannot_manufacture_match():
    case = case_named('cross-route-mixing')
    case['assessment'].update(status='MATCH', satisfied_routes=['alternative'])
    with pytest.raises(ValueError, match='structurally complete routes'):
        validate_material_support(case['assessment'], case['group'], {'career-gold': case['evidence'][0]})


def test_any_one_side_and_unused_education_route_do_not_reduce_match():
    for name in ('or-right-side', 'masters-related-major'):
        case = case_named(name)
        validate_material_support(case['assessment'], case['group'], {'career-gold': case['evidence'][0]})
        assert case['assessment']['status'] == 'MATCH'
        assert case['assessment']['satisfied_routes'] == ['primary']


def test_gap_and_partial_cannot_contradict_material_support():
    for name, wrong in [('exact-technology', 'PARTIAL'), ('writing-indirect', 'GAP'),
                        ('writing-absent', 'PARTIAL')]:
        case = case_named(name)
        case['assessment']['status'] = wrong
        with pytest.raises(ValueError, match='contradicts material support'):
            validate_material_support(case['assessment'], case['group'], {'career-gold': case['evidence'][0]})


def test_degree_constraint_cannot_hide_work_citation_behind_group_education_citation():
    case = case_named('masters-related-major')
    case['assessment']['constraint_results'][0]['evidence_ids'] = ['career-work']
    records = {'career-gold': case['evidence'][0], 'career-work': {'source_type': 'work'}}
    with pytest.raises(ValueError, match='education evidence per constraint'):
        validate_material_support(case['assessment'], case['group'], records)


def test_matching_overlay_preserves_canonical_contract():
    group = case_named('masters-related-major')['group']
    before = copy.deepcopy(group)
    overlay = matching_groups([group])[0]
    assert group == before and 'matching_routes' not in group
    assert overlay['semantic_id'] == group['semantic_id']
    routes = matching_routes(group)
    assert routes[1]['condition']['text'] == 'exceptional relevant experience'
    assert [c['constraint_id'] for c in routes[0]['items']] == ['primary:0', 'primary:1']


def test_validator_rejects_positive_citation_not_delivered(tmp_path):
    case = case_named('exact-technology')
    conn, _ = setup_world(tmp_path, case)
    try:
        collected = {}
        coverage = MatchingCoverage(conn, collected)
        collected.update(coverage.records)  # inspection alone is not delivery
        proposal = report(case)
        proposal.pop('matching_policy_version')
        with pytest.raises(ValueError, match='must be delivered'):
            validate_match(proposal, [case['group']], conn, collected, [], coverage)
    finally:
        conn.close()


def test_metrics_detect_variability_and_unsupported_inferences():
    case = case_named('writing-indirect')
    gold = report(case)
    stronger = copy.deepcopy(gold)
    a = stronger['assessments'][0]
    a.update(status='MATCH', satisfied_routes=['primary'])
    a['constraint_results'][0]['status'] = 'SATISFIED'
    metrics = matching_stability([case['group']], [gold, stronger, gold], gold)
    assert metrics['per_group_status_agreement'] == {'writing': 1 / 3}
    assert metrics['full_status_vector_agreement'] == 1 / 3
    assert metrics['status_frequencies']['writing'] == {'MATCH': 1, 'PARTIAL': 2, 'GAP': 0}
    assert metrics['unsupported_inference_rate'] == 1 / 3
    assert metrics['coverage_spread'] == 50.0
    assert matching_stability([case['group']], [gold])['unsupported_inference_rate'] is None
    stronger['matching_policy_version'] = 'different'
    with pytest.raises(ValueError, match='share the current matching policy'):
        matching_stability([case['group']], [gold, stronger])


def test_multiple_group_vector_agreement_is_distinct_from_group_agreement():
    first, second = case_named('exact-technology'), case_named('writing-indirect')
    baseline = report(first)
    baseline['assessments'].append(second['assessment'])
    changed = copy.deepcopy(baseline)
    a = changed['assessments'][1]
    a.update(status='GAP', evidence_ids=[], satisfied_routes=[])
    a['constraint_results'][0].update(status='UNSUPPORTED', evidence_ids=[])
    metrics = matching_stability([first['group'], second['group']], [baseline, changed], baseline)
    assert metrics['per_group_status_agreement'] == {'exact-cpp': 1.0, 'writing': 0.0}
    assert metrics['full_status_vector_agreement'] == 0.0
    assert metrics['coverages'] == [75.0, 50.0]
    assert metrics['coverage_spread'] == 25.0


def test_rubric_failure_retains_saved_report_and_policy_version(tmp_path):
    from evals.deterministic.test_career_jobs import JobClient

    case = case_named('exact-technology')
    case['evidence'][0].update(source_id='software', evidence_id='career-software')
    case['evidence'][0]['normalized']['source_id'] = 'software'
    conn, settings = setup_world(tmp_path, case)
    try:
        prior = action(conn, {'action': 'analyze_job', 'jd': JobClient().fixture['jd']}, settings, JobClient())
        saved = prior['jobs'][0]
        assert saved['report']['matching_policy_version'] == 'matching-v1'
        bad = JobClient(mutate=lambda p: p['assessments'][0].update(constraint_results=[]))
        with pytest.raises(ValueError, match='ended without a structured submission'):
            action(conn, {'action': 'analyze_job', 'jd': saved['raw_jd'], 'job_id': saved['id']}, settings, bad)
        from waku.runtime.career_jobs import saved_jobs

        after = saved_jobs(conn)[0]
        assert after['report'] == saved['report']
        assert after['coverage'] == saved['coverage']
        assert after['status'] == 'failed'
    finally:
        conn.close()
