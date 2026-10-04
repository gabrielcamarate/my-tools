"""Launch an explicitly selected lab engine without editing the installed Codex."""
import argparse, os
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--source',type=Path,required=True)
p.add_argument('--home',type=Path,required=True)
p.add_argument('--mode',choices=('baseline','jev'),required=True)
p.add_argument('arguments',nargs=argparse.REMAINDER)
a=p.parse_args()
real_home=Path.home().resolve();home=a.home.expanduser().resolve()
protected=real_home/'.codex'
if home==real_home or home==protected or protected in home.parents:
 p.error('The lab home must be separate from your personal HOME and CODEX_HOME')
if home.exists() and any(home.iterdir()) and not (home/'.codex-jev-lab').is_file():
 p.error('Refusing to reuse an unowned nonempty directory')
for child in (home/'.codex-jev-lab',home/'codex',home/'helper.sh'):
 if child.is_symlink():p.error('Refusing a symlink inside the lab control paths')
home.mkdir(parents=True,exist_ok=True,mode=0o700)
(home/'.codex-jev-lab').touch()
source=a.source.resolve();binary=source/'target/release/codex'
if not binary.is_file():p.error('Build the separate engine first; installed Codex is never used as fallback')
args=a.arguments
if args and args[0]=='--':args=args[1:]
if not args:p.error('Provide explicit Codex arguments after --')
env={**os.environ,'CODEX_HOME':str(home/'codex'),'HOME':str(home)}
# HOME isolates personal skills, other agent configuration and cache paths.
# An explicitly supplied provider credential is inherited; never copied to disk.
for name in ('CODEX_JEV_COMPACT','CODEX_THREAD_ID','CODEX_CLI_PATH','OPENAI_API_KEY','TYPESAFE_API_KEY'):
 env.pop(name,None)
if a.mode=='jev':
 # Same bounded resolver used by the provider; this avoids losing the credential
 # when HOME is isolated. Only the child environment receives it.
 if 'OPENROUTER_API_KEY' not in env:
  import re
  credential=real_home/'.config/siftr/.env'
  try:
   info=credential.stat()
   if credential.is_file() and info.st_mode & 0o077 == 0:
    for line in credential.read_text().splitlines():
     match=re.fullmatch(r"\s*(?:export\s+)?OPENROUTER_API_KEY\s*=\s*(.*?)\s*",line)
     if match:
      value=match[1]
      if len(value)>=2 and value[0]==value[-1] and value[0] in "\"'":value=value[1:-1]
      else:value=re.split(r"\s+#",value)[0].strip()
      env['OPENROUTER_API_KEY']=value
      break
  except OSError:pass
 bun=source/'lab-runtime/node_modules/@oven/bun-linux-x64/bin/bun'
 helper=home/'helper.sh'
 import shlex
 helper.write_text('#!/bin/sh\nexec '+shlex.quote(str(bun))+' '+shlex.quote(str(source/'jev/codex-jev-compact.ts'))+'\n')
 helper.chmod(0o700)
 env['CODEX_JEV_COMPACT']=str(helper)
os.execve(str(binary),[str(binary),'-c','cli_auth_credentials_store="file"',*args],env)
