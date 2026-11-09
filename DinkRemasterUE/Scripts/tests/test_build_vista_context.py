"""Receipt gating regression; no Blender, Unreal or repository writes required."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('reviewed_vista_context', SCRIPTS / 'build_vista_context.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class CompositionReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        base = self.root / 'SourceAssets/Art/Stonebrook/InteriorVistaV3'
        self.revision = self.root / 'SourceAssets/Art/Stonebrook/InteriorVistaV4'
        base.mkdir(parents=True)
        self.revision.mkdir(parents=True)
        self.base_scene = base / 'Stonebrook_InteriorVista_Candidate_V3.blend'
        self.base_scene.write_bytes(b'immutable base scene')
        self.scene = self.revision / 'Stonebrook_HorizonV4.blend'
        self.scene.write_bytes(b'checked editable scene')
        self.additions = self.revision / 'additions.json'
        self.receipt_path = self.revision / 'source-verification.json'
        def row(name):
            return {'name': name, 'asset_path_proposal': '/Game/Dink/Kits/Test.Test',
                    'world_cm_proposal': [1, 2, 3], 'UE_yaw_deg': 12,
                    'scale': [1, 1, 1], 'collision': False, 'camera_occluder': False}
        self.base_rows = [row('Base_%03d' % i) for i in range(316)]
        self.new_rows = [row('VistaV4_New_%02d' % i) for i in range(43)]
        self.additions.write_text(json.dumps({'base_scene_sha256': builder.sha(self.base_scene),
                                             'new_mesh_packages': 0, 'instances': self.new_rows}))
        self.receipt = {'schema': 'dink-vista-source-verification/2', 'passed': True,
                        'base_scene_sha256': builder.sha(self.base_scene),
                        'composition_scene_sha256': builder.sha(self.scene),
                        'composition_additions_sha256': builder.sha(self.additions),
                        'existing_mesh_objects': 519,
                        'existing_mesh_transform_geometry_uv_material_changes': [],
                        'new_instances': sorted(r['name'] for r in self.new_rows),
                        'new_instance_count': 43, 'new_mesh_packages': 0,
                        'checked_instances': [{'name': r['name']} for r in self.new_rows],
                        'missing_texture_references': [], 'all_texture_paths_project_relative': True}
        self.save_receipt()
        self.guard = patch.object(builder, 'validate_bundle', return_value=(
            {}, {'instances': self.base_rows}, 'pinned-v3-bundle'))
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def save_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt))

    def test_valid_scene_keeps_existing_manifest_bytes_and_provenance(self):
        actual = builder.build(self.root)
        expected_rows = []
        for index, r in enumerate(self.base_rows + self.new_rows):
            expected_rows.append({'name': 'Vista_%03d_%s' % (index, r['name']) if index < 316 else r['name'],
                                  'mesh': r['asset_path_proposal'], 'world_cm': r['world_cm_proposal'],
                                  'rotation_deg': [0, r['UE_yaw_deg'], 0], 'scale': r['scale'],
                                  'collision': False, 'camera_occluder': False})
        expected = {'schema': 'dink-art/1', 'screen': 1,
                    'context': {'visibility': 'owner_screen_only', 'render_only': True},
                    'elements': expected_rows,
                    'source_provenance': {'source_bundle_sha256': 'pinned-v3-bundle',
                        'composition_source': str(Path('SourceAssets/Art/Stonebrook/InteriorVistaV4/Stonebrook_HorizonV4.blend')),
                        'composition_scene_sha256': builder.sha(self.scene),
                        'composition_additions_sha256': builder.sha(self.additions)}}
        self.assertEqual(json.dumps(actual, indent=2), json.dumps(expected, indent=2))
        self.assertNotIn('receipt_sha256', actual['source_provenance'])

    def test_artist_scene_edit_rejects_stale_success_receipt(self):
        self.scene.write_bytes(b'artist moved one grass instance')
        with self.assertRaisesRegex(ValueError, 'stale'):
            builder.build(self.root)

    def test_addition_edit_rejects_stale_success_receipt(self):
        data = json.loads(self.additions.read_text())
        data['instances'][0]['world_cm_proposal'][0] += 100
        self.additions.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'stale'):
            builder.build(self.root)

    def test_missing_receipt_is_rejected(self):
        self.receipt_path.unlink()
        with self.assertRaisesRegex(ValueError, 'source checker'):
            builder.build(self.root)

    def test_legacy_unbound_receipt_is_rejected(self):
        self.receipt.pop('schema')
        self.save_receipt()
        with self.assertRaises(ValueError):
            builder.build(self.root)

    def test_failure_receipt_is_rejected(self):
        self.receipt['passed'] = False
        self.save_receipt()
        with self.assertRaises(ValueError):
            builder.build(self.root)

    def test_changed_baseline_receipt_is_rejected(self):
        self.receipt['base_scene_sha256'] = 'wrong'
        self.save_receipt()
        with self.assertRaisesRegex(ValueError, 'baseline'):
            builder.build(self.root)

    def test_wrong_original_inventory_is_rejected(self):
        self.receipt['existing_mesh_objects'] = 518
        self.save_receipt()
        with self.assertRaisesRegex(ValueError, 'baseline'):
            builder.build(self.root)

    def test_unchecked_addition_is_rejected(self):
        self.receipt['checked_instances'].pop()
        self.save_receipt()
        with self.assertRaisesRegex(ValueError, '43 additions'):
            builder.build(self.root)

    def test_checked_names_must_match_actual_additions(self):
        self.receipt['checked_instances'][0]['name'] = 'OtherMesh'
        self.save_receipt()
        with self.assertRaisesRegex(ValueError, '43 additions'):
            builder.build(self.root)

    def test_nonrelative_or_missing_textures_are_rejected(self):
        self.receipt['all_texture_paths_project_relative'] = False
        self.save_receipt()
        with self.assertRaisesRegex(ValueError, 'texture'):
            builder.build(self.root)


if __name__ == '__main__':
    unittest.main()
