"""Read-only exact payload/hash verification for the frozen source candidate."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()

def excluded(path):
    return '__pycache__' in path.parts or path.suffix == '.pyc' or path.name in {'SHA256SUMS.json', 'INDEX.json'} and path.parent == ROOT

index = json.loads((ROOT / 'INDEX.json').read_text())
assert sha(ROOT / 'SHA256SUMS.json') == index['sha256_manifest'], 'Manifest seal mismatch'
expected = json.loads((ROOT / 'SHA256SUMS.json').read_text())
actual_paths = {str(p.relative_to(ROOT)): p for p in ROOT.rglob('*') if p.is_file() and not excluded(p)}
assert actual_paths.keys() == expected.keys(), {'missing': sorted(expected.keys() - actual_paths.keys()), 'extra': sorted(actual_paths.keys() - expected.keys())}
for relative, digest in expected.items():
    path = actual_paths[relative]
    assert not path.is_symlink() and path.resolve().is_relative_to(ROOT), relative
    assert sha(path) == digest, relative
assert len(expected) == index['payload_files']
print(json.dumps({'passed': True, 'payload_files': len(expected), 'sha256_manifest': index['sha256_manifest'], 'scope': 'Static source packet integrity only; no native/game acceptance.'}))
