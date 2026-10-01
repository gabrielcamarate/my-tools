import { spawnSync } from 'node:child_process';
import { mkdtempSync, cpSync, readFileSync, writeFileSync, rmSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { performance } from 'node:perf_hooks';
import { realpathSync } from 'node:fs';
const root = realpathSync(new URL('..', import.meta.url));
const cli = realpathSync(process.env.JEV_TEST_FILTER_COMMAND || join((await import('node:os')).homedir(), '.local/bin/jev-test-filter'));
const { openRouterKey } = await import(join(cli, '..', 'provider.js'));
const key = openRouterKey();
if (!key) throw new Error('Shared credential unavailable');
if (!process.argv[2]) throw new Error('Usage: node benchmarks/run-test-filter.mjs LOCAL_EVIDENCE_DIRECTORY');
const stage = mkdtempSync(join(tmpdir(), 'test-filter-live-'));
const cwd = join(stage, 'project');
cpSync(join(root, 'benchmarks/fixtures/test-filter-project'), cwd, { recursive: true });
const freshHome = join(stage, 'home'); mkdirSync(freshHome);
const env = { ...process.env, HOME: freshHome, OPENROUTER_API_KEY: key };
function command(args, extra = {}) {
 const t = performance.now();
 const r = spawnSync(args[0], args.slice(1), { cwd, env: { ...env, ...extra }, encoding: 'utf8', timeout: 60000 });
 if (r.error) throw new Error('Command failed/timeout');
 return { exit: r.status, seconds: (performance.now()-t)/1000, stdout_chars:r.stdout.length, stderr_chars:r.stderr.length, stdout:r.stdout, stderr:r.stderr };
}
function brief(r) { const { stdout,stderr,...v }=r;return v; }
const results={schema_version:1,upstream_sha:'955bdf4e20ff49c3dac0b5b3eee5df0278d5be87',provider:'OpenRouter Decisions',model:'typesafe/jev-1.13',synthetic:true,cloud_actual_test:false,scenarios:[]};
try {
 for (const args of [['git','init','--quiet'],['git','config','user.name','Synthetic Fixture'],['git','config','user.email','fixture@example.invalid'],['git','add','.'],['git','commit','--quiet','-m','fixture baseline']]) {
   if(command(args).exit!==0)throw new Error('Fixture setup failed');
 }
 results.healthy=brief(command(['node','--test'],{ BENCH_TEST_DELAY_MS:'0' }));
 const credits=join(cwd,'src/credits.js');
 writeFileSync(credits,readFileSync(credits,'utf8').replace('return amount;','return amount * 0.8;'));
 const scored=command(['node',cli,'--format','node','--json']);
 const selection=JSON.parse(scored.stdout);
 results.initial_selection=selection;
 results.selection_seconds=scored.seconds;
 for(const delay of ['0','100']) {
   const baseline=command(['node','--test'],{BENCH_TEST_DELAY_MS:delay});
   const candidate=command(['node',cli,'--format','node','--exec','--','node','--test'],{BENCH_TEST_DELAY_MS:delay});
   const record=JSON.parse(readFileSync(join(cwd,'.jev-test-filter/last.json'),'utf8'));
   const replay=command(['node',cli,'--replay','.jev-test-filter/last.json','--json']);
   results.scenarios.push({delay_ms_per_test:Number(delay),baseline:brief(baseline),candidate:brief(candidate),selection:JSON.parse(replay.stdout),record_model:record.model??null});
 }
 const beforeNoKey=readFileSync(join(cwd,'.jev-test-filter/last.json'),'utf8');
 results.no_key=JSON.parse(command(['node',cli,'--format','node','--json'],{OPENROUTER_API_KEY:''}).stdout);
 results.replay=JSON.parse(command(['node',cli,'--replay','.jev-test-filter/last.json','--json']).stdout);
 results.record_preserved_after_no_key=JSON.stringify(JSON.parse(readFileSync(join(cwd,'.jev-test-filter/last.json'),'utf8')))===JSON.stringify(JSON.parse(beforeNoKey));
 command(['git','checkout','--','src/credits.js']);
 writeFileSync(join(cwd,'README.md'),readFileSync(join(cwd,'README.md'),'utf8')+'\nDocumentation only.\n');
 results.docs_only=JSON.parse(command(['node',cli,'--format','node','--json']).stdout);
 results.fresh_home=true;
 const destination=process.argv[2];
 if (!destination) throw new Error('Provide a local evidence directory as the first argument');
 mkdirSync(destination,{recursive:true});
 writeFileSync(join(destination,'results.json'),JSON.stringify(results,null,2)+'\n');
 console.log(JSON.stringify({healthy:results.healthy,selected:selection.selected,total:selection.total,fallback:selection.fallback,scenarios:results.scenarios.map(s=>({delay:s.delay_ms_per_test,baseline:s.baseline,candidate:s.candidate,selected:s.selection.selected,total:s.selection.total})),no_key:results.no_key.fallback,docs_selected:results.docs_only.selected,docs_total:results.docs_only.total},null,2));
} finally { rmSync(stage,{recursive:true,force:true}); }
