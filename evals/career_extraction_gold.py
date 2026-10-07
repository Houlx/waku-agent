"""Reviewed-source semantic metrics independent of submission and cache reliability.

Literal normalized subjects identify gold atoms. These metrics do not prove natural
language entailment; reviewers must maintain faithful gold subjects and source ranges.
"""
from itertools import combinations

from waku.runtime.career_requirements import normalized_subject, scored_groups, source_spans


def atoms(group):
    return frozenset((i['kind'], normalized_subject(i['subject'])) for i in group['constraints']['items'])


def route_signature(group):
    route = group['alternative_route']
    if route is None:
        return None
    return (route['constraints']['operator'], atoms(route), ' '.join(route['condition'].casefold().split()))


def inheritance(group):
    route = group['alternative_route']
    return frozenset() if route is None else frozenset(a for a in atoms(group) & atoms(route) if a[0] == 'major')


def semantic_gold(extracted, reference, jd):
    """Compare canonical outputs to reviewed gold, without relying on semantic hashes."""
    groups, gold = extracted['requirements'], reference['requirements']
    def all_items(group):
        route = group['alternative_route']
        return group['constraints']['items'] + (route['constraints']['items'] if route else [])

    actual_atoms = {(i['kind'], normalized_subject(i['subject'])) for g in groups for i in all_items(g)}
    gold_atoms = {(i['kind'], normalized_subject(i['subject'])) for g in gold for i in all_items(g)}
    opportunities = {atoms(g) for g in groups}
    gold_opportunities = {atoms(g) for g in gold}

    def ratio(hits, count):
        return hits / count if count else 1.0

    def field_accuracy(getter):
        # Each gold atom votes independently, so merge/split errors cannot hide
        # category or eligibility errors by dropping unmatched opportunities.
        hits = 0
        for group in gold:
            for atom in atoms(group):
                candidates = [g for g in groups if atom in atoms(g)]
                hits += bool(candidates) and all(getter(g) == getter(group) for g in candidates)
        return ratio(hits, sum(len(atoms(g)) for g in gold))

    actual_pairs = {frozenset(pair) for g in groups for pair in combinations(atoms(g), 2)}
    gold_pairs = {frozenset(pair) for g in gold for pair in combinations(atoms(g), 2)}
    universe = {frozenset(pair) for pair in combinations(actual_atoms | gold_atoms, 2)}
    # Pairwise co-membership checks both spurious merges and incorrect splits.
    merge_split = 1 - len(actual_pairs ^ gold_pairs) / max(len(universe), 1)
    spans = [s for g in groups for i in all_items(g)
             for s in source_spans(jd, i['source_excerpt'])]
    clauses = {(s['start'], s['end']) for g in gold for i in all_items(g)
               for s in source_spans(jd, i['source_excerpt'])}
    covered = 0
    for start, end in clauses:
        while start < end and (jd[start].isspace() or jd[start] in '.,;。；，'):
            start += 1
        while end > start and (jd[end - 1].isspace() or jd[end - 1] in '.,;。；，'):
            end -= 1
        covered += any(s['start'] <= start and end <= s['end'] for s in spans)
    scored_atoms = [a for g in scored_groups(groups) for a in atoms(g)]
    denominator = lambda gs: sum(2 if g['importance'] == 'required' else 1 for g in scored_groups(gs))
    actual_denominator, gold_denominator = denominator(groups), denominator(gold)
    return {
        'source_clause_recall': ratio(covered, len(clauses)),
        'unsupported_qualification_additions': len(actual_atoms - gold_atoms),
        'unsupported_qualification_rate': len(actual_atoms - gold_atoms) / max(len(actual_atoms), 1),
        'canonical_opportunity_agreement': ratio(len(opportunities & gold_opportunities),
                                                  len(opportunities | gold_opportunities)),
        'merge_split_accuracy': merge_split,
        'category_accuracy': field_accuracy(lambda g: g['category']),
        'eligibility_accuracy': field_accuracy(lambda g: g['eligibility']),
        'all_any_accuracy': field_accuracy(lambda g: g['constraints']['operator']),
        'fallback_accuracy': field_accuracy(route_signature),
        'inheritance_accuracy': field_accuracy(inheritance),
        'duplicate_scoring_rate': (len(scored_atoms) - len(set(scored_atoms))) / max(len(scored_atoms), 1),
        'weighted_denominator_agreement': float(actual_denominator == gold_denominator),
        'denominator': actual_denominator, 'gold_denominator': gold_denominator,
    }


QUALITY_FIELDS = ('source_clause_recall', 'canonical_opportunity_agreement', 'merge_split_accuracy',
                  'category_accuracy', 'eligibility_accuracy', 'all_any_accuracy', 'fallback_accuracy',
                  'inheritance_accuracy', 'weighted_denominator_agreement')


def semantic_summary(trials):
    accepted = [t['semantic_gold'] for t in trials if t['accepted']]
    fields = QUALITY_FIELDS + ('unsupported_qualification_rate', 'duplicate_scoring_rate')
    among = {key: sum(m[key] for m in accepted) / len(accepted) for key in fields} if accepted else None
    # Failed trials earn zero quality; rates remain conditional because no output
    # exists to inspect. The non-completion fraction is always reported alongside.
    across = {key: sum(m[key] for m in accepted) / len(trials) for key in QUALITY_FIELDS}
    return {'all_fresh_trials': {'total': len(trials), 'completed': len(accepted),
                                'non_completion_rate': 1 - len(accepted) / len(trials),
                                'completion_adjusted_quality': across},
            'among_accepted_trials': among,
            'method': 'Literal gold atoms and source containment; failed trials earn zero quality. '
                      'Addition and duplicate rates describe accepted outputs only. No entailment proof.'}
