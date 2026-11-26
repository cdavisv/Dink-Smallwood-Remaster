"""A9 (25 Nov 2026): the kit importer's reimport stamp is the source file's content, not its mtime (Scripts/kit_stamp.py)."""
import hashlib
import importlib.util
import os
import re
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('kit_stamp', str(PROJECT / 'Scripts/kit_stamp.py'))
kit_stamp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kit_stamp)


def fake_package(path, md5):
    path.write_bytes(b'\x00junk[{ "RelativeFilename" : "../x.fbx", "Timestamp" : "1794882825", "FileMD5" : "%s", '
                     b'"DisplayLabelName" : "" }]\x00' % md5.encode())


class KitStampTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        self.fbx = self.root / 'SM_X.fbx'
        self.fbx.write_bytes(b'fbx body ' * 100)
        self.md5 = hashlib.md5(self.fbx.read_bytes()).hexdigest()
        self.pkg = self.root / 'SM_X.uasset'

    def tearDown(self):
        self.dir.cleanup()

    def test_stamp_is_the_content_md5_with_the_suffix(self):
        self.assertEqual(kit_stamp.stamp(self.fbx, 'town2'), 'md5:%s:town2' % self.md5)
        self.assertEqual(kit_stamp.stamp(self.fbx), 'md5:' + self.md5)

    def test_a_new_mtime_is_not_a_change(self):
        tag = kit_stamp.stamp(self.fbx, 'town2')
        os.utime(self.fbx, (1, 1))
        self.assertEqual(kit_stamp.status(tag, self.fbx, self.pkg, 'town2'), 'current')

    def test_new_content_is_a_change(self):
        tag = kit_stamp.stamp(self.fbx, 'town2')
        data = bytearray(self.fbx.read_bytes())
        data[3] ^= 1  # same size, one bit
        self.fbx.write_bytes(bytes(data))
        self.assertIsNone(kit_stamp.status(tag, self.fbx, self.pkg, 'town2'))

    def test_another_importer_version_is_a_change(self):
        self.assertIsNone(kit_stamp.status(kit_stamp.stamp(self.fbx, 'town1'), self.fbx, self.pkg, 'town2'))

    def test_legacy_tag_holds_when_unreal_recorded_the_same_md5(self):
        size = self.fbx.stat().st_size
        fake_package(self.pkg, self.md5)
        self.assertEqual(kit_stamp.status('%d:1794882825:town2' % size, self.fbx, self.pkg, 'town2'), 'legacy')
        self.assertEqual(kit_stamp.status('%d:1794882825' % size, self.fbx, self.pkg), 'legacy')

    def test_legacy_tag_reimports_on_other_md5_size_or_suffix(self):
        size = self.fbx.stat().st_size
        fake_package(self.pkg, '0' * 32)
        self.assertIsNone(kit_stamp.status('%d:1:town2' % size, self.fbx, self.pkg, 'town2'))
        fake_package(self.pkg, self.md5)
        self.assertIsNone(kit_stamp.status('%d:1:town2' % (size + 1), self.fbx, self.pkg, 'town2'))
        self.assertIsNone(kit_stamp.status('%d:1:town1' % size, self.fbx, self.pkg, 'town2'))
        self.assertIsNone(kit_stamp.status('%d:1:town2' % size, self.fbx, self.root / 'missing.uasset', 'town2'))
        self.assertIsNone(kit_stamp.status('', self.fbx, self.pkg, 'town2'))

    def test_package_file(self):
        self.assertEqual(kit_stamp.package_file('/p', '/Game/Dink/Photoreal/Corpses/SM_A.SM_A'),
                         Path('/p/Content/Dink/Photoreal/Corpses/SM_A.uasset'))
        with self.assertRaises(ValueError):
            kit_stamp.package_file('/p', '/Engine/X')

    def test_master_corpse_packages_hold_without_a_reimport(self):
        """Every committed corpse mesh (legacy stamps of the 16 Nov import) counts as unchanged in this checkout."""
        kit = PROJECT / 'SourceAssets/Art/PhotorealPass/Corpses'
        import json
        rows = json.loads((kit / 'manifest.json').read_text())['assets']
        checked = 0
        for row in rows:
            pkg = kit_stamp.package_file(PROJECT, '/Game/Dink/Photoreal/Corpses/' + row['name'])
            fbx = PROJECT.parent / row['fbx'] if str(row['fbx']).startswith('DinkRemasterUE/') else kit / row['fbx']
            if not pkg.exists() or pkg.read_bytes()[:40].startswith(b'version https://git-lfs'):
                continue  # LFS pointer checkout: nothing to read
            tags = re.findall(rb'(md5:[0-9a-f]{32}:town2|\d+:\d+:town2)', pkg.read_bytes())
            self.assertTrue(tags, row['name'])
            self.assertIsNotNone(kit_stamp.status(tags[0].decode(), fbx, pkg, 'town2'), row['name'] + ' would be re-imported')
            checked += 1
        if not checked:
            self.skipTest('LFS pointers only')

    def test_corpse_lods_restored_where_bounds_hold(self):
        """A9: the corpse meshes that lost their A200 LODs at the 16 Nov kit import carry generated LODs again (add_kit_lods.py,
        DINK_KIT_LODS_STRICT=1: only where the bounds move 0.5 cm or less); the Maiden, the Mother and Dink's body keep one LOD."""
        corpses = PROJECT / 'Content/Dink/Photoreal/Corpses'
        lods = {'Girl', 'Merchant', 'Merchant_Green', 'Mother_Joppa', 'Peasant', 'Soldier', 'Knight'}
        for name in sorted(lods | {'Maiden', 'Mother'}):
            pkg = corpses / ('SM_Corpse_%s_PR.uasset' % name)
            data = pkg.read_bytes()
            if data[:40].startswith(b'version https://git-lfs'):
                self.skipTest('LFS pointers only')
            tag = re.findall(rb'kitlods1:[0-9]+:[0-9.,]+:[0-9,]+(:single)?', data)
            if name in lods:
                self.assertTrue(tag and not tag[0], name + ' has its generated LODs')
            else:
                self.assertFalse(tag and not tag[0], name + ' keeps one LOD (generated LODs would move its bounds)')


if __name__ == '__main__':
    unittest.main()
