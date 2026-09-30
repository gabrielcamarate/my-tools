import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from my_tools.benchmark import compare
from my_tools.core import ToolError


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.a = {"schema_version": 1, "arm": "baseline", "environment": {
            "fixture_revision": "synthetic-v1", "model": "example", "reasoning": "example", "acceptance": "v1"},
            "cases": [{"id": "one", "seconds": 10, "outcome": "accepted", "codex_total_tokens": 100, "recoveries": 0}]}
        self.b = json.loads(json.dumps(self.a))
        self.b["arm"] = "candidate"

    def result(self):
        for name, data in (("baseline", self.a), ("candidate", self.b)):
            (self.base / f"{name}.json").write_text(json.dumps(data))
        return compare(self.base / "baseline.json", self.base / "candidate.json")

    def test_missing_tokens_are_unknown(self):
        self.b["cases"][0]["codex_total_tokens"] = None
        self.assertIsNone(self.result()["change_percent"]["codex_total_tokens"])

    def test_failures_not_excluded_from_faster_candidate(self):
        self.b["cases"][0].update(seconds=2, outcome="failed")
        result = self.result()
        self.assertEqual(result["candidate"]["failed"], 1)
        self.assertEqual(result["quality_regression_cases"], ["one"])

    def test_incomparable_environment_rejected(self):
        self.b["environment"]["model"] = "different"
        with self.assertRaises(ToolError):
            self.result()

    def test_different_or_duplicate_cases_rejected(self):
        self.b["cases"].append(self.b["cases"][0].copy())
        with self.assertRaises(ToolError):
            self.result()

    def test_nonfinite_or_bool_metrics_rejected(self):
        for value in (float("nan"), float("inf"), True, -1):
            with self.subTest(value=value):
                self.b["cases"][0]["seconds"] = value
                with self.assertRaises(ToolError):
                    self.result()

    def test_zero_baseline_does_not_invent_percentage(self):
        self.a["cases"][0]["codex_total_tokens"] = 0
        self.assertIsNone(self.result()["change_percent"]["codex_total_tokens"])
