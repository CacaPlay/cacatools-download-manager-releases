#!/usr/bin/env python3
"""Conservative Rust/Windows pipeline gate used when Cargo is unavailable.

This does not claim to replace compilation. It catches regressions that previously
reached the user's Windows machine: unsupported reqwest APIs, Clippy patterns,
unbalanced source, unsafe cancellation cleanup and an incorrectly ordered build gate.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

from phase16_hashing import source_fingerprint

ROOT = Path(__file__).resolve().parents[2]
RUST = (ROOT / "src-tauri" / "src" / "lib.rs").read_text(encoding="utf-8")
BUILD = (ROOT / "scripts" / "build-windows-beta.ps1").read_text(encoding="utf-8-sig")
CI = (ROOT / "scripts" / "ci-windows-beta.ps1").read_text(encoding="utf-8-sig")
RUST_GATE = (ROOT / "scripts" / "rust-gate-windows.ps1").read_text(encoding="utf-8-sig")
REPORT = ROOT / "docs" / "tests" / "phase16-rust-static-gate.json"

checks: list[dict[str, Any]] = []


def check(name: str, condition: bool, detail: Any = None) -> None:
    checks.append({"name": name, "pass": bool(condition), "detail": detail})


for token in (
    "use url::{Host, Url};",
    "fn parse_public_http_url",
    "fn url_has_public_http_target",
    "fn ensure_public_network_resolution",
    "fn url_has_public_network_target",
    "fn ipv4_is_non_public",
    "fn ipv6_is_non_public",
    "Some(Host::Ipv6(address))",
    "reqwest::redirect::Policy::custom",
    '"--proto-redir"',
    "fn cancel_download_job",
    "fn normalize_torrent_source",
    "fn valid_btih_hash",
    "fn valid_btmh_hash",
    "fn magnet_auxiliary_url_is_safe",
    "fn cleanup_managed_paths_when_idle",
    "fn queue_torrent_download",
    "fn run_torrent_worker",
    "fn resume_torrent_worker_when_idle",
    "fn scheduled_job_is_torrent",
    "torrent_jobs",
    'find_runtime_binary(app.handle(), "aria2c", "CACATOOLS_ARIA2C")',
    "let mut safe_to_delete = false",
    "if !safe_to_delete",
    "fn search_media_by_title",
    "fn recover_media_source",
    "fn failure_diagnosis",
    "fn verify_direct_availability",
    "fn safe_remote_thumbnail_url",
    "fn discover_page_downloads",
    "fn html_attribute_values",
    "fn page_candidate_score",
    "fn title_similarity",
    "match_reasons",
    "fn create_download_schedule",
    "fn run_download_scheduler",
    "cancel_cleanup",
    "download_schedules",
    "DIRECT_DOWNLOAD_TIMEOUT_SECS: u64 = 7 * 24 * 60 * 60",
    "DOWNLOAD_PROGRESS_UPDATE_INTERVAL_MS: u64 = 500",
    'environment_path_override("CACATOOLS_DATA_DIR")',
    'environment_path_override("CACATOOLS_DOWNLOADS_DIR")',
    "fn absolute_path_override",
    "fn environment_path_override",
    "updated_at: String",
):
    check(f"Requisito Rust: {token}", token in RUST)

check(
    "Las rutas aisladas de datos y descargas solo aceptan valores absolutos",
    "path.is_absolute().then_some(path)" in RUST
    and re.search(r'let data_dir = match environment_path_override\("CACATOOLS_DATA_DIR"\)', RUST) is not None
    and re.search(r'let default_downloads_dir =\s*match environment_path_override\("CACATOOLS_DOWNLOADS_DIR"\)', RUST) is not None
    and "accepts_only_absolute_runtime_path_overrides" in RUST,
)

for label, forbidden in {
    "reqwest blocking read_timeout incompatible": ".read_timeout(",
    "drop de tauri::State": "drop(state)",
    "sort_by candidato ya corregido": "candidates.sort_by(|left, right| right.0.cmp(&left.0))",
    "let-and-return conocido": "let ids = rows.filter_map(Result::ok).collect::<Vec<_>>();\n        ids",
    "borrado forzado tras timeout de cancelación": "for _ in 0..100 {",
    "redirects sin política pública": "reqwest::redirect::Policy::limited(12)",
}.items():
    check(f"Ausente: {label}", forbidden not in RUST)

check(
    "Las descargas directas no conservan el antiguo límite total de dos minutos",
    re.search(r'fn run_download_worker_inner[\s\S]{0,1800}\.timeout\(Duration::from_secs\(DIRECT_DOWNLOAD_TIMEOUT_SECS\)\)', RUST) is not None
    and '.timeout(Duration::from_secs(120))' not in RUST,
)
check(
    "El snapshot conserva historial persistente sin la ventana efímera de cuatro segundos",
    "jobs.updated_at >= datetime('now','-4 seconds')" not in RUST
    and re.search(r'fn desktop_snapshot[\s\S]{0,3200}LIMIT 300', RUST) is not None
    and re.search(r'fn desktop_snapshot[\s\S]{0,3200}jobs.updated_at', RUST) is not None,
)
check(
    "El progreso directo usa muestras suavizadas y reduce escrituras SQLite",
    "DOWNLOAD_PROGRESS_UPDATE_INTERVAL_MS: u64 = 500" in RUST
    and "struct TransferRateSampler" in RUST
    and "fn stabilize_reported_speed" in RUST
    and re.search(r'fn run_download_worker_inner[\s\S]{0,9000}TransferRateSampler::new', RUST) is not None
    and re.search(r'fn run_curl_download_worker_inner[\s\S]{0,9000}TransferRateSampler::new', RUST) is not None
    and re.search(r'fn run_download_worker_inner[\s\S]{0,9000}Duration::from_millis\(DOWNLOAD_PROGRESS_UPDATE_INTERVAL_MS\)', RUST) is not None
    and re.search(r'fn run_curl_download_worker_inner[\s\S]{0,9000}Duration::from_millis\(DOWNLOAD_PROGRESS_UPDATE_INTERVAL_MS\)', RUST) is not None,
)
check(
    "La URL de descarga directa usa la política pública común",
    re.search(r"fn queue_http_download[\s\S]{0,420}parse_public_http_url", RUST) is not None,
)
check(
    "Los literales IPv6 se validan como direcciones y no como dominios",
    re.search(r"fn url_has_public_http_target[\s\S]{0,700}parsed\.host\(\)[\s\S]{0,420}Host::Ipv6", RUST)
    is not None
    and re.search(r"fn ensure_public_network_resolution[\s\S]{0,900}parsed\.host\(\)[\s\S]{0,520}Host::Ipv6", RUST)
    is not None
    and '"http://[::1]/private"' in RUST
    and '"http://[::ffff:127.0.0.1]/private"' in RUST,
)
check(
    "El analizador multimedia usa la política pública común",
    re.search(r"fn analyze_media_url[\s\S]{0,260}parse_public_http_url", RUST) is not None,
)
check(
    "La inspección previa usa la política pública común",
    re.search(r"fn inspect_download_url[\s\S]{0,700}parse_public_http_url", RUST) is not None,
)
check(
    "El fallback curl limita esquemas y no sigue redirecciones sin validar",
    all(token in RUST for token in ('"--proto"', '"=http,https"', '"--proto-redir"'))
    and '"--location"' not in RUST,
)
check(
    "Los torrents se ejecutan con argumentos tipados y sin shell concatenado",
    re.search(r"fn run_torrent_worker_inner[\s\S]{0,2200}background_command\(aria2_path\)[\s\S]{0,800}\.arg\(&source\)", RUST)
    is not None,
)
check(
    "La cancelación segura contempla procesos torrent",
    re.search(r"fn stop_job_internal[\s\S]{0,4200}active_media_pids", RUST) is not None
    and re.search(r"fn job_partial_storage_paths[\s\S]{0,900}torrent_destination_dir", RUST)
    is not None,
)

check(
    "BitTorrent desactiva descubrimiento local de pares por privacidad",
    '"--bt-enable-lpd=false"' in RUST and '"--bt-enable-lpd=true"' not in RUST,
)
check(
    "Magnet valida hashes y rechaza fuentes auxiliares privadas",
    all(token in RUST for token in ("valid_magnet_exact_topic", "magnet_auxiliary_url_is_safe", "El magnet contiene un tracker local o no seguro")),
)
check(
    "La cancelación programada reutiliza limpieza segura en reposo",
    re.search(r'fn execute_scheduled_action[\s\S]{0,8200}cleanup_managed_paths_when_idle', RUST) is not None,
)
check(
    "La recuperación de archivos directos conserva la política SSRF pública",
    re.search(r'fn verify_direct_availability[\s\S]{0,520}parse_public_http_url[\s\S]{0,420}ensure_public_network_resolution', RUST)
    is not None
    and re.search(r'fn verify_direct_availability[\s\S]{0,1600}url_has_public_network_target', RUST) is not None,
)
check(
    "Los trabajadores validan DNS antes de descargar o invocar yt-dlp",
    re.search(r'fn request_download_response[\s\S]{0,420}ensure_public_network_resolution', RUST) is not None
    and re.search(r'fn run_media_worker_inner[\s\S]{0,3200}ensure_public_network_resolution', RUST) is not None,
)
check(
    "El explorador de páginas limita HTML y rechaza destinos privados",
    re.search(r'fn discover_page_downloads[\s\S]{0,500}ensure_public_network_resolution', RUST) is not None
    and 'MAX_PAGE_BYTES: usize = 2 * 1024 * 1024' in RUST
    and re.search(r'fn discover_page_downloads[\s\S]{0,3600}url_has_public_http_target', RUST) is not None,
)
check(
    "Las miniaturas remotas rechazan HTTP, credenciales y destinos privados",
    re.search(r'fn safe_remote_thumbnail_url[\s\S]{0,520}parsed\.scheme\(\) != "https"[\s\S]{0,320}url_has_public_http_target', RUST)
    is not None,
)

check(
    "La recuperación confirma errores antes de buscar alternativas",
    re.search(r'fn verify_media_availability[\s\S]{0,1000}for attempt in 1\.\.=2', RUST) is not None
    and "diagnosis_allows_alternatives" in RUST,
)


def strip_literals(source: str) -> str:
    output: list[str] = []
    index = 0
    state = "code"
    block_depth = 0
    raw_hashes = 0
    while index < len(source):
        if state == "code":
            if source.startswith("//", index):
                state = "line"
                index += 2
                continue
            if source.startswith("/*", index):
                state = "block"
                block_depth = 1
                index += 2
                continue
            if source[index] == '"':
                state = "string"
                index += 1
                continue
            if source[index] == "'":
                simple_char = index + 2 < len(source) and source[index + 2] == "'"
                escaped_char = (
                    index + 3 < len(source)
                    and source[index + 1] == "\\"
                    and source[index + 3] == "'"
                )
                if simple_char or escaped_char:
                    state = "char"
                    index += 1
                    continue
                output.append(source[index])
                index += 1
                continue
            if source[index] == "r":
                cursor = index + 1
                while cursor < len(source) and source[cursor] == "#":
                    cursor += 1
                if cursor < len(source) and source[cursor] == '"':
                    raw_hashes = cursor - index - 1
                    state = "raw"
                    index = cursor + 1
                    continue
            output.append(source[index])
            index += 1
            continue
        if state == "line":
            if source[index] == "\n":
                output.append("\n")
                state = "code"
            index += 1
            continue
        if state == "block":
            if source.startswith("/*", index):
                block_depth += 1
                index += 2
                continue
            if source.startswith("*/", index):
                block_depth -= 1
                index += 2
                if block_depth == 0:
                    state = "code"
                continue
            index += 1
            continue
        if state in {"string", "char"}:
            if source[index] == "\\":
                index += 2
                continue
            if (state == "string" and source[index] == '"') or (
                state == "char" and source[index] == "'"
            ):
                state = "code"
            index += 1
            continue
        if state == "raw":
            ending = '"' + "#" * raw_hashes
            if source.startswith(ending, index):
                index += len(ending)
                state = "code"
                continue
            index += 1
    return "".join(output)


clean = strip_literals(RUST)


def rust_function_parameter_counts(source: str) -> list[tuple[str, int, int]]:
    """Return (name, parameter_count, line) for ordinary Rust functions.

    This intentionally ignores closures and macros. It balances nested generic,
    tuple and function-pointer delimiters so Clippy's default seven-argument
    threshold can be checked before the source reaches Windows.
    """

    results: list[tuple[str, int, int]] = []
    for match in re.finditer(r"(?m)^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source):
        name = match.group(1)
        cursor = match.end()
        start = cursor
        depth = 1
        while cursor < len(source) and depth:
            character = source[cursor]
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
            cursor += 1
        if depth != 0:
            continue
        signature = source[start : cursor - 1]
        parameters = 0
        token = []
        nested = 0
        for character in signature:
            if character in "(<[{":
                nested += 1
            elif character in ")>]}" and nested > 0:
                nested -= 1
            if character == "," and nested == 0:
                if "".join(token).strip():
                    parameters += 1
                token = []
            else:
                token.append(character)
        if "".join(token).strip():
            parameters += 1
        line = source.count("\n", 0, match.start()) + 1
        results.append((name, parameters, line))
    return results


functions_over_clippy_limit = [
    {"name": name, "parameters": count, "line": line}
    for name, count, line in rust_function_parameter_counts(clean)
    if count > 7
]
check(
    "Ninguna función supera el límite Clippy de siete argumentos",
    not functions_over_clippy_limit,
    functions_over_clippy_limit,
)
check(
    "La recuperación multimedia usa un request tipado y estable para Tauri",
    "struct MediaRecoveryRequest" in RUST
    and '#[serde(rename_all = "camelCase")]' in RUST
    and re.search(r"fn recover_media_source\s*\(\s*request: MediaRecoveryRequest,", RUST) is not None,
)

# Catch unresolved free-function calls inside the Rust test module before the
# source reaches the user's Windows compiler. Method calls (`value.call()`),
# namespaced calls (`Type::call()`) and macros (`assert!()`) are intentionally
# excluded; every remaining lowercase call must have a local `fn` definition.
test_module_index = clean.find("#[cfg(test)]")
test_source = clean[test_module_index:] if test_module_index >= 0 else ""
defined_functions = set(re.findall(r"\bfn\s+([a-z_][A-Za-z0-9_]*)\s*\(", clean))
free_test_calls = set(
    re.findall(r"(?<![.:])\b([a-z_][A-Za-z0-9_]*)\s*\(", test_source)
)
rust_keywords = {"if", "while", "for", "match", "loop", "return", "let", "fn", "unsafe", "async", "move", "cfg"}
unresolved_test_calls = sorted(free_test_calls - defined_functions - rust_keywords)
check(
    "Las pruebas Rust no llaman funciones libres sin definición",
    test_module_index >= 0 and not unresolved_test_calls,
    unresolved_test_calls,
)

for opening, closing in (("(", ")"), ("[", "]"), ("{", "}")):
    depth = 0
    minimum = 0
    for character in clean:
        if character == opening:
            depth += 1
        elif character == closing:
            depth -= 1
            minimum = min(minimum, depth)
    check(
        f"Delimitadores {opening}{closing}",
        depth == 0 and minimum >= 0,
        {"depth": depth, "minimum": minimum},
    )


COMMAND_PATTERNS = (
    ("cargo fmt", re.compile(r'Invoke-RustGate\s+"cargo-fmt"\s+@\("fmt",\s*"--all",\s*"--",\s*"--check"\)')),
    ("cargo check", re.compile(r'Invoke-RustGate\s+"cargo-check"\s+@\("check",\s*"--locked",\s*"--all-targets"\)')),
    ("cargo clippy", re.compile(r'Invoke-RustGate\s+"cargo-clippy"\s+@\("clippy",\s*"--locked",\s*"--all-targets",\s*"--",\s*"-D",\s*"warnings"\)')),
    ("cargo test", re.compile(r'Invoke-RustGate\s+"cargo-test"\s+@\("test",\s*"--locked",\s*"--lib"\)')),
)


def command_order(source: str) -> dict[str, int]:
    return {label: (match.start() if (match := pattern.search(source)) else -1) for label, pattern in COMMAND_PATTERNS}


rust_order = command_order(RUST_GATE)
check("Gate Rust unificado completo", all(value >= 0 for value in rust_order.values()), rust_order)
sequence = [rust_order[label] for label, _ in COMMAND_PATTERNS]
check(
    "Orden fmt/check/clippy/test correcto en gate unificado",
    all(value >= 0 for value in sequence) and sequence == sorted(sequence),
    rust_order,
)
check(
    "El gate Rust intenta todas las etapas y genera resumen",
    "All Rust stages were attempted" in RUST_GATE
    and "rust-gate-summary.json" in RUST_GATE
    and "Where-Object { -not $_.passed }" in RUST_GATE
    and "$Results.ToArray()" in RUST_GATE
    and "gates = @($Results)" not in RUST_GATE,
)

for pipeline_name, source in (("build", BUILD), ("ci", CI)):
    gate_index = source.find("rust-gate-windows.ps1")
    prepare_index = source.find("prepare:windows-binaries")
    check(f"Gate Rust unificado invocado en {pipeline_name}", gate_index >= 0, {"gate": gate_index})
    check(
        f"Rust se valida antes de binarios en {pipeline_name}",
        gate_index >= 0 and (prepare_index < 0 or gate_index < prepare_index),
        {"gate": gate_index, "prepare binaries": prepare_index},
    )

cargo_available = shutil.which("cargo") is not None
source_files, source_hash = source_fingerprint([
    Path(__file__),
    ROOT / "scripts/validation/phase16_hashing.py",
    ROOT / "src-tauri/src/lib.rs",
    ROOT / "scripts/build-windows-beta.ps1",
    ROOT / "scripts/ci-windows-beta.ps1",
    ROOT / "scripts/rust-gate-windows.ps1",
])
report = {
    "sourceFiles": source_files,
    "sourceHash": source_hash,
    "gate": "phase16-rust-static-gate",
    "passed": all(item["pass"] for item in checks),
    "nativeCargoExecuted": False,
    "cargoAvailable": cargo_available,
    "nativeCargoLimitation": (
        "Cargo no está instalado en este entorno. Este informe es estructural; el paquete final seguirá "
        "bloqueado hasta superar fmt, check, test y clippy en Windows."
    ),
    "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "checks": checks,
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(
    "OK: gate estático Rust Phase16 aprobado; Cargo nativo pendiente en Windows."
    if report["passed"]
    else "FAIL: gate estático Rust Phase16 con regresiones."
)
raise SystemExit(0 if report["passed"] else 1)
