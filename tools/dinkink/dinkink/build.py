"""`python3 -m dinkink build`: convert every script and write all tables."""

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import names as N
from .convert import Project, ScriptEmitter, walk_stmts, stmt_exprs, walk_expr, PSEUDO
from .overrides import BRACE_TYPOS, OWNER_DECISIONS
from .shotlist import shot_list, is_scene
from .vocab import describe, SAY_CALLS, SAY_BLOCKS

# Kinds whose scripts also hold stat/behaviour data (read by stage 5's enemy and item
# tables straight from the ASTs). They are converted like every other script: the engine
# runs their procedures (die, touch, use, arm, the drop tables...), so the story must
# contain them. Kept only to word the coverage reason.
DATA_KINDS = {"enemy", "weapon", "magic", "item", "projectile", "pickup", "container",
              "library"}
# Diagnostic codes the emitter turns into review rows itself.
EMITTER_CODES = {"say_sprite_zero", "bare_identifier_arg", "midtext_backtick",
                 "malformed_as_label", "unknown_call", "unknown_statement", "missing_paren",
                 "string_quote", "goto_missing_label", "engine_condition_differs",
                 "undeclared_variable", "engine_else_after_comment", "missing_comma"}
# Unknown commands (no engine command of that name) the remaster's director gives a meaning
# by owner decision; the switches that call them stay false.
DIRECTOR_DEFINED = {
    "sp_prop": "the remaster's director defines `sp_prop <sprite> <0|1>` (owner decision OD1, "
               "9 Nov 2026): set the placed sprite's map `prop` flag, the warp / walk-through "
               "flag that get_hard and special_block read (dink.cpp:569-575, 15337-15341; no "
               "1997 command can change it), until the screen loads again",
}
# Info-level codes that need no human decision.
SKIP_CODES = {"goto_cross_procedure", "unused_label"}

# unclosed_block rows that are one defect already reported by a curated override
SUPPRESSED = {(script, ln) for (script, _), o in BRACE_TYPOS.items() for ln in o["suppress"]}

PRIORITY = {"error": "medium", "warning": "low", "info": "low"}
CATEGORY = {"unclosed_block": "structure", "stray_close_brace": "structure",
            "code_after_procedure_block": "structure", "trailing_text": "structure",
            "missing_comma": "structure", "local_shadows_global": "variables",
            "used_before_declared": "variables", "map_script_missing": "missing-script",
            "d_without_c": "missing-script", "missing_script_reference": "missing-script"}


def comment_line(const):
    """fix_s4_st3p_l74b -> 'line 74b'"""
    return "line " + const.rsplit("_l", 1)[1]


def own_brace_only(ast, proc_name, diags, script, line):
    """True when `line` is the only unclosed block of its procedure and it is the
    procedure's own opening brace (before the first statement): the missing `}` is then
    cut off by the next `void` line, which ends the procedure in the engine too."""
    procs = [p for p in ast["procedures"] if p["name"] == proc_name]
    if not procs or line is None:
        return False
    p = procs[0]
    unclosed = [d for d in diags if d["script"] == script and d["code"] == "unclosed_block"
                and p["line"] <= (d.get("line") or 0) <= p["end_line"]]
    first = min((s["line"] for s in walk_stmts(p["body"]) if s["type"] != "comment"),
                default=None)
    return len(unclosed) == 1 and first is not None and line < first


def load_builtins(ast_dir):
    dinkc_root = Path(ast_dir).resolve().parent
    if not (dinkc_root / "dinkc" / "builtins.py").exists():
        dinkc_root = Path(__file__).resolve().parents[2] / "dinkc"
    sys.path.insert(0, str(dinkc_root))
    try:
        from dinkc import builtins as B
    finally:
        sys.path.pop(0)
    return B


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def proc_has_speech(p):
    for s in walk_stmts(p["body"]):
        if s["type"] == "choice" or (s["type"] == "call" and s["name"] in SAY_CALLS):
            return True
    return False


