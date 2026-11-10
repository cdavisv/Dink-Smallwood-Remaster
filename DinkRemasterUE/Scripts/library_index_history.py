"""Verify frozen historical bytes for exactly two append-versioned library indexes.
All ordinary asset ledger paths remain strict current-byte matches. This module
never edits ledger rows and requires the latest row to match the current index.
"""
from pathlib import Path
import hashlib
import re

INDEXES = frozenset({'SourceAssets/Art/SharedMaterials/manifest.json',
                     'SourceAssets/Art/SharedMaterials/SHA256SUMS.json'})
DIGEST = re.compile(r'[0-9a-f]{64}\Z')


def historical_index_matches(root, rows, row):
    """True only for a superseded eligible row with exact archived original bytes."""
    name = row.get('asset_path')
    digest = row.get('sha256', '')
    if name not in INDEXES or not DIGEST.fullmatch(digest):
        return False
    versions = [r for r in rows if r.get('asset_path') == name]
    if len(versions) < 2 or row not in versions[:-1]:
        return False
    latest = versions[-1].get('sha256', '')
    if latest == digest or not DIGEST.fullmatch(latest):
        return False
    root = Path(root).resolve()
    current = root / name
    history = current.parent / 'History'
    archive = history / digest / current.name
    # Every path component in this narrowly owned source tree must be regular.
    if any(p.is_symlink() for p in [current, current.parent, history, archive.parent, archive]):
        return False
    if not current.is_file() or not archive.is_file():
        return False
    if archive.resolve() != archive or current.resolve() != current:
        return False
    return (hashlib.sha256(current.read_bytes()).hexdigest() == latest and
            hashlib.sha256(archive.read_bytes()).hexdigest() == digest)
