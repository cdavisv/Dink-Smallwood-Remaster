"""Region assignment from regions.toml plus evidence from the data."""

import re
import tomllib

from .ir import col_row, screen_id
from .scripts import Scripts

KINDS = ("settlement", "wilderness", "sea", "dungeon", "interior")


def load_table(path):
    with open(path, "rb") as fh:
        t = tomllib.load(fh)
    t.setdefault("area", [])
    t.setdefault("interior", [])
    t.setdefault("stretch", [])
    t.setdefault("sheets", {})
    t.setdefault("join", [])
    for a in t["area"]:
        a.setdefault("cells", [])
        a.setdefault("screens", [])
        a.setdefault("prefixes", [])
        a.setdefault("music", [])
        a.setdefault("signs", [])
        if a["kind"] not in KINDS:
            raise ValueError("area %s: unknown kind %r" % (a["region"], a["kind"]))
        if a["sheet"] not in t["sheets"]:
            raise ValueError("area %s: sheet %r not declared in [sheets]" % (a["region"], a["sheet"]))
    return t


def in_cells(cells, c, r):
    return any(c0 <= c <= c1 and r0 <= r <= r1 for c0, r0, c1, r1 in cells)


def assign_outdoor(ir, table):
    """screen -> area dict (outdoor screens only)."""
    out = {}
    for n in ir.used:
        if ir.indoor(n):
            continue
        c, r = col_row(n)
        hit = None
        for a in table["area"]:
            if n in a["screens"]:
                hit = a
                break
        if hit is None:
            for a in table["area"]:
                if in_cells(a["cells"], c, r):
                    hit = a
                    break
        out[n] = hit
    return out


def screen_evidence(ir, scripts, n):
    names = ir.scripts_on(n)
    prefixes = sorted({p for p in (Scripts.prefix(x) for x in names) if p})
    signs = []
    for x in names:
        if "sign" in x:
            t = scripts.sign_text(x)
            if t:
                signs.append(t)
    return {"prefixes": prefixes, "music": ir.screens[n]["music"]["raw"], "signs": signs,
            "scripts": sorted(set(names))}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def judge(area, ev, all_areas):
    """(confidence, reasons) for one outdoor screen."""
    pos, neg = [], []
    for p in ev["prefixes"]:
        if p in area["prefixes"]:
            pos.append("prefix " + p)
        else:
            owners = sorted({a["region"] for a in all_areas if p in a["prefixes"]})
            if owners and area["region"] not in owners:
                neg.append("prefix %s (usually %s)" % (p, "/".join(owners)))
    if ev["music"] not in (0,):
        if ev["music"] in area["music"]:
            pos.append("music %d" % ev["music"])
        else:
            owners = sorted({a["region"] for a in all_areas if ev["music"] in a["music"]})
            if owners and area["region"] not in owners:
                neg.append("music %d (usually %s)" % (ev["music"], "/".join(owners)))
    for s in ev["signs"]:
        if any(_norm(k) in _norm(s) for k in area["signs"]):
            pos.append("sign '%s'" % s)
    if pos and not neg:
        conf = "high"
    elif pos and neg:
        conf = "medium"
    elif neg:
        conf = "low"
    else:
        conf = "medium"   # geography only (table cell); refined below with connectivity
    return conf, pos, neg


# A screen is named for its normal state (vision 0). Placements gated on a vision value are the
# other states (SCR_001: vision 1 burning, 2 burnt), so a name that describes one of them is wrong.
STATE_WORDS = re.compile(r"\b(burning|burnt|burned|ruins?|ruined)\b", re.I)


def state_name_warnings(rows):
    """Messages for screens with vision-gated placements whose name or sub-area describes a state."""
    out = []
    for r in rows:
        if r.get("vision_states") and STATE_WORDS.search(r["sub_area"] or ""):
            out.append("%s sub-area %r names a vision state; name the vision-0 state (%s)" % (
                r["id"], r["sub_area"], r["vision_states"]))
    return out
