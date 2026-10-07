"""Pure source-addressed extraction compiler; publication remains coordinator-owned.

References name Python-tokenized source endpoints, never model-authored offsets.
The catalog retains every character, including unrecognized sections and whitespace.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from waku.runtime.career_requirements import (
    EXCEPTION,
    KINDS,
    LOGISTICS,
    SECTION,
    TRAITS,
    eligibility_for,
    importance_for,
    normalized_subject,
    object_schema,
    qualification_spans,
    validate_extraction,
)


@dataclass(frozen=True)
class SourceItem:
    ref: str
    text: str
    start: int
    end: int
    section: str | None


@dataclass(frozen=True)
class SourceCatalog:
    raw: str
    items: tuple[SourceItem, ...]

    def resolve(self, reference):
        _shape(reference, {'first', 'last'}, 'source range')
        endpoints = []
        for key in ('first', 'last'):
            ref = reference[key]
            if not isinstance(ref, str) or not re.fullmatch(r't(?:0|[1-9][0-9]*)', ref):
                _fail('UNKNOWN_SOURCE_REF', f'Unknown source reference: {ref}. Use IDs from the supplied catalog.')
            index = int(ref[1:])
            if index >= len(self.items):
                _fail('UNKNOWN_SOURCE_REF', f'Unknown source reference: {ref}. Use IDs from the supplied catalog.')
            endpoints.append(self.items[index])
        first, last = endpoints
        if first.start > last.start:
            _fail('INVALID_SOURCE_RANGE', 'Put source endpoints in original order.')
        return first.start, last.end, self.raw[first.start:last.end]

    def model_input(self):
        """Expose references and original text; Python retains offsets privately."""
        return [{'ref': item.ref, 'text': item.text, 'section': item.section} for item in self.items]

    def prompt_input(self):
        """Keep exact raw text once, explicit token IDs and section transitions."""
        sections = []
        previous = object()
        for item in self.items:
            if item.section != previous:
                sections.append([item.ref, item.section])
                previous = item.section
        return {'raw': self.raw, 'tokens': [[t.ref, t.text] for t in self.items],
                'sections': sections}


def build_source_catalog(jd):
    if not isinstance(jd, str):
        raise TypeError('Source JD must be text.')
    headings = list(SECTION.finditer(jd))
    unknown = list(re.finditer(r'(?m)^\s*(?:#{1,4}\s*[^\n]+|[^\n:：]+[:：])\s*$', jd))
    items = []
    # English words stay readable; C++ uses three addressable tokens. Chinese
    # characters remain individually addressable without a segmentation dependency.
    for match in re.finditer(r'[A-Za-z0-9_]+|[^\s]', jd):
        section = next((h['title'] for h in reversed(headings) if h.end() <= match.start()), None)
        latest = next((h for h in reversed(headings) if h.end() <= match.start()), None)
        if any((latest is None or h.start() > latest.start()) and h.end() <= match.start() for h in unknown):
            section = None
        items.append(SourceItem(f't{len(items)}', match.group(), match.start(), match.end(), section))
    return SourceCatalog(jd, tuple(items))


REF_SCHEMA = object_schema({'first': {'type': 'string'}, 'last': {'type': 'string'}})
FACT_SCHEMA = object_schema({'id': {'type': 'string'}, 'kind': {'type': 'string', 'enum': list(KINDS)},
                             'support': REF_SCHEMA, 'subject': REF_SCHEMA})
FACT_REFS = {'type': 'array', 'minItems': 1, 'maxItems': 20, 'items': {'type': 'string'}}
OPERATOR = {'type': 'string', 'enum': ['ALL', 'ANY']}
FALLBACK_SCHEMA = object_schema({'operator': OPERATOR, 'facts': FACT_REFS, 'condition': REF_SCHEMA,
                                 'inherit': {'type': 'array', 'maxItems': 20, 'items': {'type': 'string'}},
                                 'inheritance_support': {'anyOf': [REF_SCHEMA, {'type': 'null'}]}})
OPPORTUNITY_SCHEMA = object_schema({'operator': OPERATOR, 'facts': FACT_REFS,
                                    'fallback': {'anyOf': [FALLBACK_SCHEMA, {'type': 'null'}]}})
SEMANTIC_IR_SCHEMA = object_schema({
    'title': {'type': 'string'}, 'summary': {'type': 'string'},
    'responsibilities': {'type': 'array', 'maxItems': 100, 'items': REF_SCHEMA},
    'facts': {'type': 'array', 'maxItems': 120, 'items': FACT_SCHEMA},
    'opportunities': {'type': 'array', 'maxItems': 60, 'items': OPPORTUNITY_SCHEMA},
    'repeats': {'type': 'array', 'maxItems': 120, 'items': object_schema({
        'fact': {'type': 'string'}, 'of': {'type': 'string'}})},
})


class ExtractionRejection(ValueError):
    """Retain a machine-readable boundary without exposing canonical repair tasks."""

    def __init__(self, failure_class, code, message):
        self.failure_class = failure_class
        self.code = code
        super().__init__(f'{code}: {message}')


def _fail(code, message):
    failure_class = ('ir_validation' if code in {'MALFORMED_IR', 'UNKNOWN_SOURCE_REF',
                     'INVALID_SOURCE_RANGE', 'UNKNOWN_FACT_REF'} else 'semantic_rejection')
    raise ExtractionRejection(failure_class, code, message)


def _shape(value, keys, label):
    if not isinstance(value, dict) or set(value) != keys:
        _fail('MALFORMED_IR', f'{label} must contain exactly {sorted(keys)}.')


def _array(value, maximum, label, minimum=0):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        _fail('MALFORMED_IR', f'{label} requires {minimum} to {maximum} entries.')


def _canonical(text):
    return re.sub(r'(?<![A-Za-z0-9_])1abview(?![A-Za-z0-9_])', 'LabVIEW', text, flags=re.IGNORECASE)


def _criteria_text(constraints):
    # Shared support can express multiple material constraints in one phrase.
    # Keep that phrase once rather than repeating it for every selected subject.
    texts = dict.fromkeys(item['text'] for item in constraints['items'])
    return (' OR ' if constraints['operator'] == 'ANY' else ' AND ').join(texts)


KIND_SUPPORT = {
    'degree': r'学历|本科|硕士|博士|学士|\b(degree|bachelor|master|phd|doctorate)\b',
    'major': r'专业|相关领域|\b(major|field|degree in|engineering|science|related)\b',
    'experience': r'经验|年|\b(experience|years?|months?|tenure)\b',
    'certification': r'证|资质|\b(certifi\w*|licen[cs]\w*)\b',
    'language': r'语|\b(English|Chinese|Mandarin|Spanish|French|German|language)\b',
    'behavior': r'能力|协调|沟通|协作|撰写|编写|\b(coordinat\w*|collaborat\w*|communicat\w*|writ\w*|document\w*|reports?|initiative)\b',
    'logistics': LOGISTICS.pattern,
    'trait': TRAITS.pattern + r'|团队合作精神|\bteamwork spirit\b',
}
INHERITANCE = re.compile(r'同(?:一|样)?专业|上述专业|相同专业|\bsame (?:major|field)\b', re.IGNORECASE)
CATEGORY_FOR = {'degree': 'education', 'major': 'education', 'technology': 'skill',
                'experience': 'experience', 'certification': 'certification', 'language': 'language',
                'behavior': 'demonstrated_capability', 'logistics': 'logistics',
                'trait': 'personal_trait', 'other': 'other'}


def _compile_extraction(catalog, ir):
    """Reject invalid semantics and return a validated groups-v1 value, without I/O.

    Canonical criteria use source wording with only the reviewed 1abview correction.
    This version deliberately offers no free-form criterion capable of adding facts.
    Existing lexical guards remain conservative, rather than proving entailment.
    """
    _shape(ir, set(SEMANTIC_IR_SCHEMA['properties']), 'semantic extraction')
    for name, maximum in [('facts', 120), ('opportunities', 60), ('repeats', 120), ('responsibilities', 100)]:
        _array(ir[name], maximum, name)
    facts, bounds = {}, {}
    clauses = qualification_spans(catalog.raw)
    for fact in ir['facts']:
        _shape(fact, set(FACT_SCHEMA['properties']), 'fact')
        key, kind = fact['id'], fact['kind']
        if not isinstance(key, str) or not key.strip() or len(key) > 64 or key in facts:
            _fail('MALFORMED_IR', 'Use unique bounded fact IDs.')
        if not isinstance(kind, str) or kind not in KINDS:
            _fail('MALFORMED_IR', 'Use a supported semantic kind.')
        start, end, support = catalog.resolve(fact['support'])
        left, right, subject = catalog.resolve(fact['subject'])
        if not start <= left < right <= end:
            _fail('UNSUPPORTED_FACT', 'Put the literal subject inside its supporting source range.')
        if not any(c['start'] <= start and end <= c['end'] for c in clauses):
            _fail('UNSUPPORTED_FACT', 'Use one qualification clause, rather than responsibility-only source.')
        if kind in KIND_SUPPORT and not re.search(KIND_SUPPORT[kind], support, re.IGNORECASE):
            _fail('UNSUPPORTED_FACT', f'Choose a source-supported kind for fact {key}.')
        if kind in {'degree', 'major', 'technology', 'experience', 'certification', 'language'} and (
                TRAITS.search(support) or LOGISTICS.search(support)):
            _fail('INVALID_RELATIONSHIP', 'Narrow objective fact support to separate traits or logistics.')
        facts[key] = {'kind': kind, 'subject': subject, 'text': _canonical(support), 'source_excerpt': support}
        bounds[key] = (start, end)

    repeated = {}
    for link in ir['repeats']:
        _shape(link, {'fact', 'of'}, 'repeat link')
        a, b = link['fact'], link['of']
        if (not isinstance(a, str) or not isinstance(b, str) or a not in facts or b not in facts
                or a == b or a in repeated):
            _fail('INVALID_REPEAT', 'Link each repeated occurrence once to an existing primary fact.')
        first, second = facts[a], facts[b]
        if (first['kind'] != second['kind'] or normalized_subject(first['subject']) != normalized_subject(second['subject'])
                or _canonical(first['source_excerpt']).casefold() != _canonical(second['source_excerpt']).casefold()
                or bounds[a] == bounds[b]):
            _fail('INVALID_REPEAT', 'Repeat links require distinct occurrences with the same criterion and threshold.')
        repeated[a] = b
    if set(repeated) & set(repeated.values()):
        _fail('INVALID_REPEAT', 'Link repeats directly to primary facts; do not chain links.')

    used = set()

    def selected(refs, operator, allow_used=False):
        _array(refs, 20, 'fact references', minimum=1)
        if not isinstance(operator, str) or operator not in {'ALL', 'ANY'}:
            _fail('INVALID_RELATIONSHIP', 'Choose explicit ALL or ANY.')
        if any(not isinstance(ref, str) or ref not in facts for ref in refs):
            _fail('UNKNOWN_FACT_REF', 'Use defined fact IDs.')
        if len(set(refs)) != len(refs) or any(ref in repeated for ref in refs):
            _fail('DUPLICATE_OPPORTUNITY', 'Reference a primary fact once; attach repeats with explicit links.')
        if not allow_used and used.intersection(refs):
            _fail('DUPLICATE_OPPORTUNITY', 'Each fact belongs to exactly one opportunity or route.')
        if operator == 'ANY' and len(refs) < 2:
            _fail('INVALID_RELATIONSHIP', 'ANY requires at least two facts.')
        if not allow_used:
            used.update(refs)
        return {'operator': operator, 'items': [dict(facts[ref]) for ref in refs]}

    def envelope(refs, extra=()):
        spans = [bounds[ref] for ref in refs] + list(extra)
        return catalog.raw[min(s[0] for s in spans):max(s[1] for s in spans)]

    groups = []
    for opportunity in ir['opportunities']:
        _shape(opportunity, set(OPPORTUNITY_SCHEMA['properties']), 'opportunity')
        refs = opportunity['facts']
        constraints = selected(refs, opportunity['operator'])
        kinds = {item['kind'] for item in constraints['items']}
        categories = {CATEGORY_FOR[kind] for kind in kinds}
        if kinds <= {'technology', 'experience'} and 'technology' in kinds:
            category = 'skill'
        elif len(categories) == 1:
            category = categories.pop()
        else:
            _fail('INVALID_RELATIONSHIP', 'Separate facts whose kinds require different groups-v1 categories.')
        route, extra, all_refs = None, [], list(refs)
        fallback = opportunity['fallback']
        if fallback is not None:
            _shape(fallback, set(FALLBACK_SCHEMA['properties']), 'fallback')
            if category != 'education':
                _fail('UNSUPPORTED_FALLBACK', 'Only education supports a conditional fallback.')
            route_constraints = selected(fallback['facts'], fallback['operator'])
            if not {item['kind'] for item in route_constraints['items']} <= {'degree', 'major'}:
                _fail('UNSUPPORTED_FALLBACK', 'Use only education facts in the fallback.')
            c_start, c_end, condition = catalog.resolve(fallback['condition'])
            fallback_clauses = [c for c in clauses if c['start'] <= c_start and c_end <= c['end']
                                and EXCEPTION.search(catalog.raw[c['start']:c['end']])
                                and any(facts[ref]['kind'] == 'degree' and c['start'] <= bounds[ref][0]
                                        and bounds[ref][1] <= c['end'] for ref in fallback['facts'])]
            if not fallback_clauses:
                _fail('UNSUPPORTED_FALLBACK', 'Reference the condition in the explicit fallback degree clause.')
            route_refs = list(fallback['facts'])
            _array(fallback['inherit'], 20, 'inherited facts')
            inherited = fallback['inherit']
            route_extra = [(c_start, c_end)]
            if inherited:
                if (any(not isinstance(ref, str) or ref not in refs or facts[ref]['kind'] != 'major'
                        for ref in inherited) or len(set(inherited)) != len(inherited)):
                    _fail('UNSUPPORTED_INHERITANCE', 'Inherit only explicitly selected primary major facts.')
                i_start, i_end, inheritance = catalog.resolve(fallback['inheritance_support'])
                if not INHERITANCE.search(inheritance) or not any(
                        c['start'] <= i_start and i_end <= c['end'] for c in fallback_clauses):
                    _fail('UNSUPPORTED_INHERITANCE', 'Reference explicit same-major wording supporting inheritance.')
                route_extra.append((i_start, i_end))
                route_constraints['items'].extend(dict(facts[ref]) for ref in inherited)
                route_refs.extend(inherited)
            elif fallback['inheritance_support'] is not None:
                _fail('UNSUPPORTED_INHERITANCE', 'Declare inherited fact IDs or omit inheritance support.')
            source = envelope(route_refs, route_extra)
            if not EXCEPTION.search(source):
                _fail('UNSUPPORTED_FALLBACK', 'Reference explicit education exception wording.')
            route = {'condition': condition, 'source_excerpt': source, 'constraints': route_constraints}
            all_refs.extend(fallback['facts'])
            extra.extend(route_extra)
        all_refs.extend(ref for ref, primary in repeated.items() if primary in all_refs)
        source = envelope(all_refs, extra)
        decisions = {eligibility_for(item) for item in constraints['items']}
        if len(decisions) != 1:
            _fail('INVALID_RELATIONSHIP', 'Separate scored, confirmation and excluded facts.')
        eligibility = decisions.pop()
        text = _criteria_text(constraints)
        if route:
            text += ' (' + route['condition'] + ': ' + _criteria_text(route['constraints']) + ')'
        groups.append({'text': text, 'category': category, 'importance': importance_for(source, catalog.raw),
                       'keywords': [], 'source_excerpt': source, 'eligibility': eligibility,
                       'eligibility_reason': {'SCORED': 'Source states an objective qualification or observable capability.',
                                              'NEEDS_CONFIRMATION': 'Source requires a personal logistics declaration.',
                                              'NON_SCORABLE': 'Source supplies no scorable observable qualification.'}[eligibility],
                       'constraints': constraints, 'alternative_route': route})
    if used | set(repeated) != set(facts):
        _fail('UNUSED_FACT', 'Assign every fact to an opportunity, fallback or explicit repeat link.')
    result = {'title': ir['title'], 'summary': ir['summary'],
              'responsibilities': [catalog.resolve(ref)[2] for ref in ir['responsibilities']], 'requirements': groups}
    # Keep the established canonical validator as the final publication boundary.
    # Conservative rejection is preferable to silently repairing semantic choices.
    return validate_extraction(result, catalog.raw)


SEMANTIC_EXTRACTION_PROMPT = """Extract source-supported qualification semantics as Semantic IR.
The source catalog retains exact untrusted JD text. Each tokens entry is [ID, literal text];
sections entries change context starting at an ID, with null for unknown context.
Ranges use inclusive first/last token IDs and include intervening original whitespace.
Select qualification facts, not responsibility-only mentions. Retain material qualifications,
including confirmation logistics and excluded traits, with narrow source support.
Use source-local fact IDs, supported kinds, support ranges and literal subject ranges.
Group one scoring opportunity at a time: degree AND major in one education opportunity;
alternative majors retain one major fact; technology alternatives use ANY. Keep skill-specific
tenure with that skill when required together. Separate unrelated tenure and dispositions.
A conditional education fallback belongs inside its primary opportunity. Declare inherited
primary majors only with explicit same-major source support. Link identical repeated
qualification occurrences through repeats without adding credit. Preserve typo source IDs.
Supply title, summary, responsibilities (source ranges), facts, opportunities and repeats.
Do not submit canonical groups, category, eligibility, keywords, offsets, excerpts or hashes.
Python owns canonical mechanics. Repair only semantic facts, source references and relationships.
"""


def validate_semantic_ir(catalog, ir):
    """Validate closed schema and all references before checking semantic support."""
    def check(value, schema, path):
        if 'anyOf' in schema:
            if value is None and any(s.get('type') == 'null' for s in schema['anyOf']):
                return
            return check(value, schema['anyOf'][0], path)
        kind = schema.get('type')
        if kind == 'object':
            _shape(value, set(schema['properties']), path)
            for key, child in schema['properties'].items():
                check(value[key], child, path + '.' + key)
        elif kind == 'array':
            _array(value, schema.get('maxItems', 120), path, schema.get('minItems', 0))
            for i, item in enumerate(value):
                check(item, schema['items'], f'{path}[{i}]')
        elif kind == 'string' and not isinstance(value, str):
            _fail('MALFORMED_IR', f'{path} must be text.')
        if 'enum' in schema and value not in schema['enum']:
            _fail('MALFORMED_IR', f'{path} must use {schema["enum"]}.')
        if schema == REF_SCHEMA:
            catalog.resolve(value)

    check(ir, SEMANTIC_IR_SCHEMA, 'semantic extraction')
    ids = [f['id'] for f in ir['facts']]
    if any(not key.strip() or len(key) > 64 for key in ids) or len(set(ids)) != len(ids):
        _fail('MALFORMED_IR', 'Use unique bounded fact IDs.')
    references = [r for o in ir['opportunities'] for r in o['facts']]
    for opportunity in ir['opportunities']:
        if opportunity['fallback']:
            references.extend(opportunity['fallback']['facts'])
            references.extend(opportunity['fallback']['inherit'])
    references.extend(r for link in ir['repeats'] for r in link.values())
    for ref in references:
        if ref not in ids:
            _fail('UNKNOWN_FACT_REF', f'Unknown fact reference: {ref}. Use a defined fact ID.')
    return ir


def compile_extraction(catalog, ir):
    """Compile checked semantics; final groups-v1 validation remains mandatory."""
    validate_semantic_ir(catalog, ir)
    try:
        return _compile_extraction(catalog, ir)
    except ExtractionRejection:
        raise
    except ValueError as exc:
        code = str(exc).split(' ', 1)[0].rstrip(':')
        if str(exc) == 'Technology alternatives require one ANY scoring group.':
            _fail('INVALID_RELATIONSHIP', 'Technology alternatives require one ANY opportunity.')
        if str(exc).startswith('Duplicate'):
            _fail('DUPLICATE_OPPORTUNITY', 'These facts create a duplicate scoring opportunity.')
        if not re.fullmatch(r'[A-Z][A-Z_]+', code):
            code = 'FINAL_CANONICAL_VALIDATION'
        semantic = code in {'MISSING_QUALIFICATION', 'INVALID_ALTERNATIVE_ROUTE',
                            'DUPLICATE_REQUIREMENT'}
        message = ('Represent every material qualification clause with supported facts and relationships.'
                   if code == 'MISSING_QUALIFICATION' else
                   'Review selected fact support, opportunity grouping, ALL/ANY and fallback relationships. '
                   'If those choices are faithful, this source may exceed current compiler limits.')
        raise ExtractionRejection('semantic_rejection' if semantic else 'compiler_rejection',
                                  code, message) from exc


def extraction_input(catalog, job_id=None):
    data = {'source_catalog': catalog.prompt_input()}
    if job_id is not None:
        data['job_id'] = job_id
    return data


def serialized_input_bytes(catalog):
    return len(json.dumps(extraction_input(catalog), ensure_ascii=False).encode('utf-8'))
