// Public synthetic fixture; no consumer project, transcript or private code.
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync, realpathSync } from 'node:fs';
import { tmpdir, homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { performance } from 'node:perf_hooks';
import assert from 'node:assert/strict';
const cli = realpathSync(process.env.CANNY_COMMAND || join(homedir(), '.local/bin/canny'));
const { openRouterKey } = await import(join(dirname(cli), 'provider.js'));
const key = openRouterKey();
assert(key, 'Shared OpenRouter credential unavailable');
assert(process.argv[2], 'Usage: node benchmarks/run-canny.mjs EVIDENCE_DIRECTORY');
const stage = mkdtempSync(join(tmpdir(), 'canny-live-'));
const project = join(stage, 'project'), home = join(stage, 'home');
mkdirSync(project); mkdirSync(home);
const env = { ...process.env, HOME: home, CANNY_HOME: join(home, '.canny'), OPENROUTER_API_KEY: key };
const results = { schema_version: 1, upstream_sha: 'f2c5e53779445d60dc4a09d2dbced2308fccb820',
  synthetic: true, provider: 'OpenRouter Decisions', model: 'typesafe/jev-1.13',
  native_agent_session: false, cloud_actual_test: false, tests: {} };
function run(args, input = '', extra = {}) {
  const start = performance.now();
  const r = spawnSync('node', [cli, ...args], { cwd: project, env: { ...env, ...extra }, input, encoding: 'utf8', timeout: 15000 });
  assert.equal(r.status, 0, 'Official CLI must exit successfully');
  return { stdout: r.stdout, milliseconds: performance.now() - start };
}
function hook(session, event, extra = {}) {
  const r = run(['hook', '--agent', 'codex'], JSON.stringify({ session_id: session, turn_id: 'synthetic', cwd: project, ...event }), extra);
  return { output: JSON.parse(r.stdout), milliseconds: r.milliseconds };
}
function edit(session, fixed = false) {
  const patch = fixed ? '*** Begin Patch\n*** Update File: math.js\n@@\n-export const add = (a,b) => a-b;\n+export const add = (a,b) => a+b;\n*** End Patch\n' : '*** Begin Patch\n*** Add File: math.js\n+export const add = (a,b) => a-b;\n*** End Patch\n';
  return hook(session, { hook_event_name: 'PostToolUse', tool_name: 'apply_patch', tool_input: { command: patch }, tool_response: 'Success. Updated math.js' });
}
function stop(session, message, extra = {}) {
  return hook(session, { hook_event_name: 'Stop', last_assistant_message: message, stop_hook_active: false }, extra);
}
try {
  mkdirSync(join(project, '.codex'));
  const foreign = { hooks: { SessionStart: [{ hooks: [{ type: 'command', command: 'echo synthetic-foreign-hook' }] }] } };
  const settings = join(project, '.codex/hooks.json'); writeFileSync(settings, JSON.stringify(foreign));
  run(['init', '--codex']); const once = readFileSync(settings, 'utf8');
  run(['init', '--codex']); assert.equal(readFileSync(settings, 'utf8'), once);
  assert(once.includes('echo synthetic-foreign-hook'));
  run(['remove']); assert.deepEqual(JSON.parse(readFileSync(settings, 'utf8')), foreign);
  results.tests.install_remove_preserves_foreign_hooks = true;
  writeFileSync(join(project, 'math.js'), 'export const add = (a,b) => a-b;\n');
  writeFileSync(join(project, 'math.test.js'), "import { test } from 'node:test'; import assert from 'node:assert/strict'; import { add } from './math.js'; test('sum',()=>assert.equal(add(2,3),5));\n");
  writeFileSync(join(project, 'package.json'), '{"type":"module"}');
  const test = () => {
    const t = performance.now();
    const r = spawnSync('node', ['--test', 'math.test.js'], { cwd: project, env, encoding: 'utf8' });
    return { exit: r.status, milliseconds: performance.now()-t, stdout: r.stdout };
  };
  edit('live'); results.tests.unverified_completion = stop('live', 'Tudo pronto. A implementação foi concluída com sucesso.');
  assert.equal(results.tests.unverified_completion.output.decision, 'block');
  const failed = test(); assert.notEqual(failed.exit, 0);
  hook('live', { hook_event_name: 'PostToolUse', tool_name: 'Bash', tool_input: { command: 'node --test math.test.js' }, tool_response: { exit_code: failed.exit, stdout: failed.stdout } });
  results.tests.failed_check = stop('live', 'Tudo pronto. A implementação foi concluída com sucesso.');
  assert.equal(results.tests.failed_check.output.decision, 'block');
  writeFileSync(join(project, 'math.js'), 'export const add = (a,b) => a+b;\n');
  edit('live', true); const passed = test(); assert.equal(passed.exit, 0);
  hook('live', { hook_event_name: 'PostToolUse', tool_name: 'Bash', tool_input: { command: 'node --test math.test.js' }, tool_response: { exit_code: passed.exit, stdout: passed.stdout } });
  results.tests.verified_completion = stop('live', 'Tudo pronto. Os testes passaram.');
  assert.deepEqual(results.tests.verified_completion.output, {});
  results.baseline_checks = { failed_exit: failed.exit, passed_exit: passed.exit, failed_ms: failed.milliseconds, passed_ms: passed.milliseconds };
  edit('no-key'); results.tests.no_key = stop('no-key', 'Unverified synthetic completion', { OPENROUTER_API_KEY: '' });
  assert.equal(results.tests.no_key.output.decision, 'block');
  edit('outage'); results.tests.network_failure = stop('outage', 'Synthetic completion during outage', { CANNY_JEV_URL: 'http://127.0.0.1:1', CANNY_JEV_TIMEOUT_MS: '100' });
  assert.equal(results.tests.network_failure.output.decision, 'block');
  results.tests.default_second_stop = hook('no-key', { hook_event_name: 'Stop', last_assistant_message: 'Unverified synthetic completion', stop_hook_active: true }, { OPENROUTER_API_KEY: '' });
  assert(results.tests.default_second_stop.output.systemMessage);
  assert.equal(results.tests.default_second_stop.output.decision, undefined);
  results.tests.status = run(['status', join(home, '.canny/sessions/codex-live.jsonl')]).stdout.replaceAll(stage, '<temporary-fixture>');
  results.tests.replay = run(['replay', join(home, '.canny/sessions/codex-live.jsonl')]).stdout;
  assert(results.tests.replay.includes('all Stop verdicts reproduced'));
  const ledger = readFileSync(join(home, '.canny/sessions/codex-live.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  results.judgments = ledger.filter(e=>e.type==='jev').map(({answers,cached,ms,error})=>({answers,cached,ms,...(error?{error}:{})}));
  assert(results.judgments.some(e=>e.answers && !e.cached && !e.error), 'Real OpenRouter judgment required');
  assert(results.judgments.some(e=>e.cached), 'Repeated judgment must use cache');
  mkdirSync(process.argv[2], { recursive: true });
  writeFileSync(join(process.argv[2], 'results.json'), JSON.stringify(results, null, 2)+'\n');
  console.log(JSON.stringify(results, null, 2));
} finally { rmSync(stage, { recursive: true, force: true }); }
