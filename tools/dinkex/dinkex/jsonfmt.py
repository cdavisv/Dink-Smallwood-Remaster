"""Small JSON writer: structure is indented, leaf records stay one per line.

Keeps the per-screen files readable and diff-friendly without ballooning to
hundreds of kilobytes of one-value-per-line output.
"""

import json


def compact(o):
    return json.dumps(o, separators=(", ", ": "), ensure_ascii=False)


def _has_records(d):
    return any(isinstance(v, list) and v and isinstance(v[0], dict) for v in d.values())


def pretty(o, expand_levels=1, level=0, indent="  "):
    pad = indent * level
    if isinstance(o, dict) and o and (level < expand_levels or (level <= expand_levels and _has_records(o))):
        items = []
        for k, v in o.items():
            items.append('%s%s%s: %s' % (pad, indent, json.dumps(str(k)), pretty(v, expand_levels, level + 1, indent)))
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if level <= expand_levels and isinstance(o, list) and o and any(isinstance(x, (dict, list)) for x in o):
        if level == expand_levels:
            items = [pad + indent + compact(x) for x in o]
        else:
            items = [pad + indent + pretty(x, expand_levels, level + 1, indent) for x in o]
        return "[\n" + ",\n".join(items) + "\n" + pad + "]"
    return compact(o)


def write_json(path, obj, expand_levels=1):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(pretty(obj, expand_levels))
        f.write("\n")
