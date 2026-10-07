"""Fresh extraction preserves qualifications and gives actionable repair feedback."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from evals.career_extraction import fresh_extraction_trials
from evals.extraction_helpers import executable_ir
from waku.config import Settings
from waku.db import connect_career
from waku.runtime.career_extraction_compiler import (
    SEMANTIC_IR_SCHEMA,
    build_source_catalog,
    compile_extraction,
)
from waku.runtime.career_jobs import analyze_job
from waku.runtime.career_requirements import (
    cache_extraction,
    cached_extraction,
    extraction_key,
    qualification_spans,
    validate_extraction,
)
from waku.tools.career import make_stage_submit_tool
from waku.tools.registry import ToolRegistry


def invalid_ir():
    ir = executable_ir(JD)
    ir['facts'][0]['support']['last'] = 't999999'
    return ir


MAJOR = '控制、计算机等相关专业'
NORMAL = '硕士及以上学历 ，' + MAJOR + '。'
FALLBACK = '相关项目经验充分者可放宽学历至本科'
EDUCATION = NORMAL + FALLBACK + ' 。'
TECHNOLOGY = '熟练使用1abview、C++任意一种编程开发软件'
COORDINATION = '具有较强的组织协调沟通能力'
WRITING = '具备一定的文字表达能力'
TRAITS = '身体健康，吃苦耐劳，爱岗敬业'
INITIATIVE = '有较强的进取意识和团队合作精神'
EXPERIENCE = '具有传感器试验平台建设与运行经验者优先 。'
QUALIFICATIONS = '\n'.join([
    EDUCATION, TECHNOLOGY + COORDINATION + ' ，' + WRITING + ' 。',
    TRAITS + '，' + INITIATIVE + ' 。', EXPERIENCE,
])
JD = ('Cedar Instruments 合成测试岗位\n岗位职责：维护1abview、C++等测试软件。\n'
      '任职要求：\n' + QUALIFICATIONS)
QUALIFICATION_ONLY_JD = 'Cedar Instruments 合成测试岗位\n任职要求：\n' + QUALIFICATIONS


def constraint(kind, subject, excerpt=None, text=None):
    return {'kind': kind, 'subject': subject, 'text': text or subject,
            'source_excerpt': excerpt or subject}


def group(category, eligibility, excerpt, items, operator='ALL', importance='required'):
    return {'text': excerpt, 'category': category, 'importance': importance,
            'keywords': [], 'source_excerpt': excerpt, 'eligibility': eligibility,
            'eligibility_reason': 'Synthetic source criterion.',
            'constraints': {'operator': operator, 'items': items}, 'alternative_route': None}


def proposal():
    education = group('education', 'SCORED', EDUCATION, [
        constraint('degree', '硕士', text='硕士及以上学历'),
        constraint('major', '计算机', MAJOR, MAJOR)])
    education['alternative_route'] = {
        'condition': '相关项目经验充分者', 'source_excerpt': FALLBACK,
        'constraints': {'operator': 'ALL', 'items': [constraint('degree', '本科')]}}
    return {'title': 'Synthetic testing role', 'summary': '', 'responsibilities': [],
            'requirements': [education,
                group('skill', 'SCORED', TECHNOLOGY, [
                    constraint('technology', '1abview', TECHNOLOGY, 'LabVIEW proficiency'),
                    constraint('technology', 'C++', TECHNOLOGY)], operator='ANY'),
                group('demonstrated_capability', 'SCORED', COORDINATION, [
                    constraint('behavior', '组织协调沟通能力', COORDINATION)]),
                group('demonstrated_capability', 'NON_SCORABLE', WRITING, [
                    constraint('behavior', '文字表达能力', WRITING)]),
                group('personal_trait', 'NON_SCORABLE', TRAITS, [
                    constraint('trait', '身体健康', TRAITS)]),
                group('personal_trait', 'NON_SCORABLE', INITIATIVE, [
                    constraint('trait', '进取意识', INITIATIVE)]),
                group('experience', 'SCORED', EXPERIENCE, [
                    constraint('experience', '传感器试验平台', EXPERIENCE)], importance='preferred')]}


def rejected_proposal(shape):
    value = proposal()
    education, technology, coordination, writing, traits = value['requirements'][:5]
    route = education['alternative_route']
    if shape == 'inherited_major':
        route['constraints']['items'].append(copy.deepcopy(education['constraints']['items'][1]))
    elif shape == 'route_subject':
        route['constraints']['items'].append(constraint('major', '计算机', FALLBACK))
    elif shape == 'corrected_typo':
        technology['constraints']['items'][0]['subject'] = 'LabVIEW'
    elif shape == 'mixed_eligibility':
        coordination['source_excerpt'] += ' ，' + WRITING
        coordination['constraints']['items'] += copy.deepcopy(writing['constraints']['items'])
        value['requirements'].remove(writing)
    elif shape == 'scored_generic_writing':
        writing['eligibility'] = 'SCORED'
    elif shape == 'punctuation':
        value['requirements'][-1]['source_excerpt'] = EXPERIENCE.replace(' 。', '。')
    elif shape == 'overlap':
        traits['constraints']['items'] = [constraint('trait', '身体健康', TRAITS)]
        value['requirements'].append(group('personal_trait', 'NON_SCORABLE', TRAITS, [
            constraint('trait', '吃苦耐劳', TRAITS)]))
        value['requirements'][-1]['text'] = '吃苦耐劳'
    elif shape == 'category_kind':
        traits['category'] = 'other'
    elif shape == 'missing_route':
        education['alternative_route'] = None
    elif shape == 'route_outside_group':
        education['source_excerpt'] = NORMAL
    else:
        raise AssertionError(shape)
    return value


@pytest.mark.parametrize(('shape', 'message'), [
    ('inherited_major', 'Alternative constraints must belong to the route source.'),
    ('route_subject', 'Constraint subject must be literal source wording.'),
    ('corrected_typo', 'Constraint subject must be literal source wording.'),
    ('mixed_eligibility', 'Eligibility must follow source constraints; separate mixed dispositions.'),
    ('scored_generic_writing', 'Eligibility must follow source constraints; separate mixed dispositions.'),
    ('punctuation', 'Requirement excerpts must occur in the pasted JD.'),
    ('overlap', 'Overlapping groups cannot create duplicate scoring opportunities.'),
    ('category_kind', 'Category must agree with material constraint kinds.'),
    ('missing_route', 'An education exception requires alternative_route, not independent credit.'),
    ('route_outside_group', 'Alternative route provenance must belong to its education group.'),
])
def test_observed_rejected_shapes_report_exact_first_error(shape, message):
    with pytest.raises(ValueError) as error:
        validate_extraction(rejected_proposal(shape), JD)
    assert message in str(error.value)
    assert " at requirements[" in str(error.value)


def test_responsibility_technology_does_not_add_provenance_obligations():
    value = proposal()
    accepted = validate_extraction(value, QUALIFICATION_ONLY_JD)
    assert len(accepted['requirements']) == 7
    assert accepted['requirements'][1]['constraints']['operator'] == 'ANY'
    assert accepted['requirements'][1]['constraints']['items'][0]['text'] == 'LabVIEW proficiency'
    # The earlier responsibility adds no requirement or provenance obligation.
    actual = validate_extraction(value, JD)
    assert len(actual['requirements']) == 7
    assert actual['requirements'][1]['source_excerpt'] == TECHNOLOGY
    assert actual['requirements'][0]['alternative_route']['source_excerpt'] == FALLBACK
    assert extraction_key(JD) == 'bb764a5c00cc49da0ad8cfc1c8210b50979d5962c8ead815874f181e3e967071'


def test_empty_tool_arguments_report_missing_result():
    registry = ToolRegistry()
    registry.register(make_stage_submit_tool(lambda value: compile_extraction(build_source_catalog(JD), value),
                                            SEMANTIC_IR_SCHEMA, 'Synthetic extraction submission.'))
    assert registry.execute('submit_stage_result', {}) == (
        'Error running submit_stage_result: make_stage_submit_tool.<locals>.execute() '
        "missing 1 required positional argument: 'result'")


@pytest.mark.parametrize('jd', [
    'Responsibilities:\nMaintain LabVIEW OR C++ testing tools.',
    '岗位职责：\n维护1abview、C++测试软件。',
    '负责开发1abview、C++测试软件。',
    'About us:\nOur product uses C++.',
])
def test_responsibilities_only_technology_does_not_force_requirements(jd):
    empty = {'title': '', 'summary': '', 'responsibilities': [], 'requirements': []}
    assert validate_extraction(empty, jd)['requirements'] == []


@pytest.mark.parametrize('jd', [
    'Qualifications:\nLabVIEW OR C++ required.',
    '熟练使用1abview、C++任意一种编程开发软件',
    'Responsibilities:\nMaintain C++ tools.\nQualifications:\nC++ required.',
    'We require C++ proficiency.',
    '熟练使用1abview进行测试开发',
])
def test_omitted_qualification_technology_still_fails(jd):
    empty = {'title': '', 'summary': '', 'responsibilities': [], 'requirements': []}
    with pytest.raises(ValueError, match='MISSING_QUALIFICATION.*Missing qualification wording'):
        validate_extraction(empty, jd)


def test_repeated_genuine_qualifications_need_coverage_without_duplicate_credit():
    first = 'LabVIEW OR C++ required'
    second = 'C++ programming knowledge required'
    value = {'title': '', 'summary': '', 'responsibilities': [], 'requirements': [
        group('skill', 'SCORED', first, [constraint('technology', 'LabVIEW', first),
                                       constraint('technology', 'C++', first)], operator='ANY')]}
    jd = 'Qualifications:\n' + first + '\n' + second
    with pytest.raises(ValueError, match='MISSING_QUALIFICATION'):
        validate_extraction(value, jd)
    value['requirements'][0]['source_excerpt'] = first + '\n' + second
    assert len(validate_extraction(value, jd)['requirements']) == 1


def test_unheaded_numbered_jd_uses_qualification_occurrences():
    jd = ('Synthetic testing role\n1.负责维护1abview、C++等软件。2.负责测试设备安装。\n\n'
          '1.' + QUALIFICATIONS)
    accepted = validate_extraction(proposal(), jd)
    assert len(accepted['requirements']) == 7
    spans = qualification_spans(jd)
    responsibility = jd.index('C++')
    assert not any(s['start'] <= responsibility < s['end'] for s in spans)
    assert extraction_key(jd) != extraction_key(jd.replace('1abview', 'LabVIEW'))


def test_responsibility_alternatives_do_not_change_joint_qualification():
    source = 'LabVIEW and C++ required'
    value = {'title': '', 'summary': '', 'responsibilities': [], 'requirements': [
        group('skill', 'SCORED', source, [constraint('technology', 'LabVIEW', source),
                                        constraint('technology', 'C++', source)])]}
    jd = 'Responsibilities: Maintain LabVIEW OR C++ tools.\nQualifications: ' + source
    assert validate_extraction(value, jd)['requirements'][0]['constraints']['operator'] == 'ALL'


def test_responsibility_cannot_be_invented_as_a_qualification():
    source = 'Maintain C++ testing tools'
    value = {'title': '', 'summary': '', 'responsibilities': [], 'requirements': [
        group('skill', 'SCORED', source, [constraint('technology', 'C++', source)])]}
    with pytest.raises(ValueError, match='NON_QUALIFICATION_PROVENANCE'):
        validate_extraction(value, 'Responsibilities:\n' + source)


def test_unheaded_english_sentences_do_not_hide_a_qualification():
    value = {'title': '', 'summary': '', 'responsibilities': [], 'requirements': []}
    with pytest.raises(ValueError, match='MISSING_QUALIFICATION'):
        validate_extraction(value, 'Maintain C++ testing tools. C++ proficiency required.')


@pytest.mark.parametrize('eligibility', ['SCORED', 'NEEDS_CONFIRMATION'])
def test_health_stays_non_scorable(eligibility):
    value = proposal()
    value['requirements'][4]['eligibility'] = eligibility
    with pytest.raises(ValueError, match='INVALID_ELIGIBILITY'):
        validate_extraction(value, JD)


def test_broad_excerpt_cannot_promote_generic_writing():
    value = proposal()
    coordination, writing = value['requirements'][2:4]
    coordination['source_excerpt'] += ' ，' + WRITING
    coordination['constraints']['items'].append(copy.deepcopy(writing['constraints']['items'][0]))
    for item in coordination['constraints']['items']:
        item['source_excerpt'] = coordination['source_excerpt']
    value['requirements'].remove(writing)
    with pytest.raises(ValueError, match='INVALID_ELIGIBILITY'):
        validate_extraction(value, JD)


@pytest.mark.parametrize('shape', ['technology_all', 'degree_or_major', 'degrees_all', 'majors_all'])
def test_alternative_semantics_remain_strict(shape):
    value = proposal()
    education, technology = value['requirements'][:2]
    if shape == 'technology_all':
        technology['constraints']['operator'] = 'ALL'
    elif shape == 'degree_or_major':
        education['constraints']['operator'] = 'ANY'
    elif shape == 'degrees_all':
        route = education['alternative_route']
        route['source_excerpt'] = EDUCATION
        route['constraints']['items'].append(constraint('degree', '硕士'))
    else:
        education['constraints']['items'].append(constraint('major', '控制', MAJOR))
    with pytest.raises(ValueError, match='one ANY|INVALID_ALTERNATIVE_ROUTE'):
        validate_extraction(value, JD)


def test_invented_subject_and_duplicate_opportunities_remain_rejected():
    value = proposal()
    value['requirements'][1]['constraints']['items'][0]['subject'] = 'Rust'
    with pytest.raises(ValueError, match='LITERAL_SUBJECT_MISMATCH'):
        validate_extraction(value, JD)
    value = proposal()
    value['requirements'].append(copy.deepcopy(value['requirements'][1]))
    with pytest.raises(ValueError, match='Duplicate or paraphrased'):
        validate_extraction(value, JD)


def test_extraction_can_repair_feedback_then_publish_in_empty_cache(tmp_path):
    from waku.runtime.career_jobs import fresh_extraction

    settings = Settings(home=tmp_path, model='offline', otel_endpoint='')
    settings.ensure_home()
    conn = connect_career(tmp_path)
    calls = []

    def create(**kwargs):
        turn = len(calls)
        if turn == 1:
            feedback = kwargs['messages'][-1]['content'][0]['content']
            assert 'UNKNOWN_SOURCE_REF' in feedback
        calls.append(turn)
        if turn == 2:
            blocks = [SimpleNamespace(type='text', text='Complete.')]
        else:
            blocks = [SimpleNamespace(type='tool_use', id=str(turn), name='submit_stage_result', input={
                'result': invalid_ir() if turn == 0 else executable_ir(JD)})]
        return SimpleNamespace(content=blocks, stop_reason='tool_use' if turn < 2 else 'end_turn',
                               usage=SimpleNamespace(input_tokens=0, output_tokens=0))

    try:
        assert cached_extraction(conn, JD) is None
        result = fresh_extraction(settings, SimpleNamespace(messages=SimpleNamespace(create=create)), JD)
        assert len(calls) == 3
        assert cache_extraction(conn, JD, result) == cached_extraction(conn, JD)
        assert len(result['requirements']) == 7
        assert conn.execute('SELECT count(*) FROM job_matches').fetchone()[0] == 0
    finally:
        conn.close()


def test_fresh_trial_measurements_use_independent_empty_caches(tmp_path):
    fixture = json.loads((Path(__file__).parents[1] / 'fixtures/career_extraction_executability.json').read_text())
    calls = []

    def create(**kwargs):
        turn = sum(m['role'] == 'assistant' for m in kwargs['messages'])
        calls.append(turn)
        if turn == 0:
            blocks = [SimpleNamespace(type='tool_use', id='submit', name='submit_stage_result',
                                      input={'result': fixture['semantic_ir']})]
        else:
            blocks = [SimpleNamespace(type='text', text='Complete.')]
        return SimpleNamespace(content=blocks, stop_reason='tool_use' if turn == 0 else 'end_turn',
                               usage=SimpleNamespace(input_tokens=0, output_tokens=0))

    settings = Settings(home=tmp_path, model='offline', otel_endpoint='')
    result = fresh_extraction_trials(settings, SimpleNamespace(messages=SimpleNamespace(create=create)),
                                     fixture, 3, tmp_path / 'trials')
    assert calls == [0, 1, 0, 1, 0, 1]
    assert result['successful_extraction_rate'] == 1.0
    assert [t['cache_rows_before'] for t in result['trials']] == [0, 0, 0]
    assert [t['cache_rows_after'] for t in result['trials']] == [1, 1, 1]
    assert [t['attempts_until_acceptance'] for t in result['trials']] == [1, 1, 1]
    assert [t['source_qualification_coverage'] for t in result['trials']] == [1.0] * 3
    assert [t['source_eligibility_agreement'] for t in result['trials']] == [1.0] * 3
    assert result['stability']['denominators'] == [7, 7, 7]
    assert all(v > 0 for v in result['stability']['group_identity_agreement'])
    assert result['stability']['eligibility_agreement'] == [1.0] * 3
    assert len(set(result['stability']['merge_split_rate'])) == 1
    assert result['stability']['semantic_duplicate_rate'] == [0.0] * 3
    assert result['denominator_agreement'] == [True] * 3
    with pytest.raises(FileExistsError):
        fresh_extraction_trials(settings, None, fixture, 1, tmp_path / 'trials')


def test_unrepaired_submissions_exhaust_without_cache_or_matching(tmp_path):
    settings = Settings(home=tmp_path, model='offline', max_iterations=10, otel_endpoint='')
    settings.ensure_home()
    conn = connect_career(tmp_path)
    conn.execute("INSERT INTO career_profile(id,raw_input_json,confirmed) VALUES(1,'{}',1)")
    conn.commit()
    shapes = ['inherited_major', 'route_subject', 'scored_generic_writing', 'punctuation',
              'punctuation', 'missing_route', 'scored_generic_writing', 'missing_route', 'missing_route', 'route_outside_group']
    calls = []

    def create(**kwargs):
        assert kwargs['system'].startswith('Extract source-supported qualification semantics')
        shape = shapes[len(calls)]
        calls.append(shape)
        block = SimpleNamespace(type='tool_use', id=f'submit-{len(calls)}',
                                name='submit_stage_result',
                                input={'result': invalid_ir()})
        return SimpleNamespace(content=[block], stop_reason='tool_use',
                               usage=SimpleNamespace(input_tokens=0, output_tokens=0))

    try:
        client = SimpleNamespace(messages=SimpleNamespace(create=create))
        with pytest.raises(ValueError) as error:
            analyze_job(conn, JD, settings, client)
        assert 'UNKNOWN_SOURCE_REF' in str(error.value)
        assert len(calls) == 10
        assert cached_extraction(conn, JD) is None
        assert conn.execute('SELECT status FROM jobs').fetchone()[0] == 'failed'
        assert conn.execute('SELECT count(*) FROM job_matches').fetchone()[0] == 0
        events = [json.loads(line) for path in (tmp_path / 'traces').glob('*.jsonl')
                  for line in path.read_text().splitlines()]
        errors = [e['output'] for e in events if e['type'] == 'tool']
        assert len(errors) == 10
        assert all('UNKNOWN_SOURCE_REF' in output for output in errors)
        assert events[-1]['reply'] == 'Career job extraction failed'
        assert events[-1]['iterations'] == 10
    finally:
        conn.close()
