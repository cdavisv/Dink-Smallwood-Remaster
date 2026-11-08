"""Tolerant, engine-faithful DinkC parser.

The HD engine never builds a syntax tree. It reads one physical line at a time
(read_next_line, D:3484), strips leading spaces and hands the text to process_line
(D:7070), which peels off at most a few prefixes (`{`, `}`, `else`, `if (...)`) and then
runs ONE statement; whatever follows that statement on the same line is discarded.
Procedures are found by scanning for a line whose first word is `void` (locate,
D:3717) and run until the next `void` line, a `return`, or the end of the file;
braces only matter when the interpreter is skipping the body of a false `if`.

This parser follows the same rules so that malformed scripts are read the way the
game reads them, and records a diagnostic wherever the source is malformed or the
engine would do something other than what the text appears to say. See README.md
for the grammar, recovery rules and node schema.
"""

import difflib
import re

from . import expr as X
from .builtins import BUILTINS, KEYWORDS, CHOICE_ONLY, SAY_CALLS

ASSIGN_OPS = {"=": "=", "+=": "+=", "-=": "-=", "*=": "*=", "/=": "/=", "*": "*=", "/": "/="}
VAR_FIGURE_OPS = ("==", ">", "<", "!=", "<=", ">=")
KNOWN_WORDS = sorted(set(BUILTINS) | KEYWORDS | CHOICE_ONLY)


# --------------------------------------------------------------------------------------
# Ports of the engine's string helpers (so quirks come out identical)
# --------------------------------------------------------------------------------------

def get_word(line, word):
    """Port of get_word (D:4850): words split on runs of spaces, a leading space
    makes word 1 empty."""
    cur = 0
    space_mode = False
    save = ""
    for ch in line:
        if space_mode and ch != " ":
            space_mode = False
            save = ""
        if not space_mode:
            if ch == " ":
                cur += 1
                if word == cur:
                    return save
                space_mode = True
                save = ""
            else:
                save += ch
    if not space_mode and cur + 1 != word:
        save = ""
    return save


def separate_string(s, num, ch):
    """Port of separate_string (misc_util.cpp:269), 1-based field `num`."""
    parts = s.split(ch)
    if num - 1 < len(parts):
        return parts[num - 1].replace("\n", "")
    return ""


def engine_words(s):
    """ev[1..14] as process_line computes them (split on single spaces)."""
    parts = s.split(" ")
    return parts[:14]


# --------------------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------------------

class Diagnostics:
    def __init__(self, script):
        self.script = script
        self.items = []

    def add(self, line, code, what, recovery, severity="warning", **extra):
        d = {"script": self.script, "file": self.script + ".c", "line": line,
             "code": code, "severity": severity, "what": what, "recovery": recovery}
        d.update(extra)
        self.items.append(d)
        return d


# --------------------------------------------------------------------------------------
# Call / argument splitting
# --------------------------------------------------------------------------------------

def split_call(s):
    """Split `name(args...) rest` into (name, [arg texts], rest, problems).

    Strings are honoured (commas and parens inside "..." do not count). A string that
    opens with a single quote and closes with a double quote is recovered as a string.
    """
    problems = []
    lp = s.index("(")
    name = s[:lp].strip()
    i = lp + 1
    depth = 0
    args = []
    cur = ""
    in_str = None
    closed = False
    while i < len(s):
        ch = s[i]
        if in_str:
            cur += ch
            if ch == '"':
                in_str = None
            i += 1
            continue
        if ch == '"':
            in_str = '"'
            cur += ch
        elif depth == 0 and ch not in " ,)" and cur.strip().startswith('"') and \
                len(cur.strip()) >= 2 and cur.strip().endswith('"') and not in_str:
            problems.append("missing comma after string argument")
            args.append(cur)
            cur = ch
        elif ch == "'" and cur.strip() == "" and '"' in s[i + 1:]:
            # 'text"  -> mismatched quote; treat as a string up to the next "
            problems.append("mismatched quote: string opened with ' and closed with \"")
            in_str = '"'
            cur += '"'
        elif ch == "(":
            depth += 1
            cur += ch
        elif ch == ")":
            if depth == 0:
                closed = True
                i += 1
                break
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            args.append(cur)
            cur = ""
        else:
            cur += ch
        i += 1
    if in_str:
        problems.append("unterminated string")
    if not closed and cur.rstrip().endswith(";"):
        cur = cur.rstrip()[:-1]
    if cur.strip() or args:
        args.append(cur)
    if not closed:
        problems.append("missing )")
    rest = s[i:] if closed else ""
    return name, args, rest, problems, closed


def parse_arg(text):
    t = text.strip()
    node, probs, rest = X.parse_expr(t)
    if rest.strip():
        probs = probs + ["unexpected text %r in argument" % rest.strip()]
    return node, probs


# --------------------------------------------------------------------------------------
# `if` condition: our parse plus an emulation of process_line's '(' branch (D:7140-7270)
# --------------------------------------------------------------------------------------

def balanced_condition(h):
    """h starts with '('. Return (inner, rest, closed)."""
    depth = 0
    in_str = False
    for i, ch in enumerate(h):
        if in_str:
            if ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return h[1:i], h[i + 1:], True
    return h[1:], "", False


