"""Content-based reimport stamps for the kit importer (import_town_exteriors.py), bug A9 (25 Nov 2026).

The importer re-imports a texture or a mesh only when its source file changed. Until 25 Nov 2026 the stamp kept in the
asset's metadata tag DinkSource was `<size>:<mtime>` of the source file. Git gives every checkout its own mtimes, so a
kit import in any copy other than the one that made the committed packages counted every file as changed, re-imported
every mesh and (hook of A200, #200) gave every single-LOD mesh over 5,000 triangles new engine LODs.

The stamp is now the file's MD5 (`md5:<32 hex>`, plus the importer's suffix such as `:town2`). A package written with
the old stamp is still taken as current without a re-import when the source has the size the old stamp names AND the
MD5 that Unreal itself recorded at that import (the package's AssetImportData `"FileMD5"` entry) equals the file's MD5;
the legacy tag then stays as it is, so nothing in the package changes until the source really does.

Plain Python (no `unreal`): tests in Scripts/tests/test_kit_stamp.py.
"""
import hashlib
import re
from pathlib import Path

_MD5 = {}
_PACKAGE_MD5 = re.compile(rb'"FileMD5" : "([0-9a-f]{32})"')
_LEGACY = re.compile(r'^(\d+):(\d+)(?::(.*))?$')


def file_md5(path):
    """MD5 of the file's bytes (the digest Unreal's FMD5Hash::HashFile stores as FileMD5), cached per run."""
    path = Path(path).resolve()
    st = path.stat()
    key = (str(path), st.st_size, st.st_mtime_ns)
    if key not in _MD5:
        digest = hashlib.md5()
        with open(path, 'rb') as f:
            for block in iter(lambda: f.read(1 << 20), b''):
                digest.update(block)
        _MD5[key] = digest.hexdigest()
    return _MD5[key]


def stamp(path, suffix=''):
    """The DinkSource tag of an import of `path` by an importer whose logic version is `suffix` ('' or e.g. 'town2')."""
    return f'md5:{file_md5(path)}' + (f':{suffix}' if suffix else '')


def package_md5s(package_file):
    """Source-file MD5s recorded in a .uasset's AssetImportData (empty when the package is missing or has none)."""
    try:
        data = Path(package_file).read_bytes()
    except OSError:
        return set()
    return {m.decode() for m in _PACKAGE_MD5.findall(data)}


def package_file(project_dir, asset_path):
    """/Game/Dink/X/Y -> <project>/Content/Dink/X/Y.uasset"""
    asset_path = str(asset_path).split('.')[0]
    if not asset_path.startswith('/Game/'):
        raise ValueError('not a /Game path: ' + asset_path)
    return Path(project_dir) / 'Content' / (asset_path[len('/Game/'):] + '.uasset')


def status(tag, path, package, suffix=''):
    """'current' (the tag is this file's content stamp), 'legacy' (an old size:mtime tag whose import Unreal recorded
    with this file's MD5: the same content, no re-import needed) or None (re-import)."""
    tag = tag or ''
    if tag == stamp(path, suffix):
        return 'current'
    m = _LEGACY.match(tag)
    if not m or (m.group(3) or '') != suffix:
        return None
    if int(m.group(1)) != Path(path).stat().st_size:
        return None
    return 'legacy' if file_md5(path) in package_md5s(package) else None
