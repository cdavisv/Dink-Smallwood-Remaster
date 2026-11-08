"""Read output lines back out of a compiled ink JSON story (inkVersion 21).

Used by the tests to prove the compiled story carries the original text. Walks every
container and splits its content at "\\n" into lines of text pieces, variable outputs
and tags. Good enough for straight-line content (which is all the converter writes
for spoken lines); not a general ink runtime.
"""


def _containers(node, path="root"):
    if isinstance(node, list):
        yield path, node
        for i, x in enumerate(node):
            if isinstance(x, (list, dict)):
                yield from _containers(x, "%s.%d" % (path, i))
    elif isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, (list, dict)):
                yield from _containers(v, "%s.%s" % (path, k))


def lines(story):
    """Yield {'text': [pieces], 'tags': [str], 'path'} for each tagged output line.
    pieces: ('t', str) or ('v', varname)."""
    for path, cont in _containers(story["root"]):
        cur, tags = [], []
        in_tag = False
        tagbuf = []
        in_ev = False
        evbuf = []
        in_str = False
        for item in cont:
            if item == "str":
                in_str = True
                continue
            if item == "/str":
                in_str = False
                continue
            if in_str:
                continue
            if item == "#":
                in_tag, tagbuf = True, []
                continue
            if item == "/#":
                in_tag = False
                tags.append("".join(tagbuf).strip())
                continue
            if item == "ev":
                in_ev, evbuf = True, []
                continue
            if item == "/ev":
                in_ev = False
                continue
            if in_ev:
                evbuf.append(item)
                if item == "out" and len(evbuf) >= 2 and isinstance(evbuf[-2], dict) \
                        and "VAR?" in evbuf[-2]:
                    cur.append(("v", evbuf[-2]["VAR?"]))
                continue
            if isinstance(item, str) and item.startswith("^"):
                (tagbuf if in_tag else cur).append(item[1:]) if in_tag else cur.append(("t", item[1:]))
                continue
            if item == "\n":
                if tags:
                    yield {"text": cur, "tags": tags, "path": path}
                cur, tags = [], []
                continue
            if isinstance(item, dict) and ("->" in item or "->t->" in item or "*" in item):
                if tags:
                    yield {"text": cur, "tags": tags, "path": path}
                cur, tags = [], []
        if tags:
            yield {"text": cur, "tags": tags, "path": path}


def tag_value(tags, key):
    for t in tags:
        if t.startswith(key + ":"):
            return t[len(key) + 1:]
    return None
