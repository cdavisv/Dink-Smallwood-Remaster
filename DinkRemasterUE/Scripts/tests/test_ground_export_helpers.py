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
                                      relief_points, water_tile_rects)
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
            self.assertFalse(walk[max(0, y - 8):y + 9, max(0, x - 8):x + 9].any())

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


class WaterTileRectsTests(unittest.TestCase):
    def test_row_runs_are_merged(self):
        rows = tiles(1, **{'0_0': 5, '0_1': 5, '0_3': 5, '2_11': 5})
        self.assertEqual(water_tile_rects(rows, CLASSES), [[0, 0, 100, 50], [150, 0, 200, 50], [550, 100, 600, 150]])

    def test_no_water_no_rects(self):
        self.assertEqual(water_tile_rects(tiles(1), CLASSES), [])


if __name__ == '__main__':
    unittest.main()
