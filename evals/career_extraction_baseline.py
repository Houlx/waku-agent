"""Replay the six frozen Phase A scenarios through the current Semantic IR pipeline."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS

from evals.career_extraction import fresh_extraction_trials, reliability_summary
from waku.config import Settings


def scripted_baseline(root):
    fixture = json.loads((Path(__file__).parent / 'fixtures/career_extraction_executability.json').read_text())
    trials = []
    for name, sequence in {
        'direct': ['valid', 'stop'],
        'semantic_repair': ['invalid', 'valid', 'stop'],
        'normal_recovery': ['stop', 'valid', 'stop'],
        'truncation_recovery': ['length', 'valid', 'stop'],
        'missing_submit': ['stop', 'stop'],
        'truncated': ['length', 'length'],
    }.items():
        calls = []

        def create(sequence=sequence, calls=calls, **kwargs):
            action = sequence[len(calls)]
            calls.append(action)
            if action in {'valid', 'invalid'}:
                value = copy.deepcopy(fixture['semantic_ir'])
                if action == 'invalid':
                    value['opportunities'][1]['operator'] = 'ALL'
                blocks = [NS(type='tool_use', id=str(len(calls)), name='submit_stage_result', input={'result': value})]
                reason = 'tool_use'
            else:
                blocks = [NS(type='text', text='Complete.')]
                reason = 'max_tokens' if action == 'length' else 'end_turn'
            return NS(content=blocks, stop_reason=reason, raw_stop_reason=action if action in {'stop', 'length'} else reason,
                      usage=NS(input_tokens=0, output_tokens=0))

        settings = Settings(home=Path(root) / name, model='offline', otel_endpoint='')
        result = fresh_extraction_trials(settings, NS(messages=NS(create=create), scripted=True), fixture, 1, Path(root) / name)
        trial = result['trials'][0]
        trials.append({key: trial[key] for key in ('accepted', 'cache_rows_before', 'cache_rows_after',
                                                  'attempts', 'attempts_until_acceptance', 'validation_errors')} |
                      {'case': name, 'terminations': calls, 'output_tokens': None,
                       'failure_events': trial['failure_events'], 'provider_turns': trial['provider_turns'],
                       'input_tokens': None, 'latency_seconds': trial['latency_seconds']})
    count = len(trials)
    return {'baseline_commit': 'Phase B integration', 'mode': 'scripted synthetic; no live reliability claim',
            'trials': trials, 'fresh_completion_rate': sum(t['accepted'] for t in trials) / count,
            'no_submit_rate': sum(t['attempts'] == 0 for t in trials) / count,
            'truncation_rate': sum('length' in t['terminations'] for t in trials) / count,
            'canonical_validator_rejection_rate': reliability_summary(trials)['compiler_final_rejection_rate'],
            'output_tokens': None,
            'reliability': reliability_summary(trials)}


def main():
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='career-phase-a-baseline-') as root:
        result = scripted_baseline(root)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
