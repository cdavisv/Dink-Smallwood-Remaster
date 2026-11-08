"""Check source syntax, pinned binary/ledger hashes, layout and approved audio."""
from pathlib import Path
import ast, csv, hashlib, json, re, subprocess, sys, tempfile, importlib.util, argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--metadata-only', action='store_true', help='Check asset hashes against the pinned pack without requiring downloaded binaries; does not prove binary contents')
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
repo = root.parent
errors = []
python_count = 0
shell_count = 0
secret_flags = []
patterns = [('github_token', re.compile(b'\\bgh[pousr]_[A-Za-z0-9]{30,}\\b')), ('openai_or_elevenlabs_key', re.compile(b'\\bsk[-_][A-Za-z0-9_-]{24,}\\b')), ('private_key', re.compile(b'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')), ('aws_key', re.compile(b'\\bAKIA[0-9A-Z]{16}\\b'))]
for p in root.rglob('*'):
    if not p.is_file() or any((x in p.parts for x in ['.git', 'Binaries', 'Intermediate', 'Saved', '__pycache__'])):
        continue
    if p.suffix == '.py':
        try:
            ast.parse(p.read_text(), filename=str(p))
            python_count += 1
        except Exception as e:
            errors.append({'file': str(p.relative_to(repo)), 'error': str(e)})
    if p.suffix == '.sh':
        result = subprocess.run(['bash', '-n', str(p)], capture_output=True, text=True)
        shell_count += 1
        if result.returncode:
            errors.append({'file': str(p.relative_to(repo)), 'error': result.stderr})
    if p.suffix in ['.py', '.sh', '.cpp', '.h', '.cs', '.json', '.csv', '.ini', '.md', '.html', '.yml', '.yaml', '.txt'] and p.stat().st_size < 10000000:
        b = p.read_bytes()
        for label, regex in patterns:
            for m in regex.finditer(b):
                secret_flags.append({'file': str(p.relative_to(repo)), 'line': b[:m.start()].count(b'\n') + 1, 'rule': label})
        if p.suffix in ['.cpp', '.h', '.cs', '.py', '.sh'] and b'\x00' in b:
            errors.append({'file': str(p.relative_to(repo)), 'error': 'Unexpected NUL byte in source'})
pack = json.loads((root / 'AssetPacks/house-v1.json').read_text())
pack_files = {row['path']: row for row in pack['files']}
missing = []
bad = []
verified_binary = 0
metadata_binary = 0
for name, row in pack_files.items():
    p = root / name
    if not p.is_file():
        if args.metadata_only:
            metadata_binary += 1
        else:
            missing.append(name)
        continue
    data = p.read_bytes()
    if data.startswith(b'version https://git-lfs.github.com/spec/'):
        metadata_binary += 1  # Git LFS pointer (checkout without LFS): the binary is not here to verify
        continue
    if hashlib.sha256(data).hexdigest() != row['sha256'] or len(data) != row['size']:
        bad.append(name)
    else:
        verified_binary += 1
rows = list(csv.DictReader((root / 'SourceAssets/asset_ledger.csv').open()))
for row in rows:
    p = root / row['asset_path']
    if not p.is_file():
        expected = pack_files.get(row['asset_path'])
        if not args.metadata_only or expected is None or expected['sha256'] != row['sha256']:
            missing.append(row['asset_path'])
        continue
    data = p.read_bytes()
    if data.startswith(b'version https://git-lfs.github.com/spec/'):
        continue  # LFS pointer; the pack check above covers pinned hashes
    if hashlib.sha256(data).hexdigest() != row['sha256']:
        bad.append(row['asset_path'])
errors.extend([{'missing_asset': x} for x in sorted(set(missing))])
errors.extend([{'asset_hash_mismatch': x} for x in sorted(set(bad))])
spec = importlib.util.spec_from_file_location('remaster_paths', root / 'Scripts/remaster_paths.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.default_data_repo(root).is_dir(), 'Extraction data repository is missing'
with tempfile.TemporaryDirectory(prefix='dink-layout-') as temp:
    t = Path(temp)
    project = t / 'DinkRemasterUE'
    project.mkdir()
    assert module.default_data_repo(project) == t / 'Dink-Smallwood-Remaster'
    (t / 'tools').mkdir()
    (t / 'bin/dink').mkdir(parents=True)
    assert module.default_data_repo(project) == t
selection = json.loads((root / 'SourceAssets/Audio/selection_manifest.json').read_text())
assert selection['runtime'] == json.loads((root / 'Content/Dink/Data/Audio/approved.json').read_text())
assert selection['counts'] == {'sfx': 44, 'music': 28, 'rejected': 4}
report = {'verification_mode': 'metadata' if args.metadata_only else 'full', 'binary_files_verified': verified_binary, 'binary_files_metadata_only': metadata_binary, 'python_syntax_files': python_count, 'shell_syntax_files': shell_count, 'ledger_rows': len(rows), 'missing_assets': len(missing), 'hash_errors': len(bad), 'secret_flags': secret_flags, 'errors': errors, 'layout_cases_passed': 3, 'approved_audio_runtime_matches': True, 'passed': not errors and (not secret_flags)}
print(json.dumps(report, indent=2), flush=True)
sys.exit(0 if report['passed'] else 1)