def _var_figure_shape(text):
    """What var_figure (D:4905) does with `text`: returns (kind, a, op, b)."""
    w2 = get_word(text, 2)
    if w2 == "":
        return ("one_word", text.strip(), None, None)
    a = get_word(text, 1)
    b = get_word(text, 3).replace(")", "")
    return ("binary", a, w2, b)


def engine_if(h):
    """Emulate how the engine evaluates `if <h>` and what it does with the rest of
    the line. Returns a dict:
      mode: simple | call_compare | call_bare | misparse | no_paren
      effective: the comparison the engine really performs, as text
      rest: text the engine goes on to execute on the same line ('' if discarded)
      rest_dropped: bool
      always_false: bool (var_figure can never be true)
    """
    if not h.startswith("("):
        return {"mode": "no_paren", "effective": None, "rest": "", "rest_dropped": True,
                "always_false": False}
    fields = h.split(")")
    ev1 = fields[0]
    temp = fields[1] if len(fields) > 1 else ""
    p = h[len(ev1) + 1:].lstrip(" ")
    if "=" in temp or ">" in temp or "<" in temp:
        op = "==" if "=" in temp else (">" if ">" in temp else "<")
        inner = h[1:].lstrip(" ")
        m = re.match(r"([A-Za-z_][A-Za-z0-9_\-]*)\s*\(", inner)
        line = "N %s %s" % (op, temp.replace("==", ""))
        rhs = _atol_text(get_word(line, 3).replace(")", ""))
        if m:
            call_end = inner.index("(")
            name, args, after, _p, _c = split_call(inner)
            call_text = "%s(%s)" % (name, ",".join(a.strip() for a in args))
            eff = "%s %s %s" % (call_text, op, rhs if rhs else "0")
            mode = "call_compare"
        else:
            eff = "<returnint of %r> %s %s" % (inner.split(")")[0], op, rhs if rhs else "0")
            mode = "misparse"
        return {"mode": mode, "effective": eff, "rest": "", "rest_dropped": True,
                "always_false": False}
    if p.startswith(")"):
        return {"mode": "call_bare", "effective": None, "rest": p[1:], "rest_dropped": False,
                "always_false": False}
    inner = separate_string(h[1:], 1, ")")
    rest = h[1 + len(inner) + 1:]
    kind, a, op, b = _var_figure_shape(inner)
    always_false = False
    if kind == "one_word":
        eff = "%s != 0" % a
    else:
        if op not in VAR_FIGURE_OPS:
            always_false = True
            eff = "false (word 2 %r is not an operator)" % op
        else:
            eff = "%s %s %s" % (_atol_text(a), op, _atol_text(b))
    return {"mode": "simple", "effective": eff, "rest": rest, "rest_dropped": False,
            "always_false": always_false, "inner": inner}


def _norm_operand(text):
    t = text.replace(" ", "")
    return t if t.startswith("&") else _atol_text(t)


def _cond_intent(node):
    """Intended comparison as (left_text, op, right_text) or None."""
    if node.get("type") == "binop" and node["op"] in X.COMPARISONS:
        return (X.to_text(node["left"]), node["op"], X.to_text(node["right"]))
    return None


# --------------------------------------------------------------------------------------
# Statements
# --------------------------------------------------------------------------------------

