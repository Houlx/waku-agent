"""Scripted structural proposals for existing coordinator regression clients.

These helpers do not judge evidence; reviewed semantic expectations live in gold fixtures.
"""
from waku.runtime.career_rubric import matching_routes


def scripted_assessment(group, status, ids, reason):
    routes = matching_routes(group)
    results = []
    for route in routes:
        items = route['items'] + ([route['condition']] if 'condition' in route else [])
        for item in items:
            support = ('SATISFIED' if status == 'MATCH' and route['route_id'] == 'primary'
                       else 'PARTIALLY_SUPPORTED' if status == 'PARTIAL' and not results
                       else 'UNSUPPORTED')
            results.append({'constraint_id': item['constraint_id'], 'status': support,
                            'evidence_ids': ids if support != 'UNSUPPORTED' else [], 'reason': reason})
    return {'requirement_id': group['id'], 'status': status, 'evidence_ids': ids, 'reason': reason,
            'constraint_results': results, 'satisfied_routes': ['primary'] if status == 'MATCH' else []}
