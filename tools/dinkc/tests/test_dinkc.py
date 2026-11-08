"""Tests for the DinkC parser and tables.

Run from tools/dinkc:  python3 -m unittest discover -s tests
The full build is written to out/_test (git-ignored) and removed afterwards.
"""

import csv
import glob
import json
import os
import re
import shutil
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # tools/dinkc
REPO = os.path.dirname(os.path.dirname(ROOT))     # repo root
sys.path.insert(0, ROOT)

from dinkc import analysis as A          # noqa: E402
from dinkc import build as B             # noqa: E402
from dinkc import mapdat, parser, source  # noqa: E402
from dinkc.builtins import BUILTINS      # noqa: E402

STORY = os.path.join(REPO, "bin", "dink", "story")
MAP = os.path.join(REPO, "bin", "dink", "map.dat")
DAT = os.path.join(REPO, "bin", "dink", "dink.dat")
OUT = os.path.join(ROOT, "out", "_test")


def parse(text, name="t"):
    return parser.parse_script(name, text)


def codes(ast):
    return [d["code"] for d in ast["diagnostics"]]


def find(nodes, pred):
    out = []
    for n, ctx in A.iter_stmts(nodes):
        if pred(n):
            out.append(n)
    return out


class FullBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(OUT):
            shutil.rmtree(OUT)
        cls.summary = B.build(STORY, MAP, DAT, OUT)
        cls.asts = {}
        for f in glob.glob(os.path.join(OUT, "ast", "*.json")):
            with open(f, encoding="utf-8") as fh:
                a = json.load(fh)
            cls.asts[a["script"]] = a

        def rd(name):
            with open(os.path.join(OUT, name), encoding="utf-8") as fh:
                return list(csv.DictReader(fh)) if name.endswith(".csv") else json.load(fh)
        cls.rd = staticmethod(rd)
        cls.dialog = rd("dialog_lines.csv")
        cls.calls = rd("calls.csv")
        cls.facts = rd("facts.csv")
        cls.kinds = {r["script"]: r for r in rd("script_kinds.csv")}
        cls.diags = rd("diagnostics.json")["diagnostics"]
        cls.choices = rd("choices.json")
        cls.shops = {s["script"]: s for s in rd("shops.json")}
        cls.enemies = {e["script"]: e for e in rd("enemies.json")}
        cls.items = {i["script"]: i for i in rd("items.json")}
        cls.globals = rd("globals.json")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(OUT, ignore_errors=True)

    def diag(self, script, code):
        return [d for d in self.diags if d["script"] == script and d["code"] == code]

    # ---- coverage -------------------------------------------------------------------

    def test_all_380_scripts_have_an_ast(self):
        cfiles = glob.glob(os.path.join(STORY, "*.c"))
        self.assertEqual(len(cfiles), 380)
        self.assertEqual(len(self.asts), 380)
        self.assertEqual(self.summary["parse_failures"], 0)
        for name, a in self.asts.items():
            self.assertEqual(a["schema"], "dinkc-ast/1")
            self.assertIsInstance(a["procedures"], list)

    def test_every_statement_has_a_line(self):
        for name, a in self.asts.items():
            for p in a["procedures"]:
                self.assertIsInstance(p["line"], int)
                for n, ctx in A.iter_stmts(p["body"]):
                    self.assertIsInstance(n.get("line"), int, (name, n))

    def test_goto_count_matches_text(self):
        # The plan says 88 gotos in 22 files. That is a text count: the word occurs
        # 88 times in 22 files, but s1-h2-o.c line 55 is `// goto talk;`, so the
        # scripts hold 87 real gotos in 21 files.
        gotos = [(name, n) for name, a in self.asts.items()
                 for _p, n, _c in A.iter_procs(a) if n["type"] == "goto"]
        self.assertEqual(len(gotos), 87)
        self.assertEqual(len({name for name, _ in gotos}), 21)
        text = [(os.path.basename(f), i) for f in glob.glob(os.path.join(STORY, "*.c"))
                for i, l in enumerate(source.load_c(f).split("\n"))
                if re.search(r"\bgoto\b", l)]
        self.assertEqual(len(text), 88)
        self.assertEqual(len({f for f, _ in text}), 22)

    def test_dialog_round_trip(self):
        pat = re.compile(r"\b(say_stop_npc|say_stop_xy|say_stop|say_xy|say)\s*\(", re.I)
        scan = set()
        for f in glob.glob(os.path.join(STORY, "*.c")):
            name = os.path.basename(f)[:-2].lower()
            for i, line in enumerate(source.load_c(f).split("\n"), 1):
                s = line.lstrip(" ")
                if s.startswith("//"):
                    continue
                for m in pat.finditer(s):
                    scan.add((name, i, m.group(1).lower()))
        got = {(r["script"], int(r["line"]), r["call"]) for r in self.dialog}
        self.assertEqual(sorted(scan - got), [], "say calls missing from dialog_lines.csv")
        self.assertEqual(sorted(got - scan), [], "dialog rows with no say call in the text")
        self.assertEqual(len(self.dialog), len(scan))

    def test_dialog_colour_and_vars(self):
        row = next(r for r in self.dialog if r["script"] == "s3-st2p" and r["line"] == "47")
        self.assertEqual(row["colour_code"], "1")
        self.assertEqual(row["text"], "I'm sorry sir, but you DON'T have enough gold!")
        self.assertEqual(row["speaker"], "&current_sprite")
        gold = next(r for r in self.dialog if r["script"] == "1gold")
        self.assertEqual(gold["vars"], "&mcrap")

    # ---- facts the user asked for -------------------------------------------------

    def test_main_globals(self):
        self.assertEqual(self.globals["&strength"][0]["initial"], 3)
        self.assertEqual(self.globals["&life"][0]["initial"], 10)
        self.assertEqual(self.globals["&lifemax"][0]["initial"], 10)
        self.assertEqual(self.globals["&strength"][0]["script"], "main")
        self.assertEqual(len(self.globals), 63)

    def test_bow_costs_1000(self):
        shop = self.shops["s3-st2p"]
        bow = [p for p in shop["purchases"] if any("item-b1" in g for g in p["grants"])]
        self.assertEqual(len(bow), 1)
        self.assertEqual(bow[0]["price"], 1000)
        self.assertEqual(bow[0]["check"]["price"], 1000)
        self.assertIn("Buy a Bow and some arrows for $1000",
                      [o["text"] for o in bow[0]["options"]])

    def test_seth_stats(self):
        s = self.enemies["s7-boss"]["summary"]
        self.assertEqual(s["hitpoints"], 300)
        self.assertEqual(s["defense"], 25)
        self.assertEqual(s["touch_damage"], 30)
        self.assertEqual(self.kinds["s7-boss"]["kind"], "boss")
        exp = [c for c in self.calls if c["script"] == "s7-boss" and c["name"] == "add_exp"]
        self.assertEqual([c["args"] for c in exp], ["10000, &current_sprite"])

    def test_level_cap_32(self):
        a = self.asts["lraise"]
        raise_ = next(p for p in a["procedures"] if p["name"] == "raise")
        ifs = find(raise_["body"], lambda n: n["type"] == "if" and "&level" in n["cond_text"])
        self.assertEqual(ifs[0]["cond_text"], "&level < 32")
        inc = find([ifs[0]["then"]], lambda n: n["type"] == "assign"
                   and n["target"] == "&level")
        self.assertEqual((inc[0]["op"], inc[0]["value"]["value"]), ("+=", 1))
        life = find([ifs[0]["then"]], lambda n: n["type"] == "assign"
                    and n["target"] == "&lifemax")
        self.assertEqual(life[0]["value"]["value"], 3)

    def test_screenlock_scripts(self):
        # The brief and the bible say 21. 21 files CONTAIN "screenlock", but in
        # en-pillf.c the only occurrence is a comment (`//screenlock(1);`), so 20
        # scripts actually call it.
        callers = {c["script"] for c in self.calls if c["name"] == "screenlock"}
        self.assertEqual(len(callers), 20)
        mentions = {os.path.basename(f)[:-2] for f in glob.glob(os.path.join(STORY, "*.c"))
                    if "screenlock" in source.load_c(f).lower()}
        self.assertEqual(len(mentions), 21)
        self.assertEqual(mentions - callers, {"en-pillf"})

    # ---- choices ----------------------------------------------------------------------

    def test_choice_numbering_counts_hidden_options(self):
        ch = next(c for c in self.choices if c["script"] == "s1-wand" and c["line"] == 17)
        opts = [(o["index"], o["text"], o["hidden_unless"]) for o in ch["options"]]
        self.assertEqual(opts[2], (3, "Ask about AlkTree nuts", "&story == 2"))
        self.assertEqual(opts[3][0:2], (4, "Leave"))

    def test_escape_unreachable_branch(self):
        ch = next(c for c in self.choices if c["script"] == "escape" and c["line"] == 10)
        self.assertEqual(len(ch["options"]), 6)
        self.assertTrue(any("[7]" in n for n in ch["notes"]))

    def test_choice_title(self):
        ch = next(c for c in self.choices if c["script"] == "lraise")
        self.assertEqual(ch["set_y"], 240)
        self.assertIn("YOU ARE NOW LEVEL &level", ch["title"])
        self.assertEqual([o["text"] for o in ch["options"]],
                         ["Increase Attack", "Increase Defense", "Increase Magic"])

    # ---- known malformed source ------------------------------------------------------

    def test_known_recoveries(self):
        self.assertEqual([d["guess"] for d in self.diag("s1-h3-3", "unknown_call")],
                         ["freeze", "unfreeze"])
        self.assertEqual([d["line"] for d in self.diag("s2-cave", "malformed_as_label")], [117])
        reutrn = self.diag("s4-h2p2", "unknown_statement")
        self.assertEqual(len(reutrn), 1)
        self.assertIn("return", reutrn[0]["recovery"])
        self.assertEqual([d["line"] for d in self.diag("s2-jack", "string_quote")], [171])
        self.assertEqual(len(self.diag("s2-jack", "trailing_text")), 2)
        for s in ("s3-dorks", "s3-gh", "s3-gs"):
            self.assertTrue(self.diag(s, "unclosed_block"), s)
        self.assertEqual(len(self.diag("s1-h3-8", "unclosed_block")), 2)
        self.assertTrue(self.diag("s2-auntp", "stray_close_brace"))
        self.assertEqual(len(self.diag("s4-st3p", "goto_missing_label")), 4)
        self.assertEqual(len(self.diag("s4-st1p", "goto_missing_label")), 1)
        self.assertTrue(self.diag("s4-sign3", "missing_paren"))
        self.assertTrue(self.diag("s2-man2", "bare_identifier_arg"))
        self.assertTrue(self.diag("s3-chick", "missing_comma"))
        self.assertTrue(self.diag("s1-wand2", "midtext_backtick"))
        self.assertTrue(self.diag("s4-st3p", "unknown_statement"))   # stray "f"
        self.assertTrue(self.diag("s3-larry", "used_before_declared"))
        self.assertTrue(self.diag("s1-boat", "undeclared_variable"))
        self.assertTrue(self.diag("s2-cult", "unused_label"))

    def test_s1_h3_8_engine_nesting(self):
        # `{` instead of `}`: the second and third bed lines end up inside the first if.
        talk = next(p for p in self.asts["s1-h3-8"]["procedures"] if p["name"] == "talk")
        top_ifs = [n for n in talk["body"] if n["type"] == "if"]
        self.assertEqual(len(top_ifs), 1)
        inner = find([top_ifs[0]["then"]], lambda n: n["type"] == "if")
        self.assertEqual([n["cond_text"] for n in inner], ["&maybe == 2", "&maybe == 3"])

    def test_map_missing_scripts(self):
        missing = {d["script"] for d in self.diags if d["code"] == "map_script_missing"}
        self.assertEqual(missing, {"s2-307s", "s2-barp", "s2-mh-s", "box-e", "big"})
        donly = [d["script"] for d in self.diags if d["code"] == "d_without_c"]
        self.assertEqual(donly, ["s1-h1-1c"])
        self.assertFalse([d for d in self.diags if d["code"] == "d_differs_from_c"])

    def test_kinds(self):
        k = self.kinds
        self.assertEqual(k["main"]["kind"], "system")
        self.assertEqual(k["item-sw1"]["kind"], "weapon")
        self.assertEqual(k["item-fb"]["kind"], "magic")
        self.assertEqual(k["s3-st2p"]["kind"], "shop")
        self.assertEqual(k["en-bonc"]["kind"], "enemy")
        for dead in ("spice", "treeduck", "water", "s1-eltr", "start-3", "s3-ch1"):
            self.assertEqual(k[dead]["kind"], "dead", dead)
        self.assertEqual(k["start-4"]["kind"], "system")
        self.assertEqual(int(k["s1-ss2"]["placed"]), 1)

    def test_facts(self):
        rows = [r for r in self.facts if r["variable"] == "&old_womans_duck"
                and r["script"] == "s1-oldd"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["written_values"], "=2;=3")
        story_king = next(r for r in self.facts if r["variable"] == "&story"
                          and r["script"] == "king")
        self.assertIn("=16", story_king["written_values"].split(";"))

    def test_items(self):
        sw = self.items["item-sw1"]
        arm = [e["effect"] for e in sw["procedures"]["arm"]]
        self.assertIn("&strength += 4", arm)
        self.assertEqual({g["by"] for g in sw["given_by"]}, {"s2-out", "s4-st3p"})


