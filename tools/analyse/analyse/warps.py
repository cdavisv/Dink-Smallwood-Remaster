"""Warp graph: every warp placement (prop != 0) plus script-driven screen
changes, with source/destination components, an inferred kind and return
links."""

import numpy as np

from .scripts import NON_PLAYER_TRIGGERS

from .ir import W, H, GRID_W, SIDEBAR, WARP, screen_id, col_row

SEQ_KIND = {
    61: "door", 62: "door",           # graphics/struct/details/door (outdoor building doors)
    428: "stairs",                    # graphics/inside/stairs
    64: "exit", 87: "exit",           # inside/details inacc-/table-: interior wall strip used as the way out
    89: "hole",                       # lands/details/crack- frame 10: a hole in the ground
}


def nearest_walkable(lab, x, y, radius=60):
    """(label, x, y, distance) of the nearest labelled pixel to (x, y), or None."""
    x = int(round(x)); y = int(round(y))
    x0, x1 = max(0, x - radius), min(W, x + radius + 1)
    y0, y1 = max(0, y - radius), min(H, y + radius + 1)
    if x0 >= x1 or y0 >= y1:
        return None
    win = lab[y0:y1, x0:x1]
    ys, xs = np.nonzero(win)
    if len(ys) == 0:
        return None
    d2 = (xs + x0 - x) ** 2 + (ys + y0 - y) ** 2
    i = int(np.argmin(d2))
    px, py = int(xs[i] + x0), int(ys[i] + y0)
    return int(lab[py, px]), px, py, float(np.sqrt(d2[i]))


def dominant_floor(ir, n):
    """Most common land terrain on a screen's tile layer (for warp kinds)."""
    tc = ir.tile_classes
    counts = {}
    for t in ir.screens[n]["tiles"]:
        row = tc.get(t["num"])
        if row and row["walkable_hint"] in ("yes", "partial"):
            counts[row["terrain"]] = counts.get(row["terrain"], 0) + 1
    if not counts:
        return None
    return max(sorted(counts), key=lambda k: counts[k])


def infer_kind(p, src_indoor, dst_indoor, dst_floor, src_floor):
    seq = p["seq"]
    k = SEQ_KIND.get(seq, "other")
    if k == "exit" and not src_indoor:
        k = "door"                    # an interior-wall strip used outdoors (rare)
    if k == "door" and src_indoor and dst_indoor:
        k = "interior_door"
    if k == "exit" and dst_indoor:
        k = "interior_door"
    if k == "hole":
        cave_dst = dst_floor == "cave_floor"
        if not src_indoor and dst_indoor:
            k = "cave_mouth" if cave_dst else "hole"
        elif src_indoor and not dst_indoor:
            k = "cave_exit" if src_floor == "cave_floor" else "hole_exit"
        elif not src_indoor and not dst_indoor:
            k = "hole"                # hole to another outdoor screen (tunnel / pit)
        else:
            k = "trapdoor"
    return k


