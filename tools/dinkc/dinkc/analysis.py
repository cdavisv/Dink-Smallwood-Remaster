"""Derived tables built from the parsed ASTs.

Every function here takes the dict {script_name: ast} produced by parser.parse_script
(plus map references where needed) and returns plain rows/dicts ready to write.
"""

import re

from . import expr as X
from .builtins import (BUILTINS, PSEUDO_VARS, ENGINE_GLOBALS, ENGINE_PROCS,
                       ENGINE_SCRIPTS, SAY_CALLS, COLOUR_CODES, DEFAULT_COLOUR)

VAR_RE = re.compile(r"&[A-Za-z0-9_][A-Za-z0-9_\-]*")


# --------------------------------------------------------------------------------------
# Generic traversal
# --------------------------------------------------------------------------------------

def iter_stmts(nodes, ctx=None):
    """Yield (node, ctx) for every statement node, in source order.

    ctx is a dict with 'path': list of enclosing if/else descriptions."""
    if ctx is None:
        ctx = {"path": []}
    for n in nodes or []:
        if n is None:
            continue
        for lead in n.get("leading", []) or []:
            yield lead, ctx
        yield n, ctx
        t = n.get("type")
        if t == "block":
            yield from iter_stmts(n["body"], ctx)
        elif t == "if":
            c1 = {"path": ctx["path"] + [("then", n)]}
            yield from iter_stmts([n["then"]], c1)
            c2 = {"path": ctx["path"] + [("else", n)]}
            yield from iter_stmts([n["else"]], c2)
        elif t == "else_stray":
            yield from iter_stmts([n["body"]], ctx)


def iter_procs(ast):
    for p in ast["procedures"]:
        for n, ctx in iter_stmts(p["body"]):
            yield p["name"], n, ctx


def stmt_exprs(n):
    """Top-level expressions of a statement node."""
    t = n.get("type")
    if t == "call":
        return [n]
    if t in ("assign", "int", "return"):
        return [n["value"]] if n.get("value") else []
    if t == "if":
        return [n["cond"]]
    if t == "choice":
        out = []
        for o in n["options"]:
            out.extend(c["expr"] for c in o["conditions"])
        return out
    return []


def stmt_calls(n):
    out = []
    for e in stmt_exprs(n):
        X.expr_calls(e, out)
    return out


def string_arg(call, k=0):
    if k < len(call["args"]) and call["args"][k].get("type") == "string":
        return call["args"][k]["value"]
    return None


def int_arg(call, k):
    if k < len(call["args"]) and call["args"][k].get("type") == "int":
        return call["args"][k]["value"]
    return None


def arg_text(call, k):
    return X.to_text(call["args"][k]) if k < len(call["args"]) else ""


def engine_runs(n, ctx):
    if n.get("engine_executes") is False:
        return False
    for kind, ifn in ctx["path"]:
        if ifn.get("engine_executes") is False:
            return False
        if kind == "else" and ifn.get("else_engine_never_runs"):
            return False
        if kind == "then" and ifn.get("engine", {}).get("always_false"):
            return False
    return True


def one_liner(n):
    """Short text rendering of a statement (for choices.json branches)."""
    t = n.get("type")
    if t == "call":
        return X.to_text(n)
    if t == "assign":
        return "%s %s %s" % (n["target"], n["op"], X.to_text(n["value"]))
    if t == "int":
        return "int %s%s" % (n["name"], (" = " + X.to_text(n["value"])) if n.get("value") else "")
    if t == "return":
        return "return" + ((" " + X.to_text(n["value"])) if n.get("value") else "")
    if t == "goto":
        return "goto %s" % n["label"]
    if t == "label":
        return "%s:" % n["name"]
    if t == "if":
        return "if (%s)" % n["cond_text"]
    if t == "choice":
        return "choice_start() [%d options]" % len(n["options"])
    if t == "unknown":
        return "?? %s" % n["text"]
    if t == "block":
        return "{...}"
    return t


# --------------------------------------------------------------------------------------
# Globals and text interpolation
# --------------------------------------------------------------------------------------

def collect_globals(asts):
    """Every make_global_int call: {name: [{'script','line','procedure','initial'}]}"""
    out = {}
    for name, ast in asts.items():
        for proc, n, ctx in iter_procs(ast):
            for c in stmt_calls(n):
                if c["name"] == "make_global_int":
                    var = string_arg(c, 0)
                    if var is None:
                        continue
                    out.setdefault(var.lower(), []).append({
                        "script": name, "line": n["line"], "procedure": proc,
                        "initial": int_arg(c, 1) if int_arg(c, 1) is not None else arg_text(c, 1),
                    })
    return out


def script_locals(ast):
    return {l["name"] for l in ast["locals"]}


def interpolated_vars(text, known):
    """Variables the engine would substitute in `text` (var_replace, D:3995):
    longest names first, so &gold does not eat &goldx. Returns (found, unknown)."""
    found = []
    work = text
    for v in sorted(known, key=len, reverse=True):
        lv = v.lower()
        idx = work.lower().find(lv)
        while idx >= 0:
            found.append((idx, v))
            work = work[:idx] + "\x00" * len(v) + work[idx + len(v):]
            idx = work.lower().find(lv)
    found.sort()
    unknown = [m.group(0) for m in VAR_RE.finditer(work)]
    return [v for _, v in found], unknown


