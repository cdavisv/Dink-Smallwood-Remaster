"""Tests for tools/analyse. Run from tools/analyse:

    python3 -m unittest discover -s tests

The real-data tests need tools/dinkex/out (run the extractor first) and
tools/data/tile_classes.csv; they build the analysis once (~12 s) in memory.
"""

import json
import os
import random
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from analyse import engine as EN                         # noqa: E402
from analyse import graph as GR                          # noqa: E402
from analyse import joins as JN                          # noqa: E402
from analyse import layout as LY                         # noqa: E402
from analyse import regions as RG                        # noqa: E402
from analyse import warps as WP                          # noqa: E402
from analyse.build import vision_setters                 # noqa: E402
from analyse.scripts import Scripts                      # noqa: E402
from analyse.build import analyse                        # noqa: E402
from analyse.ir import IR, W, H, col_row                 # noqa: E402
from analyse.labels import label                         # noqa: E402

IR_DIR = os.path.normpath(os.path.join(ROOT, "..", "dinkex", "out"))
TABLE = os.path.join(ROOT, "regions.toml")
WORLD = None


def world():
    global WORLD
    if WORLD is None:
        WORLD = analyse(IR_DIR, TABLE, log=lambda *a: None)
    return WORLD


def have_ir():
    return os.path.exists(os.path.join(IR_DIR, "world.json"))


class TestLabels(unittest.TestCase):
    def test_matches_flood_fill(self):
        from collections import deque
        rng = np.random.default_rng(7)
        for _ in range(15):
            m = rng.random((37, 53)) < 0.55
            L, n = label(m)
            B = np.zeros(m.shape, int)
            k = 0
            for y in range(m.shape[0]):
                for x in range(m.shape[1]):
                    if m[y, x] and not B[y, x]:
                        k += 1
                        q = deque([(y, x)])
                        B[y, x] = k
                        while q:
                            a, b = q.popleft()
                            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                                c, d = a + dy, b + dx
                                if 0 <= c < m.shape[0] and 0 <= d < m.shape[1] and m[c, d] and not B[c, d]:
                                    B[c, d] = k
                                    q.append((c, d))
            self.assertEqual(n, k)
            self.assertTrue(np.array_equal(L, B))


class TestLatticeSynthetic(unittest.TestCase):
    """A 4x3 sheet with a 4x 'settlement' block next to 2.75x wilderness."""

    def setUp(self):
        self.screens = [r * 32 + c + 1 for r in range(3) for c in range(4)]
        big = {self.screens[5], self.screens[6]}
        self.size = lambda n: (60.0, 40.0) if n in big else (41.25, 27.5)
        V = LY.solve_sheet(self.screens, self.size, lambda n: 4.0 if n in big else 1.0,
                           lambda v: (v[0] * 41.25, v[1] * 27.5))
        self.L = LY.Layout()
        for n in self.screens:
            self.L.corners[n] = np.array([V[v] for v in LY._corners(n)])

    def test_shared_edges_continuous_and_convex(self):
        for n in self.screens:
            self.assertTrue(self.L.is_convex(n))
            c, r = col_row(n)
            if c < 3:
                for y in np.linspace(0, H, 9):
                    d = self.L.to_world(n, W, y) - self.L.to_world(n + 1, 0, y)
                    self.assertLess(np.abs(d).max(), 1e-9)

    def test_settlement_bigger(self):
        s_big = self.L.local_scale(self.screens[5], 300, 200)["m_per_px"]
        s_small = self.L.local_scale(self.screens[0], 300, 200)["m_per_px"]
        self.assertGreater(s_big, s_small * 1.15)


