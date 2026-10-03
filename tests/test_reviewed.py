"""Fault injection for every reviewed interface, including rollback and foreign links."""
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from my_tools import reviewed,commands
from my_tools.core import Manager,ToolError,atomic_json

class ReviewedTests(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
  self.m=Manager(home=self.root/'storage');self.a='1'*40;self.b='2'*40
  self.runtime=patch.object(reviewed,'runtime',return_value=self.root);self.runtime.start();self.addCleanup(self.runtime.stop)
 def fixtures(self,name):
  e={'active':self.a,'bin_dir':str(self.root/'bin'),'skills_dir':str(self.root/'skills'),'claude_dir':str(self.root/'claude')}
  for commit in (self.a,self.b):
   for _,dest in reviewed.links(self.m,name,e,commit):
    if dest.parent==self.root/'skills':continue
    if dest.suffix or '/venv/bin/' in str(dest):dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text('synthetic')
    else:dest.mkdir(parents=True,exist_ok=True);(dest/'SKILL.md').write_text('synthetic')
  reviewed.switch(self.m,name,e,self.a)
  atomic_json(self.m.home/'interfaces.json',{'schema_version':1,'tools':{name:e}})
  return e
 def names(self):return [n for n,s in self.m.tools.items() if s['installer']=='reviewed-source-v1']
 def test_update_rollback_every_interface(self):
  for name in self.names():
   with self.subTest(tool=name):
    e=self.fixtures(name)
    for c in (self.b,self.a):
     reviewed.synchronize(self.m,name,c)
     self.assertEqual(reviewed.registry(self.m)['tools'][name]['active'],c)
     for l,d in reviewed.links(self.m,name,e,c):self.assertEqual(l.resolve(),d.resolve())
 def test_persistence_failure_restores_every_interface(self):
  for name in self.names():
   with self.subTest(tool=name):
    e=self.fixtures(name)
    with patch.object(reviewed,'atomic_json',side_effect=OSError('synthetic')):
     with self.assertRaises(OSError):reviewed.synchronize(self.m,name,self.b)
    for l,d in reviewed.links(self.m,name,e,self.a):self.assertEqual(l.resolve(),d.resolve())
 def test_foreign_command_is_preserved(self):
  e=self.fixtures('jev-axi');link=reviewed.links(self.m,'jev-axi',e,self.a)[0][0];link.unlink();link.write_text('user')
  with self.assertRaises(ToolError):reviewed.synchronize(self.m,'jev-axi',self.b)
  self.assertEqual(link.read_text(),'user')
 def test_partial_switch_restores_previous_links(self):
  e=self.fixtures('jev-axi');calls=0;original=commands.replace_link
  def replace(l,d):
   nonlocal calls
   calls+=1
   if calls==2:raise OSError('synthetic')
   original(l,d)
  with patch.object(commands,'replace_link',side_effect=replace):
   with self.assertRaises(OSError):reviewed.synchronize(self.m,'jev-axi',self.b)
  for l,d in reviewed.links(self.m,'jev-axi',e,self.a):self.assertEqual(l.resolve(),d.resolve())
 def test_patch_paths_refuse_traversal(self):
  spec={'interface':{'kind':'npm','manifest':'../escape','commands':{},'skills':[],'patch_paths':[]}}
  with self.assertRaises(ToolError):reviewed.interface(spec)
 def test_contract_change_stops_install(self):
  s=self.m.spec('jev-axi');p=self.root/s['interface']['manifest'];p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
  with self.assertRaises(ToolError):reviewed.contract(self.root,s)

 def repair_fixture(self, name='jev-axi'):
  target=self.m.location(name,self.a);(target/'source').mkdir(parents=True)
  (target/'source/sentinel').write_text('old')
  atomic_json(target/'installation.json',{'schema_version':1,'hashes':{'sentinel':'old'}})
  self.m.save({'schema_version':1,'tools':{name:{'active':self.a,'previous':None,'accepted':[self.a],'catalog_commit':self.a}}})
  return target
 def prepared(self, stage, spec, commit):
  (stage/'source').mkdir();(stage/'source/sentinel').write_text('new')
 def test_repair_failed_build_preserves_active(self):
  target=self.repair_fixture()
  with patch.object(reviewed,'hashes',return_value={'sentinel':'old'}),patch.object(reviewed,'prepare',side_effect=ToolError('build')):
   with self.assertRaises(ToolError):reviewed.repair(self.m,'jev-axi')
  self.assertEqual((target/'source/sentinel').read_text(),'old')
  self.assertEqual(list(target.parent.iterdir()),[target])
 def test_repair_failed_sync_restores_source_and_python_runtime(self):
  target=self.repair_fixture('semdecide');native=self.m.home/'native/semdecide'/self.a
  native.mkdir(parents=True);(native/'sentinel').write_text('original runtime')
  def fail(*args):
   native.mkdir();(native/'sentinel').write_text('candidate runtime');raise ToolError('sync')
  with patch.object(reviewed,'hashes',return_value={'sentinel':'old'}),patch.object(reviewed,'prepare',side_effect=self.prepared),patch.object(reviewed,'check'),patch.object(reviewed,'synchronize',side_effect=fail):
   with self.assertRaises(ToolError):reviewed.repair(self.m,'semdecide')
  self.assertEqual((target/'source/sentinel').read_text(),'old')
  self.assertEqual((native/'sentinel').read_text(),'original runtime')
 def test_repair_success_removes_only_owned_backup(self):
  target=self.repair_fixture()
  with patch.object(reviewed,'hashes',return_value={'sentinel':'old'}),patch.object(reviewed,'prepare',side_effect=self.prepared),patch.object(reviewed,'check'),patch.object(reviewed,'synchronize'):
   self.assertEqual(reviewed.repair(self.m,'jev-axi')['status'],'repaired')
  self.assertEqual((target/'source/sentinel').read_text(),'new')
  self.assertEqual(list(target.parent.iterdir()),[target])
 def test_repair_refuses_modified_active_source(self):
  target=self.repair_fixture()
  with patch.object(reviewed,'hashes',return_value={'sentinel':'modified'}),patch.object(reviewed,'prepare') as build:
   with self.assertRaises(ToolError):reviewed.repair(self.m,'jev-axi')
   build.assert_not_called()
