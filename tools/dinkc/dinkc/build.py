"""`python3 -m dinkc build`: parse every script and write all tables."""

import csv
import json
import os
import re
import time

from . import analysis as A
from . import mapdat, parser, source


def _write_csv(path, columns, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False, default=_json_default)
        f.write("\n")


def _json_default(o):
    if isinstance(o, set):
        return sorted(o)
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(type(o))


def parse_all(scripts_dir, global_functions=()):
    asts = {}
    for name in source.list_scripts(scripts_dir):
        text = source.load_c(os.path.join(scripts_dir, name + ".c"))
        asts[name.lower()] = parser.parse_script(name.lower(), text, global_functions)
    return asts


def build(scripts_dir, map_path, dat_path, out_dir, log=print, check_d=True):
    t0 = time.time()
    os.makedirs(os.path.join(out_dir, "ast"), exist_ok=True)

    asts = parse_all(scripts_dir)
    # make_global_function targets are callable from anywhere; re-resolve if any exist.
    gfuncs = set()
    for name, ast in asts.items():
        for proc, n, ctx in A.iter_procs(ast):
            for c in A.stmt_calls(n):
                if c["name"] == "make_global_function" and A.string_arg(c, 1):
                    gfuncs.add(A.string_arg(c, 1).lower())
    if gfuncs:
        asts = parse_all(scripts_dir, gfuncs)

    global_diags = []
    # .d checks
    d_only = source.list_d_only(scripts_dir)
    for d in d_only:
        global_diags.append({
            "script": d.lower(), "file": d + ".d", "line": None, "code": "d_without_c",
            "severity": "warning",
            "what": "%s.d exists with no %s.c; the engine would load the .d" % (d, d),
            "recovery": "not parsed into an AST (the pipeline reads .c files only)"})
    if check_d:
        for name in sorted(asts):
            dp = os.path.join(scripts_dir, name + ".d")
            if os.path.exists(dp):
                c_txt = source.load_c(os.path.join(scripts_dir, name + ".c"))
                if source.comparable(c_txt) != source.comparable(source.load_d(dp)):
                    global_diags.append({
                        "script": name, "file": name + ".d", "line": None,
                        "code": "d_differs_from_c", "severity": "error",
                        "what": "%s.d does not decode to the same text as %s.c; the engine "
                                "prefers the .d" % (name, name),
                        "recovery": "the AST is built from the .c"})

    # map.dat
    map_refs, n_records = mapdat.script_references(map_path, dat_path)
    for sname, refs in sorted(map_refs.items()):
        if sname not in asts:
            live = [r for r in refs if r["live"]]
            global_diags.append({
                "script": sname, "file": sname + ".c", "line": None,
                "code": "map_script_missing", "severity": "error",
                "what": "map.dat references script %r (%d live reference(s): %s) but there "
                        "is no .c file%s" % (
                            sname, len(live),
                            ", ".join("%s rec %d%s screens %s" % (
                                r["kind"], r["record"],
                                (" sprite %d" % r["sprite"]) if r["sprite"] else "",
                                r["screens"]) for r in refs[:6]),
                            " (a .d exists)" if os.path.exists(
                                os.path.join(scripts_dir, sname + ".d")) else ""),
                "recovery": "listed only; the engine logs 'Script not found' and the "
                            "sprite has no script"})
        for r in refs:
            if not r["live"] and r["kind"] == "sprite":
                pass

    globals_ = A.collect_globals(asts)
    edges = A.script_edges(asts)
    existing = set(asts) | {d.lower() for d in d_only}
    global_diags.extend(A.external_diags(asts, edges, existing))

    # Tables
    dialog, dlg_diags = A.dialog_rows(asts, globals_)
    choices = A.choices_table(asts)
    facts, shadow_diags = A.facts_rows(asts, globals_)
    var_diags = A.undeclared_var_diags(asts, globals_)
    calls = A.calls_rows(asts)
    kinds = A.classify(asts, map_refs, edges, globals_, d_only)
    enemies = A.enemies_table(asts, kinds, map_refs, edges)
    items = A.items_table(asts, kinds, edges)
    shops = A.shops_table(asts, choices)

    # Per-script diagnostics that analysis found go into the ASTs too.
    extra_by_script = {}
    for d in dlg_diags + shadow_diags + var_diags:
        extra_by_script.setdefault(d["script"], []).append(d)
    for name, ast in asts.items():
        ast["diagnostics"].extend(extra_by_script.get(name, []))
        ast["diagnostics"].sort(key=lambda d: (d["line"] or 0, d["code"]))
        _write_json(os.path.join(out_dir, "ast", name + ".json"), ast)

    all_diags = [d for name in sorted(asts) for d in asts[name]["diagnostics"]] + global_diags
    by_code = {}
    for d in all_diags:
        by_code[d["code"]] = by_code.get(d["code"], 0) + 1

    _write_csv(os.path.join(out_dir, "dialog_lines.csv"), A.DIALOG_COLUMNS, dialog)
    _write_json(os.path.join(out_dir, "choices.json"), choices)
    _write_csv(os.path.join(out_dir, "facts.csv"), A.FACT_COLUMNS, facts)
    _write_csv(os.path.join(out_dir, "script_kinds.csv"), A.KIND_COLUMNS, kinds)
    _write_json(os.path.join(out_dir, "enemies.json"), enemies)
    _write_json(os.path.join(out_dir, "items.json"), items)
    _write_json(os.path.join(out_dir, "shops.json"), shops)
    _write_csv(os.path.join(out_dir, "calls.csv"), A.CALL_COLUMNS, calls)
    _write_json(os.path.join(out_dir, "globals.json"), globals_)
    _write_json(os.path.join(out_dir, "diagnostics.json"),
                {"counts_by_code": dict(sorted(by_code.items())),
                 "count": len(all_diags), "diagnostics": all_diags})

    n_procs = sum(len(a["procedures"]) for a in asts.values())
    kind_counts = {}
    for r in kinds:
        kind_counts[r["kind"]] = kind_counts.get(r["kind"], 0) + 1
    summary = {
        "scripts": len(asts), "parse_failures": 0, "procedures": n_procs,
        "dialog_lines": len(dialog), "choices": len(choices),
        "choice_options": sum(len(c["options"]) for c in choices),
        "globals": len(globals_), "fact_rows": len(facts), "calls": len(calls),
        "diagnostics": len(all_diags), "diagnostics_by_code": dict(sorted(by_code.items())),
        "map_records": n_records, "script_kinds": dict(sorted(kind_counts.items())),
        "enemies": len(enemies), "items": len(items), "shops": len(shops),
        "seconds": round(time.time() - t0, 2),
    }
    _write_json(os.path.join(out_dir, "summary.json"), summary)
    return summary
