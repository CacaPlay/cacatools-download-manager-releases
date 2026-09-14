#!/usr/bin/env python3
"""Verify that every rendered Phase 16 download-manager control has a handler.

The visual layouts are intentionally independent, but they share one controller. This
static gate prevents a button, selector or row action from being added to either layout
without wiring it in ``app-ui/download-manager/index.js``.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from phase16_hashing import manager_source_files, source_fingerprint

ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "app-ui/download-manager/index.js"
VIEW_DIR = ROOT / "app-ui/download-manager/view"
REPORT = ROOT / "docs/tests/phase16-control-contract-gate.json"
ATTRIBUTE_RE = re.compile(r"\bdata-dm-([a-z0-9-]+)\b")
SELECTOR_CALL_RE = re.compile(
    r"(?:querySelector(?:All)?|closest|matches)\(\s*(['\"])(.*?)\1\s*\)", re.DOTALL
)
PASSIVE_ATTRIBUTES = {
    "engine-detail",
    "engine-state",
    "layout",
    "modal",
    "theme",
}


def rendered_attributes() -> set[str]:
    attributes: set[str] = set()
    for path in sorted(VIEW_DIR.glob("*.js")):
        attributes.update(ATTRIBUTE_RE.findall(path.read_text(encoding="utf-8")))
    return attributes


def handled_attributes(source: str) -> set[str]:
    attributes: set[str] = set()
    for match in SELECTOR_CALL_RE.finditer(source):
        attributes.update(ATTRIBUTE_RE.findall(match.group(2)))
    return attributes


def main() -> int:
    controller = CONTROLLER.read_text(encoding="utf-8")
    rendered = rendered_attributes()
    handled = handled_attributes(controller)
    interactive = rendered - PASSIVE_ATTRIBUTES
    missing = sorted(interactive - handled)
    orphaned = sorted((handled - rendered) - {"thumbnail"})
    source_files, source_hash = source_fingerprint(
        [
            Path(__file__),
            ROOT / "scripts/validation/phase16_hashing.py",
            CONTROLLER,
            *sorted(VIEW_DIR.glob("*.js")),
        ]
    )
    checks = [
        {
            "name": "rendered-controls-have-handlers",
            "pass": not missing,
            "detail": missing or f"{len(interactive)} interactive attributes are wired",
        },
        {
            "name": "controller-selectors-are-rendered",
            "pass": not orphaned,
            "detail": orphaned or f"{len(handled)} controller selectors are represented",
        },
        {
            "name": "independent-layout-control-surface-is-substantial",
            "pass": len(interactive) >= 30,
            "detail": len(interactive),
        },
    ]
    payload = {
        "gate": "phase16-control-contract-gate",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "passed": all(check["pass"] for check in checks),
        "sourceFiles": source_files,
        "sourceHash": source_hash,
        "renderedAttributes": sorted(rendered),
        "handledAttributes": sorted(handled),
        "passiveAttributes": sorted(PASSIVE_ATTRIBUTES),
        "checks": checks,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if payload["passed"]:
        print(
            f"OK: {len(interactive)} controles visuales del gestor tienen contrato de interacción."
        )
        return 0
    for check in checks:
        if not check["pass"]:
            print(f"FAIL {check['name']}: {check['detail']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