def split_colour(text):
    """Leading backtick codes (D:11810): returns (codes_string, colour_index, rest)."""
    codes = ""
    colour = DEFAULT_COLOUR
    rest = text
    while rest.startswith("`"):
        ch = rest[1:2]
        codes += ch
        if ch in COLOUR_CODES:
            colour = COLOUR_CODES[ch]
        rest = rest[2:]
    return codes, colour, rest


# --------------------------------------------------------------------------------------
# Dialog
# --------------------------------------------------------------------------------------

DIALOG_COLUMNS = ["script", "procedure", "line", "call", "speaker", "x", "y", "colour_code",
                  "colour", "text", "vars", "unknown_vars", "engine_executes", "raw_text"]


def dialog_rows(asts, globals_):
    gnames = set(globals_)
    rows = []
    extra_diags = []
    for name, ast in asts.items():
        known = gnames | script_locals(ast) | PSEUDO_VARS
        for proc, n, ctx in iter_procs(ast):
            for c in stmt_calls(n):
                if c["name"] not in SAY_CALLS:
                    continue
                raw = string_arg(c, 0)
                if raw is None:
                    raw = arg_text(c, 0)
                codes, colour, text = split_colour(raw)
                found, unknown = interpolated_vars(text, known)
                if c["name"] in ("say_xy", "say_stop_xy"):
                    speaker, x, y = "", arg_text(c, 1), arg_text(c, 2)
                else:
                    speaker, x, y = arg_text(c, 1), "", ""
                if "`" in text:
                    extra_diags.append({
                        "script": name, "file": name + ".c", "line": n["line"],
                        "code": "midtext_backtick", "severity": "warning",
                        "what": "backtick inside spoken text: %r" % raw,
                        "recovery": "kept verbatim; only leading backtick codes set the "
                                    "colour in say_text (D:11810), but Proton's font "
                                    "renderer (not in this repo) may also treat it as a "
                                    "colour code"})
                if codes and any(ch not in COLOUR_CODES for ch in codes):
                    extra_diags.append({
                        "script": name, "file": name + ".c", "line": n["line"],
                        "code": "unknown_colour_code", "severity": "warning",
                        "what": "unknown colour code %r in %r" % (codes, raw),
                        "recovery": "stripped; colour stays at the previous/default value"})
                if len(raw) > 200:
                    extra_diags.append({
                        "script": name, "file": name + ".c", "line": n["line"],
                        "code": "say_too_long", "severity": "warning",
                        "what": "say text is %d characters (engine limit about 200)" % len(raw),
                        "recovery": "kept whole"})
                rows.append({
                    "script": name, "procedure": proc, "line": n["line"], "call": c["name"],
                    "speaker": speaker, "x": x, "y": y, "colour_code": codes,
                    "colour": colour, "text": text, "vars": ";".join(found),
                    "unknown_vars": ";".join(unknown),
                    "engine_executes": int(engine_runs(n, ctx)), "raw_text": raw,
                })
    return rows, extra_diags


# --------------------------------------------------------------------------------------
# Choices
# --------------------------------------------------------------------------------------

def _result_index(cond):
    """`&result == N` -> N, else None."""
    if cond.get("type") == "binop" and cond["op"] == "==":
        l, r = cond["left"], cond["right"]
        if l.get("type") == "var" and l["name"].lower() == "&result" and r.get("type") == "int":
            return r["value"]
        if r.get("type") == "var" and r["name"].lower() == "&result" and l.get("type") == "int":
            return l["value"]
    return None


def _branch_summary(node, ast):
    """Flatten a branch into one-liners, noting gotos and local calls."""
    stmts, gotos, local_calls = [], [], []
    for n, ctx in iter_stmts([node]):
        if n.get("type") in ("block", "comment"):
            continue
        stmts.append({"line": n["line"], "stmt": one_liner(n)})
        if n.get("type") == "goto":
            gotos.append({"line": n["line"], "label": n["label"], "target": n.get("target")})
        for c in stmt_calls(n):
            if c.get("kind") == "local":
                local_calls.append(c["name"])
    return stmts, gotos, local_calls


def choices_table(asts):
    out = []
    for name, ast in asts.items():
        for p in ast["procedures"]:
            _choices_in(name, p["name"], p["body"], ast, out)
    return out


def _choices_in(script, proc, body, ast, out):
    for i, n in enumerate(body):
        if n is None:
            continue
        t = n.get("type")
        if t == "choice":
            out.append(_choice_entry(script, proc, n, body[i + 1:], ast))
        if t == "block":
            _choices_in(script, proc, n["body"], ast, out)
        elif t == "if":
            for sub in (n["then"], n["else"]):
                if sub is not None:
                    _choices_in(script, proc, [sub], ast, out)
        elif t == "else_stray" and n["body"] is not None:
            _choices_in(script, proc, [n["body"]], ast, out)


