"""Actual CLI regression: ordinary JSON/text cannot masquerade as LFS metadata.

All files and Git operations live in an isolated TemporaryDirectory; neither the
source checkout nor any shared index/object database is modified.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pointer(data, *, size=None, oid=None):
    return ("version https://git-lfs.github.com/spec/v1\noid sha256:" +
            (digest(data) if oid is None else oid) + "\nsize " +
            str(len(data) if size is None else size) + "\n").encode("ascii")


class LFSMetadataAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dink-lfs-audit-")
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.project = self.repo / "DinkRemasterUE"
        (self.project / "Scripts").mkdir(parents=True)
        (self.repo / "tools").mkdir()
        (self.repo / "bin/dink").mkdir(parents=True)
        # Do not inherit an invoking process's alternate/shared Git index.
        excluded = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_NAMESPACE"}
        self.env = {k: v for k, v in os.environ.items() if k not in excluded}
        self.git("init", "-q", str(self.repo))
        for name in ("verify_sources.py", "lfs_inventory.py", "remaster_paths.py"):
            shutil.copy2(SCRIPTS / name, self.project / "Scripts" / name)
        self.binary_path = "Content/test.uasset"
        self.binary = b"reviewed binary asset"
        self.stage(self.binary_path, pointer(self.binary))
        self.write(self.binary_path, self.binary)
        self.ledger = {self.binary_path: digest(self.binary)}
        self.add_plain_source("SourceAssets/source.json", b'{"approved":"source metadata"}\n')
        # Minimal supporting data allows the real audit CLI to run all its normal
        # syntax/layout/audio checks; it is not a game-content verification fixture.
        selection = {"runtime": {}, "counts": {"sfx": 44, "music": 28, "rejected": 4}}
        self.write("SourceAssets/Audio/selection_manifest.json", json.dumps(selection).encode())
        self.write("Content/Dink/Data/Audio/approved.json", b"{}")

    def git(self, *args, data=None):
        return subprocess.check_output(["git", *args], cwd=self.repo, env=self.env, input=data)

    def stage(self, name, data):
        oid = self.git("hash-object", "-w", "--stdin", data=data).decode().strip()
        self.git("update-index", "--add", "--cacheinfo", "100644", oid, "DinkRemasterUE/" + name)

    def write(self, name, data):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def write_ledger(self):
        with (self.project / "SourceAssets/asset_ledger.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["asset_path", "sha256"])
            writer.writeheader()
            writer.writerows({"asset_path": p, "sha256": h} for p, h in self.ledger.items())

    def add_plain_source(self, name, data):
        self.stage(name, data)  # Raw ordinary text in the index, deliberately not LFS.
        self.write(name, data)
        self.ledger[name] = digest(data)
        self.write_ledger()

    def audit(self, metadata=True):
        command = [sys.executable, "-B", str(self.project / "Scripts/verify_sources.py")]
        if metadata:
            command.append("--metadata-only")
        result = subprocess.run(command, cwd=self.project, env=self.env, capture_output=True, text=True)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return result.returncode, json.loads(result.stdout)

    def assert_rejected(self, name, metadata=True):
        code, report = self.audit(metadata)
        self.assertNotEqual(code, 0, report)
        self.assertFalse(report["passed"], report)
        self.assertIn({"asset_hash_mismatch": name}, report["errors"])

    def test_metadata_rejects_non_lfs_json_masquerade(self):
        self.assertEqual(self.audit()[0], 0)
        name = "SourceAssets/source.json"
        original = (self.project / name).read_bytes()
        self.write(name, pointer(original))
        self.assert_rejected(name)

    def test_metadata_rejects_non_lfs_text_masquerade(self):
        name = "SourceAssets/notes.txt"
        original = b"reviewed ordinary text\n"
        self.add_plain_source(name, original)
        self.assertEqual(self.audit()[0], 0)
        self.write(name, pointer(original))
        self.assert_rejected(name)

    def test_metadata_accepts_exact_real_indexed_pointer(self):
        self.write(self.binary_path, pointer(self.binary))
        code, report = self.audit()
        self.assertEqual(code, 0, report)
        self.assertTrue(report["passed"])
        self.assertEqual(report["binary_files_metadata_only"], 1)

    def test_metadata_rejects_pointer_size_mismatch(self):
        self.write(self.binary_path, pointer(self.binary, size=len(self.binary) + 1))
        self.assert_rejected(self.binary_path)

    def test_metadata_requires_indexed_oid_and_ledger_sha_to_agree(self):
        self.write(self.binary_path, pointer(self.binary))
        self.ledger[self.binary_path] = digest(b"a different asset")
        self.write_ledger()
        self.assert_rejected(self.binary_path)

    def test_full_default_still_requires_actual_binary_contents(self):
        self.write(self.binary_path, pointer(self.binary))
        self.assertEqual(self.audit()[0], 0)
        self.assert_rejected(self.binary_path, metadata=False)

    def test_metadata_accepts_explicit_lfs_diagnostics_in_nested_project(self):
        attrs = b'DinkRemasterUE/SourceAssets/diagnostics/* filter=lfs\n'
        oid = self.git('hash-object', '-w', '--stdin', data=attrs).decode().strip()
        self.git('update-index', '--add', '--cacheinfo', '100644', oid, '.gitattributes')
        for suffix in ['bin', 'json.gz', 'json']:
            name = 'SourceAssets/diagnostics/report.' + suffix
            data = ('reviewed diagnostic ' + suffix).encode()
            self.stage(name, pointer(data))
            self.write(name, pointer(data))
            self.ledger[name] = digest(data)
        self.write_ledger()
        code, report = self.audit()
        self.assertEqual(code, 0, report)
        self.assertEqual(report['binary_files_metadata_only'], 3)

    def test_worktree_attributes_cannot_promote_ordinary_source_pointer(self):
        (self.repo/'.gitattributes').write_text('DinkRemasterUE/SourceAssets/source.json filter=lfs\n')
        name = 'SourceAssets/source.json'
        original = (self.project/name).read_bytes()
        self.write(name, pointer(original))
        self.assert_rejected(name)


if __name__ == "__main__":
    unittest.main()
