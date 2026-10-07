"""Canonical questions and eligibility remain independent of semantic grading."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from evals.career_extraction import extraction_stability
from evals.helpers import response, text_block, tool_block
from evals.matching_helpers import scripted_assessment
from waku.config import Settings
from waku.db import connect_career
from waku.runtime import career_jobs, career_requirements
from waku.runtime.career import action, save_profile
from waku.runtime.career_extraction_compiler import build_source_catalog, compile_extraction
from waku.runtime.career_jobs import calculate_match_score, delete_job, validate_match
from waku.runtime.career_requirements import (
    cache_extraction,
    cached_extraction,
    validate_extraction,
)

GOLD = json.loads((Path(__file__).parents[1] / 'fixtures/career_requirement_groups.json').read_text())


def proposal():
    return copy.deepcopy(GOLD['extraction'])


def canonical():
    return validate_extraction(proposal(), GOLD['jd'])


def test_reviewed_gold_groups_provenance_constraints_and_dispositions():
    result = canonical()
    groups = result['requirements']
    assert len(groups) == 10
    assert [g['eligibility'] for g in groups] == [
        'SCORED', 'SCORED', 'SCORED', 'SCORED', 'NON_SCORABLE', 'NON_SCORABLE',
        'NON_SCORABLE', 'NEEDS_CONFIRMATION', 'SCORED', 'SCORED']
    assert groups[0]['category'] == 'education' and groups[0]['constraints']['operator'] == 'ALL'
    assert [i['kind'] for i in groups[0]['constraints']['items']] == ['degree', 'major']
    assert groups[0]['alternative_route']['constraints']['items'][0]['subject'] == "Bachelor's"
    assert groups[1]['constraints']['operator'] == 'ANY'
    assert [i['subject'] for i in groups[1]['constraints']['items']] == ['LabVIEW', 'C++']
    assert [g['importance'] for g in groups][-2:] == ['preferred', 'preferred']
    assert [g['category'] for g in groups][2:4] == ['demonstrated_capability'] * 2
    for g in groups:
        assert len(g['semantic_id']) == 64
        for span in g['source_spans']:
            assert GOLD['jd'][span['start']:span['end']]
    assert canonical() == result


@pytest.mark.parametrize('change', [
    lambda g: g.update(category='technical_skill'),
    lambda g: g.pop('eligibility'),
    lambda g: g.update(eligibility='UNKNOWN'),
    lambda g: g['constraints'].update(operator='XOR'),
    lambda g: g['constraints'].update(items=[]),
    lambda g: g['constraints'].update(operator='ANY', items=g['constraints']['items'][:1]),
    lambda g: g['constraints']['items'][0].update(subject='Invented subject'),
    lambda g: g.update(alternative_route=None),
])
def test_invalid_canonical_structure_is_rejected(change):
    value = proposal()
    change(value['requirements'][0])
    with pytest.raises(ValueError):
        validate_extraction(value, GOLD['jd'])


@pytest.mark.parametrize('index', [4, 5, 6, 7])
def test_excluded_clauses_cannot_be_promoted_to_scored(index):
    value = proposal()
    value['requirements'][index]['eligibility'] = 'SCORED'
    with pytest.raises(ValueError, match='Eligibility'):
        validate_extraction(value, GOLD['jd'])


def test_degree_major_split_and_independent_fallback_are_rejected():
    for position, kind in [(1, 'major'), (0, 'degree')]:
        value = proposal()
        extra = copy.deepcopy(value['requirements'][0])
        extra['text'] = 'Different education wording'
        extra['importance'] = 'preferred'
        extra['constraints']['items'] = [extra['constraints']['items'][position]]
        if kind == 'degree':
            extra['constraints']['items'] = copy.deepcopy(extra['alternative_route']['constraints']['items'][:1])
        extra['alternative_route'] = None
        extra['source_excerpt'] = extra['constraints']['items'][0]['source_excerpt']
        value['requirements'].append(extra)
        with pytest.raises(ValueError, match='one education group'):
            validate_extraction(value, GOLD['jd'])


def test_technology_alternatives_cannot_be_all_or_separate_groups():
    value = proposal()
    value['requirements'][1]['constraints']['operator'] = 'ALL'
    with pytest.raises(ValueError, match='one ANY'):
        validate_extraction(value, GOLD['jd'])
    value = proposal()
    first = value['requirements'][1]
    second = copy.deepcopy(first)
    for group, item in zip([first, second], first['constraints']['items'], strict=True):
        group['text'] = group['source_excerpt'] = item['subject']
        group['constraints'] = {'operator': 'ALL', 'items': [item]}
    value['requirements'].append(second)
    with pytest.raises(ValueError, match='one ANY'):
        validate_extraction(value, GOLD['jd'])


def test_semantic_duplicate_paraphrases_and_overlapping_groups_are_rejected():
    value = proposal()
    extra = copy.deepcopy(value['requirements'][-2])
    extra['text'] = 'Python programming proficiency'
    extra['importance'] = 'required'
    extra['source_excerpt'] = 'Experience using Python'
    extra['constraints']['items'][0]['source_excerpt'] = 'Experience using Python'
    value['requirements'].append(extra)
    with pytest.raises(ValueError, match='Duplicate or paraphrased'):
        validate_extraction(value, GOLD['jd'] + '\nExperience using Python')
    value = proposal()
    extra = copy.deepcopy(value['requirements'][2])
    extra['text'] = 'QA collaboration'
    extra['constraints']['items'][0]['subject'] = 'QA teams'
    value['requirements'].append(extra)
    with pytest.raises(ValueError, match='Overlapping'):
        validate_extraction(value, GOLD['jd'])


def test_filtering_changes_membership_without_changing_weights_or_values():
    groups = [dict(g, id=str(i)) for i, g in enumerate(canonical()['requirements'])]
    assessments = [{'requirement_id': g['id'], 'status': 'PARTIAL'}
                   for g in groups if g['eligibility'] == 'SCORED']
    assert calculate_match_score(groups, assessments) == 50.0
    assert calculate_match_score(groups[4:8], []) is None
    assert sum(2 if g['importance'] == 'required' else 1 for g in career_requirements.scored_groups(groups)) == 10
    with pytest.raises(ValueError, match='exactly one'):
        calculate_match_score(groups, assessments + [{'requirement_id': '4', 'status': 'GAP'}])
    with pytest.raises(ValueError, match='eligibility'):
        calculate_match_score([{'id': 'x', 'importance': 'required'}], [])


class GroupClient:
    def __init__(self, extraction=None, fail_matching=False):
        self.extraction = extraction if extraction is not None else copy.deepcopy(GOLD['semantic_ir'])
        self.fail_matching = fail_matching
        self.extraction_calls = 0
        self.match_inputs = []
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        turn = sum(m['role'] == 'assistant' for m in kwargs['messages']) + 1
        if 'Extract source-supported' in kwargs['system']:
            self.extraction_calls += 1
            if turn == 1:
                return response([tool_block('submit_stage_result', {'result': self.extraction})], 'tool_use')
        else:
            if self.fail_matching:
                raise RuntimeError('Synthetic matching failure')
            data = json.loads(kwargs['messages'][0]['content'].split('\n', 1)[1])
            self.match_inputs.append(copy.deepcopy(data))
            if turn == 1:
                return response([tool_block('submit_stage_result', {'result': {
                    'assessments': [scripted_assessment(g, 'GAP', [], 'No documented support.')
                                    for g in data['requirements']],
                    'strengths': [], 'gaps': [], 'recommended_focus': []}})], 'tool_use')
        return response([text_block('Complete.')])


@pytest.fixture
def world(tmp_path):
    settings = Settings(home=tmp_path, model='offline', otel_endpoint='')
    settings.ensure_home()
    conn = connect_career(tmp_path)
    action(conn, {'action': 'save_onboarding', 'raw': GOLD['profile']})
    save_profile(conn, {'basic': GOLD['profile']['basic'], 'records': [
        {'source_id': 'synthetic', 'title': 'Cedar Labs project',
         'description': GOLD['profile']['records'][0]['text'], 'skills': []}]})
    action(conn, {'action': 'confirm'})
    yield conn, settings
    conn.close()


def analyze(world, client, jd=None, job_id=None):
    state = action(world[0], {'action': 'analyze_job', 'jd': jd or GOLD['jd'], 'job_id': job_id}, world[1], client)
    return next(j for j in state['jobs'] if j['id'] == state['job_id'])


def test_unchanged_jd_reuses_set_across_jobs_reanalysis_and_profile_changes(world, tmp_path):
    conn, settings = world
    client = GroupClient()
    runs = []
    job_id = None
    for run in range(6):
        saved = analyze(world, client, job_id=job_id if run % 2 else None)
        job_id = saved['id']
        runs.append(cached_extraction(conn, GOLD['jd']))
        assert len(saved['requirements']) == 10
        assert sum(g['eligibility'] == 'SCORED' for g in saved['requirements']) == 6
        assert len(saved['report']['assessments']) == 6
        assert all(g['eligibility'] == 'SCORED' for g in client.match_inputs[-1]['requirements'])
        assert all(g['eligibility'] == 'SCORED' for g in client.match_inputs[-1]['job']['requirements'])
        assert saved['requirements'][4]['status'] is None
        assert saved['requirements'][7]['status'] is None
        if run == 2:
            profile = action(conn, {'action': 'confirm'})['profile']['normalized']
            profile['records'][0]['description'] += ' Updated explicit fact.'
            action(conn, {'action': 'confirm', 'profile': profile})
    assert client.extraction_calls == 2  # Submit plus completion, exactly one extraction stage.
    metrics = extraction_stability(runs, reference=compile_extraction(build_source_catalog(GOLD['jd']), GOLD['semantic_ir']))
    assert metrics['group_counts'] == [10] * 6
    assert metrics['denominators'] == [10] * 6
    for key in ('group_identity_agreement', 'source_clause_coverage', 'importance_agreement',
                'category_agreement', 'eligibility_agreement'):
        assert metrics[key] == [1.0] * 6
    for key in ('merge_split_rate', 'semantic_duplicate_rate'):
        assert metrics[key] == [0.0] * 6
    (tmp_path / 'extraction-stability.json').write_text(json.dumps(metrics, indent=2))
    # A fresh connection/process sees the same cache; changed model output is never consulted.
    reopened = connect_career(settings.home)
    forbidden = GroupClient(extraction={'invalid': True})
    analyze((reopened, settings), forbidden)
    assert forbidden.extraction_calls == 0
    reopened.close()


def test_cache_survives_matching_failure_and_first_validated_set_wins(world):
    conn, _ = world
    with pytest.raises(RuntimeError, match='Synthetic matching failure'):
        analyze(world, GroupClient(fail_matching=True))
    original = cached_extraction(conn, GOLD['jd'])
    assert original is not None
    client = GroupClient(extraction={'invalid': True})
    analyze(world, client)
    assert client.extraction_calls == 0
    changed = copy.deepcopy(original)
    changed['requirements'].pop()
    assert cache_extraction(conn, GOLD['jd'], changed) == original


def test_jd_and_policy_changes_get_new_keys_and_failed_updates_retain_report(world, monkeypatch):
    client = GroupClient()
    before = analyze(world, client)
    bad = GroupClient(extraction={'invalid': True})
    with pytest.raises(ValueError, match='ended without a valid structured submission'):
        analyze(world, bad, GOLD['jd'] + '\nChanged JD.', before['id'])
    saved = career_jobs.saved_jobs(world[0])[0]
    assert saved['requirements'] == before['requirements'] and saved['report'] == before['report']
    assert saved['outdated'] and saved['status'] == 'failed'
    good = GroupClient()
    analyze(world, good, GOLD['jd'] + '\nChanged JD.', before['id'])
    assert good.extraction_calls == 2
    monkeypatch.setattr(career_requirements, 'POLICY_VERSION', 'test-next-policy')
    next_client = GroupClient()
    analyzed = analyze(world, next_client)
    assert next_client.extraction_calls == 2
    assert analyzed['report']['jd_key'] != before['report']['jd_key']


def test_zero_scored_groups_remain_visible_skip_matching_and_block_resume(world):
    value = proposal()
    value['requirements'] = value['requirements'][4:8]
    from evals.extraction_helpers import excluded_ir_for

    client = GroupClient(excluded_ir_for(value))
    saved = analyze(world, client, '\n'.join(g['source_excerpt'] for g in value['requirements']))
    assert saved['coverage'] is None and len(saved['requirements']) == 4
    assert saved['report']['assessments'] == [] and client.match_inputs == []
    with pytest.raises(ValueError, match='Usable job requirements'):
        action(world[0], {'action': 'generate_resume', 'job_id': saved['id']}, world[1], client)
    with pytest.raises(ValueError, match='Assess every'):
        validate_match({'assessments': [{'requirement_id': saved['requirements'][0]['id'],
            'status': 'GAP', 'evidence_ids': [], 'reason': 'Invalid exclusion assessment.'}],
            'strengths': [], 'gaps': [], 'recommended_focus': []}, saved['requirements'], world[0], {}, ['x'])


def test_cache_deletion_preserves_shared_sets_and_removes_last_job_data(world):
    first = analyze(world, GroupClient())
    second = analyze(world, GroupClient())
    delete_job(world[0], first['id'])
    assert cached_extraction(world[0], GOLD['jd']) is not None
    delete_job(world[0], second['id'])
    assert cached_extraction(world[0], GOLD['jd']) is None


def test_diagnosed_jd_equivalent_reuses_seven_groups_and_denominator_seven(world, tmp_path):
    fixture = json.loads((Path(__file__).parents[1] / 'fixtures/career_requirement_stability.json').read_text())
    runs = []
    client = GroupClient(fixture['semantic_ir'])
    job_id = None
    for run in range(6):
        saved = analyze(world, client, fixture['jd'], job_id=job_id)
        job_id = saved['id']
        runs.append(cached_extraction(world[0], fixture['jd']))
        assert len(saved['requirements']) == 7
        assert len(saved['report']['assessments']) == 4
        assert sum(g['category'] == 'education' for g in saved['requirements']) == 1
        assert all(g['eligibility'] == 'NON_SCORABLE' for g in saved['requirements']
                   if '身体健康' in g['text'])
        assert not any(g['importance'] == 'preferred' and g['category'] == 'education'
                       for g in saved['requirements'])
    assert client.extraction_calls == 2
    metrics = extraction_stability(runs, reference=validate_extraction(fixture['extraction'], fixture['jd']))
    assert metrics['group_counts'] == [7] * 6
    assert metrics['denominators'] == [7] * 6
    assert metrics['group_identity_agreement'] == [1.0] * 6
    (tmp_path / 'diagnosed-equivalent-stability.json').write_text(json.dumps(metrics, indent=2))


def test_stability_metrics_detect_removal_and_policy_disagreements():
    first = canonical()
    changed = copy.deepcopy(first)
    changed['requirements'].pop()
    changed['requirements'][0].update(importance='preferred', category='other', eligibility='NON_SCORABLE')
    metrics = extraction_stability([first, changed])
    assert metrics['group_counts'] == [10, 9]
    assert metrics['group_identity_agreement'][1] < 1
    assert metrics['source_clause_coverage'][1] < 1
    assert metrics['merge_split_rate'][1] > 0
    assert metrics['importance_agreement'][1] < 1
    assert metrics['category_agreement'][1] < 1
    assert metrics['eligibility_agreement'][1] < 1
    assert metrics['denominators'][0] != metrics['denominators'][1]


def test_paraphrase_modifiers_cannot_evade_duplicate_subjects():
    value = proposal()
    extra = copy.deepcopy(value['requirements'][-2])
    extra.update(text='Experience in Python programming', source_excerpt='Experience in Python programming')
    extra['constraints']['items'][0].update(subject='Python programming', source_excerpt=extra['source_excerpt'])
    extra['importance'] = 'required'
    value['requirements'].append(extra)
    with pytest.raises(ValueError, match='Duplicate or paraphrased'):
        validate_extraction(value, GOLD['jd'] + '\nExperience in Python programming')


def test_explicit_importance_cannot_flip_and_route_condition_must_be_grounded():
    value = proposal()
    value['requirements'][-1]['importance'] = 'required'
    with pytest.raises(ValueError, match='Importance must follow'):
        validate_extraction(value, GOLD['jd'])
    value = proposal()
    value['requirements'][0]['alternative_route']['condition'] = 'Invented relaxation condition'
    with pytest.raises(ValueError, match='verbatim route'):
        validate_extraction(value, GOLD['jd'])


def test_legacy_reports_are_preserved_but_require_policy_reanalysis(world):
    saved = analyze(world, GroupClient())
    legacy_report = copy.deepcopy(saved['report'])
    for key in ('extraction_policy_version', 'jd_key', 'requirement_groups'):
        legacy_report.pop(key)
    with world[0]:
        world[0].execute('UPDATE jobs SET report_json=? WHERE id=?',
                         (json.dumps(legacy_report), saved['id']))
    before = tuple(world[0].execute('SELECT * FROM jobs WHERE id=?', (saved['id'],)).fetchone())
    legacy = career_jobs.saved_jobs(world[0])[0]
    assert legacy['report'] == legacy_report and legacy['outdated']
    assert not legacy['requirement_policy_current']
    assert tuple(world[0].execute('SELECT * FROM jobs WHERE id=?', (saved['id'],)).fetchone()) == before
    with pytest.raises(ValueError, match='Requirement policy has changed'):
        action(world[0], {'action': 'generate_resume', 'job_id': saved['id']}, world[1], GroupClient())
    renewed = analyze(world, GroupClient(), job_id=saved['id'])
    assert renewed['requirement_policy_current'] and not renewed['outdated']


def test_omitting_policy_sensitive_clauses_is_rejected():
    for index in [0, 1, 4, 5, 6, 7]:
        value = proposal()
        value['requirements'].pop(index)
        with pytest.raises(ValueError, match='Retain policy-sensitive'):
            validate_extraction(value, GOLD['jd'])


def test_last_job_deletion_prunes_cached_prior_jd_versions(world):
    saved = analyze(world, GroupClient())
    changed_jd = GOLD['jd'] + '\nA new immutable version.'
    analyze(world, GroupClient(), changed_jd, saved['id'])
    assert world[0].execute('SELECT count(*) FROM career_requirement_sets').fetchone()[0] == 2
    delete_job(world[0], saved['id'])
    assert world[0].execute('SELECT count(*) FROM career_requirement_sets').fetchone()[0] == 0


@pytest.mark.parametrize('source', ['Travel software industry experience', 'Dedicated GPU programming',
                                    'Character encoding experience', 'High availability systems experience'])
def test_domain_terms_do_not_become_personality_or_logistics_claims(source):
    value = proposal()
    value['requirements'] = [copy.deepcopy(value['requirements'][-1])]
    group = value['requirements'][0]
    group.update(text=source, source_excerpt=source, importance='required')
    group['constraints']['items'] = [{'kind': 'experience', 'subject': source,
                                     'text': source, 'source_excerpt': source}]
    assert validate_extraction(value, source)['requirements'][0]['eligibility'] == 'SCORED'


def test_technology_or_in_another_sentence_does_not_merge_independent_skills():
    value = proposal()
    python = copy.deepcopy(value['requirements'][-2])
    python.update(text='Python required', source_excerpt='Python required', importance='required')
    value['requirements'] = [python, value['requirements'][1]]
    jd='Python required. Proficient with LabVIEW or C++'
    assert len(validate_extraction(value, jd)['requirements']) == 2


def test_relabeling_duplicate_skill_as_experience_cannot_add_weight():
    value = proposal()
    extra = copy.deepcopy(value['requirements'][-2])
    extra.update(text='Experience using Python', source_excerpt='Experience using Python',
                 category='experience', importance='required')
    extra['constraints']['items'][0].update(kind='experience', source_excerpt=extra['source_excerpt'])
    value['requirements'].append(extra)
    with pytest.raises(ValueError, match='Duplicate or paraphrased'):
        validate_extraction(value, GOLD['jd']+'\nExperience using Python')
