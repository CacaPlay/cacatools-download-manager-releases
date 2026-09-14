#!/usr/bin/env python3
"""Conservative Windows build-script gate.

This does not replace the PowerShell parser on Windows. It catches damaged
quotes/braces, incomplete here-strings, missing native gate commands, stale
paths, and accidental regressions in the one-click build chain before the
source is handed to Windows.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from phase16_hashing import source_fingerprint

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs/tests/phase16-windows-scripts-static-gate.json"

PS_FILES = [
    "scripts/bootstrap-windows.ps1",
    "scripts/check-windows-toolchain.ps1",
    "scripts/native-check-windows.ps1",
    "scripts/rust-gate-windows.ps1",
    "scripts/prepare-windows-binaries.ps1",
    "scripts/build-windows-beta.ps1",
    "scripts/ci-windows-beta.ps1",
    "scripts/first-native-build.ps1",
    "scripts/final-windows-build.ps1",
    "scripts/smoke-test-installed-beta.ps1",
    "scripts/collect-windows-diagnostics.ps1",
]

CMD_FILES = [
    "INSTALAR_REQUISITOS_WINDOWS.cmd",
    "COMPILAR_CACATOOLS_WINDOWS.cmd",
    "COMPILAR_BETA_WINDOWS.cmd",
    "VALIDAR_CACATOOLS_WINDOWS.cmd",
]


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def strip_powershell(source: str) -> tuple[str, list[str]]:
    """Strip comments and literals while preserving line endings/delimiters."""
    output: list[str] = []
    errors: list[str] = []
    i = 0
    line = 1
    state = "code"
    quote = ""
    here_end = ""

    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""

        if state == "code":
            if ch == "#":
                state = "comment"
                i += 1
                continue
            if ch in ('"', "'"):
                quote = ch
                state = "double" if ch == '"' else "single"
                i += 1
                continue
            if ch == "@" and nxt in ('"', "'"):
                # PowerShell requires no non-whitespace content after a
                # here-string opener. Be conservative but accept the opener.
                quote = nxt
                here_end = f"{nxt}@"
                state = "here"
                i += 2
                continue
            output.append(ch)
            if ch == "\n":
                line += 1
            i += 1
            continue

        if state == "comment":
            if ch == "\n":
                output.append("\n")
                line += 1
                state = "code"
            i += 1
            continue

        if state in ("double", "single"):
            if ch == "`":
                # Backtick escapes the following character in both forms for
                # the purposes of this conservative scanner.
                i += 2
                continue
            if ch == quote:
                state = "code"
                i += 1
                continue
            if ch == "\n":
                line += 1
                if state == "single":
                    errors.append(f"single-quoted string crosses line {line}")
            i += 1
            continue

        if state == "here":
            if ch == "\n":
                line += 1
                i += 1
                # Closing marker must begin a physical line (allow spaces).
                start = i
                while start < len(source) and source[start] in " \t":
                    start += 1
                if source.startswith(here_end, start):
                    i = start + len(here_end)
                    state = "code"
                continue
            i += 1
            continue

    if state in ("double", "single"):
        errors.append("unterminated quoted string")
    elif state == "here":
        errors.append("unterminated here-string")
    return "".join(output), errors


def delimiter_errors(source: str) -> list[str]:
    stripped, errors = strip_powershell(source)
    stack: list[tuple[str, int]] = []
    pairs = {")": "(", "]": "[", "}": "{"}
    openings = set(pairs.values())
    line = 1
    for ch in stripped:
        if ch == "\n":
            line += 1
        elif ch in openings:
            stack.append((ch, line))
        elif ch in pairs:
            if not stack or stack[-1][0] != pairs[ch]:
                errors.append(f"unexpected {ch} at line {line}")
                continue
            stack.pop()
    errors.extend(f"unclosed {ch} from line {ln}" for ch, ln in stack)
    return errors


def require_tokens(path: str, source: str, tokens: list[str]) -> Check:
    missing = [token for token in tokens if token not in source]
    return Check(
        f"tokens:{path}",
        not missing,
        "all required tokens present" if not missing else f"missing: {', '.join(missing)}",
    )


def require_order(path: str, source: str, tokens: list[str]) -> Check:
    positions = [source.find(token) for token in tokens]
    ok = all(pos >= 0 for pos in positions) and positions == sorted(positions)
    return Check(
        f"order:{path}",
        ok,
        " -> ".join(tokens) if ok else f"invalid positions {dict(zip(tokens, positions))}",
    )


def main() -> int:
    checks: list[Check] = []
    for relative in PS_FILES:
        path = ROOT / relative
        if not path.exists():
            checks.append(Check(f"exists:{relative}", False, "file is missing"))
            continue
        source = path.read_text(encoding="utf-8-sig")
        errors = delimiter_errors(source)
        checks.append(Check(f"syntax-shape:{relative}", not errors, "; ".join(errors) or "balanced"))
        checks.append(Check(f"strict-mode:{relative}", "Set-StrictMode" in source, "strict mode present"))
        expected_error_mode = "Continue" if relative.endswith("collect-windows-diagnostics.ps1") else "Stop"
        marker = f'$ErrorActionPreference = "{expected_error_mode}"'
        checks.append(Check(f"error-mode:{relative}", marker in source, f"{expected_error_mode} mode present"))

    for relative in CMD_FILES:
        path = ROOT / relative
        raw = path.read_bytes() if path.exists() else b""
        source = raw.decode("utf-8-sig") if raw else ""
        checks.append(Check(f"cmd:{relative}", bool(source) and "exit /b %" in source, "propagates exit code"))
        checks.append(Check(
            f"cmd-no-utf8-bom:{relative}",
            not raw.startswith(b"\xef\xbb\xbf"),
            "first command is visible to cmd.exe" if not raw.startswith(b"\xef\xbb\xbf") else "UTF-8 BOM corrupts the first command",
        ))

    manifest_source = (ROOT / "scripts/generate-source-manifest.mjs").read_text(encoding="utf-8")
    checks.append(require_tokens("generate-source-manifest.mjs", manifest_source, [
        "'src-tauri/gen/'",
        "'src-tauri/Cargo.lock'",
        "'package-lock.json'",
        "'src-tauri/resources/bin/'",
        "'src-tauri/resources/licenses/ARIA2-COPYING.txt'",
        "'src-tauri/resources/licenses/YT-DLP-THIRD-PARTY-LICENSES.txt'",
    ]))
    checks.append(Check(
        "manifest-excludes-tauri-generated-schemas",
        "'src-tauri/gen/'" in manifest_source,
        "Tauri-generated schemas cannot invalidate a resumed Windows build",
    ))

    invalid_interpolations: list[str] = []
    scoped_names = {"env", "global", "script", "local", "private", "using"}
    variable_colon = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*):")
    for relative in PS_FILES:
        source = (ROOT / relative).read_text(encoding="utf-8-sig")
        for line_number, line in enumerate(source.splitlines(), start=1):
            for match in variable_colon.finditer(line):
                if match.group(1).lower() not in scoped_names:
                    invalid_interpolations.append(f"{relative}:{line_number}:${match.group(1)}:")
    checks.append(Check(
        "powershell-no-ambiguous-variable-colons",
        not invalid_interpolations,
        "clean" if not invalid_interpolations else ", ".join(invalid_interpolations),
    ))

    rust_gate = (ROOT / "scripts/rust-gate-windows.ps1").read_text(encoding="utf-8-sig")
    checks.append(require_tokens("rust-gate-windows.ps1", rust_gate, [
        '@("fmt", "--all", "--", "--check")',
        '@("check", "--locked", "--all-targets")',
        '@("clippy", "--locked", "--all-targets", "--", "-D", "warnings")',
        '@("test", "--locked", "--lib")',
        'rust-gate-summary.json',
        'All Rust stages were attempted',
        '$Results.ToArray()',
        'throw "The unified Rust gate failed.',
    ]))
    checks.append(Check(
        "rust-gate-materializes-generic-list",
        "gates = @($Results)" not in rust_gate and "gates = $GateArray" in rust_gate,
        "Generic.List[object] is converted to object[] before JSON summary creation",
    ))
    checks.append(require_order("rust-gate-windows.ps1", rust_gate, [
        '@("fmt", "--all", "--", "--check")',
        '@("check", "--locked", "--all-targets")',
        '@("clippy", "--locked", "--all-targets", "--", "-D", "warnings")',
        '@("test", "--locked", "--lib")',
    ]))

    build = (ROOT / "scripts/build-windows-beta.ps1").read_text(encoding="utf-8-sig")
    checks.append(require_tokens("build-windows-beta.ps1", build, [
        'npm" @("run", "check:manifest")',
        'npm" @("run", "check")',
        'npm" @("run", "build:web")',
        'rust-gate-windows.ps1',
        '$SkipRustGate',
        'prepare:windows-binaries',
        'verify:binaries',
        'npx" @("--no-install", "tauri", "build"',
        'smoke-test-installed-beta.ps1',
        'Get-FileHash',
        '$SourceManifestHash',
        'sourceManifestSha256',
        '$PreferredInstaller',
        "Extension -eq '.msi'",
    ]))
    checks.append(require_order("build-windows-beta.ps1", build, [
        'npm" @("run", "check:manifest")',
        'npm" @("run", "check")',
        'npm" @("run", "build:web")',
        'rust-gate-windows.ps1',
        'prepare:windows-binaries',
        'npx" @("--no-install", "tauri", "build"',
        'smoke-test-installed-beta.ps1',
    ]))

    smoke = (ROOT / "scripts/smoke-test-installed-beta.ps1").read_text(encoding="utf-8-sig")
    checks.append(require_tokens("smoke-test-installed-beta.ps1", smoke, [
        'CACATOOLS_DATA_DIR',
        'CACATOOLS_DOWNLOADS_DIR',
        'cacatools.sqlite3',
        '$SmokeDataDir',
        '$SmokeDownloadsDir',
        'Remove-Item Env:CACATOOLS_DATA_DIR',
        'Remove-Item Env:CACATOOLS_DOWNLOADS_DIR',
        'RedirectStandardError',
        'RUST_BACKTRACE',
        '$CrashText',
    ]))
    checks.append(Check(
        "smoke-test-uses-explicit-isolated-paths",
        '$env:CACATOOLS_DATA_DIR = $SmokeDataDir' in smoke
        and '$env:CACATOOLS_DOWNLOADS_DIR = $SmokeDownloadsDir' in smoke
        and 'Get-ChildItem $SmokeRoot -Recurse -File' not in smoke,
        "startup test verifies the isolated database and downloads directory instead of Windows known-folder redirection",
    ))

    ci = (ROOT / "scripts/ci-windows-beta.ps1").read_text(encoding="utf-8-sig")
    checks.append(require_order("ci-windows-beta.ps1", ci, [
        'npm" @("run", "check:manifest")',
        'npm" @("run", "check")',
        'npm" @("run", "build:web")',
        'rust-gate-windows.ps1',
        'prepare:windows-binaries',
        'build-windows-beta.ps1',
    ]))
    checks.append(require_tokens("ci-windows-beta.ps1", ci, [
        '-SkipRustGate',
        'output\\rust-gate',
    ]))

    native_check = (ROOT / "scripts/native-check-windows.ps1").read_text(encoding="utf-8-sig")
    checks.append(require_order("native-check-windows.ps1", native_check, [
        'npm" @("run", "check:manifest")',
        'npm" @("run", "check")',
        'npm" @("run", "build:web")',
        'rust-gate-windows.ps1',
    ]))

    first_build = (ROOT / "scripts/first-native-build.ps1").read_text(encoding="utf-8-sig")
    checks.append(require_tokens("first-native-build.ps1", first_build, [
        '$LASTEXITCODE -ne 0',
        'build-report.json',
    ]))

    bootstrap = (ROOT / "scripts/bootstrap-windows.ps1").read_text(encoding="utf-8-sig")
    checks.append(require_tokens("bootstrap-windows.ps1", bootstrap, [
        'OpenJS.NodeJS.LTS',
        'Rustlang.Rustup',
        'Microsoft.VisualStudio.2022.BuildTools',
        'Microsoft.VisualStudio.Workload.VCTools',
        'x86_64-pc-windows-msvc',
        'rustfmt clippy',
        'check-windows-toolchain.ps1',
        'environment-report.json',
    ]))

    toolchain = (ROOT / "scripts/check-windows-toolchain.ps1").read_text(encoding="utf-8-sig")
    checks.append(require_tokens("check-windows-toolchain.ps1", toolchain, [
        'Node.js 20 or newer',
        'process.arch',
        'x86_64-pc-windows-msvc',
        'cargo-clippy',
        r'Hostx64\\x64\\cl\.exe',
        'Windows Kits\\10',
        'PowerShell 5.1 or newer',
        'Move the source to C:\\CacaTools',
        'At least 12 GiB of free disk space',
        'temporary drive needs at least 4 GiB free',
        'LongPathsEnabled',
        'OneDrive|Dropbox|Google Drive',
    ]))

    prepare = (ROOT / "scripts/prepare-windows-binaries.ps1").read_text(encoding="utf-8-sig")
    checks.append(require_tokens("prepare-windows-binaries.ps1", prepare, [
        'Ensure-VerifiedCache',
        'Get-GitHubAssetSha256',
        'official GitHub asset digest',
        'officialAssetSha256',
        '.partial',
        'Get-FileHash',
        'SHA2-256SUMS',
        '$YtDlpReleaseApi',
        'X-GitHub-Api-Version',
        'YtDlpCommit',
        'YtDlpLicensesSha256',
        'raw.githubusercontent.com/yt-dlp/yt-dlp',
        'thirdPartyLicensesSourceCommit',
        'thirdPartyLicensesPinnedSha256',
        'Aria2Sha256',
        'FfmpegSha256',
        'runtime-manifest.json',
        'YT-DLP-THIRD-PARTY-LICENSES.txt',
        'FFMPEG-LICENSE.txt',
    ]))
    checks.append(Check(
        "no-unverified-runtime-downloads",
        prepare.count("Invoke-DownloadFile") >= 4 and prepare.count("Ensure-VerifiedCache") >= 4,
        "all large runtime artifacts pass through the verified cache",
    ))
    checks.append(Check(
        "yt-dlp-license-uses-immutable-source-commit",
        'AssetName "THIRD_PARTY_LICENSES.txt"' not in prepare
        and '$ReleaseBase/THIRD_PARTY_LICENSES.txt' not in prepare
        and 'raw.githubusercontent.com/yt-dlp/yt-dlp/$YtDlpCommit/THIRD_PARTY_LICENSES.txt' in prepare
        and 'thirdPartyLicensesSourceCommit' in prepare
        and 'thirdPartyLicensesPinnedSha256' in prepare
        and r'\sTHIRD_PARTY_LICENSES\.txt$' not in prepare,
        "license file is pinned to the immutable release source commit and SHA-256",
    ))
    checks.append(Check(
        "github-release-metadata-is-cached",
        '$script:GitHubReleaseCache.ContainsKey($ReleaseApi)' in prepare,
        "one release API request is reused for multiple assets",
    ))

    final = (ROOT / "scripts/final-windows-build.ps1").read_text(encoding="utf-8-sig")
    checks.append(require_order("final-windows-build.ps1", final, [
        'bootstrap-windows.ps1',
        'first-native-build.ps1',
        'Copy-Item',
        'BUILD_COMPLETED.txt',
    ]))
    checks.append(require_tokens("final-windows-build.ps1", final, [
        'final-build-transcript.txt',
        'lock-files.json',
        'source-locks',
        'collect-windows-diagnostics.ps1',
        'exit $ExitCode',
        '$PreferredInstaller',
        "Extension -eq '.msi'",
        '$CandidateReport.sourceManifestSha256',
        '$CurrentSourceManifestHash',
    ]))

    stale = []
    for relative in PS_FILES + CMD_FILES:
        text = (ROOT / relative).read_text(encoding="utf-8-sig")
        if "PHASE15" in text or "0.15.0" in text:
            stale.append(relative)
    checks.append(Check("no-phase15-build-identifiers", not stale, "clean" if not stale else ", ".join(stale)))

    # Redundant separators in human-facing Windows paths are usually accepted,
    # but often reveal accidental escaping from generated scripts.
    redundant_paths = []
    for relative in ["scripts/bootstrap-windows.ps1", "scripts/final-windows-build.ps1"]:
        text = (ROOT / relative).read_text(encoding="utf-8-sig")
        for match in re.finditer(r'"[^"\n]*\\\\[^"\n]*"', text):
            redundant_paths.append(f"{relative}:{match.group(0)}")
    checks.append(Check("no-redundant-path-separators", not redundant_paths, "clean" if not redundant_paths else "; ".join(redundant_paths)))

    passed = all(check.passed for check in checks)
    source_files, source_hash = source_fingerprint([
        Path(__file__),
        ROOT / "scripts/validation/phase16_hashing.py",
        ROOT / ".github/workflows/windows-beta.yml",
        *(ROOT / relative for relative in PS_FILES + CMD_FILES),
    ])
    payload = {
        "sourceFiles": source_files,
        "sourceHash": source_hash,
        "name": "Phase16 Windows scripts static gate",
        "passed": passed,
        "checks": [asdict(check) for check in checks],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failed = [check for check in checks if not check.passed]
    if failed:
        for check in failed:
            print(f"FAIL {check.name}: {check.detail}")
        return 1
    print(f"OK: {len(checks)} comprobaciones estáticas de scripts Windows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
