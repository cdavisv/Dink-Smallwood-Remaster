"""``dink.ini`` -> sequence table, modelled on the HD engine's loader.

The engine reads the ini in two passes (D:17555-17595, 2393-2625):

1. every ``LOAD_SEQUENCE[_NOW]`` line, in file order (a later definition of
   the same sequence number replaces an earlier one);
2. every other command (``SET_SPRITE_INFO``, ``SET_FRAME_SPECIAL``,
   ``SET_FRAME_DELAY``, ``SET_FRAME_FRAME``, ``STARTING_DINK_*`` ...), in file
   order.

Sprite state is kept per *picture* (an image file), and each sequence has a
frame table pointing at pictures, exactly as the engine does.  This matters:
``SET_FRAME_FRAME`` re-points a table slot at another sequence's picture, and a
later ``SET_SPRITE_INFO`` on that slot then edits the *other* picture.

Tokenisation follows ``separate_string`` (misc_util.cpp:269): fields are split
on single spaces and parsing stops at the first empty field, so a doubled
space ends the line.  Keywords are matched case-insensitively and exactly
(``compare``, D:412); numbers use ``atol`` (leading integer, else 0).
"""

import re
from dataclasses import dataclass, field

from .bmp import bmp_size

C_MAX_SEQUENCES = 2000          # dink.h:190

# Sequences whose colour key the engine forces off (D:2142-2160).  Applied only
# for LEFTALIGN and NOTANIM sequences.
NO_KEY_SEQS = {181, 182, 183, 184, 185, 190, 451}
# Frame 11 of sequence 181 is forced back to white-keyed (D:1743, 1999).
WHITE_KEY_FRAME_HACK = (181, 11)

_ATOL = re.compile(r"\s*([+-]?\d+)")


def atol(s):
    m = _ATOL.match(s or "")
    return int(m.group(1)) if m else 0


def tokenize(line):
    """separate_string() semantics: split on ' ', stop at the first empty field."""
    line = line.replace("\n", "").replace("\r", "")
    out = []
    for f in line.split(" "):
        if not f:
            break
        out.append(f)
    return out


def default_origin(w, h):
    """Origin ("depth dot") used when the ini gives none (D:1834-1923)."""
    return w - w // 2 + w // 6, h - h // 4 - h // 30