@unittest.skipUnless(have_ir(), "tools/dinkex/out missing: run the extractor first")
class TestRealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = world()

    def test_counts_match_extractor(self):
        ir = self.w.ir
        self.assertEqual(len(ir.used), 644)
        self.assertEqual(sum(1 for n in ir.used if ir.indoor(n)), 74)
        self.assertEqual(sum(len(ir.screens[n]["placements"]) for n in ir.used), 5846)
        self.assertEqual(len(self.w.warps), 93)
        s = ir.summary
        self.assertEqual(s["screens_used"], 644)
        self.assertEqual(s["active_placements"], 5846)
        self.assertEqual(s["warp_placements"], 93)

    def test_every_warp_destination_is_a_used_screen(self):
        for wp in self.w.warps:
            self.assertTrue(wp["dst_valid"], wp["id"])
            self.assertIn(wp["dst_screen"], self.w.ir.screens)
        for wp in self.w.swarps:
            self.assertIn(wp["dst_screen"], self.w.ir.screens, wp["id"])

    def test_every_screen_has_exactly_one_region(self):
        rows = self.w.rows
        self.assertEqual(len(rows), 644)
        self.assertEqual(len({r["screen"] for r in rows}), 644)
        regions = {a["region"] for a in self.w.table["area"]} | {"unattached_interiors"}
        for r in rows:
            self.assertTrue(r["region"], r)
            self.assertIn(r["kind"], ("settlement", "wilderness", "sea", "dungeon", "interior"))
            if not r["indoor"]:
                self.assertIn(r["region"], regions)

    def test_interiors_cover_indoor_screens_once(self):
        seen = [n for it in self.w.interiors for n in it["screen_numbers"]]
        indoor = sorted(n for n in self.w.ir.used if self.w.ir.indoor(n))
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(sorted(seen), indoor)
        self.assertEqual(len(indoor), 74)

    def test_no_reached_walkable_crossing_is_cut(self):
        sheet = self.w.screen_sheet
        cut = [c for c in self.w.crossings if c["reached"] and sheet[c["a"]] != sheet[c["b"]]]
        self.assertEqual(cut, [])

    def test_layout_continuous_along_walkable_edges(self):
        L = self.w.layout
        sheet = self.w.screen_sheet
        checked = 0
        for c in self.w.crossings:
            if not c["walkable"] or sheet[c["a"]] != sheet[c["b"]]:
                continue
            for t in np.linspace(c["from"], c["to"], 5):
                if c["axis"] == "y":
                    pa, pb = L.to_world(c["a"], W, t), L.to_world(c["b"], 0, t)
                else:
                    pa, pb = L.to_world(c["a"], t, H), L.to_world(c["b"], t, 0)
                self.assertLess(float(np.abs(pa - pb).max()), 1e-3, c)
            checked += 1
        self.assertGreater(checked, 1000)

    def test_layout_continuous_on_every_shared_edge_within_a_sheet(self):
        L = self.w.layout
        for n in self.w.ir.used:
            c, r = col_row(n)
            for m, horiz in ((n + 1, True), (n + 32, False)):
                if m not in L.corners or L.sheet_of[m] != L.sheet_of[n] or (horiz and c == 31):
                    continue
                for t in (0.0, 0.37, 1.0):
                    if horiz:
                        d = L.to_world(n, W, t * H) - L.to_world(m, 0, t * H)
                    else:
                        d = L.to_world(n, t * W, H) - L.to_world(m, t * W, 0)
                    self.assertLess(float(np.abs(d).max()), 1e-3)

    def test_invertible_on_random_samples(self):
        L = self.w.layout
        rng = random.Random(1234)
        used = self.w.ir.used
        for _ in range(1500):
            n = rng.choice(used)
            x, y = rng.uniform(0, W), rng.uniform(0, H)
            X, Y = L.to_world(n, x, y)
            x2, y2 = L.to_local(n, X, Y)
            self.assertAlmostEqual(x, x2, delta=1e-6)
            self.assertAlmostEqual(y, y2, delta=1e-6)
        for _ in range(150):
            n = rng.choice(used)
            x, y = rng.uniform(5, W - 5), rng.uniform(5, H - 5)
            X, Y = L.to_world(n, x, y)
            hit = L.locate(X, Y)
            self.assertIsNotNone(hit)
            self.assertEqual(hit[0], n)

    def test_all_quads_convex_and_sheets_separated(self):
        L = self.w.layout
        for n in self.w.ir.used:
            self.assertTrue(L.is_convex(n), n)
        gaps = self.w.table["layout"]["min_gap_m"]
        boxes = {}
        for n in self.w.ir.used:
            s = L.sheet_of[n]
            if not s.startswith("interior:"):
                boxes.setdefault(s, []).extend(L.corners[n])
        boxes = {s: LY.bbox_of(p) for s, p in boxes.items()}
        for s, b in boxes.items():
            if s != "mainland":
                self.assertGreaterEqual(LY.rect_gap(b, boxes["mainland"]), gaps - 1e-6, s)

    def test_settlements_larger_than_wilderness(self):
        L = self.w.layout
        by = {"settlement": [], "wilderness": [], "interior": []}
        for r in self.w.rows:
            if r["kind"] in by:
                by[r["kind"]].append(L.local_scale(r["screen"], W / 2, H / 2)["m_per_px"])
        self.assertGreater(np.mean(by["settlement"]), np.mean(by["wilderness"]) * 1.2)
        self.assertGreater(np.mean(by["wilderness"]), np.mean(by["interior"]))

    def test_interiors_do_not_overlap_outdoor_world(self):
        L = self.w.layout
        out = LY.bbox_of([p for n in self.w.ir.used if not self.w.ir.indoor(n) for p in L.corners[n]])
        for n in self.w.ir.used:
            if self.w.ir.indoor(n):
                self.assertGreater(LY.bbox_of(L.corners[n])[1], out[3])

    def test_deterministic_and_json_round_trip(self):
        from analyse.layout import build
        w = self.w
        L2 = build(w.ir, w.table, w.screen_kind, w.screen_sheet, w.interiors)
        for n in w.ir.used:
            self.assertTrue(np.array_equal(L2.corners[n], w.layout.corners[n]))
        data = {"screens": [{"screen": n, "sheet": L2.sheet_of[n],
                             "corners": {"nw": list(P[0]), "ne": list(P[1]), "sw": list(P[2]), "se": list(P[3])}}
                            for n, P in L2.corners.items()]}
        L3 = LY.Layout.from_json(json.loads(json.dumps(data)))
        for n in w.ir.used[::37]:
            self.assertLess(float(np.abs(L3.to_world(n, 123, 77) - L2.to_world(n, 123, 77)).max()), 1e-9)

    def test_start_reaches_known_places(self):
        reached = {n for n, _ in self.w.reached}
        for n in (439, 586, 497, 501, 417, 30, 731, 73):   # Stonebrook .. snow castle
            self.assertIn(n, reached, n)
        self.assertIn(350, reached)                          # East Wilds, through the cobbler's booth (designed join)


