from pathlib import Path
import json, re, time

ROOT = Path(__file__).resolve().parents[2]
RUST = (ROOT / 'src-tauri' / 'src' / 'lib.rs').read_text(encoding='utf-8')
CI = (ROOT / 'scripts' / 'ci-windows-beta.ps1').read_text(encoding='utf-8')
REPORT = ROOT / 'docs' / 'tests' / 'phase15-rust-static-gate.json'

checks = []
def check(name, condition, detail=None):
    checks.append({'name': name, 'pass': bool(condition), 'detail': detail})

required = [
    'struct QueueSnapshot',
    'run_curl_download_worker_inner',
    'CACATOOLS_PROGRESS:%(progress)j',
    'ensure_windows_compatible_mp4',
    'validate_downloaded_media',
    'speed_bps',
    'eta_seconds',
    '.cacatools-work',
    '--concurrent-fragments',
    '--js-runtimes',
    'String::from_utf8_lossy',
]
for token in required:
    check(f'Requisito Rust: {token}', token in RUST)

forbidden = {
    'ClientBuilder.read_timeout incompatible': '.read_timeout(',
    'drop de tauri::State': 'drop(state)',
    'sort_by antiguo de candidatos': 'candidates.sort_by(|left, right| right.0.cmp(&left.0))',
    'let-and-return conocido': 'let ids = rows.filter_map(Result::ok).collect::<Vec<_>>();\n        ids',
}
for name, token in forbidden.items():
    check(f'Ausente: {name}', token not in RUST)

# Conservative delimiter scan after removing comments and literals.
def strip_literals(source: str) -> str:
    output = []
    index = 0
    state = 'code'
    block_depth = 0
    raw_hashes = 0
    while index < len(source):
        if state == 'code':
            if source.startswith('//', index):
                state = 'line'; index += 2; continue
            if source.startswith('/*', index):
                state = 'block'; block_depth = 1; index += 2; continue
            if source[index] == '"':
                state = 'string'; index += 1; continue
            if source[index] == "'":
                simple_char = index + 2 < len(source) and source[index + 2] == "'"
                escaped_char = index + 3 < len(source) and source[index + 1] == '\\' and source[index + 3] == "'"
                if simple_char or escaped_char:
                    state = 'char'; index += 1; continue
                output.append(source[index]); index += 1; continue
            if source[index] == 'r':
                cursor = index + 1
                while cursor < len(source) and source[cursor] == '#':
                    cursor += 1
                if cursor < len(source) and source[cursor] == '"':
                    raw_hashes = cursor - index - 1
                    state = 'raw'; index = cursor + 1; continue
            output.append(source[index]); index += 1; continue
        if state == 'line':
            if source[index] == '\n':
                output.append('\n'); state = 'code'
            index += 1; continue
        if state == 'block':
            if source.startswith('/*', index):
                block_depth += 1; index += 2; continue
            if source.startswith('*/', index):
                block_depth -= 1; index += 2
                if block_depth == 0: state = 'code'
                continue
            index += 1; continue
        if state in ('string', 'char'):
            if source[index] == '\\':
                index += 2; continue
            if (state == 'string' and source[index] == '"') or (state == 'char' and source[index] == "'"):
                state = 'code'
            index += 1; continue
        if state == 'raw':
            ending = '"' + ('#' * raw_hashes)
            if source.startswith(ending, index):
                index += len(ending); state = 'code'; continue
            index += 1
    return ''.join(output)

clean = strip_literals(RUST)
for opening, closing in [('(', ')'), ('[', ']'), ('{', '}')]:
    depth = 0
    minimum = 0
    for char in clean:
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            minimum = min(minimum, depth)
    check(f'Delimitadores {opening}{closing}', depth == 0 and minimum >= 0, {'depth': depth, 'minimum': minimum})

order = {
    'cargo fmt': CI.find('@("fmt", "--all")'),
    'cargo check': CI.find('@("check", "--all-targets")'),
    'cargo test': CI.find('@("test", "--lib")'),
    'cargo clippy': CI.find('@("clippy", "--all-targets"'),
    'prepare binaries': CI.find('prepare:windows-binaries'),
}
check('Preflight nativo completo presente', all(value >= 0 for value in order.values()), order)
check(
    'Cargo se ejecuta antes de descargar binarios',
    all(order[name] < order['prepare binaries'] for name in ('cargo fmt', 'cargo check', 'cargo test', 'cargo clippy')),
    order,
)

report = {
    'passed': all(item['pass'] for item in checks),
    'nativeCargoExecuted': False,
    'nativeCargoLimitation': 'Este entorno no incluye rustc/cargo. El pipeline Windows ejecuta fmt, check, test y clippy antes del empaquetado.',
    'generatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'checks': checks,
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report['passed'] else 1)