def sprite_warps(ir, comps):
    out = []
    owners = {}
    for n in ir.used:
        s = ir.screens[n]
        for p in s["placements"]:
            if not p["is_warp"]:
                continue
            v = p["vision"]
            hard = ir.hardness(n, v if v in ir.visions(n) else 0)
            key = (n, v)
            if key not in owners:
                owners[key] = ir.owner(n, v if v in ir.visions(n) else 0)
            trig = (hard == WARP) & (owners[key] == p["index"])
            src_lab = comps[n].labels
            src = set()
            if trig.any():
                g = trig.copy()
                for _ in range(3):        # dilate 3 px, 4-neighbour
                    g2 = g.copy()
                    g2[1:, :] |= g[:-1, :]; g2[:-1, :] |= g[1:, :]
                    g2[:, 1:] |= g[:, :-1]; g2[:, :-1] |= g[:, 1:]
                    g = g2
                src = set(int(x) for x in np.unique(src_lab[g & ~trig]) if x > 0)
                trigger = "walk_into_hardbox"
            else:
                trigger = "script_only" if not p["has_hardness"] else "hardbox_overwritten"
            if not src:
                nw = nearest_walkable(src_lab, p["map_x"], p["map_y"], 80)
                if nw:
                    src = {nw[0]}
            dst = p["warp_map"]
            rec = {
                "id": p["id"], "source": "sprite", "src_screen": n, "src_id": screen_id(n),
                "x": p["map_x"], "y": p["map_y"], "seq": p["seq"], "frame": p["frame"],
                "parm_seq": p["parm_seq"], "anim_seq": p["parm_seq"] or None,
                "sound": p["sound"], "vision": v, "hard_raw": p["hard"], "script": p["script"] or None,
                "trigger": trigger,
                "src_comps": sorted(src),
                "dst_screen": dst, "dst_id": screen_id(dst) if dst in ir.screens else None,
                "dst_x": p["warp_x"] - SIDEBAR, "dst_y": p["warp_y"],
            }
            _set_dst_validity(ir, rec)
            _attach_dst(ir, comps, rec)
            rec["dst_engine"] = dst_engine(ir, rec)
            rec["kind"] = infer_kind(p, ir.indoor(n), rec["dst_screen_exists"] and ir.indoor(dst),
                                     rec["dst_screen_exists"] and dominant_floor(ir, dst), dominant_floor(ir, n))
            out.append(rec)
    return out


def _set_dst_validity(ir, rec):
    """dst_screen_exists: a map record; dst_in_bounds: inside the 600 x 400 playfield;
    dst_valid: both (a destination the engine takes literally)."""
    rec["dst_screen_exists"] = rec["dst_screen"] in ir.screens
    rec["dst_in_bounds"] = dst_in_bounds(rec["dst_x"], rec["dst_y"])
    rec["dst_valid"] = rec["dst_screen_exists"] and rec["dst_in_bounds"]


def _attach_dst(ir, comps, rec):
    """Walkable component at the destination. An off-map point is clamped to the nearest edge
    pixel first (where the engine would put Dink, or where the script walks him in from)."""
    rec["dst_comp"] = None
    rec["dst_offset_px"] = None
    if not rec["dst_screen_exists"] or rec["dst_x"] is None or rec["dst_y"] is None:
        return
    x, y = min(max(rec["dst_x"], 0), W - 1), min(max(rec["dst_y"], 0), H - 1)
    nw = nearest_walkable(comps[rec["dst_screen"]].labels, x, y, 80)
    if nw:
        rec["dst_comp"] = nw[0]
        rec["dst_offset_px"] = round(nw[3], 1)


def dst_in_bounds(x, y):
    """Map pixels (placement x minus the 20 px bar): the engine's playfield is x 0..599, y 0..399."""
    return x is not None and y is not None and 0 <= x < W and 0 <= y < H


def dst_engine(ir, rec, walk_off_screen=False, then_moves=None):
    """What the engine does with a warp destination (dink.cpp did_player_cross_screen D:14049).

    The warp sets &player_map, loads that screen and puts Dink at (x, y) without any range check.
    On the next frame `did_player_cross_screen` looks at his position: past an edge it loads the
    neighbouring screen (pmap -1 / +1 / -32 / +32, if that map record exists) and puts him on the
    opposite edge, else it clamps him to the edge. `dink_can_walk_off_screen(1)` makes it return
    at once, so an off-map position stays as written (a script walking him in, as s2-culg does).
    Outcomes: in_range, off_screen_entrance, edge_crosses, edge_clamped, no_destination."""
    x, y, n = rec["dst_x"], rec["dst_y"], rec["dst_screen"]
    if not rec["dst_screen_exists"] or x is None or y is None:
        return {"outcome": "no_destination"}
    cx, cy = min(max(x, 0), W - 1), min(max(y, 0), H - 1)
    if dst_in_bounds(x, y):
        return {"outcome": "in_range", "screen": n, "x": x, "y": y}
    out = {"x": x, "y": y, "clamped_x": cx, "clamped_y": cy}
    if walk_off_screen:
        out.update(outcome="off_screen_entrance", screen=n,
                   reason="dink_can_walk_off_screen(1) runs before the warp, so the edge check is skipped "
                          "and Dink stands outside the map at (%d, %d) until the script moves him" % (x, y))
        if then_moves:
            out["then_script_moves"] = then_moves
        return out
    step = None
    if x < 0:
        step = -1
    elif x >= W:
        step = 1
    elif y < 0:
        step = -GRID_W
    elif y >= H:
        step = GRID_W
    if step is not None and (n + step) in ir.screens:
        out.update(outcome="edge_crosses", screen=n + step,
                   reason="did_player_cross_screen loads screen %d (map record exists) on the next frame" % (n + step))
    else:
        out.update(outcome="edge_clamped", screen=n,
                   reason="no neighbouring screen, so did_player_cross_screen clamps Dink to the edge")
    return out


