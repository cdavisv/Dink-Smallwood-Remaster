"""Scripts/make_player_blockers.py and Scripts/check_player_blockers.py (alpha QA, walk-through, 15 Nov 2026)."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_player_blockers as cpb  # noqa: E402
import make_player_blockers as mpb  # noqa: E402


class MakeTableTests(unittest.TestCase):
    def test_solid_family_meshes_take_blockers(self):
        self.assertTrue(mpb.wanted("/Game/Dink/Photoreal/Unclaimed/SM_Boulder_Red_PR.SM_Boulder_Red_PR", "family"))
        self.assertTrue(mpb.wanted("/Game/X/SM_Veg_Oak_Large_01.SM_Veg_Oak_Large_01", "family_instance"))

    def test_openings_and_walk_over_things_do_not(self):
        for name in ("SM_Wall_Dungeon_Curve", "SM_Town_Wall_Door", "SM_Veg_PineForestEdge_V_01", "SM_Heart_Gold_PR",
                     "SM_Corpse_Knight_PR", "SM_Cottage_Stonebrook_PR", "SM_Teleport_Machine_PR"):
            self.assertFalse(mpb.wanted(f"/Game/X/{name}.{name}", "family"), name)

    def test_environment_only_town_kit(self):
        self.assertTrue(mpb.wanted("/Game/X/SM_Town_Wall_Plain.SM_Town_Wall_Plain", "environment"))
        self.assertFalse(mpb.wanted("/Game/X/SM_Boulder_Large_PR.SM_Boulder_Large_PR", "environment"))


class ConnectivityTests(unittest.TestCase):
    def test_label_counts_components(self):
        m = np.zeros((400, 600), bool)
        m[10:50, 10:300] = True
        m[10:50, 320:400] = True
        _, n = cpb.label(m)
        self.assertEqual(n, 2)
        cut = m & ~cpb.polygon_mask([(150, 0), (160, 0), (160, 400), (150, 400)], 0)
        _, n = cpb.label(cut)
        self.assertEqual(n, 3)

    def test_load_masks_reads_header_and_runs(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            w, h = 200, 134  # 600 x 400 map pixels at 3 px per cell
            row_free = f"{w}F"
            mask = row_free * (h - 1) + f"{w - 10}F10B"
            (Path(d) / "walk_mask.csv").write_text(f"screen,step,mask\n12,3,{mask}\n")
            masks = cpb.load_masks(Path(d))
            self.assertEqual(sorted(masks), [12])
            self.assertEqual(masks[12].shape, (400, 600))
            self.assertTrue(masks[12][0, 0])
            self.assertFalse(masks[12][399, 599])

    def test_polygon_mask_grows(self):
        square = [(100, 100), (120, 100), (120, 120), (100, 120)]
        self.assertEqual(int(cpb.polygon_mask(square, 0)[110, 110]), 1)
        self.assertEqual(int(cpb.polygon_mask(square, 0)[110, 124]), 0)
        self.assertEqual(int(cpb.polygon_mask(square, 5)[110, 124]), 1)


if __name__ == "__main__":
    unittest.main()
