"""Tools available exclusively to scoped Career runs."""
import json
import re

from waku.tools.registry import Tool


def make_submit_tool(submit):
    def execute(profile):
        submit(profile)
        return 'Career profile proposal validated. The coordinator can save it in state.db after this stage completes.'

    return Tool('submit_stage_result', 'Submit the normalized career profile for validation.',
                {'type': 'object', 'properties': {'profile': {'type': 'object',
                 'properties': {'basic': {'type': 'object'}, 'records': {'type': 'array',
                 'items': {'type': 'object', 'properties': {
                     'source_id': {'type': 'string'}, 'title': {'type': 'string'},
                     'description': {'type': 'string'},
                     'skills': {'type': 'array', 'items': {'type': 'string'}}},
                     'required': ['source_id', 'title', 'description', 'skills']}}},
                 'required': ['basic', 'records']}}, 'required': ['profile']}, execute)


def make_stage_submit_tool(submit, schema, description):
    def execute(result):
        submit(result)
        return 'Career proposal validated. The coordinator saves it only after the stage finishes.'

    return Tool('submit_stage_result', description,
                {'type': 'object', 'properties': {'result': schema}, 'required': ['result'],
                 'additionalProperties': False}, execute)


def confirmed_profile(conn):
    row = conn.execute('SELECT confirmed FROM career_profile WHERE id=1').fetchone()
    if not row or not row['confirmed']:
        raise ValueError('Confirm your Career Profile before analyzing a job.')


def get_evidence(conn, evidence_id):
    confirmed_profile(conn)
    if not isinstance(evidence_id, str):
        raise TypeError('Provide an evidence ID.')
    row = conn.execute('SELECT evidence_id,source_id,source_type,raw_text,normalized_json '
                       'FROM career_evidence WHERE evidence_id=? AND active=1', (evidence_id,)).fetchone()
    if row is None:
        raise ValueError('Unknown or inactive Career evidence ID.')
    record = dict(row)
    record['normalized'] = json.loads(record.pop('normalized_json'))
    return record


def search_career_evidence(conn, queries, limit=8):
    """Search safe literal tokens, union synonyms, and bound the combined result."""
    confirmed_profile(conn)
    if (not isinstance(queries, list) or not 1 <= len(queries) <= 8
            or not all(isinstance(q, str) and q.strip() and len(q) <= 300 for q in queries)):
        raise ValueError('Provide one to eight nonempty queries of at most 300 characters.')
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError('Search limit must be an integer from 1 to 20.')
    found = {}
    for query in queries:
        tokens = re.findall(r'[^\W_]+', query, re.UNICODE)[:16]
        if not tokens:
            continue
        expression = ' AND '.join('"' + t + '"' for t in tokens)
        rows = conn.execute(
            'SELECT e.evidence_id,e.source_type,e.normalized_json,bm25(career_evidence_fts) AS rank '
            'FROM career_evidence_fts JOIN career_evidence e ON e.id=career_evidence_fts.rowid '
            'WHERE career_evidence_fts MATCH ? AND e.active=1 ORDER BY rank,e.evidence_id LIMIT ?',
            (expression, limit))
        for row in rows:
            eid = row['evidence_id']
            if eid not in found or row['rank'] < found[eid]['rank']:
                normalized = json.loads(row['normalized_json'])
                found[eid] = {'evidence_id': eid, 'source_type': row['source_type'],
                              'title': normalized['title'], 'summary': normalized['description'],
                              'skills': normalized['skills'], 'rank': row['rank']}
    ranked = sorted(found.values(), key=lambda r: (r['rank'], r['evidence_id']))[:limit]
    return [{k: v for k, v in row.items() if k != 'rank'} for row in ranked]


def make_search_tool(conn, searches=None):
    def execute(queries, limit=8):
        results = search_career_evidence(conn, queries, limit)
        if searches is not None:
            searches.append(list(queries))
        return json.dumps(results, ensure_ascii=False)

    return Tool('search_career_evidence',
                'Search confirmed Career records with synonyms or multiple queries. Results are summaries; '
                'use get_evidence to inspect complete facts before citing them.',
                {'type': 'object', 'properties': {
                    'queries': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 8},
                    'limit': {'type': 'integer', 'minimum': 1, 'maximum': 20}},
                 'required': ['queries'], 'additionalProperties': False},
                execute)


def make_evidence_tool(conn, collected):
    def execute(evidence_id):
        record = get_evidence(conn, evidence_id)
        collected[evidence_id] = record
        return json.dumps(record, ensure_ascii=False)

    return Tool('get_evidence', 'Inspect a complete confirmed Career record and its original user input.',
                {'type': 'object', 'properties': {'evidence_id': {'type': 'string'}},
                 'required': ['evidence_id'], 'additionalProperties': False}, execute)
