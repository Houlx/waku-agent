"""Reviewed source-addressed fixtures exercise the pure Phase B compiler."""
import copy
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from evals.career_extraction_baseline import scripted_baseline
from waku.runtime.career_extraction_compiler import build_source_catalog, compile_extraction
from waku.runtime.career_requirements import extraction_key

FIXTURES = json.loads((Path(__file__).parents[1] / 'fixtures/career_extraction_compiler.json').read_text())


def ref(catalog, text, occurrence=0):
    """Fixture authors use literal text; the submitted IR contains only source IDs."""
    start = -1
    for _ in range(occurrence + 1):
        start = catalog.raw.index(text, start + 1)
    end = start + len(text)
    return {'first': next(t.ref for t in catalog.items if t.start == start),
            'last': next(t.ref for t in catalog.items if t.end == end)}


def fact(catalog, key, kind, subject, support, occurrence=0):
    support_ref = ref(catalog, support, occurrence)
    start, end, _ = catalog.resolve(support_ref)
    subject_start = catalog.raw.index(subject, start, end)
    return {'id': key, 'kind': kind, 'support': support_ref,
            'subject': {'first': next(t.ref for t in catalog.items if t.start == subject_start),
                        'last': next(t.ref for t in catalog.items if t.end == subject_start + len(subject))}}


def ir_for(catalog, facts, operator='ALL'):
    return {'title': 'Synthetic role', 'summary': '', 'responsibilities': [], 'facts': facts,
            'opportunities': [{'operator': operator, 'facts': [f['id'] for f in facts], 'fallback': None}],
            'repeats': []}


@pytest.mark.parametrize('fixture', FIXTURES, ids=[f['name'] for f in FIXTURES])
def test_reviewed_compiler_policy_cases(fixture):
    catalog = build_source_catalog(fixture['jd'])
    ir = ir_for(catalog, [fact(catalog, f'f{i}', *spec) for i, spec in enumerate(fixture['facts'])], fixture['operator'])
    before = copy.deepcopy(ir)
    result = compile_extraction(catalog, ir)
    assert ir == before
    assert result['policy_version'] == 'groups-v1'
    assert result['jd_key'] == extraction_key(fixture['jd'])
    group, = result['requirements']
    assert (group['category'], group['eligibility'], group['importance']) == (
        fixture['category'], fixture['eligibility'], fixture.get('importance', 'required'))
    assert group['constraints']['operator'] == fixture['operator']
    assert group['keywords'] == []
    assert group['eligibility_reason']
    for item, spec in zip(group['constraints']['items'], fixture['facts'], strict=True):
        assert item['subject'] == spec[1]
        assert item['source_excerpt'].encode() == spec[2].encode()
    for span in group['source_spans']:
        assert fixture['jd'][span['start']:span['end']] in group['source_excerpt']
    if fixture['name'] == 'technology_alternatives_typo':
        assert group['constraints']['items'][0]['subject'] == '1abview'
        assert group['text'] == 'Proficiency in LabVIEW OR C++ required'


def test_catalog_preserves_exact_text_and_occurrences():
    jd = 'Responsibilities:\r\nBuild 1abview.\r\nUnusual heading:\r\n1abview  1abview； C++！\n'
    catalog = build_source_catalog(jd)
    assert catalog.raw.encode() == jd.encode()
    assert catalog == build_source_catalog(jd)
    assert catalog.resolve(ref(catalog, '1abview', 1))[0] != catalog.resolve(ref(catalog, '1abview', 2))[0]
    assert catalog.resolve(ref(catalog, '1abview  1abview； C++！'))[2] == '1abview  1abview； C++！'
    assert next(t for t in catalog.items if t.start == jd.index('1abview  ')).section is None
    with pytest.raises(FrozenInstanceError):
        catalog.raw = 'rewritten'
    with pytest.raises(FrozenInstanceError):
        catalog.items[0].text = 'rewritten'
    assert 'start' not in catalog.model_input()[0]


@pytest.mark.parametrize('reference', [None, {}, {'first': 't0', 'last': 't99999'},
                                      {'first': 't1', 'last': 't0'}, {'first': 't-1', 'last': 't0'},
                                      {'first': [], 'last': 't0'}])
