"""Plain-text scans of the DinkC scripts in bin/dink/story (provisional).

This is deliberately not a parser (tools/dinkc is the real one). It finds:
- script-driven screen changes (`&player_map = N;` + `sp_x(1, X)` / `sp_y(1, Y)`),
- `screenlock(1)` calls,
- sign texts (the first backtick-% string in `*sign*` scripts),
- which other scripts a script names (string literals), for one level of
  indirection when a script is spawned rather than placed on the map.
Comments (`//` to end of line) are stripped before matching.
"""

import glob
import os
import re

RE_MAP = re.compile(r"&player_map\s*=\s*(\d+)\s*;")
RE_SPX = re.compile(r"sp_x\s*\(\s*1\s*,\s*(-?\d+)\s*\)")
RE_SPY = re.compile(r"sp_y\s*\(\s*1\s*,\s*(-?\d+)\s*\)")
RE_LOCK = re.compile(r"screenlock\s*\(\s*1\s*\)")
RE_STR = re.compile(r'"([^"\n]*)"')
RE_PREFIX = re.compile(r"^(s[1-8]|sc)-")
RE_PROC = re.compile(r"^\s*void\s+(\w+)", re.I)
RE_WALKOFF = re.compile(r"dink_can_walk_off_screen\s*\(\s*(\d+)\s*\)", re.I)
RE_MOVE1 = re.compile(r"\b(move_stop|move)\s*\(\s*1\s*,\s*(\d+)\s*,\s*(-?\d+)\s*,\s*(\d+)\s*\)", re.I)
# calls that start another script: spawn("x"), external("x", "proc"), sp_script(&spr, "x")
RE_START = re.compile(r"\b(spawn|external|sp_script|load_script)\s*\(([^)]*)\)", re.I)
RE_VISION_SET = re.compile(r"&vision\s*=\s*(\d+)|force_vision\s*\(\s*(\d+)\s*\)", re.I)

# procedures the engine itself calls on a sprite's script (dink.cpp `locate(script, "...")`)
ENTRY_PROCS = {
    "main": "screen_load",     # runs when the sprite is created: screen load, spawn, sp_script
    "touch": "player_touch", "push": "player_push", "talk": "player_talk",
    "hit": "on_hit", "attack": "on_hit", "damage": "on_hit", "die": "on_death", "duckdie": "on_death",
    "pickup": "item", "use": "item", "drop": "item", "holdingdrop": "item", "arm": "item", "disarm": "item",
    "click": "ui", "buttonon": "ui", "buttonoff": "ui", "raise": "item",
}
# entry procedures whose warps fire without the player walking into or talking to anything
NON_PLAYER_TRIGGERS = ("screen_load", "on_hit", "on_death")


def strip_comments(text):
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


