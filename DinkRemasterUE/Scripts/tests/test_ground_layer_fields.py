"""Natural ground-layer outlines (Scripts/ground_layer_fields.py, VS-09): outlines leave the 1997 tile edges, never by
more than half a tile, run on across screen borders, keep a lone 1997 tile patch, and only blend layers that meet."""
from pathlib import Path
import math
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Scripts'))
try:
    import numpy as np
    import ground_layer_fields as G  # noqa: E402
    from export_import_bundle import fold_terrain_layers, world_neighbours  # noqa: E402
except ImportError as error:    # the world export needs numpy; a machine without it cannot run it either
    raise unittest.SkipTest('ground layer fields need numpy: %s' % error)

H, W = G.MASK_H, G.MASK_W
CELLS_PER_TILE = W // 12          # 8 mask cells per 50 px tile


def tiles(pattern):
    """pattern: 8 strings of 12 characters, one per tile ('.' grass, any other letter a layer) -> layer -> 64 x 96."""
    names = {'.': 'MeadowTurf', 'r': 'RockyGrass', 'd': 'EarthPath', 's': 'DrySand', 'c': 'CobbleStreet'}
    out = {}
    for r, line in enumerate(pattern):
        for c, ch in enumerate(line):
            a = out.setdefault(names[ch], np.zeros((H, W)))
            a[r * CELLS_PER_TILE:(r + 1) * CELLS_PER_TILE, c * CELLS_PER_TILE:(c + 1) * CELLS_PER_TILE] = 1.0
    return out


def winner(weights):
    names = sorted(weights)
    return np.array(names)[np.argmax(np.stack([weights[k] for k in names]), axis=0)]


def boundary_px_of_tiles(raw):
    """Map px from each cell centre to the nearest 1997 tile boundary between two layers."""
    names = sorted(raw)
    labels = np.argmax(np.stack([raw[k] for k in names]), axis=0)
    return G.boundary_distance_px(labels, 12)


STAIRS = ['s.........  '.replace(' ', '.'), 'ss..........', 'sss.........', 'ssss........',
          'sssss.......', 'ssssss......', 'sssssss.....', 'ssssssss....']
PATCHES = ['............', '..r.........', '............', '......dd....', '.......d....', '............', '..rr........', '..rr........']