def default_hardbox(w, h):
    return {"left": -(w // 4), "top": -(h // 10), "right": w // 4, "bottom": h // 10}


@dataclass
class SeqDef:
    seq: int
    path: str                    # as written, backslashes -> '/', original case
    keyword: str                 # '' | 'BLACK' | 'LEFTALIGN' | 'NOTANIM' (upper-case)
    load_now: bool
    line_no: int
    all_lines: list
    is_anim: bool                # m_bIsAnim
    transparency: str            # 'white' | 'black' | 'none'
    speed: int = 0
    xoff: int = 0
    yoff: int = 0
    hardbox: dict = field(default_factory=lambda: {"left": 0, "top": 0, "right": 0, "bottom": 0})
    raw_tokens: list = field(default_factory=list)


@dataclass
class Pic:
    key: tuple                   # (seq, frame) of the file this picture comes from
    source: object               # gfx.Source
    width: int
    height: int
    origin: dict
    origin_source: str
    hardbox: dict
    hardbox_source: str
    custom_line: int = 0


def read_load_sequence(tokens, line_no, load_now, previous=None):
    """ReadFromLoadSequenceString() (D:2165-2220)."""
    seq = atol(tokens[2]) if len(tokens) > 2 else 0
    ev = lambda i: tokens[i - 1] if 0 < i <= len(tokens) else ""     # ev[i] in the C++ source is 1-based
    path = ev(2).replace("\\", "/")
    kw = ev(4).upper()
    trans = "white"
    is_anim = False
    keyword = ""
    if kw == "BLACK":
        trans, is_anim, keyword = "black", True, "BLACK"
    elif kw == "LEFTALIGN":
        keyword = "LEFTALIGN"
        trans = "none" if seq in NO_KEY_SEQS else "white"
    elif kw == "NOTANIM":
        keyword = "NOTANIM"
        trans = "none" if seq in NO_KEY_SEQS else "white"
    else:
        is_anim = True
    d = SeqDef(seq=seq, path=path, keyword=keyword, load_now=load_now, line_no=line_no,
               all_lines=(previous.all_lines if previous else []) + [line_no],
               is_anim=is_anim, transparency=trans, raw_tokens=list(tokens))
    if is_anim:
        d.speed = atol(ev(4))
        d.xoff = atol(ev(5))
        d.yoff = atol(ev(6))
        d.hardbox = {"left": atol(ev(7)), "top": atol(ev(8)), "right": atol(ev(9)), "bottom": atol(ev(10))}
    return d


class SequenceModel:
    """The resolved sequence table.  Build with ``SequenceModel.from_ini``."""

    def __init__(self):
        self.defs = {}               # seq -> SeqDef (final definition)
        self.superseded = {}         # seq -> [SeqDef,...] earlier definitions
        self.files = {}              # seq -> [gfx.Source] frames 1..last found on disk
        self.table = {}              # seq -> {frame idx -> (seq,frame) | -1}
        self.special = {}            # seq -> {frame idx -> int}
        self.delay = {}              # seq -> {frame idx -> (ms, source)}
        self.aliases = {}            # seq -> {frame idx -> {'seq','frame','line'} | {'loop':True,'line'}}
        self.custom = {}             # (seq,frame) -> (xoff,yoff,l,t,r,b,line_no)
        self.pics = {}               # (seq,frame) -> Pic
        self.misc = {"playmidi": [], "starting_dink": {}, "gfx_alttext_disable": False}
        self.warnings = []
        self.ini_lines = 0

    # ------------------------------------------------------------------
    @classmethod
    def from_ini(cls, ini_path, graphics):
        with open(ini_path, "r", encoding="latin1", newline="") as f:
            text = f.read()
        lines = text.split("\n")
        m = cls()
        m.ini_lines = len(lines) - (1 if lines and lines[-1] == "" else 0)
        m._pass1(lines)
        m._scan_files(graphics)
        m._pass2(lines)
        m._build_pics()
        return m

    def warn(self, msg):
        self.warnings.append(msg)

    # -- pass 1 --------------------------------------------------------
    def _pass1(self, lines):
        for n, raw in enumerate(lines, 1):
            line = raw.rstrip("\r")
            if not line or line[0] == ";":
                continue
            tk = tokenize(line)
            if not tk:
                continue
            cmd = tk[0].upper()
            if cmd not in ("LOAD_SEQUENCE", "LOAD_SEQUENCE_NOW"):
                continue
            seq = atol(tk[2]) if len(tk) > 2 else 0
            if not 0 <= seq < C_MAX_SEQUENCES:
                self.warn("line %d: sequence %d outside 0..%d, ignored" % (n, seq, C_MAX_SEQUENCES - 1))
                continue
            prev = self.defs.get(seq)
            d = read_load_sequence(tk, n, cmd == "LOAD_SEQUENCE_NOW")
            if prev is not None:
                d.all_lines = prev.all_lines + [n]
                self.superseded.setdefault(seq, []).append(prev)
                self.warn("line %d: sequence %d redefined (was line %d, %s); the later definition wins"
                          % (n, seq, prev.line_no, prev.path))
            self.defs[seq] = d

    def _scan_files(self, graphics):
        for seq, d in sorted(self.defs.items()):
            srcs, cat = graphics.frames(d.path)
            self.files[seq] = srcs
            if not srcs:
                self.warn("sequence %d (%s): no frames found on disk" % (seq, d.path))
            self.table[seq] = {i: (seq, i) for i in range(1, len(srcs) + 1)}
            self.delay[seq] = {i: (d.speed, "sequence_default") for i in range(1, len(srcs) + 1)}
            self.special[seq] = {}
            self.aliases[seq] = {}

    # -- pass 2 --------------------------------------------------------
    def _valid_seq(self, s):
        return 0 <= s < C_MAX_SEQUENCES

    def _pass2(self, lines):
        for n, raw in enumerate(lines, 1):
            line = raw.rstrip("\r")
            if not line or line[0] == ";":
                continue
            tk = tokenize(line)
            if not tk:
                continue
            cmd = tk[0].upper()
            a = lambda i: atol(tk[i]) if i < len(tk) else 0
            if cmd == "PLAYMIDI":
                self.misc["playmidi"].append({"line": n, "file": tk[1] if len(tk) > 1 else ""})
            elif cmd == "GFX_ALTTEXT_DISABLE":
                self.misc["gfx_alttext_disable"] = True
            elif cmd == "STARTING_DINK_X":
                self.misc["starting_dink"]["x"] = a(1)
            elif cmd == "STARTING_DINK_Y":
                self.misc["starting_dink"]["y"] = a(1)
            elif cmd == "STARTING_DINK_MAP":
                # not handled by the HD engine's ini loader (no matching branch)
                self.misc["starting_dink"]["map_ignored_by_engine"] = a(1)
            elif cmd == "SET_SPRITE_INFO":
                s, fr = a(1), a(2)
                if not self._valid_seq(s):
                    self.warn("line %d: SET_SPRITE_INFO sequence %d invalid" % (n, s))
                    continue
                key = self.table.get(s, {}).get(fr, 0)
                if key == 0 or key == -1:
                    self.warn("line %d: SET_SPRITE_INFO %d %d targets a missing frame (engine writes to picture 0)" % (n, s, fr))
                    continue
                self.custom[key] = (a(3), a(4), a(5), a(6), a(7), a(8), n)
            elif cmd == "SET_FRAME_SPECIAL":
                s, fr, v = a(1), a(2), a(3)
                if not self._valid_seq(s):
                    self.warn("line %d: SET_FRAME_SPECIAL sequence %d invalid" % (n, s))
                    continue
                self.special.setdefault(s, {})[fr] = v
            elif cmd == "SET_FRAME_DELAY":
                s, fr, v = a(1), a(2), a(3)
                if not self._valid_seq(s):
                    self.warn("line %d: SET_FRAME_DELAY sequence %d invalid" % (n, s))
                    continue
                self.delay.setdefault(s, {})[fr] = (v, "set_frame_delay:line%d" % n)
            elif cmd == "SET_FRAME_FRAME":
                s, fr, src_s, src_f = a(1), a(2), a(3), a(4)
                if not self._valid_seq(s):
                    self.warn("line %d: SET_FRAME_FRAME sequence %d invalid" % (n, s))
                    continue
                tbl = self.table.setdefault(s, {})
                if src_s == -1:
                    tbl[fr] = -1
                    self.aliases.setdefault(s, {})[fr] = {"loop": True, "line": n}
                else:
                    if not self._valid_seq(src_s):
                        self.warn("line %d: SET_FRAME_FRAME source sequence %d invalid" % (n, src_s))
                        continue
                    key = self.table.get(src_s, {}).get(src_f, 0)
                    if key == 0:
                        tbl.pop(fr, None)
                        self.warn("line %d: SET_FRAME_FRAME %d %d <- %d %d copies an empty slot" % (n, s, fr, src_s, src_f))
                    else:
                        tbl[fr] = key
                        self.aliases.setdefault(s, {})[fr] = {"seq": src_s, "frame": src_f, "line": n}

    # -- pictures --------------------------------------------------------
    def _build_pics(self):
        for seq, d in sorted(self.defs.items()):
            srcs = self.files[seq]
            if not srcs:
                continue
            sizes = []
            for s in srcs:
                with open(s.path, "rb") as f:
                    f.seek(s.offset)
                    head = f.read(32)
                sizes.append(bmp_size(head))
            w1, h1 = sizes[0]
            # Anim: frame 1 fixes the origin for every frame (D:1798-1830).
            if d.is_anim:
                dx, dy = default_origin(w1, h1)
                seq_x = d.xoff if d.xoff > 0 else dx
                seq_y = d.yoff if d.yoff > 0 else dy
                seq_src_x = "ini" if d.xoff > 0 else "default_from_frame1"
                seq_src_y = "ini" if d.yoff > 0 else "default_from_frame1"
            for i, (src, (w, h)) in enumerate(zip(srcs, sizes), 1):
                key = (seq, i)
                cu = self.custom.get(key)
                if cu is not None:
                    ox, oy, l, t, r, b, ln = cu
                    origin = {"x": ox, "y": oy}
                    hb = {"left": l, "top": t, "right": r, "bottom": b}
                    osrc = hsrc = "set_sprite_info:line%d" % ln
                    custom_line = ln
                else:
                    custom_line = 0
                    if d.is_anim:
                        origin = {"x": seq_x, "y": seq_y}
                        osrc = "ini" if (d.xoff > 0 and d.yoff > 0) else (
                            "default_from_frame1" if (d.xoff <= 0 and d.yoff <= 0) else "mixed_ini_and_default")
                    else:
                        dx, dy = default_origin(w, h)
                        origin = {"x": d.xoff if d.xoff > 0 else dx, "y": d.yoff if d.yoff > 0 else dy}
                        osrc = "default_own_size" if (d.xoff <= 0 and d.yoff <= 0) else "mixed_ini_and_default"
                    g = default_hardbox(w, h)
                    hb = dict(g)
                    forced_x = d.hardbox["right"] > 0
                    forced_y = d.hardbox["bottom"] > 0
                    if forced_x:
                        hb["left"], hb["right"] = d.hardbox["left"], d.hardbox["right"]
                    if forced_y:
                        hb["top"], hb["bottom"] = d.hardbox["top"], d.hardbox["bottom"]
                    hsrc = "ini" if (forced_x and forced_y) else ("default_guess" if not (forced_x or forced_y) else "mixed_ini_and_default")
                self.pics[key] = Pic(key, src, w, h, origin, osrc, hb, hsrc, custom_line)

    # -- queries -----------------------------------------------------------
    def pic_for(self, seq, frame):
        """getpic(): the picture drawn for placement (seq, frame), or None."""
        if seq == 0 or not 0 < seq < C_MAX_SEQUENCES:
            return None
        key = self.table.get(seq, {}).get(frame, 0)
        if key in (0, -1):
            return None
        return self.pics.get(key)

    def transparency_for(self, seq, frame):
        d = self.defs[seq]
        if (seq, frame) == WHITE_KEY_FRAME_HACK:
            return "white"
        return d.transparency

    def frame_indices(self, seq):
        idx = set(self.table.get(seq, {})) | set(self.special.get(seq, {})) | set(self.delay.get(seq, {}))
        return sorted(i for i in idx if i >= 0)

    # -- JSON -------------------------------------------------------------
    def frame_json(self, seq, i):
        d = self.defs[seq]
        key = self.table.get(seq, {}).get(i, 0)
        own_file = i <= len(self.files.get(seq, []))
        fr = {"frame": i}
        al = self.aliases.get(seq, {}).get(i)
        ms, dsrc = self.delay.get(seq, {}).get(i, (0, "unset"))
        fr["delay_ms"] = ms
        fr["delay_source"] = dsrc
        sp = self.special.get(seq, {}).get(i, 0)
        fr["special"] = sp
        fr["is_hit_frame"] = sp == 1
        if key == -1:
            fr.update({"loop_to_start": True, "pic": None, "image": None, "source": None,
                       "width": None, "height": None, "origin": None, "hardbox": None,
                       "alias": {"loop": True, "line": al["line"] if al else None},
                       "transparency": None})
            return fr
        if key == 0:
            fr.update({"loop_to_start": False, "pic": None, "image": None, "source": None,
                       "width": None, "height": None, "origin": None, "hardbox": None,
                       "alias": None, "transparency": None, "empty": True})
            return fr
        pic = self.pics[key]
        fr.update({
            "loop_to_start": False,
            "pic": {"seq": key[0], "frame": key[1]},
            "image": image_path(key[0], key[1]),
            "source": pic.source.to_json(),
            "width": pic.width, "height": pic.height,
            "origin": pic.origin, "origin_source": pic.origin_source,
            "hardbox": pic.hardbox, "hardbox_source": pic.hardbox_source,
            "transparency": self.transparency_for(key[0], key[1]),
            "alias": None if key == (seq, i) else {"seq": key[0], "frame": key[1], "line": al["line"] if al else None},
        })
        return fr

    def seq_json(self, seq):
        d = self.defs[seq]
        frames = [self.frame_json(seq, i) for i in self.frame_indices(seq)]
        return {
            "seq": seq,
            "path": d.path,
            "directory": d.path.rpartition("/")[0],
            "prefix": d.path.rpartition("/")[2],
            "ini_line": d.line_no,
            "ini_lines": d.all_lines,
            "load_now": d.load_now,
            "keyword": d.keyword or None,
            "flags": {"black": d.keyword == "BLACK", "leftalign": d.keyword == "LEFTALIGN",
                      "notanim": d.keyword == "NOTANIM"},
            "is_anim": d.is_anim,
            "transparency": d.transparency,
            "default_delay_ms": d.speed,
            "ini_origin": {"x": d.xoff, "y": d.yoff} if d.is_anim else None,
            "ini_hardbox": d.hardbox if d.is_anim else None,
            "file_frame_count": len(self.files.get(seq, [])),
            "frame_count": len(frames),
            "frames": frames,
        }

    def to_json(self):
        return {
            "schema": "dinkex.sequences/1",
            "ini_lines": self.ini_lines,
            "sequence_count": len(self.defs),
            "misc": self.misc,
            "redefined": {str(k): [{"line": p.line_no, "path": p.path} for p in v]
                          for k, v in sorted(self.superseded.items())},
            "warnings": self.warnings,
            "sequences": [self.seq_json(s) for s in sorted(self.defs)],
        }


def image_path(seq, frame):
    return "sprites/%d/%02d.png" % (seq, frame)