def _choice_entry(script, proc, n, following, ast):
    entry = {
        "script": script, "procedure": proc, "line": n["line"], "end_line": n["end_line"],
        "set_y": n["set_y"], "title_color": n["title_color"], "title": n["title"],
        "aborted": bool(n.get("aborted")), "options": [], "notes": [],
    }
    branches = {}
    uses_goto = False
    # Walk the statements after the menu in the same list, following `else` chains.
    stop_line = None
    for f in following:
        if f is None or f.get("type") == "comment":
            continue
        if f.get("type") == "choice":
            break
        chain = f
        matched_any = False
        while chain is not None and chain.get("type") == "if":
            idx = _result_index(chain["cond"])
            if idx is None:
                break
            matched_any = True
            stmts, gotos, calls = _branch_summary(chain["then"], ast) if chain["then"] else ([], [], [])
            br = branches.setdefault(idx, {"if_line": chain["line"], "statements": [],
                                           "gotos": [], "local_calls": []})
            br["statements"].extend(stmts)
            br["gotos"].extend(gotos)
            br["local_calls"].extend(calls)
            if gotos:
                uses_goto = True
            nxt = chain.get("else")
            if nxt is not None and nxt.get("type") == "block":
                inner = [x for x in nxt["body"] if x.get("type") != "comment"]
                nxt = inner[0] if len(inner) == 1 else nxt
            if nxt is not None and nxt.get("type") != "if":
                stmts, gotos, calls = _branch_summary(nxt, ast)
                branches.setdefault("else", {"if_line": chain.get("else_line"),
                                             "statements": stmts, "gotos": gotos,
                                             "local_calls": calls})
                nxt = None
            chain = nxt
        if not matched_any and f.get("type") == "if":
            # A different condition (e.g. &result compared with >), keep scanning.
            if "&result" in f.get("cond_text", "").lower():
                entry["notes"].append("line %d tests &result with %r" % (f["line"], f["cond_text"]))
            continue
        if f.get("type") in ("return", "goto"):
            if f.get("type") == "goto":
                uses_goto = True
                entry["notes"].append("control leaves via goto %s at line %d"
                                      % (f["label"], f["line"]))
            break
    for o in n["options"]:
        b = branches.get(o["index"])
        entry["options"].append({
            "index": o["index"], "line": o["line"], "text": o["text"],
            "conditions": [{"text": c["text"], "expr": X.to_text(c["expr"]),
                            "engine": c["engine"]} for c in o["conditions"]],
            "hidden_unless": " and ".join(c["text"] for c in o["conditions"]) or None,
            "branch": b,
            "handled": b is not None,
        })
    if "else" in branches:
        entry["else_branch"] = branches["else"]
    entry["uses_goto"] = uses_goto or any(b["gotos"] for k, b in branches.items())
    unhandled = [o["index"] for o in entry["options"] if not o["handled"]]
    if unhandled:
        entry["notes"].append("options without an `if (&result == N)` branch right after the "
                              "menu: %s (often 'Leave', or handled after a goto/label)"
                              % unhandled)
    extra = sorted(k for k in branches if isinstance(k, int) and k > len(n["options"]))
    if extra:
        entry["notes"].append("branches for &result values beyond the option count: %s "
                              "(unreachable)" % extra)
    return entry


# --------------------------------------------------------------------------------------
# Facts (global variable read/write map)
# --------------------------------------------------------------------------------------

FACT_COLUMNS = ["variable", "declared_in", "initial", "engine_bound", "script", "procedures",
                "reads", "writes", "read_lines", "write_lines", "compared_values",
                "written_values"]


def _cmp_values(cond, var):
    """Literal comparisons of `var` inside a condition tree -> ['==3', '>=5']."""
    out = []

    def rec(e):
        if not isinstance(e, dict):
            return
        if e.get("type") == "binop":
            if e["op"] in X.COMPARISONS:
                l, r = e["left"], e["right"]
                if l.get("type") == "var" and l["name"].lower() == var and r.get("type") == "int":
                    out.append("%s%d" % (e["op"], r["value"]))
                elif r.get("type") == "var" and r["name"].lower() == var and l.get("type") == "int":
                    flip = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}.get(e["op"], e["op"])
                    out.append("%s%d" % (flip, l["value"]))
            rec(e["left"])
            rec(e["right"])
        elif e.get("type") == "var" and e["name"].lower() == var:
            pass
    rec(cond)
    return out


