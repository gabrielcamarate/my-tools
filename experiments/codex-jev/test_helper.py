"""Synthetic helper acceptance; no real session or private project input."""
import argparse, json, subprocess, time
from manage import helper_command
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument("--source",required=True);parser.add_argument("--live",action="store_true");parser.add_argument("--recoverable",action="store_true");args=parser.parse_args()
root=Path(args.source)
bun=root/"lab-runtime/node_modules/@oven/bun-linux-x64/bin/bun"
items=[{"type":"message","role":"user","content":[{"type":"input_text","text":"Implement synthetic invoice calculation. Preserve AUTHORIZATION_LIMIT=125 and REQUIREMENT_SENTINEL. Old directory listings for discarded scratch folders are obsolete. The invoice requirements file was deleted after reading and cannot be read again. Its important tool result is the only source of the exact rounding rule; keep that result. Never repeat a completed write."}]}]
for i in range(24):
 items.extend([{"type":"function_call","call_id":f"stale{i}","name":"shell","arguments":json.dumps({"command":f"ls scratch/discarded-{i}"})},{"type":"function_call_output","call_id":f"stale{i}","output":("obsolete-file-name.txt\n"*1000)}])
items.extend([{"type":"function_call","call_id":"important","name":"shell","arguments":json.dumps({"command":"cat invoice-requirements.txt"})},{"type":"function_call_output","call_id":"important","output":"REQUIREMENT_SENTINEL: invoice rounding must use half-up. AUTHORIZATION_LIMIT=125."}])
for i in range(8):items.append({"type":"message","role":"user","content":[{"type":"input_text","text":"Continue implementing invoice calculation. invoice-requirements.txt was deleted and cannot be read again. Preserve the full important tool result from cat invoice-requirements.txt: it is the only evidence of the required exact rounding rule and authorization limit."}]})
if args.recoverable:
 for item in items:
  for part in item.get("content",[]):
   part["text"]=part["text"].replace("The invoice requirements file was deleted after reading and cannot be read again. Its important tool result is the only source of the exact rounding rule; keep that result.", "The requirements remain available in invoice-requirements.txt.").replace("invoice-requirements.txt was deleted and cannot be read again. Preserve the full important tool result from cat invoice-requirements.txt: it is the only evidence of the required exact rounding rule and authorization limit.", "Read invoice-requirements.txt again if needed.")
fixture=json.dumps(items)
env=None
if not args.live:
 import os
 env={**os.environ,"OPENROUTER_API_KEY":""}
t=time.monotonic();p=subprocess.run(helper_command(root),input=fixture,text=True,capture_output=True,env=env,timeout=30)
record={"live":args.live,"recoverable_source":args.recoverable,"returncode":p.returncode,"seconds":round(time.monotonic()-t,3),"input_chars":len(fixture)}
if not args.live:
 assert p.returncode!=0 and not p.stdout, "Missing credential must produce no accepted history"
 record["missing_credential_fallback"]=True
else:
 assert p.returncode==0, "Helper did not accept compaction: "+p.stderr[:300]
 answer=json.loads(p.stdout);keep=answer["keep"];replacements=answer["replace"]
 assert keep==sorted(set(keep)) and all(0<=i<len(items) for i in keep)
 assert 0 in keep, "User requirements lost"
 rebuilt=[]
 for i in keep:
  item=dict(items[i])
  if str(i) in replacements:
   assert item["type"] in ("function_call_output","custom_tool_call_output")
   item["output"]=replacements[str(i)]
  rebuilt.append(item)
 ids={x.get("call_id") for x in rebuilt if x["type"]=="function_call"}
 outputs={x.get("call_id") for x in rebuilt if x["type"]=="function_call_output"}
 assert ids==outputs, "Orphaned tool exchange"
 important=next((x for x in rebuilt if x.get("call_id")=="important" and x["type"]=="function_call_output"), {"output":""})
 requirements_preserved = all(x in important["output"] for x in ("REQUIREMENT_SENTINEL", "half-up", "125"))
 assert all(i in keep for i in range(len(items)-6,len(items))), "Recent context lost"
 record.update({"output_chars":len(json.dumps(rebuilt)),"retained_items":len(keep),"original_items":len(items),"diagnostic":p.stderr.strip(),"requirements_preserved":requirements_preserved,"paired_calls":True})
print(json.dumps(record,indent=2))

if args.live and not args.recoverable and not record["requirements_preserved"]: raise SystemExit(2)
