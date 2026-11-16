"""The corpse kit (SourceAssets/Art/PhotorealPass/Corpses): the owner's gore rule as far as data can hold it.

A family row places one mesh and nothing else, so the blood a 1997 corpse sprite lies in has to be part of that mesh:
every body of the kit carries a second material slot with its pool card. The pictures are judged by eye in the game
(Docs/Verification); this only keeps a later edit from binding a body without its pool or a mesh the kit does not hold."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
KIT = PROJECT / 'SourceAssets/Art/PhotorealPass/Corpses'
GAME = '/Game/Dink/Photoreal/Corpses/'
# the 1997 pictures that show a body in its blood (sequence of sprite_classes.csv): each needs a pool in the mesh
BODIES = {'corpse_knight', 'dragon_corpse', 'corpse_merchant', 'corpse_girl', 'corpse_maiden', 'corpse_mom', 'corpse_peasant',
          'corpse_soldier', 'dink_dead'}


def kit_rows():
    rows = json.loads((PROJECT / 'Content/Dink/Data/Art/families.json').read_text())['families']
    return [r for r in rows if r.get('mesh', '').startswith(GAME) or any(v.startswith(GAME) for v in r.get('variants', []))]


class CorpseKitTests(unittest.TestCase):
    def setUp(self):
        self.kit = json.loads((KIT / 'manifest.json').read_text())
        self.assets = {a['name']: a for a in self.kit['assets']}
        self.materials = self.kit['integration']['materials']

    def test_manifest_is_what_the_tool_writes(self):
        done = subprocess.run([sys.executable, '-I', str(KIT / 'tools/make_kit_manifest.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_every_bound_mesh_is_in_the_kit(self):
        rows = kit_rows()
        self.assertTrue(rows, 'no families.json row uses the corpse kit')
        for row in rows:
            for path in [row['mesh']] + row.get('variants', []):
                self.assertTrue(path.startswith(GAME), '%s mixes kits: %s' % (row['family'], path))
                name = path.rsplit('.', 1)[1]
                self.assertIn(name, self.assets, '%s binds %s, which the kit manifest does not import' % (row['family'], name))

    def test_a_body_is_placed_with_its_pool_of_blood(self):
        bodies = [a for a in self.assets.values() if BODIES & set(a['families'])]
        self.assertTrue(bodies)
        for asset in bodies:
            pools = [m for m in asset['materials'] if m.endswith('_Pool')]
            self.assertEqual(len(pools), 1, '%s has no pool card: a family row cannot place a companion decal' % asset['name'])
            self.assertEqual(self.materials[pools[0]]['kind'], 'masked', pools[0])
            self.assertEqual(len(asset['materials']), 2, asset['name'])
            # measured, not judged by eye (owner's rule: never less blood than 1997): the blood on the ground covers at least the
            # red area of the picture, and it does not sprawl far past the picture's footprint (the card width of placements.json)
            own = json.loads((PROJECT.parent / asset['folder'] / 'manifest.json').read_text())
            if 'sprite_red_area_m2' in own:
                self.assertGreaterEqual(own['pool_area_m2'], own['sprite_red_area_m2'], asset['name'])
                self.assertLessEqual(own['pool_extent_m'], 1.6 * own['sprite_footprint_m'], asset['name'])

    def test_bodies_keep_their_real_size_and_lie_as_the_sprite_does(self):
        for row in kit_rows():
            name = row['mesh'].rsplit('.', 1)[1]
            if BODIES & set(self.assets[name]['families']):
                self.assertEqual(row.get('fit'), 'none', row['family'])
                self.assertTrue(row.get('yaw_from_sprite'), row['family'])

    def test_the_mother_and_the_burn_holes_of_the_starting_house_are_placed_by_origin(self):
        # screen 1 is dressed by its own manifest, where family rows draw nothing: these seven are `replacements` rows
        doc = json.loads((PROJECT / 'Content/Dink/Data/Art/stonebrook.json').read_text())
        rows = {r['origin']: r['mesh'] for r in doc['replacements'] if r['mesh'].startswith(GAME)}
        self.assertEqual(rows.get('S001_P34'), GAME + 'SM_Corpse_Mother_PR.SM_Corpse_Mother_PR')
        self.assertEqual(sorted(o for o in rows if o != 'S001_P34'), ['S001_P44', 'S001_P45', 'S001_P46', 'S001_P47', 'S001_P48', 'S001_P49'])
        sizes = {a['mesh']: a['expected_size_cm'] for a in doc['assets']}
        for mesh in set(rows.values()):
            name = mesh.rsplit('.', 1)[1]
            self.assertIn(name, self.assets, 'replacement mesh is not in the kit: ' + name)
            self.assertEqual(sizes[mesh][:2], [round(v * 100, 2) for v in self.assets[name]['dimensions_m'][:2]], name)

    def test_a_picture_decal_covers_at_least_the_ground_its_1997_picture_covered(self):
        decals = self.kit['decals']
        self.assertEqual(json.loads((KIT / 'Decals/decals.json').read_text()), decals)
        pictures = set()
        for row in decals['sets']:
            for f in row['files'].values():
                self.assertTrue((KIT / 'Decals' / f).is_file(), f)
            self.assertEqual(len(row['cells']), 4, row['name'])
            for cell in row['cells']:
                pictures.add(cell['picture'])
                self.assertGreaterEqual(cell['decal_area_m2'], cell['picture_area_m2'], '%s cell %d' % (row['name'], cell['cell']))
                self.assertGreaterEqual(cell['cell_m'], max(cell['card_m']), '%s cell %d' % (row['name'], cell['cell']))
        self.assertLessEqual({'187_01', '187_02', '187_03', '188_02', '188_04', '189_01', '189_02', '189_04', '158_01', '158_02', '158_03'}, pictures)

    def test_no_collision_comes_with_the_kit(self):
        for asset in self.assets.values():
            self.assertEqual(asset['collision_hulls'], 0, asset['name'])


if __name__ == '__main__':
    unittest.main()
