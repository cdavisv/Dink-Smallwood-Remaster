"""Stage 4: (screen, pixel x, pixel y) -> world metres.

Scheme: a "lattice rubber sheet". Every grid corner of a sheet (a landmass)
gets one world position; each screen maps bilinearly from its four corners:

    u = x / 600, v = y / 400
    P(x, y) = (1-u)(1-v) P00 + u(1-v) P10 + (1-u)v P01 + uv P11

Screens of one sheet share corner vertices with their grid neighbours, so the
map is continuous across every shared edge (an edge is the same straight
segment from both sides, parametrised by the same pixel coordinate). The
corner positions come from one linear least-squares solve per sheet and axis:
each screen asks for its top and bottom edges to be `w` long and level and its
left and right edges to be `h` long and plumb, where w, h = 600, 400 px x
base_m_per_px x kind scale x stretch. Neighbours that ask for different sizes
meet half way, so scale changes are spread over the screens around a border
(weighted: settlements hold their shape, wilderness absorbs the change). A
very weak pull of every vertex towards its nominal grid position fixes the
free translation of grid-disconnected pieces.

Sheets that are not the mainland are translated as a whole along a direction
from regions.toml until their bounding box is `min_gap_m` from every sheet
placed before them. Interior sets are separate sheets packed in rows south of
the world.

Inverse: Newton iteration on the bilinear map (closed form would also do);
quads stay convex for any scale ratio the table allows, which the build and
tests check.
"""

import math

import numpy as np

from .ir import W, H, GRID_W, GRID_H, col_row, screen_id

EPS_GRAVITY = 1e-3


def _corners(n):
    c, r = col_row(n)
    return [(c, r), (c + 1, r), (c, r + 1), (c + 1, r + 1)]   # P00 P10 P01 P11


def solve_sheet(screens, size_of, weight_of, nominal):
    """Return {vertex (c, r): np.array([x, y])} for one sheet."""
    verts = sorted({v for n in screens for v in _corners(n)})
    idx = {v: i for i, v in enumerate(verts)}
    nv = len(verts)
    rows_x, rhs_x, rows_y, rhs_y = [], [], [], []

    def eq(rows, rhs, a, b, val, w):
        row = np.zeros(nv)
        row[idx[b]] += w
        row[idx[a]] -= w
        rows.append(row)
        rhs.append(val * w)

    for n in screens:
        w_m, h_m = size_of(n)
        wt = weight_of(n)
        p00, p10, p01, p11 = _corners(n)
        eq(rows_x, rhs_x, p00, p10, w_m, wt)
        eq(rows_x, rhs_x, p01, p11, w_m, wt)
        eq(rows_x, rhs_x, p00, p01, 0.0, wt)
        eq(rows_x, rhs_x, p10, p11, 0.0, wt)
        eq(rows_y, rhs_y, p00, p01, h_m, wt)
        eq(rows_y, rhs_y, p10, p11, h_m, wt)
        eq(rows_y, rhs_y, p00, p10, 0.0, wt)
        eq(rows_y, rhs_y, p01, p11, 0.0, wt)
    for v, i in idx.items():
        gx, gy = nominal(v)
        r = np.zeros(nv); r[i] = EPS_GRAVITY
        rows_x.append(r); rhs_x.append(gx * EPS_GRAVITY)
        r = np.zeros(nv); r[i] = EPS_GRAVITY
        rows_y.append(r); rhs_y.append(gy * EPS_GRAVITY)
    X = np.linalg.lstsq(np.array(rows_x), np.array(rhs_x), rcond=None)[0]
    Y = np.linalg.lstsq(np.array(rows_y), np.array(rhs_y), rcond=None)[0]
    return {v: np.array([X[i], Y[i]]) for v, i in idx.items()}


def bbox_of(points):
    a = np.array(points)
    return np.array([a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()])


def rect_gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return math.hypot(dx, dy)


def _poly(P):
    return [tuple(P[0]), tuple(P[1]), tuple(P[3]), tuple(P[2])]      # nw ne se sw


