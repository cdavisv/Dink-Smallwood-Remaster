"""Catalogue of the frame images reachable from a sequence path.

A ``load_sequence`` path such as ``graphics\\dink\\walk\\ds-w-`` names a
directory (``graphics/dink/walk``) and a file-name prefix (``ds-w-``).  Frames
are ``<prefix><NN>.bmp`` (NN = 01..99 or 100) found first in that directory's
``dir.ff`` and otherwise as loose files next to it (FFReader.cpp:206-303).
"""

import os
from dataclasses import dataclass

from . import ff as ffmod
from . import bmp as bmpmod
from .fsutil import CIResolver

MAX_FRAMES = 100        # C_MAX_SPRITE_FRAMES (dink.h:202)


@dataclass(frozen=True)
class Source:
    kind: str           # 'ff' or 'loose'
    path: str           # absolute path of the archive or the loose file
    rel: str            # path relative to the data dir
    entry: str          # lower-case entry / file name
    offset: int         # byte offset inside the archive (0 for loose)
    size: int

    def read(self):
        with open(self.path, "rb") as f:
            f.seek(self.offset)
            return f.read(self.size)

    def to_json(self):
        d = {"kind": self.kind, "file": self.rel, "entry": self.entry, "bytes": self.size}
        if self.kind == "ff":
            d["offset"] = self.offset
        return d


class DirCatalog:
    """All BMP files visible in one graphics directory."""

    def __init__(self, resolver, directory):
        self.directory = directory
        self.files = {}              # lower-case name -> Source
        self.nonbmp_ff_entries = []  # names of ff entries that are not .bmp
        ffpath = resolver.resolve(resolver.relpath(directory) + "/dir.ff")
        if ffpath and os.path.isfile(ffpath):
            data, entries = ffmod.read_ff(ffpath)
            rel = resolver.relpath(ffpath)
            for e in entries:
                if not e.name.endswith(".bmp"):
                    self.nonbmp_ff_entries.append(e.name)
                    continue
                self.files.setdefault(e.name, Source("ff", ffpath, rel, e.name, e.offset, e.size))
        for name in sorted(os.listdir(directory)):
            low = name.lower()
            full = os.path.join(directory, name)
            if low.endswith(".bmp") and os.path.isfile(full) and low not in self.files:
                self.files[low] = Source("loose", full, resolver.relpath(full), low, 0, os.path.getsize(full))

    def frames_for(self, prefix):
        """Consecutive frames prefix01, prefix02, ... (no gaps; D:2032)."""
        out = []
        prefix = prefix.lower()
        for n in range(1, MAX_FRAMES + 1):
            src = self.files.get("%s%02d.bmp" % (prefix, n))
            if src is None:
                break
            out.append(src)
        return out


class Graphics:
    def __init__(self, base):
        self.base = base
        self.resolver = CIResolver(base)
        self._dirs = {}

    def catalog(self, rel_dir):
        real = self.resolver.resolve(rel_dir)
        if real is None or not os.path.isdir(real):
            return None
        cat = self._dirs.get(real)
        if cat is None:
            cat = DirCatalog(self.resolver, real)
            self._dirs[real] = cat
        return cat

    def frames(self, ini_path):
        """ini_path like 'graphics\\\\dink\\\\walk\\\\ds-w-' -> (list[Source], dir catalog or None)."""
        p = ini_path.replace("\\", "/")
        d, _, prefix = p.rpartition("/")
        cat = self.catalog(d)
        if cat is None:
            return [], None
        return cat.frames_for(prefix), cat

    def census(self):
        """Count every BMP under graphics/: archive entries and loose files.

        Returns dict with keys archives, ff_bmp_entries, ff_nonbmp_entries,
        loose_bmps, total_bmps.
        """
        archives = ffbmp = ffother = loose = 0
        gdir = self.resolver.resolve("graphics")
        for root, _dirs, files in os.walk(gdir):
            for f in sorted(files):
                low = f.lower()
                full = os.path.join(root, f)
                if low.endswith(".ff"):
                    archives += 1
                    _, entries = ffmod.read_ff(full)
                    for e in entries:
                        if e.name.endswith(".bmp"):
                            ffbmp += 1
                        else:
                            ffother += 1
                elif low.endswith(".bmp"):
                    loose += 1
        return {
            "archives": archives,
            "ff_bmp_entries": ffbmp,
            "ff_nonbmp_entries": ffother,
            "loose_bmps": loose,
            "total_bmps": ffbmp + loose,
        }