class Engine(unittest.TestCase):
    """Synthetic snippets for the engine-emulation rules."""

    def test_void_ends_unclosed_block(self):
        a = parse("void main(void)\n{\n if (&a == 1)\n {\n  say(\"x\", 1);\n"
                  "void talk(void)\n{\n say(\"y\", 1);\n}\n")
        self.assertEqual([p["name"] for p in a["procedures"]], ["main", "talk"])
        self.assertIn("unclosed_block", codes(a))

    def test_misparse_if(self):
        a = parse("void main(void)\n{\nif (&a == 1) &b = 2;\n}\n")
        self.assertIn("engine_if_misparse", codes(a))
        n = a["procedures"][0]["body"][0]
        self.assertEqual(n["then"]["type"], "assign")
        self.assertFalse(n["then"]["engine_executes"])

    def test_call_compare_quirk(self):
        a = parse("void main(void)\n{\nif (count_item(\"x\") != 0)\n say(\"a\", 1);\n}\n")
        n = a["procedures"][0]["body"][0]
        self.assertEqual(n["engine"]["mode"], "call_compare")
        self.assertEqual(n["engine"]["effective"], 'count_item("x") == 0')
        self.assertIn("engine_condition_differs", codes(a))

    def test_simple_condition_ok(self):
        a = parse("void main(void)\n{\nif (&story >= 3) say(\"a\", 1);\n}\n")
        n = a["procedures"][0]["body"][0]
        self.assertEqual(n["engine"]["mode"], "simple")
        self.assertEqual(n["then"]["type"], "call")
        self.assertEqual(codes(a), [])

    def test_leading_space_condition_always_false(self):
        a = parse("void main(void)\n{\nif ( &a == 1)\n say(\"a\", 1);\n}\n")
        self.assertTrue(a["procedures"][0]["body"][0]["engine"]["always_false"])

    def test_nested_if_without_braces(self):
        a = parse("void main(void)\n{\nif (&a == 1)\n if (&b == 1)\n  say(\"x\", 1);\n}\n")
        self.assertIn("nested_if_no_braces", codes(a))

    def test_comment_kills_else(self):
        a = parse("void main(void)\n{\nif (&a == 1)\n say(\"x\", 1);\n//c\nelse\n"
                  " say(\"y\", 1);\n}\n")
        n = a["procedures"][0]["body"][0]
        self.assertTrue(n["else_engine_never_runs"])
        self.assertEqual(n["else"]["type"], "call")

    def test_else_chain(self):
        a = parse("void main(void)\n{\nif (&a == 1)\n{\n say(\"x\", 1);\n} else\n{\n"
                  " say(\"y\", 1);\n}\n}\n")
        n = a["procedures"][0]["body"][0]
        self.assertEqual(n["else"]["type"], "block")
        self.assertEqual(codes(a), [])

    def test_choice_parsing(self):
        a = parse('void talk(void)\n{\nchoice_start();\nset_y 240\nset_title_color 15\n'
                  'title_start();\nHello\ntitle_end();\n"One"\n(&story == 2) "Two"\n'
                  '(&a > 1) (&b < 3) "Three"\n"Four"\nchoice_end();\n}\n')
        ch = a["procedures"][0]["body"][0]
        self.assertEqual(ch["type"], "choice")
        self.assertEqual((ch["set_y"], ch["title_color"], ch["title"]), (240, 15, "Hello"))
        self.assertEqual([o["index"] for o in ch["options"]], [1, 2, 3, 4])
        self.assertEqual([len(o["conditions"]) for o in ch["options"]], [0, 1, 2, 0])
        self.assertEqual(ch["options"][2]["text"], "Three")

    def test_choice_bad_line_aborts(self):
        a = parse('void talk(void)\n{\nchoice_start();\n"One"\n//oops\n"Two"\n'
                  'choice_end();\n}\n')
        self.assertIn("choice_bad_line", codes(a))

    def test_goto_label_resolution(self):
        a = parse("void main(void)\n{\nloop:\nwait(1);\ngoto loop;\n}\n"
                  "void talk(void)\n{\ngoto loop;\ngoto nowhere;\n}\n")
        gotos = [n for p in a["procedures"] for n, _c in A.iter_stmts(p["body"])
                 if n["type"] == "goto"]
        self.assertEqual([g["target"]["line"] if g["target"] else None for g in gotos],
                         [3, 3, None])
        self.assertTrue(gotos[1]["cross_procedure"])
        self.assertIn("goto_missing_label", codes(a))

    def test_int_with_initializer_and_compound(self):
        a = parse("void main(void)\n{\nint &x = random(3,1);\n&x += 2;\n&x / 2;\n"
                  "&y=1;\n}\n")
        body = a["procedures"][0]["body"]
        self.assertEqual(body[0]["type"], "int")
        self.assertEqual(body[0]["value"]["name"], "random")
        self.assertEqual((body[1]["op"], body[1]["value"]["value"]), ("+=", 2))
        self.assertEqual(body[2]["op"], "/=")
        self.assertEqual(body[3]["type"], "unknown")
        self.assertIn("assign_no_spaces", codes(a))

    def test_rhs_arithmetic_noted(self):
        a = parse("void main(void)\n{\nint &x;\n&x = &a + 1;\n}\n")
        self.assertIn("engine_rhs_first_word", codes(a))
        n = a["procedures"][0]["body"][1]
        self.assertEqual(n["value"]["engine_value"]["name"], "&a")

    def test_header_with_brace_and_trailing(self):
        a = parse("void main(void) {\n say(\"a\", 1);\n}\nvoid click(void) }\n{\n}\n")
        self.assertEqual(a["procedures"][0]["body"][0]["type"], "call")
        self.assertIn("header_trailing", codes(a))
        self.assertNotIn("stray_close_brace", codes(a)[:1])

    def test_case_insensitive_builtin(self):
        a = parse("void main(void)\n{\nPlaysound(1,22050,0,0,0);\n}\n")
        n = a["procedures"][0]["body"][0]
        self.assertEqual((n["name"], n["name_written"], n["kind"]),
                         ("playsound", "Playsound", "builtin"))

    def test_colour_split(self):
        self.assertEqual(A.split_colour("`4`9Hi"), ("49", 9, "Hi"))
        self.assertEqual(A.split_colour("Hi"), ("", 14, "Hi"))

    def test_interpolation_longest_first(self):
        found, unknown = A.interpolated_vars("You have &goldx and &gold, &nope",
                                             {"&gold", "&goldx"})
        self.assertEqual(found, ["&goldx", "&gold"])
        self.assertEqual(unknown, ["&nope"])


