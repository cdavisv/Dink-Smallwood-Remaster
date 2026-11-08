"""DinkC AST (tools/dinkc, schema dinkc-ast/1) -> one Ink file per script.

See DESIGN.md for the mapping. The emitter works per script; `Project` holds what is
shared (globals, externals used, tables collected for the output CSVs).
"""

import re

from . import names as N
from . import text as T
from .overrides import BRACE_TYPOS
from .vocab import NOOP, SAY_CALLS, SAY_BLOCKS, BLOCKING

PSEUDO = {"&current_sprite": "current_sprite", "&current_script": "current_script",
          "&return": "v_return", "&savegameinfo": "savegameinfo_text",
          "&buttoninfo": "buttoninfo_text"}
for _i in range(1, 10):
    PSEUDO["&arg%d" % _i] = "arg%d" % _i

INK_OPS = {"&&": "and", "||": "or"}
INDENT = "    "


class Project:
    """Shared state across scripts."""

    def __init__(self, globals_, builtins, engine_globals):
        self.globals = globals_                  # {&name: initial}
        self.builtins = builtins                 # {name: signature or None}
        self.engine_globals = set(engine_globals)
        self.externals = {}                      # name -> arity
        self.names = []                          # rows for names.csv
        self.line_ids = []
        self.commands = []
        self.reviews = []                        # dicts, numbered later
        self.global_names = {g: N.global_ident(g) for g in globals_}
        self.missing_comma = {}                  # script -> lines whose call lost a `,`


class Review:
    def __init__(self, project, script, line, procedure, code, priority, category,
                 engine, intent, conversion, fix=""):
        project.reviews.append({
            "script": script, "line": line, "procedure": procedure, "code": code,
            "priority": priority, "category": category, "engine_behaviour": engine,
            "author_intent": intent, "conversion": conversion, "fix_const": fix})


ZERO = {"type": "int", "value": 0}


def engine_args(name, sig, args, comma_missing_after=None):
    """The argument list the engine's `get_parms` (dink.cpp 4116-4231) hands to a command.

    `sig` is the builtin signature (one letter per parameter, `s` string, `n` number) or
    None for a command that takes no argument list. `get_parms` zeroes its number list on
    entry and stops as soon as it needs a `,` that is not there: after a call with too few
    arguments, or after a string parameter that is not followed by a comma
    (`comma_missing_after` = the index of that string), the remaining numbers stay 0 and the
    command runs anyway. Too many arguments leave text where `)` is expected and the engine
    does not run the command at all. `external` has its own variable arity.
    """
    out = list(args)
    if sig is None or name == "external":
        return out
    if comma_missing_after is not None:
        out = out[:comma_missing_after + 1]
    if len(out) > len(sig):
        raise ValueError("%s() has %d arguments, the engine takes %d and would not run it "
                         "(unmodelled)" % (name, len(out), len(sig)))
    for k in range(len(out), len(sig)):
        if sig[k] == "s":
            raise ValueError("%s(): missing string argument %d (unmodelled)" % (name, k + 1))
        out.append(dict(ZERO))
    return out


def walk_stmts(stmts):
    for s in stmts or []:
        if s is None:
            continue
        for lead in s.get("leading") or []:
            yield lead
        yield s
        t = s["type"]
        if t == "block":
            yield from walk_stmts(s["body"])
        elif t == "if":
            yield from walk_stmts([s["then"]])
            yield from walk_stmts([s.get("else")])
        elif t == "else_stray":
            yield from walk_stmts([s["body"]])
        elif t == "hoisted":                 # emitter-made (overrides.BRACE_TYPOS)
            yield from walk_stmts(s["stmts"])


def stmt_exprs(s):
    t = s["type"]
    if t == "call":
        return [s]
    if t in ("assign", "int", "return"):
        return [s["value"]] if s.get("value") else []
    if t == "if":
        return [s["cond"]]
    if t == "choice":
        return [c["expr"] for o in s["options"] for c in o["conditions"]]
    return []


def walk_expr(e):
    if not e:
        return
    yield e
    t = e["type"]
    if t == "binop":
        yield from walk_expr(e["left"])
        yield from walk_expr(e["right"])
    elif t == "unary":
        yield from walk_expr(e["operand"])
    elif t == "call":
        for a in e["args"]:
            yield from walk_expr(a)


def expr_text(e):
    """DinkC-ish text of an expression (for comments and reviews)."""
    t = e["type"]
    if t == "int":
        return str(e["value"])
    if t == "var":
        return e["name"]
    if t == "string":
        return '"%s"' % e["value"]
    if t == "call":
        return "%s(%s)" % (e["name"], ", ".join(expr_text(a) for a in e["args"]))
    if t == "binop":
        return "%s %s %s" % (expr_text(e["left"]), e["op"], expr_text(e["right"]))
    if t == "unary":
        return e["op"] + expr_text(e["operand"])
    if t == "ident":
        return e["name"]
    return e.get("text", "?")


def comment_safe(s):
    return str(s).replace("\n", " ").replace("\r", " ")


