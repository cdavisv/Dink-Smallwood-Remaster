import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap_asset_pack as pack


def sha(data):
    return hashlib.sha256(data).hexdigest()


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "Project"
        self.root.mkdir()
        self.counter = 0

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, entries):
        self.counter += 1
        path = self.base / ("pack%d.tar.gz" % self.counter)
        with tarfile.open(path, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            for name, data, kind, pax in entries:
                member = tarfile.TarInfo(name)
                member.type = kind
                member.size = len(data) if kind in (tarfile.REGTYPE, tarfile.AREGTYPE) else 0
                member.pax_headers = pax
                if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                    member.linkname = "../outside"
                archive.addfile(member, io.BytesIO(data) if member.size else None)
        return path

    def fixture(self, files, entries=None):
        if entries is None:
            entries = [(p, data, tarfile.REGTYPE, {}) for p, data in files.items()]
        archive = self.archive(entries)
        data = archive.read_bytes()
        manifest = {"schema": pack.SCHEMA, "url": "https://example.invalid/assets.tar.gz",
                    "sha256": sha(data), "size": len(data),
                    "files": [{"path": p, "sha256": sha(payload), "size": len(payload)}
                              for p, payload in files.items()]}
        return manifest, archive

    def pointer(self, manifest, name):
        entry = next(r for r in manifest["files"] if r["path"] == name)
        return pack.Asset(name, entry["sha256"], entry["size"]).pointer()

    def write(self, name, data):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def asset_snapshot(self):
        return {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.root.rglob("*") if p.is_file() and p.relative_to(self.root).parts[0] != "Saved"}

    def test_valid_missing_pointer_current_and_idempotence(self):
        files = {"Content/a.uasset": b"asset A", "SourceAssets/b.blend": b"asset B",
                 "Content/c.uasset": b"already hydrated"}
        manifest, archive = self.fixture(files)
        self.write("Content/a.uasset", self.pointer(manifest, "Content/a.uasset"))
        current = self.write("Content/c.uasset", files["Content/c.uasset"])
        before = current.stat().st_mtime_ns
        result = pack.bootstrap(manifest, self.root, archive)
        self.assertEqual((result.verified_files, result.installed_files, result.already_current), (3, 2, 1))
        self.assertEqual(current.stat().st_mtime_ns, before)
        for name, data in files.items():
            self.assertEqual((self.root / name).read_bytes(), data)
        snapshot = self.asset_snapshot()
        result = pack.bootstrap(manifest, self.root, archive)
        self.assertEqual(result.installed_files, 0)
        self.assertEqual(self.asset_snapshot(), snapshot)

    def test_verify_only_leaves_assets_and_missing_directories_untouched(self):
        files = {"Content/a.uasset": b"A", "Missing/deep/b.blend": b"B"}
        manifest, archive = self.fixture(files)
        self.write("Content/a.uasset", self.pointer(manifest, "Content/a.uasset"))
        before = self.asset_snapshot()
        result = pack.bootstrap(manifest, self.root, archive, verify_only=True)
        self.assertEqual(result.require_hydration, 2)
        self.assertEqual(result.installed_files, 0)
        self.assertEqual(self.asset_snapshot(), before)
        self.assertFalse((self.root / "Missing").exists())
        self.assertTrue((self.root / "Saved/AssetPacks").is_dir())

    def test_tampered_archive_rejected_before_tar_parse(self):
        manifest, archive = self.fixture({"Content/a": b"A"})
        raw = bytearray(archive.read_bytes())
        raw[len(raw) // 2] ^= 1
        archive.write_bytes(raw)
        with mock.patch.object(pack, "_read_pack") as read:
            with self.assertRaisesRegex(pack.AssetPackError, "archive SHA-256"):
                pack.bootstrap(manifest, self.root, archive)
            read.assert_not_called()
        self.assertFalse((self.root / "Content").exists())

    def test_wrong_archive_size_rejected_before_tar_parse(self):
        manifest, archive = self.fixture({"Content/a": b"A"})
        manifest["size"] += 1
        with mock.patch.object(pack, "_read_pack") as read:
            with self.assertRaisesRegex(pack.AssetPackError, "archive SHA-256"):
                pack.bootstrap(manifest, self.root, archive)
            read.assert_not_called()

    def test_traversal_absolute_and_backslash_members_refused(self):
        for path in ("../escaped", "/absolute", "Content/../../escaped", "Content\\..\\escaped"):
            with self.subTest(path=path):
                manifest, archive = self.fixture({"Content/a": b"A"}, [(path, b"A", tarfile.REGTYPE, {})])
                with self.assertRaises(pack.AssetPackError):
                    pack.bootstrap(manifest, self.root, archive)
                self.assertFalse((self.base / "escaped").exists())
                self.assertFalse((self.root / "Content").exists())

    def test_pax_final_path_is_validated(self):
        manifest, archive = self.fixture({"Content/a": b"A"},
                                         [("safe", b"A", tarfile.REGTYPE, {"path": "../escaped"})])
        with self.assertRaises(pack.AssetPackError):
            pack.bootstrap(manifest, self.root, archive)
        self.assertFalse((self.base / "escaped").exists())

    def test_long_pax_filename_hydrates(self):
        path = "SourceAssets/" + "/".join(["long_component_" + "a" * 40] * 6) + "/image.bin"
        manifest, archive = self.fixture({path: b"long path asset"})
        self.assertEqual(pack.bootstrap(manifest, self.root, archive).installed_files, 1)
        self.assertEqual((self.root / path).read_bytes(), b"long path asset")

    def test_duplicate_archive_entries_refused_without_partial_install(self):
        entries = [("Content/a", b"A", tarfile.REGTYPE, {})] * 2
        manifest, archive = self.fixture({"Content/a": b"A"}, entries)
        pointer = self.pointer(manifest, "Content/a")
        self.write("Content/a", pointer)
        with self.assertRaisesRegex(pack.AssetPackError, "duplicate"):
            pack.bootstrap(manifest, self.root, archive)
        self.assertEqual((self.root / "Content/a").read_bytes(), pointer)

    def test_unexpected_and_missing_entries_refused(self):
        for entries, message in [
            ([("Content/a", b"A", tarfile.REGTYPE, {}), ("extra", b"x", tarfile.REGTYPE, {})], "unexpected"),
            ([("Content/a", b"A", tarfile.REGTYPE, {})], "missing")
        ]:
            with self.subTest(message=message):
                manifest, archive = self.fixture({"Content/a": b"A", "Content/b": b"B"}, entries)
                with self.assertRaisesRegex(pack.AssetPackError, message):
                    pack.bootstrap(manifest, self.root, archive)
                self.assertFalse((self.root / "Content").exists())

    def test_links_directories_devices_and_fifo_refused(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind):
                manifest, archive = self.fixture({"Content/a": b""}, [("Content/a", b"", kind, {})])
                with self.assertRaisesRegex(pack.AssetPackError, "nonregular"):
                    pack.bootstrap(manifest, self.root, archive)
                self.assertFalse((self.root / "Content").exists())

    def test_file_digest_and_declared_size_checked_inside_pinned_archive(self):
        for payload, message in [(b"EVIL", "SHA-256"), (b"wrong size", "size mismatch")]:
            with self.subTest(payload=payload):
                manifest, archive = self.fixture({"Content/a": b"GOOD"}, [("Content/a", payload, tarfile.REGTYPE, {})])
                with self.assertRaisesRegex(pack.AssetPackError, message):
                    pack.bootstrap(manifest, self.root, archive)
                self.assertFalse((self.root / "Content").exists())

    def test_modified_asset_refused_before_any_install(self):
        manifest, archive = self.fixture({"Content/a": b"A", "Content/z": b"Z"})
        pointer = self.pointer(manifest, "Content/a")
        self.write("Content/a", pointer)
        self.write("Content/z", b"foreign edit")
        with self.assertRaisesRegex(pack.AssetPackError, "modified asset"):
            pack.bootstrap(manifest, self.root, archive)
        self.assertEqual((self.root / "Content/a").read_bytes(), pointer)
        self.assertEqual((self.root / "Content/z").read_bytes(), b"foreign edit")

    def test_wrong_lfs_pointer_refused(self):
        manifest, archive = self.fixture({"Content/a": b"A"})
        bad = self.pointer(manifest, "Content/a").replace(manifest["files"][0]["sha256"].encode(), b"0" * 64)
        self.write("Content/a", bad)
        with self.assertRaisesRegex(pack.AssetPackError, "modified asset"):
            pack.bootstrap(manifest, self.root, archive)
        self.assertEqual((self.root / "Content/a").read_bytes(), bad)

    def test_modification_during_staging_refused_before_any_install(self):
        manifest, archive = self.fixture({"Content/a": b"A", "Content/z": b"Z"})
        pointer = self.pointer(manifest, "Content/a")
        self.write("Content/a", pointer)
        real = pack._read_pack
        def changed(*args, **kwargs):
            result = real(*args, **kwargs)
            self.write("Content/z", b"changed during verification")
            return result
        with mock.patch.object(pack, "_read_pack", side_effect=changed):
            with self.assertRaisesRegex(pack.AssetPackError, "modified asset"):
                pack.bootstrap(manifest, self.root, archive)
        self.assertEqual((self.root / "Content/a").read_bytes(), pointer)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlink_parent_leaf_and_cache_refused(self):
        for location in ("parent", "leaf", "cache"):
            with self.subTest(location=location):
                root = self.base / location
                root.mkdir()
                outside = self.base / (location + "-outside")
                outside.mkdir()
                marker = outside / "a"
                marker.write_bytes(b"outside must survive")
                manifest, archive = self.fixture({"Content/a": b"A"})
                if location == "parent":
                    (root / "Content").symlink_to(outside, target_is_directory=True)
                elif location == "leaf":
                    (root / "Content").mkdir()
                    (root / "Content/a").symlink_to(marker)
                else:
                    (root / "Saved").mkdir()
                    (root / "Saved/AssetPacks").symlink_to(outside, target_is_directory=True)
                with self.assertRaisesRegex(pack.AssetPackError, "symlink"):
                    pack.bootstrap(manifest, root, archive)
                self.assertEqual(marker.read_bytes(), b"outside must survive")

    def test_manifest_alias_and_ancestor_conflicts_refused(self):
        manifest, archive = self.fixture({"Content/a": b"A"})
        for path in ("Content/a", "content/A", "Content/a/child", "../outside", "C:/outside", "Saved/AssetPacks/cache"):
            with self.subTest(path=path):
                changed = json.loads(json.dumps(manifest))
                changed["files"].append({"path": path, "sha256": sha(b"X"), "size": 1})
                with self.assertRaises(pack.AssetPackError):
                    pack.bootstrap(changed, self.root, archive)

    def test_download_is_pinned_and_cache_revalidated(self):
        manifest, archive = self.fixture({"Content/a": b"A"})
        with mock.patch.object(pack.urllib.request, "urlopen", return_value=io.BytesIO(archive.read_bytes())):
            self.assertEqual(pack.bootstrap(manifest, self.root).installed_files, 1)
        cached = self.root / "Saved/AssetPacks" / (manifest["sha256"] + ".tar.gz")
        self.assertEqual(cached.read_bytes(), archive.read_bytes())
        data = bytearray(cached.read_bytes()); data[-1] ^= 1; cached.write_bytes(data)
        with mock.patch.object(pack.urllib.request, "urlopen") as download:
            with self.assertRaises(pack.AssetPackError):
                pack.bootstrap(manifest, self.root, verify_only=True)
            download.assert_not_called()

    def test_cli_default_manifest_and_verify_only(self):
        manifest, archive = self.fixture({"Content/a": b"A"})
        config = self.root / "AssetPacks/house-v1.json"
        config.parent.mkdir(); config.write_text(json.dumps(manifest))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(pack.main(["--archive", str(archive), "--verify-only"], _project_root=self.root), 0)
        self.assertIn("1 require hydration", output.getvalue())
        self.assertFalse((self.root / "Content").exists())


if __name__ == "__main__":
    unittest.main()
