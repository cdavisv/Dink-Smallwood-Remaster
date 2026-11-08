"""Loading script text the way the engine does.

`load_script` / `decompress_nocomp` (source/dink/dink.cpp:3526, misc_util.cpp:87):
CR becomes LF, TAB becomes a space and a NUL byte ends the file. We keep a line
split that matches the editor's view of the file (CRLF counts as one line break) so
line numbers in the AST match what a human sees in the `.c` file.

`.d` files are byte-pair encoded (misc_util.cpp:15 `dink_decompress`). The engine
prefers a `.d` over a `.c` with the same name, so we decode them only to check
that they match their `.c` and to report `.d` files that have no `.c`.
"""

import os


def normalise_text(raw: bytes) -> str:
    """Bytes of a .c file -> text with engine-equivalent characters.

    Latin-1 keeps every byte as one character. A NUL ends the script.
    """
    nul = raw.find(b"\x00")
    if nul >= 0:
        raw = raw[:nul]
    text = raw.decode("latin-1")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.replace("\t", " ")


def split_lines(text: str):
    """Return the physical lines (without terminators), 1-based by index+1."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def dink_decompress(data: bytes) -> bytes:
    """Port of misc_util.cpp `dink_decompress` (byte-pair decoding)."""
    out = bytearray()
    pair = [[0, 0] for _ in range(128)]
    if not data:
        return bytes(out)
    pos = 0
    c = data[pos]
    pos += 1
    if c > 127:
        count = (c - 128)
        for i in range(count):
            if pos + 1 < len(data) + 1:
                pair[i][0] = data[pos] if pos < len(data) else 0
                pair[i][1] = data[pos + 1] if pos + 1 < len(data) else 0
            pos += 2
    else:
        out.append(c)
    stack = []
    while True:
        if stack:
            c = stack.pop()
        else:
            if pos >= len(data) or data[pos] == 0:
                break
            c = data[pos]
            pos += 1
        if c > 127:
            p = pair[c - 128]
            stack.append(p[1])
            stack.append(p[0])
            if len(stack) > 4096:  # corrupt input guard
                break
        else:
            out.append(c)
    return bytes(out)


def load_c(path: str) -> str:
    with open(path, "rb") as f:
        return normalise_text(f.read())


def load_d(path: str) -> str:
    with open(path, "rb") as f:
        return normalise_text(dink_decompress(f.read()))


def comparable(text: str) -> str:
    """Whitespace-insensitive form used to compare a .c with its .d."""
    return "\n".join(l.strip() for l in text.split("\n") if l.strip())


def list_scripts(story_dir: str):
    """Sorted list of script base names (lower case) that have a .c file."""
    names = []
    for fn in os.listdir(story_dir):
        if fn.lower().endswith(".c"):
            names.append(fn[:-2])
    return sorted(names, key=str.lower)


def list_d_only(story_dir: str):
    cs = {fn[:-2].lower() for fn in os.listdir(story_dir) if fn.lower().endswith(".c")}
    return sorted(fn[:-2] for fn in os.listdir(story_dir)
                  if fn.lower().endswith(".d") and fn[:-2].lower() not in cs)
