"""The public tree must not carry private paths, login names or machine ids."""
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS)
import scrub_private_paths as scrub  # noqa: E402

# Built from pieces so this file never contains what it tests for.
NAME = "zz" + "private" + "x"                     # an invented login name
HOME = "/" + "home" + "/" + NAME
REPO = HOME + "/Repos/" + scrub.REPO_DIR_NAME.decode()


def rules():
    r = scrub.Rules()
    r.add_user(NAME)
    return r


def png(text_chunks):
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    idat = zlib.compress(b"\x00\x10\x20\x30")
    out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    for kind, body in text_chunks:
        out += chunk(kind, body)
    return out + chunk(b"IDAT", idat) + chunk(b"IEND", b""), idat


class TreeIsClean(unittest.TestCase):
    def test_tracked_text_files_hold_no_private_data(self):
        root = scrub.repo_root()
        found = scrub.scan(root, scrub.tracked_files(root, None), scrub.Rules(), text_only=True)
        listing = "\n".join("  %s: %s" % (n, f[0][0]) for n, f in sorted(found.items())[:40])
        self.assertEqual({}, found, "private paths or machine ids are committed; run "
                         "DinkRemasterUE/Scripts/scrub_private_paths.py --fix\n" + listing)

    def test_present_lfs_files_hold_no_private_data(self):
        root = scrub.repo_root()
        base = "DinkRemasterUE/SourceAssets/Art/PhotorealPass"
        names = [n for n in scrub.tracked_files(root, None) if n.startswith(base) and n.endswith((".fbx", ".blend"))][:400]
        real = [n for n in names if (scrub.load(root, n) or b"")[:8] and not scrub.is_lfs_pointer(scrub.load(root, n))]
        if not real:
            self.skipTest("LFS files are pointers in this checkout")
        self.assertEqual({}, scrub.scan(root, real, scrub.Rules()))


class Detection(unittest.TestCase):
    def test_finds_home_path_and_collects_the_name(self):
        r = scrub.Rules()
        data = ('{"file": "%s/Work/x.blend"}' % HOME).encode()
        r.harvest(data)
        self.assertIn(NAME, r.users)
        self.assertTrue(r.findings(data))
        self.assertTrue(r.findings(b"user name is '" + NAME.encode() + b"'"))

    def test_neutral_and_look_alike_paths_pass(self):
        r = scrub.Rules()
        for ok in (b"/home/artist/Work/x", b"/home/user/x", b"struct/home/home-01", b"dink/home/dir.ff", b"~/Work/x", b"$HOME/x"):
            r.harvest(ok)
            self.assertEqual([], r.findings(ok), ok)
        self.assertEqual(set(), r.users)

    def test_machine_id_lan_address_and_session_folder(self):
        r = scrub.Rules()
        self.assertTrue(r.findings(b"MachineId=" + b"ab12" * 8))
        self.assertTrue(r.findings(b"interface '192.168.7.21' joined"))
        self.assertTrue(r.findings(b"/tmp/claude-1000/-x-y/0a1b2c3d-1111-2222-3333-444455556666/scratch"))
        self.assertEqual([], r.findings(r.neutralise(b"MachineId=" + b"ab12" * 8 + b" 192.168.7.21")))
        url = b"data?UserID=" + b"cd34" * 8 + b"-000003e8%7C%7C" + b"cd34" * 8 + b"&App=x"
        r.harvest(url)
        out = r.neutralise(url)
        self.assertEqual(len(url), len(out))
        self.assertNotIn(b"cd34", out)
        self.assertEqual([], r.findings(out))


