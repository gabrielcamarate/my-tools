"""Version-matched Jev engines; official installations are never overwritten.

All update checks are offline/synthetic. Live provider acceptance is separate.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import struct
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
VERSION = re.compile(r"^codex-cli (\d+\.\d+\.\d+(?:-[a-z0-9.]+)?)$")


def patch_signature():
    result = hashlib.sha256()
    for name in ('integration.patch', 'openrouter.patch', 'rust-1.98-build.patch', 'manifest.json'):
        result.update((HERE / name).read_bytes())
    result.update(b'release-no-lto; strip-debug-v2')
    return result.hexdigest()


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, text=True, **kwargs)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def version(binary):
    result = run([binary, '--version'], capture_output=True, timeout=15)
    match = VERSION.fullmatch(result.stdout.strip())
    if not match:
        raise RuntimeError('Unrecognized Codex version; refusing activation')
    return match[1]


def official(target):
    path = (os.environ.get('CODEX_JEV_OFFICIAL_CLI') or shutil.which('codex')) if target == 'cli' else os.environ.get('CODEX_JEV_OFFICIAL_DESKTOP', '/usr/lib/chatgpt/resources/codex')
    if not path:
        raise RuntimeError('Official Codex executable unavailable')
    path = Path(path).resolve()
    if target == 'cli' and not os.environ.get('CODEX_JEV_OFFICIAL_CLI') and ('shims' in path.parts or path.name == 'mise' or path == Path.home() / '.local/bin/codex'):
        path = Path(run(['mise', 'which', 'codex'], capture_output=True, timeout=30).stdout.strip()).resolve()
    return path


def load(state):
    path = state / 'accepted.json'
    return json.loads(path.read_text()) if path.exists() else {}


def desktop_interface(binary):
    bundle = binary.parent / 'app.asar'
    with bundle.open('rb') as stream:
        header_size = struct.unpack('<4I', stream.read(16))[3]
        index = json.loads(stream.read(header_size))
        offset = 16 + header_size
        def walk(tree, prefix=''):
            for name, item in tree.get('files', {}).items():
                if 'files' in item:
                    yield from walk(item, prefix + name + '/')
                else:
                    yield prefix + name, item
        for name, item in walk(index):
            if name.startswith('.vite/build/main-') and name.endswith('.js') and 'offset' in item:
                stream.seek(offset + int(item['offset']))
                text = stream.read(item['size']).decode()
                if re.search(r'rawValue:[\w$]+\.CODEX_CLI_PATH', text) and 'CODEX_ELECTRON_USER_DATA_PATH' in text:
                    return digest(bundle)
    raise RuntimeError('Installed Desktop executable/profile overrides are not verified')


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix('.pending')
    with tmp.open('w') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def matches(record, binary):
    if not record or record.get('official_sha256') != digest(binary) or record.get('version') != version(binary):
        return False
    if record.get('patchset') != patch_signature():
        return False
    host = binary.parent / 'codex-code-mode-host'
    if record.get('official_host_sha256') and (not host.is_file() or digest(host) != record['official_host_sha256']):
        return False
    if record.get('desktop_bundle_sha256'):
        try:
            if desktop_interface(binary) != record['desktop_bundle_sha256']:
                return False
        except (RuntimeError, OSError, ValueError):
            return False
    for name, expected in record.get('files', {}).items():
        path = Path(record['source']) / name
        if not path.is_file() or path.is_symlink() or digest(path) != expected:
            return False
    library = Path(record['source']) / 'jev/lib'
    actual = {str(p.relative_to(Path(record['source']))) for p in library.rglob('*') if p.is_file() or p.is_symlink()}
    expected = {p for p in record['files'] if p.startswith('jev/lib/')}
    if actual != expected:
        return False
    return bool(record.get('files'))


def schemas(binary, output):
    run([binary, 'app-server', 'generate-json-schema', '--experimental', '--out', output], capture_output=True, timeout=90)
    return {str(p.relative_to(output)): json.loads(p.read_text()) for p in output.rglob('*.json')}


def validate(source, binary):
    candidate = source / 'target/release/codex'
    if version(candidate) != version(binary):
        raise RuntimeError('Candidate version differs from installed target')
    with tempfile.TemporaryDirectory(prefix='codex-jev-schema-') as tmp:
        root = Path(tmp)
        env = {**os.environ, 'HOME': str(root), 'CODEX_HOME': str(root / 'codex')}
        # Schema commands do not need authentication, personal config or provider calls.
        saved = os.environ.copy()
        try:
            os.environ.update(env)
            if schemas(binary, root / 'official') != schemas(candidate, root / 'candidate'):
                raise RuntimeError('App-server schema differs from installed target')
        finally:
            os.environ.clear()
            os.environ.update(saved)
    run([sys.executable, HERE / 'test_transport.py', source], capture_output=True, timeout=120)
    run([sys.executable, HERE / 'test_host.py', '--source', source], capture_output=True, timeout=90)
    for mode in ('baseline', 'jev', 'missing-key'):
        command = [sys.executable, HERE / 'test_engine.py', '--source', source, '--mode', mode]
        if mode == 'jev':
            command.append('--mock-jev')
        run(command, capture_output=True, timeout=240)


def accept(state, target, source, binary):
    # Fresh installed identity readback after validation; do not accept a moving target.
    before = (version(binary), digest(binary))
    patchset = patch_signature()
    bundle_hash = desktop_interface(binary) if target == 'desktop' else None
    files = ['target/release/codex', 'target/release/codex-code-mode-host', 'lab-runtime/node_modules/@oven/bun-linux-x64/bin/bun', 'jev/codex-jev-compact.ts']
    files.extend(str(p.relative_to(source)) for p in sorted((source / 'jev/lib').rglob('*')) if p.is_file())
    if any((source / p).is_symlink() for p in files):
        raise RuntimeError('Candidate runtime contains a symlink')
    hashes = {p: digest(source / p) for p in files}
    validate(source, binary)
    if before != (version(binary), digest(binary)):
        raise RuntimeError('Official executable changed during validation')
    if bundle_hash and desktop_interface(binary) != bundle_hash:
        raise RuntimeError('Desktop package changed during validation')
    if any(digest(source / p) != expected for p, expected in hashes.items()):
        raise RuntimeError('Candidate runtime changed during validation')
    if patch_signature() != patchset:
        raise RuntimeError('Maintenance patch changed during validation')
    records = load(state)
    previous = records.get(target)
    official_host = binary.parent / 'codex-code-mode-host'
    commit = run(['git', 'rev-parse', 'HEAD'], cwd=source, capture_output=True).stdout.strip() if (source / '.git').is_dir() else None
    records[target] = {'version': before[0], 'official_sha256': before[1], 'official_host_sha256': digest(official_host) if official_host.is_file() else None, 'desktop_bundle_sha256': bundle_hash, 'source': str(source), 'upstream_commit': commit, 'patchset': patch_signature(), 'files': hashes, 'accepted_at': int(time.time()), 'validation': 'schema parity, provider failure contracts, synthetic replacement/fallback/continuation', 'live_acceptance': False}
    if previous:
        atomic_json(state / f'previous-{target}.json', previous)
    atomic_json(state / 'accepted.json', records)
    print(f'{target}: {before[0]} accepted after offline validation')


def normalize_release_lock(source):
    # OpenAI release tags update workspace versions, but may leave lock versions at 0.0.0.
    original = (source / 'codex-rs/Cargo.lock').read_text()
    import tomllib
    before = tomllib.loads(original)['package']
    workspace_version = tomllib.loads((source / 'codex-rs/Cargo.toml').read_text())['workspace']['package']['version']
    blocks = original.split('[[package]]')
    for index, block in enumerate(blocks[1:], 1):
        if not re.search(r'^source = ', block, re.MULTILINE):
            blocks[index] = re.sub(r'^version = "0\.0\.0"$', 'version = "' + workspace_version + '"', block, count=1, flags=re.MULTILINE)
    normalized = '[[package]]'.join(blocks)
    after = tomllib.loads(normalized)['package']
    def external(packages):
        return [p for p in packages if 'source' in p]
    if external(before) != external(after):
        raise RuntimeError('Lock normalization changed external dependencies')
    if (source / 'codex-rs/jev-tests/Cargo.toml').exists() and not any(p['name'] == 'codex-jev-tests' for p in after):
        normalized += '\n[[package]]\nname = "codex-jev-tests"\nversion = "' + workspace_version + '"\ndependencies = [\n "codex-history",\n "codex-protocol",\n "pretty_assertions",\n "serde",\n "serde_json",\n "tokio",\n "tracing",\n]\n'
    (source / 'codex-rs/Cargo.lock').write_text(normalized)


def fetch_helper(source):
    manifest = json.loads((HERE / 'manifest.json').read_text())
    with tempfile.TemporaryDirectory(prefix='codex-jev-helper-source-') as tmp:
        root = Path(tmp)
        run(['git', 'init', root], capture_output=True)
        run(['git', 'fetch', '--depth', '1', manifest['upstream'], manifest['sha']], cwd=root)
        run(['git', 'checkout', 'FETCH_HEAD', '--', 'jev/codex-jev-compact.ts', 'jev/lib'], cwd=root)
        shutil.copytree(root / 'jev', source / 'jev')
    run(['git', 'apply', HERE / 'openrouter.patch'], cwd=source)


def prepare(state, target):
    binary = official(target)
    if matches(load(state).get(target), binary):
        print(f'{target}: current, no rebuild')
        return
    target_version = version(binary)
    bundle_hash = desktop_interface(binary) if target == 'desktop' else ''
    key = target_version + '-' + patch_signature()[:12] + '-' + digest(binary)[:8] + ('-' + bundle_hash[:8] if bundle_hash else '')
    source = state / 'versions' / key
    # Never alter an existing checkout or accepted engine in place.
    if source.exists():
        raise RuntimeError('Candidate directory already exists; inspect the failed build before retrying')
    source.parent.mkdir(parents=True, exist_ok=True)
    run(['git', 'clone', '--depth', '1', '--branch', 'rust-v' + target_version, 'https://github.com/openai/codex.git', source])
    run(['git', 'apply', '--check', HERE / 'integration.patch'], cwd=source)
    run(['git', 'apply', HERE / 'integration.patch'], cwd=source)
    fetch_helper(source)
    chatgpt_crate = source / 'codex-rs/chatgpt/src/lib.rs'
    if '#![recursion_limit = "256"]' not in chatgpt_crate.read_text():
        run(['git', 'apply', HERE / 'rust-1.98-build.patch'], cwd=source)
    normalize_release_lock(source)
    runtime = source / 'lab-runtime'
    run(['npm', 'install', '--prefix', runtime, '--ignore-scripts', 'bun@1.4.2'])
    # One serialized compiler cache; accepted executables are separate immutable copies.
    build_cache = state / 'build-cache'
    build_env = {**os.environ, 'CARGO_BUILD_JOBS': '1', 'CARGO_TARGET_DIR': str(build_cache)}
    # The user's selected toolchain must support this upstream version; no global changes.
    # Set the entire Cargo profile: a root-only lto override leaves bitcode libraries.
    # Optimization stays at release level; only inter-library LTO is disabled.
    run(['cargo', 'rustc', '--config', 'profile.release.lto=false', '--locked', '--release', '-p', 'codex-cli', '--bin', 'codex', '--', '-C', 'link-arg=-Wl,--strip-debug'], cwd=source / 'codex-rs', env=build_env)
    run(['cargo', 'test', '--config', 'profile.release.lto=false', '--locked', '--release', '-p', 'codex-jev-tests'], cwd=source / 'codex-rs', env=build_env)
    (source / 'target/release').mkdir(parents=True)
    shutil.copy2(build_cache / 'release/codex', source / 'target/release/codex')
    # Keep symbols in the compiler cache, not in the launcher copy hashed each start.
    if shutil.which('strip'):
        run(['strip', '--strip-debug', source / 'target/release/codex'])
    # This helper has no --version. Use the sibling from the exact official package,
    # record its hash, and prove its protocol via the real app-server tests.
    host = binary.parent / 'codex-code-mode-host'
    if not host.is_file():
        raise RuntimeError('Matching official Code Mode host unavailable; candidate remains inactive')
    shutil.copy2(host, source / 'target/release/codex-code-mode-host')
    accept(state, target, source, binary)


def launch(state, target, arguments):
    binary = official(target)
    record = load(state).get(target)
    env = {**os.environ}
    env.pop('CODEX_JEV_COMPACT', None)
    if matches(record, binary):
        source = Path(record['source'])
        helper = state / f'helper-{target}.sh'
        import shlex
        text = '#!/bin/sh\nexec ' + shlex.quote(str(source / 'lab-runtime/node_modules/@oven/bun-linux-x64/bin/bun')) + ' ' + shlex.quote(str(source / 'jev/codex-jev-compact.ts')) + '\n'
        helper.write_text(text)
        helper.chmod(0o700)
        env['CODEX_JEV_COMPACT'] = str(helper)
        binary = source / 'target/release/codex'
    else:
        print('Jev is not validated for the installed version; using current official Codex.', file=sys.stderr)
    if target == 'cli':
        env['CODEX_HOME'] = str(state / 'cli-codex')
        env.pop('CODEX_THREAD_ID', None)
        Path(env['CODEX_HOME']).mkdir(mode=0o700, parents=True, exist_ok=True)
        return os.execve(binary, [str(binary), *arguments], env)
    # Separate renderer and engine profiles; never restart or attach to the main app.
    desktop_interface(official('desktop'))
    env['CODEX_CLI_PATH'] = str(binary)
    env['CODEX_HOME'] = str(state / 'desktop-codex')
    env['CODEX_ELECTRON_USER_DATA_PATH'] = str(state / 'desktop-renderer')
    env['CODEX_ELECTRON_RESOURCES_PATH'] = str(official('desktop').parent)
    env.pop('CODEX_THREAD_ID', None)
    Path(env['CODEX_HOME']).mkdir(mode=0o700, parents=True, exist_ok=True)
    app = shutil.which('chatgpt')
    if not app:
        raise RuntimeError('ChatGPT desktop executable unavailable')
    os.execve(app, [app, '--user-data-dir=' + env['CODEX_ELECTRON_USER_DATA_PATH'], *arguments], env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, default=Path.home() / '.local/share/my-tools/codex-jev-managed')
    parser.add_argument('action', choices=('status', 'accept', 'update', 'launch'))
    parser.add_argument('--target', choices=('cli', 'desktop', 'all'), default='all')
    parser.add_argument('--source', type=Path)
    args, remainder = parser.parse_known_args()
    if remainder[:1] == ['--']:
        remainder = remainder[1:]
    if remainder and args.action != 'launch':
        parser.error('Unexpected arguments outside launch')
    state = args.state.expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    targets = ('cli', 'desktop') if args.target == 'all' else (args.target,)
    if args.action == 'status':
        for target in targets:
            binary = official(target)
            print(json.dumps({'target': target, 'installed': version(binary), 'jev_ready': matches(load(state).get(target), binary)}))
    elif args.action == 'launch':
        if len(targets) != 1:
            parser.error('Choose one launch target')
        launch(state, args.target, remainder)
    else:
        stable = Path.home() / '.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin'
        if stable.is_dir():
            os.environ['PATH'] = str(stable) + os.pathsep + os.environ['PATH']
        with (state / 'update.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            failures = []
            for target in targets:
                if args.action == 'accept':
                    if not args.source or len(targets) != 1:
                        parser.error('accept requires --source and one --target')
                    accept(state, target, args.source.resolve(), official(target))
                else:
                    try:
                        prepare(state, target)
                    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
                        failures.append(f'{target}: {exc}')
                        atomic_json(state / f'last-failure-{target}.json', {'target': target, 'time': int(time.time()), 'error': str(exc)})
            if failures:
                raise RuntimeError('; '.join(failures))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'Jev candidate inactive: {exc}', file=sys.stderr)
        raise SystemExit(1)