def test_invalid_catalog_ranges(reference):
    with pytest.raises(ValueError, match='MALFORMED_IR|UNKNOWN_SOURCE_REF|INVALID_SOURCE_RANGE'):
        build_source_catalog('Python required').resolve(reference)


def education(inheritance=False):
    jd = "Qualifications:\nMaster's degree in electrical engineering major. Relevant experience allows relaxation to bachelor's degree"
    if inheritance:
        jd += ' in the same major'
    jd += '.'
    catalog = build_source_catalog(jd)
    facts = [fact(catalog, 'degree', 'degree', 'Master', "Master's degree"),
             fact(catalog, 'major', 'major', 'electrical engineering', 'in electrical engineering major'),
             fact(catalog, 'fallback', 'degree', 'bachelor', "bachelor's degree")]
    ir = ir_for(catalog, facts[:2])
    ir['facts'] = facts
    ir['opportunities'][0]['fallback'] = {
        'operator': 'ALL', 'facts': ['fallback'], 'condition': ref(catalog, 'Relevant experience'),
        'inherit': ['major'] if inheritance else [],
        'inheritance_support': ref(catalog, 'same major') if inheritance else None}
    return catalog, ir


@pytest.mark.parametrize('inheritance', [False, True])
def test_conditional_fallback_requires_explicit_inheritance(inheritance):
    catalog, ir = education(inheritance)
    group, = compile_extraction(catalog, ir)['requirements']
    route = group['alternative_route']
    assert route['condition'] == 'Relevant experience'
    assert [i['kind'] for i in route['constraints']['items']] == (['degree', 'major'] if inheritance else ['degree'])
    assert route['source_excerpt'] in group['source_excerpt']
    assert all(i['source_excerpt'] in route['source_excerpt'] for i in route['constraints']['items'])
    assert group['importance'] == 'required'


@pytest.mark.parametrize('change, error', [
    ('unknown_source', 'UNKNOWN_SOURCE_REF'), ('unknown_fact', 'UNKNOWN_FACT_REF'),
    ('unused_fact', 'UNUSED_FACT'), ('duplicate', 'DUPLICATE_OPPORTUNITY'),
    ('any_degree_major', 'INVALID_ALTERNATIVE_ROUTE'), ('unsupported_kind', 'UNSUPPORTED_FACT'),
    ('unsupported_inheritance', 'UNSUPPORTED_INHERITANCE'), ('no_fallback', 'INVALID_ALTERNATIVE_ROUTE'),
    ('invented_field', 'MALFORMED_IR'), ('condition_elsewhere', 'UNSUPPORTED_FALLBACK'),
])
def test_invalid_semantics_fail_without_mutating_input(change, error):
    catalog, ir = education()
    opportunity = ir['opportunities'][0]
    if change == 'unknown_source':
        ir['facts'][0]['support']['last'] = 't999999'
    elif change == 'unknown_fact':
        opportunity['facts'][0] = 'missing'
    elif change == 'unused_fact':
        ir['facts'].append(fact(catalog, 'unused', 'degree', 'Master', "Master's degree"))
    elif change == 'duplicate':
        ir['opportunities'].append(copy.deepcopy(opportunity))
    elif change == 'any_degree_major':
        opportunity['operator'] = 'ANY'
    elif change == 'unsupported_kind':
        ir['facts'][0]['kind'] = 'language'
    elif change == 'unsupported_inheritance':
        opportunity['fallback']['inherit'] = ['major']
        opportunity['fallback']['inheritance_support'] = ref(catalog, 'Relevant experience')
    elif change == 'no_fallback':
        opportunity['fallback'] = None
        opportunity['facts'].append('fallback')
    elif change == 'invented_field':
        ir['facts'][0]['text'] = 'Invented Rust skill'
    else:
        opportunity['fallback']['condition'] = ref(catalog, "Master's degree")
    before = copy.deepcopy(ir)
    with pytest.raises(ValueError, match=error):
        compile_extraction(catalog, ir)
    assert ir == before


