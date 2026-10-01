// Synthetic-only acceptance/measurement. No personal profile, login or private project.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
const source=resolve(process.argv[2]);
const load=p=>import(pathToFileURL(resolve(source,p)).href);
const {fixtureBrowser}=await load('test/helpers.mjs');
const {goalFixture}=await load('test/goal-fixture.mjs');
const {wizardFixture}=await load('test/wizard-fixture.mjs');
const {openRouterKey}=await load('dist/provider.js');
assert.ok(openRouterKey(),'OpenRouter credential unavailable');
const {Client}=await load('node_modules/@modelcontextprotocol/client/dist/index.mjs');
const {StdioClientTransport}=await load('node_modules/@modelcontextprotocol/client/dist/stdio.mjs');
const browser=await fixtureBrowser(),results=[];
async function scenario(name,method,make,values,instruction){
 const cleanup=[],t={after(fn){cleanup.push(fn);}};
 const start=performance.now();let client;
 try{
  const f=await make(t);let r,operations=0;
  if(method==='native'){
   await f.page.getByRole('button',{name:'Add',exact:true}).click();operations++;
   for(const [key,value] of Object.entries(values)){await f.page.locator(`[name="/${key}"]`).fill(value);operations++;}
   await f.page.getByRole('button',{name:'Save',exact:true}).click();operations++;
   await f.page.getByRole('heading',{name:'Contact created',exact:true}).waitFor();operations++;
   assert.deepEqual(f.records,[Object.fromEntries(Object.entries(values).map(([k,v])=>['/'+k,v]))]);
   r={status:'complete',usage:{requests:0},verification:{independent:true}};
  }else if(method==='mcp'){
   client=new Client({name:'my-tools-live',version:'1'});
   await client.connect(new StdioClientTransport({command:process.execPath,args:[resolve(source,'dist/mcp-stdio.js')],stderr:'pipe'}));
   assert.ok((await client.listTools()).tools.some(t=>t.name==='browser_run'));
   const opened=await client.callTool({name:'browser_goto',arguments:{url:f.page.url()}});assert.ok(!opened.isError);operations++;
   const called=await client.callTool({name:'browser_run',arguments:{instruction,values}});operations++;
   assert.ok(!called.isError,'MCP browser_run failed');r=called.structuredContent ?? JSON.parse(called.content.find(i=>i.type==='text').text);
  }else{r=await f.core.run(instruction,{values});operations=1;}
  assert.equal(r.status,'complete');assert.equal(f.attempts.length,1);assert.equal(f.records.length,1);
  const flatten=(v,p='')=>Object.entries(v).flatMap(([k,x])=>x&&typeof x==='object'?flatten(x,p+'/'+k):[[p+'/'+k,x]]);
  assert.deepEqual(f.records[0],Object.fromEntries(flatten(values)));
  results.push({name,method,status:r.status,caller_operations:operations,elapsed_ms:Math.round(performance.now()-start),usage:r.usage,steps:r.steps?.length,verification:r.verification,independent_record_verified:true,submissions:f.attempts.length});
 }finally{await client?.close();for(const fn of cleanup.reverse())await fn();}
}
try{
 const fields=Array.from({length:16},(_,i)=>({path:'/field'+i,label:'Field '+i}));
 const values=Object.fromEntries(fields.map((_,i)=>['field'+i,'synthetic-value-'+i]));
 const make=t=>goalFixture(t,browser,fields,{live:true});
 const instruction='Open Add, fill all sixteen supplied fields (field0 through field15), then Save the new contact. Verify the created record.';
 await scenario('sixteen','native',make,values,instruction);
 await scenario('sixteen','sdk',make,values,instruction);
 const nested={student:{name:'Synthetic Student',email:'student@example.invalid'},guardian:{name:'Synthetic Guardian',email:'guardian@example.invalid'},course:'Piano'};
 const nestedMake=t=>goalFixture(t,browser,[{path:'/student/name',label:'Student name'},{path:'/student/email',label:'Student email'},{path:'/guardian/name',label:'Guardian name'},{path:'/guardian/email',label:'Guardian email'},{path:'/course',label:'Instrument',type:'select',options:['Choose','Piano','Viola da gamba']}],{live:true});
 await scenario('nested','sdk',nestedMake,nested,'Add a student with the supplied student name and email, guardian name and email, select course, Save, then verify the new record.');
 await scenario('wizard','sdk',t=>wizardFixture(t,browser,{live:true}),{name:'Synthetic Contact',email:'wizard@example.invalid'},'Create a new contact. Enter the supplied name, continue to the email step, enter the email and Save. Verify the created contact.');
 await scenario('nested','mcp',nestedMake,nested,'Add a student with the supplied student name and email, guardian name and email, select course, Save, then verify the new record.');
 console.log(JSON.stringify({schema_version:1,results,limits:'One sample per case; native baseline uses known selectors; caller operations are not measured Codex turns/tokens; no Cloud runtime test.'},null,2));
}catch(error){console.error(JSON.stringify({status:'failed',code:error.code??error.name,message:'Synthetic acceptance failed; no credential or provider body emitted',completed:results}));process.exitCode=1;}
finally{await browser.close();}
