"""Tests for tools/dinkink. Run: cd tools/dinkink && python3 -m unittest discover -s tests

The suite builds into a temporary directory once (about 10 s, including compiling every
file with inklecate) and checks the output against the tools/dinkc tables.
"""

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from dinkink import build as B          # noqa: E402
from dinkink import names as N          # noqa: E402
from dinkink import text as T           # noqa: E402
from dinkink import inkjson             # noqa: E402
from dinkink import convert as C        # noqa: E402
from dinkink.overrides import OWNER_DECISIONS  # noqa: E402

AST = ROOT.parent / "dinkc" / "out"
INKLECATE = shutil.which("inklecate") or os.path.expanduser("~/.local/bin/inklecate")
OUT = None
SUMMARY = None


def setUpModule():
    global OUT, SUMMARY
    if not (AST / "dialog_lines.csv").exists():
        raise unittest.SkipTest("tools/dinkc/out missing: run the dinkc build first")
    OUT = Path(tempfile.mkdtemp(prefix="dinkink-test-"))
    SUMMARY = B.build(AST, OUT, compile_files=True, quiet=True)


def tearDownModule():
    if OUT and OUT.exists():
        shutil.rmtree(OUT)


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ink_src(script):
    return (OUT / "ink" / (script + ".ink")).read_text(encoding="utf-8")


def const_decl(const):
    """How a fix switch is declared: `= true` when the owner turned it on
    (overrides.OWNER_DECISIONS), else `= false` (the engine's behaviour)."""
    return "CONST %s = %s" % (const, "true" if const in OWNER_DECISIONS else "false")


def unescape(src):
    """Ink source text (no tags) -> what the compiler stores."""
    out, i = [], 0
    while i < len(src):
        if src[i] == "\\" and i + 1 < len(src):
            out.append(src[i + 1])
            i += 2
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


_name_map = None


def var_map():
    """lower-case &name (global/pseudo) or (script, &name) -> Ink identifier."""
    global _name_map
    if _name_map is None:
        _name_map = {}
        for r in rows(OUT / "names.csv"):
            if r["kind"] in ("global", "pseudo"):
                _name_map[r["original"]] = r["ink"]
            elif r["kind"] == "local":
                script, var = r["original"].split(":", 1)
                _name_map[(script, var)] = r["ink"]
    return _name_map


def expected_template(script, text, vars_):
    """Original text with each substituted variable replaced by {ink_name}."""
    m = var_map()
    for v in sorted([v for v in vars_.split(";") if v], key=len, reverse=True):
        ink = m.get((script, v.lower())) or m[v.lower()]
        text = re.sub(re.escape(v), "{" + ink + "}", text, flags=re.I)
    return text


def line_content(src_line):
    """Text part of an Ink output line (before the first tag)."""
    s = src_line.strip(" \t")
    # tags start at the first unescaped ' #'
    i = 0
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == "#":
            return s[:i].rstrip(" ")
        i += 1
    return s


class TestLines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dialog = rows(AST / "dialog_lines.csv")
        cls.ids = {(r["script"], r["line"]): r for r in rows(OUT / "line_ids.csv")
                   if r["kind"] == "spoken"}
        cls.by_id = defaultdict(list)
        for f in (OUT / "ink").glob("*.ink"):
            for n, l in enumerate(f.read_text(encoding="utf-8").splitlines()):
                m = re.search(r"#id:(\S+)", l)
                if m:
                    cls.by_id[m.group(1)].append((f.stem, n, l))
        cls.review = {(r["script"], r["line"]) for r in rows(OUT / "review_queue.csv")}

    def test_count(self):
        self.assertEqual(len(self.dialog), 2125)
        self.assertEqual(len(self.ids), 2125)

    def test_every_line_exactly_once_verbatim(self):
        for r in self.dialog:
            idr = self.ids[(r["script"], r["line"])]
            hits = self.by_id[idr["id"]]
            if len(hits) == 2:
                # a switched line (wrong speaker, stray backtick): `{ fix: intent - else:
                # engine }` carries the id twice, only one runs. The engine variant (the
                # else branch) is the verbatim one; TestVerbatimFixes checks the other.
                (_, n0, _), (_, n1, _) = hits
                lines = (OUT / "ink" / (r["script"] + ".ink")).read_text(
                    encoding="utf-8").splitlines()
                self.assertEqual(n1, n0 + 2, hits)
                self.assertEqual(lines[n0 + 1].strip(), "- else:")
                self.assertRegex(lines[n0 - 1].strip(), r"^\{ fix_\w+:$")
            else:
                self.assertEqual(len(hits), 1, (r["script"], r["line"], hits))
            script, _, src = hits[-1]
            self.assertEqual(script, r["script"])
            got = T.decode_display(unescape(line_content(src)))
            want = expected_template(r["script"], r["text"], r["vars"])
            self.assertEqual(got, want, (r["script"], r["line"]))
            self.assertIn("#src:%s" % r["line"], src)

    # dinkc's dialog_lines.csv has engine_executes = 1 for these (it does not model a
    # missing comma or a stray `{`), but the engine never speaks them: dinkink gates them
    NEVER_SPOKEN_IN_1997 = {("s3-chick", "42"), ("s1-h3-8", "16"), ("s1-h3-8", "20")}

    def test_live_flag_matches_engine(self):
        for r in self.dialog:
            idr = self.ids[(r["script"], r["line"])]
            want = "0" if (r["script"], r["line"]) in self.NEVER_SPOKEN_IN_1997 \
                else r["engine_executes"]
            self.assertEqual(idr["live"], want, (r["script"], r["line"]))

    def test_not_executed_lines_are_gated_and_queued(self):
        dead = [r for r in self.dialog if r["engine_executes"] != "1"]
        self.assertEqual(len(dead), 2)
        for r in dead:
            idr = self.ids[(r["script"], r["line"])]
            script, n, src = self.by_id[idr["id"]][0]
            lines = ink_src(script).splitlines()
            self.assertRegex(lines[n - 1].strip(), r"^\{ fix_\w+:$")
            self.assertIn((r["script"], r["line"]), self.review)
            const = lines[n - 1].strip()[2:-1]
            self.assertIn(const_decl(const), ink_src(script))

    def test_speaker_and_colour_tags(self):
        for r in self.dialog:
            src = self.by_id[self.ids[(r["script"], r["line"])]["id"]][-1][2]   # engine variant
            self.assertIn("#col:%s" % r["colour"], src)
            self.assertIn("#say:%s" % r["call"], src)
            if r["call"].endswith("_xy"):
                self.assertNotIn("#spk:", src)
            else:
                spk = r["speaker"]
                if spk.isdigit():
                    self.assertIn("#spk:%s " % spk, src)
                elif spk.startswith("&"):
                    m = var_map()
                    ink = m.get((r["script"], spk.lower())) or m[spk.lower()]
                    self.assertIn("#spk:%s " % ink, src)
                else:
                    self.assertIn("#spk:0 ", src)       # bare word reads 0


