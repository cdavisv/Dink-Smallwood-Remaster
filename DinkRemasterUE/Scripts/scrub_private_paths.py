#!/usr/bin/env python3
"""Find and remove private, machine-identifying data from the tracked tree.

The repository is public. Files written by tools on a workstation tend to carry
the author's home folder and login name (manifests, logs, Blender and FBX files,
PNG text chunks), and Unreal logs carry a machine id and LAN address. This tool
finds them and takes them out without damaging the files.

Usage (from anywhere inside the repository):
  python3 -I DinkRemasterUE/Scripts/scrub_private_paths.py --check
  python3 -I DinkRemasterUE/Scripts/scrub_private_paths.py --fix
  ... --user NAME      also treat NAME as a private login name (repeatable)
  ... --text-only      look at plain-text files only (what the unit test does)
  ... PATH [PATH ...]  limit the run to these files or folders

What counts as private:
  * a home folder path `/home/<name>` whose name is not a neutral one
    (`artist`, `user`, `runner`, ...), and that login name wherever else it
    appears. Names are collected from the tree itself, from --user, and from
    the current login ($USER) when it is not neutral;
  * session folders of AI tools (`/tmp/claude-<uid>/...`) and `/run/user/<uid>`;
  * the Unreal `MachineId=` / `loginid=` value and 192.168.x.x addresses.

--check lists the offending files and exits 1; exit 0 means clean. Git LFS
files are examined only when the real file is in the working tree (a pointer
has nothing to examine).

--fix rewrites in place:
  * Plain text whose content hash is NOT recorded elsewhere in the tree:
    a path into this repository becomes relative (to the file's own folder for
    JSON under the photoreal pass that points at a neighbour, otherwise to the
    repository root; the bare root becomes `<repo>`), any other home path
    becomes `~/...`. Python scripts get code that derives the path instead:
    `Path(__file__).resolve().parents[n]` for paths into the repository and
    `Path.home()` for the rest, so they still run.
  * Plain text other than scripts whose sha256 IS recorded somewhere (frozen
    evidence, pinned sources): the login name is replaced by a neutral name of the same length
    (a six-letter name becomes `artist`), so recorded byte sizes stay true.
  * Binaries: the same same-length replacement, so length-prefixed strings and
    offsets stay valid. PNG: only ancillary chunks are touched and their CRCs
    recomputed (pixels untouched; compressed text chunks are re-deflated).
    JPEG: metadata segments that hold private data are dropped (lossless).
    zstd-compressed files (.blend) are decompressed, changed and recompressed
    with the same frame layout and seek table. gzip and zip/npz likewise.
  * Finally every recorded sha256 of a file that changed is updated to the new
    value wherever it is written down in a text file (repeated until stable),
    and a byte size written within a few lines of such a hash is updated when
    a recompressed container changed size, so manifests, pins and evidence
    chains still agree with the files.

Standard library only (Python 3.14 for zstd files; older Pythons skip them and
say so).
"""
import argparse
import gzip
import hashlib
import io
import os
import re
import struct
import subprocess
import sys
import zipfile
import zlib

try:
    from compression import zstd  # Python 3.14+
except ImportError:  # pragma: no cover
    zstd = None

NEUTRAL_USERS = {
    "artist", "user", "username", "runner", "name", "you", "me", "ubuntu", "vsts", "builder", "build",
    "work", "home", "dev", "developer", "example", "someone", "linuxbrew", "git", "jenkins", "circleci",
    "glados",   # the upstream project's own build host, published by upstream in its build scripts
}
REPO_DIR_NAME = b"Dink-Smallwood-Remaster"
OLD_LAYOUT = b"/Repos/Dink-Smallwood/DinkRemasterUE"   # the project before it moved into the repository
RELATIVE_JSON_ROOT = "DinkRemasterUE/SourceAssets/Art/PhotorealPass/"
SELF_NAMES = ("scrub_private_paths.py", "test_scrub_private_paths.py")

