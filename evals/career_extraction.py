"""Extraction stability metrics, independent of evidence matching and final score.

Call extraction_stability with repeated accepted canonical sets. Reuse metrics do
not establish the accuracy or repeatability of independent live model extraction.
"""
from __future__ import annotations

from waku.runtime.career_requirements import normalized_subject, scored_groups


def extraction_stability(sets, reference=None):
    if not sets:
        raise ValueError('Provide at least one canonical extraction.')
    groups = [value['requirements'] for value in sets]
    reference_groups = reference['requirements'] if reference else groups[0]
    baseline = {g['semantic_id']: g for g in reference_groups}
    baseline_ids = set(baseline)
    identities = [{g['semantic_id'] for g in run} for run in groups]
    source_sets = [{(s['start'], s['end']) for g in run for s in g['source_spans']} for run in groups]
    reference_sources = {(s['start'], s['end']) for g in reference_groups for s in g['source_spans']}

    def agreement(field):
        return [sum(g['semantic_id'] in baseline and baseline[g['semantic_id']][field] == g[field]
                    for g in run) / max(len(run), len(baseline), 1) for run in groups]

    def subjects(run):
        return [(item['kind'], normalized_subject(item['subject'])) for g in run
                for item in g['constraints']['items']]

    return {
        'group_counts': [len(run) for run in groups],
        'group_identity_agreement': [len(ids & baseline_ids) / max(len(ids | baseline_ids), 1)
                                     for ids in identities],
        'source_clause_coverage': [len(spans & reference_sources) / max(len(reference_sources), 1)
                                   for spans in source_sets],
        'merge_split_rate': [len(ids ^ baseline_ids) / max(len(ids | baseline_ids), 1) for ids in identities],
        'semantic_duplicate_rate': [(len(subjects(run)) - len(set(subjects(run)))) / max(len(subjects(run)), 1)
                                    for run in groups],
        'importance_agreement': agreement('importance'),
        'category_agreement': agreement('category'),
        'eligibility_agreement': agreement('eligibility'),
        'denominators': [sum(2 if g['importance'] == 'required' else 1 for g in scored_groups(run))
                         for run in groups],
        'coverage_reference': 'Reviewed gold source spans.' if reference else 'First accepted extraction source spans.',
    }
