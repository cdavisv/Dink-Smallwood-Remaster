import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import shared_roof_contract as C
import shared_roof_native as N
import native_texture_tools_v11 as T
import native_mesh_tools_v11c as M

P = Path(__file__).resolve().parents[2]


class SharedRoofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = C.load_contract(P)

    def test_mesh_relative_metadata_is_ready_for_verification_and_save(self):
        # Exercise the complete import orchestrator. The verifier models the real
        # source-filename check; patching individual low-level imports cannot fix order.
        class Asset:
            def __init__(self, package):
                self.package = package
                self.relative_ready = False
                self.verified = False
            def get_path_name(self):
                return self.package + '.' + self.package.rsplit('/', 1)[-1]
        class Material(Asset):
            pass
        class Mesh(Asset):
            pass
        events, receipts = [], []
        tools = SimpleNamespace(create_asset=lambda name, folder, *args: Material(folder + '/' + name))
        U = SimpleNamespace(EditorAssetLibrary=SimpleNamespace(does_asset_exist=lambda p: False),
                            AssetToolsHelpers=SimpleNamespace(get_asset_tools=lambda: tools),
                            Material=Material, MaterialFactoryNew=lambda: None,
                            StaticMeshEditorSubsystem=object(), get_default_object=lambda cls: object())
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            contract = copy.deepcopy(self.contract)
            def configure(u, asset, files, packet, guard):
                self.assertIs(u, U)
                self.assertEqual(packet, root / 'SourceAssets/Art')
                if isinstance(asset, Mesh):
                    self.assertFalse(asset.relative_ready, 'Redundant mesh metadata setup')
                    self.assertFalse(asset.verified)
                    events.append(('relative', asset.package))
                asset.relative_ready = True
            def verify(mesh, record):
                self.assertTrue(mesh.relative_ready, 'Verifier observed an absolute/raw import filename')
                self.assertFalse(C.package_file(root, mesh.package).exists(), 'Verifier ran after save')
                mesh.verified = True
                events.append(('verify', mesh.package))
                return dict(passed=True, triangles=record['triangles'], UCX=record['UCX'],
                            geometry_UV_normals_source_match=True)
            def save(asset, overwrite=False):
                self.assertFalse(overwrite)
                if isinstance(asset, Mesh):
                    self.assertTrue(asset.relative_ready)
                    self.assertTrue(asset.verified, 'Mesh saved before source verification')
                    events.append(('save', asset.package))
                file = C.package_file(root, asset.package)
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b'mocked native save')
                return True
            with patch.object(N, 'preflight_native'), patch.object(N, 'load_contract', return_value=contract), \
                 patch.object(N, 'import_shared_texture', side_effect=lambda u, source, row, guard: Asset(row['package'])), \
                 patch.object(N, 'build_graph'), patch.object(N, 'inspect_graph', return_value={}), \
                 patch.object(N, 'import_shared_roof_base', side_effect=lambda u, packet, row, package, guard: Mesh(package)), \
                 patch.object(N, 'append_lods'), patch.object(N, 'configure_policy'), \
                 patch.object(N, 'bind_named_materials'), patch.object(N, 'configure_relative_sources', side_effect=configure):
                report = N.import_trial(U, root, contract, lambda: None, save,
                                        lambda *args: {}, verify, receipts.append)
            self.assertTrue(report['passed'])
            self.assertEqual(len(report['packages']), 23)
            self.assertIs(receipts[-1], report)
            for record in contract['meshes']:
                package = record['package']
                self.assertEqual([event for event in events if event[1] == package],
                                 [('relative', package), ('verify', package), ('save', package)])

    def test_actual_binary_shared_roles_have_unique_oriented_source_correspondence(self):
        from shared_roof_verify import decode_source
        from geometry_only_match_v11 import candidates
        for record in self.contract['meshes']:
            with self.subTest(mesh=record['name']):
                triangles, hulls = decode_source(P, record)
                self.assertEqual(len(triangles), record['triangles'])
                self.assertEqual(len(hulls), record['UCX'])
                self.assertTrue(all(len(row) == 1 for row in candidates(triangles, triangles, .01)))

    def test_pixel_diagnostics_refuse_nonempty_directory_before_native_export(self):
        from shared_roof_verify import make_pixel_verifier
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / 'previous.png'
            file.write_bytes(b'previous diagnostic')
            with self.assertRaises(ValueError):
                make_pixel_verifier(None, Path(d), lambda: None)

    def test_exact23_with15_shared_and8_existing_production_delivery(self):
        c = self.contract
        self.assertEqual(len(c['trial_packages']), 23)
        self.assertEqual(len(c['production_delivery_packages']), 23)
        self.assertEqual(len(c['trial_only_meshes']), 8)
        self.assertTrue(set(c['trial_only_meshes']).isdisjoint(c['production_delivery_packages']))
        self.assertEqual(sum(r['UCX'] for r in c['meshes']), 204)
        self.assertEqual(sum(r['triangles'] for r in c['meshes']), 17322)
        self.assertEqual(len(c['camera_aliases']), 3)

    def test_normal_green_and_material_F0_are_explicit(self):
        self.assertEqual(sum(r['flip_green'] for r in self.contract['textures']), 3)
        self.assertTrue(all(r['size'] == 1024 for r in self.contract['textures']))
        for r in self.contract['materials']:
            self.assertEqual(r['camera_opacity_default'], 1)
            self.assertEqual(r['shadow_opacity'], 1)
            self.assertNotEqual(r['opaque'], r['masked'])
            self.assertAlmostEqual(r['unreal_specular'] * .08, r['dielectric_F0'])

    def test_missing_old_DLL_capability_refuses_before_import(self):
        events = []
        U = SimpleNamespace(Paths=SimpleNamespace(convert_relative_path_to_full=lambda x: x,
                                                  project_dir=lambda: str(P)),
                            SystemLibrary=SimpleNamespace(get_command_line=lambda: '-run=pythonscript',
                                                          get_console_variable_int_value=lambda x: 0))
        with self.assertRaisesRegex(ValueError, 'not compiled'):
            N.preflight_native(U, P, self.contract, lambda: events.append('guard'))
        self.assertEqual(events, ['guard'])

    def test_existing_trial_destination_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            C.assert_trial_absent(d, self.contract)
            file = C.package_file(d, next(iter(self.contract['trial_packages'])))
            file.parent.mkdir(parents=True)
            file.write_bytes(b'previous trial fixture')
            with self.assertRaises(ValueError):
                C.assert_trial_absent(d, self.contract)

    def test_trial_parent_symlink_and_hardlinked_saved_package_refuse(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as external:
            root = Path(d)
            (root / 'Content').symlink_to(Path(external), target_is_directory=True)
            with self.assertRaises(ValueError):
                C.assert_trial_absent(root, self.contract)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            file = root / 'saved.uasset'
            file.write_bytes(b'saved fixture')
            alias = root / 'alias.uasset'
            alias.hardlink_to(file)
            with self.assertRaises(ValueError):
                C.verify_package_hashes(root, {'saved.uasset': C.sha(file)})

    def test_low_level_profiles_cannot_cross_namespaces(self):
        class Boundary(Exception):
            pass
        def boundary(*args):
            raise Boundary()
        U = SimpleNamespace(EditorAssetLibrary=SimpleNamespace(does_asset_exist=boundary),
                            SystemLibrary=SimpleNamespace(get_console_variable_int_value=boundary))
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / 'T_Shared_OakLonggrain2m_BC.png'
            file.write_bytes(b'exact-byte guard fixture')
            recipe = dict(self.contract['textures'][0], source_sha256=C.sha(file))
            with self.assertRaises(Boundary):
                T.import_shared_texture(U, file, recipe, lambda: None)
            with self.assertRaises(RuntimeError):
                T.import_new(U, file, recipe, lambda: None)
            bad = dict(recipe, package=C.SHARED + 'Textures/T_Shared_NotRegistered_BC')
            with self.assertRaises(RuntimeError):
                T.import_shared_texture(U, file, bad, lambda: None)
            with self.assertRaises(RuntimeError):
                M.import_shared_roof_base(U, d, {'file': 'source'}, C.PRODUCTION + C.NAMES[0], lambda: None)

    def test_legacy_entry_points_still_reach_their_original_native_boundary(self):
        class Boundary(Exception):
            pass
        def boundary(*args):
            raise Boundary()
        U = SimpleNamespace(EditorAssetLibrary=SimpleNamespace(does_asset_exist=boundary),
                            SystemLibrary=SimpleNamespace(get_console_variable_int_value=boundary))
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / 'source'
            file.write_bytes(b'legacy boundary fixture')
            digest = C.sha(file)
            with self.assertRaises(Boundary):
                T.import_new(U, file, {'package': '/Game/Dink/Refinements/RoofChimneyV12d/Textures/T_Legacy',
                                       'source_sha256': digest}, lambda: None)
            with self.assertRaises(Boundary):
                M.import_base(U, d, {'file': 'source', 'sha256': digest}, C.PRODUCTION + C.NAMES[0], lambda: None)

    def test_old_2048_and_new_1024_dimension_checks_stay_distinct(self):
        recipe = next(r for r in self.contract['textures'] if r['compression'] == 'TC_NORMALMAP')
        class Texture:
            size = 1024
            def get_path_name(self):
                return recipe['package'] + '.' + recipe['package'].rsplit('/', 1)[-1]
            def get_editor_property(self, key):
                return {'srgb': False, 'flip_green_channel': True, 'compression_settings': 'NORMAL',
                        'address_x': 'Wrap', 'address_y': 'Wrap'}[key]
            def blueprint_get_size_x(self):
                return self.size
            blueprint_get_size_y = blueprint_get_size_x
        U = SimpleNamespace(Texture2D=Texture, TextureCompressionSettings=SimpleNamespace(TC_NORMALMAP='NORMAL'),
                            TextureAddress=SimpleNamespace(TA_WRAP='Wrap'))
        t = Texture()
        T.configure_shared_texture(U, t, recipe, lambda: None)
        with self.assertRaises(RuntimeError):
            T.configure_and_verify(U, t, recipe, lambda: None)
        t.size = 2048
        with self.assertRaises(RuntimeError):
            T.configure_shared_texture(U, t, recipe, lambda: None)

    def test_imported_slot_order_does_not_choose_the_material_role(self):
        old = {'MI_InteriorRoof_OakLonggrain_Baked': C.SHARED + 'MI_Shared_OakLonggrain2m',
               'MI_InteriorRoof_RoofBoards_Baked': C.SHARED + 'MI_Shared_OakLonggrain2m',
               'MI_InteriorRoof_OakEndgrain_Baked': C.SHARED + 'MI_Shared_OakEndgrain2m'}
        names = [list(old)[2], list(old)[0], list(old)[1]]
        class Material:
            def __init__(self, name):
                self.name = name
        U = SimpleNamespace(Material=Material, load_asset=Material)
        class Mesh:
            assigned = {}
            def get_editor_property(self, key):
                self_test.assertEqual(key, 'static_materials')
                return [SimpleNamespace(get_editor_property=lambda k, name=n: name) for n in names]
            def set_material(self, index, material):
                self.assigned[index] = material.name
        self_test = self
        mesh = Mesh()
        with patch.object(N, 'inspect_slots', return_value={'checked': True}):
            N.bind_named_materials(U, mesh, old, 17322, lambda: None)
        self.assertEqual(mesh.assigned, {i: old[name] for i, name in enumerate(names)})
        names[1] = names[0]
        with self.assertRaises(ValueError):
            N.bind_named_materials(U, mesh, old, 17322, lambda: None)

    def test_only_three_camera_aliases_are_added_and_existing_values_survive(self):
        original = json.dumps({'schema': 'dink-camera/1', 'extra': [1, 2],
                               'material_variants': {'/Existing.Base': '/Existing.Masked'}}).encode()
        result = json.loads(N.camera_map_with_aliases(original, self.contract['camera_aliases']))
        self.assertEqual(result['extra'], [1, 2])
        self.assertEqual(result['material_variants']['/Existing.Base'], '/Existing.Masked')
        self.assertEqual(set(result['material_variants']) - {'/Existing.Base'}, set(self.contract['camera_aliases']))
        with self.assertRaises(ValueError):
            N.camera_map_with_aliases(json.dumps(result).encode(), self.contract['camera_aliases'])
        wrong = dict(self.contract['camera_aliases'])
        wrong.pop(next(iter(wrong)))
        with self.assertRaises(ValueError):
            N.camera_map_with_aliases(original, wrong)

    def test_gameplay_data_add_remove_or_edit_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            file = root / C.CAMERA
            file.parent.mkdir(parents=True)
            file.write_bytes(b'camera fixture')
            expected = {str(C.CAMERA): C.sha(file)}
            N.assert_data_unchanged(root, expected)
            file.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                N.assert_data_unchanged(root, expected)
            N.assert_data_unchanged(root, expected, allow_camera=True)
            extra = file.parent / 'unrelated.json'
            extra.write_text('{}')
            with self.assertRaises(ValueError):
                N.assert_data_unchanged(root, expected, allow_camera=True)

    def test_incomplete_actual_mesh_verification_is_not_accepted(self):
        record = self.contract['meshes'][0]
        for value in ({'passed': True}, {'passed': True, 'triangles': record['triangles'],
                                        'UCX': record['UCX'], 'geometry_UV_normals_source_match': False}):
            with self.assertRaises(ValueError):
                N.checked_mesh_result(value, record)


if __name__ == '__main__':
    unittest.main()
