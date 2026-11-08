import hashlib
import os
from unittest import mock
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lfs_inventory import inventory, pointer_metadata


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        excluded = {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_COMMON_DIR', 'GIT_NAMESPACE'}
        isolated = {k: v for k, v in os.environ.items() if k not in excluded}
        patcher = mock.patch.dict(os.environ, isolated, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)

    def stage(self, name, data):
        oid = subprocess.check_output(['git', 'hash-object', '-w', '--stdin'], cwd=self.root, input=data).strip()
        subprocess.run(['git', 'update-index', '--add', '--cacheinfo', '100644', oid.decode(), name], cwd=self.root, check=True)

    def test_expected_hash_comes_from_index_despite_modified_working_bytes(self):
        raw = b'reviewed Blender bytes'
        digest = hashlib.sha256(raw).hexdigest()
        pointer = f'version https://git-lfs.github.com/spec/v1\noid sha256:{digest}\nsize {len(raw)}\n'.encode()
        self.stage('Art/mesh.blend', pointer)
        (self.root/'Art').mkdir()
        (self.root/'Art/mesh.blend').write_bytes(b'locally changed')
        self.assertEqual(inventory(self.root), {'Art/mesh.blend': {'sha256': digest, 'size': len(raw)}})

    def test_duplicate_objects_and_space_paths_keep_separate_assets(self):
        pointer = b'version https://git-lfs.github.com/spec/v1\noid sha256:' + b'a'*64 + b'\nsize 17\n'
        self.stage('Art/one mesh.fbx', pointer)
        self.stage('Art/second.fbx', pointer)
        self.assertEqual(set(inventory(self.root)), {'Art/one mesh.fbx', 'Art/second.fbx'})

    def test_raw_binary_is_rejected_instead_of_silently_accepting_non_lfs(self):
        self.stage('Art/untracked-storage.png', b'raw image bytes')
        with self.assertRaisesRegex(ValueError, 'Git LFS'):
            inventory(self.root)

    def test_noncanonical_pointer_is_not_binary_content_proof(self):
        self.assertIsNone(pointer_metadata(b'version https://git-lfs.github.com/spec/v1\noid sha256:no\nsize 17\n'))
        self.assertIsNone(pointer_metadata(b'actual binary asset'))


if __name__ == '__main__':
    unittest.main()
