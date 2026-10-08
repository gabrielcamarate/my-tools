"""Real Bun runtime: project dotenv/preloads cannot alter the managed helper."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from manage import helper_command

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
args = parser.parse_args()
bun = helper_command(args.source)[0]
with tempfile.TemporaryDirectory(prefix='codex-jev-bun-config-') as tmp:
    root = Path(tmp)
    helper = root / 'jev'
    helper.mkdir()
    (helper / '.env').write_text('JEV_FIXTURE_ENV=foreign-project\n')
    (helper / 'preload.ts').write_text('globalThis.JEV_FIXTURE_PRELOAD = true;\n')
    (helper / 'bunfig.toml').write_text('preload = ["./preload.ts"]\n')
    (helper / 'codex-jev-compact.ts').write_text('console.log(JSON.stringify({dotenv: !!process.env.JEV_FIXTURE_ENV, preload: !!globalThis.JEV_FIXTURE_PRELOAD, cwd: process.cwd()}));\n')
    command = helper_command(root)
    command[0] = bun
    env = {k: v for k, v in os.environ.items() if k not in ('BUN_OPTIONS', 'NODE_OPTIONS', 'JEV_FIXTURE_ENV')}
    control = subprocess.run([bun, '--cwd=' + str(helper), '--config=' + str(helper / 'bunfig.toml'), command[-1]], cwd=root, env=env, check=True, capture_output=True, text=True, timeout=15)
    assert json.loads(control.stdout) == {'dotenv': True, 'preload': True, 'cwd': str(helper)}, control.stdout
    result = subprocess.run(command, cwd=root, env=env, check=True, capture_output=True, text=True, timeout=15)
    probe = json.loads(result.stdout)
    assert probe == {'dotenv': False, 'preload': False, 'cwd': str(helper)}, probe
    print(json.dumps({'positive_control': True, 'project_dotenv_ignored': True, 'project_preload_ignored': True, 'owned_helper_cwd': True}))
