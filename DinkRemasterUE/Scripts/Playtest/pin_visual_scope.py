#!/usr/bin/env python3
"""Pin runtime content, import fixtures, native sources/config and custom module bytes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]

def snapshot():
    started = datetime.now(timezone.utc).isoformat()
    selected = set()
    for root in ['Content', 'ImportData', 'Source', 'Config']:
        selected.update(p for p in (PROJECT / root).rglob('*') if p.is_file())
    for plugin in (PROJECT / 'Plugins').iterdir():
        for sub in ['Source', 'Config']:
            selected.update(p for p in (plugin / sub).rglob('*') if p.is_file())
        selected.update(plugin.glob('*.uplugin'))
        selected.update((plugin / 'Binaries').rglob('*.so'))
        selected.update((plugin / 'Binaries').rglob('*.modules'))
    selected.update((PROJECT / 'Binaries').rglob('*.so'))
    selected.update((PROJECT / 'Binaries').rglob('*.modules'))
    selected.add(PROJECT / 'DinkRemaster.uproject')
    files = {str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(selected)}
    return {'schema': 'dink-visual-scope/1', 'project': str(PROJECT),
            'started_utc': started, 'completed_utc': datetime.now(timezone.utc).isoformat(),
            'files': files, 'scope': 'All Content/ImportData/Source/Config files, plugin Source/Config/descriptors, custom .so/.modules and project descriptor. Excludes volatile Saved/cache and source-art files not loaded by the game.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args()
    assert not args.out.exists(), 'Preserve existing evidence'
    data = snapshot()
    if args.compare:
        before = json.loads(args.compare.read_text())['files']
        after = data['files']
        data['changes'] = [p for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2) + '\n')
    print('Pinned', len(data['files']), 'files;', len(data.get('changes', [])), 'changes')
    if data.get('changes'):
        raise SystemExit(1)
