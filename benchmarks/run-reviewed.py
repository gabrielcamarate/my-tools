from pathlib import Path
import json,os,shlex,subprocess,tempfile,time
root=Path(__file__).resolve().parents[1];out=root/'benchmarks/results/batch-2026-10-02';out.mkdir(parents=True,exist_ok=True)
p=Path.home()/'.config/siftr/.env'
key=os.environ.get('OPENROUTER_API_KEY')
if not key:
 assert p.stat().st_mode&0o077==0
 key=next(shlex.split(x.strip().removeprefix('export ').split('=',1)[1])[0] for x in p.read_text().splitlines() if x.strip().removeprefix('export ').startswith('OPENROUTER_API_KEY='))
original_home=Path.home()
with tempfile.TemporaryDirectory(prefix='jev-batch-live-') as temp:
 d=Path(temp);env={**os.environ,'HOME':str(d),'OPENROUTER_API_KEY':key}
 for k in ('TYPESAFE_API_KEY','TYPESAFE_AI_API_KEY'):env.pop(k,None)
 def write(n,v):p=d/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(v);return p
 write('route.json',json.dumps({'request':'Fui cobrado duas vezes. Quero o reembolso.','routes':{'billing':'Cobranças, pagamentos e reembolsos','technical':'Erros técnicos'}}))
 write('draft.md','É importante destacar que estamos revolucionando o futuro. Esta solução incrível eleva sua experiência a um novo patamar.\n')
 write('logs.txt','ERROR database unavailable request=101\nERROR database unavailable request=102\nERROR database unavailable request=103\nINFO healthcheck OK\n')
 write('questions.json',json.dumps({'questions':{'refund':{'type':'noul','instructions':'Does the message request a refund?'}}}))
 write('examples.jsonl','\n'.join(json.dumps({'id':str(i),'state':text,'labels':{'refund':label},'split':'tune'}) for i,(text,label) in enumerate([('Please refund my duplicate charge.',True),('Hello, how are you?',False)])))
 source=write('repo/credits.py','def refund_failed_job(balance, reserved):\n    return balance + reserved\n')
 subprocess.run(['git','init','-q',str(d/'repo')],check=True)
 base={'openapi':'3.0.3','info':{'title':'Synthetic','version':'1'},'paths':{'/items':{'get':{'description':'Returns all items, including archived items.','responses':{'200':{'description':'OK'}}}}}}
 head=json.loads(json.dumps(base));head['paths']['/items']['get']['description']='Returns only active items. Archived items are never returned.'
 write('base.json',json.dumps(base));write('head.json',json.dumps(head))
 specsource=Path.home()/'.local/share/my-tools/tools/jev-spec/f5868225fde330ec068378edb273d77015da847e/source'
 write('spec.md','# Requirements\n\n## REQ-REFUND-1\nReturn the balance plus all reserved credits when a job fails.\n')
 write('credits.ts','export function refund(balance: number, reserved: number) { return balance + reserved; }\n')
 write('jev-spec.config.mjs',f"import {{defineConfig,noul}} from {json.dumps(str(specsource/'dist/index.js'))};\nexport default defineConfig({{targets:{{refund:{{specPath:'spec.md',codePaths:['credits.ts'],rubrics:{{'REQ-REFUND-1':noul('Does the function return the balance plus the reserved credits?')}},assertions:{{'REQ-REFUND-1':{{minProbability:0.8}}}}}}}}}});\n")
 cmds=[('jev-axi',['jev-axi','pick','Which team?','--options','billing,technical','--text','I was charged twice. Please refund.','--json']),('jev-recipes',['jev-recipes','run','route',str(d/'route.json')]),('jev-calibrate',['jev-calibrate','check','--dir',str(d),'--provider','openrouter','--json']),('tocsin',['tocsin','triage',str(d/'logs.txt'),'--only','page,ticket,log','--no-cache']),('docjev',['docjev','classify',str(original_home/'.local/share/my-tools/tools/docjev/c7abe276a970605feb9cb8b27513365b6c10726e/source/examples/classify/inbox/d01.pdf'),'--rules',str(original_home/'.local/share/my-tools/tools/docjev/c7abe276a970605feb9cb8b27513365b6c10726e/source/examples/classify/rules.yaml'),'--no-cache']),('jev-spec',['jev-spec','check','--config',str(d/'jev-spec.config.mjs'),'--format','json']),('jev-oas-sentinel',['jev-oas-sentinel','compare','--no-config','--base',str(d/'base.json'),'--head',str(d/'head.json'),'--max-jev-calls','1']),('hunch',['hunch','--cwd',str(d/'repo'),'find','Where are reserved credits returned after a failed job?','--provider','typesafe','--no-fallback','--reporter','json']),('snifftest',['snifftest','check',str(d/'draft.md'),'--format','json','--yes','--no-cache']),('semdecide',['semdecide','is','Does this request a refund?','--text','Please refund my duplicate charge.','--json','--retries','0'])]
 rows=[]
 for name,cmd in cmds:
  t=time.monotonic();r=subprocess.run(cmd,cwd=d,env=env,capture_output=True,text=True,timeout=120)
  text=(r.stdout+'\n'+r.stderr).replace(key,'<redacted>').replace(str(d),'<synthetic-fixture>').replace(str(original_home),'<user-home>')
  row={'tool':name,'exit':r.returncode,'seconds':round(time.monotonic()-t,3),'output':text[-10000:]}
  rows.append(row);print(name,r.returncode,text[:250],flush=True)
 results={x['tool']:x for x in rows}
 assert all(x['exit']==0 for x in rows), 'A synthetic command failed; inspect the sanitized result'
 parsed={n:json.JSONDecoder().raw_decode(x['output'].lstrip())[0] for n,x in results.items() if n!='tocsin'}
 assert parsed['jev-axi']['pick']=='billing'
 assert parsed['jev-recipes']['result']['route']=='billing'
 assert parsed['jev-calibrate']['provider']=='openrouter'
 assert parsed['docjev']['category']=='invoice'
 assert parsed['jev-spec']['passed'] is True
 assert parsed['jev-oas-sentinel']['metrics']['semantic_successes']==1
 assert parsed['jev-oas-sentinel']['findings']
 assert parsed['hunch']['matches'][0]['file']=='credits.py'
 assert parsed['snifftest']['judgment']['answered']==5
 assert parsed['semdecide']['verdict']=='true'
 assert 'ERROR database unavailable request=<NUM>' in results['tocsin']['output']
 (out/'live.json').write_text(json.dumps({'schema_version':1,'provider':'openrouter','synthetic_only':True,'codex_savings':'not_measured','rows':rows},indent=2,ensure_ascii=False)+'\n')