def test_explicit_repeated_identical_qualification_has_one_opportunity():
    catalog = build_source_catalog('Qualifications:\nPython proficiency required.\nPython proficiency required.')
    ir = ir_for(catalog, [fact(catalog, 'a', 'technology', 'Python', 'Python proficiency required')])
    ir['facts'].append(fact(catalog, 'b', 'technology', 'Python', 'Python proficiency required', 1))
    ir['repeats'] = [{'fact': 'b', 'of': 'a'}]
    groups = compile_extraction(catalog, ir)['requirements']
    assert len(groups) == 1
    assert len(groups[0]['constraints']['items']) == 1
    assert groups[0]['source_excerpt'].count('Python') == 2
    ir['repeats'] = []
    ir['opportunities'].append({'operator': 'ALL', 'facts': ['b'], 'fallback': None})
    with pytest.raises(ValueError, match='Duplicate|OVERLAPPING'):
        compile_extraction(catalog, ir)


def test_different_experience_thresholds_cannot_be_collapsed():
    catalog = build_source_catalog('Qualifications:\nPython experience of 3 years.\nPython experience of 5 years.')
    ir = ir_for(catalog, [fact(catalog, 'a', 'experience', 'Python', 'Python experience of 3 years')])
    ir['facts'].append(fact(catalog, 'b', 'experience', 'Python', 'Python experience of 5 years'))
    ir['repeats'] = [{'fact': 'b', 'of': 'a'}]
    with pytest.raises(ValueError, match='INVALID_REPEAT'):
        compile_extraction(catalog, ir)


def test_duty_only_technology_is_not_a_qualification():
    catalog = build_source_catalog('Responsibilities:\nMaintain Python services.')
    ir = ir_for(catalog, [fact(catalog, 'a', 'technology', 'Python', 'Maintain Python services')])
    with pytest.raises(ValueError, match='UNSUPPORTED_FACT'):
        compile_extraction(catalog, ir)
    ir['facts'] = []
    ir['opportunities'] = []
    ir['responsibilities'] = [ref(catalog, 'Maintain Python services')]
    assert compile_extraction(catalog, ir)['requirements'] == []


def test_qualification_occurrence_selected_instead_of_duty_mention():
    catalog = build_source_catalog('Responsibilities:\nMaintain LabVIEW systems.\nQualifications:\nLabVIEW proficiency required.')
    ir = ir_for(catalog, [fact(catalog, 'a', 'technology', 'LabVIEW', 'LabVIEW proficiency required')])
    group, = compile_extraction(catalog, ir)['requirements']
    assert group['source_excerpt'] == 'LabVIEW proficiency required'
    assert all(s['start'] > catalog.raw.index('Qualifications') for s in group['source_spans'])


def test_unknown_heading_does_not_hide_unheaded_qualification():
    catalog = build_source_catalog('Special candidate signals:\nLabVIEW proficiency required.')
    ir = ir_for(catalog, [fact(catalog, 'a', 'technology', 'LabVIEW', 'LabVIEW proficiency required')])
    assert len(compile_extraction(catalog, ir)['requirements']) == 1
    ir['facts'] = []
    ir['opportunities'] = []
    with pytest.raises(ValueError, match='MISSING_QUALIFICATION'):
        compile_extraction(catalog, ir)


def test_unrelated_clause_between_education_facts_stays_in_provenance():
    catalog = build_source_catalog("Qualifications:\nMaster's degree required.\nOffice provides equipment.\nElectrical engineering major required.")
    ir = ir_for(catalog, [fact(catalog, 'd', 'degree', 'Master', "Master's degree required"),
                          fact(catalog, 'm', 'major', 'Electrical engineering', 'Electrical engineering major required')])
    group, = compile_extraction(catalog, ir)['requirements']
    assert 'Office provides equipment.' in group['source_excerpt']
    assert len(group['constraints']['items']) == 2


def test_broad_mixed_disposition_support_rejects_instead_of_silently_excluding_skill():
    catalog = build_source_catalog('Qualifications:\nPython proficiency and good health required.')
    ir = ir_for(catalog, [fact(catalog, 'a', 'technology', 'Python', 'Python proficiency and good health required')])
    # The existing policy marks this source NON_SCORABLE. Rejecting the
    # inseparable mixed excerpt is safer than silently losing the skill.
    with pytest.raises(ValueError, match='INVALID_RELATIONSHIP'):
        compile_extraction(catalog, ir)
    ir['facts'] = [fact(catalog, 'a', 'technology', 'Python', 'Python proficiency'),
                   fact(catalog, 'b', 'trait', 'health', 'good health required')]
    ir['opportunities'] = [{'operator': 'ALL', 'facts': [key], 'fallback': None} for key in ['a', 'b']]
    assert [g['eligibility'] for g in compile_extraction(catalog, ir)['requirements']] == ['SCORED', 'NON_SCORABLE']