class Formats(unittest.TestCase):
    def test_map_dat_layout(self):
        size = os.path.getsize(MAP)
        self.assertEqual(size % mapdat.MAP_RECORD, 0)
        recs = mapdat.read_map_dat(MAP)
        self.assertEqual(len(recs), 644)
        refs, n = mapdat.script_references(MAP, DAT)
        self.assertIn("s1-ss2", refs)

    def test_dink_dat(self):
        self.assertEqual(os.path.getsize(DAT), mapdat.DINK_DAT_SIZE)
        dd = mapdat.read_dink_dat(DAT)
        self.assertEqual(sum(1 for v in dd["loc"][1:] if v > 0) > 500, True)

    def test_d_decoder_matches_c(self):
        c = source.load_c(os.path.join(STORY, "main.c"))
        d = source.load_d(os.path.join(STORY, "main.d"))
        self.assertEqual(source.comparable(c), source.comparable(d))

    def test_builtins_match_engine_source(self):
        cpp = os.path.join(REPO, "source", "dink", "dink.cpp")
        if not os.path.exists(cpp):
            self.skipTest("engine source not present")
        with open(cpp, encoding="latin-1") as f:
            lines = f.read().split("\n")[7069:11458]
        names = set()
        for l in lines:
            for m in re.findall(r'compare\(ev\[1\], *(?:\([^)]*\))? *"([^"]*)"\)', l):
                names.add(m.lower())
        names -= {"void", "else", "if", "int", "goto", "return", "return;"}
        self.assertEqual(names, set(BUILTINS))


if __name__ == "__main__":
    unittest.main()
