"""Provider contract, invalid-response fallback and literal preservation."""
import json, os, subprocess, sys
from pathlib import Path
root=Path(sys.argv[1]);lab=Path(__file__).resolve().parent
bun=root/'lab-runtime/node_modules/@oven/bun-linux-x64/bin/bun'
items=[{'type':'message','role':'developer','content':[{'type':'input_text','text':'Do not repeat writes. INITIAL_SENTINEL'}]}]
for i in range(25):
 items += [{'type':'function_call','call_id':str(i),'name':'shell','arguments':'{}'}, {'type':'function_call_output','call_id':str(i),'output': ('NECESSARY_LITERAL_😀' if i==24 else 'obsolete listing\n'*1000)}]
items += [{'type':'message','role':'user','content':[{'type':'input_text','text':'Preserve LAST_SENTINEL'}]}]*8
results=[]
for scenario in ('network','malformed','http-error','invalid-probability','keep-all','select'):
 p=subprocess.run([str(bun),'--preload',str(lab/'mock-provider.ts'),str(root/'jev/codex-jev-compact.ts')],input=json.dumps(items),text=True,capture_output=True,env={**os.environ,'OPENROUTER_API_KEY':'synthetic-key','JEV_LAB_SCENARIO':scenario},timeout=15)
 if scenario=='select':
  assert p.returncode==0,p.stderr
  answer=json.loads(p.stdout)
  assert 0 in answer['keep'] and 49 in answer['keep'] and 50 in answer['keep']
  assert all(i in answer['keep'] for i in range(53,59))
  assert not answer['replace']
  assert items[50]['output']=='NECESSARY_LITERAL_😀'
 else:assert p.returncode!=0 and not p.stdout,(scenario,p.stdout)
 results.append({'case':scenario,'passed':True,'returncode':p.returncode})
print(json.dumps(results,indent=2))