class Fixing(unittest.TestCase):
    def test_same_length_replacement_keeps_sizes(self):
        r = rules()
        data = b"\x05\x00" + (HOME + "/a.fbx").encode() + b"\x00" + (HOME + "/b").encode("utf-16-le")
        out = r.neutralise(data)
        self.assertEqual(len(data), len(out))
        self.assertEqual([], r.findings(out))
        self.assertEqual(len(NAME), len(scrub.neutral_name(NAME)))

    def test_text_becomes_relative(self):
        r = rules()
        base = scrub.RELATIVE_JSON_ROOT
        src = ('{"file": "%s/%sProps/_build/Props.blend", "log": "%s/Work/QA/run.log", "root": "%s"}' % (REPO, base, HOME, REPO)).encode()
        out = scrub.relative_text(base + "Props/_build/validation.json", src, r).decode()
        self.assertIn('"file": "Props.blend"', out)
        self.assertIn('"log": "~/Work/QA/run.log"', out)
        self.assertIn('"root": "<repo>"', out)
        out = scrub.relative_text("DinkRemasterUE/Docs/note.md", ("see %s/tools/blender/x.py." % REPO).encode(), r)
        self.assertEqual(b"see tools/blender/x.py.", out)

    def test_script_derives_its_paths(self):
        r = rules()
        src = ("import json\nfrom pathlib import Path\nROOT=Path('%s/DinkRemasterUE')\nQA=Path('%s/Work/QA')\n"
               "sys.path.insert(0,'%s/tools/blender')\n" % (REPO, HOME, REPO)).encode()
        out = scrub.python_text("DinkRemasterUE/SourceAssets/Art/X/Tools/build.py", src, r).decode()
        self.assertNotIn(NAME, out)
        self.assertIn("ROOT=Path(Path(__file__).resolve().parents[4])", out)
        self.assertIn("QA=Path(Path.home()/'Work/QA')", out)
        self.assertIn("sys.path.insert(0,str(Path(__file__).resolve().parents[5]/'tools/blender'))", out)
        compile(out, "build.py", "exec")

    def test_script_text_inside_a_longer_string_is_not_turned_into_code(self):
        r = rules()
        src = ("from pathlib import Path\ncmd = \"py exec(open('%s/Work/QA/read.py').read())\"\n# see %s/notes\n" % (HOME, HOME)).encode()
        self.assertEqual(src, scrub.python_text("DinkRemasterUE/Docs/x.py", src, r))
        out = r.neutralise(src)
        self.assertEqual(len(src), len(out))
        self.assertEqual([], r.findings(out))

    def test_png_text_chunks_are_cleaned_and_pixels_kept(self):
        r = rules()
        text = ("File\0" + HOME + "/render.blend").encode()
        packed = b"Comment\0\0" + zlib.compress(("made in " + HOME).encode())
        data, idat = png([(b"tEXt", text), (b"zTXt", packed)])
        self.assertTrue(any(r.findings(v) for v in scrub.binary_views("a.png", data)))
        out = scrub.binary_fix(data, r)
        self.assertFalse(any(r.findings(v) for v in scrub.binary_views("a.png", out)))
        chunks = list(scrub.png_chunks(out))
        self.assertEqual(idat, [b for k, b in chunks if k == b"IDAT"][0])
        self.assertEqual(len(text), len([b for k, b in chunks if k == b"tEXt"][0]))
        p = 8
        while p < len(out):                      # every CRC is right
            n, kind = struct.unpack(">I4s", out[p:p + 8])
            self.assertEqual(zlib.crc32(out[p + 4:p + 8 + n]) & 0xFFFFFFFF, struct.unpack(">I", out[p + 8 + n:p + 12 + n])[0])
            p += 12 + n

    def test_jpeg_metadata_segment_is_dropped(self):
        r = rules()
        com = ("made in " + HOME).encode()
        keep = b"\xff\xdb" + struct.pack(">H", 4) + b"\x00\x01"
        data = b"\xff\xd8" + b"\xff\xfe" + struct.pack(">H", len(com) + 2) + com + keep + b"\xff\xda\x00\x02" + b"\x11\x22\xff\xd9"
        out = scrub.binary_fix(data, r)
        self.assertEqual(b"\xff\xd8" + keep + b"\xff\xda\x00\x02" + b"\x11\x22\xff\xd9", out)

    @unittest.skipIf(scrub.zstd is None, "needs Python 3.14 for zstd")
    def test_zstd_file_keeps_its_frames_and_seek_table(self):
        r = rules()
        frames = [b"BLENDER-v500" + (HOME + "/a.blend").encode() + b"\0" * 64, b"tail " + HOME.encode() + b"\0" * 32]
        data = scrub.zstd_pack(frames, True)
        self.assertIsNotNone(scrub.zstd_frames(data))
        out = scrub.binary_fix(data, r)
        got, seekable = scrub.zstd_unpack(out)
        self.assertTrue(seekable)
        self.assertEqual([len(f) for f in frames], [len(f) for f in got])
        self.assertEqual([], r.findings(b"".join(got)))

    def test_fix_updates_recorded_hashes(self):
        import hashlib
        r = rules()
        with tempfile.TemporaryDirectory() as root:
            a = ("log from %s/Work/QA\n" % HOME).encode()
            Path(root, "a.log").write_bytes(a)
            b = ('{"a.log": "%s"}\n' % hashlib.sha256(a).hexdigest()).encode()
            Path(root, "b.json").write_bytes(b)
            Path(root, "c.json").write_bytes(('{"b": "%s"}\n' % hashlib.sha256(b).hexdigest()).encode())
            names = scrub.tracked_files(root, None)
            hits = scrub.scan(root, names, r)
            self.assertEqual(["a.log"], sorted(hits))
            scrub.fix(root, names, r, hits)
            a2 = Path(root, "a.log").read_bytes()
            b2 = Path(root, "b.json").read_bytes()
            c2 = Path(root, "c.json").read_bytes()
            self.assertEqual(len(a), len(a2))                       # pinned text: same length
            self.assertIn(hashlib.sha256(a2).hexdigest().encode(), b2)
            self.assertIn(hashlib.sha256(b2).hexdigest().encode(), c2)
            self.assertEqual({}, scrub.scan(root, names, r))


if __name__ == "__main__":
    unittest.main()