class StubIR:
    """Just enough of IR for layout.build and warps.dst_engine."""

    def __init__(self, screens):
        self.used = sorted(screens)
        self.screens = {n: {} for n in screens}

    def indoor(self, n):
        return False


def stub_table():
    return {"layout": {"base_m_per_px": 0.025, "weight": {"settlement": 4.0}, "min_gap_m": 100.0,
                       "interior_offset_m": 100.0, "interior_spacing_m": 10.0, "interior_row_width_m": 500.0},
            "scale": {"settlement": 4.0, "wilderness": 2.75},
            "sheets": {"mainland": {"anchor": "fixed"}, "fragments": {"direction": [-1.0, -1.0]}}}


class TestLayoutOverlapRule(unittest.TestCase):
    """A 10x10 block of settlement screens (60 x 40 m) and a lone wilderness screen one empty
    column east of it. The block grows from 41.25 to 60 m per screen about its centre, so its east
    edge passes the lone screen's nominal grid position: the lone piece lands inside the block."""

    def setUp(self):
        self.block = [r * 32 + c + 1 for r in range(10) for c in range(10)]
        self.lone = 5 * 32 + 11 + 1                                 # column 11, row 5: no grid neighbour
        self.ir = StubIR(self.block + [self.lone])
        self.kind = {n: "settlement" for n in self.block}
        self.kind[self.lone] = "wilderness"
        self.sheet = {n: "mainland" for n in self.ir.used}

    def test_unplaced_piece_really_overlaps(self):
        L = LY._build(self.ir, stub_table(), self.kind, self.sheet, [])
        pairs = LY.overlaps(L.corners)
        self.assertTrue(pairs)
        self.assertTrue(all(self.lone in (a, b) for _, a, b in pairs))

    def test_unreached_piece_is_parked_and_flagged(self):
        L = LY.build(self.ir, stub_table(), self.kind, self.sheet, [], reached=set(self.block))
        self.assertEqual(LY.overlaps(L.corners), [])
        self.assertEqual(L.sheet_of[self.lone], "fragments")
        self.assertIn(self.lone, L.displaced)
        self.assertEqual(L.displaced[self.lone]["from_sheet"], "mainland")
        for n in self.block:
            self.assertEqual(L.sheet_of[n], "mainland")
        # the result is a fixed point: building again from the final sheets needs no displacement
        final = {**self.sheet, self.lone: "fragments"}
        L2 = LY.build(self.ir, stub_table(), self.kind, final, [])
        self.assertTrue(np.array_equal(L2.corners[self.lone], L.corners[self.lone]))

    def test_overlap_of_reached_screens_stops_the_build(self):
        with self.assertRaises(LY.LayoutError):
            LY.build(self.ir, stub_table(), self.kind, self.sheet, [], reached=set(self.ir.used))

    def test_overlap_without_reach_information_stops_the_build(self):
        with self.assertRaises(LY.LayoutError):
            LY.build(self.ir, stub_table(), self.kind, self.sheet, [])

    def test_touching_quads_are_not_overlaps(self):
        L = LY._build(self.ir, stub_table(), self.kind, {**self.sheet, self.lone: "fragments"}, [])
        self.assertEqual(LY.overlaps({n: L.corners[n] for n in self.block}), [])