HOME_RE = re.compile(rb"(?<![A-Za-z0-9_.\-/~$}])/home/([a-z_][a-z0-9_\-]{0,31})(?![A-Za-z0-9_\-.])")
PATH_TAIL = rb"(?:/[A-Za-z0-9_.+\-@%=~]+)*/?"
CLAUDE_TMP_RE = re.compile(rb"/tmp/claude-(\d+)/([^/\s\"']+)/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
RUN_USER_RE = re.compile(rb"/run/user/([1-9]\d*)")
MACHINE_RE = re.compile(rb"((?:MachineId=|loginid=\"|LoginId=|DeviceId=|UserID=))([0-9a-fA-F]{32})")
LAN_RE = re.compile(rb"(?<![\d.])192\.168\.(\d{1,3})\.(\d{1,3})(?![\d.])")
SHA_RE = re.compile(rb"(?<![0-9a-fA-F])[0-9a-f]{64}(?![0-9a-fA-F])")
TEXT_SNIFF = 8192


def neutral_name(name):
    """A neutral login name of the same length."""
    if len(name) == 6:
        return "artist"
    return ("user" + "0" * len(name))[:len(name)] if len(name) >= 4 else "usr"[:len(name)]


def is_neutral(name):
    return name.lower() in NEUTRAL_USERS or re.fullmatch(r"user0*|usr?", name.lower()) is not None


class Rules:
    def __init__(self, users=()):
        self.users = set()
        self.machine_ids = set()   # values seen after MachineId= and the like; removed wherever they recur
        for u in users:
            self.add_user(u)

    def add_user(self, name):
        name = name.strip()
        if name and not is_neutral(name) and len(name) >= 3:
            self.users.add(name)

    def harvest(self, data):
        for m in HOME_RE.finditer(data):
            self.add_user(m.group(1).decode("ascii"))
        for m in MACHINE_RE.finditer(data):
            if set(m.group(2)) != {ord("0")}:
                self.machine_ids.add(m.group(2))

    def user_patterns(self):
        out = []
        for u in sorted(self.users, key=len, reverse=True):
            for form in {u, u.upper(), u.capitalize()}:
                repl = neutral_name(u)
                repl = repl.upper() if form.isupper() else repl.capitalize() if form[0].isupper() else repl
                out.append((form.encode(), repl.encode()))
                out.append((form.encode("utf-16-le"), repl.encode("utf-16-le")))
        return out

    # ---- detection ----
    def findings(self, data):
        """Return a list of (category, example bytes) found in data."""
        found = []
        for form, _ in self.user_patterns():
            i = data.find(form)
            if i >= 0:
                found.append(("login name / home path", data[max(0, i - 24):i + len(form) + 40]))
                break
        if not found:
            for m in HOME_RE.finditer(data):
                if not is_neutral(m.group(1).decode()):
                    found.append(("login name / home path", data[m.start():m.end() + 40]))
                    break
        m = CLAUDE_TMP_RE.search(data)
        if m and set(m.group(3)) - set(b"0-"):
            found.append(("AI session folder", m.group(0)))
        m = RUN_USER_RE.search(data)
        if m:
            found.append(("/run/user uid", m.group(0)))
        for m in MACHINE_RE.finditer(data):
            if set(m.group(2)) != {ord("0")}:
                found.append(("machine id", m.group(0)))
                break
        else:
            for mid in self.machine_ids:
                i = data.find(mid)
                if i >= 0:
                    found.append(("machine id", data[max(0, i - 16):i + 32]))
                    break
        for m in LAN_RE.finditer(data):
            if m.group(1).strip(b"0") or m.group(2).strip(b"0"):
                found.append(("LAN address", m.group(0)))
                break
        return found

    # ---- same-length neutralisation (text and binary) ----
    def neutralise(self, data):
        for form, repl in self.user_patterns():
            if form in data:
                data = data.replace(form, repl)
        data = CLAUDE_TMP_RE.sub(lambda m: m.group(0)[:m.start(3) - m.start(0)] + re.sub(rb"[0-9a-f]", b"0", m.group(3)), data)
        data = RUN_USER_RE.sub(lambda m: b"/run/user/" + b"0" * len(m.group(1)), data)
        data = MACHINE_RE.sub(lambda m: m.group(1) + b"0" * 32, data)
        for mid in self.machine_ids:
            data = data.replace(mid, b"0" * 32)
        data = LAN_RE.sub(lambda m: b"192.168." + b"0" * len(m.group(1)) + b"." + b"0" * len(m.group(2)), data)
        return data


# --------------------------------------------------------------------------- containers

def png_chunks(data):
    p = 8
    while p + 12 <= len(data):
        n, kind = struct.unpack(">I4s", data[p:p + 8])
        yield kind, data[p + 8:p + 8 + n]
        p += 12 + n


def png_text_payload(kind, body):
    """(prefix, text, compressed?) for a text chunk; text is what a reader sees."""
    if kind == b"tEXt":
        return b"", body, False
    key, _, rest = body.partition(b"\0")
    if kind == b"zTXt":
        return key + b"\0" + rest[:1], zlib.decompress(rest[1:]), True
    if kind == b"iTXt":
        flag, method = rest[:1], rest[1:2]
        lang, _, rest2 = rest[2:].partition(b"\0")
        trans, _, text = rest2.partition(b"\0")
        prefix = key + b"\0" + flag + method + lang + b"\0" + trans + b"\0"
        if flag == b"\x01":
            return prefix, zlib.decompress(text), True
        return prefix, text, False
    return None


def png_views(data):
    for kind, body in png_chunks(data):
        if kind in (b"IDAT", b"IEND", b"IHDR", b"PLTE"):
            continue
        if kind in (b"tEXt", b"zTXt", b"iTXt"):
            try:
                yield png_text_payload(kind, body)[1]
            except zlib.error:
                yield body
        else:
            yield body


def png_fix(data, rules):
    out = [data[:8]]
    for kind, body in png_chunks(data):
        if kind not in (b"IDAT", b"IEND", b"IHDR", b"PLTE"):
            if kind in (b"tEXt", b"zTXt", b"iTXt"):
                try:
                    prefix, text, packed = png_text_payload(kind, body)
                    new = rules.neutralise(text)
                    if new != text:
                        body = prefix + (zlib.compress(new, 9) if packed else new)
                except zlib.error:
                    body = rules.neutralise(body)
            else:
                body = rules.neutralise(body)
        out.append(struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))
    return b"".join(out)


