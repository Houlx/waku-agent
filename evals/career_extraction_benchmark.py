"""Run isolated synthetic IR/compiler trials and compare the frozen Phase A cases."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS

from evals.career_extraction import fresh_extraction_trials
from evals.career_extraction_baseline import scripted_baseline
from waku.config import Settings

FIXTURES = Path(__file__).parent / 'fixtures'


class GoldClient:
    """Submit reviewed IR, exercising production compilation rather than canonical acceptance."""
    scripted = True

    def __init__(self, ir):
        self.ir = ir
        self.messages = NS(create=self.create)

    def create(self, **kwargs):
        initial = len(kwargs['messages']) == 1
        blocks = [NS(type='tool_use', id='gold', name='submit_stage_result', input={'result': copy.deepcopy(self.ir)})]
        if not initial:
            blocks = [NS(type='text', text='Complete.')]
        return NS(content=blocks, stop_reason='tool_use' if initial else 'end_turn',
                  raw_stop_reason='tool_use' if initial else 'end_turn',
                  usage=NS(input_tokens=0, output_tokens=0))


def scripted_benchmark(root):
    fixtures = json.loads((FIXTURES / 'career_extraction_gold.json').read_text())
    settings = Settings(home=Path(root), model='offline', otel_endpoint='')
    runs = [dict(name=f['name'], **fresh_extraction_trials(settings, GoldClient(f['semantic_ir']),
                 f, 1, Path(root) / f['name'])) for f in fixtures]
    return {'mode': 'scripted synthetic; construction and metric calibration, not model quality',
            'phase_a_frozen': json.loads((FIXTURES / 'career_phase_a_baseline.json').read_text()),
            'phase_b_reliability': scripted_baseline(Path(root) / 'reliability'), 'gold_cases': runs,
            'live_trials_run': False, 'token_usage': None}


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='career-phase-b-benchmark-') as root:
        result = scripted_benchmark(root)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