class TestCompiledText(unittest.TestCase):
    """The compiled story (what Inkpot loads) carries the original text."""

    def test_compiled_json_lines(self):
        story = json.load(open(OUT / "json" / "dink.json", encoding="utf-8-sig"))
        found = {}
        for ln in inkjson.lines(story):
            lid = inkjson.tag_value(ln["tags"], "id")
            if not lid:
                continue
            s = "".join(p[1] if p[0] == "t" else "{" + p[1] + "}" for p in ln["text"])
            found[lid] = T.decode_display(T.clean_output_whitespace(s))
        ids = {r["id"]: r for r in rows(OUT / "line_ids.csv")}
        dialog = {(r["script"], r["line"]): r for r in rows(AST / "dialog_lines.csv")}
        n = 0
        for lid, r in ids.items():
            if r["kind"] != "spoken":
                continue
            d = dialog[(r["script"], r["line"])]
            self.assertIn(lid, found)
            self.assertEqual(found[lid], expected_template(r["script"], d["text"], d["vars"]),
                             lid)
            n += 1
        self.assertEqual(n, 2125)

    def test_runtime_round_trip(self):
        """Every spoken and title line through the real ink runtime (inklecate -p)."""
        dialog = {(r["script"], r["line"]): r for r in rows(AST / "dialog_lines.csv")}
        ids = rows(OUT / "line_ids.csv")
        src_by_id = {}
        for f in (OUT / "ink").glob("*.ink"):
            for l in f.read_text(encoding="utf-8").splitlines():
                m = re.search(r"#id:(\S+)", l)
                if m and "#opt:" not in l:
                    src_by_id[m.group(1)] = line_content(l)
        body, expected, used = [], [], set()
        for r in ids:
            if r["kind"] not in ("spoken", "title"):
                continue
            src = src_by_id[r["id"]]
            used |= set(re.findall(r"(?<!\\)\{(\w+)\}", src))
            body.append(src)
            if r["kind"] == "spoken":
                d = dialog[(r["script"], r["line"])]
                expected.append(expected_template(r["script"], d["text"], d["vars"]))
            else:
                expected.append(None)               # titles: checked for no loss below
        decl = ['VAR %s = "@%s@"' % (v, v) for v in sorted(used)]
        # inklecate's play loop is quadratic in one long uninterrupted output, so the
        # lines go through the runtime in chunks of 200
        out = []
        for k in range(0, len(body), 200):
            tmp = OUT / ("roundtrip%d.ink" % k)
            tmp.write_text("\n".join(decl + body[k:k + 200] + ["-> END"]) + "\n",
                           encoding="utf-8")
            r = subprocess.run([INKLECATE, "-p", str(tmp)], capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, encoding="utf-8")
            got = [re.sub(r"@(\w+)@", r"{\1}", o) for o in r.stdout.splitlines()]
            self.assertEqual(len(got), len(body[k:k + 200]), (r.stdout + r.stderr)[:500])
            out += got
        titles = [x for x in ids if x["kind"] == "title"]
        k = 0
        for got, want in zip(out, expected):
            got = T.decode_display(got)
            if want is not None:
                self.assertEqual(got, want)
            k += 1
        tl = [T.decode_display(o) for o, w in zip(out, expected) if w is None]
        m = var_map()
        rev = {}
        for r in rows(OUT / "names.csv"):
            rev[r["ink"]] = r["original"].split(":", 1)[-1]
        self.assertEqual(len(tl), len(titles))
        for t, row in zip(tl, titles):
            if not row["text"].strip(" "):
                self.assertEqual(t.strip(" "), "", row["id"])      # #blank title line
                continue
            # undo variable names to compare with the raw title text
            back = re.sub(r"\{(\w+)\}", lambda mm: rev[mm.group(1)], t)
            self.assertEqual(back.lower(), row["text"].lower(), row["id"])

    def test_random_is_the_engine_rule(self):
        """random(range, base) is an EXTERNAL (the runtime's own seedable rand() source);
        the Ink fallback keeps the engine rule: base when range is 0, else base..base+range-1."""
        decls = (OUT / "ink" / "_decls.ink").read_text(encoding="utf-8")
        self.assertIn("EXTERNAL random(p1, p2)", decls)
        for f in (OUT / "ink").glob("*.ink"):
            if f.name != "_decls.ink":
                self.assertNotIn("RANDOM(", f.read_text(encoding="utf-8"), f.name)
        self.assertIn("random(", ink_src("emake"))
        tmp = OUT / "random_check.ink"
        tmp.write_text("INCLUDE _decls.ink\n" + "\n".join(
            ["{random(0, 7)}"] + ["{random(3, 10)}"] * 30 + ["{random(1, 4)}", "-> END"]) + "\n",
            encoding="utf-8")
        (OUT / "ink" / "random_check.ink").write_text(tmp.read_text(encoding="utf-8"),
                                                     encoding="utf-8")
        r = subprocess.run([INKLECATE, "-p", str(OUT / "ink" / "random_check.ink")],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        (OUT / "ink" / "random_check.ink").unlink()
        got = [int(x) for x in r.stdout.split()]
        self.assertEqual(got[0], 7)
        self.assertTrue(all(10 <= v <= 12 for v in got[1:31]), got)
        self.assertEqual(got[31], 4)

    def test_escaping_edge_cases_through_runtime(self):
        cases = ["Megapotion!  All stats raised by one.", " Also:  leading space",
                 "trailing  ", "{braces} [brackets] a|b # hash", "// not a comment",
                 "-> not a divert", "<> no glue", "- dash", "* star", "+ plus", "= eq",
                 "~ tilde", "VAR x = 1", "TODO: this", "back\\slash", "<- thread",
                 "a /* b */ c", "(paren)", ">> not a command", "x   y    z"]
        tmp = OUT / "esc.ink"
        tmp.write_text("\n".join(T.encode_plain(c) for c in cases) + "\n-> END\n",
                       encoding="utf-8")
        r = subprocess.run([INKLECATE, "-p", str(tmp)], capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, encoding="utf-8")
        self.assertEqual([T.decode_display(x) for x in r.stdout.splitlines()], cases,
                         r.stderr)


class TestMenus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.menus = json.load(open(AST / "choices.json", encoding="utf-8"))

    @staticmethod
    def norm_cond(script, text):
        m = var_map()

        def sub(mm):
            v = mm.group(0).lower()
            return m.get((script, v)) or m[v]
        t = re.sub(r"&[A-Za-z0-9_][A-Za-z0-9_\-]*", sub, text)
        t = t.replace("&&", " and ").replace("||", " or ")
        return re.sub(r"[\s()]", "", t)

    def test_menus_and_options_in_order(self):
        self.assertEqual(len(self.menus), 115)
        n_opts = 0
        for menu in self.menus:
            src = ink_src(menu["script"]).splitlines()
            start = src.index("= m%d" % menu["line"])
            opts = []
            for k in range(start + 1, len(src)):
                l = src[k]
                if l.startswith("= "):
                    break
                if l.startswith("+ ") and "#opt:" in l:
                    opts.append((l, src[k + 1].strip()))
            self.assertEqual(len(opts), len(menu["options"]), menu["script"])
            for (l, res), o in zip(opts, menu["options"]):
                self.assertEqual(res, "~ result = %d" % o["index"])
                m = re.match(r"^\+ ((?:\{[^}]*\} )*)\[(.*) #opt:(\S+)\]$", l)
                self.assertIsNotNone(m, l)
                conds = re.findall(r"\{([^}]*)\}", m.group(1))
                self.assertEqual([re.sub(r"[\s()]", "", c) for c in conds],
                                 [self.norm_cond(menu["script"], c["text"])
                                  for c in o["conditions"]], l)
                text = T.decode_display(unescape(m.group(2)))
                text = re.sub(r"\{(savegameinfo|buttoninfo)\(\d+\)\}", r"&\1", text)
                want = o["text"]
                for v in re.findall(r"\{(\w+)\}", text):
                    text = text.replace("{%s}" % v, "@")
                want = re.sub(r"&[A-Za-z0-9_][A-Za-z0-9_\-]*",
                              lambda mm: "@" if mm.group(0).lower() in var_map()
                              or (menu["script"], mm.group(0).lower()) in var_map()
                              else mm.group(0), want)
                want = want.replace("@savegameinfo", "&savegameinfo")
                self.assertEqual(text.replace("&savegameinfo", "@").replace("&buttoninfo", "@"),
                                 want.replace("&savegameinfo", "@").replace("&buttoninfo", "@"))
                n_opts += 1
        self.assertEqual(n_opts, 359)


class TestFactsAndCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cov = {r["script"]: r for r in rows(OUT / "coverage.csv")}

    def test_coverage_accounts_for_all_scripts(self):
        scripts = {p.stem for p in (AST / "ast").glob("*.json")}
        self.assertEqual(len(scripts), 380)
        self.assertTrue(scripts <= set(self.cov))
        for s in scripts:
            r = self.cov[s]
            self.assertIn(r["status"], ("converted", "converted-dead", "dead", "empty"))
            self.assertTrue(r["reason"])
            if r["status"] in ("converted", "converted-dead"):
                self.assertEqual(int(r["lines_in"]),
                                 int(r["lines_out_live"]) + int(r["lines_out_disabled"]), s)
                self.assertEqual(r["menus_in"], r["menus_out"], s)
                self.assertEqual(r["options_in"], r["options_out"], s)
                self.assertEqual(r["commands_in"], r["commands_out"], s)
                self.assertEqual(r["compiles"], "yes", s)
            else:
                self.assertEqual(r["lines_in"], "0", s)
                self.assertEqual(r["menus_in"], "0", s)

    def test_every_procedure_of_every_script_converted(self):
        """Nov 2026 rule: kind no longer decides; every procedure of every script with
        code is in the story (stat blocks stay readable from the ASTs too)."""
        for s, r in self.cov.items():
            if r["status"] in ("converted", "converted-dead"):
                ast = json.load(open(AST / "ast" / (s + ".json"), encoding="utf-8"))
                names = {p["name"] for p in ast["procedures"]}
                self.assertEqual(int(r["procedures_converted"]), len(names), s)
                self.assertEqual(int(r["commands_left_as_data"]), 0, s)
        # the drop tables, pickups, enemies, items and engine-run system scripts
        want = {"emake": ["small", "medium", "large", "xlarge"],
                "make": ["apotion", "foodduck", "sfb", "heart", "lgold"],
                "heart": ["touch"], "sgold": ["touch"],
                "en-pill": ["main", "hit", "die"], "en-drag": ["main", "die"],
                "en-gmog": ["main"], "s1-nut": ["main", "touch"], "s2-jack": ["main"],
                "dam-bom2": ["main"], "dam-bomn": ["damage"], "item-sw1": [
                    "use", "arm", "disarm", "pickup", "holdingdrop", "drop"],
                "item-fst": ["use", "arm"], "item-fb": ["use", "arm"], "item-nut": ["use"],
                "newgame": ["main"], "main": ["main"], "dinfo": ["die"],
                "lraise": ["raise"], "escape": ["main"], "bar-e": ["hit"],
                "s4-sec1": ["hit"], "s4-gs": ["main"]}
        nm = {r["original"] for r in rows(OUT / "names.csv") if r["kind"] == "entry"}
        for s, procs in want.items():
            for pr in procs:
                self.assertIn("%s:%s" % (s, pr), nm)

    def test_every_call_target_is_in_the_story(self):
        """Every script a converted script can reach by external, spawn, sp_script,
        script_attach-style string calls, add_item or add_magic is in the story with the
        procedure the caller names, except scripts the original never shipped: five map or
        sp_script references, `ranstuff` (only the dead s1-slim calls it; the engine finds
        nothing and drops nothing) and the .d-only s1-h1-1c."""
        absent = {"s2-307s", "s2-barp", "s2-mh-s", "box-e", "big", "s1-h1-1c", "ranstuff"}
        nm = {r["original"] for r in rows(OUT / "names.csv") if r["kind"] == "entry"}
        knots = {r["original"] for r in rows(OUT / "names.csv") if r["kind"] == "knot"}
        checked = 0
        missing = set()
        for s, r in self.cov.items():
            if r["status"] not in ("converted", "converted-dead"):
                continue
            ast = json.load(open(AST / "ast" / (s + ".json"), encoding="utf-8"))
            for p in ast["procedures"]:
                for st in B.walk_stmts(p["body"]):
                    for e in B.stmt_exprs(st):
                        for x in B.walk_expr(e):
                            if x.get("type") != "call":
                                continue
                            args = x.get("args") or []
                            lits = [a.get("value") for a in args if a.get("type") == "string"]
                            tgt = None
                            if x["name"] in ("external", "spawn", "sp_script",
                                             "add_item", "add_magic") and lits:
                                tgt = lits[0].lower()
                            if not tgt:
                                continue
                            checked += 1
                            if tgt in absent:
                                missing.add(tgt)
                                continue
                            self.assertIn(tgt, knots, (s, x["name"], tgt))
                            if x["name"] == "external" and len(lits) > 1:
                                self.assertIn("%s:%s" % (tgt, lits[1].lower()), nm,
                                              (s, x["name"], tgt))
        self.assertGreater(checked, 150)
        self.assertLessEqual(missing, absent)

    def test_global_reads_and_writes_survive(self):
        m = var_map()
        procs_conv = {}
        for s, r in self.cov.items():
            if r["status"] in ("converted", "converted-dead"):
                procs_conv[s] = set(re.findall(r"^= p_(\w+)$", ink_src(s), re.M))
        checked = 0
        menu_lines = defaultdict(set)
        for mnu in json.load(open(AST / "choices.json")):
            menu_lines[mnu["script"]].add(str(mnu["line"]))
        for f in rows(AST / "facts.csv"):
            s = f["script"]
            if s not in procs_conv:
                continue
            procs = set(f["procedures"].split(";"))
            if not procs & procs_conv[s]:
                continue
            ink = m.get((s, f["variable"])) or m[f["variable"]]
            src = ink_src(s)
            uses = len(re.findall(r"(?<![\w.])%s(?![\w(])" % re.escape(ink), src))
            # dinkc counts a choice condition on the choice_start line and on the
            # option line; count each source line once
            reads = len(set(f["read_lines"].split(";")) - {""} - menu_lines[s])
            writes = len(re.findall(r"~ %s = " % re.escape(ink), src))
            if procs <= procs_conv[s]:
                w = int(f["writes"])
                # make_global_int (main.c) writes the initial value: that is the VAR
                # declaration in _decls.ink, not an assignment
                w -= sum(1 for v in f["written_values"].split(";") if v.startswith("init="))
                if f["variable"] == "&result":
                    w = 0       # written by menus; TestMenus checks those
                self.assertGreaterEqual(writes, w, (s, f["variable"]))
                self.assertGreaterEqual(uses, reads + w, (s, f["variable"]))
            else:
                self.assertGreater(uses, 0, (s, f["variable"]))
            checked += 1
        self.assertGreater(checked, 400)

    def test_everything_compiles(self):
        self.assertTrue(SUMMARY["root_compiles"])
        self.assertEqual(SUMMARY["files_failed"], 0)
        self.assertEqual(SUMMARY["files_compiled"], SUMMARY["ink_files"])
        r = subprocess.run([INKLECATE, "-o", str(OUT / "t.json"), str(OUT / "ink" / "dink.ink")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("ERROR", r.stdout + r.stderr)

    def test_name_mapping_reversible(self):
        nm = rows(OUT / "names.csv")
        by_ink, by_orig = {}, {}
        for r in nm:
            key = r["ink"]
            self.assertNotIn(key, by_ink, r)
            by_ink[key] = r["original"]
            self.assertNotIn((r["kind"], r["original"]), by_orig, r)
            by_orig[(r["kind"], r["original"])] = key
        for r in nm:
            if r["kind"] == "global":
                self.assertEqual(N.global_ident(r["original"]), r["ink"])
            if r["kind"] == "knot":
                self.assertEqual(N.knot_ident(r["original"]), r["ink"])
        # identifiers that share Ink's global namespace never collide
        flat = [r["ink"] for r in nm if r["kind"] in ("global", "pseudo", "local", "fix", "knot")]
        self.assertEqual(len(flat), len(set(flat)))
        self.assertEqual(N.global_ident("&s2-nad"), "s2_nad")
        self.assertEqual(N.global_ident("&return"), "v_return")

    def test_review_queue(self):
        rq = rows(OUT / "review_queue.csv")
        keys = {(r["script"], r["line"], r["code"]) for r in rq}
        for d in json.load(open(AST / "diagnostics.json"))["diagnostics"]:
            if d["code"] in B.SKIP_CODES or d["severity"] == "info":
                continue
            code = {"missing_paren": "engine_never_runs", "string_quote": "engine_never_runs",
                    "bare_identifier_arg": "say_sprite_zero"}.get(d["code"], d["code"])
            line = str(d.get("line") or "")
            if code == "unclosed_block" and (d["script"], d.get("line")) in B.SUPPRESSED:
                continue                  # one defect, reported once at the typo (line 13)
            if code == "undeclared_variable":
                self.assertTrue(any(k[0] == d["script"] and k[2] == code for k in keys), d)
                continue
            self.assertIn((d["script"], line, code), keys, d)
        for r in rq:
            if r["fix_const"]:
                self.assertIn(const_decl(r["fix_const"]), ink_src(r["script"]))


class TestGolden(unittest.TestCase):
    """Hand-checked conversions."""

    def body(self, script, stitch):
        src = ink_src(script)
        m = re.search(r"^= %s\n(.*?)(?=^= |\Z)" % re.escape(stitch), src, re.S | re.M)
        self.assertIsNotNone(m, stitch)
        return [l.strip(" \t") for l in m.group(1).splitlines() if l.strip(" \t")]

    def assertSequence(self, lines, expected):
        """expected items appear in this order (each a prefix of some line)."""
        i = 0
        for l in lines:
            if i < len(expected) and l.startswith(expected[i]):
                i += 1
        self.assertEqual(i, len(expected), "missing %r" % (expected[i:i + 1],))

    def test_s1_h1_m_opening(self):
        b = self.body("s1-h1-m", "p_main")
        self.assertSequence(b, [
            "~ s1_h1_m__whob = sp(26)",
            ">> sp_hitpoints {current_sprite} 0 #cmd",
            "{ story > 2:",
            ">> sp_active {s1_h1_m__whob} 0 #cmd",
            "->->",
            "{ old_womans_duck > 2:",
            "{ pig_story == 0:",
            ">> move_stop {current_sprite} 2 160 1 #cmd",
            ">> freeze {current_sprite} #cmd",
            ">> wait 200 #cmd",
            "Dink, it's getting late!  No food until you feed the pigs! #id:s1-h1-m.main.001"
            " #say:say_stop #spk:current_sprite #col:13",
            ">> wait 200 #cmd",
            ">> unfreeze {current_sprite} #cmd",
            "->->",
            "~ story = 2",
            ">> move_stop 1 8 370 1 #cmd",
            ">> freeze 1 #cmd",
            ">> move_stop {current_sprite} 2 200 1 #cmd",
            ">> wait 1000 #cmd",
            "Dink, can you do something for me? #id:s1-h1-m.main.002",
            ">> wait 500 #cmd",
            "Yes, what is it? #id:s1-h1-m.main.003 #say:say_stop #spk:1 #col:14",
        ])
        # get_version() > 108: the engine evaluates > 0; the written test is behind a switch
        self.assertIn("(not fix_s1_h1_m_l72 and (get_version() > 0))", ink_src("s1-h1-m"))

    def test_s3_st2p_shop(self):
        talk = self.body("s3-st2p", "m74")
        self.assertIn("+ [Buy a Bow and some arrows for $1000 #opt:s3-st2p.talk.c1.2]", talk)
        self.assertSequence(self.body("s3-st2p", "p_talk"), [
            "-> m74 ->", "{ result == 1:", "~ s3_st2p__hasbow = count_item(\"item-b1\")",
            "{ result == 2:", "-> d_s3_st2p.lbl_buy"])
        self.assertSequence(self.body("s3-st2p", "lbl_buy"), [
            "~ s3_st2p__junk = free_items()",
            "{ s3_st2p__junk < 1:", "-> m35 ->", "->->",
            "{ gold < 1000:", "I'm sorry sir, but you DON'T have enough gold!", "->->",
            "~ gold = gold - 1000",
            ">> add_item \"item-b1\" 438 8 #cmd"])
        cmds = [r for r in rows(OUT / "director_commands.csv")
                if r["script"] == "s3-st2p" and r["form"] == "var-write"]
        self.assertEqual([(r["command"], r["args"]) for r in cmds], [("=gold", "-= 1000")])

    def test_s3_chick_state_gated_menu(self):
        m = self.body("s3-chick", "m25")
        self.assertEqual([l for l in m if l.startswith("+")], [
            "+ [Say hi #opt:s3-chick.talk.c1.1]",
            "+ [Ask what she does #opt:s3-chick.talk.c1.2]",
            "+ {mayor == 0} [Tell her about the planned assault #opt:s3-chick.talk.c1.3]",
            "+ {mayor == 3} [See what's happened since #opt:s3-chick.talk.c1.4]",
            "+ {mayor == 4} [Show her the Scroll #opt:s3-chick.talk.c1.5]",
            "+ [Leave #opt:s3-chick.talk.c1.6]"])
        self.assertIn("~ result = 5", m)            # hidden options still count
        t = self.body("s3-chick", "p_talk")
        self.assertSequence(t, ["{ gobpass == 5:", "{ mayor == 0:", "** FIXING BUG"
                                if False else "\\** FIXING BUG", "~ gobpass = 0", "->->",
                                ">> freeze 1", "-> m25 ->", "{ result == 3:",
                                "~ s3_chick__wherex = sp_x(current_sprite, -1)",
                                "~ mayor = 1", "{ s3_chick__wherey < 200:",
                                ">> move_stop {current_sprite} 2 210 1 #cmd"])

    def test_mainloop_goto(self):
        main = self.body("s2-healp", "p_main")
        self.assertEqual(main[-1].split(" //")[0], "-> lbl_mainloop")
        loop = self.body("s2-healp", "lbl_mainloop")
        self.assertEqual(loop[-1], "-> d_s2_healp.lbl_mainloop // goto mainloop")
        self.assertIn(">> wait 500 #cmd #src:23", loop)
        hit = self.body("s2-healp", "p_hit")
        self.assertEqual(hit[-1], "-> d_s2_healp.lbl_mainloop // goto mainloop")

    def test_nested_label(self):
        # goto duck jumps into a block nested in another branch; continuation stitches
        src = ink_src("s1-lg")
        self.assertIn("= lbl_duck", src)
        self.assertIn("-> d_s1_lg.lbl_duck // goto duck", src)
        self.assertEqual(src.count("#id:s1-lg.talk.007 "), 1)

    def test_s1_bul_cutscene(self):
        self.assertSequence(self.body("s1-bul", "p_main"), [
            ">> sp_speed {current_sprite} 2 #cmd", "{ pig_story == 0:", ">> freeze 1 #cmd",
            ">> wait 200 #cmd", "Here, piggie piggies. #id:s1-bul.main.001 #say:say_stop #spk:1",
            ">> wait 200 #cmd", ">> move_stop {current_sprite} 1 542 1 #cmd #src:20",
            ">> playmidi \"bullythe.mid\" #cmd #src:21",
            "Well, lookie what we got here. #id:s1-bul.main.002 #say:say_stop "
            "#spk:current_sprite #col:6",
            "Bawahahahah!  See you around, squirt.",
            ">> move_stop {current_sprite} 3 700 1 #cmd",
            "I *HATE* that guy! #id:", ">> unfreeze 1 #cmd", ">> stopmidi #cmd",
            "~ pig_story = 1"])
        shots = (OUT / "shot_lists" / "s1-bul.md").read_text(encoding="utf-8")
        self.assertIn("this sprite (s1-bul) walks down-left to x=542 through obstacles "
                      "(script waits)", shots)
        self.assertIn("Music: \"bullythe.mid\"", shots)

    def test_s7_boss_taunts(self):
        hit = self.body("s7-boss", "p_hit")
        self.assertSequence(hit, [
            "~ s7_boss__dam = sp_hitpoints(current_sprite, -1)",
            "{ s7_boss__dam < 270:", "~ s7_boss__speed = 2",
            "~ s7_boss__dam = random(2, 1)", "{ s7_boss__dam == 1:", "->->",
            "~ s7_boss__dam = sp_hitpoints(current_sprite, -1)",
            "{ s7_boss__dam < 6:",
            "Watch Conan O'brien! #id:s7-boss.hit.001 #say:say #spk:current_sprite #col:15",
            "->->",
            "{ s7_boss__dam < 15:", "MOTHER!!!!!!!!!! #id:s7-boss.hit.002",
            "{ s7_boss__dam < 50:", "FEEL MY WRATH, SMALLWOOD!",
            "{ s7_boss__dam < 100:", "I felt that.",
            "{ s7_boss__dam < 140:",
            "Listen to the birds.. even they are calling for your heart.",
            ">> playsound 49 22050 0 {current_sprite} 0 #cmd"])

    def test_engine_bugs_kept(self):
        src = ink_src("s4-sign3")
        self.assertRegex(src, r"\{ fix_s4_sign3_l17:\n\s+Long live the ducks\. #id:")
        self.assertIn("{ fix_s2_cave_l117:\n        >> wait 200 #cmd", ink_src("s2-cave"))
        st3 = ink_src("s4-st3p")
        self.assertIn("goto mainloop: label missing", st3)
        self.assertIn("#spk:0 #col:10 #src:25 #review:s2-man2:25", ink_src("s2-man2"))
        # non-code text (pasted lyrics) is referenced by line, never copied
        ast = json.load(open(AST / "ast" / "spice.json"))
        unknown = [x["text"] for p in ast["procedures"] for x in p["body"]
                   if x["type"] == "unknown" and len(x["text"]) > 12]
        self.assertGreater(len(unknown), 5)
        for t in unknown:
            self.assertNotIn(t, ink_src("spice"))


class TestVerbatimFixes(unittest.TestCase):
    """Converter rules C1-C7 from doc/remaster/verbatim_review.md. Policy: the 1997 script
    ships verbatim, the engine's behaviour is the live default, author intent sits behind
    `CONST fix_<script>_l<line> = false`; a tag cannot be switched, so wrong text or a wrong
    speaker is switched as a whole line."""

    @classmethod
    def setUpClass(cls):
        cls.rq = rows(OUT / "review_queue.csv")
        cls.cov = {r["script"]: r for r in rows(OUT / "coverage.csv")}

    def review(self, script, line=None, code=None):
        return [r for r in self.rq if r["script"] == script
                and (line is None or r["line"] == str(line))
                and (code is None or r["code"] == code)]

    def lines(self, script):
        return [l.strip(" \t") for l in ink_src(script).splitlines()]

    def test_c1_wrong_speaker_line_is_a_real_switch(self):
        src = ink_src("s2-man2")
        self.assertIn("CONST fix_s2_man2_l25 = false", src)
        ls = self.lines("s2-man2")
        i = ls.index("{ fix_s2_man2_l25:")
        self.assertTrue(ls[i + 1].startswith("Fight!!! #id:s2-man2.main.001 #say:say_stop_npc "
                                             "#spk:current_sprite #col:10 #src:25"), ls[i + 1])
        self.assertEqual(ls[i + 2], "- else:")
        self.assertTrue(ls[i + 3].startswith("Fight!!! #id:s2-man2.main.001 #say:say_stop_npc "
                                             "#spk:0 #col:10 #src:25"), ls[i + 3])
        self.assertEqual(ls[i + 4], "}")
        for f in (OUT / "ink").glob("*.ink"):
            self.assertNotIn("spk_intent", f.read_text(encoding="utf-8"), f.name)
        rows_ = self.review("s2-man2", 25, "say_sprite_zero")
        self.assertEqual(len(rows_), 1)
        self.assertEqual(rows_[0]["fix_const"], "fix_s2_man2_l25")
        # one spoken line, counted once
        self.assertEqual(sum(1 for r in rows(OUT / "line_ids.csv")
                             if r["id"] == "s2-man2.main.001"), 1)

    def test_c2_typo_intent_emits_the_corrected_command(self):
        ls = self.lines("s1-h3-3")
        for const, wrong, right, line in (("fix_s1_h3_3_l8", "freeeze", "freeze", 8),
                                          ("fix_s1_h3_3_l10", "unfreeeze", "unfreeze", 10)):
            i = ls.index("{ %s:" % const)
            branch = ls[i + 1:ls.index("}", i)]
            self.assertIn(">> %s 1 #cmd #src:%d" % (right, line), branch)
            self.assertTrue(any(l.startswith("//") and wrong in l for l in branch), branch)
            self.assertFalse(any(l.startswith(">> " + wrong) for l in ls))
        voc = {r["command"] for r in rows(OUT / "director_vocabulary.csv")}
        self.assertNotIn("freeeze", voc)
        self.assertNotIn("unfreeeze", voc)
        cmds = [(r["line"], r["command"], r["form"]) for r in rows(OUT / "director_commands.csv")
                if r["script"] == "s1-h3-3"]
        self.assertIn(("8", "freeze", "fix-intent"), cmds)
        self.assertIn(("10", "unfreeze", "fix-intent"), cmds)
        self.assertFalse([c for c in cmds if c[1].startswith(("freeeze", "unfreeeze"))])
        for line in ("8", "10"):
            r = self.review("s1-h3-3", line, "unknown_call")[0]
            self.assertTrue(r["fix_const"])
            self.assertIn(r["author_intent"], ("freeze", "unfreeze"))

    def test_engine_args_models_get_parms(self):
        """dink.cpp get_parms 4116-4231: zeroed list, a missing `,` after a string stops
        parsing (rest 0), and a call with too few arguments gets zeros."""
        zero = {"type": "int", "value": 0}
        s, v = {"type": "string", "value": "x"}, {"type": "var", "name": "&current_sprite"}
        self.assertEqual(C.engine_args("say_stop", "sn", [s, v], 0), [s, zero])
        self.assertEqual(C.engine_args("say_stop", "sn", [s, v]), [s, v])
        self.assertEqual(C.engine_args("sp_active", "nn", [v]), [v, zero])
        self.assertEqual(C.engine_args("external", "ssnnnnnnnn", [s, s]), [s, s])
        self.assertEqual(C.engine_args("kill_this_task", None, []), [])
        with self.assertRaises(ValueError):          # too many: the engine does not run it
            C.engine_args("freeze", "n", [v, v])

    def test_c3_missing_comma_line_is_never_spoken(self):
        ls = self.lines("s3-chick")
        i = [k for k, l in enumerate(ls) if "#src:42" in l][0]
        self.assertEqual(ls[i - 1], "{ fix_s3_chick_l42:")
        self.assertEqual(ls[i + 1], "}")
        self.assertIn("CONST fix_s3_chick_l42 = true // owner decision", ink_src("s3-chick"))
        lid = [r for r in rows(OUT / "line_ids.csv") if r["script"] == "s3-chick"
               and r["line"] == "42"][0]
        self.assertEqual(lid["live"], "0")
        r = self.review("s3-chick", 42, "missing_comma")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["fix_const"], "fix_s3_chick_l42")
        self.assertEqual(r[0]["category"], "never-spoken")
        self.assertNotIn("does not need", r[0]["conversion"] + r[0]["engine_behaviour"])
        design = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
        self.assertNotIn("does not need the comma", design)
        self.assertIn("get_parms", design)

    def test_c3_short_argument_lists_get_the_engines_zero(self):
        # dam-icee.c:74 `sp_active(&temp1hold);` -> get_parms leaves the value 0 (removes it)
        self.assertIn(">> sp_active {temp1hold} 0 #cmd #src:74", ink_src("dam-icee"))
        for row in rows(OUT / "director_commands.csv"):
            if row["script"] == "dam-icee" and row["line"] == "74":
                self.assertEqual(row["args"], "{temp1hold} 0")

    def test_c4_brace_typo_hoists_nested_conditionals_behind_a_switch(self):
        src = ink_src("s1-h3-8")
        self.assertIn("CONST fix_s1_h3_8_l13 = true // owner decision", src)
        ls = self.lines("s1-h3-8")
        i = ls.index("{ s1_h3_8__maybe == 1:")
        self.assertTrue(ls[i + 1].startswith("Libby's bed, ahh yeah. #id:s1-h3-8.talk.001"))
        self.assertEqual(ls[i + 2], "}")                 # the == 1 block holds only line 12
        self.assertEqual(ls[i + 3], "{ fix_s1_h3_8_l13:")
        self.assertEqual(ls[i + 4], "{ s1_h3_8__maybe == 2:")
        self.assertTrue(ls[i + 5].startswith("Libby's bed, to dream the impossible dream... "
                                             "#id:s1-h3-8.talk.002"))
        self.assertEqual(ls[i + 6], "}")
        self.assertEqual(ls[i + 7], "{ s1_h3_8__maybe == 3:")
        self.assertTrue(ls[i + 8].startswith("Libby's bed, looks lonely. #id:s1-h3-8.talk.003"))
        self.assertEqual(ls[i + 9:i + 12], ["}", "}", "->->"])
        for n in (1, 2, 3):
            self.assertEqual(src.count("#id:s1-h3-8.talk.00%d " % n), 1)
        lid = {r["id"]: r["live"] for r in rows(OUT / "line_ids.csv")
               if r["script"] == "s1-h3-8"}
        self.assertEqual((lid["s1-h3-8.talk.001"], lid["s1-h3-8.talk.002"],
                          lid["s1-h3-8.talk.003"]), ("1", "0", "0"))
        rs = self.review("s1-h3-8")
        self.assertEqual([(r["line"], r["fix_const"]) for r in rs], [("13", "fix_s1_h3_8_l13")])
        self.assertEqual(rs[0]["category"], "never-spoken")
        self.assertFalse(self.review("s1-h3-8", code="unclosed_block"))

    def test_c4_unclosed_procedure_brace_is_low(self):
        rs = self.review("s3-dorks", 35, "unclosed_block") + \
            self.review("s3-gh", 57, "unclosed_block") + self.review("s3-gs", 58, "unclosed_block")
        self.assertEqual(len(rs), 3)
        for r in rs:
            self.assertEqual(r["priority"], "low", r)
            self.assertEqual(r["fix_const"], "")
        self.assertEqual([r for r in self.rq if r["code"] == "unclosed_block"], rs)

    def test_c5_midtext_backtick_is_a_text_switch(self):
        self.assertIn("CONST fix_s1_wand2_l187 = false", ink_src("s1-wand2"))
        ls = self.lines("s1-wand2")
        i = ls.index("{ fix_s1_wand2_l187:")
        self.assertTrue(ls[i + 1].startswith("Hello, I'm Chance Zands #id:s1-wand2.makefun.008 "
                                             "#say:say_stop #spk:current_sprite #col:9 #src:187"),
                        ls[i + 1])
        self.assertEqual(ls[i + 2], "- else:")
        self.assertTrue(ls[i + 3].startswith("Hello, I'm Chance `Zands #id:s1-wand2.makefun.008 "
                                             "#say:say_stop #spk:current_sprite #col:9 #src:187"),
                        ls[i + 3])
        r = self.review("s1-wand2", 187, "midtext_backtick")
        self.assertEqual([x["fix_const"] for x in r], ["fix_s1_wand2_l187"])

    def test_c6_goto_to_a_missing_label_has_no_empty_switch(self):
        for script, lines in (("s4-st1p", (166,)), ("s4-st3p", (74, 82, 91, 98))):
            src = ink_src(script)
            ls = self.lines(script)
            for n in lines:
                self.assertNotIn("fix_%s_l%d" % (script.replace("-", "_"), n), src)
                r = self.review(script, n, "goto_missing_label")[0]
                self.assertEqual(r["fix_const"], "")
                self.assertEqual(r["category"], "engine-matches-intent")
            marks = [k for k, l in enumerate(ls) if l.startswith("// goto mainloop: label missing")]
            self.assertEqual(len(marks), len(lines))
            for k in marks:
                self.assertEqual(ls[k + 1], "->->")          # ends the procedure, not the flow
            self.assertNotIn("-> DONE", ls)                  # bare `-> DONE` only from kill_this_task
        names = {r["ink"] for r in rows(OUT / "names.csv") if r["kind"] == "fix"}
        self.assertFalse({n for n in names if n.startswith(("fix_s4_st1p", "fix_s4_st3p"))})

    def test_c6_kill_this_task_still_ends_the_flow(self):
        n = 0
        for f in (OUT / "ink").glob("*.ink"):
            ls = [l.strip(" \t") for l in f.read_text(encoding="utf-8").splitlines()]
            for k, l in enumerate(ls):
                if l.startswith(">> kill_this_task"):
                    self.assertEqual(ls[k + 1], "-> DONE", f.name)
                    n += 1
        self.assertGreater(n, 40)

    def test_c7_unknown_command_note_is_not_invented(self):
        voc = {r["command"]: r for r in rows(OUT / "director_vocabulary.csv")}
        r = voc["sp_prop"]
        self.assertEqual(r["category"], "unknown-command")
        self.assertNotIn("set the property", r["note"])
        self.assertIn("not an engine command", r["note"])
        self.assertEqual(r["lines"], "0")
        self.assertEqual(r["fix_intent"], "2")
        # real sp_* commands keep their description
        self.assertIn("leave unchanged", voc["sp_brain"]["note"])
        # sp_prop stays a no-op: both switches false, nothing else touched
        for script, line in (("s5-end", 33), ("s5-fguy", 6)):
            self.assertIn("CONST fix_%s_l%d = false" % (script.replace("-", "_"), line),
                          ink_src(script))

    def test_c7_never_spoken_category(self):
        got = sorted((r["script"], r["line"]) for r in self.rq if r["category"] == "never-spoken")
        self.assertEqual(got, [("s1-h3-8", "13"), ("s2-jack", "171"), ("s3-chick", "42"),
                               ("s4-sign3", "17")])
        for r in self.rq:
            if r["category"] == "never-spoken":
                self.assertTrue(r["fix_const"], r)
                self.assertEqual(r["priority"], "high")

    def test_c7_dead_d_file_is_classified(self):
        r = self.cov["s1-h1-1c"]
        self.assertEqual(r["status"], "dead")
        self.assertIn("dead data", r["reason"])
        q = self.review("s1-h1-1c", code="d_without_c")[0]
        self.assertEqual(q["category"], "dead-data")
        self.assertEqual(q["priority"], "low")
        # a .d that something references stays `missing`
        self.assertEqual(self.cov["big"]["status"], "missing")

    def test_all_switches_true_still_compiles(self):
        """Flipping any fix switch to true (the intent branches) must compile cleanly."""
        tmp = OUT / "switches_true"
        shutil.copytree(OUT / "ink", tmp)
        n = 0
        for f in tmp.glob("*.ink"):
            t = f.read_text(encoding="utf-8")
            t, k = re.subn(r"^(CONST fix_\w+) = false", r"\1 = true", t, flags=re.M)
            n += k
            f.write_text(t, encoding="utf-8")
        self.assertGreater(n + len(OWNER_DECISIONS), 15)
        r = subprocess.run([INKLECATE, "-o", str(OUT / "t_true.json"), str(tmp / "dink.ink")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("ERROR", r.stdout + r.stderr)
        self.assertNotIn("WARNING", r.stdout + r.stderr)


class TestOwnerDecisions(unittest.TestCase):
    """Owner decision OD2 (doc/remaster/verbatim_review.md, 9 Nov 2026): the four pure-typo
    switches are on in the shipped build, every other `fix_` switch stays false. Each enabled
    switch carries its dink.cpp citation (overrides.OWNER_DECISIONS)."""

    ENABLED = {"fix_s2_jack_l171", "fix_s4_sign3_l17", "fix_s3_chick_l42", "fix_s1_h3_8_l13"}

    def consts(self):
        got = {}
        for f in sorted((OUT / "ink").glob("*.ink")):
            for m in re.finditer(r"^CONST (fix_\w+) = (\w+)(.*)$", f.read_text(encoding="utf-8"),
                                 flags=re.M):
                got[m.group(1)] = (m.group(2), m.group(3), f.stem)
        return got

    def test_table_is_the_four_typos(self):
        self.assertEqual(set(OWNER_DECISIONS), self.ENABLED)
        for name, d in OWNER_DECISIONS.items():
            self.assertIs(d["value"], True, name)
            self.assertEqual(d["decided"], "2026-11-09", name)
            self.assertRegex(d["dink_cpp"], r"dink\.cpp:\d+", name)
            self.assertTrue(d["reason"].startswith("typo: "), name)

    def test_the_four_are_true_and_every_other_false(self):
        got = self.consts()
        self.assertGreaterEqual(len(got), 16)
        for name, (value, comment, script) in got.items():
            if name in self.ENABLED:
                self.assertEqual(value, "true", name)
                self.assertTrue(comment.startswith(" // owner decision 9 Nov 2026: typo: "),
                                comment)
                self.assertIn("dink.cpp: ", comment)
            else:
                self.assertEqual(value, "false", name)
                self.assertTrue(comment.startswith(" // review: "), comment)
        self.assertTrue(self.ENABLED <= set(got))
        # the OD1 switches stay off: sp_prop is defined in the director but not used
        self.assertEqual(got["fix_s5_fguy_l6"][0], "false")
        self.assertEqual(got["fix_s5_end_l33"][0], "false")

    def test_fix_const_line(self):
        self.assertTrue(C.fix_const_line("fix_s4_sign3_l17", "x").startswith(
            "CONST fix_s4_sign3_l17 = true // owner decision 9 Nov 2026: "))
        self.assertEqual(C.fix_const_line("fix_s2_cave_l117", "x"),
                         "CONST fix_s2_cave_l117 = false // review: x")
        self.assertEqual(C.owner_date("2026-11-09"), "9 Nov 2026")

    def block(self, script, stitch):
        ls = [l.strip(" \t") for l in ink_src(script).splitlines()]
        i = ls.index("= " + stitch)
        j = next((k for k in range(i + 1, len(ls)) if ls[k].startswith("= ")), len(ls))
        return ls[i:j]

    def gated(self, script, stitch, const, starts):
        b = self.block(script, stitch)
        i = b.index("{ %s:" % const)
        for k, text in enumerate(starts):
            self.assertTrue(any(l.startswith(text) for l in b[i + 1:]), (script, text))
        return b, i

    def test_lines_sit_in_their_knots(self):
        b, i = self.gated("s2-jack", "p_die", "fix_s2_jack_l171", [])
        self.assertTrue(b[i + 1].startswith("I guess I just killed your husband. "
                                            "#id:s2-jack.die.002 #say:say_stop #spk:1 "))
        self.assertEqual(b[i + 2], "}")
        b, i = self.gated("s4-sign3", "p_talk", "fix_s4_sign3_l17", [])
        self.assertTrue(b[i + 1].startswith("Long live the ducks. #id:s4-sign3.talk.005 "
                                            "#say:say_stop #spk:current_sprite "))
        b, i = self.gated("s3-chick", "p_talk", "fix_s3_chick_l42", [])
        self.assertEqual(b[i + 1], "Hello Dink, I'm Christina. #id:s3-chick.talk.005 "
                                   "#say:say_stop #spk:current_sprite #col:9 #src:42")
        b, i = self.gated("s1-h3-8", "p_talk", "fix_s1_h3_8_l13", [
            "Libby's bed, to dream the impossible dream... #id:s1-h3-8.talk.002",
            "Libby's bed, looks lonely. #id:s1-h3-8.talk.003"])
        self.assertEqual(b[i + 1], "{ s1_h3_8__maybe == 2:")

    def test_compiled_story_has_the_switches_on(self):
        # CONSTs are inlined by inklecate: with the four on, the compiled story holds four
        # `true` literals the all-false build does not (the only booleans in the story are
        # the fix switches and EXTERNAL fallbacks).
        story = json.dumps(json.loads((OUT / "json" / "dink.json").read_text(encoding="utf-8-sig")))
        self.assertIn("I guess I just killed your husband.", story)
        self.assertIn("Long live the ducks.", story)
        self.assertIn("Hello Dink, I'm Christina.", story)
        tmp = OUT / "switches_default"
        if tmp.exists():
            shutil.rmtree(tmp)
        shutil.copytree(OUT / "ink", tmp)
        for f in tmp.glob("*.ink"):
            t = f.read_text(encoding="utf-8")
            f.write_text(re.sub(r"^(CONST fix_\w+) = true", r"\1 = false", t, flags=re.M),
                         encoding="utf-8")
        r = subprocess.run([INKLECATE, "-o", str(OUT / "t_false.json"), str(tmp / "dink.ink")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        off = json.dumps(json.loads((OUT / "t_false.json").read_text(encoding="utf-8-sig")))
        self.assertEqual(story.count("true") - off.count("true"), 4)


if __name__ == "__main__":
    unittest.main()
