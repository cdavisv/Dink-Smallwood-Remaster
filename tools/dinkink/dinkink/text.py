"""Verbatim text for Ink: variable interpolation, escaping and whitespace protection.

The Ink runtime trims each output line and collapses runs of spaces
(Story.CleanOutputWhitespace). Every space it would remove is written as U+00A0;
the game shows `text.replace(NBSP, " ")`. Characters Ink would read as syntax are
escaped with a backslash, which the compiler removes.
"""

import re

NBSP = " "
_ALWAYS = set("\\{}[]|#")
_LEADING = set("-*+=~(>/<")
_KEYWORD_START = re.compile(r"^(INCLUDE|VAR|CONST|LIST|EXTERNAL|TODO)\b")


def find_vars(text, known):
    """Split `text` into segments the way the engine substitutes variables
    (decipher_string / var_replace): longest names first, case-insensitive.
    `known` maps lower-case DinkC names (with &) to the Ink expression to print.
    Returns [("t", str) | ("v", ink_expr, original_spelling)]."""
    work = text
    hits = []
    low = text.lower()
    taken = [False] * len(text)
    for v in sorted(known, key=len, reverse=True):
        start = 0
        while True:
            idx = low.find(v, start)
            if idx < 0:
                break
            if not any(taken[idx:idx + len(v)]):
                hits.append((idx, v))
                for k in range(idx, idx + len(v)):
                    taken[k] = True
                start = idx + len(v)
            else:
                start = idx + 1
    hits.sort()
    segs = []
    pos = 0
    for idx, v in hits:
        if idx > pos:
            segs.append(("t", work[pos:idx]))
        segs.append(("v", known[v], work[idx:idx + len(v)]))
        pos = idx + len(v)
    if pos < len(work):
        segs.append(("t", work[pos:]))
    return segs


def encode(segs):
    """Ink source for a line of text made of segments (see find_vars)."""
    items = []
    for s in segs:
        if s[0] == "t":
            items.extend(s[1])
        else:
            items.append(("v", s[1]))
    n = len(items)
    nonspace = [i for i, c in enumerate(items) if c != " "]
    first = nonspace[0] if nonspace else n
    last = nonspace[-1] if nonspace else -1
    out = []
    for i, c in enumerate(items):
        if isinstance(c, tuple):
            out.append("{" + c[1] + "}")
            continue
        if c == NBSP and all(x == NBSP for x in items):
            out.append(c)
            continue
        if c == "\t" or c == "\n" or c == "\r" or c == NBSP:
            raise ValueError("unexpected character %r in text" % c)
        if c == " ":
            if i < first or i > last or (i > 0 and items[i - 1] == " "):
                out.append(NBSP)
            else:
                out.append(" ")
            continue
        nxt = items[i + 1] if i + 1 < n else None
        esc = False
        if c in _ALWAYS:
            esc = True
        elif c == "<" and nxt in (">", "-"):
            esc = True
        elif c == "-" and nxt == ">":
            esc = True
        elif c == "/" and (nxt in ("/", "*") or (i > 0 and items[i - 1] == "/")):
            # ink strips comments before it reads escapes, so neither character
            # of a `//` or `/*` may stay next to the other
            esc = True
        elif c == "*" and i > 0 and items[i - 1] == "/":
            esc = True
        elif i == first and c in _LEADING:
            esc = True
        out.append("\\" + c if esc else c)
    s = "".join(out)
    if _KEYWORD_START.match(s):
        s = "\\" + s
    return s


def encode_plain(text):
    return encode([("t", text)])


def decode_display(s):
    """What the player sees from a runtime output string."""
    return s.replace(NBSP, " ")


def clean_output_whitespace(s):
    """Port of ink's Story.CleanOutputWhitespace (C# runtime 1.1/1.2)."""
    out = []
    current_ws_start = -1
    start_of_line = 0
    for i, c in enumerate(s):
        is_inline_ws = c == " " or c == "\t"
        if is_inline_ws and current_ws_start == -1:
            current_ws_start = i
        if not is_inline_ws:
            if c != "\n" and current_ws_start > 0 and current_ws_start != start_of_line:
                out.append(" ")
            current_ws_start = -1
        if c == "\n":
            start_of_line = i + 1
        if not is_inline_ws:
            out.append(c)
    return "".join(out)


def ink_string_literal(s):
    """A string argument inside an Ink expression ("..."); Ink has no escape for '"'."""
    if '"' in s or "\n" in s:
        raise ValueError("cannot put %r in an Ink string literal" % s)
    return '"' + s.replace("\\", "\\\\") + '"'