def facts_rows(asts, globals_):
    gnames = set(globals_)
    usage = {}  # (var, script) -> dict
    shadow_diags = []
    for name, ast in asts.items():
        locs = script_locals(ast)
        for v in sorted(locs & gnames):
            first = [l for l in ast["locals"] if l["name"] == v][0]
            shadow_diags.append({
                "script": name, "file": name + ".c", "line": first["line"],
                "code": "local_shadows_global", "severity": "warning",
                "what": "local `int %s` has the same name as a global" % v,
                "recovery": "uses of %s in this script are treated as the local, not the "
                            "global (the engine looks up locals first once declared)" % v})
        known = gnames | locs | PSEUDO_VARS

        def rec(var, kind, line, proc, value=None):
            var = var.lower()
            if var not in gnames or var in locs:
                return
            u = usage.setdefault((var, name), {"reads": [], "writes": [], "procs": set(),
                                               "cmp": [], "wvals": []})
            u["procs"].add(proc)
            if kind == "r":
                u["reads"].append(line)
            else:
                u["writes"].append(line)
                if value is not None:
                    u["wvals"].append(value)

        for proc, n, ctx in iter_procs(ast):
            t = n.get("type")
            ln = n["line"]
            if t == "assign":
                val = n["value"]
                vtxt = (str(val["value"]) if val.get("type") == "int" else X.to_text(val))
                rec(n["target"], "w", ln, proc, "%s%s" % (n["op"], vtxt))
                if n["op"] != "=":
                    rec(n["target"], "r", ln, proc)
            if t == "int" and n.get("value"):
                pass  # target is a local
            for e in stmt_exprs(n):
                for v in X.expr_vars(e):
                    rec(v, "r", ln, proc)
                if t == "if":
                    for v in set(X.expr_vars(e)):
                        if v in gnames and v not in locs:
                            usage[(v, name)]["cmp"].extend(_cmp_values(e, v))
            if t == "choice":
                for o in n["options"]:
                    for c in o["conditions"]:
                        for v in set(X.expr_vars(c["expr"])):
                            if v in gnames and v not in locs:
                                rec(v, "r", o["line"], proc)
                                usage[(v, name)]["cmp"].extend(_cmp_values(c["expr"], v))
                    f, _u = interpolated_vars(o["text"], known)
                    for v in f:
                        rec(v, "r", o["line"], proc)
                rec("&result", "w", ln, proc, "choice 1..%d" % len(n["options"]))
            for c in stmt_calls(n):
                if c["name"] == "make_global_int":
                    var = string_arg(c, 0)
                    if var:
                        rec(var, "w", ln, proc, "init=%s" % arg_text(c, 1))
                if c["name"] in SAY_CALLS:
                    s = string_arg(c, 0)
                    if s:
                        f, _u = interpolated_vars(s, known)
                        for v in f:
                            rec(v, "r", ln, proc)
    rows = []
    for (var, script), u in sorted(usage.items()):
        decl = globals_.get(var, [])
        rows.append({
            "variable": var,
            "declared_in": ";".join(sorted({"%s:%d" % (d["script"], d["line"]) for d in decl})),
            "initial": decl[0]["initial"] if decl else "",
            "engine_bound": int(var in ENGINE_GLOBALS),
            "script": script,
            "procedures": ";".join(sorted(u["procs"])),
            "reads": len(u["reads"]), "writes": len(u["writes"]),
            "read_lines": ";".join(str(x) for x in sorted(set(u["reads"]))),
            "write_lines": ";".join(str(x) for x in sorted(set(u["writes"]))),
            "compared_values": ";".join(sorted(set(u["cmp"]), key=_vkey)),
            "written_values": ";".join(sorted(set(u["wvals"]), key=_vkey)),
        })
    return rows, shadow_diags


def _vkey(s):
    m = re.search(r"-?\d+", s)
    return (re.sub(r"-?\d+", "", s), int(m.group(0)) if m else 0, s)


def undeclared_var_diags(asts, globals_):
    """Variables used that are neither globals, locals nor pseudo-variables."""
    gnames = set(globals_)
    out = []
    for name, ast in asts.items():
        locs = script_locals(ast)
        seen = set()
        decls = {}
        for l in ast["locals"]:
            decls.setdefault(l["name"], []).append((l["procedure"], l["line"]))

        def late_decl(v, proc, line):
            """Line of a same-procedure declaration after `line`, if the variable is
            not declared in main()/arm() (which run first) nor earlier in `proc`."""
            ds = decls.get(v, [])
            if any(p in ("main", "arm") for p, _l in ds):
                return None
            same = [l for p, l in ds if p == proc]
            if not same or min(same) < line:
                return None
            return min(same)
        for proc, n, ctx in iter_procs(ast):
            vs = []
            if n.get("type") == "assign":
                vs.append(n["target"].lower())
            for e in stmt_exprs(n):
                vs.extend(X.expr_vars(e))
            for v in vs:
                if v in gnames or v in PSEUDO_VARS or v in seen:
                    continue
                if v in locs:
                    dl = late_decl(v, proc, n["line"])
                    if dl is not None and v not in seen:
                        seen.add(v)
                        out.append({
                            "script": name, "file": name + ".c", "line": n["line"],
                            "code": "used_before_declared", "severity": "warning",
                            "what": "%s used at line %d before its `int` at line %d"
                                    % (v, n["line"], dl),
                            "recovery": "treated as the script's local; in the engine the "
                                        "use fails unless an earlier procedure run declared it"})
                    continue
                seen.add(v)
                out.append({
                    "script": name, "file": name + ".c", "line": n["line"],
                    "code": "undeclared_variable", "severity": "error",
                    "what": "%s is never declared (no make_global_int, no int)" % v,
                    "recovery": "kept; the engine logs an error and reads it as 0 / ignores "
                                "the assignment"})
        for l in ast["locals"]:
            if len(l["name"]) > 19:
                out.append({
                    "script": name, "file": name + ".c", "line": l["line"],
                    "code": "var_name_too_long", "severity": "warning",
                    "what": "%s is longer than the engine's 19-character name limit" % l["name"],
                    "recovery": "kept"})
    for g in globals_:
        if len(g) > 19:
            d = globals_[g][0]
            out.append({"script": d["script"], "file": d["script"] + ".c", "line": d["line"],
                        "code": "var_name_too_long", "severity": "warning",
                        "what": "%s is longer than the engine's 19-character name limit" % g,
                        "recovery": "kept"})
    return out


# --------------------------------------------------------------------------------------
# Calls cross reference and script graph
# --------------------------------------------------------------------------------------

CALL_COLUMNS = ["name", "kind", "script", "procedure", "line", "args", "engine_executes"]

