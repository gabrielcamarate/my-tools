"""Repair must preserve the previously active source and cache on failure."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from my_tools import pruner
from my_tools.core import ToolError

class RepairTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name);self.target=self.base/('a'*40)
        (self.target/'source').mkdir(parents=True)
        (self.target/'source/sentinel').write_text('old')
        self.manager=SimpleNamespace(state=lambda:{'tools':{'jev-pruner':{'active':'a'*40}}},
            location=lambda n,c:self.target,spec=lambda n:{})
        self.check=patch('my_tools.pruner.check');self.check.start();self.addCleanup(self.check.stop)
        self.reg=patch('my_tools.plugins.registry',return_value={'tools':{'jev-pruner':{'root':str(self.target/'source')}}})
        self.reg.start();self.addCleanup(self.reg.stop)
        self.owner=patch('my_tools.plugins.ownership');self.owner.start();self.addCleanup(self.owner.stop)
    def prepare(self, stage, spec, commit):
        (stage/'source').mkdir();(stage/'source/sentinel').write_text('new')
    def test_patch_cannot_modify_pruning_engine(self):
        with patch('my_tools.pruner.checked',return_value='1\t1\tsrc/output.ts') as run:
            with self.assertRaises(ToolError):pruner.apply_provider(self.target/'source')
            self.assertEqual(run.call_count,1)
    def test_patch_conflict_never_applies_partial_changes(self):
        stat=pruner.checked(['git','apply','--numstat',str(pruner.PATCH)])
        with patch('my_tools.pruner.checked',side_effect=[stat,ToolError('conflict')]) as run:
            with self.assertRaises(ToolError):pruner.apply_provider(self.target/'source')
            self.assertEqual(run.call_count,2)
            self.assertIn('--check',run.call_args.args[0])
    def test_build_failure_does_not_touch_active_or_cache(self):
        with patch('my_tools.pruner.prepare',side_effect=ToolError('build failed')),patch('my_tools.plugins.refresh') as refresh:
            with self.assertRaises(ToolError):pruner.rebuild(self.manager)
            refresh.assert_not_called()
        self.assertEqual((self.target/'source/sentinel').read_text(),'old')
        self.assertEqual(list(self.base.iterdir()),[self.target])
    def test_cache_failure_restores_old_source_before_reinstall(self):
        observed=[]
        def refresh(link):
            observed.append((self.target/'source/sentinel').read_text())
            if len(observed)==1:raise ToolError('cache failed')
        with patch('my_tools.pruner.prepare',side_effect=self.prepare),patch('my_tools.plugins.refresh',side_effect=refresh):
            with self.assertRaises(ToolError):pruner.rebuild(self.manager)
        self.assertEqual(observed,['new','old'])
        self.assertEqual(list(self.base.iterdir()),[self.target])
    def test_success_removes_owned_previous_source(self):
        with patch('my_tools.pruner.prepare',side_effect=self.prepare),patch('my_tools.plugins.refresh'):
            self.assertEqual(pruner.rebuild(self.manager)['status'],'repaired')
        self.assertEqual((self.target/'source/sentinel').read_text(),'new')
        self.assertEqual(list(self.base.iterdir()),[self.target])

if __name__=='__main__':unittest.main()
