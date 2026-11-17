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
                                      map_neighbours, mark_sea_water, relief_points, water_is_sea,
                                      water_meets, water_sea_weights, water_tile_rects, water_links, water_sea_patches,
                                      capped_shore_distance, signed_shore_distance, shore_alpha, world_neighbours,
                                      SHORE_PX_CM, SHAPE_CELL_PX, SHAPE_H, SHAPE_W, SHAPE_LAND_CORE_PX,
                                      SHAPE_OFFSET_PX, map_noise, natural_shore, shape_cells, water_draw_rects,
                                      shore_distance_cm, water_band_blockers, blocker_rects, wet_bed_follows_shore)
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


class NaturalShoreTests(unittest.TestCase):
    """The 1997 water outline smoothed in world space (natural_shore): no 50 px stairs, the same on both sides of a
    screen border, never far from the 1997 outline, and a one-tile river is never cut."""

    @staticmethod
    def stair():
        # a river running diagonally down a screen in 50 px steps (two tiles wide), as the 1997 tiles draw it
        fine = np.zeros((400, 600), bool)
        for k in range(8):
            fine[k * 50:(k + 1) * 50, k * 50:k * 50 + 100] = True
        return fine

    def test_the_noise_is_a_function_of_the_map_position(self):
        a = map_noise(465, SHAPE_H, SHAPE_W, 8, SHAPE_CELL_PX)
        b = map_noise(466, SHAPE_H, SHAPE_W, 8, SHAPE_CELL_PX)
        self.assertTrue(np.allclose(a[:, SHAPE_W + 8:], b[:, 8:16]))         # 465's east margin is 466's west edge
        self.assertLessEqual(np.abs(a).max(), 0.5)

    def test_a_stair_becomes_a_slope_near_its_outline(self):
        base = shape_cells(self.stair())
        alpha, shaped = natural_shore(465, {465: base}, {})
        self.assertEqual(alpha.shape, (64, 96))
        self.assertEqual(shaped.shape, (SHAPE_H, SHAPE_W))
        self.assertTrue((shaped != base).any(), 'the outline is still the tiles')
        sd = capped_shore_distance(base, SHAPE_CELL_PX, 12)                # map px from the 1997 outline
        self.assertFalse((shaped & (sd >= SHAPE_LAND_CORE_PX)).any())      # never more than 25 px onto the land
        self.assertFalse((base & ~shaped).any())                            # never back inside the 1997 water
        self.assertFalse((~shaped & (sd < SHAPE_OFFSET_PX - SHAPE_CELL_PX)).any())   # at least the offset onto the land
        # the inner corners of the stair fill in: water where the 1997 tiles had a land corner
        self.assertTrue((shaped & ~base).any())

    def test_a_one_tile_river_is_never_cut(self):
        fine = np.zeros((400, 600), bool); fine[175:225, :] = True
        _, shaped = natural_shore(300, {300: shape_cells(fine)}, {})
        self.assertTrue(shaped[SHAPE_H // 2, :].all())

    def test_two_screens_agree_on_their_border(self):
        fine = self.stair()
        a, b = shape_cells(fine), shape_cells(np.roll(fine, -300, axis=1) & (np.arange(600) < 300)[None, :])
        base = {464: a, 465: b}
        left, _ = natural_shore(464, base, {(1, 0): 465})
        right, _ = natural_shore(465, base, {(-1, 0): 464})
        self.assertTrue(np.allclose(left[:, -1], right[:, 0], atol=1e-6))

    def test_the_drawn_water_covers_the_shaped_water(self):
        _, shaped = natural_shore(465, {465: shape_cells(self.stair())}, {})
        cover = np.zeros((400, 600), bool)
        for x0, y0, x1, y1 in water_draw_rects(shaped):
            self.assertTrue(0 <= x0 < x1 <= 600 and 0 <= y0 < y1 <= 400)
            cover[y0:y1, x0:x1] = True
        ys, xs = np.nonzero(shaped)
        self.assertTrue(cover[(ys * SHAPE_CELL_PX).astype(int), (xs * SHAPE_CELL_PX).astype(int)].all())
        self.assertEqual(water_draw_rects(np.zeros((SHAPE_H, SHAPE_W), bool)), [])

    def test_the_shoreline_field_is_signed_and_runs_on_across_a_border(self):
        fine = self.stair()
        base = {464: shape_cells(fine), 465: shape_cells(np.roll(fine, -300, axis=1) & (np.arange(600) < 300)[None, :])}
        left = shore_distance_cm(464, base, {(1, 0): 465})
        right = shore_distance_cm(465, base, {(-1, 0): 464})
        self.assertEqual(left.shape, (SHAPE_H, SHAPE_W))
        self.assertLess(left[10, 25], 0)                                    # in the river
        self.assertGreater(left[120, 10], 300)                              # far up the bank
        # one cell either side of the border: neighbouring cells of one field differ by at most one cell's length
        self.assertLessEqual(np.abs(left[:, -1] - right[:, 0]).max(), SHAPE_CELL_PX * 4.38 + 1e-6)

    def test_no_water_no_shore(self):
        alpha, shaped = natural_shore(7, {7: np.zeros((SHAPE_H, SHAPE_W), bool)}, {})
        self.assertTrue((alpha == 1.0).all() and not shaped.any())


EAST_EDGE = [[500, 100, 600, 300]]      # water reaching a screen's east edge
WEST_EDGE = [[0, 100, 100, 300]]
SOUTH_EDGE = [[200, 300, 400, 400]]
NORTH_EDGE = [[200, 0, 400, 100]]
ALL_EDGES = [[0, 0, 600, 400]]


def water(kind='wilderness', layers=('MeadowTurf', 'WetSand', 'RockyGrass'), tiles=30, fill=ALL_EDGES, sheet=False):
    return {'kind': kind, 'layers': list(layers), 'tiles': tiles, 'fill': [] if sheet else fill, 'sheet': sheet}


class SeaWaterTests(unittest.TestCase):
    def test_the_importers_own_rule(self):
        self.assertTrue(water_is_sea('sea', ['WetSand']))                     # a sea sheet: only wet sand, still sea
        self.assertTrue(water_is_sea('wilderness', ['MeadowTurf', 'DrySand']))
        self.assertTrue(water_is_sea('settlement', ['ShingleBeach']))
        self.assertFalse(water_is_sea('wilderness', ['MeadowTurf', 'WetSand']))  # WetSand is every water bed
        self.assertFalse(water_is_sea('', []))

    def test_neighbours_do_not_wrap_across_a_row_end(self):
        self.assertEqual(map_neighbours(385), [386, 353, 417])               # column 0: 384 ends the row above
        self.assertEqual(map_neighbours(384), [383, 352, 416])               # column 31: 385 starts the row below
        self.assertEqual(map_neighbours(633), [632, 634, 601, 665])

    def test_fills_meet_only_where_both_reach_the_shared_edge(self):
        self.assertTrue(water_meets(EAST_EDGE, WEST_EDGE, 'E'))
        self.assertFalse(water_meets(EAST_EDGE, [[0, 310, 100, 400]], 'E'))  # both at the edge, rows apart
        self.assertFalse(water_meets([[100, 100, 200, 200]], WEST_EDGE, 'E'))
        self.assertTrue(water_meets(SOUTH_EDGE, NORTH_EDGE, 'S'))
        self.assertFalse(water_meets(SOUTH_EDGE, EAST_EDGE, 'S'))

    def test_open_water_is_sea_and_a_river_fades_to_pond(self):
        # a row of screens 101..106: open sea of wet sand only, then a river running west to east away from it
        w = {101: water(layers=['WetSand'], tiles=96), 102: water(), 103: water(), 104: water(), 105: water(), 106: water()}
        weights = water_sea_weights(w)
        self.assertEqual([weights[n] for n in range(101, 107)], [1.0, 1.0, 0.5, 0.0, 0.0, 0.0])

    def test_water_that_does_not_meet_is_not_joined(self):
        w = {101: water(kind='sea', layers=['WetSand'], tiles=96), 102: water(fill=[[100, 100, 200, 200]])}
        self.assertEqual(water_sea_weights(w), {101: 1.0, 102: 0.0})

    def test_coast_between_two_sea_screens_is_sea_and_no_step_is_bigger_than_half(self):
        # open sea at both ends of a row (101, 105); 103 is two screens from either, but its water joins two sea screens.
        # A river runs south from 103 (135, 167, 199): 135 would be pond by distance, next to the now-sea 103 it is half.
        w = {101: water(tiles=96), 102: water(), 103: water(), 104: water(), 105: water(tiles=96),
             135: water(), 167: water(), 199: water()}
        weights = water_sea_weights(w)
        self.assertEqual([weights[n] for n in (101, 102, 103, 104, 105)], [1.0] * 5)
        self.assertEqual([weights[n] for n in (135, 167, 199)], [0.5, 0.0, 0.0])
        for a in weights:
            for b in map_neighbours(a):
                if b in weights:
                    self.assertLessEqual(abs(weights[a] - weights[b]), 0.5, (a, b))

    def test_a_sheet_takes_the_colour_of_the_water_round_it(self):
        # the 633 case: a sheet of three tiles at the corner where two estuary screens meet the sea
        w = {633: water(tiles=3, sheet=True), 634: water(), 665: water(), 666: water(layers=['WetSand', 'DrySand'])}
        self.assertEqual(water_sea_weights(w)[633], 1.0)
        # an inland ford: pond
        w = {465: water(tiles=15, sheet=True), 464: water(), 466: water()}
        self.assertEqual(water_sea_weights(w)[465], 0.0)

    def test_mark_sea_water_writes_every_water_screen_and_skips_dry_ones(self):
        rows = {'101': {'classes': {'water': 96}, 'layers': ['WetSand'], 'water_surface': True},
                '102': {'classes': {'water': 3}, 'layers': ['MeadowTurf', 'WetSand'], 'water_tiles': [[0, 0, 50, 50]]},
                '103': {'classes': {'grass': 96}, 'layers': ['MeadowTurf', 'DrySand']}}
        weights = mark_sea_water(rows, {101: 'wilderness', 102: 'wilderness', 103: 'wilderness'}, {101: ALL_EDGES})
        self.assertEqual(weights, {101: 1.0, 102: 1.0})
        self.assertEqual(rows['102']['water_sea'], 1.0)
        self.assertEqual(rows['102']['water_sea_patch'], [1.0] * 9)
        self.assertNotIn('water_sea', rows['103'])

    def test_the_sea_weight_runs_on_across_every_joined_border(self):
        # 634 (sea) - 635 (half) - 636 (pond) in a row, 603 (pond) north of 635, 667 south of 635 not joined
        w = {634: water(tiles=96), 635: water(), 636: water(), 603: water(), 667: water(fill=[[100, 100, 200, 200]])}
        weights = {634: 1.0, 635: 0.5, 636: 0.0, 603: 0.0, 667: 0.0}
        links = water_links(w)
        patch = water_sea_patches(weights, links)
        self.assertEqual(patch[635][4], 0.5)                                 # the centre keeps the screen's weight
        self.assertEqual(patch[635][3], 0.75)                                # west edge: halfway to 634
        self.assertEqual(patch[635][5], 0.25)                                # east edge: halfway to 636
        self.assertEqual(patch[635][7], 0.5)                                 # south: 667 does not join, own weight
        for n in patch:                                                      # joined screens agree all along the edge
            for m in links[n]:
                a, b = patch[n], patch[m]
                if m == n + 1:
                    self.assertEqual((a[2], a[5], a[8]), (b[0], b[3], b[6]), (n, m))
                if m == n + 32:
                    self.assertEqual((a[6], a[7], a[8]), (b[0], b[1], b[2]), (n, m))


class ShoreAlphaTests(unittest.TestCase):
    def test_capped_distance_is_exact_within_the_cap(self):
        rng = np.random.default_rng(3)
        grid = np.zeros((20, 30), bool)
        grid[5:14, 4:20] = True
        grid |= rng.random(grid.shape) > 0.93
        exact = signed_shore_distance(grid, SHORE_PX_CM)
        capped = capped_shore_distance(grid, SHORE_PX_CM, cap=11)
        near = np.abs(exact) < 10 * SHORE_PX_CM
        self.assertTrue(np.allclose(exact[near], capped[near]))

    def test_neighbours_must_lie_against_the_screen_in_the_world(self):
        c = lambda x, y: {'nw': [x, y], 'ne': [x + 50, y], 'sw': [x, y + 30], 'se': [x + 50, y + 30]}
        corners = {465: c(100, 100), 464: c(50, 100), 466: c(400, 100), 433: c(100, 70), 498: c(150, 130)}
        self.assertEqual(world_neighbours(465, corners), {(-1, 0): 464, (0, -1): 433, (1, 1): 498})
        self.assertEqual(world_neighbours(385, {385: c(0, 0), 384: c(-50, 0)}), {})   # 384 ends the row above

    def test_a_pond_across_a_border_has_one_depth_on_both_sides(self):
        # a pond straddling the border of 464 (west) and 465: its west bank lies on 464 two texels from the border
        a = np.zeros((64, 96), bool); a[20:44, 94:] = True
        b = np.zeros((64, 96), bool); b[20:44, :30] = True
        cells = {464: a, 465: b}
        left = shore_alpha(464, cells, {(1, 0): 465})
        right = shore_alpha(465, cells, {(-1, 0): 464})
        self.assertTrue(np.allclose(left[:, -1], right[:, 0], atol=1e-6))     # the same value on the border
        self.assertGreater(right[32, 0], 0.2)                                 # shallow: the bank on 464 is near
        self.assertLess(right[32, 0], 0.5)
        alone = shore_alpha(465, cells, {})                                   # on its own 465 never saw that bank
        self.assertLess(alone[32, 0], right[32, 0] - 0.2)
        self.assertTrue((shore_alpha(465, {465: np.zeros((64, 96), bool)}, {}) == 1.0).all())


class WetBedTests(unittest.TestCase):
    def test_the_sand_under_the_water_ends_on_the_waterline(self):
        # grass (layer 1) on a mask whose west half is water (alpha 0) and east half land (alpha 1), the waterline at x 48
        rgba = np.zeros((64, 96, 4)); rgba[:, :, 0] = 1.0
        rgba[:, :, 3] = np.clip(0.5 + (np.arange(96) - 47.5) * 0.02, 0, 1)[None, :]
        out = wet_bed_follows_shore(rgba, ['MeadowTurf', 'WetSand', 'EarthPath'], 'WetSand')
        self.assertTrue(np.allclose(out[:, :40, 1], 1.0) and np.allclose(out[:, :40, 0], 0.0))   # water: all wet sand
        self.assertTrue(np.allclose(out[:, 70:, :3], rgba[:, 70:, :3]))                          # up the bank: unchanged
        self.assertTrue((out[0, 48:55, 1] > 0).all() and (out[0, 48:55, 1] < 1).all())            # a short wet band
        self.assertTrue(np.allclose(out[:, :, 3], rgba[:, :, 3]))                                  # the alpha stays
        self.assertIs(wet_bed_follows_shore(rgba, ['MeadowTurf'], 'WetSand'), rgba)               # no bed layer: as it was


class WaterBandTests(unittest.TestCase):
    """Player-only blockers on the drawn water that covers 1997 walkable ground: never a passage closed."""

    def ponds(self):
        walk = np.ones((400, 600), bool)
        water = np.zeros_like(walk)
        water[100:300, 100:285] = True; water[100:300, 315:500] = True      # two ponds, a 30 px land bridge between
        shaped = np.zeros_like(walk)
        shaped[80:320, 80:305] = True; shaped[80:320, 295:520] = True       # drawn 20 px past both
        return walk & ~water, shaped, water

    def test_the_band_follows_the_drawn_water_on_wide_land(self):
        walk, shaped, water = self.ponds()
        band, back = water_band_blockers(shaped, walk, water, 4.4, [])
        self.assertTrue(band[200, 500:520].all() and band[90, 120:220].all())
        self.assertFalse((band & ~walk).any() or (band & ~shaped).any())

    def test_a_land_bridge_between_two_waters_stays_open(self):
        walk, shaped, water = self.ponds()
        band, back = water_band_blockers(shaped, walk, water, 4.4, [])
        # shrunk, not closed: a row across the bridge keeps a walkable gap of the capsule (6 px) and more
        for y in (150, 200, 250):
            self.assertGreaterEqual(int((~band[y, 285:315]).sum()), 12)
        # and the player still gets from the north side to the south side through it
        from export_import_bundle import band_problems
        self.assertFalse(band_problems(walk, band, 6, [(300, 50), (300, 350)]).any())

    def test_an_edge_crossing_is_never_closed(self):
        walk = np.zeros((400, 600), bool); walk[:, 0:40] = True; walk[180:220, :] = True   # a path to the west edge
        shaped = np.zeros_like(walk); shaped[:, 20:40] = True                # drawn water over half the path's mouth
        band, _ = water_band_blockers(shaped, walk, ~walk, 4.4, [(300, 200)])
        self.assertFalse(band[180:220, 0:40].all(axis=1).any())

    def test_rects_cover_the_band_on_the_texel_grid(self):
        walk, shaped, water = self.ponds()
        band, _ = water_band_blockers(shaped, walk, water, 4.4, [])
        cover = np.zeros_like(band)
        for x0, y0, x1, y1 in blocker_rects(band):
            cover[y0:y1, x0:x1] = True
        self.assertGreater((cover & band).sum() / band.sum(), 0.9)
        self.assertEqual(blocker_rects(np.zeros_like(band)), [])


class WaterTileRectsTests(unittest.TestCase):
    def test_row_runs_are_merged(self):
        rows = tiles(1, **{'0_0': 5, '0_1': 5, '0_3': 5, '2_11': 5})
        self.assertEqual(water_tile_rects(rows, CLASSES), [[0, 0, 100, 50], [150, 0, 200, 50], [550, 100, 600, 150]])

    def test_no_water_no_rects(self):
        self.assertEqual(water_tile_rects(tiles(1), CLASSES), [])


if __name__ == '__main__':
    unittest.main()