def _poly_area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def _clip(subject, clipper):
    """Sutherland-Hodgman: intersection of two convex polygons (any winding)."""
    def side(pt, a, b):
        return (b[0] - a[0]) * (pt[1] - a[1]) - (b[1] - a[1]) * (pt[0] - a[0])

    area2 = sum(clipper[i][0] * clipper[(i + 1) % len(clipper)][1] - clipper[(i + 1) % len(clipper)][0] * clipper[i][1]
                for i in range(len(clipper)))
    if area2 < 0:
        clipper = clipper[::-1]
    out = subject
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        inp, out = out, []
        if not inp:
            break
        prev = inp[-1]
        for cur in inp:
            sc, sp = side(cur, a, b), side(prev, a, b)
            if sc >= 0:
                if sp < 0:
                    t = sp / (sp - sc)
                    out.append((prev[0] + t * (cur[0] - prev[0]), prev[1] + t * (cur[1] - prev[1])))
                out.append(cur)
            elif sp >= 0:
                t = sp / (sp - sc)
                out.append((prev[0] + t * (cur[0] - prev[0]), prev[1] + t * (cur[1] - prev[1])))
            prev = cur
    return out


def overlaps(corners, min_area_m2=1e-3):
    """[(area m2, screen a, screen b)] for every pair of screen quads that overlap in the world.
    Quads that only share an edge or a corner have zero area and are not reported."""
    items = sorted(corners)
    polys = {n: _poly(corners[n]) for n in items}
    boxes = {n: bbox_of(corners[n]) for n in items}
    found = []
    for i, a in enumerate(items):
        ba = boxes[a]
        for b in items[i + 1:]:
            bb = boxes[b]
            if ba[2] <= bb[0] or bb[2] <= ba[0] or ba[3] <= bb[1] or bb[3] <= ba[1]:
                continue
            inter = _clip(polys[a], polys[b])
            if len(inter) >= 3:
                ar = _poly_area(inter)
                if ar > min_area_m2:
                    found.append((round(ar, 3), a, b))
    return sorted(found, reverse=True)


class LayoutError(Exception):
    pass


class Layout:
    def __init__(self):
        self.corners = {}     # screen -> 4x2 array (P00, P10, P01, P11)
        self.sheet_of = {}    # screen -> sheet name
        self.sheet_shift = {} # sheet -> translation applied after the solve
        self.displaced = {}   # screen -> {"from_sheet": ..., "overlapped": [screens]} (see build)
        self.notes = []

    # ---- forward ---------------------------------------------------------
    def to_world(self, n, x, y):
        P = self.corners[n]
        u, v = x / W, y / H
        return ((1 - u) * (1 - v)) * P[0] + (u * (1 - v)) * P[1] + ((1 - u) * v) * P[2] + (u * v) * P[3]

    def jacobian(self, n, x, y):
        """2x2: columns d(world)/dx, d(world)/dy in metres per pixel."""
        P = self.corners[n]
        u, v = x / W, y / H
        dx = ((1 - v) * (P[1] - P[0]) + v * (P[3] - P[2])) / W
        dy = ((1 - u) * (P[2] - P[0]) + u * (P[3] - P[1])) / H
        return np.stack([dx, dy], 1)

    def local_scale(self, n, x, y):
        J = self.jacobian(n, x, y)
        det = float(np.linalg.det(J))
        sx = float(np.linalg.norm(J[:, 0]))
        sy = float(np.linalg.norm(J[:, 1]))
        rot = math.degrees(math.atan2(J[1, 0], J[0, 0]))
        return {"m_per_px": math.sqrt(abs(det)), "x": sx, "y": sy, "rot_deg": rot, "det": det}

    # ---- inverse ---------------------------------------------------------
    def to_local(self, n, X, Y, iters=30):
        target = np.array([X, Y], float)
        p = np.array([W / 2, H / 2], float)
        for _ in range(iters):
            f = self.to_world(n, p[0], p[1]) - target
            if abs(f[0]) < 1e-9 and abs(f[1]) < 1e-9:
                break
            p = p - np.linalg.solve(self.jacobian(n, p[0], p[1]), f)
        return float(p[0]), float(p[1])

    def screen_bbox(self, n):
        return bbox_of(self.corners[n])

    def locate(self, X, Y, tol=1e-6):
        """(screen, x, y) for a world point, or None. Interior of a quad wins;
        on a shared edge the lower screen number is returned."""
        best = None
        for n, P in self.corners.items():
            b = bbox_of(P)
            if not (b[0] - 1e-6 <= X <= b[2] + 1e-6 and b[1] - 1e-6 <= Y <= b[3] + 1e-6):
                continue
            x, y = self.to_local(n, X, Y)
            if -tol <= x <= W + tol and -tol <= y <= H + tol:
                if best is None or n < best[0]:
                    best = (n, x, y)
        return best

    def quad_area(self, n):
        P = self.corners[n]
        poly = [P[0], P[1], P[3], P[2]]
        s = 0.0
        for i in range(4):
            a, b = poly[i], poly[(i + 1) % 4]
            s += a[0] * b[1] - a[1] * b[0]
        return abs(s) / 2.0

    def is_convex(self, n):
        P = self.corners[n]
        poly = [P[0], P[1], P[3], P[2]]
        signs = []
        for i in range(4):
            a, b, c = poly[i], poly[(i + 1) % 4], poly[(i + 2) % 4]
            cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            signs.append(cr > 0)
        return all(signs) or not any(signs)

    # ---- serialisation ---------------------------------------------------
    @classmethod
    def from_json(cls, data):
        L = cls()
        for s in data["screens"]:
            n = s["screen"]
            c = s["corners"]
            L.corners[n] = np.array([c["nw"], c["ne"], c["sw"], c["se"]], float)
            L.sheet_of[n] = s["sheet"]
        return L


