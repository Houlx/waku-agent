"""Extraction stability metrics, independent of evidence matching and final score.

Call extraction_stability with repeated accepted canonical sets. Reuse metrics do
not establish the accuracy or repeatability of independent live model extraction.
"""
from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path

from evals.career_extraction_gold import semantic_gold, semantic_summary
from waku.db import connect_career
from waku.runtime.career_extraction_compiler import build_source_catalog, serialized_input_bytes
from waku.runtime.career_jobs import fresh_extraction
from waku.runtime.career_requirements import (
    cache_extraction,
    normalized_subject,
    scored_groups,
    source_spans,
    validate_extraction,
)


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


def fresh_extraction_trials(settings, client, fixture, trials, root, progress=None):
    """Run extraction only, in a new empty database per trial; never clear an existing cache."""
    if not 1 <= trials <= 20:
        raise ValueError('Use 1 to 20 independent trials.')
    jd = fixture['jd']
    reference = validate_extraction(fixture['extraction'], jd)
    result = {'kind': 'independent fresh extraction', 'provider': settings.provider,
              'model': settings.model, 'jd_key': reference['jd_key'], 'trials': [],
              'reference': reference, 'accepted': []}
    expected_denominator = sum(2 if g['importance'] == 'required' else 1
                               for g in scored_groups(reference['requirements']))
    for index in range(trials):
        home = Path(root) / f'trial-{index + 1}'
        home.mkdir(parents=True, exist_ok=False)
        trial_settings = replace(settings, home=home, otel_endpoint='')
        trial_settings.ensure_home()
        conn = connect_career(home)
        activity = []
        trial = {'trial': index + 1, 'home': str(home), 'accepted': False, 'cache_rows_before': 0}
        started = time.monotonic()
        try:
            trial['cache_rows_before'] = conn.execute('SELECT count(*) FROM career_requirement_sets').fetchone()[0]
            assert trial['cache_rows_before'] == 0
            extracted = fresh_extraction(trial_settings, client, jd, activity=activity)
            cache_extraction(conn, jd, extracted)
            trial.update(accepted=True, group_count=len(extracted['requirements']),
                         scored_group_count=len(scored_groups(extracted['requirements'])))
            result['accepted'].append(extracted)
            trial.update(qualification_agreement(extracted, reference, jd))
            trial['semantic_gold'] = semantic_gold(extracted, reference, jd)
        except Exception as exc:
            # Provider exceptions can contain request/credential details; record only the class.
            trial['error'] = type(exc).__name__
        finally:
            events = [json.loads(line) for path in sorted((home / 'traces').glob('*.jsonl'))
                      for line in path.read_text().splitlines()]
            submissions = [e for e in events if e['type'] == 'tool' and e['tool'] == 'submit_stage_result']
            llm = [e for e in events if e['type'] == 'llm']
            outcomes = [e for e in events if e['type'] == 'career_extraction_outcome']
            protocol = [e for e in events if e['type'] == 'career_extraction_submission']
            trial['failure_events'] = [e for e in outcomes + protocol if 'failure_class' in e]
            trial['terminations'] = [{'normalized': e.get('stop_reason'), 'raw': e.get('raw_stop_reason')}
                                      for e in llm]
            trial['recovery_used'] = any(e.get('event') == 'submit_only_recovery' for e in protocol)
            classes = {e.get('failure_class') for e in outcomes}
            trial['ir_outcome'] = ('valid_shape' if trial['accepted'] or classes & {'semantic_rejection', 'compiler_rejection'}
                                   else 'invalid' if 'ir_validation' in classes else 'not_received')
            trial['compiler_outcome'] = ('accepted' if trial['accepted'] else
                                         'rejected' if classes & {'semantic_rejection', 'compiler_rejection'} else
                                         'not_reached')
            trial['provider_turns'] = sum(e.get('event') in {'provider_request', 'tool_choice_unsupported'} for e in protocol)
            trial['input_tokens'] = sum(e.get('usage', {}).get('in', 0) for e in llm)
            trial['output_tokens'] = sum(e.get('usage', {}).get('out', 0) for e in llm)
            if getattr(client, 'scripted', False) or not llm:
                trial['input_tokens'] = trial['output_tokens'] = None
            trial['latency_seconds'] = time.monotonic() - started
            trial['serialized_input_bytes'] = serialized_input_bytes(build_source_catalog(jd))
            trial['attempts'] = len(submissions)
            trial['iterations'] = sum(e['type'] == 'llm' for e in events)
            trial['attempts_until_acceptance'] = next((i for i, e in enumerate(submissions, 1)
                                                      if not e['output'].startswith('Error')), None)
            trial['validation_errors'] = [e['output'] for e in submissions if e['output'].startswith('Error')]
            trial['cache_rows_after'] = conn.execute('SELECT count(*) FROM career_requirement_sets').fetchone()[0]
            assert conn.execute('SELECT count(*) FROM job_matches').fetchone()[0] == 0
            conn.close()
        result['trials'].append(trial)
        if progress:
            progress(trial)
    result['reliability'] = reliability_summary(result['trials'])
    result['semantic_quality'] = semantic_summary(result['trials'])
    result['successful_extraction_rate'] = sum(t['accepted'] for t in result['trials']) / trials
    if result['accepted']:
        result['stability'] = extraction_stability(result['accepted'], reference=reference)
        result['denominator_agreement'] = [d == expected_denominator for d in result['stability']['denominators']]
    else:
        result['stability'] = None
        result['denominator_agreement'] = []
    return result


