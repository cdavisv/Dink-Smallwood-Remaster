"""The world export's ground helpers (Scripts/export_import_bundle.py): layer folding, forest and relief points,
water tile rectangles. None of them may put anything where a player can stand."""
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Scripts'))
try:
    import numpy as np
    from export_import_bundle import (RELIEF_MAX_CLEAR_PX, RELIEF_MIN_CLEAR_PX, fold_terrain_layers, forest_points,  # noqa: E402
                                      mark_sea_water, natural_water_shape, relief_points, water_tile_rects)
except ImportError as error:    # the world export needs numpy and Pillow; a machine without them cannot run it either
    raise unittest.SkipTest('world export helpers need numpy and Pillow: %s' % error)

CLASSES = {1: {'terrain': 'grass'}, 2: {'terrain': 'cliff_face'}, 3: {'terrain': 'rock_mass'}, 4: {'terrain': 'forest_canopy'},
           5: {'terrain': 'water'}, 6: {'terrain': 'cave_wall'}}


def tiles(default=1, **at):
    """12 x 8 tiles of class `default`; at = {'r_c': class number}."""
    out = []
    for row in range(8):
        for col in range(12):
            out.append({'row': row, 'col': col, 'num': at.get('%d_%d' % (row, col), default)})
    return out


def w(v):
    return np.full((4, 4), float(v))


class FoldTerrainLayersTests(unittest.TestCase):
    def test_four_layers_or_fewer_come_back_untouched(self):
        weights = {'MeadowTurf': w(5), 'EarthPath': w(3), 'CliffRock': w(2), 'DrySand': w(1)}
        out, merged, dropped = fold_terrain_layers(weights)
        self.assertEqual(sorted(out), sorted(weights))
        self.assertEqual((merged, dropped), ({}, {}))

    def test_a_fifth_layer_folds_into_its_own_family_first(self):
        weights = {'MeadowTurf': w(5), 'RockyGrass': w(0.5), 'EarthPath': w(3), 'CliffRock': w(2), 'DrySand': w(1)}
        out, merged, dropped = fold_terrain_layers(weights)
        self.assertEqual(merged, {'RockyGrass': 'MeadowTurf'})
        self.assertEqual(dropped, {})
        self.assertAlmostEqual(float(out['MeadowTurf'][0, 0]), 5.5)
        self.assertEqual(len(out), 4)

    def test_without_a_relative_the_smallest_layer_is_dropped_into_its_nearest(self):
        weights = {'MeadowTurf': w(5), 'EarthPath': w(3), 'CliffRock': w(2), 'DrySand': w(1), 'Snow': w(0.2)}
        out, merged, dropped = fold_terrain_layers(weights)
        self.assertEqual(merged, {})
        self.assertEqual(dropped, {'Snow': 'CliffRock'})
        self.assertEqual(len(out), 4)

    def test_the_total_weight_is_kept(self):
        weights = {k: w(i + 1) for i, k in enumerate(('MeadowTurf', 'RockyGrass', 'WildGrass', 'EarthPath', 'TransitionDirt', 'CliffRock', 'Snow'))}
        out, _, _ = fold_terrain_layers(weights)
        self.assertAlmostEqual(sum(float(v.sum()) for v in out.values()), sum(float(v.sum()) for v in weights.values()))


class ForestPointsTests(unittest.TestCase):
    def test_no_tree_within_reach_of_walkable_ground(self):
        walk = np.zeros((400, 600), bool)
        walk[:, :100] = True                                    # the two west columns are open ground
        points = forest_points(7, tiles(4), CLASSES, walk)
        self.assertTrue(points)
        for x, y, _edge in points:
            self.assertFalse(walk[max(0, y - 40):y + 41, max(0, x - 40):x + 41].any())

    def test_no_tree_between_the_play_camera_and_ground_to_its_north(self):
        walk = np.zeros((400, 600), bool)
        walk[100:150, :] = True                                 # a path across the screen, forest on both sides
        points = forest_points(7, tiles(4), CLASSES, walk)
        self.assertTrue(points)
        south = [y for _x, y, _edge in points if y > 150]
        self.assertTrue(south and min(south) > 150 + 110)       # nothing in the camera's corridor south of the path
        north = [y for _x, y, _edge in points if y < 100]
        self.assertTrue(north and max(north) < 100 - 40)        # north of it only the boughs' reach is kept clear

    def test_a_walkable_forest_gets_no_tree(self):
        self.assertEqual(forest_points(7, tiles(4), CLASSES, np.ones((400, 600), bool)), [])


