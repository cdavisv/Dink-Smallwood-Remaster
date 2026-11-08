"""Synthetic source/publication fixtures: no Unreal, Blender, LFS or external files."""
import importlib.util
import json
from pathlib import Path
import shutil
import contextlib
import hashlib
import io
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent if HERE.name == 'tests' else HERE
spec = importlib.util.spec_from_file_location('underfloor_pub', SCRIPTS / 'publish_underfloor_surface.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / p.SOURCE_REL
        self.source.mkdir(parents=True)
        # Synthetic raw bytes deliberately require neither LFS hydration nor Blender.
        (self.source/'UnderfloorV1.blend').write_bytes(b'unit-test-blend-source')
        (self.source/'SM_Underfloor_Stonebrook_V1.fbx').write_bytes(b'unit-test-fbx-source')
        bindings = [{'name': 'Floor%02d' % i, 'world_cm': [float(i), 0., 0.],
                     'rotation_deg': [0., 0., 0.], 'scale': [1., 1., 1.]} for i in range(56)]
        signature = hashlib.sha256(json.dumps(bindings,sort_keys=True,separators=(',', ':')).encode()).hexdigest()
        plan = {'dimensions_m': [14., 13., .02], 'floor_bindings': bindings,
                'floor_transform_signature_sha256': signature}
        element = {'name':'StartingHouseUnderfloorV1','mesh':p.DEST+'.'+p.DEST.rsplit('/',1)[1],
                   'world_cm':[0.,0.,-18.], 'rotation_deg':[0.,0.,0.], 'scale':[1.,1.,1.],
                   'collision':False,'camera_occluder':False}
        material = {'schema':'dink-underfloor-asset/1','proposed_native_package':p.DEST,
                    'source_geometry':{'triangles':44,'source_UCX_count':0},
                    'proposed_runtime_element':element}
        context = {'schema':'dink-art/1','screen':1,
                   'context':{'visibility':'owner_screen_only','render_only':True},
                   'assets':[{'mesh':element['mesh'],'expected_size_cm':[1400.,1300.,2.],
                              'expected_lods':1,'bounds_tolerance_cm':1}], 'elements':[element]}
        for name, document in [('underfloor_plan.json',plan),('asset_manifest.json',material),
                               ('stonebrook_underfloor_v1.context.draft.json',context)]:
            (self.source/name).write_text(json.dumps(document))
        handoff = {'files':{f.name:p.sha(f) for f in self.source.iterdir()}}
        (self.source/'source_handoff.json').write_text(json.dumps(handoff))
        # Only in-memory test configuration changes; production has no override hook.
        pin = mock.patch.object(p,'HANDOFF_SHA',p.sha(self.source/'source_handoff.json'))
        pin.start()
        self.addCleanup(pin.stop)
        scripts = self.root / 'Scripts'
        scripts.mkdir()
        for name in ('import_underfloor_surface.py', 'publish_underfloor_surface.py'):
            shutil.copyfile(SCRIPTS / name, scripts / name)
        plan = json.loads((self.source / 'underfloor_plan.json').read_text())
        data = self.root / 'Content/Dink/Data/Art'
        data.mkdir(parents=True)
        self.house = data / 'stonebrook.json'
        rows = [dict(row, mesh='/Game/Refined/SM_Floor_Oak_2m_01.SM_Floor_Oak_2m_01') for row in plan['floor_bindings']]
        self.house.write_text(json.dumps({'elements': rows}))
        (data / 'stonebrook_vista_v4.json').write_text('{"protected":359}')
        for relative in p.PACKAGES:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'fixture-package-' + relative.encode())
        old = self.root / 'Content/Dink/Old.uasset'
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_bytes(b'protected-old-asset')
        report = {'passed': True, 'mode': 'verify', 'project': str(self.root),
                  'protected_changes': [], 'runtime_data_changes': [],
                  'source_handoff_sha256': p.sha(self.source / 'source_handoff.json'),
                  'importer_sha256': p.sha(scripts / 'import_underfloor_surface.py'),
                  'publisher_sha256': p.sha(scripts / 'publish_underfloor_surface.py'),
                  'saved_package_sha256': {r: p.sha(self.root / r) for r in p.PACKAGES},
                  'all_asset_sha256': p.asset_pins(self.root), 'runtime_data_sha256': p.data_pins(self.root)}
        self.verify = self.root / 'verification.json'
        self.verify.write_text(json.dumps(report))

    def check(self):
        return p.check_publication(self.root, self.verify)

    def cli(self, apply=False):
        argv = ['publish_underfloor_surface.py', '--project', str(self.root), '--verification', str(self.verify)]
        if apply:
            argv.append('--apply')
        with mock.patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
            p.main()
        return 0

    def test_check_only_no_content_writes(self):
        before = {str(f.relative_to(self.root)): p.sha(f) for f in (self.root/'Content').rglob('*') if f.is_file()}
        self.assertEqual(self.cli(), 0)
        self.assertEqual(before, {str(f.relative_to(self.root)): p.sha(f) for f in (self.root/'Content').rglob('*') if f.is_file()})

    def test_apply_idempotence_and_dryrun_preserves_receipt(self):
        self.assertEqual(self.cli(True), 0)
        receipt = self.root / 'Saved/Art/underfloor_surface_publication.json'
        before = receipt.read_bytes()
        self.assertEqual(self.cli(), 0)
        self.assertEqual(receipt.read_bytes(), before)
        self.assertTrue(self.check()[2])
        self.assertEqual(self.cli(True), 0)

    def test_source_fbx_tamper(self):
        (self.source/'SM_Underfloor_Stonebrook_V1.fbx').write_bytes(b'tampered')
        with self.assertRaises(AssertionError): self.check()

    def test_source_blend_tamper(self):
        (self.source/'UnderfloorV1.blend').write_bytes(b'tampered')
        with self.assertRaises(AssertionError): self.check()

    def test_plan_tamper(self):
        (self.source/'underfloor_plan.json').write_text('{}')
        with self.assertRaises(AssertionError): self.check()

    def test_transform_drift(self):
        doc = json.loads(self.house.read_text()); doc['elements'][0]['world_cm'][0] += 1
        self.house.write_text(json.dumps(doc))
        with self.assertRaises(AssertionError): self.check()

    def test_existing_and_new_asset_drift(self):
        for relative in ['Content/Dink/Old.uasset', *p.PACKAGES]:
            path = self.root/relative; old=path.read_bytes(); path.write_bytes(b'drift')
            with self.assertRaises(AssertionError): self.check()
            path.write_bytes(old)

    def test_data_added_deleted_changed(self):
        path=self.house.with_name('foreign.json');path.write_text('{}')
        with self.assertRaises(AssertionError): self.check()
        path.unlink()
        path=self.house.with_name('stonebrook_vista_v4.json'); old=path.read_bytes();path.write_text('{}')
        with self.assertRaises(AssertionError): self.check()
        path.unlink()
        with self.assertRaises(AssertionError): self.check()
        path.write_bytes(old)
        self.check()

    def test_foreign_context_refused(self):
        (self.root/p.CONTEXT).write_text('{}')
        with self.assertRaises(AssertionError): self.check()

    def test_published_context_drift_refused(self):
        self.assertEqual(self.cli(True),0)
        (self.root/p.CONTEXT).write_text('{}')
        with self.assertRaises(AssertionError): self.check()

    def test_fresh_published_verification_without_local_receipt(self):
        self.assertEqual(self.cli(True),0)
        (self.root/'Saved/Art/underfloor_surface_publication.json').unlink()
        report=json.loads(self.verify.read_text())
        report['runtime_data_sha256']=p.data_pins(self.root)
        self.verify.write_text(json.dumps(report))
        self.assertTrue(self.check()[2])
        self.assertEqual(self.cli(),0)
        self.assertEqual(self.cli(True),0)

    def test_fresh_published_verification_rejects_wrong_payload(self):
        (self.root/p.CONTEXT).write_text('{}')
        report=json.loads(self.verify.read_text())
        report['runtime_data_sha256']=p.data_pins(self.root)
        self.verify.write_text(json.dumps(report))
        with self.assertRaises(AssertionError): self.check()

    def test_verification_replaced_refused_after_apply(self):
        self.assertEqual(self.cli(True),0)
        self.verify.write_text(self.verify.read_text()+'\n')
        with self.assertRaises(AssertionError): self.check()


if __name__ == '__main__':
    unittest.main()
