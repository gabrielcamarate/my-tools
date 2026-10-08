"""Real app-server engine + synthetic ChatGPT backend + optional live Jev.

This verifies replacement/fallback/continuation mechanics, not ChatGPT inference quality
or the latency of its real compaction service. The optional --chatgpt arm uses an
in-memory access-token snapshot; it never refreshes or changes personal authentication.
"""
import argparse, base64, json, os, queue, subprocess, tempfile, threading, time, uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--mode',choices=('baseline','jev','missing-key'),required=True);parser.add_argument('--chatgpt',action='store_true');parser.add_argument('--mock-jev',action='store_true');parser.add_argument('--model',default='gpt-6-sol');args=parser.parse_args()
requests=[]
class Backend(BaseHTTPRequestHandler):
 protocol_version="HTTP/1.1"
 def log_message(self,*_):pass
 def do_GET(self):
  payload=b'{"models":[]}'
  if self.headers.get('Upgrade'):
   self.send_response(426);self.send_header('Content-Length','0');self.end_headers();return
  self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
 def do_POST(self):
  raw=self.rfile.read(int(self.headers.get('Content-Length','0')));body=json.loads(raw)
  items=body.get('input',[]);is_compact=any(i.get('type')=='compaction_trigger' for i in items) or '/compact' in self.path
  requests.append({'compact':is_compact,'items':items,'chars':len(raw)})
  if is_compact:
   item={'type':'compaction','encrypted_content':'SYNTHETIC_CHECKPOINT'}
  else:
   text=json.dumps(items)
   valid=all(s in text for s in ('REQUIREMENT_SENTINEL','half-up','125')) or any(i.get('encrypted_content')=='SYNTHETIC_CHECKPOINT' for i in items)
   item={'type':'message','role':'assistant','id':'answer','content':[{'type':'output_text','text':'CONTINUATION_PASS' if valid else 'CONTINUATION_FAIL'}]}
  events=[{'type':'response.output_item.done','item':item},{'type':'response.completed','response':{'id':'response-'+str(len(requests)),'usage':{'input_tokens':0,'output_tokens':0,'total_tokens':0}}}]
  payload=''.join('data: '+json.dumps(event)+'\n\n' for event in events).encode()
  self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Content-Length',str(len(payload)));self.end_headers()
  self.wfile.write(payload)
  self.wfile.flush()

