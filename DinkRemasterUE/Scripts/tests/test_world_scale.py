"""World scale (doc/remaster/WORLD_SCALE.md): the layout scales, the hero pace table and the pixel mapping of
Scripts/world_scale_convert_art.py.

Owner decision of 16 Nov 2026: the 1997 map scaled up (not redesigned) with the ratios wilderness/sea 2.75 -> 3.6,
dungeon 2.25 -> 2.7, settlement 4.0 -> 4.6, interior 1.75 -> 2.0. The simulation stays in 1997 pixels; only metres
change, so a running Dink must cover the same pixels per second on every screen (owner decision A75)."""
import importlib.util
import json
import math
import sys
import tomllib
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
REPO = PROJECT.parent
APPROVED = {  # kind: (scale before, scale after) as approved by the owner on 16 Nov 2026
    "settlement": (4.0, 4.6), "wilderness": (2.75, 3.6), "sea": (2.75, 3.6), "dungeon": (2.25, 2.7), "interior": (1.75, 2.0)}


def load_export(test):
    """The exporter reads and writes PNGs: the CI source audit has numpy only, so these tests skip without Pillow."""
    try:
        import PIL  # noqa: F401
    except ImportError:
        test.skipTest("Pillow is not installed")
    return load_script("export_import_bundle")


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, PROJECT / "Scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(PROJECT / "Scripts"))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(PROJECT / "Scripts"))
    return module