class ScriptParser:
    def __init__(self, script, text):
        self.script = script
        from .source import split_lines
        self.lines = split_lines(text)
        self.diag = Diagnostics(script)
        self.items = []

    # ---- statement text -> node -------------------------------------------------------

    def parse_statement(self, s, ln):
        """Parse one statement (the rest of a line). Returns a node."""
        words = engine_words(s)
        w1 = words[0]
        w2 = words[1] if len(words) > 1 else ""
        name = w1.split("(")[0] if "(" in w1 else w1
        lname = name.lower()

        if lname == "int":
            return self.parse_int(s, ln)
        if lname in ("return", "return;"):
            return self.parse_return(s, ln, name)
        if lname == "goto":
            label = w2
            exact = label.endswith(";")
            lab = label[:-1] if exact else label
            node = {"type": "goto", "line": ln, "label": lab, "exact_match": exact,
                    "target": None}
            after = " ".join(words[2:]).strip()
            if after and not after.startswith("//"):
                self.diag.add(ln, "trailing_text", "text after goto: %r" % after,
                              "ignored, as the engine does")
            return node
        if w2 in ASSIGN_OPS:
            return self.parse_assign(s, ln, w1, w2)
        if "(" in s and not s.startswith("("):
            return self.parse_call(s, ln)
        return self.parse_unknown(s, ln)

    def parse_int(self, s, ln):
        body = s[len(s.split(" ")[0]):]
        tmp = s.replace("=", " ")
        tmp = separate_string(tmp, 1, ";")
        vname = get_word(tmp, 2)
        node = {"type": "int", "line": ln, "name": vname, "value": None}
        if not vname.startswith("&"):
            self.diag.add(ln, "bad_int", "int declaration without &-name: %r" % s.strip(),
                          "engine refuses to create the variable; kept as an int node with "
                          "engine_executes=false", severity="error")
            node["engine_executes"] = False
        if "=" in body:
            rhs = body.split("=", 1)[1]
            node["value"] = self.rhs_expr(rhs, ln)
        else:
            after = body.strip()
            after = after[len(vname):].strip() if after.startswith(vname) else after
            if after not in ("", ";") and not after.startswith("//"):
                self.diag.add(ln, "trailing_text", "text after int declaration: %r" % after,
                              "ignored, as the engine does")
        return node

    def parse_return(self, s, ln, written):
        rest = s[len(written):].strip()
        node = {"type": "return", "line": ln, "value": None}
        if rest.startswith(";"):
            rest = rest[1:].strip()
        if rest and not rest.startswith("//"):
            node["value"] = self.rhs_expr(rest, ln)
        return node

    def rhs_expr(self, rhs, ln):
        """Parse an assignment right-hand side; note where the engine reads less."""
        text = rhs.strip()
        if text.endswith(";"):
            text = text[:-1].rstrip()
        node, probs, rest = X.parse_expr(text)
        for p in probs:
            self.diag.add(ln, "expr_problem", "%s in %r" % (p, text), "best-effort parse")
        if rest.strip() and not rest.strip().startswith("//"):
            r = rest.strip()
            if r.startswith(";"):
                r = r[1:].strip()
            if r and not r.startswith("//"):
                self.diag.add(ln, "trailing_text", "text after expression: %r" % rest.strip(),
                              "ignored, as the engine does")
        if node.get("type") == "binop":
            self.diag.add(ln, "engine_rhs_first_word",
                          "arithmetic in assignment %r: the engine only reads the first value "
                          "(var_equals uses ev[3] or a single call)" % text,
                          "AST keeps the full expression; engine_value holds what the engine "
                          "computes")
            first = node
            while first.get("type") == "binop":
                first = first["left"]
            node = dict(node)
            node["engine_value"] = first
        return node

    def parse_assign(self, s, ln, target, op):
        rhs = s[len(target):].lstrip(" ")[len(op):]
        node = {"type": "assign", "line": ln, "target": target, "op": ASSIGN_OPS[op],
                "op_written": op, "value": self.rhs_expr(rhs, ln)}
        if not target.startswith("&"):
            node["engine_executes"] = False
            self.diag.add(ln, "bad_assign_target", "assignment to %r (no &)" % target,
                          "engine logs 'Unknown var' and does nothing; engine_executes=false",
                          severity="error")
        if op == "/=" and "(" in rhs:
            self.diag.add(ln, "engine_div_assign", "`/=` with a call on the right",
                          "engine skips only one character of `/=` unless "
                          "set_use_latest_fixes_level(1) (D:11292); noted only")
        return node

    def parse_call(self, s, ln):
        name, arg_texts, rest, problems, closed = split_call(s)
        args = []
        arg_problems = []
        for a in arg_texts:
            node, probs = parse_arg(a)
            args.append(node)
            arg_problems.extend(probs)
        node = {"type": "call", "line": ln, "name": name.lower(), "name_written": name,
                "args": args}
        if " " in name.strip():
            # e.g. "foo bar(1)" - the engine's ev[1] is "foo"
            node["name"] = name.split(" ")[0].lower()
            self.diag.add(ln, "odd_call", "space inside call name %r" % name,
                          "treated as a call to %r" % node["name"])
        if not closed:
            sig = BUILTINS.get(node["name"])
            eff = ("get_parms fails without ')' so the engine does not run this command"
                   if sig else "the engine still attempts the call")
            self.diag.add(ln, "missing_paren", "missing ) in %r" % s.strip(),
                          "arguments recovered up to end of line; " + eff,
                          severity="error", engine_executes=not bool(sig))
            if sig:
                node["engine_executes"] = False
        for p in problems:
            if p == "missing )":
                continue
            if p == "missing comma after string argument":
                self.diag.add(ln, "missing_comma", "%s in %r" % (p, s.strip()),
                              "split into two arguments; the engine's get_parms does not "
                              "need the comma, so the line works in the game")
                continue
            self.diag.add(ln, "string_quote", "%s in %r" % (p, s.strip()),
                          "string recovered between the quotes; the engine reads text "
                          "between the first two \" characters, so this line probably "
                          "shows garbage or nothing", severity="error")
            node["engine_executes"] = False
        for p in arg_problems:
            self.diag.add(ln, "arg_problem", "%s in %r" % (p, s.strip()),
                          "kept the leading valid expression", severity="error")
        sig = BUILTINS.get(node["name"]) or ""
        for k, a in enumerate(args):
            if a.get("type") == "ident" and (k >= len(sig) or sig[k] == "n"):
                self.diag.add(ln, "bare_identifier_arg",
                              "argument %d of %s is the bare word %r (missing &?)"
                              % (k + 1, name, a["name"]),
                              "kept as an ident node; the engine's atol() reads it as 0",
                              severity="error")
                if node["name"] in ("say", "say_stop") and k == 1:
                    self.diag.add(ln, "say_sprite_zero",
                                  "%s to sprite 0: the engine refuses ('Sprite 0 can talk? "
                                  "Yeah, didn't think so.', D:7752/7910) so this line is "
                                  "never shown" % node["name"], "engine_executes=false",
                                  severity="error")
                    node["engine_executes"] = False
                elif node["name"] in SAY_CALLS and k == 1:
                    self.diag.add(ln, "say_sprite_zero",
                                  "%s to sprite 0: no sprite-0 check in this command, so the "
                                  "text is attached to unused sprite 0 and drawn at its "
                                  "position, not over the speaker" % node["name"],
                                  "line kept; speaker recorded as written",
                                  severity="error")
        r = rest.strip()
        if r.startswith(";"):
            r = r[1:].strip()
        if r and not r.startswith("//"):
            sig = BUILTINS.get(node["name"])
            how = "ignored, as the engine does"
            if r.startswith(":") or r.startswith("."):
                how = ("ignored; the engine accepts a call without ';' so the command "
                       "still runs")
            self.diag.add(ln, "trailing_text", "text after call: %r" % r, how)
        return node

    def parse_unknown(self, s, ln):
        text = s.strip()
        node = {"type": "unknown", "line": ln, "text": text, "engine_executes": False}
        m = re.match(r"^(&[A-Za-z0-9_\-]+)\s*(\+=|-=|\*=|/=|=)\s*(.*)$", text)
        if m:
            node["guess"] = {"type": "assign", "target": m.group(1), "op": m.group(2),
                             "value": X.parse_expr(m.group(3).rstrip(";"))[0]}
            self.diag.add(ln, "assign_no_spaces",
                          "assignment without spaces around the operator: %r" % text,
                          "the engine does not recognise it (ev[2] must be the operator) and "
                          "does nothing; kept as unknown with a guess", severity="error")
            return node
        word = re.match(r"[A-Za-z_&][A-Za-z0-9_\-]*", text)
        guess = None
        if word:
            close = difflib.get_close_matches(word.group(0).lower(), KNOWN_WORDS, n=1,
                                              cutoff=0.75)
            guess = close[0] if close else None
        if guess:
            node["guess"] = guess
        self.diag.add(ln, "unknown_statement", "unrecognised statement %r" % text,
                      "engine logs MERROR and skips it; kept as an 'unknown' node"
                      + (" (probable intent: %s)" % guess if guess else ""),
                      severity="error")
        return node

    # ---- line lexing ---------------------------------------------------------------------

    def lex_line(self, s, ln):
        """Split one physical line into items. Returns list of items."""
        items = []
        dropped = False
        while True:
            s = s.lstrip(" ")
            if not s:
                break
            if s.startswith("//"):
                items.append({"kind": "comment", "line": ln, "text": s[2:].strip()})
                break
            words = engine_words(s)
            w1 = words[0]
            w2 = words[1] if len(words) > 1 else ""
            if w1.lower() == "void":
                items.append(self.lex_void(s, ln))
                break
            if w1.endswith(":") and len(w2) < 2 and not w1.startswith("say"):
                items.append({"kind": "label", "line": ln, "name": w1[:-1]})
                if not re.match(r"^[A-Za-z_][A-Za-z0-9_\-]*$", w1[:-1]):
                    self.diag.add(ln, "malformed_as_label",
                                  "%r ends with ':' so the engine reads it as a label" % s.strip(),
                                  "kept as a label (a no-op), as in the engine"
                                  + ("; probably meant %s)" % w1[:-1] if "(" in w1 else ""),
                                  severity="error")
                after = " ".join(words[1:]).strip()
                if after and not after.startswith("//"):
                    self.diag.add(ln, "trailing_text", "text after label: %r" % after,
                                  "ignored, as the engine does")
                break
            if s[0] == "{":
                items.append({"kind": "open", "line": ln})
                s = s[1:]
                continue
            if s[0] == "}":
                items.append({"kind": "close", "line": ln})
                s = s[1:]
                continue
            name = w1.split("(")[0] if "(" in w1 else w1
            if name.lower() == "else":
                items.append({"kind": "else", "line": ln})
                s = s[len(name):]
                continue
            if name.lower() == "if":
                h = s[len(name):].lstrip(" ")
                item, rest = self.lex_if(h, ln)
                items.append(item)
                if item["engine"]["rest_dropped"] and rest.strip() and not \
                        rest.strip().startswith("//"):
                    dropped = True
                    sub = self.lex_line(rest, ln)
                    for it in sub:
                        it["engine_executes"] = False
                        if it["kind"] == "stmt":
                            it["node"]["engine_executes"] = False
                    items.extend(sub)
                    break
                s = rest
                continue
            if s[0] == "(":
                node = self.parse_unknown(s, ln)
                items.append({"kind": "stmt", "line": ln, "node": node})
                break
            node = self.parse_statement(s, ln)
            items.append({"kind": "stmt", "line": ln, "node": node})
            break
        return items

    def lex_void(self, s, ln):
        words = engine_words(s)
        w2 = words[1] if len(words) > 1 else ""
        pname = separate_string(w2, 1, "(").strip()
        item = {"kind": "void", "line": ln, "name": pname.lower(), "name_written": pname,
                "header": s.strip(), "brace_on_header": False}
        m = re.match(r"void\s+[^(]*(\([^)]*\))?\s*(.*)$", s.strip(), re.I)
        trailing = m.group(2).strip() if m else ""
        if trailing == "{":
            item["brace_on_header"] = True
        elif trailing and not trailing.startswith("//"):
            self.diag.add(ln, "header_trailing", "text after procedure header: %r" % trailing,
                          "ignored: the engine starts the procedure on the next line",
                          severity="error")
        if not pname:
            self.diag.add(ln, "bad_header", "procedure header without a name: %r" % s.strip(),
                          "kept as a procedure named ''", severity="error")
        return item

    def lex_if(self, h, ln):
        eng = engine_if(h)
        if not h.startswith("("):
            self.diag.add(ln, "if_no_paren", "if without '(': %r" % h,
                          "condition parsed from the rest of the line; the engine evaluates "
                          "it as a statement", severity="error")
            node, probs, rest = X.parse_expr(h)
            return {"kind": "if", "line": ln, "cond": node, "cond_text": h.strip(),
                    "engine": eng}, ""
        inner, rest, closed = balanced_condition(h)
        if not closed:
            self.diag.add(ln, "if_unclosed", "unclosed '(' in if condition: %r" % h,
                          "condition taken to end of line", severity="error")
        cond, probs, crest = X.parse_expr(inner)
        for p in probs:
            self.diag.add(ln, "expr_problem", "%s in condition %r" % (p, inner),
                          "best-effort parse")
        if crest.strip():
            self.diag.add(ln, "expr_problem", "unparsed text in condition: %r" % crest,
                          "ignored")
        item = {"kind": "if", "line": ln, "cond": cond, "cond_text": inner.strip(),
                "engine": eng}
        intent = _cond_intent(cond)
        mode = eng["mode"]
        if mode == "misparse":
            self.diag.add(ln, "engine_if_misparse",
                          "statement on the same line as `if (%s)` contains = < or > before "
                          "its first ')': the engine mistakes it for a function comparison"
                          % inner.strip(),
                          "AST keeps the intended condition and statement; the engine "
                          "evaluates %s and drops the statement (engine_executes=false)"
                          % eng["effective"], severity="error")
        elif mode == "call_compare":
            # effective: "<call> <op> <rhs>"
            if intent:
                eff_op = eng["effective"].rsplit(" ", 2)[1]
                eff_rhs = eng["effective"].rsplit(" ", 1)[1]
                if eff_op != intent[1] or eff_rhs != _norm_operand(intent[2]):
                    self.diag.add(ln, "engine_condition_differs",
                                  "function comparison `%s`: the engine evaluates `%s`"
                                  % (inner.strip(), eng["effective"]),
                                  "AST keeps the written condition; engine.effective records "
                                  "the real one (D:7171-7241 quirk)")
            if rest.strip() and not rest.strip().startswith("//"):
                self.diag.add(ln, "engine_if_rest_dropped",
                              "statement after a function comparison on the same line: %r"
                              % rest.strip(),
                              "the engine discards the rest of the line after evaluating the "
                              "call; kept with engine_executes=false", severity="error")
        elif mode == "simple":
            if eng["always_false"]:
                self.diag.add(ln, "engine_condition_differs",
                              "condition `%s` is always false in the engine: %s"
                              % (inner, eng["effective"]),
                              "AST keeps the written condition", severity="error")
            elif intent:
                kind, a, op, b = _var_figure_shape(eng["inner"])
                if kind == "one_word" or (_atol_text(a), op, _atol_text(b)) != (
                        _norm_operand(intent[0]), intent[1], _norm_operand(intent[2])):
                    self.diag.add(ln, "engine_condition_differs",
                                  "condition `%s`: the engine evaluates `%s`"
                                  % (inner.strip(), eng["effective"]),
                                  "AST keeps the written condition")
        return item, rest

    # ---- choice menus (talk_get, D:5072) ------------------------------------------------

    def read_choice(self, node, i):
        """Lines after a choice_start() statement at line index i-1. Returns new i."""
        node["type"] = "choice"
        node.pop("name", None)
        node.pop("name_written", None)
        node.pop("args", None)
        node.update({"set_y": None, "title_color": None, "title": None, "title_line": None,
                     "options": [], "end_line": None, "closed": False})
        retnum = 0
        n = len(self.lines)
        while i < n:
            ln = i + 1
            line = self.lines[i].lstrip(" ")
            i += 1
            first = get_word(line, 1)
            if first.lower() == "set_y":
                node["set_y"] = _atol(get_word(line, 2))
                continue
            if first.lower() == "set_title_color":
                node["title_color"] = _atol(get_word(line, 2))
                continue
            if line.strip() == "":
                continue
            check = separate_string(line, 1, "(").strip()
            if check.lower() == "title_start":
                title = []
                node["title_line"] = ln
                ended = False
                while i < n:
                    tl = self.lines[i]
                    i += 1
                    if separate_string(tl.lstrip(" "), 1, "(").strip().lower() == "title_end":
                        ended = True
                        break
                    title.append(tl.strip())
                node["title"] = "\n".join(t for t in title if t != "")
                node["title_lines"] = title
                if not ended:
                    self.diag.add(ln, "title_unclosed", "title_start without title_end",
                                  "title runs to end of file", severity="error")
                continue
            if check.lower() == "choice_end":
                node["end_line"] = ln
                node["closed"] = True
                if retnum == 0:
                    self.diag.add(ln, "choice_empty", "choice with no options",
                                  "engine logs an error and the menu is not shown",
                                  severity="error")
                return i
            # option, possibly with conditions
            conds = []
            work = line
            ok = True
            while True:
                pre = separate_string(work, 1, '"').strip()
                if len(pre) > 2:
                    if "(" not in pre:
                        self.diag.add(ln, "choice_bad_line",
                                      "line inside a choice that is not an option: %r"
                                      % line.strip(),
                                      "the engine aborts the menu here (talk_get returns "
                                      "false) and runs the remaining lines as statements; "
                                      "we stop the menu here too", severity="error")
                        node["end_line"] = ln
                        node["aborted"] = True
                        return i - 1
                    cinner = separate_string(separate_string(pre, 2, "("), 1, ")")
                    cnode, probs, crest = X.parse_expr(cinner)
                    conds.append({"text": cinner.strip(), "expr": cnode,
                                  "engine": _var_figure_desc(cinner)})
                    first_close = separate_string(work, 1, ")")
                    work = work[len(first_close) + 1:]
                    continue
                break
            text = separate_string(work, 2, '"')
            retnum += 1
            raw_quotes = work.count('"')
            if raw_quotes < 2:
                self.diag.add(ln, "choice_option_quote",
                              "choice option without a closing quote: %r" % line.strip(),
                              "option text taken to end of line, as the engine does")
            opt = {"index": retnum, "line": ln, "text": text,
                   "conditions": conds}
            if text.strip() == "":
                self.diag.add(ln, "choice_empty_option",
                              "choice line with no text: %r" % line.strip(),
                              "the engine shows an empty option; kept", severity="warning")
            node["options"].append(opt)
        self.diag.add(node["line"], "choice_unclosed", "choice_start without choice_end",
                      "menu runs to end of file (the engine would loop forever)",
                      severity="error")
        return i

    # ---- driver --------------------------------------------------------------------------

    def lex(self):
        i = 0
        n = len(self.lines)
        while i < n:
            ln = i + 1
            line_items = self.lex_line(self.lines[i], ln)
            i += 1
            for it in line_items:
                self.items.append(it)
            last = line_items[-1] if line_items else None
            if last and last["kind"] == "stmt" and last["node"].get("type") == "call" and \
                    last["node"]["name"] == "choice_start":
                i = self.read_choice(last["node"], i)
        return self.items

    def parse(self):
        self.lex()
        tb = TreeBuilder(self)
        return tb.build()


