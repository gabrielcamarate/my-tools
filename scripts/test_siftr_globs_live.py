"""Synthetic official CLI regression: unsupported braces vs repeated fnmatch globs."""
import json
import subprocess
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="siftr-globs-") as folder:
    root = Path(folder)
    target = root / "web/app"
    target.mkdir(parents=True)
    (target / "credits.ts").write_text("export function refund_failed_job(balance: number, reserved: number) {\n  // Return reserved credits when a job fails.\n  return balance + reserved;\n}\n")
    (target / "theme.tsx").write_text("export function Theme() { return <div>Theme settings</div>; }\n")
    def search(*globs):
        cmd = ["siftr", "search", "Where are reserved credits refunded after a job fails?", folder, "--no-ignore", "--json", "--stats"]
        for pattern in globs:
            cmd.extend(["-g", pattern])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        assert result.returncode in (0, 1), "Siftr CLI failed; provider response suppressed"
        return json.loads(result.stdout)
    bad = search("web/**/*.{ts,tsx}")
    good = search("*.ts", "*.tsx")
    assert bad["scanned"] == 0 and bad["requests"] == 0
    assert good["scanned"] == 2 and good["requests"] > 0
    assert good["files"][0]["path"] == "web/app/credits.ts"
    print(json.dumps({"schema_version": 1, "interface": "official Siftr CLI", "invalid_glob_scanned": bad["scanned"], "invalid_glob_requests": bad["requests"], "fixed_scanned": good["scanned"], "fixed_requests": good["requests"], "top_path": good["files"][0]["path"], "top_score": good["files"][0]["score"], "elapsed_seconds": good["timings"]["total"], "limits": "Synthetic regression; no Codex task savings measured"}, indent=2))
