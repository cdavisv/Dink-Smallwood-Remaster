"""Readers for `dink.dat` and `map.dat` (layouts from bible 04 section 1, dink.h).

Only the fields script analysis needs are decoded. Script names are NUL-terminated
13-byte fields; bytes after the first NUL are garbage left by the editor and are
ignored, as the engine's strlen() would.
"""

import struct

MAP_RECORD = 31280
SPRITE_SIZE = 220
SPRITE_BASE = 8020
BASE_SCRIPT_OFF = 30240
DINK_DAT_SIZE = 11488


def _cstr(buf: bytes) -> str:
    n = buf.find(b"\x00")
    if n >= 0:
        buf = buf[:n]
    return buf.decode("latin-1")


def read_dink_dat(path: str):
    """Return {'loc': [769], 'music': [769], 'indoor': [769]} (index 0 unused)."""
    with open(path, "rb") as f:
        d = f.read()
    if len(d) < 20 + 3 * 769 * 4:
        raise ValueError("dink.dat too short: %d bytes" % len(d))
    loc = list(struct.unpack_from("<769i", d, 20))
    music = list(struct.unpack_from("<769i", d, 20 + 769 * 4))
    indoor = list(struct.unpack_from("<769i", d, 20 + 2 * 769 * 4))
    return {"loc": loc, "music": music, "indoor": indoor}


def read_map_dat(path: str):
    """Yield one dict per 31,280-byte record: record number (1-based), base script
    and the live placement slots 1..99 (the engine reads indices 1..99, D:5980)."""
    with open(path, "rb") as f:
        data = f.read()
    count = len(data) // MAP_RECORD
    records = []
    for k in range(count):
        off = k * MAP_RECORD
        rec = data[off:off + MAP_RECORD]
        base = _cstr(rec[BASE_SCRIPT_OFF:BASE_SCRIPT_OFF + 13])
        sprites = []
        for j in range(1, 100):
            so = SPRITE_BASE + j * SPRITE_SIZE
            x, y, seq, frame, typ, size = struct.unpack_from("<6i", rec, so)
            active = rec[so + 24] != 0
            brain = struct.unpack_from("<i", rec, so + 36)[0]
            script = _cstr(rec[so + 40:so + 53])
            (speed, base_walk, base_idle, base_attack, base_hit, timer, que,
             hard) = struct.unpack_from("<8i", rec, so + 92)
            (base_die, gold, hitpoints, strength, defense, exp, sound, vision, nohit,
             touch_damage) = struct.unpack_from("<10i", rec, so + 160)
            sprites.append({
                "index": j, "x": x, "y": y, "seq": seq, "frame": frame,
                "type": typ, "size": size, "active": active, "brain": brain,
                "script": script, "vision": vision, "speed": speed,
                "base_walk": base_walk, "base_idle": base_idle,
                "base_attack": base_attack, "base_hit": base_hit, "base_die": base_die,
                "timer": timer, "que": que, "hard": hard, "gold": gold,
                "hitpoints": hitpoints, "strength": strength, "defense": defense,
                "exp": exp, "sound": sound, "nohit": nohit, "touch_damage": touch_damage,
            })
        records.append({"record": k + 1, "base_script": base, "sprites": sprites})
    return records


def script_references(map_path: str, dat_path: str = None):
    """Map each referenced script name (lower case) to a list of references.

    A reference is a dict: kind ('base' or 'sprite'), record, screen (or None when no
    dink.dat screen points at the record), sprite index, type, active, vision, live.
    `live` follows the engine: the screen exists in dink.dat, and for sprites the slot
    is active and not of type 0 or 2 (those never load their script, D:6036-6146), and
    the name is longer than one character (D:6141, D:6805).
    """
    records = read_map_dat(map_path)
    rec_to_screens = {}
    if dat_path:
        dd = read_dink_dat(dat_path)
        for screen in range(1, 769):
            r = dd["loc"][screen]
            if r > 0:
                rec_to_screens.setdefault(r, []).append(screen)
    refs = {}
    for rec in records:
        screens = rec_to_screens.get(rec["record"], []) if dat_path else [None]
        on_map = bool(screens) or not dat_path
        if len(rec["base_script"]) > 1:
            refs.setdefault(rec["base_script"].lower(), []).append({
                "kind": "base", "record": rec["record"],
                "screens": screens, "sprite": None, "type": None,
                "active": True, "vision": 0, "live": on_map,
            })
        for sp in rec["sprites"]:
            if len(sp["script"]) > 1:
                refs.setdefault(sp["script"].lower(), []).append({
                    "kind": "sprite", "record": rec["record"],
                    "screens": screens, "sprite": sp["index"], "type": sp["type"],
                    "active": sp["active"], "vision": sp["vision"],
                    "brain": sp["brain"], "seq": sp["seq"], "frame": sp["frame"],
                    "x": sp["x"], "y": sp["y"],
                    "editor_stats": {k: sp[k] for k in (
                        "hitpoints", "strength", "defense", "exp", "touch_damage",
                        "speed", "timer", "base_walk", "base_idle", "base_attack",
                        "base_hit", "base_die", "gold", "nohit", "sound", "hard")},
                    "live": on_map and sp["active"] and sp["type"] not in (0, 2),
                })
    return refs, len(records)