class SmoothScreenTests(unittest.TestCase):
    def single(self, pattern, n=245):
        raw = {n: tiles(pattern)}
        return raw[n], G.smooth_screen_layers(n, raw, {})

    def test_weights_are_a_partition_of_one(self):
        _, out = self.single(PATCHES)
        total = sum(out.values())
        self.assertTrue(np.allclose(total, 1.0, atol=1e-6))
        for v in out.values():
            self.assertGreaterEqual(float(v.min()), 0.0)

    def test_no_outline_moves_more_than_half_a_tile(self):
        for pattern in (PATCHES, STAIRS):
            raw, out = self.single(pattern)
            # the new winner differs from the 1997 tile only within half a tile (+ half a cell of sampling) of a boundary
            edge = G.edge_aligned(np.pad(boundary_px_of_tiles(raw), 1, mode='edge'), 1)
            changed = winner(out) != winner(G.edge_aligned_own(raw))
            self.assertTrue(changed.any(), 'the outline must leave the tile edges')
            self.assertLessEqual(float(edge[changed].max()), G.MAX_SHIFT_PX + G.CELL_PX)

    def test_a_lone_tile_patch_keeps_its_layer(self):
        _, out = self.single(PATCHES)
        self.assertIn('RockyGrass', out)
        # the single rocky tile at row 1, col 2 still wins round its centre
        cy, cx = int(1.5 * CELLS_PER_TILE), int(2.5 * CELLS_PER_TILE)
        self.assertGreater(float(out['RockyGrass'][cy - 1:cy + 2, cx - 1:cx + 2].mean()), 0.5)

    def test_corners_are_rounded_and_stairs_follow_the_diagonal(self):
        raw, out = self.single(STAIRS)
        sand = out['DrySand'] > 0.5
        # the stair outline of the tiles lies up to 25 px off the diagonal; the natural one lies closer to it on average
        ys, xs = np.mgrid[0:H, 0:W]
        px_x, px_y = xs * (600.0 / (W - 1)), ys * (400.0 / (H - 1))
        diag = (px_y - (px_x - 25.0)) / math.sqrt(2.0)      # the tile staircase's mean line: y = x - 25 px
        tile_sand = G.edge_aligned_own(raw)['DrySand'] > 0.5

        def off_line(mask):
            band = np.abs(diag) < 60
            edge = mask & ~np.roll(mask, 1, axis=1)
            return float(np.abs(diag[edge & band]).mean())
        self.assertLess(off_line(sand), off_line(tile_sand))

    def test_blending_only_between_layers_that_meet(self):
        # sand and a path never meet on this screen: no texel holds both
        _, out = self.single(['ss..........', 'ss..........', 'ss..........', 'ss..........',
                              '..........dd', '..........dd', '..........dd', '..........dd'])
        self.assertFalse(((out['DrySand'] > 0.01) & (out['EarthPath'] > 0.01)).any())

    def test_laid_patterns_bend_less(self):
        street = ['............', '............', 'cccccccccccc', 'cccccccccccc', '............', '............', '............', '............']
        raw = {300: tiles(street)}
        wavy = G.smooth_screen_layers(300, raw, {})
        straight = G.smooth_screen_layers(300, raw, {}, bend={'CobbleStreet': G.STRUCTURED_BEND})

        def wobble(w):
            m = w['CobbleStreet'] > 0.5
            top = np.argmax(m, axis=0).astype(float)
            return float(top[8:-8].std())
        self.assertLess(wobble(straight), wobble(wavy))

    def test_same_input_same_output(self):
        _, a = self.single(PATCHES)
        _, b = self.single(PATCHES)
        for k in a:
            self.assertTrue(np.array_equal(a[k], b[k]))


class AcrossBordersTests(unittest.TestCase):
    """Two screens side by side on the 1997 map (245 west of 246), one path running east across their border."""

    def setUp(self):
        west = ['............', '............', '............', 'dddddddddddd', 'dddddddddddd', '............', '............', '............']
        east = ['............', '............', '............', 'ddd.........', 'dddd........', 'd..dd.......', '....dd......', '.....d......']
        self.raw = {245: tiles(west), 246: tiles(east)}
        corners = {245: {'nw': (0, 0), 'ne': (10, 0), 'sw': (0, 7), 'se': (10, 7)},
                   246: {'nw': (10, 0), 'ne': (20, 0), 'sw': (10, 7), 'se': (20, 7)}}
        self.nb = {n: world_neighbours(n, corners) for n in (245, 246)}

    def test_neighbours_by_shared_corners_only(self):
        self.assertEqual(self.nb[245], {(1, 0): 246})
        self.assertEqual(self.nb[246], {(-1, 0): 245})
        self.assertEqual(world_neighbours(245, {245: {'nw': (0, 0), 'ne': (10, 0), 'sw': (0, 7), 'se': (10, 7)},
                                                246: {'nw': (50, 0), 'ne': (60, 0), 'sw': (50, 7), 'se': (60, 7)}}), {})
        # never across a row end: screen 32 ends its row, 33 starts the next one
        self.assertEqual(world_neighbours(32, {32: {'nw': (0, 0), 'ne': (1, 0), 'sw': (0, 1), 'se': (1, 1)},
                                               33: {'nw': (1, 0), 'ne': (2, 0), 'sw': (1, 1), 'se': (2, 1)}}), {})

    def test_the_shared_edge_holds_the_same_weights_on_both_sides(self):
        west = G.smooth_screen_layers(245, self.raw, self.nb[245])
        east = G.smooth_screen_layers(246, self.raw, self.nb[246])
        for k in set(west) | set(east):
            a = west.get(k, np.zeros((H, W)))[:, -1]
            b = east.get(k, np.zeros((H, W)))[:, 0]
            self.assertLess(float(np.abs(a - b).max()), 1e-6, k)

    def test_without_the_neighbour_the_edge_differs(self):
        # proof that the test above tests something: each screen on its own does not meet the other at the edge
        west = G.smooth_screen_layers(245, self.raw, {})
        east = G.smooth_screen_layers(246, self.raw, {})
        self.assertGreater(float(np.abs(west['EarthPath'][:, -1] - east['EarthPath'][:, 0]).max()), 0.05)

    def test_the_noise_is_the_same_at_the_same_world_point(self):
        gx, gy = np.array([599.0, 600.0, 1234.5]), np.array([10.0, 10.0, 77.0])
        a = G.value_noise(gx, gy, 36.0, 7)
        b = G.value_noise(gx.copy(), gy.copy(), 36.0, 7)
        self.assertTrue(np.array_equal(a, b))
        self.assertLess(abs(a[0] - a[1]), 0.2)        # smooth: 1 px apart, nearly the same value
        self.assertTrue(np.all(np.abs(G.value_noise(np.arange(0, 5000, 7.0), np.arange(0, 5000, 7.0), 36.0, 3)) <= 1.0))