def proc_has_code(p):
    return any(s["type"] not in ("comment", "label", "block") for s in walk_stmts(p["body"]))


def select_procs(ast, status):
    """Every procedure once (a duplicate `void` name: the engine finds the first)."""
    procs = []
    seen = set()
    for p in ast["procedures"]:
        if p["name"] in seen:
            continue
        seen.add(p["name"])
        procs.append(p)
    return procs


def classify(ast, kind, has_lines, has_menus):
    """Status of one script. Rule (since Nov 2026): every script with an executable
    statement is converted in full, whatever its kind, because the engine can run any of
    its procedures (by placement, sp_script, external, spawn, add_item/add_magic, or by
    name like main/newgame/dinfo/lraise/escape). Only the place it is reached from
    decides whether it is `converted` or `converted-dead`."""
    procs = ast["procedures"]
    has_code = any(proc_has_code(p) for p in procs)
    if kind == "dead":
        if has_code:
            return "converted-dead", "not placed in map.dat and not called; kept as a draft"
        return "dead", "not placed, not called, nothing to convert"
    if kind == "empty" or not has_code:
        return "empty", "no executable statements"
    if kind in DATA_KINDS:
        return "converted", ("%s script: every procedure converted (the engine runs them); "
                             "its stat block is also data for stage 5 tables" % kind)
    if kind == "system":
        return "converted", "engine system script (run by name or by the start menu)"
    return "converted", "narrative script (%s)" % kind


def count_calls(procs):
    ids = set()
    for p in procs:
        for s in walk_stmts(p["body"]):
            for e in stmt_exprs(s):
                for x in walk_expr(e):
                    if x["type"] == "call" and x["name"] not in SAY_CALLS:
                        ids.add(id(x))
    return ids


def run_inklecate(src, dst):
    exe = shutil.which("inklecate") or os.path.expanduser("~/.local/bin/inklecate")
    r = subprocess.run([exe, "-o", str(dst), str(src)], capture_output=True, text=True)
    msgs = [l.strip() for l in (r.stdout + r.stderr).splitlines() if l.strip()]
    errors = [m for m in msgs if m.startswith("ERROR")]
    warnings = [m for m in msgs if m.startswith("WARNING")]
    ok = r.returncode == 0 and not errors and Path(dst).exists()
    return ok, errors, warnings


