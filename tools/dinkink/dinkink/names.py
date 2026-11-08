"""Original DinkC names <-> Ink identifiers (DESIGN.md section 1)."""

import re

# Lower-case words Ink reserves (keywords, operators, weave words).
INK_RESERVED = {"true", "false", "not", "and", "or", "mod", "has", "hasnt", "else",
                "return", "temp", "function", "done", "end", "stopping", "cycle",
                "shuffle", "once", "var", "const", "list", "include", "external",
                "ref", "on", "?"}

_IDENT = re.compile(r"^[A-Za-z0-9_]+$")


def script_ident(script):
    s = script.lower().replace("-", "_")
    if not _IDENT.match(s):
        raise ValueError("script name %r does not map to an Ink identifier" % script)
    if s in INK_RESERVED or s.isdigit():
        s = "k_" + s
    return s


def global_ident(var):
    """'&s2-nad' -> 's2_nad'; '&return' -> 'v_return'."""
    s = var.lstrip("&").lower()
    if "__" in s:
        raise ValueError("global %r contains '__', which is reserved for locals" % var)
    s = s.replace("-", "_")
    if not _IDENT.match(s):
        raise ValueError("variable %r does not map to an Ink identifier" % var)
    if s in INK_RESERVED or s.isdigit() or s.startswith("v_"):
        s = "v_" + s
    return s


def knot_ident(script):
    """Knots share Ink's namespace with VARs and stitches (`&s2-nad` vs `s2-nad.c`,
    `die.c` vs every `die` procedure), so every script knot gets the prefix `d_`."""
    return "d_" + script_ident(script)


def entry_ident(proc):
    """Entry stitch for a procedure: `on_talk` (a bare `story` would clash with &story)."""
    return "on_" + proc


def local_ident(script, var):
    return script_ident(script) + "__" + var.lstrip("&").lower().replace("-", "_")


def label_ident(label):
    s = re.sub(r"[^A-Za-z0-9_]", "_", label.lower())
    return "lbl_" + s


def fix_ident(script, line, suffix=""):
    return "fix_%s_l%d%s" % (script_ident(script), line, suffix)
