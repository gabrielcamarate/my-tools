// Explicit live test: synthetic history only. No key is written or printed.
// Run from the installed source: node --import tsx scripts/test_compaction_live.mjs <source>
import { readFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';

const root = resolve(process.argv[2] || '');
assert(process.argv[2], 'Pass the installed plugin source.');
const { register } = await import(pathToFileURL(join(root, 'hooks/fast-jev.ts')));

const log = (i) => Array.from({ length: 60 }, (_, m) =>
  `2026-10-07T10:${String(m).padStart(2, '0')}:00Z build[${i}] step ${m}: compiled module_${100 + ((i * 37 + m * 11) % 900)}.o in ${5 + ((i + m) % 80)}ms`).join('\n');
const message = (role, text, extra = {}) => ({ role, text, toolUses: [], ...extra });

function transcript() {
  const messages = [message('user', 'Inspect the synthetic build logs, then read config.toml and report the server port.')];
  for (let i = 1; i <= 10; i++) {
    const id = `toolu_${i}`;
    messages.push(message('assistant', '', { toolUses: [{ tool_use_id: id, tool: 'Bash', input: { command: `cat build${i}.log` } }] }));
    messages.push(message('user', '', { toolResults: [{ tool_use_id: id, text: log(i), isError: false }] }));
  }
  messages.push(message('assistant', 'All ten builds compiled; no failures in the logs.'));
  messages.push(message('assistant', '', { toolUses: [{ tool_use_id: 'toolu_cfg', tool: 'Read', input: { file_path: 'config.toml' } }] }));
  messages.push(message('user', '', { toolResults: [{ tool_use_id: 'toolu_cfg', text: '[server]\nport = 8471\nworkers = 3', isError: false }] }));
  messages.push(message('assistant', 'The server port is 8471.'));
  messages.push(message('user', 'Now add a fourth worker and keep the port.'));
  return messages;
}

async function compact({ env, fetch: override, messages = transcript() }) {
  const handlers = {}, logs = [], metrics = [];
  register((name, handler) => { handlers[name] = handler; }, {});
  const $ = {
    env: { get: async (name) => env[name] },
    fs: { read: (path) => readFile(path, 'utf8') },
    http: {
      fetch: override ?? (async (url, init) => {
        const start = performance.now();
        const response = await fetch(url, init);
        const text = await response.text();
        let answers = {};
        try { answers = JSON.parse(text).answers ?? {}; } catch { /* reported by the hook */ }
        metrics.push({ host: new URL(url).host, status: response.status, seconds: +((performance.now() - start) / 1000).toFixed(3),
          model: JSON.parse(init.body).model, questions: Object.keys(JSON.parse(init.body).questions).length,
          answers: Object.keys(answers).length });
        return { status: response.status, ok: response.ok, text };
      }),
    },
    ui: { log: (text) => logs.push(text), toast: () => {} },
  };
  let delegated = false;
  const outcome = await handlers['session.compact']($, { messages }, async () => { delegated = true; return { native: true }; });
  return { outcome, delegated, logs, metrics, input: messages };
}

const home = process.env.HOME;
const live = await compact({ env: { HOME: home } });
assert(!live.delegated, `Jev did not replace the summary: ${live.logs.at(-1)}`);
assert(live.metrics.length > 0 && live.metrics.every((m) => m.status === 200 && m.host === 'openrouter.ai' && m.answers === m.questions));
const kept = live.outcome.messages;
const texts = kept.map((m) => m.text).join('\n');
for (const m of live.input.filter((m) => m.text)) assert(texts.includes(m.text), 'User/assistant text changed');
assert(JSON.stringify(kept).includes('port = 8471'), 'Recent config result was dropped');
const size = (list) => JSON.stringify(list).length;

const missing = await compact({ env: { HOME: home, OPENROUTER_API_KEY: '' } });
assert(missing.delegated && /OPENROUTER_API_KEY is not configured/.test(missing.logs.at(-1)));
const failing = await compact({ env: { HOME: home }, fetch: async () => ({ status: 401, ok: false, text: 'synthetic unauthorized' }) });
assert(failing.delegated && /Jev request failed \(401\)/.test(failing.logs.at(-1)));
const short = await compact({ env: { HOME: home }, messages: transcript().slice(-4) });
assert(short.delegated && /fallback to built-in summary/.test(short.logs.at(-1)));

console.log(JSON.stringify({
  live: { result: live.logs.at(-1), messages: `${kept.length}/${live.input.length}`,
    characters: `${size(live.input)} -> ${size(kept)}`, requests: live.metrics },
  fallback: { missing_key: missing.logs.at(-1), provider_failure: failing.logs.at(-1), short_history: short.logs.at(-1) },
}, null, 2));
