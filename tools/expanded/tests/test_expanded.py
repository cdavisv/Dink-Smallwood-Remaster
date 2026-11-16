"""tools/expanded: python3 -m unittest discover -s tests (from tools/expanded; about 15 s, runs the converter twice)."""

import copy
import csv
import json
import os
import shutil
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from expanded import build as B  # noqa: E402
from expanded import packs as P  # noqa: E402
from expanded import story as S  # noqa: E402

REPO = B.REPO
PROJECT = B.PROJECT
PACKS = os.path.join(PROJECT, "Plugins", "DinkExpanded", "Packs")
STORY = os.path.join(PROJECT, "Content", "Dink", "Data", "Story")
ANALYSE = os.path.join(REPO, "tools", "analyse", "out")


def base():
    return P.Base(PROJECT, os.path.join(REPO, "bin", "dink", "story"), ANALYSE)


class FixturePack:
    """A throwaway pack directory (pack.toml + story/*.c) for rule tests."""

    TOML = textwrap.dedent("""
        [pack]
        id = "testbed"
        number = 9
        [[sheet]]
        id = "main"
        kind = "wilderness"
        [[screen]]
        screen = 360
        sheet = "main"
        grid = [0, 0]
        base_script = "x9-base"
        solids = [[0, 0, 600, 40]]
        [[placement]]
        screen = 360
        index = 1
        x = 300
        y = 200
        kind = "npc"
        script = "x9-npc"
        [[join]]
        id = "testbed_in"
        from = { screen = 301, rect = [252, 318, 292, 372] }
        to = { screen = 360, point = [520, 200] }
        back = { screen = 360, rect = [566, 158, 600, 242] }
        return = { screen = 301, point = [312, 345] }
        """)
    SCRIPTS = {
        "x9-base": 'void main( void )\n{\n &x9_seen = 1;\n}\n',
        "x9-glob": 'void main( void )\n{\n make_global_int("&x9_seen", 0);\n}\n',
        "x9-npc": 'void talk( void )\n{\n say_stop("`3Hello.", &current_sprite);\n &gold += 1;\n}\n',
    }

    def __init__(self, toml=None, scripts=None):
        self.root = tempfile.mkdtemp(prefix="expanded_fixture_")
        d = os.path.join(self.root, "testbed")
        os.makedirs(os.path.join(d, "story"))
        with open(os.path.join(d, "pack.toml"), "w") as fh:
            fh.write(toml if toml is not None else self.TOML)
        for name, text in (scripts if scripts is not None else self.SCRIPTS).items():
            with open(os.path.join(d, "story", name + ".c"), "w") as fh:
                fh.write(text)

    def packs(self):
        return P.find_packs(self.root)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TestRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = base()

    def problems(self, toml=None, scripts=None):
        f = FixturePack(toml, scripts)
        try:
            return P.check_against_base(f.packs(), self.base)
        finally:
            f.close()

    def test_fixture_is_clean(self):
        self.assertEqual(self.problems(), [])

    def test_1997_screen_number_refused(self):
        p = self.problems(FixturePack.TOML.replace("screen = 360", "screen = 366"))
        self.assertTrue(any("is a 1997 screen" in x for x in p), p)

    def test_script_outside_namespace_refused(self):
        s = dict(FixturePack.SCRIPTS, **{"s9-oops": "void main( void )\n{\n}\n"})
        p = self.problems(scripts=s)
        self.assertTrue(any("outside the namespace" in x for x in p), p)

    def test_1997_story_global_write_refused(self):
        s = dict(FixturePack.SCRIPTS, **{"x9-npc": "void talk( void )\n{\n &story = 9;\n}\n"})
        p = self.problems(scripts=s)
        self.assertTrue(any("writes the 1997 story global &story" in x for x in p), p)

    def test_engine_stat_write_allowed(self):
        self.assertEqual(self.problems(), [])  # x9-npc adds gold

    def test_script_attach_refused(self):
        s = dict(FixturePack.SCRIPTS, **{"x9-npc": "void talk( void )\n{\n script_attach(1000);\n}\n"})
        p = self.problems(scripts=s)
        self.assertTrue(any("script_attach" in x for x in p), p)

    def test_global_outside_namespace_or_nonzero_refused(self):
        s = dict(FixturePack.SCRIPTS, **{"x9-glob": 'void main( void )\n{\n make_global_int("&mything", 0);\n make_global_int("&x9_two", 2);\n}\n'})
        p = self.problems(scripts=s)
        self.assertTrue(any("outside the namespace &x9_" in x for x in p), p)
        self.assertTrue(any("initial value 2" in x for x in p), p)

    def test_join_on_hardness_refused(self):
        # x 230-249 on SCR_301 is the treeline's hardness outline.
        p = self.problems(FixturePack.TOML.replace("rect = [252, 318, 292, 372]", "rect = [225, 318, 260, 372]"))
        self.assertTrue(any("not open ground" in x for x in p), p)

    def test_join_next_to_1997_script_sprite_refused(self):
        # S301_P06 (en-pill1) stands at map (285, 215).
        p = self.problems(FixturePack.TOML.replace("rect = [252, 318, 292, 372]", "rect = [260, 200, 300, 240]"))
        self.assertTrue(any("S301_P06" in x for x in p), p)

    def test_join_from_pack_screen_refused(self):
        with self.assertRaises(P.PackError):
            FixturePack(FixturePack.TOML.replace("from = { screen = 301", "from = { screen = 360")).packs()

    def test_placement_on_1997_screen_refused(self):
        with self.assertRaises(P.PackError):
            FixturePack(FixturePack.TOML.replace("[[placement]]\nscreen = 360", "[[placement]]\nscreen = 301")).packs()

    def test_shipped_packs_are_clean(self):
        self.assertEqual(P.check_against_base(P.find_packs(PACKS), self.base), [])


