"""Content packs: the authoring format (Plugins/DinkExpanded/Packs/<pack>/pack.toml + story/*.c) and its rules.

A pack never changes 1997 data. Everything here is checked against the 1997 tables the Unreal project
ships (Content/Dink/Data/Gameplay, Content/Dink/Data/Facts) and the 1997 scripts (bin/dink/story), and,
when it exists, against tools/analyse/out (which 1997 land is reached by design).
"""

import csv
import os
import re
import tomllib

W, H = 600, 400
BAR = 20                      # placements.csv x includes the 20 px status bar (dinkex map_x = x - 20)
KINDS = ("wilderness", "settlement", "dungeon", "interior")
PLACEMENT_KINDS = ("npc", "creature", "item", "prop")
# 1997 engine stats a pack script may change (rewards, damage, menus). Every other 1997 global is the
# 1997 story's: packs read it at most.
WRITABLE_BASE_GLOBALS = {"gold", "life", "lifemax", "strength", "defense", "magic", "exp", "vision",
                         "result", "last_text", "missile_target", "enemy_sprite", "missle_source"}
# Pack scripts must not outlive the pack's screens (they would run in the 1997 world).
FORBIDDEN_CALLS = {"script_attach": "script_attach (a pack script must end with its screen)",
                   "load_game": "load_game", "save_game": "save_game (saves belong to the 1997 save machines)",
                   "restart_game": "restart_game", "kill_game": "kill_game"}


class PackError(Exception):
    pass


def _rect(v, where):
    if not (isinstance(v, list) and len(v) == 4 and all(isinstance(x, int) for x in v)):
        raise PackError("%s: a rectangle is [x0, y0, x1, y1] in map pixels" % where)
    x0, y0, x1, y1 = v
    if not (0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H):
        raise PackError("%s: rectangle %s is not inside 600 x 400" % (where, v))
    return v


def _point(v, where):
    if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)):
        raise PackError("%s: a point is [x, y] in map pixels" % where)
    if not (0 <= v[0] <= W and 0 <= v[1] <= H):
        raise PackError("%s: point %s is not inside 600 x 400" % (where, v))
    return [v[0], v[1]]


