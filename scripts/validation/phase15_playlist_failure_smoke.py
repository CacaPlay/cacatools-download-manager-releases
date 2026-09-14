#!/usr/bin/env python3
"""Static smoke check for playlist terminal states and retry controls."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
js = (ROOT / "app-ui/main.js").read_text(encoding="utf-8")
rust = (ROOT / "src-tauri/src/lib.rs").read_text(encoding="utf-8")
checks = {
    "terminal card": "playlist-terminal-card" in js,
    "last error": "last_error" in js and "last_error" in rust,
    "retry failed": "retry_failed_playlist_items" in js and "retry_failed_playlist_items" in rust,
    "batch pause": "set_playlist_batch_paused" in js and "set_playlist_batch_paused" in rust,
    "lossy output": "String::from_utf8_lossy(&bytes)" in rust,
}
report = {
    "suite": "Phase 15 playlist failure and recovery",
    "passed": all(checks.values()),
    "steps": [{"name": name, "passed": passed} for name, passed in checks.items()],
}
out = ROOT / "docs/tests/phase15-playlist-failure-smoke.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
raise SystemExit(0 if report["passed"] else 1)
