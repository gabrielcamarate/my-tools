// Synthetic offline regression: native Canny config, no provider or private project data.
import {spawnSync} from 'node:child_process';
import {mkdtempSync,mkdirSync,writeFileSync,rmSync,realpathSync} from 'node:fs';
import {tmpdir,homedir} from 'node:os';
import {join} from 'node:path';
import assert from 'node:assert/strict';
const cli=realpathSync(join(homedir(),'.local/bin/canny'));
const temp=mkdtempSync(join(tmpdir(),'canny-artifact-scope-'));
const project=join(temp,'project'), home=join(temp,'home');
mkdirSync(project); mkdirSync(home);
const env={...process.env,HOME:home,CANNY_HOME:join(home,'.canny'),OPENROUTER_API_KEY:''};
const config={ignore:['(^|/)backups/epr-plant/(add-roads-r11|add-crossings-r12)\\.py$'],strict:true};
const run=(args,input='')=>{
 const r=spawnSync('node',[cli,...args],{cwd:project,env,input,encoding:'utf8',timeout:10000});
 assert.equal(r.status,0,r.stderr);return r.stdout;
};
const hook=(id,event)=>JSON.parse(run(['hook','--agent','codex'],JSON.stringify({session_id:id,turn_id:'fixture',cwd:project,...event})));
const edit=(id,path)=>hook(id,{hook_event_name:'PostToolUse',tool_name:'apply_patch',tool_input:{command:`*** Begin Patch\n*** Add File: ${path}\n+synthetic = 1\n*** End Patch\n`},tool_response:`Success. Updated ${path}`});
const stop=id=>hook(id,{hook_event_name:'Stop',last_assistant_message:'Done.',stop_hook_active:false});
try{
 writeFileSync(join(project,'.canny.json'),JSON.stringify(config));
 edit('untrusted','backups/epr-plant/add-crossings-r12.py');
 assert.equal(stop('untrusted').decision,'block');
 run(['trust']);
 edit('artifact','backups/epr-plant/add-roads-r11.py');
 edit('artifact','backups/epr-plant/add-crossings-r12.py');
 assert.notEqual(stop('artifact').decision,'block');
 edit('app','src/feature.ts');assert.equal(stop('app').decision,'block');
 hook('app',{hook_event_name:'PostToolUse',tool_name:'Bash',tool_input:{command:'node --test'},tool_response:{exit_code:1,stdout:'synthetic test failure'}});
 assert.equal(stop('app').decision,'block');
 const testPath=join(project,'scope.test.cjs');
 writeFileSync(testPath,"const {test}=require('node:test');const assert=require('node:assert/strict');test('fixture',()=>assert.equal(2+2,4));\n");
 const result=spawnSync('node',['--test','scope.test.cjs'],{cwd:project,env,encoding:'utf8'});assert.equal(result.status,0);
 hook('app',{hook_event_name:'PostToolUse',tool_name:'Bash',tool_input:{command:'node --test scope.test.cjs'},tool_response:{exit_code:result.status,stdout:result.stdout}});
 assert.notEqual(stop('app').decision,'block');
 edit('mixed','backups/epr-plant/add-crossings-r12.py');edit('mixed','src/feature.ts');assert.equal(stop('mixed').decision,'block');
 edit('other','backups/epr-plant/unknown.py');assert.equal(stop('other').decision,'block');
 edit('ordinary','scripts/ordinary.py');assert.equal(stop('ordinary').decision,'block');
 console.log(JSON.stringify({synthetic:true,provider_calls:0,untrusted_config_blocks:true,reviewed_artifact_scripts_do_not_require_app_suite:true,app_without_check_blocks:true,failed_check_blocks:true,app_passing_check_allows:true,mixed_change_blocks:true,unknown_generator_blocks:true,ordinary_python_blocks:true,cleanup:'owned fixture removed in finally'}));
}finally{rmSync(temp,{recursive:true,force:true});}