def jpeg_segments(data):
    """Yield (start, end, marker, payload) for the header segments up to SOS."""
    p = 2
    while p + 4 <= len(data) and data[p] == 0xFF:
        marker = data[p + 1]
        if marker in (0xDA, 0xD9):
            return
        if 0xD0 <= marker <= 0xD7 or marker == 0x01:
            p += 2
            continue
        n = struct.unpack(">H", data[p + 2:p + 4])[0]
        yield p, p + 2 + n, marker, data[p + 4:p + 2 + n]
        p += 2 + n


def jpeg_meta(marker):
    return marker == 0xFE or marker == 0xE1 or marker == 0xED or 0xE3 <= marker <= 0xEC  # COM, Exif/XMP, IPTC, APP3-12


def jpeg_views(data):
    for _, _, marker, payload in jpeg_segments(data):
        if jpeg_meta(marker):
            yield payload


def jpeg_fix(data, rules):
    out, last = [], 0
    for start, end, marker, payload in jpeg_segments(data):
        if jpeg_meta(marker) and rules.findings(payload):
            out.append(data[last:start])
            last = end
    out.append(data[last:])
    return b"".join(out)


ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
SEEK_FOOTER = b"\xb1\xea\x92\x8f"
SEEK_HEADER = b"\x5e\x2a\x4d\x18"


def zstd_frames(data):
    """Return (frame compressed sizes, has checksum) from a seek table, or None."""
    if len(data) < 17 or data[-4:] != SEEK_FOOTER:
        return None
    count, desc = struct.unpack("<IB", data[-9:-4])
    entry = 12 if desc & 0x80 else 8
    table = 8 + count * entry + 9
    if len(data) < table or data[-table:-table + 4] != SEEK_HEADER:
        return None
    sizes = [struct.unpack("<I", data[-table + 8 + i * entry:-table + 12 + i * entry])[0] for i in range(count)]
    if sum(sizes) + table != len(data):
        return None
    return sizes