# (call name, argument index holding a script name, edge kind)
SCRIPT_REF_CALLS = {
    "external": (0, "external"), "spawn": (0, "spawn"), "sp_script": (1, "sp_script"),
    "add_item": (0, "add_item"), "add_magic": (0, "add_magic"),
    "make_global_function": (0, "global_function"),
    "compare_weapon": (0, "compare"), "compare_magic": (0, "compare"),
    "count_item": (0, "compare"), "count_magic": (0, "compare"),
    "kill_this_item": (0, "compare"), "kill_this_magic": (0, "compare"),
    "get_item": (0, "compare"), "get_magic": (0, "compare"),
    "compare_sprite_script": (1, "compare"),
}
CALLING_EDGES = {"external", "spawn", "sp_script", "add_item", "add_magic", "global_function"}


def calls_rows(asts):
    rows = []
    for name, ast in asts.items():
        for proc, n, ctx in iter_procs(ast):
            runs = int(engine_runs(n, ctx))
            for c in stmt_calls(n):
                rows.append({"name": c["name"], "kind": c.get("kind", ""), "script": name,
                             "procedure": proc, "line": n["line"],
                             "args": ", ".join(X.to_text(a) for a in c["args"]),
                             "engine_executes": runs})
    return rows


def script_edges(asts):
    """[(from_script, to_script, kind, line, procedure, extra)]"""
    edges = []
    for name, ast in asts.items():
        for proc, n, ctx in iter_procs(ast):
            for c in stmt_calls(n):
                spec = SCRIPT_REF_CALLS.get(c["name"])
                if not spec:
                    continue
                k, kind = spec
                target = string_arg(c, k)
                if not target:
                    continue
                extra = string_arg(c, 1) if c["name"] == "external" else None
                edges.append((name, target.lower(), kind, n["line"], proc, extra))
    return edges


def external_diags(asts, edges, existing):
    """external()/spawn()/sp_script()/add_item() targets that do not exist."""
    out = []
    procs = {n: {p["name"] for p in a["procedures"]} for n, a in asts.items()}
    for src, dst, kind, line, proc, extra in edges:
        if kind not in CALLING_EDGES:
            continue
        if dst not in existing:
            out.append({"script": src, "file": src + ".c", "line": line,
                        "code": "missing_script_reference", "severity": "error",
                        "what": "%s refers to script %r which has no .c file" % (kind, dst),
                        "recovery": "edge kept; the engine logs 'Script not found'"})
        elif kind == "external" and extra and dst in procs and extra.lower() not in procs[dst]:
            out.append({"script": src, "file": src + ".c", "line": line,
                        "code": "missing_external_procedure", "severity": "error",
                        "what": "external(%r, %r): no such procedure" % (dst, extra),
                        "recovery": "edge kept; the engine logs 'Couldn't find procedure'"})
    return out


# --------------------------------------------------------------------------------------
# Script classification
# --------------------------------------------------------------------------------------

KIND_COLUMNS = ["script", "kind", "tags", "placed", "placed_count", "base_count", "screens",
                "called", "called_by", "engine_loaded", "procedures", "evidence"]

STAT_CALLS = ("sp_hitpoints", "sp_defense", "sp_strength", "sp_touch_damage", "sp_exp",
              "sp_speed", "sp_timing", "sp_brain", "sp_base_walk", "sp_base_idle",
              "sp_base_attack", "sp_base_hit", "sp_base_die", "sp_base_death", "sp_range",
              "sp_distance", "sp_target", "sp_nohit", "sp_notouch", "sp_frame_delay",
              "sp_hard", "sp_attack_wait", "sp_gold", "sp_attack_hit_sound",
              "sp_attack_hit_sound_speed", "sp_flying", "sp_follow", "sp_sound",
              "sp_attack_hit_sound")


def _script_features(name, ast, globals_):
    f = {"procs": [p["name"] for p in ast["procedures"]], "calls": {}, "self_stats": {},
         "gold_dec": [], "gold_cmp": 0, "says": 0, "say_stops": 0, "choices": 0,
         "freeze_player": 0, "move_stop": 0, "writes": set(), "screenlock": 0,
         "stats_on_self": 0, "brain_self": None, "init_seq": 0, "other_says": 0,
         "use_consumes": False, "warps": 0}
    for proc, n, ctx in iter_procs(ast):
        if n.get("type") == "choice":
            f["choices"] += 1
        if n.get("type") == "assign":
            f["writes"].add(n["target"].lower())
            if n["target"].lower() == "&player_map":
                f["warps"] += 1
            if n["target"].lower() == "&gold" and n["op"] == "-=":
                f["gold_dec"].append(n["line"])
        if n.get("type") == "if" and "&gold" in n["cond_text"].lower():
            f["gold_cmp"] += 1
        for c in stmt_calls(n):
            nm = c["name"]
            f["calls"][nm] = f["calls"].get(nm, 0) + 1
            if nm in ("say", "say_stop", "say_stop_npc", "say_xy", "say_stop_xy"):
                f["says"] += 1
                if nm in ("say_xy", "say_stop_xy") or arg_text(c, 1) != "1":
                    f["other_says"] += 1
            if proc == "use" and nm in ("kill_this_item", "kill_cur_item"):
                f["use_consumes"] = True
            if nm == "load_screen":
                f["warps"] += 1
            if nm == "freeze" and arg_text(c, 0) == "1":
                f["freeze_player"] += 1
            if nm == "screenlock":
                f["screenlock"] += 1
            if nm == "init":
                f["init_seq"] += 1
            if nm in STAT_CALLS and arg_text(c, 0).lower() == "&current_sprite":
                f["stats_on_self"] += 1
                if nm == "sp_brain" and int_arg(c, 1) is not None:
                    f["brain_self"] = int_arg(c, 1)
                if nm == "sp_hitpoints" and int_arg(c, 1) is not None:
                    f["self_stats"]["hitpoints"] = int_arg(c, 1)
    return f