class ReliefPointsTests(unittest.TestCase):
    def setUp(self):
        self.no_warp = np.zeros((400, 600), bool)

    def test_rock_only_on_relief_tiles_and_only_where_nobody_can_stand(self):
        walk = np.zeros((400, 600), bool)
        walk[200:, :] = True                                    # the south half is open ground
        rows = tiles(1, **{'0_0': 2, '1_5': 3, '6_6': 2})       # the last one lies in the open ground
        points = relief_points(9, rows, CLASSES, walk, self.no_warp)
        self.assertEqual(sorted(p[4] for p in points), [0, 1])
        for x, y, clear, tier, _cls in points:
            self.assertEqual(tier, 1)
            self.assertTrue(RELIEF_MIN_CLEAR_PX <= clear <= RELIEF_MAX_CLEAR_PX)
            yy, xx = np.ogrid[0:400, 0:600]
            self.assertFalse((walk & ((yy - y) ** 2 + (xx - x) ** 2 <= clear * clear)).any())

    def test_an_enclosed_pocket_is_tier_two_and_an_open_one_gets_nothing(self):
        rows = tiles(1, **{'3_3': 3})                           # tile centre (175, 175)
        pocket = np.zeros((400, 600), bool)
        pocket[150:200, 150:200] = True                         # walkable, touches no edge
        points = relief_points(9, rows, CLASSES, pocket, self.no_warp)
        self.assertEqual([p[3] for p in points], [2])
        open_ground = pocket.copy()
        open_ground[175, 0:200] = True                          # a corridor to the west edge
        self.assertEqual(relief_points(9, rows, CLASSES, open_ground, self.no_warp), [])

    def test_a_pocket_with_a_warp_a_placement_or_a_reached_component_stays_flat(self):
        rows = tiles(1, **{'3_3': 3})
        pocket = np.zeros((400, 600), bool)
        pocket[150:200, 150:200] = True
        warp = np.zeros((400, 600), bool)
        warp[160:165, 160:165] = True
        self.assertEqual(relief_points(9, rows, CLASSES, pocket, warp), [])
        self.assertEqual(relief_points(9, rows, CLASSES, pocket, self.no_warp, entries=[(170, 170)]), [])

    def test_indoor_screens_get_tier_one_only(self):
        rows = tiles(1, **{'3_3': 6})
        pocket = np.zeros((400, 600), bool)
        pocket[150:200, 150:200] = True
        self.assertEqual(relief_points(9, rows, CLASSES, pocket, self.no_warp, indoor=True), [])


class NaturalWaterShapeTests(unittest.TestCase):
    def test_a_pond_is_rounded_and_stays_near_its_tiles(self):
        shape = natural_water_shape(tiles(1, **{'3_5': 5, '3_6': 5, '4_5': 5, '4_6': 5}), CLASSES, 438)
        self.assertEqual(shape.shape, (400, 600))
        self.assertTrue(shape[200, 300])                                    # the middle of the pond is water
        self.assertFalse(shape[:100].any() or shape[300:].any() or shape[:, :200].any() or shape[:, 400:].any())
        squares = np.zeros((400, 600), bool); squares[150:250, 250:350] = True
        self.assertTrue((shape != squares).any(), 'the outline is the tile squares')
        self.assertTrue(0.5 < shape.sum() / squares.sum() < 1.5)

    def test_same_screen_same_shape_and_no_water_no_shape(self):
        a = natural_water_shape(tiles(1, **{'3_5': 5}), CLASSES, 465)
        self.assertTrue((a == natural_water_shape(tiles(1, **{'3_5': 5}), CLASSES, 465)).all())
        self.assertFalse(natural_water_shape(tiles(1), CLASSES, 465).any())

    def test_at_the_screen_rim_the_tile_outline_holds(self):
        shape = natural_water_shape(tiles(1, **{'3_0': 5, '4_0': 5}), CLASSES, 7)
        self.assertTrue(shape[160:240, 0].all())                            # water reaches the west rim over the tiles' span
        self.assertFalse(shape[:120, 0].any() or shape[280:, 0].any())


class SeaWaterTests(unittest.TestCase):
    def test_a_shore_or_a_screen_beside_one_is_sea_and_an_inland_pond_is_not(self):
        rows = {'100': {'water_tiles': [[0, 0, 50, 50]], 'classes': {'water': 1}, 'layers': ['MeadowTurf', 'WetSand']},
                '132': {'classes': {'water': 40}, 'layers': ['WetSand', 'DrySand']},
                '200': {'water_tiles': [[0, 0, 50, 50]], 'classes': {'water': 1}, 'layers': ['MeadowTurf', 'DrySand']},
                '300': {'water_tiles': [[0, 0, 50, 50]], 'classes': {'water': 1}, 'layers': ['MeadowTurf', 'WetSand']},
                '301': {'classes': {'grass': 96}, 'layers': ['MeadowTurf', 'DrySand']}}
        mark_sea_water(rows)
        self.assertTrue(rows['100']['water_sea'])       # the screen south of it is a sea shore
        self.assertTrue(rows['200']['water_sea'])       # its own beach
        self.assertFalse(rows['300']['water_sea'])      # dry sand next door without water is not a shore
        self.assertNotIn('water_sea', rows['132'])


class WaterTileRectsTests(unittest.TestCase):
    def test_row_runs_are_merged(self):
        rows = tiles(1, **{'0_0': 5, '0_1': 5, '0_3': 5, '2_11': 5})
        self.assertEqual(water_tile_rects(rows, CLASSES), [[0, 0, 100, 50], [150, 0, 200, 50], [550, 100, 600, 150]])

    def test_no_water_no_rects(self):
        self.assertEqual(water_tile_rects(tiles(1), CLASSES), [])


if __name__ == '__main__':
    unittest.main()