class Scripts:
    def __init__(self, story_dir):
        self.dir = story_dir
        self.text = {}
        for f in sorted(glob.glob(os.path.join(story_dir, "*.c"))):
            name = os.path.splitext(os.path.basename(f))[0].lower()
            with open(f, encoding="latin-1") as fh:
                self.text[name] = strip_comments(fh.read())

    @staticmethod
    def prefix(name):
        m = RE_PREFIX.match(name or "")
        return m.group(1) if m else None

    def procedures(self, name):
        """[(first line, proc name lower-case)] in file order (1-based lines)."""
        out = []
        for i, line in enumerate(self.text.get(name, "").splitlines()):
            m = RE_PROC.match(line)
            if m:
                out.append((i + 1, m.group(1).lower()))
        return out

    def proc_at(self, name, line):
        """(proc, first line, last line) of the procedure that runs `line` (the engine runs a
        procedure from its `void` line to the next `void` line), or (None, 0, 0)."""
        procs = self.procedures(name)
        n_lines = len(self.text.get(name, "").splitlines())
        for k, (first, p) in enumerate(procs):
            last = procs[k + 1][0] - 1 if k + 1 < len(procs) else n_lines
            if first <= line <= last:
                return p, first, last
        return None, 0, 0

    def entry_procs(self, name, proc):
        """Engine entry procedures through which `proc` of script `name` can run: the proc itself
        when the engine calls it, else every entry procedure that reaches it through local calls
        (`enter();` inside `talk`). A proc nothing calls is reported as itself."""
        procs = self.procedures(name)
        names = {p for _, p in procs}
        text = self.text.get(name, "").splitlines()
        callers = {p: set() for p in names}
        for k, (first, p) in enumerate(procs):
            last = procs[k + 1][0] - 1 if k + 1 < len(procs) else len(text)
            body = "\n".join(text[first:last])        # the lines after the `void` line
            for q in names:
                if q != p and re.search(r"\b%s\s*\(" % re.escape(q), body, re.I):
                    callers[q].add(p)
        found, seen, todo = set(), set(), [proc]
        while todo:
            cur = todo.pop()
            if cur in seen:
                continue
            seen.add(cur)
            if cur in ENTRY_PROCS:
                found.add(cur)
            todo.extend(callers.get(cur, ()))
        return sorted(found) or [proc]

    def walk_off_screen_at(self, name, line):
        """True when `dink_can_walk_off_screen(1)` ran earlier in the procedure holding `line`
        and was not reset to 0 before it (the engine then skips did_player_cross_screen)."""
        proc, first, _ = self.proc_at(name, line)
        if proc is None:
            return False
        state = False
        for ln in self.text[name].splitlines()[first - 1:line - 1]:
            m = RE_WALKOFF.search(ln)
            if m:
                state = m.group(1) == "1"
        return state

    def moves_after(self, name, line, window=40):
        """First `move(1, dir, until, nohard)` / `move_stop(...)` of the player after `line`
        in the same procedure: what a script does to Dink once it has placed him."""
        proc, _, last = self.proc_at(name, line)
        if proc is None:
            return None
        lines = self.text[name].splitlines()
        for i in range(line, min(last, line + window)):
            m = RE_MOVE1.search(lines[i])
            if m:
                return {"line": i + 1, "call": m.group(1), "dir": int(m.group(2)), "until": int(m.group(3)),
                        "nohard": bool(int(m.group(4)))}
        return None

    def started_scripts(self, name):
        """[(call, script)] for scripts this one starts by name (spawn / external / sp_script)."""
        out = []
        for fn, args in RE_START.findall(self.text.get(name, "")):
            q = RE_STR.findall(args)
            if q and q[0].lower() in self.text:
                out.append((fn.lower(), q[0].lower()))
        return out

    def vision_values(self, name):
        """Sorted values this script gives `&vision` (assignment or force_vision)."""
        return sorted({int(a or b) for a, b in RE_VISION_SET.findall(self.text.get(name, ""))})

    def running_with(self, roots):
        """{script: how} for `roots` (scripts on a screen) and everything they start, transitively.
        `how` is 'screen' for a root or 'spawn:<parent>' / 'external:<parent>' / 'sp_script:<parent>'."""
        seen, todo = {}, [(r, "screen") for r in roots]
        while todo:
            s, how = todo.pop(0)
            if s in seen:
                continue
            seen[s] = how
            for fn, t in self.started_scripts(s):
                todo.append((t, "%s:%s" % (fn, s)))
        return seen

    def warps(self):
        """Script-driven screen changes: list of dicts."""
        out = []
        for name, t in self.text.items():
            lines = t.splitlines()
            for i, line in enumerate(lines):
                m = RE_MAP.search(line)
                if not m:
                    continue
                window = "\n".join(lines[i:i + 6])
                x = RE_SPX.search(window)
                y = RE_SPY.search(window)
                proc, _, _ = self.proc_at(name, i + 1)
                entries = self.entry_procs(name, proc) if proc else []
                triggers = sorted({ENTRY_PROCS.get(e, "called") for e in entries})
                out.append({
                    "script": name, "line": i + 1, "target": int(m.group(1)),
                    "x": int(x.group(1)) if x else None, "y": int(y.group(1)) if y else None,
                    "proc": proc, "entry_procs": entries, "triggers": triggers,
                    "walk_off_screen": self.walk_off_screen_at(name, i + 1),
                    "then_moves": self.moves_after(name, i + 1),
                })
        return out

    def screenlock_scripts(self):
        return sorted(n for n, t in self.text.items() if RE_LOCK.search(t))

    def sign_text(self, name):
        t = self.text.get(name)
        if t is None:
            return None
        for s in RE_STR.findall(t):
            if s.startswith("`%"):
                return s[2:].strip()
        return None

    def mentions(self, name):
        """Scripts that name `name` in a string literal (spawn, sp_script, ...)."""
        out = []
        needle = '"%s"' % name
        for other, t in self.text.items():
            if other != name and needle in t.lower():
                out.append(other)
        return sorted(out)


def placed_scripts(ir):
    """script name -> sorted list of screens where it is attached on the map."""
    where = {}
    for n in ir.used:
        for sc in ir.scripts_on(n):
            where.setdefault(sc, set()).add(n)
    return {k: sorted(v) for k, v in where.items()}


def script_screens(ir, scripts, name, placed=None, depth=2):
    """Screens where a script runs: placed directly, else via scripts that name it.
    Returns (screens, how) with how = 'placed' | 'via:<script>' | None."""
    placed = placed if placed is not None else placed_scripts(ir)
    if name in placed:
        return placed[name], "placed"
    if depth == 0:
        return [], None
    found = set()
    via = []
    for other in scripts.mentions(name):
        scr, how = script_screens(ir, scripts, other, placed, depth - 1)
        if scr:
            found.update(scr)
            via.append(other)
    if found:
        return sorted(found), "via:" + ",".join(via)
    return [], None


RE_REMOVE = re.compile(
    r"void\s+die\s*\(|draw_hard_map|draw_hard_sprite|sp_hard\s*\(\s*&current_sprite\s*,\s*1\s*\)"
    r"|sp_active\s*\(\s*&current_sprite\s*,\s*0\s*\)|sp_kill\s*\(\s*&current_sprite")


def removable_reason(scripts, p):
    """Why a placed sprite's hardbox can disappear in play, or None.

    - its script dies / redraws hardness / clears its own hardness / deactivates
      itself (barrels, boxes, bombable rocks, burnable trees, pushable rocks);
    - it has a moving or fighting brain set in the map (monsters, people).
    Thorns (`thorn.c`: touch damage, hitpoints 0) are permanent and not removable.
    """
    name = p.get("script") or ""
    if len(name) > 1:
        t = scripts.text.get(name)
        if t and RE_REMOVE.search(t):
            return "script:" + name
    if p.get("brain", 0) not in (0, 15) and p.get("type") == 1:
        return "brain:%d" % p["brain"]
    return None


def removable_map(ir, scripts):
    """screen -> {placement index: reason} for sprites whose hardbox can go away."""
    out = {}
    for n in ir.used:
        d = {}
        for p in ir.screens[n]["placements"]:
            if p["has_hardness"] and not p["is_warp"]:
                r = removable_reason(scripts, p)
                if r:
                    d[p["index"]] = r
        out[n] = d
    return out