def classify(asts, map_refs, edges, globals_, d_only=()):
    existing = set(asts)
    called_by = {}
    for src, dst, kind, line, proc, extra in edges:
        if kind in CALLING_EDGES and src != dst:
            called_by.setdefault(dst, set()).add("%s:%s" % (kind, src))
    rows = []
    for name in sorted(asts, key=str.lower):
        ast = asts[name]
        lname = name.lower()
        f = _script_features(name, ast, globals_)
        refs = map_refs.get(lname, [])
        live = [r for r in refs if r["live"]]
        sprite_refs = [r for r in live if r["kind"] == "sprite"]
        base_refs = [r for r in live if r["kind"] == "base"]
        screens = sorted({s for r in live for s in (r["screens"] or [])})
        cb = sorted(called_by.get(lname, set()))
        engine_loaded = lname in ENGINE_SCRIPTS or lname.startswith("button")
        tags, ev = [], []
        procs = set(f["procs"])
        cb_kinds = {c.split(":")[0] for c in cb}
        hp = f["self_stats"].get("hitpoints")

        cb_scripts = {c.split(":", 1)[1] for c in cb}
        if engine_loaded:
            tags.append("system"); ev.append("loaded by the engine by name")
        elif cb and not (cb_kinds & {"add_item", "add_magic"}) and \
                all(c in ENGINE_SCRIPTS or c.startswith("start") for c in cb_scripts):
            tags.append("system"); ev.append("started by %s" % ",".join(sorted(cb_scripts)))
        if "add_magic" in cb_kinds:
            tags.append("magic"); ev.append("given by add_magic")
        if "add_item" in cb_kinds or lname.startswith("item-"):
            if "add_magic" in cb_kinds:
                pass
            elif f["use_consumes"]:
                tags.append("item"); ev.append("use() removes the item (consumable)")
            elif "arm" in procs:
                tags.append("weapon"); ev.append("armed with arm()/use() and not consumed")
            else:
                tags.append("item"); ev.append("inventory script")
        if lname.startswith("dam-") or ("damage" in procs and "sp_script" in cb_kinds):
            tags.append("projectile"); ev.append("damage() script attached to a missile")
        boss = (hp is not None and hp >= 150) or ("boss" in lname)
        enemyish = (f["brain_self"] in (9, 10) or lname.startswith("en-") or
                    (f["stats_on_self"] >= 3 and "die" in procs and
                     ("sp_hitpoints" in f["calls"] or "sp_touch_damage" in f["calls"])))
        if enemyish:
            if boss:
                tags.append("boss"); ev.append(("enemy with %s hitpoints" % hp) if hp else
                                               "enemy, 'boss' in name")
            else:
                tags.append("enemy"); ev.append("sets brain %s / %s hitpoints on itself"
                                                % (f["brain_self"], hp))
        if "touch" in procs and any(w in f["writes"] for w in
                                    ("&life", "&gold", "&strength", "&defense", "&magic",
                                     "&lifemax")) and not enemyish:
            tags.append("pickup"); ev.append("touch() changes player stats")
        elif "touch" in procs and ("add_item" in f["calls"] or "add_magic" in f["calls"]) \
                and not enemyish:
            tags.append("pickup"); ev.append("touch() gives an item")
        drops = any(dst in ("make", "emake") for s_, dst, k, *_ in edges if s_ == name)
        if any(w in lname for w in ("box", "barrel", "chest", "crate", "bar-")) or \
                lname.startswith("ch") and lname[2:3].isdigit() or \
                ("hit" in procs and drops and not enemyish and "talk" not in procs):
            tags.append("container"); ev.append("breakable or openable object that drops "
                                                "items")
        if lname in ("make", "emake") or (cb and cb_kinds == {"external"} and
                                         "talk" not in procs and not base_refs):
            tags.append("library"); ev.append("only reached through external()")
        if "sign" in lname:
            tags.append("sign"); ev.append("'sign' in name")
        if base_refs:
            tags.append("screen-base"); ev.append("base script of %d map screen(s)"
                                                  % len(base_refs))
        if f["gold_dec"] and (f["choices"] or "buy" in procs):
            tags.append("shop"); ev.append("deducts &gold at line(s) %s"
                                           % ",".join(map(str, f["gold_dec"][:5])))
        if f["warps"] and ("touch" in procs or base_refs or "talk" in procs):
            tags.append("warp"); ev.append("changes screen (load_screen/&player_map)")
        if "talk" in procs and f["says"] and not enemyish:
            if f["other_says"]:
                tags.append("npc"); ev.append("talk() with %d line(s) not spoken by Dink"
                                              % f["other_says"])
            else:
                tags.append("object"); ev.append("talk()/hit() where only Dink speaks "
                                                 "(examinable object)")
        if f["freeze_player"] and (f["calls"].get("move_stop", 0) or
                                   f["calls"].get("say_stop", 0) >= 4) \
                and ("talk" not in procs or base_refs or "spawn" in cb_kinds):
            tags.append("cutscene"); ev.append("freezes Dink and runs %d say_stop / %d "
                                               "move_stop" % (f["calls"].get("say_stop", 0),
                                                              f["calls"].get("move_stop", 0)))
        placed = bool(live)
        called = bool(cb)
        real_code = any(n.get("type") not in ("comment",) for p in ast["procedures"]
                        for n in p["body"])
        if not real_code:
            tags.append("empty"); ev.append("no statements")
        if not placed and not called and not engine_loaded and "system" not in tags:
            # referenced only by "compare" edges, start.c buttons etc. still count as dead
            tags.append("dead"); ev.append("not placed in map.dat and not called by any script")
        order = ["system", "boss", "enemy", "weapon", "magic", "item", "projectile", "shop",
                 "pickup", "container", "library", "sign", "cutscene", "npc", "warp", "object",
                 "screen-base", "empty", "dead"]
        kind = next((k for k in order if k in tags), "other")
        if "dead" in tags:
            kind = "dead"
        rows.append({
            "script": name, "kind": kind, "tags": ";".join(t for t in order if t in tags),
            "placed": int(placed), "placed_count": len(sprite_refs),
            "base_count": len(base_refs),
            "screens": ";".join(str(s) for s in screens[:40]) + (";..." if len(screens) > 40 else ""),
            "called": int(called), "called_by": ";".join(cb),
            "engine_loaded": int(engine_loaded),
            "procedures": ";".join(f["procs"]),
            "evidence": "; ".join(ev),
        })
    return rows


