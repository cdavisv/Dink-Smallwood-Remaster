"""Scripts/art_wiring_audit.py: package reading, the checks and the reviewed-reason table."""
import importlib.util
import json
import os
import struct
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'art_wiring_audit.py'
spec = importlib.util.spec_from_file_location('art_wiring_audit', SCRIPT)
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def fstrings(*values):
    """Bytes as a .uasset stores FStrings: int32 length (with the NUL), ASCII, NUL."""
    out = b'\x00' * 16
    for v in values:
        b = v.encode() + b'\x00'
        out += struct.pack('<i', len(b)) + b
    return out


class FakePackages(A.Packages):
    def __init__(self, blobs):
        self.lfs = None
        self.files = {g: g for g in blobs}
        self.by_name = {}
        for g in blobs:
            self.by_name.setdefault(os.path.basename(g), []).append(g)
        self._strings = {}
        self.unreadable = set()
        self.blobs = blobs

    def strings(self, game):
        data = self.blobs[game]
        return [m.group(2).decode() for m in A.FSTRING.finditer(data) if len(m.group(2)) + 1 == m.group(1)[0]]


class PackageReading(unittest.TestCase):
    def setUp(self):
        self.pk = FakePackages({
            '/Game/Dink/K/SM_Rock': fstrings('/Game/Dink/K/SM_Rock', '/Game/Dink/K/MI_Rock', 'SM_Rock',
                                             '/Script/Engine.StaticMesh', 'LODs', '1', 'NaniteEnabled', 'False',
                                             'Triangles', '9000'),
            '/Game/Dink/K/MI_Rock': fstrings('/Game/Dink/K/MI_Rock', '/Game/Dink/K/Textures/T_Rock_BC', 'MI_Rock',
                                             '/Script/Engine.MaterialInstanceConstant'),
            '/Game/Dink/K/SM_Grey': fstrings('SM_Grey', '/Script/Engine.StaticMesh',
                                             '/Engine/EngineMaterials/WorldGridMaterial'),
            '/Game/Dink/K/Textures/T_Rock_N': fstrings('T_Rock_N', '/Script/Engine.Texture2D', 'CompressionSettings',
                                                       'TC_Default', 'SRGB', 'True'),
            '/Game/Dink/K/Textures/T_Rock_ORM': fstrings('T_Rock_ORM', '/Script/Engine.Texture2D',
                                                         'CompressionSettings', 'TC_Masks', 'SRGB', 'False'),
            '/Game/Dink/V/SM_Veg_Grass': fstrings('SM_Veg_Grass', '/Script/Engine.StaticMesh', 'NaniteEnabled', 'True',
                                                  '/Game/Dink/K/MI_Rock'),
            '/Game/Dink/K/SM_Chair_Oak': fstrings('SM_Chair_Oak', '/Script/Engine.StaticMesh', 'NaniteEnabled', 'True',
                                                  '/Game/Dink/K/MI_Rock'),
        })

    def flags(self, game):
        return [f for f, _ in A.check_package(self.pk, game, self.pk.tags(game))]

    def test_tags_and_class(self):
        t = self.pk.tags('/Game/Dink/K/SM_Rock')
        self.assertEqual(t['_class'], 'StaticMesh')
        self.assertEqual(t['Triangles'], '9000')
        self.assertIn('/Game/Dink/K/MI_Rock', self.pk.refs('/Game/Dink/K/SM_Rock'))

    def test_mesh_checks(self):
        self.assertEqual(self.flags('/Game/Dink/K/SM_Rock'), ['lod'])          # one LOD, 9000 triangles, Nanite off
        self.assertEqual(self.flags('/Game/Dink/K/SM_Grey'), ['default_material'])
        self.assertIn('missing_texture', self.flags('/Game/Dink/K/MI_Rock'))   # T_Rock_BC is not a package
        self.assertEqual(self.flags('/Game/Dink/V/SM_Veg_Grass'), ['nanite'])
        self.assertEqual(self.flags('/Game/Dink/K/SM_Chair_Oak'), [])          # "chair" is not hair

    def test_texture_checks(self):
        self.assertEqual(self.flags('/Game/Dink/K/Textures/T_Rock_N'), ['texture'])
        self.assertEqual(self.flags('/Game/Dink/K/Textures/T_Rock_ORM'), [])

    def test_reachability(self):
        via = A.reach(self.pk, {'/Game/Dink/K/SM_Rock': {'Content/Dink/Data/Art/families.json'}})
        self.assertIn('/Game/Dink/K/MI_Rock', via)
        self.assertTrue(via['/Game/Dink/K/MI_Rock'].startswith('via SM_Rock'))
        self.assertNotIn('/Game/Dink/K/SM_Grey', via)


