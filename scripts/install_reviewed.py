"""Repeatable local/Cloud installation of the reviewed ten-tool batch."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    catalog = json.loads((ROOT / 'tools.json').read_text())['tools']
    for name, spec in catalog.items():
        if spec['installer'] != 'reviewed-source-v1':
            continue
        for args in (['install', name], ['integrate', name, '--apply']):
            result = subprocess.run([sys.executable, str(ROOT / 'bin/my-tools'), *args], cwd=ROOT)
            if result.returncode:
                return result.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