server=ThreadingHTTPServer(('127.0.0.1',0),Backend);threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with tempfile.TemporaryDirectory(prefix='codex-jev-engine-') as temporary:
  home=Path(temporary);(home/'.codex-jev-lab').touch();codex_home=home/'codex';codex_home.mkdir()
  # Fake credentials only work with the owned loopback mock backend.
  claims={'exp':int(time.time())+3600,'https://api.openai.com/auth':{'chatgpt_plan_type':'pro','chatgpt_account_id':'synthetic-account'}}
  jwt='e30.'+base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')+'.synthetic'
  (codex_home/'auth.json').write_text(json.dumps({'auth_mode':'chatgpt','OPENAI_API_KEY':None,'tokens':{'id_token':jwt,'access_token':jwt,'refresh_token':'synthetic-unused','account_id':'synthetic-account'},'last_refresh':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}))
  (codex_home/'auth.json').chmod(0o600)
  if args.chatgpt:(codex_home/'auth.json').unlink()
  config='openai_base_url="http://127.0.0.1:'+str(server.server_port)+'"\nchatgpt_base_url="http://127.0.0.1:'+str(server.server_port)+'"\nmodel="gpt-5.5"\n[features]\nenable_request_compression=false\nlocal_thread_store_compression=false\n'
  if args.chatgpt:config='model='+json.dumps(args.model)+'\nmodel_reasoning_effort="low"\n[features]\nenable_request_compression=false\nlocal_thread_store_compression=false\n'
  (codex_home/'config.toml').write_text(config)
  env={**os.environ}
  if args.mode=='missing-key':env['OPENROUTER_API_KEY']=''
  launcher=Path(__file__).parent/'run.py';mode='baseline' if args.mode=='baseline' else 'jev'
  command=['python3',str(launcher),'--source',str(args.source),'--home',str(home),'--mode',mode,'--','app-server']
  if args.mock_jev:
   if args.chatgpt:raise RuntimeError('Synthetic Jev must not be reported as a real-provider test')
   command[command.index('--'):command.index('--')]=['--helper-preload',str(Path(__file__).parent/'mock-provider.ts')]
   env['OPENROUTER_API_KEY']='synthetic-key'
   env['JEV_LAB_SCENARIO']='select'
  error_log=home/'stderr.log'
  with error_log.open('w') as error:
   process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=error,env=env,text=True,bufsize=1,start_new_session=True)
   messages=queue.Queue()
   def reader():
    for line in process.stdout:
     try:messages.put(json.loads(line))
     except ValueError:pass
   threading.Thread(target=reader,daemon=True).start();counter=0;notifications=[]
   def receive(deadline):
    try:return messages.get(timeout=max(.01,deadline-time.monotonic()))
    except queue.Empty:raise RuntimeError('App-server timeout: '+error_log.read_text()[-1600:])
   def rpc(method,params):
    global counter
    counter+=1;identifier=counter
    process.stdin.write(json.dumps({'id':identifier,'method':method,'params':params})+'\n');process.stdin.flush()
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
     message=receive(deadline)
     if message.get('id')==identifier:
      if 'error' in message:raise RuntimeError(str(message['error']))
      return message['result']
     notifications.append(message)
    raise RuntimeError('RPC timed out')
   try:
    rpc('initialize',{'clientInfo':{'name':'codex_jev_lab','version':'1.0'},'capabilities':{'experimentalApi':True}})
    process.stdin.write('{"method":"initialized","params":{}}\n');process.stdin.flush()
    if args.chatgpt:
     # No refresh token, personal config or existing rollout is copied into the fork.
     # API stores externally managed credentials only in this process's memory.
     personal=Path.home()/'.codex/auth.json'
     if not personal.is_file() or personal.stat().st_mode & 0o077:raise RuntimeError('Personal auth snapshot is not a private regular file')
     auth=json.loads(personal.read_text());tokens=auth.get('tokens') or {}
     access=tokens.get('access_token');account=tokens.get('account_id')
     if not access or not account:raise RuntimeError('No reusable access-token/account pair; separate lab login required')
     rpc('account/login/start',{'type':'chatgptAuthTokens','accessToken':access,'chatgptAccountId':account})
     del auth,tokens,access
    history=[{'type':'message','role':'user','content':[{'type':'input_text','text':'Implement invoice calculation. Invoice requirements were deleted and cannot be read again. Keep the important tool result; it is the only evidence of the exact rounding rule.'}]}]
    for i in range(24):history.extend([{'type':'function_call','call_id':'stale'+str(i),'name':'shell','arguments':json.dumps({'command':'ls discarded-'+str(i)})},{'type':'function_call_output','call_id':'stale'+str(i),'output':'obsolete-file.txt\n'*300}])
    history.extend([{'type':'function_call','call_id':'important','name':'shell','arguments':'{"command":"cat invoice-requirements.txt"}'},{'type':'function_call_output','call_id':'important','output':'REQUIREMENT_SENTINEL: half-up rounding; authorization limit 125.'}])
    history.extend([{'type':'message','role':'user','content':[{'type':'input_text','text':'Preserve the important result from cat invoice-requirements.txt. File deleted; no reread possible.'}]}]*8)
    result=rpc('thread/resume',{'threadId':str(uuid.uuid4()),'history':history,'cwd':str(home),'approvalPolicy':'never','sandbox':'read-only'})
    tid=result['thread']['id'];start=time.monotonic();rpc('thread/compact/start',{'threadId':tid})
    deadline=time.monotonic()+120;compacted=False
    while time.monotonic()<deadline:
     message=receive(deadline);notifications.append(message)
     item=message.get('params',{}).get('item',{})
     if message.get('method')=='item/completed' and item.get('type')=='contextCompaction':compacted=True
     if message.get('method')=='turn/completed' and compacted:break
     if message.get('method')=='error' and not message.get('params',{}).get('willRetry'):raise RuntimeError(str(message))
    if not compacted:raise RuntimeError('Compaction completion not observed')
    elapsed=time.monotonic()-start
    rpc('turn/start',{'threadId':tid,'input':[{'type':'text','text':'Use only preserved conversation evidence. State the exact rounding rule and authorization limit. Reply with ROUNDING=<rule>; LIMIT=<number>. Do not use tools.'}]})
    deadline=time.monotonic()+120;answer=''
    while time.monotonic()<deadline:
     message=receive(deadline);notifications.append(message)
     item=message.get('params',{}).get('item',{})
     if message.get('method')=='item/completed' and item.get('type')=='agentMessage':answer+=item.get('text','')
     if message.get('method')=='turn/completed':break
    compact_calls=sum(r['compact'] for r in requests)
    if not args.chatgpt:
     assert compact_calls==(0 if args.mode=='jev' else 1),requests
     if args.mode=='jev':assert 'CONTINUATION_PASS' in answer,answer
    else:
     normalized=answer.lower().replace(' ', '-');assert 'half-up' in normalized and '125' in answer, 'Necessary requirement lost in real continuation'
    report={'mode':args.mode,'engine_compaction_completed':True,'native_mock_calls':compact_calls,'compaction_seconds':round(elapsed,3),'continuation_answer':answer,'forwarded_request_chars':[r['chars'] for r in requests],'backend':'real ChatGPT' if args.chatgpt else 'synthetic loopback; timings are not real ChatGPT compaction timings'}
    if args.chatgpt:
     report['native_mock_calls']=None
     report['model']=args.model
     logs=list(codex_home.rglob('*.jsonl'))
     compacted_records=[]
     for log in logs:
      for line in log.read_text().splitlines():
       try:record=json.loads(line)
       except ValueError:continue
       if record.get('type')=='compacted':compacted_records.append(record.get('payload',{}))
     report['compaction_response_ids_present']=[bool(record.get('compaction_response_id')) for record in compacted_records]
     if args.mode=='jev':
      assert compacted_records and not any(report['compaction_response_ids_present']), 'Jev did not replace native compaction'
     else:
      assert any(report['compaction_response_ids_present']), 'Native compaction fallback was not demonstrated'
    print(json.dumps(report,indent=2))
   finally:
    import signal
    if process.poll() is None:
     os.killpg(process.pid,signal.SIGTERM)
     try:process.wait(timeout=8)
     except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
finally:server.shutdown();server.server_close()