# --------------------------------------------------------------------------------------
# Enemies, items, shops
# --------------------------------------------------------------------------------------

def _stat_name(call):
    return call[3:] if call.startswith("sp_") else call


def enemies_table(asts, kinds, map_refs, edges):
    kind_of = {r["script"]: r for r in kinds}
    out = []
    for name, ast in sorted(asts.items()):
        k = kind_of[name]
        tags = k["tags"].split(";")
        if not ({"enemy", "boss"} & set(tags)):
            # scripts that only set stats on other sprites are still interesting if they
            # set hitpoints on something
            if not any(c["name"] == "sp_hitpoints" for _p, n, _c in iter_procs(ast)
                       for c in stmt_calls(n)):
                continue
        entry = {"script": name, "kind": k["kind"], "tags": tags,
                 "procedures": [p["name"] for p in ast["procedures"]],
                 "stats": {}, "other_sprites": {}, "drops": [], "screenlock": [],
                 "sounds": [], "behaviours": [], "placed_count": k["placed_count"],
                 "editor_stats": []}
        for proc, n, ctx in iter_procs(ast):
            for c in stmt_calls(n):
                nm = c["name"]
                if nm in STAT_CALLS or nm in ("sp_nodraw", "sp_que", "sp_size", "sp_seq",
                                              "sp_frame", "sp_pseq", "sp_pframe"):
                    target = arg_text(c, 0)
                    val = c["args"][1] if len(c["args"]) > 1 else None
                    if val is None:
                        continue
                    v = val["value"] if val.get("type") == "int" else X.to_text(val)
                    rec = {"value": v, "procedure": proc, "line": n["line"]}
                    if target.lower() == "&current_sprite":
                        entry["stats"].setdefault(_stat_name(nm), []).append(rec)
                    else:
                        entry["other_sprites"].setdefault(target, {}).setdefault(
                            _stat_name(nm), []).append(rec)
                elif nm == "external":
                    tgt = (string_arg(c, 0) or "").lower()
                    if tgt in ("emake", "make") or (proc == "die" and tgt):
                        entry["drops"].append({"script": tgt, "procedure": string_arg(c, 1),
                                               "args": [X.to_text(a) for a in c["args"][2:]],
                                               "in": proc, "line": n["line"]})
                elif nm == "screenlock":
                    entry["screenlock"].append({"value": arg_text(c, 0), "in": proc,
                                                "line": n["line"]})
                elif nm == "playsound":
                    entry["sounds"].append({"sound": arg_text(c, 0), "in": proc,
                                            "line": n["line"]})
                elif nm in ("move", "move_stop", "hurt", "create_sprite", "spawn", "sp_kill",
                            "playmidi", "kill_this_task", "add_exp"):
                    entry["behaviours"].append({"call": X.to_text(c), "in": proc,
                                                "line": n["line"]})
        # flatten stats: last literal set in main() wins, others listed
        flat = {}
        for stat, recs in entry["stats"].items():
            main_recs = [r for r in recs if r["procedure"] == "main"]
            pick = (main_recs or recs)[-1]
            flat[stat] = pick["value"]
        entry["summary"] = flat
        for r in map_refs.get(name.lower(), []):
            if r["kind"] == "sprite" and r["live"]:
                es = {k2: v for k2, v in r["editor_stats"].items() if v}
                if es:
                    entry["editor_stats"].append({"record": r["record"], "sprite": r["sprite"],
                                                  "screens": r["screens"], **es})
        out.append(entry)
    return out


ITEM_EFFECT_VARS = ("&strength", "&defense", "&magic", "&life", "&lifemax", "&gold", "&exp",
                    "&magic_cost", "&cur_weapon", "&cur_magic", "&speed", "&timing")


