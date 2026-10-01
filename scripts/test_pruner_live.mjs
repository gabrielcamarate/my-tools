// Explicit live test: synthetic history/output only. No key is written or printed.
import { mkdtempSync, writeFileSync, readFileSync, rmSync, readdirSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { createHash, randomUUID } from 'node:crypto';
import assert from 'node:assert/strict';
const root = resolve(process.argv[2] || '');
assert(process.argv[2], 'Pass the installed plugin root.');
const { openRouterKey } = await import(pathToFileURL(join(root, 'dist/codex/provider.js')));
const { estimateTokens } = await import(pathToFileURL(join(root, 'dist/jev.js')));
const key = await openRouterKey();
assert(key, 'OpenRouter credential unavailable.');
const folder = mkdtempSync(join(tmpdir(), 'pruner-live-'));
const id = randomUUID(), transcript = join(folder, 'synthetic.jsonl'), metrics = join(folder, 'metrics.jsonl');
const hash = b => createHash('sha256').update(b).digest('hex');
try {
  writeFileSync(transcript, [
    { type: 'session_meta', payload: { id } },
    { type: 'response_item', payload: { type: 'message', role: 'user', content: [{ type: 'input_text', text: 'Inspect the synthetic build. Find the Q7 artifact, stable-snapshot rollback and deployment blocking reason. Keep these exact values and diagnostics.' }] } },
    { type: 'response_item', payload: { type: 'function_call', call_id: 'prior', name: 'exec_command', arguments: '{"cmd":"node fixture.mjs 0"}' } },
    { type: 'response_item', payload: { type: 'function_call_output', call_id: 'prior', output: 'Deployment plan: target Q7; rollback track stable-snapshot.' } },
  ].map(e => JSON.stringify(e)).join('\n'), { mode: 0o600 });
  // Call the actual official hook, with a synthetic event, never this chat.
  const hook = spawnSync('node', [join(root, 'dist/codex/hook.js')], {
    cwd: folder, env: { ...process.env, HOME: folder },
    input: JSON.stringify({ hook_event_name: 'PreToolUse', tool_name: 'Bash', session_id: id, transcript_path: transcript }),
  });
  assert.equal(hook.status, 0);
  const instrument = join(folder, 'instrument.mjs');
  writeFileSync(instrument, `import { appendFileSync } from 'node:fs';
const nativeFetch = globalThis.fetch;
globalThis.fetch = async (url, init) => {
  const start=performance.now(), response=await nativeFetch(url,init);
  const data=await response.clone().json();
  appendFileSync(process.env.PRUNE_TEST_METRICS, JSON.stringify({status:response.status,seconds:(performance.now()-start)/1000,usage:data.usage,answer_types:[...new Set(Object.values(data.answers||{}).map(a=>a.type))],questions:Object.keys(JSON.parse(init.body).questions).length})+'\\n');
  return response;
};`, { mode: 0o600 });
  const fixture = join(root, 'tests/fixtures/codex-noisy-build.mjs');
  const rawStart = performance.now();
  const raw = spawnSync('node', [fixture, '1'], { cwd: folder });
  const rawSeconds = (performance.now() - rawStart) / 1000;
  const start = performance.now();
  const wrapped = spawnSync('node', ['--import', instrument, join(root, 'dist/codex/run.js'), '--', 'node', fixture, '1'], {
    cwd: folder, env: { ...process.env, HOME: folder, CODEX_THREAD_ID: id, OPENROUTER_API_KEY: key, PRUNE_TEST_METRICS: metrics },
    timeout: 180000, maxBuffer: 16 * 1024 * 1024,
  });
  const wrappedSeconds = (performance.now() - start) / 1000;
  assert.equal(wrapped.status, raw.status);
  assert.deepEqual(wrapped.stderr, raw.stderr);
  const original = raw.stdout.toString(), displayed = wrapped.stdout.toString();
  const required = ['bundle Q7 = release-Q7-stage1-6d81.tar.gz', 'ERROR: deployment blocked because the release directory is not writable.', 'rollback stable-snapshot = snapshot-stage1-a312', 'Stage 1 finished; deployment remains blocked.'];
  for (const line of required) assert(displayed.includes(line), `Missing required synthetic line: ${line}`);
  const archives = readdirSync(join(folder, '.jev-pruner')).filter(p => p.endsWith('.txt'));
  assert.equal(archives.length, 1);
  const archive = join(folder, '.jev-pruner', archives[0]);
  assert.deepEqual(readFileSync(archive), raw.stdout);
  const calls = readFileSync(metrics, 'utf8').trim().split('\n').map(JSON.parse);
  const result = { schema_version: 1, kind: 'synthetic_live_openrouter', provider: 'openrouter_decisions', model: 'typesafe/jev-1.13',
    upstream_sha: 'edbc60262a5edc07e18d646c1a3f8a9f0ae868c5',
    raw_bytes: raw.stdout.length, displayed_bytes: wrapped.stdout.length,
    raw_estimated_tokens: estimateTokens(original), displayed_estimated_tokens: estimateTokens(displayed),
    stdout_reduction_percent: 100 * (1 - wrapped.stdout.length / raw.stdout.length),
    raw_seconds: rawSeconds, wrapped_seconds: wrappedSeconds,
    pruned: displayed.includes('[fast-jev-output full output:'),
    original_sha256: hash(raw.stdout), archive_sha256: hash(readFileSync(archive)), archive_mode: statSync(archive).mode & 0o777,
    required_lines_preserved: required.length, stderr_equal: true, exit_code: wrapped.status, calls,
    integration: 'official wrapper + official hook invoked with synthetic event; not automatic agent selection',
    cloud: 'not executed in Codex Cloud', cleanup: 'owned synthetic folder removed in finally' };
  assert(result.pruned, 'No pruning marker: live pruning did not occur.');
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
} finally { rmSync(folder, { recursive: true, force: true }); }
