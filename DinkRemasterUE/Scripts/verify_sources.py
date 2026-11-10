"""Check source syntax, pinned binary/ledger hashes, layout and approved audio."""
from pathlib import Path
import ast, csv, hashlib, json, re, subprocess, sys, tempfile, importlib.util, argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--metadata-only', action='store_true', help='Check staged Git LFS pointer hashes without requiring downloaded binaries; does not prove binary contents')
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
from lfs_inventory import inventory, pointer_metadata
pack_files = inventory(root)
missing = []
bad = []
verified_binary = 0
metadata_binary = 0
for name, row in pack_files.items():
    p = root / name
    if not p.is_file():
        missing.append(name)
        continue
    data = p.read_bytes()
    if args.metadata_only and pointer_metadata(data) == row:
        metadata_binary += 1
        continue
    if hashlib.sha256(data).hexdigest() != row['sha256'] or len(data) != row['size']:
        bad.append(name)
    else:
        verified_binary += 1
rows = list(csv.DictReader((root / 'SourceAssets/asset_ledger.csv').open()))
from hero_source_history import AUTHORITY, validate_history
history_proof = {'indices': set(), 'historical_rows_binary_verified': 0,
                 'historical_rows_metadata_only': 0}
if any(row['asset_path'] in {entry['asset_path'] for entry in AUTHORITY} for row in rows):
    try:
        history_proof = validate_history(root, rows, json.loads(
            (root / 'Docs/Verification/RoofNativeCurrent/AcceptedHeroSourceHistory.json').read_text()),
            metadata_only=args.metadata_only, inventory=pack_files)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        errors.append({'accepted_hero_history_error': str(exc)})
for row_index, row in enumerate(rows):
    if row_index in history_proof['indices']:
        continue  # Exact archived/current binary or pointer proof already checked.
    p = root / row['asset_path']
    if not p.is_file():
        expected = pack_files.get(row['asset_path'])
        if not args.metadata_only or expected is None or expected['sha256'] != row['sha256']:
            missing.append(row['asset_path'])
        continue
    data = p.read_bytes()
    pointer = pointer_metadata(data)
    expected = pack_files.get(row['asset_path'])
    if (args.metadata_only and pointer is not None and pointer == expected
            and pointer['sha256'] == row['sha256']):
        continue
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
report = {'verification_mode': 'metadata' if args.metadata_only else 'full', 'binary_files_verified': verified_binary, 'binary_files_metadata_only': metadata_binary, 'python_syntax_files': python_count, 'shell_syntax_files': shell_count, 'ledger_rows': len(rows), 'historical_rows_binary_verified': history_proof['historical_rows_binary_verified'], 'historical_rows_metadata_only': history_proof['historical_rows_metadata_only'], 'missing_assets': len(missing), 'hash_errors': len(bad), 'secret_flags': secret_flags, 'errors': errors, 'layout_cases_passed': 3, 'approved_audio_runtime_matches': True, 'passed': not errors and (not secret_flags)}
print(json.dumps(report, indent=2), flush=True)
sys.exit(0 if report['passed'] else 1)