def zstd_unpack(data):
    """Return (list of decompressed frames, seekable?)."""
    sizes = zstd_frames(data)
    if sizes is None:
        return [zstd.ZstdFile(io.BytesIO(data)).read()], False
    frames, p = [], 0
    for n in sizes:
        frames.append(zstd.decompress(data[p:p + n]))
        p += n
    return frames, True


def zstd_pack(frames, seekable):
    if not seekable:
        return zstd.compress(frames[0], 3)
    packed = [zstd.compress(f, 3) for f in frames]
    table = b"".join(struct.pack("<II", len(c), len(f)) for c, f in zip(packed, frames))
    table += struct.pack("<IB", len(frames), 0) + SEEK_FOOTER
    return b"".join(packed) + SEEK_HEADER + struct.pack("<I", len(table)) + table


def zstd_fix(data, rules):
    frames, seekable = zstd_unpack(data)
    whole = b"".join(frames)
    new = rules.neutralise(whole)
    if new == whole:
        return data
    out, p = [], 0
    for f in frames:
        out.append(new[p:p + len(f)])
        p += len(f)
    return zstd_pack(out, seekable)


def gzip_fix(data, rules):
    raw = gzip.decompress(data)
    new = rules.neutralise(raw)
    if new == raw:
        return data
    mtime = struct.unpack("<I", data[4:8])[0]
    name = b""
    if data[3] & 0x08:
        start = 10 + (2 + struct.unpack("<H", data[10:12])[0] if data[3] & 0x04 else 0)
        name = data[start:data.index(b"\0", start)]
    buf = io.BytesIO()
    with gzip.GzipFile(filename=name.decode("latin-1"), mode="wb", fileobj=buf, mtime=mtime) as g:
        g.write(new)
    return buf.getvalue()


