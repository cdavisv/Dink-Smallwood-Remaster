"""Scripts/export_landforms.py helpers (stdlib unittest; no data repo needed)."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np

try:
    import PIL  # noqa: F401  (the exporter reads and writes PNGs; the CI source audit has numpy only)
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("Pillow is not installed")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import export_landforms as lf  # noqa: E402


class LandformsHelpers(unittest.TestCase):
    def test_distance_is_chamfer_euclidean(self):
        src = np.zeros((21, 21), bool)
        src[10, 10] = True
        d = lf.distance(src, 30)
        self.assertEqual(d[10, 10], 0)
        self.assertAlmostEqual(float(d[10, 15]), 5.0, places=5)
        self.assertAlmostEqual(float(d[13, 13]), 3 * math.sqrt(2), places=4)
        self.assertEqual(float(lf.distance(src, 3)[10, 20]), 4.0)   # saturates at limit + 1

    def test_gauss_keeps_constants_and_mean(self):
        a = np.full((40, 50), 2.5, np.float32)
        self.assertTrue(np.allclose(lf.gauss(a, 3.0), 2.5, atol=1e-5))
        b = np.zeros((60, 60), np.float32)
        b[30, 30] = 1.0
        g = lf.gauss(b, 2.0)
        self.assertAlmostEqual(float(g.sum()), 1.0, places=4)
        self.assertEqual(np.unravel_index(int(np.argmax(g)), g.shape), (30, 30))

    def test_smooth_min_is_below_both_and_close(self):
        a = np.array([0.0, 1.0, 5.0])
        b = np.array([1.0, 1.0, 0.0])
        m = lf.smin(a, b, 0.12)
        self.assertTrue(np.all(m <= np.minimum(a, b) + 1e-9))
        self.assertTrue(np.all(m >= np.minimum(a, b) - 0.12 * math.log(2) - 1e-9))

    def test_vertex_grids_of_neighbours_share_their_edge(self):
        rng = np.random.default_rng(1)
        h = lf.gauss(rng.random((2 * lf.SH // lf.CELL_PX, 2 * lf.SW // lf.CELL_PX)).astype(np.float32), 2.0)
        a = lf.vertex_grid(h, 0, 0)
        e = lf.vertex_grid(h, 1, 0)
        s = lf.vertex_grid(h, 0, 1)
        self.assertEqual(a.shape, (lf.GH, lf.GW))
        self.assertTrue(np.array_equal(a[:, -1], e[:, 0]))
        self.assertTrue(np.array_equal(a[-1, :], s[0, :]))

    def test_value_noise_is_deterministic_and_in_range(self):
        n1 = lf.value_noise((50, 70), 12.0, 7)
        n2 = lf.value_noise((50, 70), 12.0, 7)
        self.assertTrue(np.array_equal(n1, n2))
        self.assertGreaterEqual(float(n1.min()), 0.0)
        self.assertLessEqual(float(n1.max()), 1.0)

    def test_parse_screens(self):
        self.assertIsNone(lf.parse_screens("all"))
        self.assertEqual(lf.parse_screens("3,5-7"), {3, 5, 6, 7})

    def test_drawn_shore_reads_the_mask_alpha_as_distance(self):
        import tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            # one screen whose drawn waterline runs down the middle (alpha 0.5 at x = 300 px), water to the west
            mw, mh = 96, 64
            xs = np.arange(mw) / (mw - 1) * lf.SW                       # map px of each texel (edge to edge)
            d_cm = (xs - 300.0) * 6.9                                    # ~6.9 cm per map px
            alpha = np.clip(0.5 + d_cm / lf.SHORE_RANGE_CM, 0, 1)
            rgba = np.zeros((mh, mw, 4), np.uint8)
            rgba[:, :, 3] = np.round(alpha * 255).astype(np.uint8)[None, :]
            (Path(tmp) / "ground_mask").mkdir()
            Image.fromarray(rgba, "RGBA").save(Path(tmp) / "ground_mask" / "SCR_001.png")
            scr = [{"screen": 1, "col": 0, "row": 0, "indoor": False, "sheet": "world", "ground_mask": "ground_mask/SCR_001.png"}]
            H, W = lf.SH // lf.CELL_PX, lf.SW // lf.CELL_PX
            d, n = lf.drawn_shore(scr, Path(tmp), H, W, lf.CELL_PX)
        self.assertEqual(n, 1)
        row = d[40]
        x = (np.arange(W) + 0.5) * lf.CELL_PX
        known = np.isfinite(row)
        self.assertTrue(known[np.abs(x - 300) < 20].all(), "the band around the line is measured")
        self.assertFalse(known[x < 150].any(), "the clipped alpha far out is not")
        # the sign flips at the drawn line and the distance grows ~6.9 cm per px
        self.assertLess(float(row[int(290 / lf.CELL_PX)]), 0.0)
        self.assertGreater(float(row[int(310 / lf.CELL_PX)]), 0.0)
        self.assertAlmostEqual(float(row[int(320 / lf.CELL_PX)]), (322.5 - 300) * 0.069, delta=0.05)

    def test_fade_out_carries_and_decays(self):
        known = np.zeros((1, 20), bool)
        known[0, :5] = True
        v = lf.fade_out(np.where(known, 1.0, 0.0), known, np.full((1, 20), 0.5), 40)
        self.assertEqual(float(v[0, 4]), 1.0)
        self.assertAlmostEqual(float(v[0, 5]), 0.5, places=5)
        self.assertAlmostEqual(float(v[0, 6]), 0.25, places=5)


if __name__ == "__main__":
    unittest.main()