class TestBuild(unittest.TestCase):
    """The fixture pack (x9, testbed) plus every shipped pack, built into a temporary directory."""

    @classmethod
    def setUpClass(cls):
        cls.out = tempfile.mkdtemp(prefix="expanded_out_")
        cls.fixture = FixturePack()
        cls.packs_dir = cls.fixture.root
        for p in P.find_packs(PACKS):
            shutil.copytree(p.dir, os.path.join(cls.packs_dir, os.path.basename(p.dir)))
        cls.packs, cls.stale, cls.manifest = B.build(cls.packs_dir, cls.out, ANALYSE)
        cls.knot_prefixes = tuple("d_x%d_" % p.number for p in cls.packs)
        cls.script_prefixes = tuple("x%d-" % p.number for p in cls.packs)
        cls.global_prefixes = tuple("&x%d_" % p.number for p in cls.packs)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.out, ignore_errors=True)
        cls.fixture.close()

    def read(self, rel):
        with open(os.path.join(self.out, rel), encoding="utf-8") as fh:
            return fh.read()

    def test_every_1997_container_byte_identical(self):
        with open(os.path.join(STORY, "dink.json"), encoding="utf-8-sig") as fh:
            base = json.load(fh)
        merged = json.loads(self.read("Story/dink.json"))
        self.assertEqual(merged["inkVersion"], base["inkVersion"])
        self.assertEqual(merged["root"][:-1], base["root"][:-1], "root flow unchanged")
        self.assertEqual(merged["listDefs"], base["listDefs"])
        bn, mn = base["root"][-1], merged["root"][-1]
        for k, v in bn.items():
            if k != "global decl":
                self.assertEqual(mn[k], v, k)
        extra = sorted(k for k in mn if k not in bn)
        self.assertEqual(extra, self.manifest["pack_knots"])
        self.assertTrue(extra and all(k.startswith(self.knot_prefixes) for k in extra), extra)
        # global decl: the 1997 declarations, in order, then the packs' (all 0), then /ev end.
        bd, mdl = bn["global decl"], mn["global decl"]
        tail = len(bd) - bd.index("/ev")          # /ev, end (and the container's null terminator)
        self.assertEqual(mdl[:len(bd) - tail], bd[:-tail])
        self.assertEqual(mdl[-tail:], bd[-tail:])
        added = mdl[len(bd) - tail:-tail]
        names = [t["VAR="] for t in added if isinstance(t, dict)]
        self.assertEqual(sorted(names), self.manifest["pack_vars"])
        self.assertEqual([t for t in added if not isinstance(t, dict)], [0] * len(names))

    def test_names_rows_appended_only(self):
        with open(os.path.join(STORY, "names.csv"), newline="") as fh:
            base_rows = list(csv.reader(fh))
        rows = list(csv.reader(self.read("Story/names.csv").splitlines()))
        self.assertEqual(rows[:len(base_rows)], base_rows)
        for r in rows[len(base_rows):]:
            self.assertTrue(r[4].startswith(self.script_prefixes) or r[1].startswith(self.global_prefixes), r)

    def test_tables_have_the_1997_header_and_pack_rows_only(self):
        with open(os.path.join(PROJECT, "Content", "Dink", "Data", "Gameplay", "placements.csv"), newline="") as fh:
            header = next(csv.reader(fh))
        rows = list(csv.reader(self.read("Gameplay/placements.csv").splitlines()))
        self.assertEqual(rows[0], header)
        own = {s["screen"] for p in self.packs for s in p.screens}
        for r in rows[1:]:
            d = dict(zip(header, r))
            self.assertIn(int(d["screen"]), own)
            self.assertEqual(d["origin"], "S%03d_P%02d" % (int(d["screen"]), int(d["index"])))
        screens = list(csv.reader(self.read("Gameplay/screens.csv").splitlines()))
        self.assertEqual(screens[0], ["screen", "base_script"])
        self.assertEqual({int(r[0]) for r in screens[1:]}, own)

    def test_hardness_round_trip(self):
        b = P.Base.__new__(P.Base)
        b.gameplay_dir = os.path.join(self.out, "Gameplay")
        b._hard = {}
        for p in self.packs:
            for s in p.screens:
                g = b.hardness(s["screen"])[0]
                expect = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in
                             {tuple(r) for r in s["solids"]})  # overlaps counted below
                solid = sum(1 for row in g for c in row if c == 1)
                self.assertGreater(solid, 0)
                self.assertLessEqual(solid, expect)
                for x0, y0, x1, y1 in s["solids"]:
                    self.assertEqual(g[y0][x0], 1)
                    self.assertEqual(g[y1 - 1][x1 - 1], 1)

    def test_registry_and_lines(self):
        reg = json.loads(self.read("packs.json"))
        self.assertEqual(reg["schema"], "dink-expanded/1")
        self.assertEqual([p["id"] for p in reg["packs"]], [p.id for p in self.packs])
        lines = list(csv.DictReader(self.read("lines.csv").splitlines()))
        self.assertGreater(len(lines), 0)
        self.assertTrue(all(r["status"] == "draft, owner to approve" for r in lines))

    def test_check_mode_after_build(self):
        _packs, stale, _m = B.build(self.packs_dir, self.out, ANALYSE, check=True)
        self.assertEqual(stale, [])

    def test_merge_refuses_a_changed_1997_knot(self):
        with open(os.path.join(STORY, "dink.json"), encoding="utf-8-sig") as fh:
            base_text = fh.read()
        sup = json.loads(base_text)
        sup["root"][-1]["d_s1_h1_m"] = ["done", None]
        with self.assertRaises(S.StoryError):
            S.merge(base_text, json.dumps(sup), self.packs)


class TestCommittedOutput(unittest.TestCase):
    def test_plugin_data_is_up_to_date(self):
        out = os.path.join(PROJECT, "Plugins", "DinkExpanded", "Content", "Data")
        _packs, stale, _m = B.build(PACKS, out, ANALYSE, check=True)
        self.assertEqual(stale, [], "run: cd tools/expanded && python3 -m expanded build")


if __name__ == "__main__":
    unittest.main()