class Reasons(unittest.TestCase):
    def test_known_table_parses_and_matches(self):
        rows = A.known_rows()
        self.assertTrue(rows)
        self.assertIsNone(A.known_reason('SK_Duck', '', rows))           # #113 merged: the duck is wired, no reason
        self.assertEqual(A.known_reason('AN_Duck_Peck', '', rows)[0], 'bug')
        self.assertEqual(A.known_reason('SM_Castle_Wall_8m', 'SourceAssets/Art/PhotorealPass/Structures/Castle/x.fbx', rows)[0], 'queued')
        self.assertIsNone(A.known_reason('SM_Castle_Wall_8m', 'SourceAssets/Art/Other/x.fbx', rows))
        self.assertEqual(A.known_reason('SM_Anything', 'SourceAssets/Art/StonebrookRuins/Export/a.fbx', rows)[0], 'alternate')

    def test_gap_flag(self):
        self.assertEqual(A.gap_flag('queued: PR #113', ''), 'queued')
        self.assertEqual(A.gap_flag('', 'VS-02'), 'queued')
        self.assertEqual(A.gap_flag('deliberate: a reviewed reason', ''), 'deliberate')
        self.assertEqual(A.gap_flag('STATUS.md: not imported: hangs on a wall', ''), 'documented')  # not reviewed here
        self.assertEqual(A.gap_flag('replaced: mocap', ''), 'replaced')
        self.assertIsNone(A.gap_flag('', ''))

    def test_clip_played(self):
        natural = {'drop_prefixes': ['Walk_']}
        self.assertTrue(A.deliberate_clip_reason('AN_Walk_Timid', natural, {}))
        self.assertEqual(A.clip_played('AN_Fist_Jab_Timid', '', {'Fist_Jab'}, {}, []), "yes (C++ asks for 'Fist_Jab')")
        self.assertTrue(A.clip_played('AN_Wave', '', set(), {}, []).startswith('no (no runtime'))

    def test_card_table_counts_only_drawn_cards(self):
        with tempfile.TemporaryDirectory() as d:
            audit = Path(d) / 'audit.jsonl'
            prim = lambda o, z, frame: {'cn': 'Card', 'o': o, 'max': [0, 0, z],
                                        'mats': [{'m': '/Game/Dink/_Generated/Sprites/MI_Sprite_93_%02d.MI_Sprite_93_%02d' % (frame, frame)}]}
            audit.write_text(json.dumps({'screen': 409, 'prims': [prim('S409_P01', 100, 4), prim('S409_P02', -2000, 4),
                                                                   prim('S409_P03', 100, 1)]}) + '\n')
            cov = Path(d) / 'cov.csv'
            cov.write_text('origin_id,state\nS409_P01,placeholder\nS409_P03,final\n')
            rows = A.card_table(str(audit), str(cov), str(Path(d) / 'none.json'), {'fence_rail_ns': {'SM_Fence'}})
        by = {r['class']: r for r in rows}
        self.assertEqual(by['fence_rail_ns']['cards'], 1)               # the buried card is not drawn
        self.assertEqual(by['fence_rail_ns']['mesh_available'], 'SM_Fence')
        self.assertEqual(by['fence_rail_ew']['final_origin_cards'], 'S409_P03')


