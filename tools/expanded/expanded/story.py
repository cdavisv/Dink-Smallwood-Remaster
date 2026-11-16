"""The packs' scripts in the 1997 story.

The pack DinkC scripts go through the same converter as the 1997 ones (tools/dinkc -> tools/dinkink ->
inklecate), compiled together with the 1997 scripts so they share its globals. The result is then MERGED
into the project's shipped 1997 story (Content/Dink/Data/Story/dink.json): the packs add knots and VARs,
and every 1997 container stays byte-for-byte what the 1997 story has (checked here, and again by the
tests). The merged story is what the game loads only while the DinkExpanded switch is on.
"""

import copy
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))


class StoryError(Exception):
    pass


def _run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise StoryError("%s failed (%d):\n%s\n%s" % (" ".join(cmd[:4]), r.returncode, r.stdout[-3000:], r.stderr[-3000:]))
    return r.stdout


def convert(base_story_dir, packs, work, data_dir):
    """dinkc + dinkink on the 1997 scripts plus every pack's story/*.c. Returns the dinkink out dir."""
    scripts = os.path.join(work, "story")
    os.makedirs(scripts, exist_ok=True)
    for f in os.listdir(base_story_dir):
        shutil.copy2(os.path.join(base_story_dir, f), scripts)
    for p in packs:
        for sc in p.scripts:
            shutil.copy2(os.path.join(p.story_dir, sc + ".c"), os.path.join(scripts, sc + ".c"))
    dinkc_out = os.path.join(work, "dinkc")
    ink_out = os.path.join(work, "dinkink")
    py = sys.executable
    _run([py, "-m", "dinkc", "build", "--scripts", scripts, "--map", os.path.join(data_dir, "map.dat"),
          "--dat", os.path.join(data_dir, "dink.dat"), "--out", dinkc_out, "--no-d-check"], os.path.join(REPO, "tools", "dinkc"))
    _run([py, "-m", "dinkink", "build", "--ast", dinkc_out, "--out", ink_out, "--no-file-check"],
         os.path.join(REPO, "tools", "dinkink"))
    return ink_out


def _named(story):
    named = story["root"][-1]
    if not isinstance(named, dict):
        raise StoryError("story root has no named container dictionary")
    return named


def _decls(gdecl):
    """'global decl' container -> ([(value_tokens, name)], index of '/ev').

    inklecate writes: ev, <value>, {VAR=: n1}, <value>, {VAR=: n2}, ..., /ev, end; a value is one token (0) or a
    string run (str, ^text, /str)."""
    if not gdecl or gdecl[0] != "ev":
        raise StoryError("'global decl' does not start with ev")
    out = []
    start = 1
    for i, tok in enumerate(gdecl):
        if isinstance(tok, dict) and "VAR=" in tok:
            out.append((gdecl[start:i], tok["VAR="]))
            start = i + 1
    end = start
    if gdecl[end:end + 2] != ["/ev", "end"]:
        raise StoryError("unexpected 'global decl' layout at %d: %r" % (end, gdecl[end:end + 3]))
    return out, end


def merge(base_json, superset_json, packs):
    """1997 story + the packs' knots and VARs. Raises StoryError if a 1997 container would change."""
    base = json.loads(base_json)
    sup = json.loads(superset_json)
    bn, sn = _named(base), _named(sup)
    prefixes = tuple("d_x%d_" % p.number for p in packs)
    gprefixes = tuple("x%d_" % p.number for p in packs)
    changed = [k for k in bn if k != "global decl" and bn[k] != sn.get(k)]
    if changed:
        raise StoryError("the converter's 1997 knots differ from the project's shipped story (%s ...): sync the story first "
                         "(Scripts/sync_story.py) or the pack changed a 1997 knot" % ", ".join(changed[:5]))
    extra = [k for k in sn if k not in bn]
    stray = [k for k in extra if not k.startswith(prefixes)]
    if stray:
        raise StoryError("knots outside the packs' namespaces: %s" % ", ".join(stray[:10]))
    bdecl, bend = _decls(bn["global decl"])
    sdecl, _ = _decls(sn["global decl"])
    bnames = {n for _, n in bdecl}
    sdict = {n: v for v, n in sdecl}
    for v, n in bdecl:
        if sdict.get(n) != v:
            raise StoryError("1997 VAR %s changed its initial value in the superset" % n)
    new = [(v, n) for v, n in sdecl if n not in bnames]
    for v, n in new:
        # Pack globals x<n>_*; pack script locals become x<n>_<script>__<local> (the converter's naming).
        if not n.startswith(gprefixes):
            raise StoryError("VAR %s is outside the packs' namespaces" % n)
        if v != [0]:
            raise StoryError("pack VAR %s starts at %r; pack variables start at 0" % (n, v))
    merged = copy.deepcopy(base)
    mn = _named(merged)
    for k in extra:
        mn[k] = sn[k]
    gd = mn["global decl"]
    insert = []
    for v, n in new:
        insert.extend(v + [{"VAR=": n}])
    mn["global decl"] = gd[:bend] + insert + gd[bend:]
    return merged, extra, [n for _, n in new]


def merged_names(base_names_csv, superset_names_csv, packs):
    """names.csv: the 1997 rows unchanged, then every row the packs add."""
    prefixes_script = tuple("x%d-" % p.number for p in packs)
    prefixes_global = tuple("&x%d_" % p.number for p in packs)
    base_rows = list(csv.reader(io.StringIO(base_names_csv)))
    base_set = {tuple(r) for r in base_rows}
    add = []
    for r in csv.reader(io.StringIO(superset_names_csv)):
        if tuple(r) in base_set:
            continue
        kind, original, ink, scope, script = r
        if not (script.startswith(prefixes_script) or original.lower().startswith(prefixes_global)):
            raise StoryError("names.csv row outside the packs: %s" % r)
        add.append(r)
    missing = [r for r in base_rows if tuple(r) not in {tuple(x) for x in csv.reader(io.StringIO(superset_names_csv))}]
    if missing:
        raise StoryError("the superset lost 1997 names rows: %s" % missing[:3])
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    for r in base_rows + add:
        w.writerow(r)
    return buf.getvalue(), add


def pack_lines(ink_out, packs):
    """Every spoken line, title and option of the packs' scripts (line_ids.csv rows): the owner's draft table."""
    prefixes = tuple("x%d-" % p.number for p in packs)
    with open(os.path.join(ink_out, "line_ids.csv"), newline="") as fh:
        return [r for r in csv.DictReader(fh) if r["script"].startswith(prefixes)]


def pack_review(ink_out, packs):
    """The converter's review findings on pack scripts (new code must have none that change behaviour)."""
    prefixes = tuple("x%d-" % p.number for p in packs)
    path = os.path.join(ink_out, "review_queue.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="") as fh:
        return [r for r in csv.DictReader(fh) if r["script"].startswith(prefixes)]