def test_general_tenure_and_skill_tenure_keep_explicit_opportunities():
    catalog = build_source_catalog('Qualifications:\nIndustry experience of 5 years required.\nPython experience of 3 years preferred.')
    ir = ir_for(catalog, [fact(catalog, 'general', 'experience', 'Industry', 'Industry experience of 5 years required'),
                          fact(catalog, 'skill', 'technology', 'Python', 'Python experience of 3 years preferred')])
    ir['opportunities'] = [{'operator': 'ALL', 'facts': [key], 'fallback': None} for key in ['general', 'skill']]
    groups = compile_extraction(catalog, ir)['requirements']
    assert [g['category'] for g in groups] == ['experience', 'skill']
    assert [g['importance'] for g in groups] == ['required', 'preferred']
    assert '5 years' in groups[0]['text']
    assert '3 years' in groups[1]['text']


def test_compiler_does_not_guess_technology_operator():
    fixture = FIXTURES[1]
    catalog = build_source_catalog(fixture['jd'])
    ir = ir_for(catalog, [fact(catalog, f'f{i}', *spec) for i, spec in enumerate(fixture['facts'])])
    with pytest.raises(ValueError, match='one ANY'):
        compile_extraction(catalog, ir)


@pytest.mark.parametrize('mutation', ['extra_top', 'bad_facts', 'bad_fact_id', 'bad_kind', 'extra_fact',
                                       'bad_opportunity', 'bad_operator', 'duplicate_fact', 'bad_repeat',
                                       'repeat_cycle', 'subject_outside_support'])
def test_ir_schema_is_checked_without_provider_schema_enforcement(mutation):
    catalog = build_source_catalog('Qualifications:\nPython proficiency required.\nPython proficiency required.')
    ir = ir_for(catalog, [fact(catalog, 'a', 'technology', 'Python', 'Python proficiency required')])
    if mutation == 'extra_top':
        ir['eligibility'] = 'SCORED'
    elif mutation == 'bad_facts':
        ir['facts'] = 'facts'
    elif mutation == 'bad_fact_id':
        ir['facts'][0]['id'] = []
    elif mutation == 'bad_kind':
        ir['facts'][0]['kind'] = []
    elif mutation == 'extra_fact':
        ir['facts'][0]['source_spans'] = []
    elif mutation == 'bad_opportunity':
        ir['opportunities'][0] = []
    elif mutation == 'bad_operator':
        ir['opportunities'][0]['operator'] = 'XOR'
    elif mutation == 'duplicate_fact':
        ir['opportunities'][0]['facts'] = ['a', 'a']
    elif mutation == 'bad_repeat':
        ir['repeats'] = [{'fact': [], 'of': 'a'}]
    elif mutation == 'repeat_cycle':
        ir['facts'].append(fact(catalog, 'b', 'technology', 'Python', 'Python proficiency required', 1))
        ir['repeats'] = [{'fact': 'a', 'of': 'b'}, {'fact': 'b', 'of': 'a'}]
    else:
        ir['facts'][0]['subject'] = ref(catalog, 'Python', 1)
    with pytest.raises(ValueError, match='MALFORMED_IR|INVALID_RELATIONSHIP|DUPLICATE_OPPORTUNITY|INVALID_REPEAT|UNSUPPORTED_FACT'):
        compile_extraction(catalog, ir)


def test_frozen_phase_a_baseline_replays_in_empty_databases(tmp_path):
    expected = json.loads((Path(__file__).parents[1] / 'fixtures/career_phase_a_baseline.json').read_text())
    assert scripted_baseline(tmp_path) == expected
    assert all(t['cache_rows_before'] == 0 for t in expected['trials'])
    assert [t['cache_rows_after'] for t in expected['trials']] == [1, 1, 1, 1, 0, 0]