def script_warp_kind(name, triggers):
    """Kind of a script warp. By script name: `s6-warp` teleport machine, `*-warp` teleport,
    `*hole*` pit. Otherwise by what starts it: a warp in a procedure the player starts by walking
    into the sprite (`touch`, `push`) or talking to it (`talk`) is a `script_transition`; one that
    fires from `main` (the screen loads), `die` or a combat procedure belongs to a scripted
    sequence the player does not trigger by walking into anything: a `cutscene`."""
    if name.endswith("-warp") or name in ("s6-warp", "s7-warp"):
        return "teleport_machine" if name == "s6-warp" else "teleport"
    if "hole" in name:
        return "pit"
    if set(triggers) & set(NON_PLAYER_TRIGGERS):
        return "cutscene"
    return "script_transition"


def script_warps(ir, comps, scripts):
    from .scripts import script_screens, placed_scripts
    placed = placed_scripts(ir)
    out = []
    for i, w in enumerate(scripts.warps()):
        srcs, how = script_screens(ir, scripts, w["script"], placed)
        name = w["script"]
        kind = script_warp_kind(name, w["triggers"])
        dst = w["target"]
        rec = {
            "id": "SW_%s_L%d" % (name, w["line"]), "source": "script", "script": name, "line": w["line"],
            "src_screens": srcs, "src_how": how,
            "proc": w["proc"], "entry_procs": w["entry_procs"], "triggers": w["triggers"],
            "player_triggered": not (set(w["triggers"]) & set(NON_PLAYER_TRIGGERS)),
            "dst_screen": dst, "dst_id": screen_id(dst) if dst in ir.screens else None,
            "dst_x": (w["x"] - SIDEBAR) if w["x"] is not None else None, "dst_y": w["y"],
            "kind": kind,
        }
        _set_dst_validity(ir, rec)
        _attach_dst(ir, comps, rec)
        rec["dst_engine"] = dst_engine(ir, rec, w["walk_off_screen"], w["then_moves"])
        out.append(rec)
    return out


def link_returns(ir, warps, swarps):
    """has_return / return_ids for sprite warps (and script warps)."""
    by_src = {}
    for w in warps:
        by_src.setdefault(w["src_screen"], []).append(w)
    for w in warps + swarps:
        back = []
        if w["dst_screen_exists"]:
            srcs = [w["src_screen"]] if w["source"] == "sprite" else w["src_screens"]
            for cand in by_src.get(w["dst_screen"], []):
                if cand["dst_screen"] in srcs:
                    d = 0.0
                    if w["dst_x"] is not None and w["dst_y"] is not None:
                        d = ((cand["x"] - w["dst_x"]) ** 2 + (cand["y"] - w["dst_y"]) ** 2) ** 0.5
                    back.append((d, cand["id"]))
            for sw in swarps:
                if w["dst_screen"] in sw["src_screens"] and sw["dst_screen"] in srcs and sw is not w:
                    back.append((1e9, sw["id"]))
        back.sort()
        w["return_warps"] = [b[1] for b in back]
        w["has_return_warp"] = bool(back)