def zip_views(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            yield info.filename.encode() + b"\0" + z.read(info)


def zip_fix(data, rules):
    buf = io.BytesIO()
    changed = False
    with zipfile.ZipFile(io.BytesIO(data)) as z, zipfile.ZipFile(buf, "w") as out:
        for info in z.infolist():
            raw = z.read(info)
            new = rules.neutralise(raw)
            changed |= new != raw
            out.writestr(info, new, compress_type=info.compress_type)
    return buf.getvalue() if changed else data


def binary_views(path, data):
    """The byte strings a reader of this file would see, for searching."""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            yield from png_views(data)
        elif data[:2] == b"\xff\xd8":
            yield from jpeg_views(data)
        elif data[:4] == ZSTD_MAGIC:
            if zstd is None:
                return
            yield b"".join(zstd_unpack(data)[0])
        elif data[:2] == b"\x1f\x8b":
            yield gzip.decompress(data)
        elif data[:4] == b"PK\x03\x04":
            yield from zip_views(data)
        else:
            yield data
    except Exception as ex:  # a damaged container is reported, not skipped silently
        sys.stderr.write("warning: could not read inside %s (%s)\n" % (path, ex))
        yield data


def binary_fix(data, rules):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return png_fix(data, rules)
    if data[:2] == b"\xff\xd8":
        return jpeg_fix(data, rules)
    if data[:4] == ZSTD_MAGIC:
        return zstd_fix(data, rules) if zstd else data
    if data[:2] == b"\x1f\x8b":
        return gzip_fix(data, rules)
    if data[:4] == b"PK\x03\x04":
        return zip_fix(data, rules)
    return rules.neutralise(data)


# --------------------------------------------------------------------------- text rewriting

def split_private_path(rest):
    """rest is what follows /home/<name>. Return ('repo', relative path) or ('home', rest)."""
    marker = b"/" + REPO_DIR_NAME
    i = rest.find(marker)
    if i >= 0 and rest[i + len(marker):i + len(marker) + 1] in (b"", b"/"):
        return "repo", rest[i + len(marker):].strip(b"/")
    if rest.startswith(OLD_LAYOUT) and rest[len(OLD_LAYOUT):len(OLD_LAYOUT) + 1] in (b"", b"/"):
        return "repo", rest[len(b"/Repos/Dink-Smallwood/"):].strip(b"/")
    return "home", rest


def private_path_re(rules):
    names = b"|".join(re.escape(u.encode()) for u in sorted(rules.users, key=len, reverse=True))
    return re.compile(rb"(?<![A-Za-z0-9_.\-/~$}])/home/(?:" + names + rb")(" + PATH_TAIL + rb")") if names else None


def relative_text(path, data, rules):
    """Variable-length rewrite for prose, logs, JSON and the like."""
    rx = private_path_re(rules)
    if rx is None:
        return data
    here = os.path.dirname(path)

    def repl(m):
        rest = m.group(1)
        trail = b""
        while rest[-1:] in (b".", b"/") and not rest.endswith(b".."):
            trail = rest[-1:] + trail
            rest = rest[:-1]
        if trail.startswith(b"/") and trail != b"/":
            trail = trail  # "dir/." keeps its punctuation
        kind, rel = split_private_path(rest)
        if kind == "home":
            return b"~" + rest + trail
        if not rel:
            return b"<repo>" + trail
        rel_s = rel.decode("utf-8", "replace")
        if path.startswith(RELATIVE_JSON_ROOT) and path.endswith(".json") and rel_s.startswith(RELATIVE_JSON_ROOT):
            stream = path[len(RELATIVE_JSON_ROOT):].split("/")[0]
            if rel_s[len(RELATIVE_JSON_ROOT):].split("/")[0] == stream:
                return os.path.relpath(rel_s, here).replace(os.sep, "/").encode() + trail
        return rel + trail

    return rx.sub(repl, data)


def python_text(path, data, rules):
    """Make a script derive its paths instead of naming a home folder.

    Only a string literal that is, on its own, a private path is replaced (found with the tokenizer, so
    text inside a longer string, an f-string or a comment is never turned into code; neutralise() deals
    with those). `Path('<private>')` and a bare `'<private>'` both become an expression."""
    import ast
    import tokenize
    rx = private_path_re(rules)
    if rx is None:
        return data
    depth = path.count("/")  # parents[depth] of the script is the repository root
    script_dir = os.path.dirname(path)

    def expr(rest):
        kind, rel = split_private_path(rest.rstrip(b"/"))
        if kind == "repo":
            rel_s = rel.decode()
            if rel_s == "" or (script_dir + "/").startswith(rel_s + "/"):
                return "Path(__file__).resolve().parents[%d]" % (depth - (rel_s.count("/") + 1 if rel_s else 0))
            return "Path(__file__).resolve().parents[%d]/%r" % (depth, rel_s)
        return "Path.home()/%r" % rest.strip(b"/").decode()

    try:
        text = data.decode("utf-8")
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (UnicodeDecodeError, tokenize.TokenError, SyntaxError, IndentationError):
        return data
    lines = text.split("\n")
    edits = []
    for i, tok in enumerate(tokens):
        if tok.type != tokenize.STRING or tok.start[0] != tok.end[0]:
            continue
        if re.match(r"[A-Za-z]*[bBfF]", tok.string):
            continue
        try:
            value = ast.literal_eval(tok.string)
        except (ValueError, SyntaxError):
            continue
        if not isinstance(value, str):
            continue
        m = rx.fullmatch(value.encode("utf-8", "replace"))
        if not m:
            continue
        inside_path = (i >= 2 and tokens[i - 1].string == "(" and tokens[i - 2].string == "Path"
                       and i + 1 < len(tokens) and tokens[i + 1].string == ")")
        code = expr(m.group(1))
        edits.append((tok.start[0] - 1, tok.start[1], tok.end[1], code if inside_path else "str(" + code + ")"))
    if not edits:
        return data
    for row, c0, c1, code in sorted(edits, reverse=True):
        lines[row] = lines[row][:c0] + code + lines[row][c1:]
    new = "\n".join(lines)
    if not re.search(r"^\s*from pathlib import [^\n]*\bPath\b", new, re.M):
        rows = new.split("\n")
        at = next((i for i, l in enumerate(rows) if re.match(r"(import|from)\s", l) and not l.startswith("from __future__")), None)
        if at is None:
            return data
        rows.insert(at, "from pathlib import Path")
        new = "\n".join(rows)
    try:
        compile(new, path, "exec")
    except SyntaxError:
        return data
    return new.encode("utf-8")


# --------------------------------------------------------------------------- tree walking

def git(root, *args, **kw):
    return subprocess.run(["git", "-C", root, *args], capture_output=True, check=True, **kw).stdout


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        return subprocess.run(["git", "-C", here, "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return os.path.dirname(os.path.dirname(here))


def tracked_files(root, limits):
    try:
        names = git(root, "ls-files", "-z").split(b"\0")
        names = [n.decode("utf-8", "surrogateescape") for n in names if n]
    except (OSError, subprocess.CalledProcessError):
        names = []
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x != ".git"]
            names += [os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/") for f in files]
    if limits:
        lim = [os.path.relpath(os.path.abspath(l), root).replace(os.sep, "/").rstrip("/") for l in limits]
        names = [n for n in names if any(n == l or n.startswith(l + "/") or l == "." for l in lim)]
    return sorted(names)


def is_lfs_pointer(data):
    return len(data) < 300 and data.startswith(b"version https://git-lfs.github.com/spec/")


def is_text(data):
    head = data[:TEXT_SNIFF]
    return b"\0" not in head


def load(root, name):
    full = os.path.join(root, name)
    if os.path.islink(full) or not os.path.isfile(full):
        return None
    with open(full, "rb") as f:
        return f.read()


def scan(root, names, rules, text_only=False):
    """Return {name: [(category, example)]}; collects login names on the way."""
    todo = []
    for name in names:
        if os.path.basename(name) in SELF_NAMES:
            continue
        data = load(root, name)
        if data is None or is_lfs_pointer(data):
            continue
        text = is_text(data)
        if text_only and not text:
            continue
        views = [data] if text else list(binary_views(name, data))
        for v in views:
            rules.harvest(v)
        todo.append((name, views))
    hits = {}
    for name, views in todo:
        found = []
        for v in views:
            found += rules.findings(v)
        if found:
            hits[name] = found
    return hits


def recorded_hashes(root, names):
    seen = set()
    for name in names:
        data = load(root, name)
        if data is None or is_lfs_pointer(data) or not is_text(data):
            continue
        seen.update(SHA_RE.findall(data))
    return seen


def propagate(root, all_names, pending, recorded, resized):
    """Write new sha256 values (and, beside them, new byte sizes) wherever the old ones are recorded.

    pending maps old to new hash. A file that records a hash may itself be recorded elsewhere, so this
    repeats until nothing changes. A size is only touched within a few lines of the hash it belongs to."""
    rounds, updated, first = 0, set(), True
    every = dict(pending)
    while (pending or first) and rounds < 200:
        rounds += 1
        recorded.update(pending.values())
        nxt = {}
        for name in all_names:
            data = load(root, name)
            if data is None or is_lfs_pointer(data) or not is_text(data):
                continue
            found = set(SHA_RE.findall(data))
            if not any(h in pending for h in found) and not (first and any(h in resized for h in found)):
                continue
            old = hashlib.sha256(data).hexdigest().encode()
            new = SHA_RE.sub(lambda m: pending.get(m.group(0), m.group(0)), data)
            for h in set(SHA_RE.findall(new)) & set(resized):
                was, now = (str(n).encode() for n in resized[h])
                rx = re.compile(rb"(?<![\d.])" + was + rb"(?![\d.])")
                at = new.find(h)
                while at >= 0:
                    lo, hi = max(0, at - 400), at + 64 + 400
                    patched = rx.sub(now, new[lo:hi])
                    new = new[:lo] + patched + new[hi:]
                    at = new.find(h, at + 64)
            if new == data:
                continue
            with open(os.path.join(root, name), "wb") as f:
                f.write(new)
            updated.add(name)
            if old in recorded:
                nxt[old] = hashlib.sha256(new).hexdigest().encode()
        pending, first = nxt, False
        every.update(nxt)
    rename_hashed_paths(root, all_names, every)
    return updated, rounds


def rename_hashed_paths(root, all_names, mapping):
    """A folder or file named after the sha256 of a file that changed (a content-addressed archive)
    is renamed to the new hash; the text that refers to it has already been updated."""
    moves = {}
    for name in all_names:
        parts = name.split("/")
        for i, part in enumerate(parts):
            new = mapping.get(part.encode())
            hops = 0
            while new in mapping and hops < 1000:   # a file updated in several rounds: follow to its final hash
                new, hops = mapping[new], hops + 1
            if new:
                moves["/".join(parts[:i + 1])] = "/".join(parts[:i] + [new.decode()])
    for src in sorted(moves, key=len, reverse=True):
        a, b = os.path.join(root, src), os.path.join(root, moves[src])
        if os.path.exists(a) and not os.path.exists(b):
            os.rename(a, b)
    return moves


def fix(root, names, rules, hits, verbose=True):
    all_names = tracked_files(root, None)
    recorded = recorded_hashes(root, all_names)
    changed = {}   # old sha256 -> new sha256
    resized = {}   # new sha256 -> (old size, new size), for containers that had to be recompressed
    report = {"relative": 0, "script": 0, "same_length": 0, "binary": 0, "resized": []}
    for name in sorted(hits):
        full = os.path.join(root, name)
        data = load(root, name)
        old = hashlib.sha256(data).hexdigest()
        if is_text(data):
            new = data
            if name.endswith(".py"):
                new = python_text(name, new, rules)   # a script must keep running, pinned or not
                report["script"] += new != data
            elif old.encode() not in recorded:
                new = relative_text(name, new, rules)
                report["relative"] += new != data
            else:
                report["same_length"] += 1
            new = rules.neutralise(new)
        else:
            new = binary_fix(data, rules)
            report["binary"] += 1
            if len(new) != len(data):
                report["resized"].append((name, len(data), len(new)))
                resized[hashlib.sha256(new).hexdigest().encode()] = (len(data), len(new))
        if new != data:
            with open(full, "wb") as f:
                f.write(new)
            changed[old] = hashlib.sha256(new).hexdigest()
    # keep recorded hashes and byte sizes true
    pending = {k.encode(): v.encode() for k, v in changed.items() if k.encode() in recorded}
    updated, rounds = propagate(root, all_names, pending, recorded, resized)
    report["hash_files"] = len(updated)
    report["hash_rounds"] = rounds
    report["changed"] = len(changed)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--fix", action="store_true")
    ap.add_argument("--user", action="append", default=[], help="a login name to treat as private")
    ap.add_argument("--text-only", action="store_true")
    ap.add_argument("--root", help="repository root (default: found from this script)")
    ap.add_argument("paths", nargs="*")
    args = ap.parse_args(argv)
    root = args.root or repo_root()
    rules = Rules(args.user + [os.environ.get("USER", ""), os.environ.get("LOGNAME", "")])
    names = tracked_files(root, args.paths)
    hits = scan(root, names, rules, args.text_only)
    if args.fix and hits:
        report = fix(root, names, rules, hits)
        print("fixed %d files: %d text made relative, %d scripts made to derive paths, %d pinned text files same-length, %d binaries; "
              "%d files had recorded sha256 values updated (%d rounds)" % (
                  report["changed"], report["relative"], report["script"], report["same_length"], report["binary"],
                  report["hash_files"], report["hash_rounds"]))
        for name, a, b in report["resized"]:
            print("  size changed %d -> %d  %s" % (a, b, name))
        hits = scan(root, names, rules, args.text_only)
    by_cat = {}
    for name, found in sorted(hits.items()):
        for cat, ex in found:
            by_cat.setdefault(cat, []).append((name, ex))
    for cat, rows in sorted(by_cat.items()):
        print("%s: %d files" % (cat, len(rows)))
        for name, ex in rows[:200]:
            print("  %s  [%s]" % (name, ex[:80].decode("utf-8", "replace").replace("\n", " ")))
        if len(rows) > 200:
            print("  ... %d more" % (len(rows) - 200))
    if hits:
        print("%d files hold private data. Run with --fix, or correct them by hand." % len(hits))
        return 1
    print("clean: no private paths or machine ids in %d files" % len(names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
