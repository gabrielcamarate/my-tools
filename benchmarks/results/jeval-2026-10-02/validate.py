"""Repeat offline validation using public synthetic fixtures and the official CLI."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

FIXTURE = Path(__file__).resolve().parent


def main():
    env = os.environ.copy()
    env.pop('OPENROUTER_API_KEY', None)
    env.pop('TYPESAFE_API_KEY', None)
    env.update(HTTP_PROXY='http://127.0.0.1:9', HTTPS_PROXY='http://127.0.0.1:9')
    def run(*args):
        return subprocess.run(['jeval', *map(str, args)], capture_output=True,
                              text=True, env=env, check=True, timeout=30).stdout
    with tempfile.TemporaryDirectory(prefix='jeval-validation-') as folder:
        root = Path(folder)
        control = root / 'control'
        run('ingest', FIXTURE / 'control-decisions.jsonl', '--root', control)
        start = time.monotonic()
        md = run('report', '--root', control, '--format', 'md')
        elapsed = time.monotonic() - start
        html = root / 'report.html'
        run('report', '--root', control, '--out', html)
        contents = html.read_text()
        for marker in ('80.0%', '0.100'):
            assert marker in md and marker in contents, marker
        stored = [json.loads(line) for line in (control / '.jeval/records.jsonl').read_text().splitlines()]
        gold = [r for r in stored if r['label_source'] == 'human_review']
        baseline_accuracy = sum(r['prediction'] == r['label'] for r in gold) / len(gold)
        # All gold records have confidence 0.9; both binning schemes give this gap.
        assert len(gold) == 200 and baseline_accuracy == 0.8
        assert abs(abs(0.9 - baseline_accuracy) - 0.1) < 1e-12
        assert len(stored) == 202 and 'Labeled decisions 200' in md
        thresholds = root / 'thresholds.yaml'
        run('threshold', '--root', control, '--costs', FIXTURE / 'costs.yaml', '--out', thresholds)
        assert 'auto_rate: 0.0' in thresholds.read_text()
        # Invalid binning must fail, not generate a falsely reassuring report.
        failed = subprocess.run(['jeval', 'report', '--root', str(control), '--bins', '1'],
                                env=env, capture_output=True, text=True, timeout=30)
        assert failed.returncode != 0
        unlabeled = root / 'unlabeled.jsonl'
        row = dict(gold[0], label=None, label_source=None)
        unlabeled.write_text(json.dumps(row) + '\n')
        run('ingest', unlabeled, '--root', root / 'empty-labels')
        refused = run('report', '--root', root / 'empty-labels', '--format', 'md')
        assert 'Labeled decisions 0' in refused and 'Not enough labeled data' in refused
        print(json.dumps({'control_gold': len(gold), 'accuracy': baseline_accuracy,
                          'expected_ece': 0.1, 'report_seconds': elapsed,
                          'html_md_agree': True, 'bad_bins_rejected': True,
                          'no_labels_no_metrics': True, 'threshold_not_deployed': True}))


if __name__ == '__main__':
    main()