def _atol_text(word):
    """How decipher_string+atol read a word: a variable stays a variable, anything
    else becomes the number atol() makes of it."""
    if word.startswith("&"):
        return word
    return str(_atol(word))


def _atol(s):
    m = re.match(r"\s*([-+]?\d+)", s or "")
    return int(m.group(1)) if m else 0


def _var_figure_desc(text):
    kind, a, op, b = _var_figure_shape(text)
    if kind == "one_word":
        return "%s != 0" % a
    if op not in VAR_FIGURE_OPS:
        return "false"
    return "%s %s %s" % (a or "0", op, b or "0")


# --------------------------------------------------------------------------------------
# Tree building
# --------------------------------------------------------------------------------------

class TreeBuilder:
    def __init__(self, sp):
        self.sp = sp
        self.items = sp.items
        self.diag = sp.diag
        self.pos = 0

    def peek(self):
        return self.items[self.pos] if self.pos < len(self.items) else None

    def take(self):
        it = self.items[self.pos]
        self.pos += 1
        return it

    def build(self):
        preamble = []
        procedures = []
        # preamble: items before the first void
        while self.peek() is not None and self.peek()["kind"] != "void":
            it = self.take()
            if it["kind"] == "comment":
                preamble.append(self.comment(it))
            else:
                preamble.append(self.item_to_node(it))
                self.diag.add(it["line"], "code_outside_procedure",
                              "code before the first procedure",
                              "kept in 'preamble'; the engine never runs it")
        while self.peek() is not None:
            hdr = self.take()
            body, end_line, braced = self.proc_body(hdr)
            procedures.append({"name": hdr["name"], "name_written": hdr["name_written"],
                               "line": hdr["line"], "end_line": end_line,
                               "header": hdr["header"], "braced": braced, "body": body})
        return preamble, procedures

    def comment(self, it):
        return {"type": "comment", "line": it["line"], "text": it["text"]}

    def proc_body(self, hdr):
        """Statements from the header to the next void (or EOF)."""
        body = []
        end_line = hdr["line"]
        if hdr.get("brace_on_header"):
            # `void main(void) {` - treat as opening the body block
            self.items.insert(self.pos, {"kind": "open", "line": hdr["line"]})
        while self.peek() is not None and self.peek()["kind"] != "void":
            it = self.peek()
            end_line = it["line"]
            if it["kind"] == "close":
                self.take()
                self.diag.add(it["line"], "stray_close_brace",
                              "'}' with no open block in procedure %s" % hdr["name"],
                              "ignored (the engine clamps its brace level at 0)")
                continue
            node = self.statement(hdr["name"])
            if node is not None:
                body.append(node)
        if self.pos < len(self.items):
            end_line = self.items[self.pos]["line"] - 1
        else:
            end_line = len(self.sp.lines)
        # Flatten the usual "{ ... }" body.
        braced = False
        real = [n for n in body if n["type"] != "comment"]
        if real and real[0]["type"] == "block":
            braced = True
            first_block = real[0]
            after = real[1:]
            if after:
                self.diag.add(after[0]["line"], "code_after_procedure_block",
                              "statements after the closing brace of procedure %s"
                              % hdr["name"],
                              "kept in the procedure: the engine runs everything up to the "
                              "next void line", severity="info")
            idx = body.index(first_block)
            body = body[:idx] + first_block["body"] + body[idx + 1:]
        return body, end_line, braced

    def statement(self, proc):
        it = self.peek()
        if it is None or it["kind"] == "void":
            return None
        kind = it["kind"]
        if kind == "comment":
            self.take()
            return self.comment(it)
        if kind == "label":
            self.take()
            return {"type": "label", "line": it["line"], "name": it["name"]}
        if kind == "open":
            return self.block(proc)
        if kind == "close":
            return None
        if kind == "if":
            return self.if_stmt(proc)
        if kind == "else":
            self.take()
            self.diag.add(it["line"], "stray_else", "else without a matching if",
                          "kept as 'else_stray'; the engine only runs its body if the "
                          "statement just before it was skipped", severity="warning")
            body = self.body_stmt(proc, it)
            return {"type": "else_stray", "line": it["line"], "body": body}
        if kind == "stmt":
            self.take()
            return self.item_to_node(it)
        self.take()
        return None

    def item_to_node(self, it):
        if it["kind"] == "stmt":
            n = it["node"]
            if it.get("engine_executes") is False:
                n["engine_executes"] = False
            return n
        if it["kind"] == "comment":
            return self.comment(it)
        if it["kind"] == "label":
            return {"type": "label", "line": it["line"], "name": it["name"]}
        return {"type": "unknown", "line": it["line"], "text": it["kind"],
                "engine_executes": False}

    def block(self, proc):
        op = self.take()
        node = {"type": "block", "line": op["line"], "end_line": None, "body": [],
                "closed": False}
        while True:
            it = self.peek()
            if it is None or it["kind"] == "void":
                where = "end of file" if it is None else "procedure header at line %d" % it["line"]
                self.diag.add(op["line"], "unclosed_block",
                              "block opened here in procedure %s is never closed" % proc,
                              "closed at %s, which is where the engine stops skipping too"
                              % where, severity="error")
                node["end_line"] = (it["line"] - 1) if it else len(self.sp.lines)
                return node
            if it["kind"] == "close":
                self.take()
                node["end_line"] = it["line"]
                node["closed"] = True
                return node
            s = self.statement(proc)
            if s is not None:
                node["body"].append(s)

    def body_stmt(self, proc, owner):
        """The single statement/block that an if/else controls."""
        skipped = []
        while True:
            it = self.peek()
            if it is None or it["kind"] == "void":
                self.diag.add(owner["line"], "if_no_body",
                              "%s with no statement before the procedure ends" % owner["kind"],
                              "body is empty", severity="error")
                return None
            if it["kind"] in ("comment", "label"):
                skipped.append(self.statement(proc))
                continue
            if it["kind"] == "close":
                self.diag.add(owner["line"], "if_no_body",
                              "%s directly followed by '}'" % owner["kind"],
                              "body is empty; the engine applies the skip to the first "
                              "statement after the block", severity="error")
                return None
            break
        node = self.statement(proc)
        if skipped and node is not None:
            node = dict(node)
            node.setdefault("leading", []).extend(skipped)
        return node

    def if_stmt(self, proc):
        it = self.take()
        node = {"type": "if", "line": it["line"], "cond": it["cond"],
                "cond_text": it["cond_text"],
                "engine": {k: v for k, v in it["engine"].items() if k in
                           ("mode", "effective", "rest_dropped", "always_false")},
                "then": None, "else": None}
        if it.get("engine_executes") is False:
            node["engine_executes"] = False
        then = self.body_stmt(proc, it)
        node["then"] = then
        if then is not None and then.get("type") == "if" and then["line"] > it["line"] \
                and then.get("then") is not None and then["then"]["line"] > then["line"]:
            self.diag.add(then["line"], "nested_if_no_braces",
                          "if inside an unbraced if, with its own body on a later line",
                          "parsed as C would; NOTE the engine skips only the inner if line "
                          "when the outer condition is false, so the inner body still runs",
                          severity="error")
        if then is not None and then.get("type") == "choice":
            self.diag.add(then["line"], "choice_as_if_body",
                          "choice_start as the body of an unbraced if",
                          "if the condition is false the engine skips only the choice_start "
                          "line and runs the option lines as statements", severity="error")
        # else?
        comments = []
        save = self.pos
        while self.peek() is not None and self.peek()["kind"] == "comment":
            comments.append(self.take())
        nx = self.peek()
        if nx is not None and nx["kind"] == "else":
            el = self.take()
            if comments:
                self.diag.add(el["line"], "engine_else_after_comment",
                              "comment line between an if body and its else",
                              "parsed as an else; NOTE the engine resets its else flag on "
                              "the comment, so this else branch never runs",
                              severity="error")
                node["else_engine_never_runs"] = True
                node["comments_before_else"] = [self.comment(c) for c in comments]
            node["else_line"] = el["line"]
            node["else"] = self.body_stmt(proc, el)
        else:
            self.pos = save
        return node


