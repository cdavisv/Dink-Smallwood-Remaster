#!/usr/bin/env python3
"""Hydrate hash-pinned release assets without Git LFS (Python 3.8+, stdlib only).

Install this script under PROJECT/Scripts/. The default manifest is
PROJECT/AssetPacks/house-v1.json; --manifest can select another manifest.
--verify-only validates the pack and destination eligibility, without installing
assets. Only Saved/AssetPacks cache files/directories may be written in that mode.
The tracked manifest is the trust anchor. PAX metadata is handled by tarfile,
then every final yielded path/type/size and every file digest is checked manually.
No tar extraction API writes paths from an archive.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tarfile
import tempfile
import unicodedata
from dataclasses import dataclass
from typing import BinaryIO, Callable, Dict, Mapping, Optional, Union
import urllib.parse
import urllib.request

CHUNK = 1024 * 1024
SCHEMA = "dink-asset-pack/1"
CACHE_PARTS = ("Saved", "AssetPacks")
HEX256 = re.compile(r"^[0-9a-fA-F]{64}$")
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {
    prefix + str(i) for prefix in ("COM", "LPT") for i in range(1, 10)
}


class AssetPackError(RuntimeError):
    pass


@dataclass(frozen=True)
class Asset:
    path: str
    sha256: str
    size: int

    def pointer(self) -> bytes:
        return ("version https://git-lfs.github.com/spec/v1\n"
                "oid sha256:" + self.sha256 + "\nsize " + str(self.size) + "\n").encode("ascii")


@dataclass(frozen=True)
class Manifest:
    url: str
    sha256: str
    size: int
    files: Dict[str, Asset]


@dataclass(frozen=True)
class Result:
    verified_files: int
    installed_files: int
    already_current: int
    require_hydration: int
    verify_only: bool


def _digest(value, label: str) -> str:
    if not isinstance(value, str) or not HEX256.fullmatch(value):
        raise AssetPackError(label + " must be a SHA-256 hex digest")
    return value.lower()


def _size(value, label: str, positive=False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise AssetPackError(label + " must be a nonnegative integer" if not positive
                             else label + " must be a positive integer")
    return value


def _path_key(path: str) -> str:
    return unicodedata.normalize("NFC", path).casefold()


def _parts(path: str):
    if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path:
        raise AssetPackError("invalid project-relative asset path: " + repr(path))
    parts = path.split("/")
    for part in parts:
        if (part in ("", ".", "..") or part.endswith((".", " ")) or
                any(ord(c) < 32 or c in '<>:"|?*' for c in part) or
                part.split(".", 1)[0].upper() in RESERVED_NAMES or
                part.casefold() in (".git", ".hg", ".svn")):
            raise AssetPackError("unsafe asset path: " + repr(path))
    if tuple(p.casefold() for p in parts[:2]) == ("saved", "assetpacks"):
        raise AssetPackError("asset path uses the bootstrap cache: " + path)
    return tuple(parts)


def validate_manifest(data: Mapping) -> Manifest:
    if not isinstance(data, Mapping) or data.get("schema") != SCHEMA:
        raise AssetPackError("unsupported asset-pack manifest schema")
    url = data.get("url")
    if not isinstance(url, str):
        raise AssetPackError("manifest url must be HTTPS")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise AssetPackError("manifest url must be an HTTPS URL without credentials or fragment")
    archive_hash = _digest(data.get("sha256"), "archive sha256")
    archive_size = _size(data.get("size"), "archive size", positive=True)
    rows = data.get("files")
    if not isinstance(rows, list) or not rows:
        raise AssetPackError("manifest files must be a nonempty list")
    files = {}
    keys = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise AssetPackError("manifest file entry must be an object")
        path = row.get("path")
        _parts(path)
        key = _path_key(path)
        if key in keys:
            raise AssetPackError("duplicate/aliased manifest path: " + path)
        keys.add(key)
        files[path] = Asset(path, _digest(row.get("sha256"), path + " sha256"),
                            _size(row.get("size"), path + " size"))
    for path in files:
        parts = _parts(path)
        for i in range(1, len(parts)):
            if _path_key("/".join(parts[:i])) in keys:
                raise AssetPackError("manifest file is another asset's ancestor: " + path)
    return Manifest(url, archive_hash, archive_size, files)


def _lstat(path: Path):
    try:
        return path.lstat()
    except FileNotFoundError:
        return None


def _link(st) -> bool:
    # Windows junctions/reparse points need the same treatment as POSIX symlinks.
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & 0x400)


def _root(path: Path) -> Path:
    path = Path(path).absolute()
    st = _lstat(path)
    if st is None or _link(st) or not stat.S_ISDIR(st.st_mode):
        raise AssetPackError("project root must be an existing real directory")
    return path.resolve(strict=True)


def _safe_path(root: Path, parts, create_parents=False) -> Path:
    current = root
    for i, part in enumerate(parts):
        current = current / part
        st = _lstat(current)
        is_parent = i < len(parts) - 1
        if st is None and is_parent and create_parents:
            try:
                current.mkdir()
            except FileExistsError:
                pass
            st = _lstat(current)
        if st is not None:
            if _link(st):
                raise AssetPackError("symlink/reparse target or ancestor refused: " + str(current))
            if is_parent and not stat.S_ISDIR(st.st_mode):
                raise AssetPackError("target ancestor is not a directory: " + str(current))
    return current


def _cache(root: Path) -> Path:
    # The sentinel makes both actual cache components go through parent checks.
    sentinel = _safe_path(root, CACHE_PARTS + (".sentinel",), create_parents=True)
    return sentinel.parent


@contextlib.contextmanager
def _regular_reader(path: Path):
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(path), flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise AssetPackError("not a regular file: " + str(path))
        with os.fdopen(fd, "rb") as handle:
            fd = None
            yield handle
    finally:
        if fd is not None:
            os.close(fd)


def _hash_stream(handle: BinaryIO, limit: int) -> str:
    digest = hashlib.sha256()
    count = 0
    while True:
        chunk = handle.read(CHUNK)
        if not chunk:
            break
        count += len(chunk)
        if count > limit:
            raise AssetPackError("file exceeds its pinned size")
        digest.update(chunk)
    if count != limit:
        raise AssetPackError("file size differs from its pinned size")
    return digest.hexdigest()


def _destination_state(root: Path, asset: Asset) -> str:
    path = _safe_path(root, _parts(asset.path))
    st = _lstat(path)
    if st is None:
        return "missing"
    if _link(st) or not stat.S_ISREG(st.st_mode):
        raise AssetPackError("nonregular asset destination refused: " + asset.path)
    with _regular_reader(path) as handle:
        if st.st_size == asset.size and _hash_stream(handle, asset.size) == asset.sha256:
            return "current"
        pointer = asset.pointer()
        if st.st_size == len(pointer):
            handle.seek(0)
            if handle.read(len(pointer) + 1) == pointer:
                return "pointer"
    raise AssetPackError("modified asset would be overwritten: " + asset.path)


def _download(manifest: Manifest, cache: Path, progress) -> Path:
    dest = cache / (manifest.sha256 + ".tar.gz")
    st = _lstat(dest)
    if st is not None:
        if _link(st) or not stat.S_ISREG(st.st_mode):
            raise AssetPackError("nonregular cached archive refused")
        return dest  # Revalidated before parsing, even when named by its digest.
    fd, name = tempfile.mkstemp(prefix=".download-", suffix=".part", dir=str(cache))
    temp = Path(name)
    try:
        digest = hashlib.sha256()
        count = 0
        next_report = 64 * CHUNK
        request = urllib.request.Request(manifest.url, headers={"User-Agent": "DinkAssetPack/1"})
        with os.fdopen(fd, "wb") as out:
            fd = None
            with urllib.request.urlopen(request, timeout=30) as response:
                while True:
                    chunk = response.read(CHUNK)
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > manifest.size:
                        raise AssetPackError("download exceeds pinned archive size")
                    out.write(chunk)
                    digest.update(chunk)
                    if progress and count >= next_report:
                        progress("Downloaded %d / %d bytes" % (count, manifest.size))
                        next_report += 64 * CHUNK
            out.flush()
            os.fsync(out.fileno())
        if count != manifest.size or digest.hexdigest() != manifest.sha256:
            raise AssetPackError("download archive SHA-256/size mismatch")
        st = _lstat(dest)
        if st is not None and (_link(st) or not stat.S_ISREG(st.st_mode)):
            raise AssetPackError("cached archive path changed to a nonregular file")
        os.replace(str(temp), str(dest))
        return dest
    finally:
        if fd is not None:
            os.close(fd)
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _read_pack(handle: BinaryIO, manifest: Manifest, stage: Optional[Path], pending, progress):
    staged = {}
    seen = set()
    # tarfile resolves PAX long paths before yielding each member. We never call
    # extract/extractall and never join an unchecked member name to the root.
    with tarfile.open(fileobj=handle, mode="r|gz", ignore_zeros=True) as archive:
        for member in archive:
            _parts(member.name)
            if member.name in seen:
                raise AssetPackError("duplicate archive member: " + member.name)
            if member.name not in manifest.files:
                raise AssetPackError("unexpected archive member: " + member.name)
            seen.add(member.name)
            asset = manifest.files[member.name]
            if (member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE) or
                    member.sparse is not None or member.linkname):
                raise AssetPackError("nonregular archive member: " + member.name)
            if member.size != asset.size:
                raise AssetPackError("archive member size mismatch: " + member.name)
            stream = archive.extractfile(member)
            if stream is None:
                raise AssetPackError("archive member has no regular payload: " + member.name)
            target = stage / ("%06d.stage" % len(seen)) if stage and member.name in pending else None
            digest = hashlib.sha256()
            remaining = asset.size
            with stream, (target.open("xb") if target else contextlib.nullcontext()) as out:
                while remaining:
                    chunk = stream.read(min(CHUNK, remaining))
                    if not chunk:
                        raise AssetPackError("truncated archive member: " + member.name)
                    remaining -= len(chunk)
                    digest.update(chunk)
                    if out is not None:
                        out.write(chunk)
            if digest.hexdigest() != asset.sha256:
                raise AssetPackError("archive member SHA-256 mismatch: " + member.name)
            if target:
                staged[member.name] = target
            if progress and len(seen) % 128 == 0:
                progress("Verified %d / %d asset payloads" % (len(seen), len(manifest.files)))
    missing = set(manifest.files) - seen
    if missing:
        raise AssetPackError("missing archive member: " + sorted(missing)[0])
    return staged


def bootstrap(manifest_data: Mapping, project_root: Path, archive_path: Optional[Path] = None,
              verify_only: bool = False, progress: Optional[Callable[[str], None]] = None) -> Result:
    """Internal root parameter permits isolated tests; the CLI has no root override.

    Existing files must be exact manifest bytes or the exact canonical three-line
    LFS pointer for that file. All payloads and all destinations are validated
    before any asset is installed; destinations are checked again before replace.
    An interrupted install is resumable because current exact files are skipped.
    """
    manifest = validate_manifest(manifest_data)
    root = _root(project_root)
    cache = _cache(root)
    archive_path = Path(archive_path) if archive_path is not None else _download(manifest, cache, progress)
    if _lstat(archive_path) is not None and _link(archive_path.lstat()):
        raise AssetPackError("symlink archive path refused")
    with tempfile.TemporaryDirectory(prefix=".stage-", dir=str(cache)) as staging:
        with _regular_reader(archive_path) as handle:
            if os.fstat(handle.fileno()).st_size != manifest.size or _hash_stream(handle, manifest.size) != manifest.sha256:
                raise AssetPackError("archive SHA-256/size mismatch (not parsed)")
            handle.seek(0)
            states = {p: _destination_state(root, a) for p, a in manifest.files.items()}
            pending = {p for p, state in states.items() if state != "current"}
            staged = _read_pack(handle, manifest, None if verify_only else Path(staging), pending, progress)
        # Preflight the entire set again, so a modification during staging does
        # not cause a partial install before the later foreign file is noticed.
        final_states = {p: _destination_state(root, a) for p, a in manifest.files.items()}
        if verify_only:
            return Result(len(manifest.files), 0, sum(s == "current" for s in final_states.values()),
                          sum(s != "current" for s in final_states.values()), True)
        for p, state in final_states.items():
            if state != "current" and p not in staged:
                raise AssetPackError("asset changed during verification; retry: " + p)
        installed = 0
        for p in sorted(staged):
            asset = manifest.files[p]
            if _destination_state(root, asset) == "current":
                continue
            target = _safe_path(root, _parts(p), create_parents=True)
            # A second path/state check after directory creation rejects links or
            # foreign files introduced while the pack was being verified.
            if _destination_state(root, asset) == "current":
                continue
            os.chmod(str(staged[p]), 0o644)
            os.replace(str(staged[p]), str(target))
            installed += 1
        return Result(len(manifest.files), installed, len(manifest.files) - installed, 0, False)


def main(argv=None, *, _project_root=None) -> int:
    root = Path(_project_root) if _project_root is not None else Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, default=root / "AssetPacks" / "house-v1.json")
    parser.add_argument("--archive", type=Path, help="use a local tar.gz instead of downloading")
    parser.add_argument("--verify-only", action="store_true", help="validate pack/target eligibility; install no assets")
    args = parser.parse_args(argv)
    try:
        with args.manifest.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        result = bootstrap(data, root, args.archive, args.verify_only,
                           progress=lambda text: print(text, file=sys.stderr, flush=True))
        if result.verify_only:
            print("Verified %d pack files; %d already current, %d require hydration; no assets changed." %
                  (result.verified_files, result.already_current, result.require_hydration))
        else:
            print("Verified %d pack files; hydrated %d, already current %d." %
                  (result.verified_files, result.installed_files, result.already_current))
        return 0
    except (AssetPackError, OSError, ValueError, tarfile.TarError, EOFError) as error:
        print("Asset pack error: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
