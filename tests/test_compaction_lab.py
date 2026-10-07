"""Protect the installed Codex while launching only an explicitly owned lab."""
import json, os, subprocess, tempfile, unittest
from pathlib import Path
RUN=Path(__file__).resolve().parents[1]/'experiments/codex-jev/run.py'
class LabIsolationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.home=self.root/'personal';self.home.mkdir()
  (self.home/'.codex').mkdir();(self.home/'.codex/config.toml').write_text('personal sentinel')
  self.source=self.root/'source';binary=self.source/'target/release/codex';binary.parent.mkdir(parents=True)
  binary.write_text('#!/usr/bin/env python3\nimport os,json,sys\nfrom pathlib import Path\nassert Path(os.environ["CODEX_HOME"]).is_dir(), "Missing lab CODEX_HOME at startup"\nprint(json.dumps({"home":os.environ["HOME"],"codex_home":os.environ["CODEX_HOME"],"helper":os.environ.get("CODEX_JEV_COMPACT"),"thread":os.environ.get("CODEX_THREAD_ID"),"args":sys.argv[1:]}))\n');binary.chmod(0o700)
  self.env={**os.environ,'HOME':str(self.home),'CODEX_HOME':str(self.home/'.codex'),'CODEX_JEV_COMPACT':'untrusted','CODEX_THREAD_ID':'personal-thread','OPENROUTER_API_KEY':''}
 def run_lab(self,home,mode='baseline'):
  return subprocess.run(['python3',str(RUN),'--source',str(self.source),'--home',str(home),'--mode',mode,'--','--version'],env=self.env,text=True,capture_output=True)
 def test_rejects_personal_and_nested_codex_home(self):
  for home in [self.home,self.home/'.codex',self.home/'.codex/nested']:
   self.assertNotEqual(self.run_lab(home).returncode,0)
  self.assertEqual((self.home/'.codex/config.toml').read_text(),'personal sentinel')
 def test_rejects_unowned_nonempty_directory(self):
  home=self.root/'foreign';home.mkdir();(home/'keep').write_text('foreign')
  self.assertNotEqual(self.run_lab(home).returncode,0)
  self.assertEqual((home/'keep').read_text(),'foreign')
 def test_rejects_lab_codex_symlink_to_personal_settings(self):
  home=self.root/'owned';home.mkdir();(home/'.codex-jev-lab').touch()
  (home/'codex').symlink_to(self.home/'.codex',target_is_directory=True)
  self.assertNotEqual(self.run_lab(home).returncode,0)
  self.assertEqual((self.home/'.codex/config.toml').read_text(),'personal sentinel')
 def test_baseline_isolates_home_and_clears_inherited_compactor(self):
  home=self.root/'baseline';r=self.run_lab(home);self.assertEqual(r.returncode,0,r.stderr)
  data=json.loads(r.stdout);self.assertEqual(data['home'],str(home));self.assertEqual(data['codex_home'],str(home/'codex'))
  self.assertIsNone(data['helper']);self.assertIsNone(data['thread']);self.assertIn('cli_auth_credentials_store="file"',data['args'])
 def test_jev_uses_only_lab_helper_and_preserves_personal_config(self):
  home=self.root/'jev';r=self.run_lab(home,'jev');self.assertEqual(r.returncode,0,r.stderr)
  data=json.loads(r.stdout);self.assertEqual(data['helper'],str(home/'helper.sh'))
  self.assertEqual((self.home/'.codex/config.toml').read_text(),'personal sentinel')
if __name__=='__main__':unittest.main()