# --------------------------------------------------------------------------------------
# Post-processing: goto resolution, call kinds, locals
# --------------------------------------------------------------------------------------

def walk(nodes, fn, proc=None, depth=0):
    """Call fn(node, proc) on every statement node, depth first, in source order."""
    for n in nodes:
        if n is None:
            continue
        fn(n, proc)
        for lead in n.get("leading", []) or []:
            fn(lead, proc)
        t = n.get("type")
        if t == "block":
            walk(n["body"], fn, proc, depth + 1)
        elif t == "if":
            walk([n["then"]], fn, proc, depth + 1)
            walk([n["else"]], fn, proc, depth + 1)
        elif t == "else_stray":
            walk([n["body"]], fn, proc, depth + 1)


def resolve(script, lines, procedures, diag, global_functions=()):
    proc_names = {}
    for p in procedures:
        if p["name"] in proc_names:
            diag.add(p["line"], "duplicate_procedure",
                     "procedure %s defined again (first at line %d)"
                     % (p["name"], proc_names[p["name"]]["line"]),
                     "the engine always finds the first one", severity="warning")
        else:
            proc_names[p["name"]] = p

    def proc_at(line):
        cur = None
        for p in procedures:
            if p["line"] <= line:
                cur = p
        return cur["name"] if cur else None

    stripped = [l.lstrip(" ") for l in lines]

    def fix(n, proc):
        t = n.get("type")
        if t == "goto":
            lab = n["label"]
            key = (lab + ":") if n["exact_match"] else lab
            hit = None
            for idx, l in enumerate(stripped):
                if l.lower().startswith(key.lower()) and key:
                    hit = idx + 1
                    break
            if hit is None:
                diag.add(n["line"], "goto_missing_label", "goto %s: no such label" % lab,
                         "target=null; in the engine the goto runs to the end of the file "
                         "and the script ends", severity="error")
            else:
                tproc = proc_at(hit)
                is_label = stripped[hit - 1].rstrip().endswith(":")
                n["target"] = {"line": hit, "procedure": tproc, "is_label": is_label}
                if tproc != proc:
                    n["cross_procedure"] = True
                    diag.add(n["line"], "goto_cross_procedure",
                             "goto %s in %s jumps into procedure %s (line %d)"
                             % (lab, proc, tproc, hit),
                             "resolved; labels are file-wide in the engine (locate_goto scans "
                             "from the top)", severity="info")
                if not is_label:
                    diag.add(n["line"], "goto_prefix_match",
                             "goto %s matches line %d, which is not a plain label" % (lab, hit),
                             "resolved to that line, as the engine's prefix match does")
        elif t == "call":
            nm = n["name"]
            if nm in BUILTINS:
                n["kind"] = "builtin"
            elif nm in proc_names:
                n["kind"] = "local"
            elif nm in global_functions:
                n["kind"] = "global_function"
            else:
                n["kind"] = "unknown"
                guess = difflib.get_close_matches(nm, KNOWN_WORDS, n=1, cutoff=0.75)
                if nm in CHOICE_ONLY:
                    what = "%s() outside a choice block" % nm
                else:
                    what = "call to unknown procedure %s()" % nm
                diag.add(n["line"], "unknown_call", what,
                         "kept as a call with kind=unknown; the engine looks for a local "
                         "procedure, logs 'Procedure void %s not found' and continues"
                         % nm + (" (probable intent: %s)" % guess[0] if guess else ""),
                         severity="error", guess=guess[0] if guess else None)
                if guess:
                    n["guess"] = guess[0]
        for c in _nested_calls(n):
            if c is n:
                continue
            nm = c["name"].lower()
            c["kind"] = ("builtin" if nm in BUILTINS else "local" if nm in proc_names
                         else "global_function" if nm in global_functions else "unknown")

    for p in procedures:
        walk(p["body"], fix, p["name"])

    # Labels nobody jumps to.
    targets = set()
    labels = []

    def gather(n, proc):
        if n.get("type") == "goto" and n.get("target"):
            targets.add(n["target"]["line"])
        if n.get("type") == "label":
            labels.append((n, proc))

    for p in procedures:
        walk(p["body"], gather, p["name"])
    for n, proc in labels:
        if n["line"] not in targets and re.match(r"^[A-Za-z_][A-Za-z0-9_\-]*$", n["name"]):
            diag.add(n["line"], "unused_label", "label %s: in %s is never the target of a goto"
                     % (n["name"], proc), "kept", severity="info")


def _nested_calls(n):
    out = []
    t = n.get("type")
    if t == "call":
        for a in n["args"]:
            X.expr_calls(a, out)
    elif t in ("assign", "int", "return"):
        if n.get("value"):
            X.expr_calls(n["value"], out)
    elif t == "if":
        X.expr_calls(n["cond"], out)
    return out


def parse_script(script, text, global_functions=()):
    """Parse one script. Returns the AST dict (diagnostics included)."""
    sp = ScriptParser(script, text)
    preamble, procedures = sp.parse()
    resolve(script, sp.lines, procedures, sp.diag, global_functions)
    locals_ = []

    def collect(n, proc):
        if n.get("type") == "int" and n.get("name", "").startswith("&"):
            locals_.append({"name": n["name"].lower(), "line": n["line"], "procedure": proc})

    for p in procedures:
        walk(p["body"], collect, p["name"])
    ast = {
        "schema": "dinkc-ast/1",
        "script": script,
        "file": script + ".c",
        "line_count": len(sp.lines),
        "preamble": preamble,
        "procedures": procedures,
        "locals": locals_,
        "diagnostics": sp.diag.items,
    }
    return ast