class TestScriptWarpTriggers(unittest.TestCase):
    def scripts(self, files):
        d = tempfile.mkdtemp()
        for name, text in files.items():
            with open(os.path.join(d, name + ".c"), "w", encoding="latin-1") as fh:
                fh.write(text)
        return Scripts(d)

    def test_procedure_and_entry_resolution(self):
        sc = self.scripts({"t": "void main( void )\n{\n  if (&x == 1)\n  {\n    &player_map = 5;\n    sp_x(1, 100);\n"
                                "    sp_y(1, 100);\n  }\n}\n\nvoid talk( void )\n{\n  go();\n}\n\n"
                                "void go( void )\n{\n  &player_map = 6;\n  sp_x(1, 1);\n  sp_y(1, 1);\n}\n"})
        ws = {w["target"]: w for w in sc.warps()}
        self.assertEqual((ws[5]["proc"], ws[5]["triggers"]), ("main", ["screen_load"]))
        self.assertEqual((ws[6]["proc"], ws[6]["entry_procs"], ws[6]["triggers"]), ("go", ["talk"], ["player_talk"]))

    def test_kind_rule(self):
        k = WP.script_warp_kind
        self.assertEqual(k("s2-cave2", ["screen_load"]), "cutscene")
        self.assertEqual(k("en-gmog", ["on_death"]), "cutscene")
        self.assertEqual(k("s3-mayor", ["player_talk"]), "script_transition")
        self.assertEqual(k("s2-sec1", ["player_touch"]), "script_transition")
        self.assertEqual(k("s1-hole", ["player_touch"]), "pit")
        self.assertEqual(k("s6-warp", ["player_talk"]), "teleport_machine")
        self.assertEqual(k("s7-warp", ["player_talk"]), "teleport")
        self.assertEqual(k("x-warp", ["screen_load"]), "teleport")

    def test_walk_off_screen_and_follow_up_move(self):
        sc = self.scripts({"t": "void talk( void )\n{\n  dink_can_walk_off_screen(1);\n  &player_map = 66;\n"
                                "  sp_x(1, 320);\n  sp_y(1, 480);\n  move_stop(1, 8, 353, 1)\n}\n"
                                "void other( void )\n{\n  &player_map = 7;\n}\n"})
        w = sc.warps()
        self.assertTrue(w[0]["walk_off_screen"])
        self.assertEqual(w[0]["then_moves"]["until"], 353)
        self.assertFalse(w[1]["walk_off_screen"])


@unittest.skipUnless(have_ir(), "tools/dinkex/out missing: run the extractor first")
class TestRealScriptWarps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = world()
        cls.sw = {x["id"]: x for x in cls.w.swarps}

    def test_cave2_line_154_is_a_cutscene_warp(self):
        x = self.sw["SW_s2-cave2_L154"]
        self.assertEqual((x["kind"], x["proc"], x["triggers"]), ("cutscene", "main", ["screen_load"]))
        self.assertFalse(x["player_triggered"])

    def test_every_non_player_trigger_is_a_cutscene_and_every_cutscene_a_non_player_trigger(self):
        for x in self.w.swarps:
            if x["kind"] in ("pit", "teleport", "teleport_machine"):
                continue
            self.assertEqual(x["kind"] == "cutscene", not x["player_triggered"], x["id"])
        cut = sorted(x["id"] for x in self.w.swarps if x["kind"] == "cutscene")
        self.assertEqual(cut, ["SW_en-gmog_L68", "SW_s1-ltr_L36", "SW_s2-bar_L104", "SW_s2-cave2_L154"])

    def test_talk_warps_stay_player_warps(self):
        for i in ("SW_s3-mayor_L140", "SW_s2-culg_L42", "SW_s2-mdoor_L82"):
            self.assertEqual(self.sw[i]["kind"], "script_transition")
            self.assertEqual(self.sw[i]["triggers"], ["player_talk"])
        self.assertEqual(self.sw["SW_s2-ca-g_L179"]["entry_procs"], ["talk"])    # enter() is called from talk


class TestDestinationValidation(unittest.TestCase):
    def rec(self, n, x, y):
        return {"dst_screen": n, "dst_x": x, "dst_y": y, "dst_screen_exists": True}

    def test_in_range_and_bounds(self):
        ir = StubIR([66, 98])
        self.assertTrue(WP.dst_in_bounds(0, 0) and WP.dst_in_bounds(599, 399))
        self.assertFalse(WP.dst_in_bounds(600, 10) or WP.dst_in_bounds(10, 400) or WP.dst_in_bounds(-1, 10))
        self.assertEqual(WP.dst_engine(ir, self.rec(66, 300, 200))["outcome"], "in_range")

    def test_walk_off_screen_keeps_the_position(self):
        out = WP.dst_engine(StubIR([66, 98]), self.rec(66, 300, 480), True, {"until": 353})
        self.assertEqual((out["outcome"], out["screen"], out["clamped_y"]), ("off_screen_entrance", 66, 399))
        self.assertEqual(out["then_script_moves"], {"until": 353})

    def test_without_the_flag_the_engine_crosses_or_clamps(self):
        crosses = WP.dst_engine(StubIR([66, 98]), self.rec(66, 300, 480))
        self.assertEqual((crosses["outcome"], crosses["screen"]), ("edge_crosses", 98))     # pmap + 32 exists
        clamps = WP.dst_engine(StubIR([66]), self.rec(66, 300, 480))
        self.assertEqual(clamps["outcome"], "edge_clamped")
        left = WP.dst_engine(StubIR([66, 65]), self.rec(66, -5, 100))
        self.assertEqual((left["outcome"], left["screen"]), ("edge_crosses", 65))
        self.assertEqual(WP.dst_engine(StubIR([66]), dict(self.rec(70, 1, 1), dst_screen_exists=False))["outcome"],
                         "no_destination")


