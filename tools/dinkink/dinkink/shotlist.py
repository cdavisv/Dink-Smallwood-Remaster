"""Plain-language shot lists for scripted scenes (out/shot_lists/<script>.md)."""

from .convert import walk_stmts, expr_text

DIRS = {1: "down-left", 2: "down", 3: "down-right", 4: "left", 6: "right", 7: "up-left",
        8: "up", 9: "up-right"}
SCENE_CMDS = {"move", "move_stop", "fade_down", "fade_up"}


def is_scene(proc):
    names = [s["name"] for s in walk_stmts(proc["body"]) if s["type"] == "call"]
    if SCENE_CMDS & set(names):
        return True
    freezes_dink = any(s["type"] == "call" and s["name"] == "freeze" and s["args"]
                       and s["args"][0].get("value") == 1 for s in walk_stmts(proc["body"]))
    return freezes_dink and names.count("say_stop") >= 4


class Shots:
    def __init__(self, ast, dialog, globals_):
        self.ast = ast
        self.dialog = dialog
        self.globals = globals_
        self.actors = {}
        self.lines = []

    def who(self, e):
        if e is None:
            return "?"
        if e["type"] == "int":
            return "Dink" if e["value"] == 1 else "sprite %d" % e["value"]
        if e["type"] == "var":
            n = e["name"].lower()
            if n == "&current_sprite":
                return "this sprite (%s)" % self.ast["script"]
            return self.actors.get(n, n.lstrip("&"))
        if e["type"] == "ident":
            return "sprite 0 (bare word %s)" % e["name"]
        return expr_text(e)

    @staticmethod
    def arg(c, k):
        a = c["args"][k] if k < len(c["args"]) else None
        return expr_text(a) if a else "?"

    def call(self, c):
        n = c["name"]
        a = c["args"]
        if n in ("say", "say_stop", "say_stop_npc", "say_xy", "say_stop_xy"):
            row = self.dialog.get(c["line"]) or {}
            text = row.get("text", expr_text(a[0]) if a else "")
            if n.endswith("_xy"):
                who = "Text at (%s, %s)" % (self.arg(c, 1), self.arg(c, 2))
            else:
                who = "**%s**" % self.who(a[1] if len(a) > 1 else None)
            note = "" if "stop" in n else " _(does not wait)_"
            return "%s: “%s”%s" % (who, text, note)
        if n == "wait":
            v = a[0].get("value") if a else None
            return "Wait %.2f s" % (v / 1000.0) if isinstance(v, int) else "Wait %s ms" % self.arg(c, 0)
        if n in ("move", "move_stop"):
            d = a[1].get("value") if len(a) > 1 else None
            axis = "y" if d in (2, 8) else "x"
            return "%s walks %s to %s=%s%s%s" % (
                self.who(a[0]), DIRS.get(d, "dir %s" % self.arg(c, 1)), axis, self.arg(c, 2),
                " through obstacles" if self.arg(c, 3) == "1" else "",
                " (script waits)" if n == "move_stop" else " (script carries on)")
        if n == "freeze":
            return "Freeze %s" % self.who(a[0] if a else None)
        if n == "unfreeze":
            return "Unfreeze %s" % self.who(a[0] if a else None)
        if n == "playmidi":
            return "Music: %s" % self.arg(c, 0)
        if n == "stopmidi":
            return "Music stops"
        if n == "playsound":
            return "Sound %s" % self.arg(c, 0)
        if n == "fade_down":
            return "Fade to black"
        if n == "fade_up":
            return "Fade in"
        if n == "create_sprite":
            return "Spawn sprite at (%s, %s): seq %s frame %s, brain %s" % tuple(
                self.arg(c, k) for k in (0, 1, 3, 4, 2))
        if n == "sp_active" and self.arg(c, 1) == "0":
            return "%s is removed" % self.who(a[0])
        if n == "screenlock":
            return "Screen exits %s" % ("locked" if self.arg(c, 0) == "1" else "unlocked")
        if n == "load_screen":
            return "Load screen &player_map"
        if n == "draw_screen":
            return "Show the new screen"
        if n == "add_item":
            return "Dink gets item %s" % self.arg(c, 0)
        if n == "add_magic":
            return "Dink gets magic %s" % self.arg(c, 0)
        if n == "add_exp":
            return "Dink gains %s experience" % self.arg(c, 0)
        if n == "external":
            return "Run %s.%s" % (self.arg(c, 0), self.arg(c, 1))
        if n == "spawn":
            return "Start scene %s in parallel" % self.arg(c, 0)
        if n == "kill_this_task":
            return "Script ends"
        if n in ("debug", "preload_seq", "load_sound"):
            return None
        if n.startswith("sp_") and a:
            return "%s: %s = %s" % (self.who(a[0]), n[3:], self.arg(c, 1))
        if c.get("kind") == "local":
            return "Run procedure %s" % n
        return "%s(%s)" % (n, ", ".join(expr_text(x) for x in a))

    def stmts(self, stmts, depth):
        ind = "  " * depth
        for s in stmts or []:
            if s is None:
                continue
            t = s["type"]
            txt = None
            if t == "call":
                txt = self.call(s)
            elif t == "assign" or t == "int":
                target = (s.get("target") or s.get("name")).lower()
                val = s.get("value")
                if val and val["type"] == "call" and val["name"] == "create_sprite":
                    a = val["args"]
                    label = "%s (seq %s)" % (target.lstrip("&"), expr_text(a[3]) if len(a) > 3 else "?")
                    self.actors[target] = label
                    txt = "Spawn **%s** at (%s, %s), brain %s" % (
                        label, expr_text(a[0]), expr_text(a[1]), expr_text(a[2]))
                elif target in self.globals:
                    txt = "Fact %s %s %s" % (target.lstrip("&"), s.get("op", "="),
                                             expr_text(val) if val else "0")
            elif t == "if":
                self.lines.append("%s- If `%s`:" % (ind, s.get("cond_text")))
                self.stmts([s["then"]], depth + 1)
                if s.get("else"):
                    self.lines.append("%s- Otherwise:" % ind)
                    self.stmts([s["else"]], depth + 1)
                continue
            elif t == "block":
                self.stmts(s["body"], depth)
                continue
            elif t == "choice":
                self.lines.append("%s- Menu:" % ind)
                for o in s["options"]:
                    cond = " (only if %s)" % " and ".join(c["text"] for c in o["conditions"]) \
                        if o["conditions"] else ""
                    self.lines.append("%s  %d. %s%s" % (ind, o["index"], o["text"], cond))
                continue
            elif t == "goto":
                txt = "Go back to `%s`" % s["label"]
            elif t == "label":
                txt = "(label `%s`)" % s["name"]
            elif t == "return":
                txt = "End of procedure"
            if txt:
                self.lines.append("%s- %s _(line %d)_" % (ind, txt, s["line"]))


def shot_list(ast, procs, dialog, kind, screens, globals_):
    out = ["# Shot list: %s" % ast["script"], "",
           "Kind: %s. Screens: %s. Generated from `bin/dink/story/%s.c`; coordinates are "
           "original screen pixels." % (kind, screens or "none", ast["script"]), ""]
    for p in procs:
        sh = Shots(ast, dialog, globals_)
        sh.stmts(p["body"], 0)
        out.append("## %s()" % p["name"])
        out.append("")
        out += sh.lines or ["- (nothing staged)"]
        out.append("")
    return "\n".join(out)