PARK_SHEET = "fragments"


def _grid_piece(ir, sheet_of, n):
    """Screens joined to n by grid adjacency inside n's sheet (no wrap)."""
    todo, piece = [n], {n}
    while todo:
        c, r = col_row(todo.pop())
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cc, rr = c + dc, r + dr
            if 0 <= cc < GRID_W and 0 <= rr < GRID_H:
                m = rr * GRID_W + cc + 1
                if m in ir.screens and m not in piece and sheet_of.get(m) == sheet_of[n]:
                    piece.add(m)
                    todo.append(m)
    return piece


def build(ir, table, screen_kind, screen_sheet, interiors, reached=None):
    """Lay out every screen. screen_kind/screen_sheet: dicts for every used screen (outdoor sheets
    from the table; interior screens get sheet 'interior:<INT id>').

    Overlap rule. Grid pieces that touch no other screen (SCR_299) sit at their nominal position,
    which can land on stretched neighbours. No two screens may overlap in the world. When a pair
    does, the screen that is not reached (`reached`: set of screen numbers the player can reach)
    is parked, with the unreached grid piece it belongs to, on the `fragments` sheet and flagged in
    `Layout.displaced`; the layout is then solved again. Two reached screens that overlap, or an
    unreached piece that holds a reached screen, raise LayoutError."""
    screen_sheet = dict(screen_sheet)
    displaced = {}
    for _ in range(len(ir.used)):
        L = _build(ir, table, screen_kind, screen_sheet, interiors)
        L.displaced = displaced
        pairs = overlaps(L.corners)
        if not pairs:
            return L
        if reached is None:
            raise LayoutError("screens overlap in the world and no reach information was given: %s" % pairs[:5])
        for area, a, b in pairs:
            ra, rb = a in reached, b in reached
            if ra and rb:
                raise LayoutError("reached screens %s and %s overlap by %.1f m2" % (screen_id(a), screen_id(b), area))
            loser, winner = (b, a) if ra else (a, b)
            if screen_sheet[loser] == PARK_SHEET or PARK_SHEET not in table["sheets"]:
                raise LayoutError("unreached screen %s overlaps %s by %.1f m2 and cannot be parked" % (
                    screen_id(loser), screen_id(winner), area))
            piece = _grid_piece(ir, screen_sheet, loser)
            if piece & set(reached):
                raise LayoutError("screen %s overlaps %s by %.1f m2 but its grid piece holds reached screens" % (
                    screen_id(loser), screen_id(winner), area))
            for m in piece:
                displaced[m] = {"from_sheet": screen_sheet[m], "overlapped": [screen_id(winner)]}
                screen_sheet[m] = PARK_SHEET
            break                                   # re-solve before looking at the other pairs
    raise LayoutError("layout did not settle")


