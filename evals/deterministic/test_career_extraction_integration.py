"""Production fresh extraction accepts only source-addressed semantics and preserves cache boundaries."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from evals.career_extraction import fresh_extraction_trials
from evals.career_extraction_benchmark import GoldClient, scripted_benchmark
from evals.career_extraction_gold import semantic_gold, semantic_summary
from evals.deterministic.test_career_extraction_compiler import fact, ir_for
from waku.config import Settings
from waku.db import connect_career
from waku.runtime.career_extraction_compiler import (
    ExtractionRejection,
    build_source_catalog,
    compile_extraction,
    serialized_input_bytes,
    validate_semantic_ir,
)
from waku.runtime.career_jobs import analyze_job
from waku.runtime.career_requirements import cache_extraction, extraction_key, validate_extraction

FIXTURES = Path(__file__).parents[1] / 'fixtures'
GOLD = json.loads((FIXTURES / 'career_extraction_gold.json').read_text())


def repeated_client(value):
    def create(**kwargs):
        return NS(content=[NS(type='tool_use', id=str(len(kwargs['messages'])),
                             name='submit_stage_result', input={'result': copy.deepcopy(value)})],
                  stop_reason='tool_use', raw_stop_reason='tool_use',
                  usage=NS(input_tokens=0, output_tokens=0))
    return NS(messages=NS(create=create), scripted=True)


@pytest.mark.parametrize('case', GOLD, ids=lambda c: c['name'])
def test_reviewed_gold_exercises_fresh_production_path(tmp_path, case):
    settings = Settings(home=tmp_path, model='offline', otel_endpoint='')
    result = fresh_extraction_trials(settings, GoldClient(case['semantic_ir']), case, 1, tmp_path / 'runs')
    trial, = result['trials']
    assert trial['accepted'] and trial['cache_rows_before'] == 0 and trial['cache_rows_after'] == 1
    assert trial['attempts_until_acceptance'] == 1
    metrics = trial['semantic_gold']
    assert metrics['canonical_opportunity_agreement'] == 1
    assert metrics['source_clause_recall'] == 1
    assert metrics['weighted_denominator_agreement'] == 1
    assert metrics['unsupported_qualification_additions'] == 0
    assert metrics['duplicate_scoring_rate'] == 0


@pytest.mark.parametrize('kind', ['legacy', 'source_ref', 'fact_ref', 'unsupported', 'compiler'])
def test_rejected_fresh_ir_never_publishes(tmp_path, kind):
    case = copy.deepcopy(GOLD[2])
    value = case['semantic_ir']
    if kind == 'legacy':
        value = case['extraction']
    elif kind == 'source_ref':
        value['facts'][0]['support']['last'] = 't999999'
    elif kind == 'fact_ref':
        value['opportunities'][0]['facts'] = ['unknown']
    elif kind == 'unsupported':
        value['facts'][0]['kind'] = 'degree'
    else:
        case['jd'] = "Qualifications:\nMaster's degree required.\nGood health required.\nElectrical engineering major required."
        catalog = build_source_catalog(case['jd'])
        facts = [fact(catalog, 'd', 'degree', 'Master', "Master's degree required"),
                 fact(catalog, 'm', 'major', 'Electrical engineering', 'Electrical engineering major required'),
                 fact(catalog, 'h', 'trait', 'health', 'Good health required')]
        value = ir_for(catalog, facts[:2])
        value['facts'] = facts
        value['opportunities'].append({'operator': 'ALL', 'facts': ['h'], 'fallback': None})
    settings = Settings(home=tmp_path, model='offline', max_iterations=2, otel_endpoint='')
    settings.ensure_home()
    conn = connect_career(tmp_path)
    try:
        conn.execute("INSERT INTO career_profile(id,raw_input_json,confirmed) VALUES(1,'{}',1)")
        conn.commit()
        with pytest.raises(ValueError, match='rejected Semantic IR'):
            analyze_job(conn, case['jd'], settings, repeated_client(value))
        assert conn.execute('SELECT count(*) FROM career_requirement_sets').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM job_requirements').fetchone()[0] == 0
        events = [json.loads(line) for p in (tmp_path / 'traces').glob('*.jsonl') for line in p.read_text().splitlines()]
        expected = ('compiler_rejection' if kind == 'compiler' else
                    'semantic_rejection' if kind == 'unsupported' else 'ir_validation')
        assert {e['failure_class'] for e in events if e['type'] == 'career_extraction_outcome'} == {expected}
    finally:
        conn.close()


def test_existing_canonical_cache_bypasses_ir_and_preserves_exact_identity(tmp_path):
    settings = Settings(home=tmp_path, model='offline', otel_endpoint='')
    settings.ensure_home()
    conn = connect_career(tmp_path)
    try:
        conn.execute("INSERT INTO career_profile(id,raw_input_json,confirmed) VALUES(1,'{}',1)")
        conn.commit()
        jd = 'Good health required.'
        extraction = {'title': '', 'summary': '', 'responsibilities': [], 'requirements': [{
            'text': jd, 'source_excerpt': jd, 'category': 'personal_trait', 'importance': 'required',
            'eligibility': 'NON_SCORABLE', 'eligibility_reason': 'Excluded trait.', 'keywords': [],
            'alternative_route': None, 'constraints': {'operator': 'ALL', 'items': [{
                'kind': 'trait', 'subject': 'health', 'text': jd, 'source_excerpt': jd}]}}]}
        cache_extraction(conn, jd, validate_extraction(extraction, jd))
        class NoCalls:
            @property
            def messages(self):
                raise AssertionError('Cached groups must bypass the provider.')
        analyze_job(conn, jd, settings, NoCalls())
        assert conn.execute('SELECT count(*) FROM career_requirement_sets').fetchone()[0] == 1
        assert extraction_key(jd) != extraction_key(' ' + jd)
        assert extraction_key('1abview') != extraction_key('LabVIEW')
    finally:
        conn.close()


@pytest.mark.parametrize('mutation', ['title', 'summary', 'range', 'fallback', 'repeat', 'inheritance'])
def test_ir_reference_shapes_fail_before_semantic_compilation(mutation):
    case = copy.deepcopy(GOLD[16])
    ir = case['semantic_ir']
    if mutation in {'title', 'summary'}:
        ir[mutation] = []
    elif mutation == 'range':
        ir['facts'][0]['subject'] = {'first': 0, 'last': 't1'}
    elif mutation == 'fallback':
        ir['opportunities'][0]['fallback']['facts'] = ['missing']
    elif mutation == 'inheritance':
        ir['opportunities'][0]['fallback']['inherit'] = ['missing']
    else:
        ir['repeats'] = [{'fact': 'missing', 'of': 'degree'}]
    with pytest.raises(ExtractionRejection) as exc:
        validate_semantic_ir(build_source_catalog(case['jd']), ir)
    assert exc.value.failure_class == 'ir_validation'


def test_compact_catalog_preserves_addressability_and_exact_source():
    catalog = build_source_catalog('Responsibilities:\r\n1abview.\nOdd section:\n中文  中文！\n')
    payload = catalog.prompt_input()
    assert payload['raw'] == catalog.raw
    assert payload['tokens'] == [[t.ref, t.text] for t in catalog.items]
    assert payload['sections'][-1][1] is None
    old = json.dumps({'raw': catalog.raw, 'items': catalog.model_input()}, ensure_ascii=False).encode()
    assert serialized_input_bytes(catalog) < len(old)


def test_gold_metrics_detect_semantic_errors_even_with_unchanged_hashes():
    case = GOLD[1]
    reference = validate_extraction(case['extraction'], case['jd'])
    actual = compile_extraction(build_source_catalog(case['jd']), case['semantic_ir'])
    assert semantic_gold(actual, reference, case['jd'])['all_any_accuracy'] == 1
    actual['requirements'][0]['constraints']['operator'] = 'ALL'
    actual['requirements'][0]['category'] = 'experience'
    actual['requirements'][0]['eligibility'] = 'NON_SCORABLE'
    metrics = semantic_gold(actual, reference, case['jd'])
    assert metrics['all_any_accuracy'] == metrics['category_accuracy'] == metrics['eligibility_accuracy'] == 0
    assert metrics['weighted_denominator_agreement'] == 0
    metrics = semantic_gold({'requirements': []}, reference, case['jd'])
    assert metrics['source_clause_recall'] == metrics['canonical_opportunity_agreement'] == 0


def test_gold_metrics_detect_split_merge_additions_duplicates_fallback_and_inheritance():
    case = GOLD[16]
    reference = validate_extraction(case['extraction'], case['jd'])
    actual = compile_extraction(build_source_catalog(case['jd']), case['semantic_ir'])
    actual['requirements'][0]['alternative_route']['constraints']['items'].pop()
    m = semantic_gold(actual, reference, case['jd'])
    assert m['fallback_accuracy'] == m['inheritance_accuracy'] == 0
    actual['requirements'][0]['constraints']['items'][0]['subject'] = 'invented degree'
    m = semantic_gold(actual, reference, case['jd'])
    assert m['unsupported_qualification_additions'] == 1
    actual['requirements'].append(copy.deepcopy(actual['requirements'][0]))
    assert semantic_gold(actual, reference, case['jd'])['duplicate_scoring_rate'] == 0.5
    case = GOLD[0]
    reference = validate_extraction(case['extraction'], case['jd'])
    actual = copy.deepcopy(reference)
    second = copy.deepcopy(actual['requirements'][0])
    second['constraints']['items'] = [actual['requirements'][0]['constraints']['items'].pop()]
    actual['requirements'].append(second)
    m = semantic_gold(actual, reference, case['jd'])
    assert m['merge_split_accuracy'] == 0
    assert m['canonical_opportunity_agreement'] == 0


def test_failed_trials_reduce_all_trial_quality():
    case = GOLD[2]
    canonical = validate_extraction(case['extraction'], case['jd'])
    m = semantic_gold(canonical, canonical, case['jd'])
    summary = semantic_summary([{'accepted': True, 'semantic_gold': m}, {'accepted': False}])
    assert summary['among_accepted_trials']['source_clause_recall'] == 1
    assert summary['all_fresh_trials']['completion_adjusted_quality']['source_clause_recall'] == 0.5
    assert summary['all_fresh_trials']['non_completion_rate'] == 0.5


def test_scripted_phase_a_comparison_and_gold_metrics(tmp_path):
    result = scripted_benchmark(tmp_path)
    before, after = result['phase_a_frozen'], result['phase_b_reliability']
    assert before['fresh_completion_rate'] == after['fresh_completion_rate'] == 4 / 6
    assert after['no_submit_rate'] == after['truncation_rate'] == 2 / 6
    assert [t['attempts_until_acceptance'] for t in after['trials']] == [1, 2, 1, 1, None, None]
    assert len(result['gold_cases']) == 25
    assert all(run['trials'][0]['accepted'] for run in result['gold_cases'])


@pytest.mark.parametrize('mutation,metric', [('legacy', 'malformed_ir_count'),
                                            ('unsupported', 'ir_semantic_rejection_count'),
                                            ('arguments', 'malformed_arguments_count')])
def test_evaluator_preserves_failure_classes_and_noncompletion(tmp_path, mutation, metric):
    case = copy.deepcopy(GOLD[2])
    ir = case['semantic_ir']
    if mutation == 'legacy':
        ir = case['extraction']
    elif mutation == 'unsupported':
        ir['facts'][0]['kind'] = 'degree'
    client = GoldClient(ir)
    if mutation == 'arguments':
        original = client.create
        def malformed(**kwargs):
            response = original(**kwargs)
            if len(kwargs['messages']) == 1:
                response.content[0].input = {'unexpected': ir}
            return response
        client.messages = NS(create=malformed)
    result = fresh_extraction_trials(Settings(home=tmp_path, model='offline', otel_endpoint=''),
                                     client, case, 1, tmp_path / 'runs')
    assert result['reliability'][metric] == 1
    assert result['reliability']['completed_trials'] == 0
    assert result['semantic_quality']['among_accepted_trials'] is None
    assert result['semantic_quality']['all_fresh_trials']['non_completion_rate'] == 1
    assert result['trials'][0]['cache_rows_after'] == 0


def test_malformed_provider_arguments_preserve_submission_failure(tmp_path):
    from evals.deterministic.test_career_extraction_submission import ForcedExtraction

    class MalformedProvider(ForcedExtraction):
        def _call(self, kwargs):
            response = super()._call(kwargs)
            response.choices[0].message.tool_calls[0].function.arguments = '{'
            return response
    case = GOLD[2]
    result = fresh_extraction_trials(Settings(home=tmp_path, model='offline', otel_endpoint=''),
                                     MalformedProvider(), case, 1, tmp_path / 'runs')
    assert result['reliability']['malformed_arguments_count'] == 1
    assert result['trials'][0]['error'] == 'JSONDecodeError'
    assert result['trials'][0]['provider_turns'] == 1
    assert result['trials'][0]['cache_rows_after'] == 0
