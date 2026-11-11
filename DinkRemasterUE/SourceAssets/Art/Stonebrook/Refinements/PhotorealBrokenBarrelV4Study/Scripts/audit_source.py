"""Portable read-only source inventory audit; accepts only exact Git LFS oid/size metadata."""
from pathlib import Path
import json,hashlib,re
Q=Path(__file__).resolve().parents[1]
checks=json.loads((Q/'SHA256SUMS.json').read_bytes())
actual={str(p.relative_to(Q))for p in Q.rglob('*')if p.is_file()}
assert actual==set(checks)|{'SHA256SUMS.json'}
for n,fact in checks.items():
 p=Q/n;assert not p.is_symlink();data=p.read_bytes();digest=hashlib.sha256(data).hexdigest()
 if data.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
  assert data==('version https://git-lfs.github.com/spec/v1\noid sha256:'+fact['sha256']+'\nsize '+str(fact['bytes'])+'\n').encode(),n
 else:assert digest==fact['sha256']and len(data)==fact['bytes'],n
m=json.loads((Q/'manifest.json').read_bytes());assert not m['runtime_activated']and not m['native_appearance_accepted']and not m['Blender_roundtrip_normal_gate_passed']
assert checks[m['source']]['sha256']==m['source_sha256']
assert json.loads((Q/'Evidence/RELOCATED_REOPEN.json').read_bytes())['geometry_fingerprints_exact']
print('PASS',len(checks)+1,'source files; no runtime activation; exact LFS metadata accepted')
