"""Expression tokenizer and parser for DinkC.

DinkC's own evaluator is tiny (var_figure, D:4905: one value, or `a op b` split on
spaces), but scripts are written as if they were C. We parse the C-like intent into
a tree and let the statement parser annotate where the engine would evaluate it
differently.

Expression nodes (all dicts):
  {"type": "int", "value": 5}
  {"type": "var", "name": "&story"}            names keep their case as written
  {"type": "string", "value": "...", "unterminated": bool}
  {"type": "call", "name": "random", "args": [expr, ...]}
  {"type": "binop", "op": "==", "left": expr, "right": expr}
  {"type": "unary", "op": "-", "operand": expr}
  {"type": "ident", "name": "foo"}             bare word (not a DinkC value)
  {"type": "raw", "text": "..."}               could not be parsed
"""

import re

TOKEN_RE = re.compile(r"""
    (?P<ws>\s+)
  | (?P<string>"[^"]*"?)
  | (?P<var>&[A-Za-z0-9_][A-Za-z0-9_\-]*)
  | (?P<number>\d+)
  | (?P<ident>[A-Za-z_][A-Za-z0-9_\-]*)
  | (?P<op>==|!=|<=|>=|&&|\|\||\+=|-=|\*=|/=|[-+*/<>=(),;!])
  | (?P<junk>.)
""", re.X)

PRECEDENCE = {
    "||": 1, "&&": 2,
    "==": 3, "!=": 3, "<": 3, ">": 3, "<=": 3, ">=": 3,
    "+": 4, "-": 4,
    "*": 5, "/": 5,
}

COMPARISONS = ("==", "!=", "<", ">", "<=", ">=")


class Token:
    __slots__ = ("kind", "text", "pos")

    def __init__(self, kind, text, pos):
        self.kind, self.text, self.pos = kind, text, pos

    def __repr__(self):
        return "Token(%s,%r)" % (self.kind, self.text)


def tokenize(text):
    toks = []
    for m in TOKEN_RE.finditer(text):
        kind = m.lastgroup
        if kind == "ws":
            continue
        toks.append(Token(kind, m.group(), m.start()))
    return toks


class ParseError(Exception):
    pass


class ExprParser:
    def __init__(self, text):
        self.text = text
        self.toks = tokenize(text)
        self.i = 0
        self.problems = []

    def peek(self, k=0):
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else None

    def next(self):
        t = self.peek()
        self.i += 1
        return t

    def at_end(self):
        return self.i >= len(self.toks)

    def parse(self, min_prec=0):
        left = self.unary()
        while True:
            t = self.peek()
            if t is None or t.kind != "op" or t.text not in PRECEDENCE:
                break
            prec = PRECEDENCE[t.text]
            if prec < min_prec:
                break
            self.next()
            right = self.parse(prec + 1)
            left = {"type": "binop", "op": t.text, "left": left, "right": right}
        return left

    def unary(self):
        t = self.peek()
        if t is not None and t.kind == "op" and t.text in ("-", "!", "+"):
            self.next()
            operand = self.unary()
            if t.text == "+":
                return operand
            if t.text == "-" and operand.get("type") == "int":
                return {"type": "int", "value": -operand["value"]}
            return {"type": "unary", "op": t.text, "operand": operand}
        return self.primary()

    def primary(self):
        t = self.next()
        if t is None:
            raise ParseError("unexpected end of expression")
        if t.kind == "number":
            return {"type": "int", "value": int(t.text)}
        if t.kind == "var":
            return {"type": "var", "name": t.text}
        if t.kind == "string":
            unterminated = len(t.text) < 2 or not t.text.endswith('"')
            if unterminated:
                self.problems.append("unterminated string")
            node = {"type": "string",
                    "value": t.text[1:-1] if not unterminated else t.text[1:]}
            if unterminated:
                node["unterminated"] = True
            return node
        if t.kind == "ident":
            nt = self.peek()
            if nt is not None and nt.kind == "op" and nt.text == "(":
                self.next()
                args = self.call_args()
                return {"type": "call", "name": t.text, "args": args}
            return {"type": "ident", "name": t.text}
        if t.kind == "op" and t.text == "(":
            e = self.parse()
            nt = self.peek()
            if nt is not None and nt.text == ")":
                self.next()
            else:
                self.problems.append("missing ) in expression")
            return e
        raise ParseError("unexpected %r" % t.text)

    def call_args(self):
        args = []
        nt = self.peek()
        if nt is not None and nt.text == ")":
            self.next()
            return args
        while True:
            if self.at_end():
                self.problems.append("missing ) after arguments")
                return args
            args.append(self.parse())
            nt = self.peek()
            if nt is None:
                self.problems.append("missing ) after arguments")
                return args
            if nt.text == ",":
                self.next()
                continue
            if nt.text == ")":
                self.next()
                return args
            # Anything else: stray characters inside the argument list.
            self.problems.append("unexpected %r in argument list" % nt.text)
            self.next()
            if self.peek() is not None and self.peek().text == ")":
                self.next()
                return args


def parse_expr(text):
    """Parse a whole expression. Returns (node, problems, rest_tokens_text)."""
    p = ExprParser(text)
    if not p.toks:
        return {"type": "raw", "text": text.strip()}, ["empty expression"], ""
    try:
        node = p.parse()
    except ParseError as e:
        return {"type": "raw", "text": text.strip()}, [str(e)], ""
    rest = ""
    if not p.at_end():
        rest = text[p.peek().pos:]
    return node, p.problems, rest


def expr_vars(node, out=None):
    """All variable names (lower case) read by an expression."""
    if out is None:
        out = []
    if not isinstance(node, dict):
        return out
    t = node.get("type")
    if t == "var":
        out.append(node["name"].lower())
    elif t == "call":
        for a in node["args"]:
            expr_vars(a, out)
    elif t == "binop":
        expr_vars(node["left"], out)
        expr_vars(node["right"], out)
    elif t == "unary":
        expr_vars(node["operand"], out)
    return out


def expr_calls(node, out=None):
    if out is None:
        out = []
    if not isinstance(node, dict):
        return out
    t = node.get("type")
    if t == "call":
        out.append(node)
        for a in node["args"]:
            expr_calls(a, out)
    elif t == "binop":
        expr_calls(node["left"], out)
        expr_calls(node["right"], out)
    elif t == "unary":
        expr_calls(node["operand"], out)
    return out


def to_text(node):
    """Render an expression back to DinkC-ish text (for CSV columns)."""
    if not isinstance(node, dict):
        return str(node)
    t = node.get("type")
    if t == "int":
        return str(node["value"])
    if t == "var":
        return node["name"]
    if t == "string":
        return '"%s"' % node["value"]
    if t == "call":
        return "%s(%s)" % (node["name"], ", ".join(to_text(a) for a in node["args"]))
    if t == "binop":
        return "%s %s %s" % (to_text(node["left"]), node["op"], to_text(node["right"]))
    if t == "unary":
        return "%s%s" % (node["op"], to_text(node["operand"]))
    if t == "ident":
        return node["name"]
    return node.get("text", "")