class Classifier(unittest.TestCase):
    """Review of PR #154 (15 Nov 2026): what may and may not count as a runtime binding."""

    def setUp(self):
        self.pk = FakePackages({'/Game/Dink/A/SM_Door': b'', '/Game/Dink/B/SM_Door': b'', '/Game/Dink/A/SM_Only': b'',
                                '/Game/Dink/Photoreal/TownExteriors/SM_Wall': b'', '/Game/Dink/Old/SM_Wall': b''})
        self.roots = A.collections.defaultdict(set)

    def test_a_free_text_fields_do_not_bind(self):
        A.walk_json({'family': 'x', 'mesh': '/Game/Dink/A/SM_Only.SM_Only',
                     'note': 'SM_Door is imported but unbound; see /Game/Dink/B/SM_Door', 'why': 'SM_Door'},
                    'families.json', self.pk, self.roots)
        self.assertEqual(sorted(self.roots), ['/Game/Dink/A/SM_Only'])

    def test_a_keys_and_asset_lists_do_not_bind(self):
        A.walk_json({'mesh_swaps': {'/Game/Dink/A/SM_Door': ['/Game/Dink/A/SM_Only']},
                     'assets': [{'mesh': '/Game/Dink/B/SM_Door.SM_Door'}]}, 'environment.json', self.pk, self.roots)
        self.assertEqual(sorted(self.roots), ['/Game/Dink/A/SM_Only'])     # (d): the swap source key is not bound

    def test_b_a_path_binds_only_the_package_it_names(self):
        A.walk_json({'mesh': '/Game/Dink/A/SM_Door.SM_Door'}, 'm.json', self.pk, self.roots)
        self.assertEqual(sorted(self.roots), ['/Game/Dink/A/SM_Door'])      # not the same-named twin in B
        A.walk_json({'mesh': 'SM_Door'}, 'm.json', self.pk, self.roots)     # an ambiguous bare name binds nothing more
        self.assertEqual(sorted(self.roots), ['/Game/Dink/A/SM_Door'])
        A.walk_json({'mesh': 'SM_Wall'}, 'town_houses.json', self.pk, self.roots,
                    A.BARE_PREFIX['town_houses.json'])                      # resolved under the runtime's folder
        self.assertIn('/Game/Dink/Photoreal/TownExteriors/SM_Wall', self.roots)
        self.assertNotIn('/Game/Dink/Old/SM_Wall', self.roots)

    def test_c_only_runtime_modules_are_cpp_roots(self):
        dirs = [d.replace(os.sep, '/') for d in A.runtime_module_dirs()]
        self.assertTrue(any(d.endswith('Plugins/DinkCore/Source/DinkCore') for d in dirs))
        self.assertFalse(any('DinkImport' in d or 'DinkParity' in d or 'DinkProbe' in d for d in dirs))

    def test_c_cpp_literals_bind_but_comments_do_not(self):
        text = '// SM_Only is mentioned in a comment\nLoad(TEXT("/Game/Dink/A/SM_Door.SM_Door"));'
        for lit in A.CPP_LITERAL.findall(text):
            A.bind_string(lit, 'x.cpp', self.pk, self.roots)
        self.assertEqual(sorted(self.roots), ['/Game/Dink/A/SM_Door'])


class Swaps(unittest.TestCase):
    """environment.json mesh_swaps: which roots the runtime swaps (review 2 of PR #154)."""

    def test_authored_swapped_context_and_family_not(self):
        swapped = {'/Game/K/SM_Oak': ['/Game/P/SM_Veg_Oak']}
        roots = {'/Game/K/SM_Oak': {'Content/Dink/Data/Art/stonebrook_exterior.json', 'Content/Dink/Data/Art/vista.json',
                                    'Content/Dink/Data/Art/families.json', 'Content/Dink/Data/Art/camera_exteriors.json'}}
        authored = {'Content/Dink/Data/Art/stonebrook_exterior.json': 439}
        context = {'Content/Dink/Data/Art/vista.json'}
        done, decided, missed = A.swap_status(['/Game/K/SM_Oak'], roots, swapped, {}, authored, context)
        self.assertEqual(done, ['Content/Dink/Data/Art/stonebrook_exterior.json'])
        self.assertEqual(decided, [])
        self.assertEqual(missed, ['Content/Dink/Data/Art/families.json', 'Content/Dink/Data/Art/vista.json'])  # camera_* ignored

    def test_only_tag_limits_the_swap_on_purpose(self):
        g = '/Game/K/SM_Cottage'
        swapped = {g: ['/Game/P/SM_Cottage_PR']}
        only = {g: 'DinkArtScreen_439'}
        roots = {g: {'a439.json', 'a001.json', 'vista.json'}}
        done, decided, missed = A.swap_status([g], roots, swapped, only, {'a439.json': 439, 'a001.json': 1}, {'vista.json'})
        self.assertEqual(done, ['a439.json'])
        self.assertEqual(decided, ['a001.json', 'vista.json'])   # kept old on purpose, not a wiring bug
        self.assertEqual(missed, [])


if __name__ == '__main__':
    unittest.main()
