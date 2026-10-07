"""Matching-only material support contract; canonical extraction stays untouched."""
from __future__ import annotations

import copy

POLICY_VERSION = 'matching-v1'
SUPPORT_STATUSES = ('SATISFIED', 'PARTIALLY_SUPPORTED', 'UNSUPPORTED')


def object_schema(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


TEXT = {'type': 'string'}
TEXTS = {'type': 'array', 'items': TEXT}
CONSTRAINT_RESULT = object_schema({
    'constraint_id': TEXT, 'status': {'type': 'string', 'enum': list(SUPPORT_STATUSES)},
    'evidence_ids': TEXTS, 'reason': TEXT})
MATCH_SCHEMA = object_schema({
    'assessments': {'type': 'array', 'items': object_schema({
        'requirement_id': TEXT, 'status': {'type': 'string', 'enum': ['MATCH', 'PARTIAL', 'GAP']},
        'evidence_ids': TEXTS, 'reason': TEXT,
        'constraint_results': {'type': 'array', 'items': CONSTRAINT_RESULT},
        'satisfied_routes': TEXTS})},
    'strengths': TEXTS, 'gaps': TEXTS, 'recommended_focus': TEXTS})

# This is deliberately small. No transitive or arbitrary academic equivalence.
RELATED_MAJORS = {'computing': ['computer science', 'software engineering']}

MATCH_PROMPT = '''Assess each supplied requirement exactly once under matching-v1.
Assess every material constraint in matching_routes, including unused routes and
alternative conditions. Give each constraint SATISFIED, PARTIALLY_SUPPORTED or
UNSUPPORTED, delivered evidence IDs and a concise factual reason.
SATISFIED means sufficient factual support for the actual constraint.
PARTIALLY_SUPPORTED means genuine relevant support that is weaker, indirect or below
an explicit threshold. State the supported fact and the unmet/weaker material.
UNSUPPORTED means confirmed Career Evidence does not establish the constraint.
Never use PARTIAL as a generic uncertainty bucket or assert the person lacks a skill.
An ALL route is satisfied only when ALL its constraints are SATISFIED; an ANY route
needs at least one SATISFIED constraint. An alternative route also requires its
condition to be SATISFIED. Never mix constraints across routes. List every complete
route in satisfied_routes. MATCH requires a complete route. Otherwise PARTIAL needs
positive material support plus weaker/unmet material; no positive support means GAP.
Constraint results have no separate weights. Return exactly one status per group.
Cite the union of constraint evidence IDs at group level. Positive constraints need
citations; UNSUPPORTED has no supporting citations. Never infer support from a citation alone.
Use observable collaboration, ownership, stakeholder communication, leadership,
review coordination or writing outputs for SCORED demonstrated capabilities.
Literal 'team player' or 'strong initiative' wording is unnecessary. Project success
alone does not prove a personality trait. Excluded traits are never supplied for matching.
Judge only the actual JD criterion: good writing does not imply contract drafting,
publication or regulatory writing. Indirect relevant output can justify partial support.
Degree level and major are separate. Confirmed bachelor's < master's < doctorate
levels may satisfy a lower degree threshold, but cannot satisfy an unrelated major.
Use exact majors, explicit confirmed equivalence mappings in evidence, or ONLY the
provided reviewed_related_majors when the constraint permits a related field.
Do not invent degree/major equivalence. An unsupported major plus a supported degree
is PARTIAL, not MATCH. A lower relevant degree is partial degree-level support.
For explicit numeric/duration thresholds, meets/exceeds is SATISFIED, relevant but
below is PARTIALLY_SUPPORTED, absent relevant evidence is UNSUPPORTED. Do not invent
exact duration from ambiguous dates, double-count overlapping intervals, or use total
employment duration as skill tenure without facts connecting that duration to the skill.
Named technologies need actual support. LabVIEW OR C++ gets no partial support from
React, JavaScript, Java or general software work. No adjacent-technology equivalences
are approved by this policy. Explicit named-technology learning/prototype evidence
may be partial when below an explicitly required proficiency level.
In full coverage mode all active evidence is supplied in evidence; judge all of it
regardless of searches. In inventory mode inspect required_coverage_ids with
get_evidence before claiming GAP. Incomplete delivery is a validation failure.
Coverage proves availability, not semantic support. Searches are supplemental; a miss
cannot establish absence. Cite supplied full records or records delivered after lookup.
Never invent qualifications or facts absent from original records and explicit edits.
Summarize strengths, gaps and recommended resume focus. Do not calculate an overall score.'''


def matching_routes(group):
    """Assign stable local IDs without editing groups-v1 or its cache/identity."""
    routes = []
    for name, source in [('primary', group), ('alternative', group.get('alternative_route'))]:
        if source is None:
            continue
        constraints = [dict(item, constraint_id=f'{name}:{i}')
                       for i, item in enumerate(source['constraints']['items'])]
        route = {'route_id': name, 'operator': source['constraints']['operator'], 'items': constraints}
        if name == 'alternative':
            # The condition can be stronger than the route's abbreviated items.
            route['condition'] = {'constraint_id': 'alternative:condition', 'kind': 'condition',
                                  'text': source['condition'], 'source_excerpt': source['source_excerpt']}
        routes.append(route)
    return routes


def matching_groups(groups):
    return [dict(copy.deepcopy(g), matching_routes=matching_routes(g)) for g in groups]


def validate_material_support(assessment, group, delivered):
    """Enforce route algebra and citations; semantic truth remains model-owned."""
    routes = matching_routes(group)
    constraints = {c['constraint_id']: c for route in routes
                   for c in route['items'] + ([route['condition']] if 'condition' in route else [])}
    results = assessment['constraint_results']
    if not isinstance(results, list) or len(results) != len(constraints):
        raise ValueError('Assess every material constraint exactly once.')
    indexed = {}
    cited = set()
    for result in results:
        if not isinstance(result, dict) or set(result) != set(CONSTRAINT_RESULT['properties']):
            raise ValueError('Constraint result must contain exactly the rubric fields.')
        cid = result['constraint_id']
        if not isinstance(cid, str) or cid not in constraints or cid in indexed:
            raise ValueError('Unknown or duplicate constraint ID within group.')
        status = result['status']
        if not isinstance(status, str) or status not in SUPPORT_STATUSES:
            raise ValueError('Invalid material support status.')
        reason = result['reason']
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 20000:
            raise ValueError('Constraint reason must be bounded factual text.')
        ids = result['evidence_ids']
        if (not isinstance(ids, list) or len(ids) > 100
                or any(not isinstance(eid, str) or eid not in delivered for eid in ids)
                or len(ids) != len(set(ids))):
            raise ValueError('Constraint citations must be unique delivered evidence IDs.')
        if (status != 'UNSUPPORTED') != bool(ids):
            raise ValueError('Positive material support requires citations; unsupported material has none.')
        if (ids and constraints[cid]['kind'] in {'degree', 'major'}
                and not any(delivered[eid]['source_type'] == 'education' for eid in ids)):
            raise ValueError('Degree and major support require education evidence per constraint.')
        cited.update(ids)
        indexed[cid] = status
    complete = []
    for route in routes:
        values = [indexed[c['constraint_id']] == 'SATISFIED' for c in route['items']]
        satisfied = all(values) if route['operator'] == 'ALL' else any(values)
        if 'condition' in route:
            satisfied = satisfied and indexed[route['condition']['constraint_id']] == 'SATISFIED'
        if satisfied:
            complete.append(route['route_id'])
    supplied = assessment['satisfied_routes']
    if (not isinstance(supplied, list) or any(not isinstance(r, str) for r in supplied)
            or len(supplied) != len(set(supplied)) or set(supplied) != set(complete)):
        raise ValueError('Satisfied routes must identify exactly the structurally complete routes.')
    expected = 'MATCH' if complete else 'PARTIAL' if cited else 'GAP'
    if assessment['status'] != expected:
        raise ValueError('Group status contradicts material support and satisfied routes.')
    if set(assessment['evidence_ids']) != cited:
        raise ValueError('Group citations must equal the union of constraint citations.')