class Pack:
    """One pack.toml, read and shape-checked (no 1997 data needed)."""

    def __init__(self, path):
        self.dir = os.path.dirname(os.path.abspath(path))
        with open(path, "rb") as fh:
            d = tomllib.load(fh)
        p = d.get("pack") or {}
        self.id = str(p.get("id", "")).lower()
        self.number = p.get("number")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.id or ""):
            raise PackError("%s: pack.id must be lower-case letters, digits, _" % path)
        if not isinstance(self.number, int) or not 1 <= self.number <= 9:
            raise PackError("pack %s: number must be 1-9 (it names the namespace x<n>)" % self.id)
        self.prefix_script = "x%d-" % self.number
        self.prefix_global = "x%d_" % self.number
        self.name = p.get("name", self.id)
        self.wave = p.get("wave", "")
        self.status = p.get("status", "greybox")
        self.draft = bool(p.get("draft", True))
        self.approved = str(p.get("approved", ""))      # the date the owner approved the text (with draft = false)
        self.sheets = []
        for s in d.get("sheet", []):
            sid = str(s.get("id", "")).lower()
            kind = s.get("kind", "wilderness")
            if kind not in KINDS:
                raise PackError("pack %s sheet %s: kind %s not one of %s" % (self.id, sid, kind, KINDS))
            direction = s.get("direction", [-1.0, 0.0])
            self.sheets.append({"id": sid, "kind": kind, "direction": [float(direction[0]), float(direction[1])],
                                "gap_m": float(s.get("gap_m", 1500.0))})
        sheet_ids = {s["id"] for s in self.sheets}
        self.screens = []
        cells = set()
        for s in d.get("screen", []):
            n = s.get("screen")
            where = "pack %s screen %s" % (self.id, n)
            if not isinstance(n, int):
                raise PackError("%s: screen must be an int" % where)
            sheet = str(s.get("sheet", "")).lower()
            if sheet not in sheet_ids:
                raise PackError("%s: sheet %r is not declared" % (where, sheet))
            grid = s.get("grid")
            if not (isinstance(grid, list) and len(grid) == 2 and all(isinstance(g, int) and g >= 0 for g in grid)):
                raise PackError("%s: grid is [col, row] on its sheet" % where)
            if (sheet, tuple(grid)) in cells:
                raise PackError("%s: grid cell %s taken" % (where, grid))
            cells.add((sheet, tuple(grid)))
            kind = s.get("kind", "wilderness")
            if kind not in KINDS:
                raise PackError("%s: kind %s" % (where, kind))
            base = str(s.get("base_script", "")).lower()
            if base and not base.startswith(self.prefix_script):
                raise PackError("%s: base script %s is outside the namespace %s" % (where, base, self.prefix_script))
            self.screens.append({
                "screen": n, "grid": grid, "sheet": sheet, "name": s.get("name", ""), "kind": kind,
                "region": str(s.get("region", self.id)).lower(), "base_script": base,
                "music": int(s.get("music", 0)), "indoor": bool(s.get("indoor", kind == "interior")),
                "solids": [_rect(r, where + " solid") for r in s.get("solids", [])],
            })
        own = {s["screen"] for s in self.screens}
        self.placements = []
        seen = set()
        for pl in d.get("placement", []):
            where = "pack %s placement S%s_P%s" % (self.id, pl.get("screen"), pl.get("index"))
            if pl.get("screen") not in own:
                raise PackError("%s: placements go on the pack's own screens only" % where)
            idx = pl.get("index")
            if not isinstance(idx, int) or not 1 <= idx <= 99 or (pl["screen"], idx) in seen:
                raise PackError("%s: index must be 1..99 and unique on the screen" % where)
            seen.add((pl["screen"], idx))
            kind = pl.get("kind", "prop")
            if kind not in PLACEMENT_KINDS:
                raise PackError("%s: kind %s not one of %s" % (where, kind, PLACEMENT_KINDS))
            script = str(pl.get("script", "")).lower()
            x, y = _point([pl.get("x", -1), pl.get("y", -1)], where)
            self.placements.append({
                "screen": pl["screen"], "index": idx, "x": int(x), "y": int(y),
                "seq": int(pl.get("seq", 0)), "frame": int(pl.get("frame", 1)), "brain": int(pl.get("brain", 0)),
                "size": int(pl.get("size", 100)), "script": script, "kind": kind, "name": pl.get("name", ""),
                "hard": bool(pl.get("hard", False)),
                "hitpoints": int(pl.get("hitpoints", 0)), "strength": int(pl.get("strength", 0)),
                "defense": int(pl.get("defense", 0)), "exp": int(pl.get("exp", 0)),
                "touch_damage": int(pl.get("touch_damage", 0)), "speed": int(pl.get("speed", 1)),
                "timing": int(pl.get("timing", 0)), "base_walk": int(pl.get("base_walk", -1)),
                "base_idle": int(pl.get("base_idle", -1)), "base_attack": int(pl.get("base_attack", -1)),
                "base_die": int(pl.get("base_die", -1)), "nohit": int(pl.get("nohit", 0)),
            })
        self.joins = []
        for j in d.get("join", []):
            jid = j.get("id", "")
            where = "pack %s join %s" % (self.id, jid)
            try:
                frm, to, back, ret = j["from"], j["to"], j["back"], j["return"]
            except KeyError as e:
                raise PackError("%s: needs from, to, back and return (%s missing)" % (where, e))
            if frm["screen"] in own or ret["screen"] in own:
                raise PackError("%s: from and return are 1997 screens" % where)
            if to["screen"] not in own or back["screen"] not in own:
                raise PackError("%s: to and back are the pack's screens" % where)
            req = j.get("requires")
            if req and not str(req.get("fact", "")).startswith(self.prefix_global):
                raise PackError("%s: a join condition reads a pack fact (%s*)" % (where, self.prefix_global))
            self.joins.append({
                "id": jid, "note": j.get("note", ""),
                "from": {"screen": frm["screen"], "rect": _rect(frm["rect"], where + " from")},
                "to": {"screen": to["screen"], "point": _point(to["point"], where + " to")},
                "back": {"screen": back["screen"], "rect": _rect(back["rect"], where + " back")},
                "return": {"screen": ret["screen"], "point": _point(ret["point"], where + " return")},
                "requires": ({"fact": req["fact"], "at_least": int(req.get("at_least", 1))} if req else None),
            })
        self.story_dir = os.path.join(self.dir, "story")
        self.scripts = sorted(f[:-2].lower() for f in os.listdir(self.story_dir) if f.endswith(".c")) \
            if os.path.isdir(self.story_dir) else []

    def runtime(self):
        """The packs.json entry (map pixels; DinkExpanded's FDinkExpandedRegistry reads it)."""
        return {
            "id": self.id, "number": self.number, "name": self.name, "wave": self.wave, "status": self.status,
            "draft": self.draft, "sheets": self.sheets,
            "screens": self.screens,
            "placements": [{k: p[k] for k in ("screen", "index", "x", "y", "seq", "frame", "brain", "size", "script",
                                              "kind", "name", "hard")} for p in self.placements],
            "joins": [{k: j[k] for k in ("id", "from", "to", "back", "return", "requires")} for j in self.joins],
        }