class FoldAndWindowTests(unittest.TestCase):
    def test_a_neighbours_sliver_folds_before_the_screens_own_layer(self):
        big, small = np.full((4, 4), 10.0), np.full((4, 4), 1.0)
        w = {'MeadowTurf': big, 'RockyGrass': small, 'DrySand': big, 'CliffRock': big, 'WetSand': np.full((4, 4), 3.0)}
        # by size RockyGrass (own, small) would merge into meadow; with priorities the neighbour's wet sand goes
        out, merged, dropped = fold_terrain_layers(w, keep={'MeadowTurf': 2, 'RockyGrass': 2, 'DrySand': 2, 'CliffRock': 2, 'WetSand': 0})
        self.assertIn('RockyGrass', out)
        self.assertNotIn('WetSand', out)
        self.assertEqual(dict(merged, **dropped), {'WetSand': 'DrySand'})

    def test_a_shared_corner_is_filled_the_same_from_both_screens(self):
        # 245 and 246 side by side, no screens above them: the window corner above their border must match
        west = tiles(PATCHES)
        east = tiles(['dddddddddddd'] + ['............'] * 7)
        raw = {245: west, 246: east}
        m = G.MARGIN_CELLS
        a = G.screen_window(245, raw, {(1, 0): 246}, m)
        b = G.screen_window(246, raw, {(-1, 0): 245}, m)
        # the band above the screens, the last m columns of 245's window = the first m columns of 246's own part
        for k in set(a) | set(b):
            za = a.get(k, np.zeros_like(a['MeadowTurf']))[:m, m + W:]
            zb = b.get(k, np.zeros_like(b['MeadowTurf']))[:m, m:2 * m]
            self.assertTrue(np.array_equal(za, zb), k)


class OwnLayersKeptTests(unittest.TestCase):
    def test_an_own_layer_with_a_relative_is_not_merged_before_a_neighbours_sliver(self):
        # 452: DrySand (own, has WetSand as family) must not merge while the neighbour-only CobbleStreet sliver exists
        big, small = np.full((4, 4), 10.0), np.full((4, 4), 0.5)
        w = {'MeadowTurf': big, 'DrySand': np.full((4, 4), 2.0), 'WetSand': big, 'ShingleBeach': big, 'CobbleStreet': small}
        out, merged, dropped = fold_terrain_layers(w, keep={'MeadowTurf': 3, 'DrySand': 2, 'WetSand': 3, 'ShingleBeach': 3, 'CobbleStreet': 1})
        self.assertIn('DrySand', out)
        self.assertEqual(set(dict(merged, **dropped)), {'CobbleStreet'})

    def test_no_screen_loses_an_own_layer_it_had_room_for(self):
        """Over every screen of the committed ground_classes.json: a screen whose own tile classes map to four layers or
        fewer draws every one of them (none merged or dropped), and its layers include all of them. (A layer that only
        comes from the colour split of a transition tile may fold.)"""
        import json
        facts = json.loads((PROJECT / 'Content/Dink/Data/Environment/ground_classes.json').read_text())['screens']
        checked = 0
        for n, f in facts.items():
            if f.get('outline') != 'natural':
                continue
            own = {f['layer_of'][c] for c, k in f.get('classes', {}).items() if k and c in f.get('layer_of', {}) and f['layer_of'][c] != '@surroundings'}
            own |= set(f.get('surroundings') or {})
            if len(own) > 4:
                continue
            checked += 1
            lost = set(f.get('merged') or {}) | set(f.get('dropped') or {})
            self.assertFalse(own & lost, (n, f.get('merged'), f.get('dropped')))
            self.assertTrue(own <= set(f['layers']), (n, sorted(own - set(f['layers']))))
        self.assertGreater(checked, 400)


