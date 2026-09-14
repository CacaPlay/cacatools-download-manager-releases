#!/usr/bin/env python3
"""Verify the frontend/native Tauri command contract for Phase 16.

The gate prevents a common desktop failure: a visible control invoking a command that
was renamed, removed, or omitted from ``generate_handler!``. It uses only literal
command names; intentionally dynamic command construction is rejected by design.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from phase16_hashing import manager_source_files, source_fingerprint

ROOT = Path(__file__).resolve().parents[2]
RUST_PATH = ROOT / "src-tauri/src/lib.rs"
RUST_SOURCE_DIR = ROOT / "src-tauri/src"
MAIN_PATH = ROOT / "app-ui/main.js"
REPORT = ROOT / "docs/tests/phase16-command-contract-gate.json"

INVOKE_PATTERNS = (
    re.compile(r"(?<![\w.])invoke\s*\(\s*['\"]([a-zA-Z0-9_]+)['\"]"),
    re.compile(r"\bcontext\.invoke\?\.\s*\(\s*['\"]([a-zA-Z0-9_]+)['\"]"),
)
COMMAND_DEF_RE = re.compile(r"#\[tauri::command\]\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+([a-zA-Z0-9_]+)", re.MULTILINE)
HANDLER_RE = re.compile(r"tauri::generate_handler!\s*\[([\s\S]*?)\]\s*\)")


def frontend_commands(files: list[Path]) -> tuple[set[str], list[str]]:
    commands: set[str] = set()
    dynamic: list[str] = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        for pattern in INVOKE_PATTERNS:
            commands.update(pattern.findall(source))
        for line_number, line in enumerate(source.splitlines(), 1):
            if re.search(r"\bfunction\s+invoke\s*\(", line):
                continue
            if re.search(r"(?<![\w.])invoke\s*\(", line) or "context.invoke?.(" in line:
                if not any(pattern.search(line) for pattern in INVOKE_PATTERNS):
                    dynamic.append(f"{path.relative_to(ROOT).as_posix()}:{line_number}")
    return commands, dynamic


def handler_commands(source: str) -> set[str]:
    match = HANDLER_RE.search(source)
    if not match:
        return set()
    commands: set[str] = set()
    for entry in match.group(1).split(","):
        value = re.sub(r"//.*", "", entry).strip()
        if not value:
            continue
        command = value.split("::")[-1].strip()
        if re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", command):
            commands.add(command)
    return commands


def main() -> int:
    frontend_files = [MAIN_PATH, *manager_source_files()]
    invoked, dynamic = frontend_commands(frontend_files)
    rust = RUST_PATH.read_text(encoding="utf-8")
    rust_sources = sorted(RUST_SOURCE_DIR.rglob("*.rs"))
    registered = handler_commands(rust)
    command_defs: set[str] = set()
    for rust_source in rust_sources:
        command_defs.update(COMMAND_DEF_RE.findall(rust_source.read_text(encoding="utf-8")))

    missing_handler = sorted(invoked - registered)
    unmarked_handler = sorted(registered - command_defs)
    source_files, source_hash = source_fingerprint([
        Path(__file__),
        ROOT / "scripts/validation/phase16_hashing.py",
        *rust_sources,
        *frontend_files,
    ])
    checks = [
        {
            "name": "frontend-invocations-are-literal",
            "pass": not dynamic,
            "detail": dynamic or "all command names are statically auditable",
        },
        {
            "name": "frontend-commands-registered",
            "pass": not missing_handler,
            "detail": missing_handler or f"{len(invoked)} frontend commands registered",
        },
        {
            "name": "registered-functions-marked-as-tauri-commands",
            "pass": not unmarked_handler,
            "detail": unmarked_handler or f"{len(registered)} registered commands have #[tauri::command]",
        },
        {
            "name": "native-command-set-is-not-truncated",
            "pass": len(registered) >= 35,
            "detail": len(registered),
        },
    ]
    payload = {
        "gate": "phase16-command-contract-gate",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "passed": all(check["pass"] for check in checks),
        "sourceFiles": source_files,
        "sourceHash": source_hash,
        "frontendCommands": sorted(invoked),
        "registeredCommands": sorted(registered),
        "checks": checks,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if payload["passed"]:
        print(f"OK: contrato frontend/Rust verificado ({len(invoked)} invocaciones, {len(registered)} comandos nativos).")
        return 0
    for check in checks:
        if not check["pass"]:
            print(f"FAIL {check['name']}: {check['detail']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