def items_table(asts, kinds, edges):
    kind_of = {r["script"]: r for r in kinds}
    givers = {}
    for src, dst, kind, line, proc, extra in edges:
        if kind in ("add_item", "add_magic"):
            givers.setdefault(dst, []).append({"by": src, "kind": kind, "line": line,
                                               "procedure": proc})
    # seq/frame passed to add_item
    icons = {}
    for name, ast in asts.items():
        for proc, n, ctx in iter_procs(ast):
            for c in stmt_calls(n):
                if c["name"] in ("add_item", "add_magic"):
                    t = (string_arg(c, 0) or "").lower()
                    icons.setdefault(t, set()).add((arg_text(c, 1), arg_text(c, 2)))
    out = []
    for name, ast in sorted(asts.items()):
        lname = name.lower()
        k = kind_of[name]
        tags = set(k["tags"].split(";"))
        if not (tags & {"weapon", "magic", "item", "pickup"}) and lname not in givers:
            continue
        entry = {"script": name, "kind": k["kind"], "tags": sorted(tags - {""}),
                 "given_by": givers.get(lname, []),
                 "icon_seq_frame": sorted(icons.get(lname, set())),
                 "procedures": {}}
        for p in ast["procedures"]:
            effects = []
            for n, ctx in iter_stmts(p["body"]):
                if n.get("type") == "assign" and n["target"].lower() in ITEM_EFFECT_VARS:
                    effects.append({"line": n["line"], "effect": one_liner(n)})
                for c in stmt_calls(n):
                    if c["name"] in ("init", "sp_seq", "sp_base_attack", "sp_base_walk",
                                     "sp_base_idle", "sp_base_hit", "playsound",
                                     "kill_this_item", "kill_this_magic", "add_exp",
                                     "draw_status", "arm_weapon", "arm_magic",
                                     "activate_bow", "get_last_bow_power", "create_sprite",
                                     "sp_script", "add_item", "add_magic", "hurt",
                                     "sp_brain", "sp_speed", "sp_strength", "sp_timing",
                                     "sp_attack_hit_sound"):
                        effects.append({"line": n["line"], "effect": X.to_text(c)})
            if effects:
                entry["procedures"][p["name"]] = effects
        out.append(entry)
    return out


def _gold_cond_price(cond):
    """`&gold < N` / `&gold >= N` -> N."""
    if cond.get("type") == "binop" and cond["op"] in X.COMPARISONS:
        l, r = cond["left"], cond["right"]
        if l.get("type") == "var" and l["name"].lower() == "&gold" and r.get("type") == "int":
            return r["value"], cond["op"]
    return None


def shops_table(asts, choices):
    out = []
    by_script_choices = {}
    for ch in choices:
        by_script_choices.setdefault(ch["script"], []).append(ch)
    for name, ast in sorted(asts.items()):
        purchases, income, checks = [], [], []
        for p in ast["procedures"]:
            for n, ctx in iter_stmts(p["body"]):
                if n.get("type") == "if":
                    gp = _gold_cond_price(n["cond"])
                    if gp:
                        checks.append({"line": n["line"], "procedure": p["name"],
                                       "price": gp[0], "op": gp[1]})
                if n.get("type") == "assign" and n["target"].lower() == "&gold":
                    val = n["value"]
                    v = val["value"] if val.get("type") == "int" else X.to_text(val)
                    if n["op"] == "-=":
                        purchases.append({"line": n["line"], "procedure": p["name"],
                                          "price": v, "path": [
                                              ("%s:%s" % (kind, ifn["cond_text"]))
                                              for kind, ifn in ctx["path"]]})
                    elif n["op"] in ("+=", "="):
                        income.append({"line": n["line"], "procedure": p["name"],
                                       "op": n["op"], "value": v})
        if not purchases:
            continue
        # what each purchase grants: following statements in the same procedure until
        # a return or the end of the enclosing block
        for pu in purchases:
            pu["grants"] = _grants_after(ast, pu["procedure"], pu["line"])
            pu["check"] = next((c for c in reversed(checks) if c["procedure"] == pu["procedure"]
                                and c["line"] < pu["line"] and str(c["price"]) == str(pu["price"])),
                               None)
            pu["options"] = _options_reaching(by_script_choices.get(name, []), ast, pu)
        out.append({"script": name, "purchases": purchases, "gold_checks": checks,
                    "gold_income": income})
    return out


def _grants_after(ast, procname, line):
    proc = next(p for p in ast["procedures"] if p["name"] == procname)
    grants = []
    started = False
    for n, ctx in iter_stmts(proc["body"]):
        if n["line"] == line and n.get("type") == "assign":
            started = True
            continue
        if not started:
            continue
        t = n.get("type")
        if t in ("return", "goto"):
            break
        if t == "assign" and n["target"].lower() != "&gold":
            grants.append(one_liner(n))
        for c in stmt_calls(n):
            if c["name"] in ("add_item", "add_magic", "add_exp", "external", "sp_script",
                             "create_sprite", "spawn") or c.get("kind") == "local":
                grants.append(X.to_text(c))
        if len(grants) > 12:
            break
    return grants


def _options_reaching(choices, ast, pu):
    hits = []
    for ch in choices:
        for o in ch["options"]:
            b = o.get("branch")
            if not b:
                continue
            lines = [s["line"] for s in b["statements"]]
            procs = set(b["local_calls"]) | {g["target"]["procedure"] for g in b["gotos"]
                                              if g.get("target")}
            inside = ch["procedure"] == pu["procedure"] and lines and \
                min(lines) <= pu["line"] <= max(lines)
            if inside or pu["procedure"] in procs:
                hits.append({"choice_line": ch["line"], "index": o["index"],
                             "text": o["text"]})
    return hits
