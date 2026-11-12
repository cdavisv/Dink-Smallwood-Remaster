"""Source metadata and fail-before-asset-access checks; no Unreal dependency."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'closed_eaves_preflight', ROOT / 'Scripts/RoofNative/house439_closed_eaves_preflight.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PACKET = ROOT / MODULE.SOURCE / 'Packet'


class ClosedEavesPreparationTests(unittest.TestCase):
    def setUp(self):
        self.export = json.loads((PACKET / 'Evidence/EXPORT_READBACK.json').read_text())
        self.frame = json.loads((PACKET / 'Evidence/ROLE_BINDINGS_AND_FRAME.json').read_text())
        self.row = json.loads((ROOT / MODULE.SOURCE / 'delivery_manifest.json').read_text())['candidate_asset_row']

    def test_actual_frozen_export_and_new_bounds(self):
        MODULE.validate_export(self.export)
        MODULE.validate_candidate_row(self.row, self.frame)

    def test_old_bounds_and_relaxed_tolerance_rejected(self):
        row = copy.deepcopy(self.row)
        row['expected_size_cm'][0] = 1882.9998016357422
        with self.assertRaisesRegex(ValueError, 'fresh source bounds'):
            MODULE.validate_candidate_row(row, self.frame)
        row = copy.deepcopy(self.row)
        row['bounds_tolerance_cm'] = 2.0
        with self.assertRaisesRegex(ValueError, 'tolerance'):
            MODULE.validate_candidate_row(row, self.frame)

    def test_export_roles_handedness_and_normal_errors_rejected(self):
        for key, value in (
                ('actual_material_slots', self.export['actual_material_slots'][:-1]),
                ('bitangent_sign_changes', 1), ('normal_difference_degrees', [0, 0, .051]),
                ('Mikk_difference_degrees', [0, 0, float('nan')]),
                ('triangles_before_after', [182626, 182625])):
            report = copy.deepcopy(self.export)
            report[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                MODULE.validate_export(report)

    def test_missing_or_wrong_inspector_refused_without_asset_access(self):
        paths = SimpleNamespace(project_dir=lambda: str(ROOT),
                                convert_relative_path_to_full=lambda value: value)
        for library in (None, SimpleNamespace(inspect_static_mesh_geometry=lambda mesh:
                                             '{"schema":"old","valid":true}')):
            U = SimpleNamespace(Paths=paths, DinkMaterialArtLibrary=library)
            with self.assertRaises(ValueError):
                MODULE.inspect_compiled_geometry_capability(U, ROOT, lambda: None)

    def test_null_probe_requires_guard_and_exact_project(self):
        called = []
        paths = SimpleNamespace(project_dir=lambda: str(ROOT),
                                convert_relative_path_to_full=lambda value: value)
        def probe(mesh):
            self.assertIsNone(mesh)
            return '{"schema":"dink-static-mesh-geometry/1","valid":false,"error":"null_mesh"}'
        U = SimpleNamespace(Paths=paths, DinkMaterialArtLibrary=SimpleNamespace(
            inspect_static_mesh_geometry=probe))
        MODULE.inspect_compiled_geometry_capability(U, ROOT, lambda: called.append('guard'))
        self.assertEqual(called, ['guard'])
        with self.assertRaises(ValueError):
            MODULE.inspect_compiled_geometry_capability(U, ROOT, None)
        with self.assertRaises(ValueError):
            MODULE.inspect_compiled_geometry_capability(U, ROOT / 'wrong', lambda: None)


if __name__ == '__main__':
    unittest.main()