@unittest.skipUnless(have_ir(), "tools/dinkex/out missing: run the extractor first")
class TestRealDestinations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = world()

    def test_culg_destination_is_off_map_and_entered_on_foot(self):
        x = next(s for s in self.w.swarps if s["id"] == "SW_s2-culg_L42")
        self.assertEqual((x["dst_screen"], x["dst_x"], x["dst_y"]), (66, 300, 480))
        self.assertTrue(x["dst_screen_exists"])
        self.assertFalse(x["dst_in_bounds"])
        self.assertFalse(x["dst_valid"])
        e = x["dst_engine"]
        self.assertEqual(e["outcome"], "off_screen_entrance")          # dink_can_walk_off_screen(1) at L37
        self.assertEqual((e["then_script_moves"]["dir"], e["then_script_moves"]["until"]), (8, 353))
        self.assertIsNotNone(x["dst_comp"])                            # clamped to y 399, lands on SCR_066's floor

    def test_every_other_destination_is_inside_its_screen(self):
        for x in self.w.warps + self.w.swarps:
            if x["id"] == "SW_s2-culg_L42":
                continue
            self.assertTrue(x["dst_valid"], x["id"])
            self.assertEqual(x["dst_engine"]["outcome"], "in_range", x["id"])


class TestVisionSetters(unittest.TestCase):
    def test_setter_found_through_spawn_external_and_sp_script(self):
        d = tempfile.mkdtemp()
        files = {"base": 'void main( void )\n{\n  spawn("mid");\n}\n',
                 "mid": 'void main( void )\n{\n  external("leaf", "main");\n  sp_script(&x, "force");\n}\n',
                 "leaf": "void main( void )\n{\n  &vision = 2;\n}\n",
                 "force": "void main( void )\n{\n  force_vision(0);\n}\n",
                 "other": "void main( void )\n{\n  &vision = 9;\n}\n"}
        for k, v in files.items():
            with open(os.path.join(d, k + ".c"), "w") as fh:
                fh.write(v)
        sc = Scripts(d)

        class ir:
            @staticmethod
            def scripts_on(n):
                return ["base"]
        got = vision_setters(ir, sc, 1)
        self.assertEqual({k: v["values"] for k, v in got.items()}, {"leaf": [2], "force": [0]})
        self.assertEqual(got["leaf"]["how"], "external:mid")
        self.assertNotIn("other", got)                      # not started from this screen's scripts


@unittest.skipUnless(have_ir(), "tools/dinkex/out missing: run the extractor first")
class TestRealVision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = world()
        from analyse.build import vision_variants
        cls.v = vision_variants(cls.w)

    def test_every_gated_value_is_either_set_by_a_script_or_listed_as_never_set(self):
        self.assertEqual(self.v["screen_count"], 37)
        for s in self.v["screens"]:
            for val in s["visions"]:
                who = s["vision_set_by"][val]
                self.assertEqual(not who, int(val) in s["visions_never_set"], (s["screen"], val))

    def test_known_setters(self):
        by = {s["screen"]: s for s in self.v["screens"]}
        self.assertEqual(by["SCR_001"]["vision_set_by"], {"1": ["s1-h1-s"], "2": ["s1-h1-s"]})
        self.assertEqual(by["SCR_439"]["vision_set_by"], {"1": ["s1-h1-o"], "2": ["s1-h1-o"]})
        self.assertEqual(by["SCR_440"]["vision_set_by"], {"2": ["findduck"]})

    def test_screens_whose_vision_no_script_sets(self):
        never = [x["screen"] for x in self.v["never_set"]]
        self.assertEqual(never, ["SCR_098", "SCR_099", "SCR_307", "SCR_333", "SCR_342", "SCR_368", "SCR_378",
                                 "SCR_379", "SCR_409", "SCR_438", "SCR_472", "SCR_477", "SCR_478", "SCR_504",
                                 "SCR_538", "SCR_666"])
        self.assertEqual(self.v["screens_with_unset_visions"], 16)
        # the search is not what is missing: no script anywhere that assigns &vision runs on these screens
        setters = {n for n in self.w.scripts.text if self.w.scripts.vision_values(n)}
        for sid in never:
            n = int(sid[4:])
            self.assertFalse(setters & set(self.w.scripts.running_with(self.w.ir.scripts_on(n))), sid)


