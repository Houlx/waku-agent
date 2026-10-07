"""Frozen-input matching experiments; this module never runs extraction.

Call repeated_matching with a configured client only for explicitly requested live
trials. Scripted clients test the protocol, not model semantic repeatability.
"""
from __future__ import annotations

import copy
from collections import Counter
from functools import partial
from itertools import combinations

from waku.runtime.career_jobs import calculate_match_score, run_stage, validate_match
from waku.runtime.career_matching import MatchingCoverage, evidence_snapshot
from waku.runtime.career_requirements import digest, scored_groups
from waku.runtime.career_rubric import (
    MATCH_PROMPT,
    MATCH_SCHEMA,
    POLICY_VERSION,
    RELATED_MAJORS,
    matching_groups,
)
from waku.tools.career import make_evidence_tool, make_search_tool


def matching_stability(groups, reports, reference=None):
    """Measure pairwise status agreement and gold-reviewed positive overclaims.

    The gold oracle checks statuses and material support, not free-text reasoning.
    Without reviewed gold, unsupported inference is unmeasured (null).
    """
    groups = scored_groups(groups)
    ids = [g['id'] for g in groups]
    if not reports or any(r.get('matching_policy_version') != POLICY_VERSION for r in reports):
        raise ValueError('Trials must share the current matching policy.')
    vectors = []
    for report in reports:
        assessments = report['assessments']
        if len(assessments) != len(ids) or {a['requirement_id'] for a in assessments} != set(ids):
            raise ValueError('Trials must assess the same frozen groups exactly once.')
        by_id = {a['requirement_id']: a for a in assessments}
        vectors.append(tuple(by_id[rid]['status'] for rid in ids))
    pairs = list(combinations(vectors, 2))
    agreement = lambda values: sum(values) / len(pairs) if pairs else 1.0
    scores = [calculate_match_score(groups, r['assessments']) for r in reports]
    unsupported = None
    if reference is not None:
        gold = {a['requirement_id']: a for a in reference['assessments']}
        if set(gold) != set(ids):
            raise ValueError('Reviewed gold must assess the same groups.')
        overclaims = 0
        for report in reports:
            for a in report['assessments']:
                expected = gold[a['requirement_id']]
                material = {c['constraint_id']: c for c in expected['constraint_results']}
                overclaim = (a['status'] == 'MATCH' and expected['status'] != 'MATCH')
                for c in a['constraint_results']:
                    g = material[c['constraint_id']]
                    overclaim |= (c['status'] != 'UNSUPPORTED' and g['status'] == 'UNSUPPORTED'
                                  or c['status'] == 'SATISFIED' and g['status'] == 'PARTIALLY_SUPPORTED'
                                  or bool(set(c['evidence_ids']) - set(g['evidence_ids'])))
                overclaims += bool(overclaim)
        unsupported = overclaims / max(len(reports) * len(ids), 1)
    return {
        'trials': len(reports), 'matching_policy_version': POLICY_VERSION,
        'per_group_status_agreement': {rid: agreement([a[i] == b[i] for a, b in pairs])
                                       for i, rid in enumerate(ids)},
        'full_status_vector_agreement': agreement([a == b for a, b in pairs]),
        'status_frequencies': {rid: {s: Counter(v[i] for v in vectors)[s]
                                    for s in ('MATCH', 'PARTIAL', 'GAP')} for i, rid in enumerate(ids)},
        'unsupported_inference_rate': unsupported,
        'unsupported_inference_basis': 'Reviewed gold material/status/citation overclaims; prose is not judged.',
        'coverages': scores,
        'coverage_spread': max(scores) - min(scores) if scores and scores[0] is not None else None,
    }


def repeated_matching(conn, settings, client, groups, repeats=6, reference=None):
    """Run fresh matching stages on one frozen confirmed snapshot and group set."""
    if not isinstance(repeats, int) or repeats < 1:
        raise ValueError('Provide a positive trial count.')
    frozen = matching_groups(scored_groups(copy.deepcopy(groups)))
    snapshot_id, _ = evidence_snapshot(conn)
    reports = []
    for _ in range(repeats):
        collected, searches = {}, []
        coverage = MatchingCoverage(conn, collected)
        if coverage.snapshot_id != snapshot_id:
            raise ValueError('Frozen experiment evidence changed between trials.')
        report = run_stage(
            settings, client, 'evidence matching', MATCH_PROMPT,
            {'requirements': frozen, 'job_id': 'frozen-matching', 'matching_policy_version': POLICY_VERSION,
             'reviewed_related_majors': RELATED_MAJORS}, MATCH_SCHEMA,
            partial(validate_match, requirements=frozen, conn=conn, collected=collected,
                    searches=searches, coverage=coverage),
            (make_search_tool(conn, searches), make_evidence_tool(conn, collected)), coverage=coverage)
        coverage.assert_current()
        report['matching_policy_version'] = POLICY_VERSION
        reports.append(report)
    return {'snapshot_id': snapshot_id, 'requirement_fingerprint': digest(frozen),
            'metrics': matching_stability(frozen, reports, reference), 'reports': reports}