def find_packs(packs_dir):
    out = []
    if not os.path.isdir(packs_dir):
        return out
    for name in sorted(os.listdir(packs_dir)):
        p = os.path.join(packs_dir, name, "pack.toml")
        if os.path.isfile(p):
            out.append(Pack(p))
    return out


# ---------------------------------------------------------------------------------------------------
# 1997 data the rules read (all tracked in the repository)

class Base:
    def __init__(self, project, story_dir, analyse_out=None):
        self.project = project
        gp = os.path.join(project, "Content", "Dink", "Data", "Gameplay")
        self.gameplay_dir = gp
        with open(os.path.join(gp, "screens.csv"), newline="") as fh:
            self.screens = {int(r["screen"]): r["base_script"] for r in csv.DictReader(fh)}
        with open(os.path.join(gp, "placements.csv"), newline="") as fh:
            rows = list(csv.reader(fh))
        self.placement_header = rows[0]
        self.placements = [dict(zip(rows[0], r)) for r in rows[1:]]
        self.globals = {}
        with open(os.path.join(project, "Content", "Dink", "Data", "Facts", "dink_globals.csv")) as fh:
            for line in fh:
                if line.startswith("#") or line.startswith("name,"):
                    continue
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    self.globals[parts[0].lower()] = parts[2]
        self.story_dir = story_dir
        self.script_names = {f[:-2].lower() for f in os.listdir(story_dir) if f.endswith(".c")}
        # Every screen number a 1997 script names in &player_map assignments.
        self.script_screens = set()
        for f in os.listdir(story_dir):
            if f.endswith(".c"):
                with open(os.path.join(story_dir, f), errors="replace") as fh:
                    for m in re.finditer(r"&player_map\s*=\s*(\d+)", fh.read()):
                        self.script_screens.add(int(m.group(1)))
        self.analyse_out = analyse_out if analyse_out and os.path.isdir(analyse_out) else None
        self._hard = {}

    def hardness(self, screen):
        """{vision: [[code] * 600] * 400} from Hardness/SCR_nnn.txt (the same RLE the runtime parses)."""
        if screen not in self._hard:
            out = {}
            cur = None
            path = os.path.join(self.gameplay_dir, "Hardness", "SCR_%03d.txt" % screen)
            with open(path) as fh:
                for line in fh:
                    line = line.rstrip("\n")
                    if line.startswith("#"):
                        continue
                    if line == "tiles" or line.startswith("vision "):
                        cur = []
                        out["tiles" if line == "tiles" else int(line[7:])] = cur
                        continue
                    if cur is None or len(cur) >= H:
                        continue
                    row = []
                    for tok in line.split():
                        n, _, code = tok.partition(":")
                        row.extend([int(code or 0)] * int(n))
                    cur.append(row[:W] + [0] * (W - len(row)))
            self._hard[screen] = out
        return self._hard[screen]

    def reach_level(self, screen):
        if not self.analyse_out:
            return None
        with open(os.path.join(self.analyse_out, "regions.csv"), newline="") as fh:
            for r in csv.DictReader(fh):
                if int(r["screen"]) == screen:
                    return r["reach_level"], r["indoor"] == "1"
        return None


def check_against_base(packs, base):
    """Every rule that needs the 1997 data. Returns a list of problems (empty = fine)."""
    problems = []
    owners = {}
    numbers = {}
    for p in packs:
        if p.number in numbers:
            problems.append("packs %s and %s share number %d (namespace x%d)" % (numbers[p.number], p.id, p.number, p.number))
        numbers[p.number] = p.id
        for s in p.screens:
            n = s["screen"]
            if not 1 <= n <= 768:
                problems.append("pack %s: screen %d is outside the 1997 map's 1..768" % (p.id, n))
            if n in base.screens:
                problems.append("pack %s: screen %d is a 1997 screen (map.dat has a record); packs own only unused slots" % (p.id, n))
            if n in base.script_screens:
                problems.append("pack %s: screen %d is named by a 1997 script (&player_map)" % (p.id, n))
            if n in owners:
                problems.append("pack %s: screen %d is also owned by pack %s" % (p.id, n, owners[n]))
            owners[n] = p.id
        for sc in p.scripts:
            if not sc.startswith(p.prefix_script):
                problems.append("pack %s: script %s.c is outside the namespace %s*" % (p.id, sc, p.prefix_script))
            if sc in base.script_names:
                problems.append("pack %s: script %s.c has the name of a 1997 script" % (p.id, sc))
        for pl in p.placements:
            sc = pl["script"]
            if sc and not sc.startswith(p.prefix_script) and sc not in base.script_names:
                problems.append("pack %s: placement S%d_P%02d runs %s, neither the pack's nor a 1997 script" % (p.id, pl["screen"], pl["index"], sc))
        for j in p.joins:
            problems.extend(check_join(p, j, base))
        problems.extend(check_scripts(p, base))
    return problems