@unittest.skipUnless(have_ir(), "tools/dinkex/out missing: run the extractor first")
class TestRegionNaming(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = world()
        cls.rows = {r["screen"]: r for r in cls.w.rows}

    def test_scr_001_is_named_for_its_normal_state(self):
        r = self.rows[1]
        self.assertEqual(r["sub_area"], "Dink's house")
        self.assertIsNone(RG.STATE_WORDS.search(r["sub_area"]))
        self.assertTrue(r["vision_states"].startswith("1: 13 placements (s1-h1-s); 2: 6 placements"))
        it = next(i for i in self.w.interiors if 1 in i["screen_numbers"])
        self.assertEqual(it["name"], "Dink's house")

    def test_no_screen_is_named_for_a_vision_state(self):
        self.assertEqual(self.w.naming_warnings, [])

    def test_state_name_check_flags_a_state_name(self):
        bad = [{"id": "SCR_001", "sub_area": "Dink's house (burning-house set)", "vision_states": "1: 13 placements (s1-h1-s)"},
               {"id": "SCR_002", "sub_area": "Burnt cabin", "vision_states": ""}]
        out = RG.state_name_warnings(bad)
        self.assertEqual(len(out), 1)
        self.assertIn("SCR_001", out[0])


class TestEngineReachRules(unittest.TestCase):
    """Tiny component graph: 1 -land/water-> 2 -water/land-> 3, and 3 wraps onto 4 (void)."""

    def setUp(self):
        def cr(a, b, ca, cb):
            return {"a": a, "a_comp": 1, "b": b, "b_comp": 1, "a_class": ca, "b_class": cb}
        self.crossings = [cr(1, 2, "land", "water"), cr(2, 3, "water", "land")]
        self.wraps = [cr(3, 4, "land", "void")]
        self.start = (1, 1)

    def test_design_blocks_water_engine_wades_wrap_needs_flag(self):
        seen = GR.reach({}, self.crossings, [], [], self.start)
        self.assertEqual(sorted(seen), [(1, 1)])
        wading = EN.engine_reach({}, self.crossings, self.wraps, [], [], self.start)
        self.assertEqual(sorted(wading), [(1, 1), (2, 1), (3, 1), (4, 1)])
        dry = EN.engine_reach({}, self.crossings, self.wraps, [], [], self.start, barrier=EN.DRY)
        self.assertEqual(sorted(dry), [(1, 1)])
        self.assertEqual(EN.edge_kind((3, 1), (4, 1), self.crossings, self.wraps, [], [])[0], "wrap")
        self.assertEqual(EN.edge_kind((1, 1), (2, 1), self.crossings, self.wraps, [], [])[0], "crossing")


@unittest.skipUnless(have_ir(), "tools/dinkex/out missing: run the extractor first")
class TestEastWilds(unittest.TestCase):
    """East Wilds (cols 27-31, rows 8-20). The 1997 data has no designed way in; since the owner's
    designed join of 9 Nov 2026 (regions.toml [[join]] cobbler_booth_doorway) the cobbler's booth
    is one interior and its doorway leads from the Koka room (SCR_290) to the East Wilds door
    S289_P19. The engine's two sequence-break routes are left as they are."""

    @classmethod
    def setUpClass(cls):
        cls.w = world()
        cls.rows = {r["screen"]: r for r in cls.w.rows}
        cls.ew = sorted(n for n, r in cls.rows.items() if r["region"] == "east_wilds")
        cls.rep = EN.report(cls.w)

    def levels(self):
        out = {}
        for n in self.ew:
            out.setdefault(self.rows[n]["reach_level"], []).append(n)
        return out

    def test_designed_route_through_the_booth(self):
        node = next((352, k) for k in range(1, 10) if (352, k) in self.w.reached)
        path = EN.route(self.w.reached, node)
        hops = []
        for a, b in zip(path, path[1:]):
            kind, ident = EN.edge_kind(a, b, self.w.crossings, self.w.wraps, self.w.warps, self.w.swarps)
            hops.append((a[0], b[0], kind, ident))
        i = next(k for k, h in enumerate(hops) if h[3] == "S734_P31")
        self.assertEqual(hops[i][:3], (734, 290, "warp"))                 # Koka Isle's booth door
        self.assertEqual(hops[i + 1][:3], (290, 289, "crossing"))        # the doorway
        self.assertEqual(hops[i + 2], (289, 350, "warp", "S289_P19"))     # the East Wilds door
        self.assertEqual(path[-1][0], 352)
        self.assertIn(727, [n for n, _ in path])                          # over the Koka bridge
        row = self.rows[352]
        self.assertTrue(row["reached"] and row["reached_without_script_warps"])
        self.assertEqual(row["reach_level"], "design")

    def test_east_wilds_reached_by_design(self):
        self.assertEqual(len(self.ew), 55)            # 4 x 13 + 3 outdoor cells; SCR_289 is the booth's (koka_isle)
        self.assertEqual(self.rows[289]["region"], "koka_isle")
        lv = self.levels()
        self.assertEqual(lv["design"], [284, 285, 286, 287, 288, 316, 317, 318, 319, 320, 348, 349, 350, 351, 352,
                                        380, 381, 382, 383, 575, 607, 639])
        self.assertNotIn("engine_dry", lv)            # the booth door route is designed now
        reg = self.rep["regions"]["east_wilds"]
        self.assertEqual(reg["engine_only_dry"], [])
        self.assertNotIn("route_to_largest_land_dry", reg)
        for n in (289, 316, 317, 318, 319, 320, 348, 349, 350, 351, 352, 380, 381, 382, 383):
            self.assertNotIn("SCR_%03d" % n, self.rep["engine_only_dry_screens"])
        self.assertTrue(self.rep["engine_only_dry_screens"])     # sequence breaks elsewhere stay listed

    def test_engine_wading_and_the_screens_nothing_reaches(self):
        lv = self.levels()
        self.assertEqual(len(lv["engine_wading"]), 24)
        self.assertEqual(lv["none"], [509, 510, 541, 542, 573, 574, 605, 606, 637])

    def test_the_row_wrap_is_a_real_crossing_from_the_cliff_into_the_booth(self):
        wrap = [c for c in self.w.wraps if (c["a"], c["b"]) == (288, 289)]
        self.assertEqual(len(wrap), 1)
        self.assertEqual((wrap[0]["from"], wrap[0]["to"]), (17, 400))
        self.assertEqual((wrap[0]["a_class"], wrap[0]["b_class"]), ("blocked", "void"))   # why the design skips it
        self.assertFalse(any(c["a"] == 288 and c["b"] == 289 for c in self.w.crossings))   # not a grid neighbour

    def test_glitch_routes_are_left_as_they_were(self):
        # the wrap lands in SCR_289's void, which still touches the East Wilds door (the join's jambs
        # close only the passage); the engine's dry search still takes it
        door = next(x for x in self.w.warps if x["id"] == "S289_P19")
        void = [k for k in door["src_comps"] if self.w.comps[289].terrain_class(k) == "void"]
        self.assertEqual(len(void), 1)
        self.assertIn((289, void[0]), self.w.dry_seen)
        used = [(c["a"], c["b"]) for c in self.rep["wrap_crossings_in_dry_reach"]]
        self.assertIn(("SCR_288", "SCR_289"), used)

    def test_the_rock_that_opens_the_cliff_is_a_removable_hardbox(self):
        ir = self.w.ir
        idx = next(p["index"] for p in ir.screens[277]["placements"] if p["id"] == "S277_P03")
        self.assertEqual(self.w.removable[277][idx], "script:s1-roc")

    def test_no_script_or_warp_targets_the_east_wilds(self):
        ew = set(self.ew)
        for x in self.w.swarps:
            self.assertNotIn(x["dst_screen"], ew, x["id"])
        for x in self.w.warps:
            if x["dst_screen"] in ew:
                self.assertIn(x["src_screen"], ew | {289}, x["id"])   # only the booth door and EW's own doors


def _table_with(side_changes=None):
    """regions.toml with the booth join's sides changed: side_changes = {289: {"tiles": ...}, ...}."""
    t = RG.load_table(TABLE)
    import copy as _copy
    t = _copy.deepcopy(t)
    for side in t["join"][0]["side"]:
        side.update((side_changes or {}).get(side["screen"], {}))
    return t


@unittest.skipUnless(have_ir(), "tools/dinkex/out missing: run the extractor first")
class TestDesignedJoin(unittest.TestCase):
    """regions.toml [[join]] cobbler_booth_doorway (owner decision, 9 Nov 2026)."""

    @classmethod
    def setUpClass(cls):
        cls.w = world()
        cls.join = next(j for j in cls.w.joins if j["id"] == "cobbler_booth_doorway")

    def test_the_booth_is_one_interior_with_both_doors(self):
        it = next(i for i in self.w.interiors if 289 in i["screen_numbers"])
        self.assertEqual(it["id"], "INT_289")
        self.assertEqual(it["screen_numbers"], [289, 290])
        self.assertEqual(sorted(e["warp"] for e in it["entrances"]), ["S350_P09", "S734_P31"])
        self.assertEqual(sorted(e["warp"] for e in it["exits"]), ["S289_P19", "S290_P19"])
        self.assertEqual(it["region"], "koka_isle")
        self.assertEqual(it["name"], "Cobbler's booth (Koka door east room, East Wilds door west room)")
        self.assertFalse(any(290 in i["screen_numbers"] and i is not it for i in self.w.interiors))
        area = next(a for a in self.w.table["area"] if a["region"] == "east_wilds")
        self.assertEqual(area["name"], "East Wilds (entered from the cobbler's booth)")

    def test_the_doorway_is_a_walkable_reached_crossing(self):
        cs = [c for c in self.w.crossings if (c["a"], c["b"]) == (289, 290) and c["walkable"]]
        self.assertEqual(len(cs), 1)
        c = cs[0]
        self.assertEqual((c["dir"], c["from"], c["to"], c["a_class"], c["b_class"]), ("right", 176, 214, "land", "land"))
        self.assertTrue(c["reached"])
        self.assertEqual(self.join["crossings"][0]["length"], 38)
        # the two floors are one walk group
        self.assertEqual(self.w.group_of[(289, c["a_comp"])], self.w.group_of[(290, c["b_comp"])])

    def test_tiles_and_hardness_are_patched_in_memory_only(self):
        ir = self.w.ir
        for (n, col, row, num) in ((289, 11, 1, 18), (289, 11, 2, 6), (289, 11, 3, 18),
                                   (289, 9, 4, 18), (289, 10, 4, 19), (289, 11, 4, 6),
                                   (290, 0, 1, 19), (290, 0, 2, 7), (290, 0, 3, 19), (290, 0, 4, 7)):
            with open(os.path.join(IR_DIR, "screens", "SCR_%03d.json" % n), encoding="utf-8") as fh:
                old = json.load(fh)["tiles"][row * 12 + col]                # tools/dinkex/out itself is untouched
            self.assertEqual(ir.tile_classes[old["num"]]["terrain"], "void")
            t = ir.screens[n]["tiles"][row * 12 + col]
            self.assertEqual((t["col"], t["row"], t["x"], t["y"], t["num"], t["designed_join"], t["replaces"]),
                             (col, row, old["x"], old["y"], num, "cobbler_booth_doorway", old["num"]))
            self.assertEqual(ir.tile_classes[num]["terrain"], "wood_floor")
        for n, rect in ((289, (480, 176, 600, 214)), (290, (0, 125, 97, 214))):
            raw, h = ir.raw_hardness(n), ir.hardness(n)
            x0, y0, x1, y1 = rect
            self.assertTrue((h[y0:y1, x0:x1] == 0).all())
            self.assertTrue((raw[y0:y1, x0:x1] != 0).any())                 # the walls were there
            side = next(s for s in self.join["sides"] if s["screen_number"] == n)
            changed = h != raw
            keep = ~(JN.tile_mask(side))
            keep[y0:y1, x0:x1] = False
            self.assertFalse(changed[keep].any())                             # nothing else changes
            jambs = changed & (h == 1)
            self.assertTrue((raw[jambs] == 0).all())                          # jambs only close void
            self.assertEqual(int(jambs.sum()), side["closed_px"])
            self.assertEqual(int((changed & (h == 0)).sum()), side["opened_px"])
        self.assertEqual(self.join["sides"][0]["cut_hardboxes"], ["S289_P11", "S289_P12"])
        self.assertEqual(self.join["sides"][1]["cut_hardboxes"], ["S290_P10", "S290_P14"])

    def test_the_join_is_json_ready(self):
        data = json.loads(json.dumps(self.w.joins))
        self.assertEqual(data[0]["decided"], "2026-11-09")
        self.assertEqual([s["open"] for s in data[0]["sides"]], [[480, 176, 600, 214], [0, 125, 97, 214]])

    def test_bad_overrides_stop_the_build(self):
        ir = IR(IR_DIR)
        cases = {
            "not void": {289: {"tiles": [[10, 1, 18]]}},                      # tile (10, 1) is wood already
            "not used on this screen": {289: {"tiles": [[11, 1, 999]]}},
            "not floor": {289: {"tiles": [[11, 1, 30]]}},                     # a void tile as the replacement
            "warp hardness": {289: {"open": [480, 125, 600, 214]}},          # over the door S289_P19
            "does not reach": {290: {"open": [10, 125, 97, 214]}},
            "is not floor": {290: {"open": [0, 125, 97, 260]}},               # into row 5's void
        }
        for expect, change in cases.items():
            with self.assertRaises(SystemExit, msg=expect) as cm:
                JN.resolve(ir, _table_with(change))
            self.assertIn(expect, str(cm.exception.code))
        t = _table_with()
        t["join"][0]["screens"] = [289, 291]
        with self.assertRaises(SystemExit):
            JN.resolve(ir, t)

    def test_a_bad_override_stops_the_whole_build_early(self):
        with open(TABLE, encoding="utf-8") as fh:
            text = fh.read()
        bad = text.replace("tiles = [[11, 1, 18], [11, 2, 6],", "tiles = [[11, 1, 18], [10, 2, 6],")
        self.assertNotEqual(bad, text)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "regions.toml")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(bad)
            with self.assertRaises(SystemExit) as cm:
                analyse(IR_DIR, p, log=lambda *a: None)
        self.assertIn("SCR_289 tile (10, 2) is tile 19", str(cm.exception.code))

    def test_a_join_without_a_crossing_stops_the_build(self):
        j = {"id": "x", "screen_numbers": [289, 290]}
        crossings = [{"a": 289, "b": 290, "walkable": False}]
        with self.assertRaises(SystemExit):
            JN.check_crossings([j], crossings)


@unittest.skipUnless(have_ir(), "tools/dinkex/out missing: run the extractor first")
class TestRealLayoutOverlaps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = world()

    def test_no_two_screens_overlap(self):
        self.assertEqual(LY.overlaps(self.w.layout.corners), [])

    def test_scr_299_is_parked_not_on_murkwood(self):
        L = self.w.layout
        self.assertEqual(L.sheet_of[299], "fragments")
        self.assertEqual(L.displaced[299]["overlapped"], ["SCR_333"])
        self.assertEqual(L.displaced[299]["from_sheet"], "mainland")
        self.assertEqual(L.sheet_of[333], "mainland")
        self.assertNotIn(299, {n for n, _ in self.w.reached})
        row = next(r for r in self.w.rows if r["screen"] == 299)
        self.assertEqual(row["sheet"], "fragments")

    def test_only_unreached_screens_are_parked(self):
        reached = {n for n, _ in self.w.reached} | {n for n, _ in self.w.engine_seen}
        self.assertEqual(sorted(self.w.layout.displaced), [298, 299])      # 298 is 299's grid neighbour
        self.assertFalse(set(self.w.layout.displaced) & reached)


if __name__ == "__main__":
    unittest.main()