def reliability_summary(trials):
    total = len(trials)
    result = {'total_fresh_trials': total, 'completed_trials': sum(t['accepted'] for t in trials)}
    filters = {
        'missing_submit': lambda e: e.get('code') == 'MISSING_SUBMIT',
        'truncation': lambda e: e.get('code') == 'TRUNCATION',
        'malformed_arguments': lambda e: e.get('code') == 'MALFORMED_ARGUMENTS',
        'malformed_ir': lambda e: e.get('failure_class') == 'ir_validation',
        'ir_semantic_rejection': lambda e: e.get('failure_class') == 'semantic_rejection',
        'compiler_final_rejection': lambda e: e.get('failure_class') == 'compiler_rejection',
    }
    for name, predicate in filters.items():
        count = sum(any(predicate(e) for e in t['failure_events']) for t in trials)
        result[name + '_count'] = count
        result[name + '_rate'] = count / total
    result['completion_rate'] = result['completed_trials'] / total
    for key in ('attempts_until_acceptance', 'provider_turns', 'output_tokens', 'input_tokens', 'latency_seconds'):
        result[key] = [t[key] for t in trials]
    return result


def qualification_agreement(extracted, reference, jd):
    """Compare gold material spans and dispositions, tolerating excerpt-edge punctuation.

    This metric trims only gold span boundaries; it never rewrites the JD, submitted
    provenance, canonical spans or cache identity. It does not judge semantic entailment.
    """
    actual = [(s, g['eligibility']) for g in extracted['requirements']
              for s in source_spans(jd, g['source_excerpt'])]
    covered, agreed, total = 0, 0, 0
    for group in reference['requirements']:
        for span in group['source_spans']:
            start, end = span['start'], span['end']
            while start < end and (jd[start].isspace() or jd[start] in '.,;。；，'):
                start += 1
            while end > start and (jd[end - 1].isspace() or jd[end - 1] in '.,;。；，'):
                end -= 1
            dispositions = [eligibility for s, eligibility in actual
                            if s['start'] <= start and s['end'] >= end]
            covered += bool(dispositions)
            agreed += bool(dispositions) and all(e == group['eligibility'] for e in dispositions)
            total += 1
    return {'source_qualification_coverage': covered / max(total, 1),
            'source_eligibility_agreement': agreed / max(total, 1)}


def main():
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description='Opt-in independent fresh extraction, without matching.')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--trials', type=int, default=5)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.live:
        parser.error('Use --live to explicitly allow configured provider calls.')
    from waku.config import load_settings
    from waku.loop.models import get_client

    fixture = json.loads((Path(__file__).parent / 'fixtures/career_extraction_executability.json').read_text())
    settings = load_settings()
    client = get_client(settings)
    try:
        result = fresh_extraction_trials(settings, client, fixture, args.trials,
                                        Path(tempfile.mkdtemp(prefix='career-fresh-extraction-')),
                                        lambda t: print(f'Trial {t["trial"]}: accepted={t["accepted"]}; '
                                                        f'attempts={t["attempts"]}', flush=True))
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Successful extraction rate: {result["successful_extraction_rate"]:.0%}', flush=True)
    finally:
        close = getattr(client, 'close', None)
        if callable(close):
            close()


if __name__ == '__main__':
    main()
