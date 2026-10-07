"""Resolve reviewed literal semantic fixture selections into source-addressed IR."""
import copy

from waku.runtime.career_extraction_compiler import build_source_catalog


def source_ref(catalog, text, occurrence=0):
    start = -1
    for _ in range(occurrence + 1):
        start = catalog.raw.index(text, start + 1)
    end = start + len(text)
    return {'first': next(t.ref for t in catalog.items if t.start == start),
            'last': next(t.ref for t in catalog.items if t.end == end)}


def executable_ir(jd):
    """Reviewed selections for the two synthetic executable JD layouts."""
    import json
    from pathlib import Path

    fixture = json.loads((Path(__file__).parent / 'fixtures/career_extraction_executability.json').read_text())
    original = build_source_catalog(fixture['jd'])
    target = build_source_catalog(jd)
    ir = copy.deepcopy(fixture['semantic_ir'])

    def remap(value):
        if isinstance(value, dict):
            if set(value) == {'first', 'last'}:
                text = original.resolve(value)[2]
                value.update(source_ref(target, text))
            else:
                for child in value.values():
                    remap(child)
        elif isinstance(value, list):
            for child in value:
                remap(child)
    for fact in ir['facts']:
        support_text = original.resolve(fact['support'])[2]
        subject_text = original.resolve(fact['subject'])[2]
        fact['support'] = source_ref(target, support_text)
        start, end, _ = target.resolve(fact['support'])
        subject_start = jd.index(subject_text, start, end)
        fact['subject'] = {'first': next(t.ref for t in target.items if t.start == subject_start),
                           'last': next(t.ref for t in target.items if t.end == subject_start + len(subject_text))}
    remap(ir['opportunities'])
    remap(ir['responsibilities'])
    return ir


def excluded_ir_for(extraction):
    """Select the reviewed excluded clauses for the browser's shortened synthetic JD."""
    jd = '\n'.join(g['source_excerpt'] for g in extraction['requirements'])
    catalog = build_source_catalog(jd)
    selections = [('trait', '身体健康', '身体健康，吃苦耐劳，爱岗敬业'),
                  ('trait', '责任心', '责任心强，良好的职业道德'),
                  ('trait', 'initiative', 'Strong initiative and teamwork spirit'),
                  ('logistics', 'travel', 'Willing to travel, work shifts and relocate')]
    facts = [{'id': f'f{i}', 'kind': kind, 'support': source_ref(catalog, support),
              'subject': source_ref(catalog, subject)}
             for i, (kind, subject, support) in enumerate(selections)]
    return {'title': extraction['title'], 'summary': '', 'responsibilities': [], 'facts': facts,
            'opportunities': [{'operator': 'ALL', 'facts': [f['id']], 'fallback': None} for f in facts],
            'repeats': []}