class EdgeAlignedTests(unittest.TestCase):
    def test_edge_texels_sit_on_the_screen_edge(self):
        # each cell holds the position of its centre, in cells from the screen's west edge (3 cells of margin)
        window = np.tile(np.arange(W + 6, dtype=float) - 3 + 0.5, (H + 6, 1))
        out = G.edge_aligned(window, 3)
        self.assertAlmostEqual(float(out[0, 0]), 0.0, places=6)
        self.assertAlmostEqual(float(out[0, -1]), float(W), places=6)

    def test_an_unsmoothed_screen_keeps_its_layers(self):
        raw = tiles(PATCHES)
        out = G.edge_aligned_own(raw)
        self.assertEqual(set(out), set(raw))
        self.assertTrue(np.allclose(sum(out.values()), 1.0))


if __name__ == '__main__':
    unittest.main()


L_TURN = ['............', '..d.........', '..d.........', '..d.........', '..dddddd....', '............', '............', '............']
S_TURN = ['............', '.ddd........', '...d........', '...d........', '...ddddd....', '.......d....', '.......ddd..', '............']
TWO_PATHS = ['............', '..d.d.......', '..d.d.......', '..d.d.......', '..d.d.......', '............', '............', '............']


class ConnectivityTests(unittest.TestCase):
    """Owner review of 16 Nov 2026: a one-tile path that turns must stay one path; two kept apart stay apart."""

    def path_parts(self, pattern, n):
        out = G.smooth_screen_layers(n, {n: tiles(pattern)}, {})
        return G.components(winner(out) == 'EarthPath')

    def test_one_tile_l_and_s_turns_stay_one_path(self):
        for pattern in (L_TURN, S_TURN):
            for n in (245, 341, 430, 694):        # several noise positions on the global map
                lab = self.path_parts(pattern, n)
                self.assertEqual(len(np.unique(lab[lab >= 0])), 1, (pattern, n))

    def test_two_paths_one_tile_apart_stay_two(self):
        for n in (245, 341, 430, 694):
            lab = self.path_parts(TWO_PATHS, n)
            self.assertEqual(len(np.unique(lab[lab >= 0])), 2, n)

    def test_report_counts_faults_before_and_after(self):
        report = {}
        for n in range(240, 260):
            G.smooth_screen_layers(n, {n: tiles(S_TURN)}, {}, report=report)
        self.assertEqual(report.get('split', 0), 0)
        self.assertEqual(report.get('merged', 0), 0)
        self.assertIn('split_before', report)

    def test_neck_stays_inside_the_1997_path(self):
        raw = tiles(S_TURN)
        src = raw['EarthPath'] > 0.5
        neck = G.dilate(G.skeleton(src), G.NECK_RADIUS_CELLS) & src
        self.assertTrue(neck.any())
        self.assertEqual(len(np.unique(G.components(neck)[neck])), 1)

    def test_path_on_transition_tiles_stays_one_path(self):
        # 341: the 1997 path is drawn on transition tiles whose colour split gives the path only 40 % of the tile
        raw = tiles(L_TURN)
        path = raw['EarthPath'] * 0.4
        raw = {'EarthPath': path, 'MeadowTurf': 1.0 - path}
        for n in (245, 341):
            lab = G.components(winner(G.smooth_screen_layers(n, {n: raw}, {})) == 'EarthPath')
            self.assertEqual(len(np.unique(lab[lab >= 0])), 1, n)
