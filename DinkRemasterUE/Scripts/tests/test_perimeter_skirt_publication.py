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
spec = importlib.util.spec_from_file_location('perimeter_skirt_pub', SCRIPTS / 'publish_perimeter_skirt_surface.py')
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
        (self.source/'PerimeterSkirtV1.blend').write_bytes(b'unit-test-blend-source')
        (self.source/'SM_Stonebrook_PerimeterSkirt_V1.fbx').write_bytes(b'unit-test-fbx-source')
        bindings = [{'name': 'Floor%02d' % i, 'world_cm': [float(i), 0., 0.],
                     'rotation_deg': [0., 0., 0.], 'scale': [1., 1., 1.]} for i in range(56)]
        signature = hashlib.sha256(json.dumps(bindings,sort_keys=True,separators=(',', ':')).encode()).hexdigest()
        color={'name':'M_Stonebrook_Underfloor_DarkOak_V1','base_color_linear':[.009,.005,.0025],
               'roughness':.96,'metallic':0,'specular':.25,'opaque':True}
        plan={'dimensions_m':[14.,13.,.178],'floor_bindings':bindings,
              'floor_transform_signature_sha256':signature,'placement_world_cm':[0.,0.,-18.], 'material':color}
        element={'name':'StartingHousePerimeterSkirtV1','mesh':p.DEST+'.'+p.DEST.rsplit('/',1)[1],
                 'world_cm':plan['placement_world_cm'],'rotation_deg':[0,0,0],'scale':[1,1,1],
                 'collision':False,'camera_occluder':False}
        material={'schema':'dink-perimeter-skirt/1','proposed_package':p.DEST,'vertices':48,'triangles':96,
                  'source_UCX_count':0,'world_top_cm':-.2,'world_base_cm':-18,
                  'inside_original_floor_contour':True,'material':color,
                  'placement_world_cm':plan['placement_world_cm'],'dimensions_m':plan['dimensions_m'],
                  'files':{'SM_Stonebrook_PerimeterSkirt_V1.fbx':'test_hash_placeholder'}}
        context={'schema':'dink-art/1','screen':1,'context':{'visibility':'owner_screen_only','render_only':True},
                 'source':p.SOURCE_REL+'/asset_manifest.json',
                 'assets':[{'mesh':element['mesh'],'expected_size_cm':[1400.,1300.,17.8],
                            'expected_lods':1,'bounds_tolerance_cm':1}], 'elements':[element]}
        exported={'passed':True,'actual_native_gap_rays_replayed':7,
                  'ray_results':[{'nearest_front_facing_normal_dot_ray':-1} for _ in range(7)]}
        for name,doc in [('underfloor_plan.json',plan),('asset_manifest.json',material),
                         ('stonebrook_perimeter_skirt_v1.context.draft.json',context),('export_verification.json',exported)]:
            (self.source/name).write_text(json.dumps(doc))
        handoff = {'files':{f.name:p.sha(f) for f in self.source.iterdir()}}
        (self.source/'source_handoff.json').write_text(json.dumps(handoff))
        # Only in-memory test configuration changes; production has no override hook.
        pin = mock.patch.object(p,'HANDOFF_SHA',p.sha(self.source/'source_handoff.json'))
        pin.start()
        self.addCleanup(pin.stop)
        scripts = self.root / 'Scripts'
        scripts.mkdir()
        for name in ('import_perimeter_skirt_surface.py', 'publish_perimeter_skirt_surface.py','perimeter_fbxparse.py'):
            shutil.copyfile(SCRIPTS / name, scripts / name)
        module=self.root/'Binaries/Linux/unit.so';module.parent.mkdir(parents=True);module.write_bytes(b'synthetic DLL')
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
                  'importer_sha256': p.sha(scripts / 'import_perimeter_skirt_surface.py'),
                  'publisher_sha256': p.sha(scripts / 'publish_perimeter_skirt_surface.py'),
                  'tool_sha256':p.tool_pins(self.root),'module_sha256':p.module_pins(self.root),
                  'saved_package_sha256': {r: p.sha(self.root / r) for r in p.PACKAGES},
                  'all_asset_sha256': p.asset_pins(self.root), 'runtime_data_sha256': p.data_pins(self.root)}
        self.verify = self.root / 'verification.json'
        self.verify.write_text(json.dumps(report))

    def check(self):
        return p.check_publication(self.root, self.verify)

    def cli(self, apply=False):
        argv = ['publish_perimeter_skirt_surface.py', '--project', str(self.root), '--verification', str(self.verify)]
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
        receipt = self.root / 'Saved/Art/perimeter_skirt_surface_publication.json'
        before = receipt.read_bytes()
        self.assertEqual(self.cli(), 0)
        self.assertEqual(receipt.read_bytes(), before)
        self.assertTrue(self.check()[2])
        self.assertEqual(self.cli(True), 0)

    def test_source_fbx_tamper(self):
        (self.source/'SM_Stonebrook_PerimeterSkirt_V1.fbx').write_bytes(b'tampered')
        with self.assertRaises(AssertionError): self.check()

    def test_source_blend_tamper(self):
        (self.source/'PerimeterSkirtV1.blend').write_bytes(b'tampered')
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
        (self.root/'Saved/Art/perimeter_skirt_surface_publication.json').unlink()
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



    def test_module_drift_rejected(self):
        (self.root/'Binaries/Linux/unit.so').write_bytes(b'changed')
        with self.assertRaises(AssertionError): self.check()

    def test_parser_drift_rejected(self):
        (self.root/'Scripts/perimeter_fbxparse.py').write_text('changed')
        with self.assertRaises(AssertionError): self.check()

    def test_shared_content_symlink_rejected(self):
        outside=self.root/'outside';outside.mkdir()
        (self.root/'Content/shared').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(AssertionError): self.check()

    def test_shared_saved_symlink_rejected(self):
        outside=self.root/'outside';outside.mkdir()
        (self.root/'Saved').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(AssertionError): self.check()

    def test_material_dependency_drift_rejected(self):
        # Reused material is protected by all-asset pins, never a writable candidate.
        path=self.root/(p.MAT.replace('/Game/','Content/',1)+'.uasset')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'new or changed shared material')
        with self.assertRaises(AssertionError): self.check()


if __name__ == '__main__':
    unittest.main()
