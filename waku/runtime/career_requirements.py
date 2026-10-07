"""Canonical JD scoring groups, structural policy and immutable extraction reuse.

This module validates questions and denominator membership. It does not judge
whether Career Evidence satisfies a question.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata

POLICY_VERSION = 'groups-v1'
CATEGORIES = ('education', 'experience', 'skill', 'certification', 'language',
              'demonstrated_capability', 'logistics', 'personal_trait', 'other')
ELIGIBILITIES = ('SCORED', 'NEEDS_CONFIRMATION', 'NON_SCORABLE')
KINDS = ('degree', 'major', 'technology', 'experience', 'certification', 'language',
         'behavior', 'logistics', 'trait', 'other')


def object_schema(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


TEXT = {'type': 'string'}
TEXTS = {'type': 'array', 'items': TEXT}
CONSTRAINT_SCHEMA = object_schema({
    'kind': {'type': 'string', 'enum': list(KINDS)}, 'subject': TEXT,
    'text': TEXT, 'source_excerpt': TEXT})
CONSTRAINTS_SCHEMA = object_schema({
    'operator': {'type': 'string', 'enum': ['ALL', 'ANY']},
    'items': {'type': 'array', 'minItems': 1, 'maxItems': 20, 'items': CONSTRAINT_SCHEMA}})
ROUTE_SCHEMA = object_schema({'condition': TEXT, 'source_excerpt': TEXT,
                              'constraints': CONSTRAINTS_SCHEMA})
GROUP_SCHEMA = object_schema({
    'text': TEXT, 'category': {'type': 'string', 'enum': list(CATEGORIES)},
    'importance': {'type': 'string', 'enum': ['required', 'preferred']},
    'keywords': TEXTS, 'source_excerpt': TEXT,
    'eligibility': {'type': 'string', 'enum': list(ELIGIBILITIES)},
    'eligibility_reason': TEXT, 'constraints': CONSTRAINTS_SCHEMA,
    'alternative_route': {'anyOf': [ROUTE_SCHEMA, {'type': 'null'}]}})
EXTRACTION_SCHEMA = object_schema({
    'title': TEXT, 'summary': TEXT, 'responsibilities': TEXTS,
    'requirements': {'type': 'array', 'maxItems': 60, 'items': GROUP_SCHEMA}})

EXTRACTION_PROMPT = '''Extract canonical requirement groups from the pasted JD only.
Each group is one independent scoring opportunity, not one opportunity per comma.
Use the closed schema categories. Never turn responsibilities into invented qualifications.
Retain all qualification clauses, including excluded and confirmation clauses.
Keep degree and major in ONE education group with ALL constraints. Keep a bachelor's
relaxation/exception as alternative_route in that group, NEVER a separate preference.
Use ANY for alternatives such as LabVIEW OR C++; do not score each option separately.
Use ALL for jointly required constraints. A route has a verbatim condition excerpt
and its own shallow ALL/ANY constraints; do not nest expression trees.
Each constraint needs kind, a concise subject copied literally from its source_excerpt,
a faithful text, and the smallest verbatim source_excerpt that contains that constraint.
Subjects name the qualification (e.g. Python), not paraphrases such as Python proficiency.
Do not split or repeat the same qualification across groups, even when the JD repeats
or paraphrases it. Combine its source wording into one group. Do not use overlapping
constraint excerpts across groups. Degree/major constraints share the education group.
Choose eligibility BEFORE matching: SCORED for objective qualifications and observable
capabilities; NEEDS_CONFIRMATION for travel, shifts, relocation, availability or driver's
license declarations; NON_SCORABLE for vague traits, health, diligence, dedication,
morality, responsibility or undefined initiative. Never infer health or character from
career success. A generic teamwork spirit or writing ability without observable criteria
is NON_SCORABLE; actual collaboration tasks and writing outputs can be demonstrated_capability.
A group cannot mix scored constraints with excluded/confirmation constraints: separate
those clauses. All education/skill/experience/certification/language groups must use
appropriate constraint kinds. An exception inherits its education group's importance.
Use explicit required/preferred wording; default to required when unspecified.
Provide a short eligibility_reason. Use an empty requirements list only when the JD
has no qualification clauses. Do not assign IDs, source offsets or calculate a score.'''

# These are eligibility guards, not a semantic MATCH/PARTIAL/GAP rubric.
TRAITS = re.compile(
    r'身体健康|吃苦耐劳|爱岗敬业|职业道德|道德品质|责任心|进取意识|敬业|品行|'
    r'\b(healthy|good health|physical fitness|integrity|work ethic|ethical character|sense of responsibility|strong responsibility|good character|diligen\w*|dedication|dedicated to work|dedicated employee|moral\w*|initiative|personality|'
    r'hard.?working|conscientious|responsible attitude)\b', re.IGNORECASE)
LOGISTICS = re.compile(
    r'出差|倒班|轮班|夜班|搬迁|异地|驾照|驾驶证|到岗|'
    r'\b(willing(?:ness)? to travel|able to travel|travel required|travel up to|business travel|'
    r'willing(?:ness)? to relocate|relocation required|work shifts?|shift availability|'
    r'available to start|driver.?s? licen[cs]e)\b', re.IGNORECASE)
OBSERVABLE = re.compile(
    r'组织协调|协调|沟通|协作|撰写|编写|文档|报告|\b(coordinat\w*|collaborat\w*|'
    r'communicat\w*|write|writing|document\w*|reports?)\b', re.IGNORECASE)
GENERIC_CAPABILITY = re.compile(
    r'^\s*(具备一定的)?文字表达能力[。.]?\s*$|团队合作精神|\b(teamwork spirit|'
    r'good writing skills|written expression ability)\b', re.IGNORECASE)
EXCEPTION = re.compile(r'放宽|破格|例外|\b(exception|waiv\w*|relax\w*|in lieu|instead of)\b', re.IGNORECASE)
SUBJECT_ALIASES = {
    'teamwork': 'collaboration', 'team collaboration': 'collaboration',
    'team cooperation': 'collaboration', '团队协作': 'collaboration', '团队合作': 'collaboration',
    'labview': 'labview', '1abview': 'labview', 'c plus plus': 'c++',
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def extraction_key(jd):
    return digest([POLICY_VERSION, jd])


def normalized_subject(value):
    text = unicodedata.normalize('NFKC', value).strip().casefold()
    text = re.sub(r'\b(proficiency|proficient|experience|experienced|programming|language|languages|skill|skills|knowledge|expertise|using|with|in|of|the|a|an)\b', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return SUBJECT_ALIASES.get(text, text)


def _object(value, schema, label):
    if not isinstance(value, dict) or set(value) != set(schema['properties']):
        raise ValueError(f'{label} must contain exactly the canonical schema fields.')


def _text(value, label, empty=False):
    if not isinstance(value, str) or len(value) > 20000 or (not empty and not value.strip()):
        raise ValueError(f'{label} must be bounded text.')


def _texts(value, label):
    if not isinstance(value, list) or len(value) > 100:
        raise ValueError(f'{label} must be a bounded text list.')
    for item in value:
        _text(item, label)


def source_spans(jd, excerpt):
    _text(excerpt, 'Source excerpt')
    spans = [{'start': m.start(), 'end': m.end()} for m in re.finditer(re.escape(excerpt), jd)]
    if not spans:
        raise ValueError('Requirement excerpts must occur in the pasted JD.')
    if len(spans) > 100:
        raise ValueError('Source excerpt is ambiguous; use a longer verbatim excerpt.')
    return spans


def _constraints(value, jd):
    _object(value, CONSTRAINTS_SCHEMA, 'Constraints')
    if value['operator'] not in ('ALL', 'ANY'):
        raise ValueError('Constraints require ALL or ANY.')
    items = value['items']
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        raise ValueError('Constraints require 1 to 20 items.')
    keys, spans = [], []
    for item in items:
        _object(item, CONSTRAINT_SCHEMA, 'Constraint')
        if item['kind'] not in KINDS:
            raise ValueError('Unsupported constraint kind.')
        for key in ('text', 'subject', 'source_excerpt'):
            _text(item[key], key)
        if item['subject'].casefold() not in item['source_excerpt'].casefold():
            raise ValueError('Constraint subject must be literal source wording.')
        keys.append((item['kind'], normalized_subject(item['subject'])))
        spans.extend(source_spans(jd, item['source_excerpt']))
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate material constraints are not allowed.')
    if value['operator'] == 'ANY' and len(items) < 2:
        raise ValueError('ANY requires at least two alternatives.')
    return keys, spans


def eligibility_for(item):
    """Decide disposition from original constraint wording, never Career Evidence."""
    source = item['source_excerpt']
    trait_source = source
    if item['kind'] == 'behavior' and OBSERVABLE.search(source):
        trait_source = re.sub(r'进取意识|\binitiative\b', '', source, flags=re.IGNORECASE)
    if TRAITS.search(trait_source) or item['kind'] == 'trait':
        return 'NON_SCORABLE'
    if LOGISTICS.search(source) or item['kind'] == 'logistics':
        return 'NEEDS_CONFIRMATION'
    if item['kind'] == 'behavior':
        return ('SCORED' if OBSERVABLE.search(source) and not GENERIC_CAPABILITY.search(source)
                else 'NON_SCORABLE')
    if item['kind'] == 'other':
        return 'NON_SCORABLE'
    return 'SCORED'


def _group_policy(group):
    items = group['constraints']['items']
    decisions = {eligibility_for(item) for item in items}
    source = group['source_excerpt']
    if TRAITS.search(source) and not (all(i['kind'] == 'behavior' for i in items)
                                     and OBSERVABLE.search(source)
                                     and not TRAITS.search(re.sub(r'进取意识|\binitiative\b', '', source, flags=re.IGNORECASE))):
        decisions.add('NON_SCORABLE')
    elif LOGISTICS.search(source):
        decisions.add('NEEDS_CONFIRMATION')
    if len(decisions) != 1 or group['eligibility'] not in decisions:
        raise ValueError('Eligibility must follow source constraints; separate mixed dispositions.')
    kinds = {i['kind'] for i in items}
    allowed = {
        'education': {'degree', 'major'}, 'experience': {'experience'},
        'skill': {'technology', 'experience'}, 'certification': {'certification'}, 'language': {'language'},
        'demonstrated_capability': {'behavior'}, 'logistics': {'logistics'},
        'personal_trait': {'trait'}, 'other': {'other'},
    }
    if not kinds <= allowed[group['category']]:
        raise ValueError('Category must agree with material constraint kinds.')
    if group['category'] == 'personal_trait' and group['eligibility'] != 'NON_SCORABLE':
        raise ValueError('Personal traits cannot enter Coverage.')
    if group['category'] == 'logistics' and group['eligibility'] != 'NEEDS_CONFIRMATION':
        raise ValueError('Logistics require user confirmation.')


def _importance(group, jd):
    excerpts = []
    for span in source_spans(jd, group['source_excerpt']):
        prefix = re.split(r'[.。;；\n]', jd[max(0, span['start'] - 80):span['start']])[-1]
        suffix = re.split(r'[.。;；\n]', jd[span['end']:span['end'] + 32])[0]
        excerpts.append(prefix + group['source_excerpt'] + suffix)
    if any(re.search(r'\brequired\b|必须|必需|必备', text, re.IGNORECASE) for text in excerpts):
        expected = 'required'
    elif any(re.search(r'\bpreferred\b|优先', text, re.IGNORECASE) for text in excerpts):
        expected = 'preferred'
    else:
        expected = 'required'
    if group['importance'] != expected:
        raise ValueError('Importance must follow explicit source wording; default is required.')


def validate_extraction(result, jd):
    """Reject duplicate opportunities and invalid structure before caching or matching."""
    _object(result, EXTRACTION_SCHEMA, 'Job analysis')
    for key in ('title', 'summary'):
        _text(result[key], key, empty=True)
    _texts(result['responsibilities'], 'Responsibilities')
    groups = result['requirements']
    if not isinstance(groups, list) or len(groups) > 60:
        raise ValueError('Extract at most 60 canonical requirement groups.')
    seen_text, seen_keys, prior_spans = set(), set(), []
    education = False
    canonical = []
    for original in groups:
        _object(original, GROUP_SCHEMA, 'Requirement group')
        group = copy.deepcopy(original)
        if not isinstance(group['category'], str) or group['category'] not in CATEGORIES:
            raise ValueError('Unsupported requirement category.')
        if not isinstance(group['importance'], str) or group['importance'] not in ('required', 'preferred'):
            raise ValueError('Importance must be required or preferred.')
        if not isinstance(group['eligibility'], str) or group['eligibility'] not in ELIGIBILITIES:
            raise ValueError('Missing or unsupported eligibility.')
        for key in ('text', 'eligibility_reason', 'source_excerpt'):
            _text(group[key], key)
        _texts(group['keywords'], 'Keywords')
        source_spans(jd, group['source_excerpt'])
        keys, spans = _constraints(group['constraints'], jd)
        if any(item['source_excerpt'] not in group['source_excerpt']
               for item in group['constraints']['items']):
            raise ValueError('Constraint provenance must belong to its group source excerpt.')
        _group_policy(group)
        if group['category'] == 'education':
            if re.search(r'专业|\bdegree in\b|\bmajor\b', group['source_excerpt'], re.IGNORECASE) and not any(
                    item['kind'] == 'major' for item in group['constraints']['items']):
                raise ValueError('A degree and major clause requires both constraints in one education group.')
            if education:
                raise ValueError('Degree, major and alternative routes require one education group.')
            education = True
        elif EXCEPTION.search(group['source_excerpt']):
            raise ValueError('Alternative qualification routes cannot be independent requirements.')
        route = group['alternative_route']
        if route is not None:
            if group['category'] != 'education':
                raise ValueError('Only education supports a conditional qualification route in this policy.')
            _object(route, ROUTE_SCHEMA, 'Alternative route')
            _text(route['condition'], 'Alternative condition')
            source_spans(jd, route['source_excerpt'])
            if route['condition'] not in route['source_excerpt']:
                raise ValueError('Alternative condition must use verbatim route wording.')
            if route['source_excerpt'] not in group['source_excerpt']:
                raise ValueError('Alternative route provenance must belong to its education group.')
            route_keys, route_spans = _constraints(route['constraints'], jd)
            if not any(kind == 'degree' for kind, subject in route_keys):
                raise ValueError('An education alternative requires a degree constraint.')
            if any(item['source_excerpt'] not in route['source_excerpt']
                   for item in route['constraints']['items']):
                raise ValueError('Alternative constraints must belong to the route source.')
            spans.extend(route_spans + source_spans(jd, route['source_excerpt']))
        elif EXCEPTION.search(group['source_excerpt']):
            raise ValueError('An education exception requires alternative_route, not independent credit.')
        _importance(group, jd)
        text_key = normalized_subject(group['text'])
        # Source overlap is conservative: ambiguous excerpts must be narrowed,
        # never silently counted twice. Literal subjects also catch repetitions
        # in different sentences, including paraphrases around the same skill.
        subjects = {subject for kind, subject in keys}
        if text_key in seen_text or subjects & seen_keys:
            raise ValueError('Duplicate or paraphrased qualification groups are not allowed.')
        if any(a['start'] < b['end'] and b['start'] < a['end'] for a in spans for b in prior_spans):
            raise ValueError('Overlapping groups cannot create duplicate scoring opportunities.')
        seen_text.add(text_key)
        seen_keys.update(subjects)
        prior_spans.extend(spans)
        group['source_spans'] = sorted([{'start': a, 'end': b} for a, b in
                                        {(s['start'], s['end']) for s in spans}], key=lambda s: s['start'])
        group['semantic_id'] = digest([extraction_key(jd), sorted(keys)])
        canonical.append(group)
    _validate_technology_alternatives(canonical, jd)
    _require_known_clauses(canonical, jd)
    return dict(result, requirements=canonical, policy_version=POLICY_VERSION, jd_key=extraction_key(jd))


def _require_known_clauses(groups, jd):
    # Fail closed for recognizable policy-sensitive source clauses. This guard
    # does not claim to understand every arbitrary qualification in natural language.
    sensitive = re.compile(
        TRAITS.pattern + '|' + LOGISTICS.pattern +
        r"|硕士|本科学历|学历|相关专业|\bmaster['’]?s? degree\b|\bbachelor['’]?s? degree\b|"
        r'\bdegree in\b|\bLabVIEW\b|\b1abview\b|C\+\+', re.IGNORECASE)
    spans = [span for group in groups for span in source_spans(jd, group['source_excerpt'])]
    for match in sensitive.finditer(jd):
        if not any(span['start'] <= match.start() and span['end'] >= match.end() for span in spans):
            raise ValueError('Retain policy-sensitive JD clauses with group provenance.')


def _validate_technology_alternatives(groups, jd):
    technologies = [(index, group['constraints']['operator'], item)
                    for index, group in enumerate(groups)
                    for item in group['constraints']['items'] if item['kind'] == 'technology']
    for owner, operator, item in technologies:
        if re.search(r'\bor\b|或者|或|任意一种', item['source_excerpt'], re.IGNORECASE) and operator != 'ANY':
            raise ValueError('Technology alternatives require one ANY scoring group.')
    for position, (owner, operator, item) in enumerate(technologies):
        for other_owner, other_operator, other in technologies[position + 1:]:
            a = source_spans(jd, item['subject'])[0]
            b = source_spans(jd, other['subject'])[0]
            left, right = sorted((a, b), key=lambda span: span['start'])
            between = jd[left['end']:right['start']]
            suffix = jd[right['end']:right['end'] + 16]
            if len(between) > 100 or re.search(r'[。;；\n]|\.\s', between):
                continue
            alternative = re.search(r'\bor\b|或者|或', between, re.IGNORECASE) or (
                re.fullmatch(r'[、,，\s]*', between) and re.search(r'任意一种|其中一种', suffix))
            if alternative and (owner != other_owner or operator != 'ANY' or other_operator != 'ANY'):
                raise ValueError('Technology alternatives require one ANY scoring group.')


def scored_groups(requirements):
    for group in requirements:
        if group.get('eligibility') not in ELIGIBILITIES:
            raise ValueError('Every scoring group requires eligibility before matching.')
    return [g for g in requirements if g['eligibility'] == 'SCORED']


def cached_extraction(conn, jd):
    row = conn.execute('SELECT extraction_json FROM career_requirement_sets WHERE jd_key=? AND raw_jd=? '
                       'AND policy_version=?', (extraction_key(jd), jd, POLICY_VERSION)).fetchone()
    return json.loads(row[0]) if row else None


def cache_extraction(conn, jd, extracted):
    # First validated publication wins, including concurrent processes. A later
    # candidate cannot silently replace a set already used for this JD/policy.
    with conn:
        conn.execute('INSERT INTO career_requirement_sets VALUES(?,?,?,?) ON CONFLICT(jd_key) DO NOTHING',
                     (extraction_key(jd), jd, POLICY_VERSION, json.dumps(extracted, ensure_ascii=False)))
    return cached_extraction(conn, jd)


def prune_extractions(conn):
    jobs = [(row['raw_jd'], json.loads(row['report_json'] or '{}')) for row in
            conn.execute('SELECT raw_jd,report_json FROM jobs')]
    for row in conn.execute('SELECT jd_key,raw_jd FROM career_requirement_sets').fetchall():
        if not any(jd == row['raw_jd'] or report.get('jd_key') == row['jd_key'] for jd, report in jobs):
            conn.execute('DELETE FROM career_requirement_sets WHERE jd_key=?', (row['jd_key'],))


def policy_current(report):
    return bool(report and report.get('extraction_policy_version') == POLICY_VERSION)