def build(ast_dir, out_dir, compile_files=True, jobs=8, quiet=False):
    t0 = time.time()
    ast_dir, out_dir = Path(ast_dir), Path(out_dir)
    B = load_builtins(ast_dir)
    for sub in ("ink", "json", "shot_lists", "check"):
        if (out_dir / sub).exists():
            shutil.rmtree(out_dir / sub)
        (out_dir / sub).mkdir(parents=True)

    asts = {}
    for f in sorted((ast_dir / "ast").glob("*.json")):
        a = json.load(open(f, encoding="utf-8"))
        asts[a["script"]] = a
    kinds = {r["script"]: r for r in read_csv(ast_dir / "script_kinds.csv")}
    dialog_rows = read_csv(ast_dir / "dialog_lines.csv")
    globals_json = json.load(open(ast_dir / "globals.json", encoding="utf-8"))
    diags = json.load(open(ast_dir / "diagnostics.json", encoding="utf-8"))["diagnostics"]
    choices = json.load(open(ast_dir / "choices.json", encoding="utf-8"))

    globals_ = {g.lower(): v[0]["initial"] for g, v in globals_json.items()}
    project = Project(globals_, B.BUILTINS, B.ENGINE_GLOBALS)
    for d in diags:
        if d["code"] == "missing_comma":
            project.missing_comma.setdefault(d["script"], set()).add(int(d["line"]))

    # spoken line IDs: <script>.<procedure>.<nnn>
    dialog = defaultdict(dict)
    by_proc = defaultdict(list)
    for r in dialog_rows:
        by_proc[(r["script"], r["procedure"])].append(r)
    for (script, proc), rows in by_proc.items():
        for k, r in enumerate(sorted(rows, key=lambda r: int(r["line"])), 1):
            r["_id"] = "%s.%s.%03d" % (script, proc, k)
            dialog[script][int(r["line"])] = r

    undeclared = defaultdict(set)
    for d in diags:
        if d["code"] == "undeclared_variable":
            m = re.search(r"(&[A-Za-z0-9_\-]+)", d["what"])
            undeclared[d["script"]].add(m.group(1).lower())

    def screen_context(script, seen=()):
        """Screens a script runs on: its own map.dat placements, else those of the
        scripts that attach it (sp_script) or spawn it, recursively."""
        row = kinds.get(script, {})
        if row.get("screens"):
            return set(row["screens"].split(";")), []
        found, via = set(), []
        for ref in (row.get("called_by") or "").split(";"):
            how, _, caller = ref.partition(":")
            if how in ("sp_script", "spawn") and caller and caller not in seen:
                sc, _ = screen_context(caller, seen + (script,))
                if sc:
                    found |= sc
                    via.append(caller)
        return found, via

    def screens_text(script):
        sc, via = screen_context(script)
        txt = ";".join(sorted(sc, key=lambda x: int(x) if x.isdigit() else 0))
        if via:
            txt += " (via %s)" % ",".join(via)
        return txt

    coverage = []
    included = []
    shot_scripts = []
    stats = Counter()
    for script, ast in asts.items():
        krow = kinds.get(script, {})
        kind = krow.get("kind", "other")
        screens = screens_text(script)
        lines_in = len(dialog.get(script, {}))
        menus_ast = [s for p in ast["procedures"] for s in walk_stmts(p["body"])
                     if s["type"] == "choice"]
        options_in = sum(len(m["options"]) for m in menus_ast)
        status, reason = classify(ast, kind, lines_in > 0, bool(menus_ast))
        row = {"script": script, "kind": kind, "status": status, "reason": reason,
               "placed": krow.get("placed", ""), "called_by": krow.get("called_by", ""),
               "screens": screens, "procedures": len(ast["procedures"]),
               "lines_in": lines_in, "menus_in": len(menus_ast), "options_in": options_in,
               "commands_in": len(count_calls(ast["procedures"]))}
        if status in ("converted", "converted-dead"):
            procs = select_procs(ast, status)
            menus_meta = {}
            for p in procs:
                k = 0
                for s in walk_stmts(p["body"]):
                    if s["type"] == "choice":
                        k += 1
                        menus_meta[(p["name"], s["line"])] = k
            em = ScriptEmitter(project, ast, kind, status, screens, dialog.get(script, {}),
                               menus_meta, undeclared.get(script, set()), procs)
            src = em.emit()
            (out_dir / "ink" / (script + ".ink")).write_text(src, encoding="utf-8")
            included.append(script)
            calls_in = count_calls(procs)
            data_calls = len(count_calls(ast["procedures"])) - len(calls_in)
            row.update({
                "ink_file": "ink/%s.ink" % script, "knot": em.knot,
                "procedures_converted": len(procs),
                "lines_out_live": sum(1 for _, g in em.spoken if not g),
                "lines_out_disabled": sum(1 for _, g in em.spoken if g),
                "menus_out": len(em.menus_out), "options_out": em.options_out,
                "commands_in": len(calls_in),
                "commands_out": len(calls_in & em.rendered_calls),
                "commands_left_as_data": data_calls,
                "fix_switches": len(em.fixes)})
            project.names.append({"kind": "knot", "original": script, "ink": em.knot,
                                  "scope": "script", "script": script})
            for p in procs:
                project.names.append({"kind": "entry", "original": "%s:%s" % (script, p["name"]),
                                      "ink": "%s.%s" % (em.knot, N.entry_ident(p["name"])), "scope": "procedure",
                                      "script": script})
            for l in sorted(em.locals):
                project.names.append({"kind": "local", "original": "%s:%s" % (script, l),
                                      "ink": N.local_ident(script, l), "scope": "local",
                                      "script": script})
            for const, comment in em.fixes:
                project.names.append({"kind": "fix", "original": "%s:%s" % (script, comment_line(const)),
                                      "ink": const, "scope": "const", "script": script})
            scene_procs = [p for p in procs if is_scene(p)]
            if kind == "cutscene" or scene_procs:
                sl = shot_list(ast, scene_procs or procs, dialog.get(script, {}), kind,
                               screens, globals_)
                (out_dir / "shot_lists" / (script + ".md")).write_text(sl, encoding="utf-8")
                shot_scripts.append(script)
        else:
            row.update({"procedures_converted": 0, "lines_out_live": 0,
                        "lines_out_disabled": 0, "menus_out": 0, "options_out": 0,
                        "commands_out": 0, "commands_left_as_data": row["commands_in"],
                        "commands_in": 0, "fix_switches": 0})
        stats[status] += 1
        coverage.append(row)

    # every owner decision must name a switch the converter made (a renamed or vanished
    # constant must not silently leave the decision unapplied)
    made = {n["ink"] for n in project.names if n["kind"] == "fix"}
    stale = sorted(set(OWNER_DECISIONS) - made)
    if stale:
        raise SystemExit("overrides.OWNER_DECISIONS names switches the converter did not "
                         "make: %s" % ", ".join(stale))

    # scripts referenced but without a .c file; a `.d` with no `.c` that nothing references
    # is dead data (the engine would load it, but nothing asks for it)
    referenced = {d["script"] for d in diags
                  if d["code"] in ("map_script_missing", "missing_script_reference")}
    referenced |= {m.group(1) for d in diags if d["code"] == "missing_script_reference"
                   for m in [re.search(r"script '([^']+)'", d["what"])] if m}
    dead_d = set()
    for d in diags:
        if d["code"] in ("map_script_missing", "d_without_c"):
            row = {"script": d["script"], "kind": "", "status": "missing",
                   "reason": d["what"][:200], "procedures": 0, "lines_in": 0,
                   "menus_in": 0, "options_in": 0, "commands_in": 0}
            if d["code"] == "d_without_c" and d["script"] not in referenced:
                dead_d.add(d["script"])
                row.update({"kind": "dead", "status": "dead",
                            "reason": "dead data: %s.d exists with no .c and nothing "
                                      "references the script (map.dat, dink.dat, dink.ini "
                                      "or any script); not converted" % d["script"]})
            coverage.append(row)

    # globals
    for g, ink in sorted(project.global_names.items()):
        project.names.append({"kind": "global", "original": g, "ink": ink,
                              "scope": "global", "script": "main"})
    for orig, ink in sorted(PSEUDO.items()):
        project.names.append({"kind": "pseudo", "original": orig, "ink": ink,
                              "scope": "global", "script": ""})

    # root files
    decls = ["// _decls.ink - generated by tools/dinkink. Globals, engine variables and",
             "// external functions shared by every script file.", ""]
    decls.append("// Quest facts and engine-bound stats (make_global_int in main.c).")
    for g, ink in sorted(project.global_names.items(), key=lambda x: x[1]):
        decls.append("VAR %s = %s // %s" % (ink, globals_[g], g))
    decls.append("")
    decls.append("// Engine pseudo-variables, set by the runtime before entering a knot.")
    seen = set(project.global_names.values())
    for orig, ink in sorted(PSEUDO.items(), key=lambda x: x[1]):
        if ink in seen:
            continue
        seen.add(ink)
        init = '""' if ink.endswith("_text") else "0"
        decls.append("VAR %s = %s // %s" % (ink, init, orig))
    decls.append("")
    decls.append("// Engine queries: bind each in DinkNarrative with lookaheadSafe = false.")
    decls.append("// The functions below are fallbacks for inklecate -p and tests only.")
    clash = set(project.externals) & seen
    if clash:
        raise ValueError("external functions clash with variables: %s" % clash)
    for name, arity in sorted(project.externals.items()):
        params = ", ".join("p%d" % i for i in range(1, arity + 1))
        decls.append("EXTERNAL %s(%s)" % (name, params))
    decls.append("")
    for name, arity in sorted(project.externals.items()):
        params = ", ".join("p%d" % i for i in range(1, arity + 1))
        decls.append("=== function %s(%s) ===" % (name, params))
        if name == "random":
            # engine: range 0 returns base, else (rand() % range) + base; C's % of a positive
            # rand() by a negative range is the same as by its magnitude
            decls += ["{ p1 == 0:", "    ~ return p2", "}",
                      "~ temp r = p1", "{ r < 0:", "    ~ r = -r", "}",
                      "~ return RANDOM(p2, p2 + r - 1)"]
            continue
        ret = '""' if name in ("savegameinfo", "buttoninfo") else "0"
        decls.append("~ return %s" % ret)
    (out_dir / "ink" / "_decls.ink").write_text("\n".join(decls) + "\n", encoding="utf-8")

    root = ["// dink.ink - root of the converted Dink Smallwood scripts (tools/dinkink).",
            "// Enter a script with ChoosePathString(\"<knot>.<procedure>\"), see DESIGN.md.",
            "INCLUDE _decls.ink"]
    root += ["INCLUDE %s.ink" % s for s in included]
    root += ["", "-> DONE"]
    (out_dir / "ink" / "dink.ink").write_text("\n".join(root) + "\n", encoding="utf-8")

    # compile
    report = []
    ok_root, err_root, warn_root = run_inklecate(out_dir / "ink" / "dink.ink",
                                                 out_dir / "json" / "dink.json")
    report.append("root dink.ink: %s, %d errors, %d warnings" % (
        "ok" if ok_root else "FAILED", len(err_root), len(warn_root)))
    report += ["  " + m for m in err_root + warn_root]
    file_results = {}
    if compile_files:
        def one(script):
            wrapper = out_dir / "ink" / ("_check_%s.ink" % script)
            wrapper.write_text("INCLUDE _decls.ink\nINCLUDE %s.ink\n-> DONE\n" % script,
                               encoding="utf-8")
            try:
                return script, run_inklecate(wrapper, out_dir / "check" / (script + ".json"))
            finally:
                wrapper.unlink()
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            for script, res in ex.map(one, included):
                file_results[script] = res
        bad = [s for s, r in file_results.items() if not r[0]]
        nwarn = sum(len(r[2]) for r in file_results.values())
        report.append("per-file: %d compiled, %d failed, %d warnings" % (
            len(file_results), len(bad), nwarn))
        for s, (ok, errs, warns) in sorted(file_results.items()):
            for m in errs + warns:
                report.append("  %s: %s" % (s, m))
    shutil.rmtree(out_dir / "check", ignore_errors=True)
    (out_dir / "compile_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    for row in coverage:
        if row["script"] in file_results:
            r = file_results[row["script"]]
            row["compiles"] = "yes" if r[0] else "NO"
            row["compile_warnings"] = len(r[2])

    # review queue: emitter rows + diagnostics not already covered
    have = {(r["script"], int(r["line"] or 0), r["code"]) for r in project.reviews}
    status_of = {r["script"]: r["status"] for r in coverage}
    for d in diags:
        if d["code"] in EMITTER_CODES or d["code"] in SKIP_CODES:
            continue
        key = (d["script"], int(d.get("line") or 0), d["code"])
        if key in have:
            continue
        if d["code"] == "unclosed_block" and (d["script"], d.get("line")) in SUPPRESSED:
            continue                    # reported once, at the typo, by a curated override
        prio = PRIORITY.get(d["severity"], "low")
        proc = ""
        m = re.search(r"in procedure (\w+)", d["what"])
        if m:
            proc = m.group(1)
        category = CATEGORY.get(d["code"], "other")
        conversion = d.get("recovery", "")
        if d["code"] == "unclosed_block" and own_brace_only(asts[d["script"]], proc, diags,
                                                            d["script"], d.get("line")):
            # the procedure's own `{` with no `}` before the next `void` line: the engine
            # ends a procedure there anyway (dink.cpp 7131, 7323), so nothing changes
            prio = "low"
            conversion = ("no behavioural difference: the engine ends the procedure at the "
                          "next `void` line (dink.cpp 7131, 7323), as the converter does")
        elif d["code"] == "unclosed_block" and any(
                ln > int(d.get("line") or 0) and r["procedure"] == proc
                for ln, r in dialog.get(d["script"], {}).items()):
            # spoken lines after a block the author never closed: whether they
            # belong inside it changes what the player sees (bible correction 10)
            prio = "high"
        if d["code"] == "d_without_c" and d["script"] in dead_d:
            prio, category = "low", "dead-data"
            conversion = ("not converted: a .d with no .c that nothing references is dead "
                          "data (coverage status `dead`)")
        project.reviews.append({
            "script": d["script"], "line": d.get("line") or "", "procedure": proc,
            "code": d["code"], "priority": prio,
            "category": category,
            "engine_behaviour": d["what"], "author_intent": "",
            "conversion": conversion, "fix_const": ""})
    # emitter-covered diagnostics whose script was not converted still need a row
    for d in diags:
        if d["code"] in EMITTER_CODES and status_of.get(d["script"]) not in (
                "converted", "converted-dead"):
            project.reviews.append({
                "script": d["script"], "line": d.get("line") or "", "procedure": "",
                "code": d["code"], "priority": "low", "category": "not-converted",
                "engine_behaviour": d["what"], "author_intent": "",
                "conversion": "script not converted (%s)" % status_of.get(d["script"]),
                "fix_const": ""})
    prank = {"high": 0, "medium": 1, "low": 2}
    project.reviews.sort(key=lambda r: (prank[r["priority"]], r["script"],
                                        int(r["line"] or 0), r["code"]))
    for k, r in enumerate(project.reviews, 1):
        r["id"] = "R%04d" % k
        r["status"] = status_of.get(r["script"], "missing")

    # vocabulary
    freq = Counter((c["command"], c["form"]) for c in project.commands)
    by_cmd = defaultdict(Counter)
    scripts_per = defaultdict(set)
    for c in project.commands:
        by_cmd[c["command"]][c["form"]] += 1
        scripts_per[c["command"]].add(c["script"])
    externals_count = Counter()
    for s in included:
        txt = (out_dir / "ink" / (s + ".ink")).read_text(encoding="utf-8")
        for name in project.externals:
            externals_count[name] += len(re.findall(r"(?<![\w.])%s\(" % re.escape(name), txt))
    vocab_rows = []
    for name in sorted(set(by_cmd) | set(project.externals)):
        if name.startswith("="):
            cat, args, note, blocking = "fact-write", "op value", "engine-bound stat write", False
        elif name in by_cmd and name not in B.BUILTINS and name not in project.externals:
            # written in a script but not an engine command (dink.cpp has no such name):
            # only the switched-off intent branch uses it; never a described command
            cat, args, blocking = "unknown-command", "", False
            note = ("not an engine command: dink.cpp has no such name, so the engine logs it "
                    "and skips the line; written only in a switched-off intent branch (see the "
                    "unknown_call rows of review_queue.csv)")
            if name in DIRECTOR_DEFINED:
                note += "; " + DIRECTOR_DEFINED[name]
            else:
                note += "; the director need not run it"
        else:
            cat, args, note, blocking = describe(name, B.BUILTINS.get(name))
        forms = by_cmd.get(name, Counter())
        vocab_rows.append({"command": name, "category": cat, "args": args,
                           "blocking": int(blocking), "lines": forms.get("line", 0),
                           "external_calls": externals_count.get(name, 0),
                           "comments": forms.get("comment", 0),
                           "fix_intent": forms.get("fix-intent", 0),
                           "var_writes": forms.get("var-write", 0),
                           "scripts": len(scripts_per.get(name, ())), "note": note})
    for name, blocks in SAY_BLOCKS.items():
        n = sum(1 for r in project.line_ids if r.get("call") == name)
        vocab_rows.append({"command": "(line) " + name, "category": "dialogue",
                           "args": "text #spk/#x #y #col", "blocking": int(blocks),
                           "lines": n, "external_calls": 0, "comments": 0, "fix_intent": 0,
                           "var_writes": 0, "scripts": len({r["script"] for r in project.line_ids
                                                            if r.get("call") == name}),
                           "note": "spoken line"})
    vocab_rows.sort(key=lambda r: -(r["lines"] + r["external_calls"] + r["var_writes"]))

    # write tables
    write_csv(out_dir / "names.csv", project.names,
              ["kind", "original", "ink", "scope", "script"])
    write_csv(out_dir / "line_ids.csv", project.line_ids,
              ["id", "kind", "script", "procedure", "line", "call", "speaker", "colour",
               "live", "text"])
    write_csv(out_dir / "director_commands.csv", project.commands,
              ["script", "procedure", "line", "command", "form", "blocking", "args", "kind",
               "status", "screens"])
    write_csv(out_dir / "director_vocabulary.csv", vocab_rows,
              ["command", "category", "args", "blocking", "lines", "external_calls",
               "comments", "fix_intent", "var_writes", "scripts", "note"])
    write_csv(out_dir / "review_queue.csv", project.reviews,
              ["id", "priority", "category", "code", "script", "status", "line", "procedure",
               "engine_behaviour", "author_intent", "conversion", "fix_const"])
    write_csv(out_dir / "coverage.csv", coverage,
              ["script", "kind", "status", "reason", "placed", "called_by", "screens",
               "ink_file", "knot", "procedures", "procedures_converted", "lines_in",
               "lines_out_live", "lines_out_disabled", "menus_in", "menus_out", "options_in",
               "options_out", "commands_in", "commands_out", "commands_left_as_data",
               "fix_switches", "compiles", "compile_warnings"])

    summary = {
        "scripts": len(asts), "coverage_rows": len(coverage), "status": dict(stats),
        "ink_files": len(included), "spoken_lines": sum(1 for r in project.line_ids
                                                        if r["kind"] == "spoken"),
        "spoken_lines_live": sum(1 for r in project.line_ids
                                 if r["kind"] == "spoken" and r["live"]),
        "titles": sum(1 for r in project.line_ids if r["kind"] == "title"),
        "menus": sum(int(r.get("menus_out") or 0) for r in coverage),
        "options": sum(int(r.get("options_out") or 0) for r in coverage),
        "command_rows": len(project.commands),
        "command_lines": sum(1 for c in project.commands if c["form"] == "line"),
        "externals": len(project.externals),
        "review_items": len(project.reviews),
        "review_by_priority": dict(Counter(r["priority"] for r in project.reviews)),
        "review_by_code": dict(Counter(r["code"] for r in project.reviews).most_common()),
        "shot_lists": len(shot_scripts),
        "root_compiles": ok_root, "root_warnings": len(warn_root),
        "files_compiled": len(file_results),
        "files_failed": sum(1 for r in file_results.values() if not r[0]),
        "file_warnings": sum(len(r[2]) for r in file_results.values()),
        "seconds": round(time.time() - t0, 1)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1) + "\n",
                                          encoding="utf-8")
    if not quiet:
        print(json.dumps(summary, indent=1))
    return summary
