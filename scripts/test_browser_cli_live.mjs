// Synthetic official CLI acceptance. Never uses a personal browser profile.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {randomUUID} from 'node:crypto';
const source=resolve(process.argv[2]);
const load=p=>import(pathToFileURL(resolve(source,p)).href);
const {fixtureBrowser}=await load('test/helpers.mjs');
const {goalFixture}=await load('test/goal-fixture.mjs');
const folder=mkdtempSync(join(tmpdir(),'jev-cli-acceptance-'));
const session='acceptance-'+randomUUID(),cleanup=[];
const browser=await fixtureBrowser();let opened=false;
async function cli(...args){
 return new Promise((ok,no)=>{
  const child=spawn('jev-browser',args,{cwd:folder,stdio:['ignore','pipe','pipe']});
  let out='';child.stdout.on('data',b=>out+=b);child.stderr.resume();
  const timer=setTimeout(()=>child.kill('SIGTERM'),120000);
  child.on('error',e=>{clearTimeout(timer);no(e);});
  child.on('close',code=>{clearTimeout(timer);if(code!==0)return no(new Error('CLI failed, exit '+code));try{ok(JSON.parse(out));}catch{no(new Error('CLI response was not JSON'));}});
 });
}
try{
 const f=await goalFixture({after(fn){cleanup.push(fn);}},browser,[{path:'/name',label:'Name'},{path:'/email',label:'Email'}]);
 await cli('open',f.page.url(),'--session',session,'--output-dir',folder);opened=true;
 const start=performance.now();
 const result=await cli('run','--session',session,'--args',JSON.stringify({instruction:'Open Add, enter supplied name and email, Save the contact, and verify Contact created.',values:{name:'Synthetic Contact',email:'cli@example.invalid'}}));
 // A semantic status alone does not prove or disprove a committed effect.
 await cli('assert','--session',session,'--args',JSON.stringify({target:'h2',property:'text',expected:'Contact created'}));
 assert.equal(f.attempts.length,1);assert.equal(f.records.length,1);
 assert.deepEqual(f.records[0],{'/name':'Synthetic Contact','/email':'cli@example.invalid'});
 console.log(JSON.stringify({schema_version:1,interface:'official jev-browser CLI',status:result.status,elapsed_ms:Math.round(performance.now()-start),submissions:f.attempts.length,independent_record_verified:true,exact_values_verified:true,read_only_reconciliation:true,limits:'Synthetic sample; not automatic agent selection or Codex savings'},null,2));
}catch(e){console.error(JSON.stringify({status:'failed',message:e.message}));process.exitCode=1;}
finally{if(opened)await cli('close','--session',session).catch(()=>{process.exitCode=1;});for(const fn of cleanup.reverse())await fn();await browser.close();rmSync(folder,{recursive:true,force:true});}