def check_join(pack, j, base):
    """The 1997 side of a join: an overlay trigger on land the player really reaches, clear of everything 1997 put there."""
    out = []
    where = "pack %s join %s" % (pack.id, j["id"])
    for side in ("from", "return"):
        n = j[side]["screen"]
        if n not in base.screens:
            out.append("%s: %s screen %d has no 1997 map record" % (where, side, n))
            return out
    x0, y0, x1, y1 = j["from"]["rect"]
    rx, ry = j["return"]["point"]
    for screen, rect, label in ((j["from"]["screen"], (x0, y0, x1, y1), "trigger"),
                                (j["return"]["screen"], (int(rx) - 6, int(ry) - 6, int(rx) + 6, int(ry) + 6), "return point")):
        hard = base.hardness(screen)
        for vision, grid in hard.items():
            if vision == "tiles":
                continue
            bad = [(x, y, grid[y][x]) for y in range(max(0, rect[1]), min(H, rect[3]))
                   for x in range(max(0, rect[0]), min(W, rect[2])) if grid[y][x] != 0]
            if bad:
                out.append("%s: %s on SCR_%03d is not open ground in vision %s (%d pixels with hardness, e.g. %s)"
                           % (where, label, screen, vision, len(bad), bad[0]))
                break
        # Keep clear of every scripted 1997 sprite (its touch/talk box) and every warp: the overlay must not stand on 1997 business.
        for pl in base.placements:
            if int(pl["screen"]) != screen or pl["type"] != "1":
                continue
            px, py = int(pl["x"]) - BAR, int(pl["y"])
            scripted = bool(pl["script"]) or pl["prop"] == "1"
            margin = 40 if scripted else 0
            if scripted and rect[0] - margin <= px < rect[2] + margin and rect[1] - margin <= py < rect[3] + margin:
                out.append("%s: %s on SCR_%03d is within %d px of 1997 sprite %s (%s)" % (where, label, screen, margin, pl["origin"], pl["script"] or "warp"))
    reach = base.reach_level(j["from"]["screen"])
    if reach is not None:
        level, indoor = reach
        if level != "design":
            out.append("%s: SCR_%03d is reached '%s', not by design (tools/analyse regions.csv)" % (where, j["from"]["screen"], level))
    return out


_ASSIGN = re.compile(r"^\s*(?:int\s+)?&([a-z0-9_\-]+)\s*(=|\+=|-=|\*=|/=)", re.I)
_LOCAL = re.compile(r"\bint\s+&([a-z0-9_\-]+)", re.I)
_GLOBAL = re.compile(r"make_global_int\s*\(\s*\"&([a-z0-9_\-]+)\"\s*,\s*(-?\d+)", re.I)
_CALL = re.compile(r"\b([a-z_][a-z0-9_]*)\s*\(", re.I)


def check_scripts(pack, base):
    """Pack scripts keep to their namespace: own globals x<n>_*, 1997 story globals read-only, no script outliving its screen."""
    out = []
    for sc in pack.scripts:
        with open(os.path.join(pack.story_dir, sc + ".c"), errors="replace") as fh:
            text = fh.read()
        locals_ = {m.group(1).lower() for m in _LOCAL.finditer(text)}
        for m in _GLOBAL.finditer(text):
            name, init = m.group(1).lower(), int(m.group(2))
            if not name.startswith(pack.prefix_global):
                out.append("pack %s: %s.c declares global &%s outside the namespace &%s*" % (pack.id, sc, name, pack.prefix_global))
            if init != 0:
                out.append("pack %s: %s.c gives &%s the initial value %d; pack globals start at 0 (facts that do not exist read 0)" % (pack.id, sc, name, init))
        for ln, line in enumerate(text.splitlines(), 1):
            code = line.split("//", 1)[0]
            m = _ASSIGN.match(code)
            if m:
                name = m.group(1).lower()
                if name in locals_ or name.startswith(pack.prefix_global):
                    pass
                elif name in base.globals and name not in WRITABLE_BASE_GLOBALS:
                    out.append("pack %s: %s.c:%d writes the 1997 story global &%s (packs read 1997 story state, never write it)" % (pack.id, sc, ln, name))
                elif name not in base.globals and name not in locals_:
                    out.append("pack %s: %s.c:%d writes &%s, which is neither a local, a pack global nor a 1997 global" % (pack.id, sc, ln, name))
            for c in _CALL.finditer(code):
                if c.group(1).lower() in FORBIDDEN_CALLS:
                    out.append("pack %s: %s.c:%d calls %s" % (pack.id, sc, ln, FORBIDDEN_CALLS[c.group(1).lower()]))
    return out