@unittest.skipUnless((REPO / "tools/analyse/regions.toml").is_file(), "needs the repository's tools/analyse")
class RegionScales(unittest.TestCase):
    def setUp(self):
        self.table = tomllib.loads((REPO / "tools/analyse/regions.toml").read_text(encoding="utf-8"))

    def test_enlarged_scales_are_the_approved_ones(self):
        for kind, (before, after) in APPROVED.items():
            self.assertAlmostEqual(self.table["scale_enlarged"][kind], after, msg=kind)
            self.assertAlmostEqual(self.table["scale"][kind], before, msg=kind)

    def test_switch_is_on_by_owner_decision(self):
        # Owner, 23 Nov 2026 ("Yes, approved ratios", option A of doc/remaster/WORLD_SCALE.md section 11): the enlarged world is on,
        # with one re-baseline of the probe's md5 table (Plugins/DinkParity/Docs/packaged_probe.md)
        self.assertIs(self.table["world_scale"]["enlarged"], True)

    def test_loader_applies_the_switch(self):
        sys.path.insert(0, str(REPO / "tools/analyse"))
        try:
            from analyse import regions
        except ImportError as e:  # the analyser reads PNGs (Pillow): absent in the CI source audit
            self.skipTest(str(e))
        finally:
            sys.path.remove(str(REPO / "tools/analyse"))
        import tempfile
        text = (REPO / "tools/analyse/regions.toml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as d:
            for on in (False, True):
                p = Path(d) / ("on.toml" if on else "off.toml")
                p.write_text(text.replace("enlarged = true", "enlarged = %s" % ("true" if on else "false")), encoding="utf-8")
                t = regions.load_table(str(p))
                for kind, (before, after) in APPROVED.items():
                    self.assertAlmostEqual(t["scale"][kind], after if on else before, msg=(on, kind))

    def test_pace_reference_is_the_scale_the_run_was_tuned_at(self):
        ref = self.table["pace"]["reference"]
        for kind, (before, _after) in APPROVED.items():
            self.assertAlmostEqual(ref[kind], before, msg=kind)
        self.assertFalse(self.table["pace"]["walk_follows_scale"], "the walk stays a human 1.7 m/s")


class HeroPaceTable(unittest.TestCase):
    """Content/Dink/Data/Gameplay/hero_pace.json, read by ADinkGreyboxCharacter::PaceScale(): written by the export for
    the layout in use. With the switch off it is 1 everywhere (the hero moves exactly as before)."""

    def setUp(self):
        self.pace = json.loads((PROJECT / "Content/Dink/Data/Gameplay/hero_pace.json").read_text(encoding="utf-8"))

    def test_committed_table_is_the_enlarged_one_while_the_switch_is_on(self):
        for kind, (before, after) in APPROVED.items():
            self.assertAlmostEqual(self.pace["scale"][kind], after, msg=kind)
            self.assertAlmostEqual(self.pace["run"][kind], round(after / before, 4), places=4, msg=kind)
            self.assertEqual(self.pace["walk"][kind], 1.0, kind)
        self.assertEqual(len(self.pace["screens"]), 644)
        # WORLD_SCALE.md section 4: every screen's centre factor lies in 1.1416-1.3911 (the rubber sheet blends the kinds)
        self.assertTrue(all(1.14 <= v <= 1.40 for v in self.pace["screens"].values()))

    def test_enlarged_kind_factor_is_scale_over_reference(self):
        export = load_export(self)
        layout = {"scale": {k: a for k, (_b, a) in APPROVED.items()},
                  "pace": {"reference": {k: b for k, (b, _a) in APPROVED.items()}, "walk_follows_scale": False}, "screens": []}
        made = export.hero_pace(layout)
        for kind, (before, after) in APPROVED.items():
            self.assertAlmostEqual(made["run"][kind], round(after / before, 4), places=4, msg=kind)
            self.assertEqual(made["walk"][kind], 1.0, kind)

    def test_the_generator_gives_the_committed_kind_factors(self):
        export = load_export(self)
        layout = {"scale": self.pace["scale"], "pace": {"reference": self.pace["reference"], "walk_follows_scale": False},
                  "screens": [{"screen": 7, "m_per_px_center": 0.09, "pace_m_per_px_reference": 0.06875}]}
        made = export.hero_pace(layout)
        self.assertEqual(made["run"], self.pace["run"])
        self.assertEqual(made["walk"], self.pace["walk"])
        self.assertEqual(made["screens"], {"7": round(0.09 / 0.06875, 4)})

    def test_run_pixels_per_second_do_not_change(self):
        export = load_export(self)
        made = export.hero_pace({"scale": {k: a for k, (_b, a) in APPROVED.items()},
                                 "pace": {"reference": {k: b for k, (b, _a) in APPROVED.items()}}, "screens": []})
        base = 0.025  # metres per 1997 pixel before the kind multiplier
        for kind, (before, after) in APPROVED.items():
            px_new = 600.0 * made["run"][kind] / (base * after * 100.0)
            px_ref = 600.0 / (base * before * 100.0)
            self.assertAlmostEqual(px_new / px_ref, 1.0, places=3, msg=kind)


class PixelMapping(unittest.TestCase):
    """world_scale_convert_art.py moves a position through the 1997 pixel it stood on: old corners -> (u, v) -> new."""

    def setUp(self):
        self.conv = load_script("world_scale_convert_art")

    @staticmethod
    def corners(x0, y0, w, h, skew=0.0):
        return {"nw": [x0, y0], "ne": [x0 + w, y0 + skew], "sw": [x0 - skew, y0 + h], "se": [x0 + w + skew, y0 + h - skew]}

    def test_inverse_bilinear_round_trip(self):
        c = self.corners(-120.0, 40.0, 41.25, 27.5, skew=1.3)
        for u, v in ((0.0, 0.0), (1.0, 1.0), (0.31, 0.77), (0.5, 0.5), (0.99, 0.02)):
            x, y = self.conv.bilinear(c, u, v)
            uu, vv = self.conv.inverse(c, x, y)
            self.assertAlmostEqual(uu, u, places=9)
            self.assertAlmostEqual(vv, v, places=9)

    def test_point_keeps_its_pixel_and_height(self):
        old = self.corners(100.0, 200.0, 41.25, 27.5)  # a wild screen at 2.75 (6.875 cm/px)
        new = self.corners(130.0, 260.0, 54.0, 36.0)   # the same screen at 3.6 (9 cm/px)
        px = (213.0, 151.0)
        world_old = [(100.0 + px[0] / 600.0 * 41.25) * 100.0, (200.0 + px[1] / 400.0 * 27.5) * 100.0, 37.5]
        world_new, ratio, pixel = self.conv.convert_point(old, new, world_old)
        self.assertAlmostEqual(pixel[0], px[0], places=6)
        self.assertAlmostEqual(pixel[1], px[1], places=6)
        self.assertAlmostEqual(world_new[0], (130.0 + px[0] / 600.0 * 54.0) * 100.0, places=4)
        self.assertAlmostEqual(world_new[1], (260.0 + px[1] / 400.0 * 36.0) * 100.0, places=4)
        self.assertEqual(world_new[2], 37.5, "heights are real and stay")
        self.assertAlmostEqual(ratio, math.sqrt((54.0 * 36.0) / (41.25 * 27.5)), places=9)

    def test_space_runs_and_objects_are_told_apart(self):
        self.assertTrue(self.conv.is_space("/Game/Dink/Kits/Stonebrook/SM_Floor_Oak_2m_01.SM_Floor_Oak_2m_01"))
        self.assertFalse(self.conv.is_space("/Game/Dink/Props/SM_Barrel_Oak_01.SM_Barrel_Oak_01"))
        self.assertTrue("SM_Fence_SplitRail_4m_01".startswith(self.conv.RUNS))
        self.assertTrue("SM_Cottage_Stonebrook_01".startswith(self.conv.UNIFORM))


if __name__ == "__main__":
    unittest.main()