class ScriptEmitter:
    def __init__(self, project, ast, kind, status, screens, dialog, menus_meta,
                 undeclared, convert_procs):
        self.p = project
        self.ast = ast
        self.script = ast["script"]
        self.knot = N.knot_ident(self.script)
        self.kind = kind
        self.status = status
        self.screens = screens
        self.dialog = dialog                     # {line: csv row}
        self.menus_meta = menus_meta             # {(proc, line): ordinal}
        self.undeclared = undeclared             # set of &names (lower)
        self.convert_procs = convert_procs       # ordered list of proc dicts
        self.locals = {l["name"].lower() for l in ast["locals"]} | set(undeclared)
        self.procs = {}
        for p in ast["procedures"]:
            self.procs.setdefault(p["name"], p)   # the engine uses the first
        self.stitches = []
        self.fixes = []                          # (const, comment)
        self.fix_count = {}
        self.cur_proc = None
        self.mode = "engine"                     # undeclared-variable rendering
        self.gated = 0                           # >0 while emitting a disabled intent
        self.undeclared_fix = {}
        self.rendered_calls = set()
        self.spoken = []                         # (line, gated)
        self.menus_out = []
        self.options_out = 0
        self.var_writes = []
        self.var_reads = []
        self.commands_out = 0
        self.why_never = {}                      # id(call node) -> why the engine skips it
        self.typo_used = set()                   # BRACE_TYPOS entries applied
        self._label_names()
        self._mark_missing_comma()

    # ---------------------------------------------------------------- names
    def _label_names(self):
        self.label_stitch = {}                   # label line -> stitch name
        self.goto_targets = set()
        used = set()
        for p in self.ast["procedures"]:
            for s in walk_stmts(p["body"]):
                if s["type"] == "goto" and s.get("target"):
                    self.goto_targets.add(s["target"]["line"])
        for p in self.ast["procedures"]:
            for s in walk_stmts(p["body"]):
                if s["type"] == "label" and s["line"] in self.goto_targets:
                    name = N.label_ident(s["name"])
                    if name in used:
                        name += "_l%d" % s["line"]
                    used.add(name)
                    self.label_stitch[s["line"]] = name
        missing = self.goto_targets - set(self.label_stitch)
        if missing:
            raise ValueError("%s: goto targets that are not labels: %s" % (self.script, missing))

    def _mark_missing_comma(self):
        """Calls whose argument list the engine's get_parms cuts short at a missing `,`
        after a string (dink.cpp 4206-4225): the rest of the arguments read 0."""
        for line in sorted(self.p.missing_comma.get(self.script, ())):
            nodes = [x for p in self.ast["procedures"] for x in walk_stmts(p["body"])
                     if x["type"] == "call" and x["line"] == line]
            if not nodes:
                raise ValueError("%s:%d missing comma, but no call on that line" % (
                    self.script, line))
            for x in nodes:
                args = x["args"]
                at = [i for i, a in enumerate(args[:-1]) if a["type"] == "string"]
                if not at:
                    raise ValueError("%s:%d missing comma: no string argument is followed by "
                                     "another argument" % (self.script, line))
                eargs = engine_args(x["name"], self.p.builtins.get(x["name"]), args, at[0])
                if x["name"] in ("say", "say_stop") and eargs[1] == ZERO:
                    # speaker 0: `say`/`say_stop` log "Sprite 0 can talk?" and return
                    # (dink.cpp 7750, 7908); nothing is spoken and nothing blocks
                    self.why_never[id(x)] = "missing_comma"
                else:
                    raise ValueError("%s:%d missing comma in %s(): effect on the engine's "
                                     "arguments is not modelled" % (self.script, line,
                                                                    x["name"]))

    def var(self, name, write=False):
        lo = name.lower()
        if lo in PSEUDO:
            return PSEUDO[lo]
        if lo in self.undeclared:
            if self.mode == "engine":
                return None
            return N.local_ident(self.script, lo)
        if lo in self.locals:
            return N.local_ident(self.script, lo)
        if lo in self.p.global_names:
            return self.p.global_names[lo]
        raise ValueError("%s: unknown variable %s" % (self.script, name))

    def known_text_vars(self):
        out = {}
        for g, ink in self.p.global_names.items():
            out[g] = ink
        for l in self.locals:
            if l not in self.undeclared:
                out[l] = N.local_ident(self.script, l)
        for k, v in PSEUDO.items():
            out[k] = v
        return out

    def new_fix(self, line, comment):
        k = self.fix_count.get(line, 0)
        self.fix_count[line] = k + 1
        const = N.fix_ident(self.script, line, "" if k == 0 else chr(ord("a") + k))
        self.fixes.append((const, comment))
        return const

    def review(self, line, code, priority, category, engine, intent, conversion, fix=""):
        Review(self.p, self.script, line, self.cur_proc or "", code, priority, category,
               engine, intent, conversion, fix)

    # ---------------------------------------------------------------- expressions
    def expr(self, e):
        t = e["type"]
        if t == "int":
            return str(e["value"])
        if t == "var":
            v = self.var(e["name"])
            if v is None:
                return "0"
            self.var_reads.append(v)
            return v
        if t == "string":
            return T.ink_string_literal(e["value"])
        if t == "ident":
            return "0"
        if t == "binop":
            op = INK_OPS.get(e["op"], e["op"])
            return "(%s %s %s)" % (self.expr(e["left"]), op, self.expr(e["right"]))
        if t == "unary":
            if e["op"] == "!":
                return "(not %s)" % self.expr(e["operand"])
            return "(%s%s)" % (e["op"], self.expr(e["operand"]))
        if t == "call":
            return self.call_expr(e)
        raise ValueError("%s: cannot convert expression %r" % (self.script, e))

    def call_expr(self, c):
        self.rendered_calls.add(id(c))
        name = c["name"]
        args = c["args"]
        if name == "random":
            # random(range, base) is the engine's (rand() % range) + base, and base when range
            # is 0 (dink.cpp "random"). An EXTERNAL, so the runtime answers from its own
            # seedable rand() source in call order; _decls.ink has an Ink fallback.
            a = [self.expr(x) for x in args]
            if len(a) != 2:
                raise ValueError("%s: random with %d args" % (self.script, len(a)))
            self.p.externals["random"] = 2
            return "random(%s, %s)" % (a[0], a[1])
        if c.get("kind") == "local":
            raise ValueError("%s: local procedure used as a value" % self.script)
        sig = self.p.builtins.get(name)
        arity = len(sig) if sig else len(args)
        a = [self.expr(x) for x in args]
        if len(a) != arity:
            self.review(c.get("line", 0), "external_arity", "medium", "engine-differs",
                        "%s() called with %d arguments, signature has %d" % (name, len(a), arity),
                        "", "padded/truncated to the signature")
            a = (a + ["0"] * arity)[:arity]
        prev = self.p.externals.get(name)
        if prev is not None and prev != arity:
            raise ValueError("external %s used with arity %d and %d" % (name, prev, arity))
        self.p.externals[name] = arity
        return "%s(%s)" % (name, ", ".join(a))

    def cond_expr(self, e):
        """Top-level condition without the outer parentheses."""
        r = self.expr(e)
        if r.startswith("(") and r.endswith(")") and e["type"] == "binop":
            return r[1:-1]
        return r

    def engine_cond(self, s):
        """Ink condition the engine actually evaluates, plus the written one if it differs."""
        cond = s["cond"]
        eng = s.get("engine") or {}
        written = self.cond_expr(cond)
        if eng.get("always_false"):
            return "false", written
        if eng.get("mode") == "call_compare" and cond["type"] == "binop" \
                and cond["left"]["type"] == "call":
            op = cond["op"]
            if op in ("!=", "<=", ">="):
                e = dict(cond, op="==")
            elif op in ("<", ">"):
                e = dict(cond, right={"type": "int", "value": 0})
            else:
                e = cond
            # the engine record must agree with ours
            want = eng.get("effective", "").replace(" ", "")
            got = expr_text(e).replace(" ", "")
            if want and want != got:
                raise ValueError("%s:%d engine condition %r vs %r" % (
                    self.script, s["line"], want, got))
            # call nodes are shared, so rendering twice is fine
            engine = self.cond_expr(e)
            return engine, (written if engine != written else None)
        if eng.get("mode") not in (None, "simple", "call_compare", "call_bare"):
            self.review(s["line"], "engine_if_mode", "high", "engine-differs",
                        "if mode %s" % eng.get("mode"), s.get("cond_text", ""),
                        "converted as written")
        return written, None

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def has_code(lines):
        return any(not l.strip().startswith("//") for l in lines)

    def emit_if(self, cond, then_lines, else_lines, depth):
        ind = INDENT * depth
        out = []
        tc, ec = self.has_code(then_lines), self.has_code(else_lines)
        # comments in a branch with no code would leave an empty branch, which Ink
        # rejects: move them in front of the conditional
        if not tc and then_lines:
            out += [ind + "// (then-branch of `%s`:) " % cond + l.strip().lstrip("/ ")
                    for l in then_lines]
            then_lines = []
        if not ec and else_lines:
            out += [ind + "// (else-branch of `%s`:) " % cond + l.strip().lstrip("/ ")
                    for l in else_lines]
            else_lines = []
        if then_lines and else_lines:
            out.append(ind + "{ %s:" % cond)
            out += then_lines
            out.append(ind + "- else:")
            out += else_lines
            out.append(ind + "}")
        elif then_lines:
            out.append(ind + "{ %s:" % cond)
            out += then_lines
            out.append(ind + "}")
        elif else_lines:
            out.append(ind + "{ not (%s):" % cond)
            out += else_lines
            out.append(ind + "}")
        else:
            if "(" in cond and any(ch.isalpha() for ch in cond.split("(")[0]):
                out.append(ind + "~ temp _evaluated_l%d = %s" % (len(self.stitches), cond))
            else:
                out.append(ind + "// (empty if: %s)" % cond)
        return out

    def gate(self, const, intent, engine, depth):
        """{ fix: intent - else: engine }"""
        return self.emit_if(const, intent, engine, depth)

    def contains_target(self, s):
        for x in walk_stmts([s]):
            if x["type"] == "label" and x["line"] in self.goto_targets:
                return True
        return False

    def add_stitch(self, name, lines):
        self.stitches.append((name, lines))

    @staticmethod
    def ends_with_divert(lines, depth):
        for l in reversed(lines):
            st = l.strip()
            if not st or st.startswith("//"):
                continue
            code = st.split("//")[0].strip()
            if l[:len(l) - len(l.lstrip())] != INDENT * depth:
                return False
            if code == "->->" or code == "-> DONE":
                return True
            return code.startswith("->") and not code.endswith("->")
        return False

    @staticmethod
    def terminator(cont, depth):
        return INDENT * depth + ("->->" if cont is None else "-> " + cont)

    # ---------------------------------------------------------------- statements
    def split_brace_typos(self, stmts):
        """Curated `{`-for-`}` typos (overrides.BRACE_TYPOS): the typo block ends the
        enclosing `if` body early and its statements follow as gated siblings."""
        out = []
        for s in stmts:
            hoist = []
            if s["type"] == "if" and s["then"]["type"] == "block" and s["then"]["body"]:
                last = s["then"]["body"][-1]
                key = (self.script, last["line"])
                if last["type"] == "block" and key in BRACE_TYPOS:
                    self.typo_used.add(key)
                    const = self.new_fix(last["line"], "`{` at line %d was meant to be `}`"
                                         % last["line"])
                    o = BRACE_TYPOS[key]
                    self.review(last["line"], "brace_typo", "high", "never-spoken",
                                o["engine"], o["intent"],
                                "engine live (the nested tests cannot run); they are hoisted "
                                "behind " + const, const)
                    s = dict(s, then=dict(s["then"], body=s["then"]["body"][:-1]))
                    out.append(s)
                    hoisted = [h for h in last["body"] if h is not None]
                    out.append({"type": "hoisted", "line": last["line"], "const": const,
                                "stmts": hoisted})
                    continue
            out.append(s)
        return out

    def emit_list(self, stmts, depth, cont):
        out = []
        stmts = self.split_brace_typos([s for s in stmts if s is not None])
        for idx, s in enumerate(stmts):
            if s["type"] == "label" and s["line"] in self.label_stitch:
                name = self.label_stitch[s["line"]]
                out += self.leading(s, depth)
                out.append(INDENT * depth + "-> %s // label %s: (line %d)" % (
                    name, comment_safe(s["name"]), s["line"]))
                body = self.emit_list(stmts[idx + 1:], 0, cont)
                if not self.ends_with_divert(body, 0):
                    body.append(self.terminator(cont, 0))
                self.add_stitch(name, ["// label `%s:` at line %d" % (
                    comment_safe(s["name"]), s["line"])] + body)
                return out
            if s["type"] in ("if", "block", "else_stray") and self.contains_target(s):
                cname = "c%d" % s["line"]
                rest = self.emit_list(stmts[idx + 1:], 0, cont)
                if not self.ends_with_divert(rest, 0):
                    rest.append(self.terminator(cont, 0))
                self.add_stitch(cname, ["// continuation after the statement at line %d" %
                                        s["line"]] + rest)
                out += self.emit_stmt(s, depth, cname)
                if not self.ends_with_divert(out, depth):
                    out.append(INDENT * depth + "-> " + cname)
                return out
            out += self.emit_stmt(s, depth, cont)
        return out

    def leading(self, s, depth):
        out = []
        for lead in s.get("leading") or []:
            if lead["type"] == "comment":
                out.append(INDENT * depth + "//" + comment_safe(lead["text"]))
            else:
                out.append(INDENT * depth + "// (%s at line %d)" % (lead["type"], lead["line"]))
        return out

    def uses_undeclared(self, s):
        if not self.undeclared:
            return False
        if s["type"] in ("assign", "int"):
            nm = s.get("target") or s.get("name")
            if nm and nm.lower() in self.undeclared:
                return True
        for e in stmt_exprs(s):
            for x in walk_expr(e):
                if x["type"] == "var" and x["name"].lower() in self.undeclared:
                    return True
        return False

    def undeclared_const(self, s):
        """One switch per undeclared variable (first use line)."""
        names = sorted({x["name"].lower() for e in stmt_exprs(s) for x in walk_expr(e)
                        if x["type"] == "var" and x["name"].lower() in self.undeclared}
                       | ({s["target"].lower()} if s.get("target", "") and
                          s["target"].lower() in self.undeclared else set()))
        key = names[0]
        if key not in self.undeclared_fix:
            const = self.new_fix(s["line"], "undeclared variable %s" % key)
            self.undeclared_fix[key] = const
            self.review(s["line"], "undeclared_variable", "medium", "engine-differs",
                        "%s is never declared: the engine reads 0 and loses writes" % key,
                        "a variable that keeps its value",
                        "engine live; every use has the intent behind " + const, const)
        return self.undeclared_fix[key]

    def emit_stmt(self, s, depth, cont):
        out = self.leading(s, depth)
        if s.get("engine_executes") is False or id(s) in self.why_never:
            return out + self.emit_not_executed(s, depth, cont)
        if s["type"] not in ("if", "block") and self.uses_undeclared(s):
            const = self.undeclared_const(s)
            self.mode = "intent"
            self.gated += 1
            intent = self.emit_inner(s, depth + 1, cont)
            self.gated -= 1
            self.mode = "engine"
            engine = self.emit_inner(s, depth + 1, cont)
            return out + self.gate(const, intent, engine, depth)
        return out + self.emit_inner(s, depth, cont)

    def emit_not_executed(self, s, depth, cont):
        ind = INDENT * depth
        if s["type"] == "unknown":
            guess = s.get("guess")
            txt = s["text"]
            show = txt if (len(txt) <= 12 or "(" in txt or ";" in txt) else None
            if guess == "return":
                const = self.new_fix(s["line"], "unrecognised `%s`" % comment_safe(txt))
                self.review(s["line"], "unknown_statement", "high", "engine-differs",
                            "`%s` is not a statement; the engine ignores it and carries on" % txt,
                            "return", "engine live; `->->` behind " + const, const)
                return self.gate(const, [INDENT * (depth + 1) + "->->"], [], depth)
            self.review(s["line"], "unknown_statement", "low", "not-code",
                        "ignored", "", "comment only")
            if show is None:
                return [ind + "// [line %d: not DinkC and never executed; text not copied, "
                              "see the original file]" % s["line"]]
            return [ind + "// [line %d: unrecognised statement, never executed: %s]" % (
                s["line"], comment_safe(show))]
        why = self.why_never.get(id(s))
        spoken = s["type"] == "call" and s["name"] in SAY_CALLS
        const = self.new_fix(s["line"], "statement the engine never runs" if why is None
                             else "missing comma: statement the engine never runs")
        self.gated += 1
        intent = self.emit_inner(s, depth + 1, cont)
        self.gated -= 1
        if why == "missing_comma":
            self.review(s["line"], "missing_comma", "high", "never-spoken",
                        "get_parms (dink.cpp 4206-4225) demands a `,` after a string "
                        "parameter and otherwise returns early with the remaining "
                        "parameters 0: the speaker is sprite 0, which %s rejects "
                        "(7750, 7908), so the line is never spoken and nothing blocks"
                        % s["name"],
                        "speak the line (a comma was meant)",
                        "engine live (nothing); the written line behind " + const, const)
        else:
            self.review(s["line"], "engine_never_runs", "high",
                        "never-spoken" if spoken else "engine-differs",
                        "the engine does not run this statement (source error)",
                        "run it", "engine live (nothing); intent behind " + const, const)
        return self.gate(const, intent, [], depth)

    def emit_inner(self, s, depth, cont):
        ind = INDENT * depth
        t = s["type"]
        if t == "comment":
            return [ind + "//" + comment_safe(s["text"])]
        if t == "label":
            if "(" in s["name"]:
                return self.malformed_label(s, depth)
            return [ind + "// label `%s:` (no goto targets it)" % comment_safe(s["name"])]
        if t == "block":
            return self.emit_list(s["body"], depth, cont)
        if t == "hoisted":
            # statements the engine nests where the author closed a block (BRACE_TYPOS)
            self.gated += 1
            lines = self.emit_list(s["stmts"], depth + 1, cont)
            self.gated -= 1
            return self.gate(s["const"], lines, [], depth)
        if t == "if":
            return self.emit_if_stmt(s, depth, cont)
        if t == "else_stray":
            self.review(s["line"], "stray_else", "medium", "engine-differs",
                        "else without if", "", "body converted unconditionally")
            return [ind + "// stray else at line %d" % s["line"]] + \
                self.emit_list([s["body"]], depth, cont)
        if t == "call":
            return self.emit_call(s, depth)
        if t == "assign":
            return self.emit_assign(s, depth)
        if t in ("int", "assign") and s.get("value") and s["value"]["type"] == "call" \
                and s["value"]["name"] in SAY_CALLS and s.get("op", "=") == "=":
            # `int &text = say_xy(...)`: the line is spoken, the director stores the
            # text sprite's handle in the variable
            target = self.var(s.get("name") or s["target"], write=True)
            self.rendered_calls.add(id(s["value"]))
            self.var_writes.append(target)
            fake = dict(s["value"], line=s["line"])
            if self.say_variants(fake):
                raise ValueError("%s:%d: a switched spoken line stored in a handle variable "
                                 "is not modelled" % (self.script, s["line"]))
            return [ind + self.say_line(fake, self.gated > 0) + " #handle:%s" % target]
        if t == "int":
            target = self.var(s["name"], write=True)
            val = self.expr(s["value"]) if s.get("value") else "0"
            if target is None:
                return [ind + "// (engine: int %s on an undeclared name)" % s["name"]]
            self.var_writes.append(target)
            return [ind + "~ %s = %s" % (target, val)]
        if t == "return":
            out = []
            if s.get("value"):
                out.append(ind + "~ v_return = %s" % self.expr(s["value"]))
            return out + [ind + "->->"]
        if t == "goto":
            return self.emit_goto(s, depth)
        if t == "choice":
            return self.emit_choice(s, depth)
        if t == "unknown":
            return [ind + "// unrecognised: " + comment_safe(s["text"])]
        raise ValueError("%s:%d unhandled statement %s" % (self.script, s["line"], t))

    def malformed_label(self, s, depth):
        name, _, rest = s["name"].partition("(")
        args = [a.strip() for a in rest.split(",") if a.strip()]
        intent_txt = ">> %s %s #cmd #src:%d" % (name, " ".join(args), s["line"])
        const = self.new_fix(s["line"], "`%s:` read as a label" % s["name"])
        self.review(s["line"], "malformed_as_label", "medium", "engine-differs",
                    "`%s:` ends in ':' so the engine treats it as a label (no-op)" % s["name"],
                    "%s(%s)" % (name, ", ".join(args)), "engine live; intent behind " + const,
                    const)
        self.p.commands.append(self.cmd_row(s["line"], name, "fix-intent", " ".join(args)))
        return self.gate(const, [INDENT * (depth + 1) + intent_txt], [], depth)

    def emit_if_stmt(self, s, depth, cont):
        cond, written = self.engine_cond(s)
        never = bool((s.get("engine") or {}).get("always_false"))
        self.gated += never
        then_lines = self.emit_list([s["then"]], depth + 1, cont)
        self.gated -= never
        else_lines = []
        if s.get("else"):
            if s.get("else_engine_never_runs"):
                self.gated += 1
                body = self.emit_list([s["else"]], depth + 2, cont)
                self.gated -= 1
                const = self.new_fix(s.get("else_line") or s["line"], "else after a comment")
                self.review(s.get("else_line") or s["line"], "engine_else_after_comment",
                            "high", "engine-differs",
                            "a comment between the if body and else makes the engine skip the else",
                            "run the else body when the condition is false",
                            "engine live; intent behind " + const, const)
                else_lines = self.gate(const, body, [], depth + 1)
            else:
                else_lines = self.emit_list([s["else"]], depth + 1, cont)
        if self.uses_undeclared(s):
            const = self.undeclared_const(s)
            self.mode = "intent"
            intent_cond, _ = self.engine_cond(s)
            self.mode = "engine"
            cond = "(%s and (%s)) or (not %s and (%s))" % (const, intent_cond, const, cond)
        if written is not None:
            const = self.new_fix(s["line"], "written condition: %s" % s.get("cond_text"))
            self.review(s["line"], "engine_condition_differs", "low", "engine-differs",
                        "engine evaluates `%s`" % (s.get("engine") or {}).get("effective"),
                        "`%s`" % s.get("cond_text"), "engine live; written condition behind " +
                        const, const)
            cond = "(%s and (%s)) or (not %s and (%s))" % (const, written, const, cond)
        return self.emit_if(cond, then_lines, else_lines, depth)

    def emit_assign(self, s, depth):
        ind = INDENT * depth
        target = self.var(s["target"], write=True)
        val_node = s.get("engine_value") or s["value"]
        if s.get("engine_value"):
            self.review(s["line"], "engine_rhs_first_word", "high", "engine-differs",
                        "engine assigns %s" % expr_text(s["engine_value"]),
                        expr_text(s["value"]), "engine value used")
        if target is None:
            # undeclared target in engine mode: the write is lost
            for x in walk_expr(val_node):
                if x["type"] == "call":
                    self.expr(val_node)
                    break
            return [ind + "// (engine: write to undeclared %s is lost)" % s["target"]]
        val = self.expr(val_node)
        op = s["op"]
        if op == "*":
            op = "*="
        if op == "/":
            op = "/="
        if op == "=":
            rhs = val
        else:
            rhs = "%s %s %s" % (target, op[0], val)
        self.var_writes.append(target)
        lo = s["target"].lower()
        if lo in self.p.engine_globals and lo != "&result" and lo not in self.locals:
            self.p.commands.append(self.cmd_row(s["line"], "=" + target, "var-write",
                                                "%s %s" % (op, val)))
        return [ind + "~ %s = %s" % (target, rhs)]

    def emit_goto(self, s, depth):
        ind = INDENT * depth
        tgt = s.get("target")
        if not tgt:
            # No switch: there is no target to put behind one, so the engine's outcome (the
            # procedure ends; a caller would resume, proc_return) is also the only reading.
            self.review(s["line"], "goto_missing_label", "high", "engine-matches-intent",
                        "no line starts with `%s:`; the engine runs off the end and the "
                        "procedure stops" % s["label"],
                        "probably jump back to `%s` (no such label exists)" % s["label"],
                        "engine live (`->->`, the procedure ends); no target, so no switch")
            return [ind + "// goto %s: label missing (the engine ends the procedure)"
                    % comment_safe(s["label"]),
                    ind + "->->"]
        name = self.label_stitch[tgt["line"]]
        return [ind + "-> %s.%s // goto %s" % (self.knot, name, comment_safe(s["label"]))]

    # ---------------------------------------------------------------- calls
    def cmd_row(self, line, command, form, args, blocking=None):
        return {"script": self.script, "procedure": self.cur_proc or "", "line": line,
                "command": command, "form": form,
                "blocking": int(command in BLOCKING if blocking is None else blocking),
                "args": args, "kind": self.kind, "status": self.status,
                "screens": self.screens}

    def cmd_arg(self, a):
        t = a["type"]
        if t == "int":
            return str(a["value"])
        if t == "string":
            return '"' + T.encode_plain(a["value"]).replace('"', '\\"') + '"' \
                if a["value"] else '""'
        if t == "ident":
            return "0"
        v = self.expr(a)
        if v.lstrip("-").isdigit():
            return v
        return "{%s}" % v

    def emit_call(self, s, depth):
        ind = INDENT * depth
        gated = self.gated > 0
        name = s["name"]
        self.rendered_calls.add(id(s))
        if name in SAY_CALLS:
            return self.emit_say(s, depth, gated)
        kind = s.get("kind")
        if kind == "local":
            if name in self.procs:
                return [ind + "-> %s.p_%s -> // %s()" % (self.knot, name, name)]
            self.review(s["line"], "missing_local_procedure", "medium", "engine-differs",
                        "no procedure %s in this script; the engine logs and skips" % name,
                        "", "comment")
            return [ind + "// call to missing procedure %s()" % name]
        if kind == "unknown" or (kind != "builtin" and name not in self.p.builtins):
            guess = s.get("guess") or ""
            const = self.new_fix(s["line"], "unknown command %s()" % name)
            if guess in self.p.builtins:
                # a misspelt engine command: the intent branch runs the corrected one, the
                # written spelling stays in a comment and out of the command tables
                args = " ".join(self.cmd_arg(a) for a in engine_args(
                    guess, self.p.builtins[guess], s["args"]))
                self.review(s["line"], "unknown_call", "medium", "engine-differs",
                            "%s() is not an engine command; the engine logs and skips it" % name,
                            guess, "engine live (nothing); corrected call `%s` behind %s"
                            % (guess, const), const)
                self.p.commands.append(self.cmd_row(s["line"], guess, "fix-intent", args))
                line = ">> %s%s #cmd #src:%d" % (guess, (" " + args) if args else "", s["line"])
                note = "// written as %s(%s): not an engine command, corrected to %s" % (
                    name, comment_safe(", ".join(expr_text(a) for a in s["args"])), guess)
                return self.gate(const, [INDENT * (depth + 1) + note,
                                         INDENT * (depth + 1) + line], [], depth)
            args = " ".join(self.cmd_arg(a) for a in s["args"])
            self.review(s["line"], "unknown_call", "medium", "engine-differs",
                        "%s() is not an engine command; the engine logs and skips it" % name,
                        "unclear", "engine live (nothing); written call behind " +
                        const, const)
            self.p.commands.append(self.cmd_row(s["line"], name, "fix-intent", args, False))
            line = ">> %s%s #cmd #src:%d" % (name, (" " + args) if args else "", s["line"])
            return self.gate(const, [INDENT * (depth + 1) + line], [], depth)
        if name in NOOP:
            for a in s["args"]:
                for x in walk_expr(a):
                    if x["type"] == "call":
                        self.rendered_calls.add(id(x))
            self.p.commands.append(self.cmd_row(s["line"], name, "comment",
                                                ", ".join(expr_text(a) for a in s["args"]),
                                                False))
            return [ind + "// %s(%s) [engine no-op here: %s]" % (
                name, comment_safe(", ".join(expr_text(a) for a in s["args"])), NOOP[name])]
        if name == "random":
            for x in walk_expr(s):
                self.rendered_calls.add(id(x))
            self.p.commands.append(self.cmd_row(s["line"], name, "comment", "", False))
            return [ind + "// random() as a statement has no effect"]
        args = [self.cmd_arg(a) for a in engine_args(name, self.p.builtins.get(name), s["args"])]
        self.commands_out += 1
        argtxt = " ".join(args)
        self.p.commands.append(self.cmd_row(s["line"], name, "fix-intent" if gated else "line",
                                            argtxt))
        out = [ind + ">> %s%s #cmd #src:%d" % (name, (" " + argtxt) if args else "", s["line"])]
        if name == "kill_this_task":
            out.append(ind + "-> DONE")
        return out

    def say_variants(self, s):
        """(speaker, text) of the intent line when the engine's differs: a bare-word
        speaker reads 0 (intent: the variable), a stray backtick in the text (intent:
        without it). None when the line needs no switch."""
        row = self.dialog.get(s["line"])
        name = s["name"]
        args = s["args"]
        ident = name not in ("say_xy", "say_stop_xy") and len(args) > 1 \
            and args[1]["type"] == "ident"
        backtick = row is not None and "`" in row["text"]
        if not (ident or backtick):
            return None
        spk = self.var("&" + args[1]["name"]) if ident else None
        return {"spk": spk, "text": row["text"].replace("`", "") if backtick else None,
                "ident": ident, "backtick": backtick}

    def emit_say(self, s, depth, gated):
        """A spoken line. Where the author's line differs from what the engine does with
        it (wrong speaker, stray backtick) the whole line is switched, since a tag cannot
        be: `{ fix_<script>_l<line>: <intent line> - else: <engine line> }`, same #id."""
        ind = INDENT * depth
        v = self.say_variants(s)
        if v is None:
            return [ind + self.say_line(s, gated)]
        key = "%s:%d" % (self.script, s["line"])
        what = []
        if v["ident"]:
            what.append("wrong speaker: bare word %s" % s["args"][1]["name"])
        if v["backtick"]:
            what.append("stray backtick in the text")
        const = self.new_fix(s["line"], ", ".join(what))
        if v["ident"]:
            a = s["args"][1]["name"]
            self.review(s["line"], "say_sprite_zero", "high", "wrong-speaker",
                        "speaker is the bare word `%s`, which reads 0: the text goes to "
                        "sprite 0" % a, "speaker &%s" % a,
                        "engine live (#spk:0); the intended speaker behind " + const, const)
        if v["backtick"]:
            self.review(s["line"], "midtext_backtick", "low", "text",
                        "backtick inside the text after the colour code (the engine reads "
                        "colour codes only at the start of the text; the font renderer is "
                        "not in this repository)",
                        "a stray keystroke: the text without the backtick",
                        "engine live (verbatim); the text without the backtick behind "
                        + const, const)
        intent = self.say_line(s, gated, spk=v["spk"], text=v["text"], review=key)
        engine = self.say_line(s, gated, record=False, review=key)
        return self.gate(const, [ind + INDENT + intent], [ind + INDENT + engine], depth)

    def say_line(self, s, gated, spk=None, text=None, record=True, review=None):
        """One output line. `spk`/`text` override the speaker variable and the text (the
        intent variant of a switched line); `record=False` for the second variant of a
        line that is already counted."""
        row = self.dialog.get(s["line"])
        if row is None or row["procedure"] != self.cur_proc:
            raise ValueError("%s:%d say without dialog_lines row" % (self.script, s["line"]))
        name = s["name"]
        segs = T.find_vars(text if text is not None else row["text"],
                           {v.lower(): self.known_text_vars()[v.lower()]
                            for v in row["vars"].split(";") if v})
        out_text = T.encode(segs)
        tags = ["id:" + row["_id"], "say:" + name]
        if name in ("say_xy", "say_stop_xy"):
            for k, a in (("x", s["args"][1]), ("y", s["args"][2])):
                if a["type"] == "int":
                    tags.append("%s:%d" % (k, a["value"]))
                elif a["type"] == "var":
                    tags.append("%s:%s" % (k, self.var(a["name"])))
                else:
                    raise ValueError("%s:%d say_xy coordinate %r" % (self.script, s["line"], a))
        else:
            a = s["args"][1] if len(s["args"]) > 1 else {"type": "int", "value": 0}
            if spk is not None:
                pass                            # the intended speaker (bare word -> variable)
            elif a["type"] == "int":
                spk = str(a["value"])
            elif a["type"] == "var":
                spk = self.var(a["name"]) or "0"
            elif a["type"] == "ident":
                spk = "0"                       # a bare word reads 0 in the engine
            else:
                raise ValueError("%s:%d speaker %r" % (self.script, s["line"], a))
            tags.append("spk:" + spk)
        tags.append("col:%s" % row["colour"])
        tags.append("src:%d" % s["line"])
        if review:
            tags.append("review:" + review)
        if record:
            self.spoken.append((s["line"], gated))
            self.p.line_ids.append({"id": row["_id"], "kind": "spoken", "script": self.script,
                                    "procedure": self.cur_proc, "line": s["line"],
                                    "call": name, "speaker": row["speaker"],
                                    "colour": row["colour"], "live": int(not gated),
                                    "text": row["text"]})
        return out_text + " " + " ".join("#" + t for t in tags)

    # ---------------------------------------------------------------- menus
    def emit_choice(self, s, depth):
        ind = INDENT * depth
        ordinal = self.menus_meta[(self.cur_proc, s["line"])]
        stitch = "m%d" % s["line"]
        base = "%s.%s" % (self.script, self.cur_proc)
        lines = ["// menu from line %d (choice_start ... choice_end)" % s["line"]]
        lines.append(">> choice_start %s %s #cmd #src:%d" % (
            s.get("set_y") or 0, s.get("title_color") or 0, s["line"]))
        self.p.commands.append(self.cmd_row(s["line"], "choice_start", "line",
                                            "%s %s" % (s.get("set_y") or 0,
                                                       s.get("title_color") or 0)))
        known = self.known_text_vars()
        for k, tl in enumerate(s.get("title_lines") or [], 1):
            tid = "%s.t%d.%d" % (base, ordinal, k)
            segs = T.find_vars(tl, known)
            tags = "#title #id:%s" % tid
            if not tl.strip(" "):
                # an empty title line still takes a row on screen; ink drops empty
                # lines, so it is written as one U+00A0 and tagged
                segs = [("t", T.NBSP * max(1, len(tl)))]
                tags += " #blank"
            if s.get("title_color"):
                tags += " #col:%s" % s["title_color"]
            tags += " #src:%d" % (s.get("title_line") or s["line"])
            lines.append(T.encode(segs) + " " + tags)
            self.p.line_ids.append({"id": tid, "kind": "title", "script": self.script,
                                    "procedure": self.cur_proc, "line": s.get("title_line")
                                    or s["line"], "call": "title", "speaker": "",
                                    "colour": s.get("title_color") or "", "live": 1,
                                    "text": tl})
        all_conditional = bool(s["options"]) and all(o["conditions"] for o in s["options"])
        for o in s["options"]:
            conds = []
            for c in o["conditions"]:
                conds.append("{%s}" % self.cond_expr(c["expr"]))
            special = {"&savegameinfo": "savegameinfo(%d)" % o["index"],
                       "&buttoninfo": "buttoninfo(%d)" % o["index"]}
            kv = dict(known)
            kv.update(special)
            for fn in ("savegameinfo", "buttoninfo"):
                if "&" + fn in o["text"].lower():
                    self.p.externals[fn] = 1
            segs = T.find_vars(o["text"], kv)
            oid = "%s.c%d.%d" % (base, ordinal, o["index"])
            lines.append("+ %s[%s #opt:%s]" % ("".join(c + " " for c in conds),
                                              T.encode(segs), oid))
            lines.append(INDENT + "~ result = %d" % o["index"])
            lines.append(INDENT + "->->")
            self.options_out += 1
            self.p.line_ids.append({"id": oid, "kind": "option", "script": self.script,
                                    "procedure": self.cur_proc, "line": o["line"],
                                    "call": "choice", "speaker": "", "colour": "",
                                    "live": 1, "text": o["text"]})
        if all_conditional:
            lines.append("+ -> // fallback when no option is visible (engine behaviour unverified)")
            lines.append(INDENT + "~ result = 0")
            lines.append(INDENT + "->->")
            self.review(s["line"], "menu_all_conditional", "low", "unverified",
                        "every option has a condition; with none visible the engine's "
                        "behaviour is unverified", "", "Ink fallback sets result = 0")
        if s.get("aborted") or not s.get("closed", True):
            self.review(s["line"], "choice_aborted", "high", "engine-differs",
                        "menu aborted or unclosed", "", "options before the problem kept")
        self.add_stitch(stitch, lines)
        self.menus_out.append(s["line"])
        return [ind + "-> %s -> // menu, sets result" % stitch]

    # ---------------------------------------------------------------- script
    def emit(self):
        for p in self.convert_procs:
            self.cur_proc = p["name"]
            slot = len(self.stitches)
            self.add_stitch("p_" + p["name"], None)
            body = self.emit_list(p["body"], 0, None)
            if not self.ends_with_divert(body, 0):
                body.append("->->")
            self.stitches[slot] = ("p_" + p["name"], ["// %s (lines %d-%d)" % (
                comment_safe(p["header"]), p["line"], p["end_line"])] + body)
        self.cur_proc = None
        return self.render()

    def render(self):
        out = []
        out.append("// %s.ink - generated by tools/dinkink from bin/dink/story/%s.c" % (
            self.script, self.script))
        out.append("// kind: %s; status: %s; screens: %s" % (
            self.kind, self.status, self.screens or "none"))
        out.append("// Draft for human review against the original. Spoken text is verbatim;")
        out.append("// U+00A0 marks spaces the Ink runtime would otherwise collapse (DESIGN.md 3).")
        if self.status == "converted-dead":
            out.append("// DEAD SCRIPT: not placed in map.dat and not called by any script.")
        out.append("")
        locs = sorted(self.locals)
        for l in locs:
            tag = " // undeclared in the original (see review)" if l in self.undeclared else ""
            out.append("VAR %s = 0%s" % (N.local_ident(self.script, l), tag))
        for const, comment in self.fixes:
            out.append("CONST %s = false // review: %s" % (const, comment_safe(comment)))
        if locs or self.fixes:
            out.append("")
        out.append("=== %s ===" % self.knot)
        for p in self.convert_procs:
            out.append("= %s" % N.entry_ident(p["name"]))
            out.append("-> p_%s -> DONE" % p["name"])
        # reading order: each procedure body, then its label/continuation stitches by
        # line, then its menus by line
        procs = [n for n, _ in self.stitches if n.startswith("p_")]
        owner, cur = {}, None
        for n, _ in self.stitches:
            if n.startswith("p_"):
                cur = n
            owner[n] = cur

        def key(item):
            n = item[0]
            rank = 0 if n.startswith("p_") else (2 if re.match(r"m\d+$", n) else 1)
            m = re.search(r"line (\d+)", item[1][0] if item[1] else "")
            return (procs.index(owner[n]), rank, int(m.group(1)) if m and rank else 0)
        for name, lines in sorted(self.stitches, key=key):
            out.append("")
            out.append("= %s" % name)
            out += lines
        return "\n".join(out) + "\n"
