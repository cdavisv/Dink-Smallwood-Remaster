"""List original duck placements (candidate origins) from the dinkex extraction (read-only).

    python3 Tools/duck_origins.py

Writes duck_origins.json.  These are NOT written into duck_manifest.json `origins`:
attaching the model to live actors is the integrating agent's decision.
"""
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import duck_common as D  # noqa: E402

DUCK_SEQS = {21, 23, 24, 26, 27, 29, 111, 113, 117, 119, 121, 123, 127, 129}
out_dir = D.pipeline_dir().parent / 'dinkex' / 'out' / 'screens'
rows = []
for f in sorted(glob.glob(str(out_dir / '*.json'))):
    d = json.loads(Path(f).read_text())
    for p in d.get('placements', []):
        seq = p.get('seq') or (p.get('pic') or {}).get('seq')
        if seq in DUCK_SEQS:
            rows.append({'origin': p.get('id'), 'seq': seq, 'brain': p.get('brain'), 'script': p.get('script'),
                         'vision': p.get('vision')})
quackers = [r['origin'] for r in rows if r['script'] == 's1-oldd']
(D.ROOT / 'duck_origins.json').write_text(json.dumps({
    'source': 'tools/dinkex/out/screens (original dink.dat placements with duck sequences 21-29/111-129)',
    'count': len(rows), 'quackers_s1_oldd': quackers, 'placements': rows}, indent=2) + '\n')
print('duck placements', len(rows), 'Quackers (s1-oldd):', quackers)