def _build(ir, table, screen_kind, screen_sheet, interiors):
    lay = table["layout"]
    base = lay["base_m_per_px"]
    scales = table["scale"]
    weights = lay.get("weight", {})
    stretch = {}
    for st in table.get("stretch", []):
        for c0, r0, c1, r1 in st["cells"]:
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    stretch[(c, r)] = (st.get("x", 1.0), st.get("y", 1.0))

    def size_of(n):
        k = scales[screen_kind[n]]
        sx, sy = stretch.get(col_row(n), (1.0, 1.0)) if not ir.indoor(n) else (1.0, 1.0)
        return W * base * k * sx, H * base * k * sy

    def weight_of(n):
        return weights.get(screen_kind[n], 1.0)

    nom_w = W * base * scales["wilderness"]
    nom_h = H * base * scales["wilderness"]

    def nominal(v):
        return (v[0] * nom_w, v[1] * nom_h)

    L = Layout()
    by_sheet = {}
    for n in ir.used:
        by_sheet.setdefault(screen_sheet[n], []).append(n)
    placed_boxes = []
    # outdoor sheets in table order, mainland first
    order = [s for s in table["sheets"] if s in by_sheet]
    for name in order:
        cfg = table["sheets"][name]
        scr = by_sheet[name]
        V = solve_sheet(scr, size_of, weight_of, nominal)
        corners = {n: np.array([V[v] for v in _corners(n)]) for n in scr}
        box = bbox_of([p for c in corners.values() for p in c])
        shift = np.zeros(2)
        if cfg.get("anchor") != "fixed":
            d = np.array(cfg.get("direction", [1.0, 0.0]), float)
            d = d / np.linalg.norm(d)
            gap = lay["min_gap_m"]

            def ok(t):
                b = box + np.array([*(d * t), *(d * t)])
                return all(rect_gap(b, pb) >= gap for pb in placed_boxes)
            t = 0.0
            step = 50.0
            while not ok(t):
                t += step
            lo = max(0.0, t - step)
            hi = t
            if not ok(lo):
                for _ in range(40):
                    mid = (lo + hi) / 2
                    if ok(mid):
                        hi = mid
                    else:
                        lo = mid
                t = hi
            else:
                t = lo
            shift = d * t
        shift = shift + np.array(cfg.get("offset", [0.0, 0.0]), float)
        for n in scr:
            L.corners[n] = corners[n] + shift
            L.sheet_of[n] = name
        L.sheet_shift[name] = shift.tolist()
        placed_boxes.append(box + np.array([*shift, *shift]))

    # interiors: each set its own sheet, packed in rows south of the world
    world = np.array([min(b[0] for b in placed_boxes), min(b[1] for b in placed_boxes),
                      max(b[2] for b in placed_boxes), max(b[3] for b in placed_boxes)])
    x0 = world[0]
    y = world[3] + lay["interior_offset_m"]
    cur = x0
    row_h = 0.0
    spacing = lay["interior_spacing_m"]
    for it in interiors:
        scr = it["screen_numbers"]
        name = "interior:" + it["id"]
        V = solve_sheet(scr, size_of, weight_of, nominal)
        corners = {n: np.array([V[v] for v in _corners(n)]) for n in scr}
        box = bbox_of([p for c in corners.values() for p in c])
        wbox, hbox = box[2] - box[0], box[3] - box[1]
        if cur > x0 and cur + wbox > x0 + lay["interior_row_width_m"]:
            cur = x0
            y += row_h + spacing
            row_h = 0.0
        shift = np.array([cur - box[0], y - box[1]])
        for n in scr:
            L.corners[n] = corners[n] + shift
            L.sheet_of[n] = name
        L.sheet_shift[name] = shift.tolist()
        cur += wbox + spacing
        row_h = max(row_h, hbox)
    return L
