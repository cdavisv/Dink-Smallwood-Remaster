"""Smooth, natural outlines for the land ground layers of the terrain mask (VS-09, owner direction of 15 Nov 2026).

The 1997 ground is 50 px tiles, so the layer weights that `export_import_bundle.terrain_mask` reads from the tile
classes are tile rectangles: pale rocky-grass squares, dashed strips of dirt tiles, stair-stepped sand coasts. Here
the weights of every screen are rebuilt in world space, with the screens round it, and given natural outlines:

  1. a window of mask cells (6.25 map px each) holds the screen's raw tile weights and MARGIN_CELLS of its
     world-adjacent neighbours' (the same layer by name), so every step below sees across the screen's borders;
  2. each layer's weight is blurred (SMOOTH_SIGMA_PX): corners round off, stair steps and dashed rows of tiles run
     together into one curving strip;
  3. a low-frequency value noise in GLOBAL map pixels (the 1997 map's 32 x 24 screens laid edge to edge) bends the
     outline where two layers meet (BEND_AMPLITUDE, wavelengths BEND_WAVELENGTHS_PX); laid patterns (cobbles,
     flagstones, boards) bend less (STRUCTURED_BEND);
  4. the winner of each cell is the layer with the largest bent field; no outline moves more than MAX_SHIFT_PX
     (half a tile) from the 1997 one: a cell farther than that from every 1997 layer boundary keeps its 1997 layer;
  5. the winners' outline is feathered (FEATHER_PX blur of each winner's cells, so only the layers that meet there
     share the ramp), and the material's height blend turns the ramp into grass growing over dirt, not a fade;
  6. the result is sampled at points spread from edge to edge (texel 0 on the west edge, texel 95 on the east
     edge, `edge_aligned`), like the water shore distance: two screens hold the same weights along their shared
     border, and M_Env_Terrain's clamped lookup shows exactly those edge texels on the border (inside, the texels
     sit at most half a texel, 3 px, from where the material reads them), so a path or a field edge runs on across it.

Visual only: the terrain mask never feeds collision, hardness, placements or warps. Pure numpy (no scipy).
"""
from __future__ import annotations

import math
import zlib

import numpy as np

MASK_W, MASK_H = 96, 64            # mask texels per screen (export_import_bundle.TERRAIN_MASK_W/H)
CELL_PX = 600.0 / MASK_W           # 6.25 map px per mask cell
MARGIN_CELLS = 22                  # cells of the neighbours round a screen: the reach of field blur, line lift, shift cap and feather
SMOOTH_SIGMA_PX = 12.0             # blur of each layer's weight: rounds a tile corner by about 9 px, joins rows of tiles
BEND_AMPLITUDE = 1.2               # noise added to a layer's field where it meets another: bends the outline by up to
                                   # about +-15 px (the shift cap below holds it to half a tile)
BEND_WAVELENGTHS_PX = ((90.0, 0.6), (36.0, 1.0), (18.0, 0.35))   # octaves (wavelength, weight): one tile is 50 px
PATCH_VARIATION = 0.5               # weight of a slow octave (PATCH_WAVELENGTH_PX) that varies patch size over a field
PATCH_WAVELENGTH_PX = 260.0
STRUCTURED_BEND = 0.25             # cobbles, flagstones, boards, masonry: laid by hand, their edges bend less
FEATHER_PX = 8.0                   # blur of the new outline: a blend ramp about 20 px wide (10 to 90 %)
MAX_SHIFT_PX = 25.0                # the 1997 outline moves at most half a tile
LINE_RADIUS_PX = 30.0              # a layer is measured against its own peak within this radius (thin lines run on)
PEAK_FLOOR = 0.3                   # ... but a layer whose peak there stays below this is not lifted (stray specks)
WORLD_COLUMNS, SCREEN_W_PX, SCREEN_H_PX = 32, 600, 400

def screen_origin_px(n: int):
    """Global map pixel of screen n's north-west corner (the 1997 map's screens laid edge to edge)."""
    return ((n - 1) % WORLD_COLUMNS) * SCREEN_W_PX, ((n - 1) // WORLD_COLUMNS) * SCREEN_H_PX


def _hash01(ix: np.ndarray, iy: np.ndarray, seed: int) -> np.ndarray:
    """A stable pseudo-random number in [0, 1) per integer lattice point (no platform-dependent RNG)."""
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float64) / float(1 << 24)


def value_noise(gx: np.ndarray, gy: np.ndarray, wavelength: float, seed: int) -> np.ndarray:
    """Smooth value noise in [-1, 1] at global map pixels (gx, gy): one random value per lattice point every
    `wavelength` px, blended with a smoothstep. The same point gives the same value on every screen."""
    x, y = gx / wavelength, gy / wavelength
    x0, y0 = np.floor(x), np.floor(y)
    fx, fy = x - x0, y - y0
    fx, fy = fx * fx * (3.0 - 2.0 * fx), fy * fy * (3.0 - 2.0 * fy)
    a, b = _hash01(x0, y0, seed), _hash01(x0 + 1, y0, seed)
    c, d = _hash01(x0, y0 + 1, seed), _hash01(x0 + 1, y0 + 1, seed)
    return ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy) * 2.0 - 1.0


def layer_seed(name: str) -> int:
    return zlib.crc32(name.encode("utf-8")) & 0x7FFFFFFF


def blur(a: np.ndarray, sigma_cells: float) -> np.ndarray:
    """Separable Gaussian blur (truncated at 3 sigma), edges repeated."""
    r = max(1, int(math.ceil(3.0 * sigma_cells)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_cells) ** 2)
    k /= k.sum()
    p = np.pad(a, ((0, 0), (r, r)), mode="edge")
    a = sum(k[i] * p[:, i:i + a.shape[1]] for i in range(2 * r + 1))
    p = np.pad(a, ((r, r), (0, 0)), mode="edge")
    return sum(k[i] * p[i:i + a.shape[0], :] for i in range(2 * r + 1))


def local_max(a: np.ndarray, r: int) -> np.ndarray:
    """Largest value within a (2r+1)-cell square round each cell, edges repeated."""
    h, w = a.shape
    p = np.pad(a, r, mode="edge")
    out = a.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            np.maximum(out, p[r + dy:r + dy + h, r + dx:r + dx + w], out=out)
    return out


def boundary_distance_px(labels: np.ndarray, cap_cells: int) -> np.ndarray:
    """Per cell: map px from the cell's centre to the nearest boundary between two different labels (half a cell
    for a cell next to another label); cells with no other label within `cap_cells` get a value beyond the cap."""
    h, w = labels.shape
    best = np.full(labels.shape, np.inf)
    p = np.pad(labels, cap_cells, mode="edge")
    for dy in range(-cap_cells, cap_cells + 1):
        for dx in range(-cap_cells, cap_cells + 1):
            r = math.hypot(dy, dx)
            if r == 0 or r > cap_cells:
                continue
            other = p[cap_cells + dy:cap_cells + dy + h, cap_cells + dx:cap_cells + dx + w] != labels
            np.minimum(best, np.where(other, r, np.inf), out=best)
    return np.where(np.isinf(best), (cap_cells + 1) * CELL_PX, (best - 0.5) * CELL_PX)


def smooth_fields(raw: dict, origin_px, bend: dict | None = None, vary: dict | None = None, *, sigma_px: float | None = None,
                  amplitude: float | None = None, feather_px: float | None = None, max_shift_px: float | None = None,
                  line_radius_px: float | None = None, peak_floor: float | None = None, connected: bool = True,
                  region: np.ndarray | None = None, report: dict | None = None, fixed=()) -> dict:
    """Natural layer weights on a grid of mask cells. `raw`: layer -> 2D weights (the 1997 tile weights; any
    sum, normalised here; cells without weight count as the first layer); `origin_px`: global map pixel of the
    grid's north-west corner; `bend`: layer -> noise factor (default 1). -> layer -> weights (sum 1 per cell),
    on the same cells. Steps 2-5 of the module docstring. The raw weights' own fractions (the colour split of a
    1997 transition tile) decide only which layer wins a cell."""
    sigma_px = SMOOTH_SIGMA_PX if sigma_px is None else sigma_px
    amplitude = BEND_AMPLITUDE if amplitude is None else amplitude
    feather_px = FEATHER_PX if feather_px is None else feather_px
    max_shift_px = MAX_SHIFT_PX if max_shift_px is None else max_shift_px
    line_radius_px = LINE_RADIUS_PX if line_radius_px is None else line_radius_px
    peak_floor = PEAK_FLOOR if peak_floor is None else peak_floor
    names = sorted(raw)
    if not names:
        return {}
    stack = np.stack([np.asarray(raw[k], dtype=np.float64) for k in names])
    total = stack.sum(axis=0)
    first = np.zeros_like(stack); first[0] = 1.0
    stack = np.where(total > 1e-6, stack / np.maximum(total, 1e-6), first)
    if len(names) == 1:
        return {names[0]: stack[0]}
    h, w = stack.shape[1:]
    labels = np.argmax(stack, axis=0)
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float64)
    gx = origin_px[0] + (gx + 0.5) * CELL_PX
    gy = origin_px[1] + (gy + 0.5) * CELL_PX
    fields = np.stack([blur(stack[i], sigma_px / CELL_PX) for i in range(len(names))])
    # A thin 1997 feature (a ledge line, a narrow path drawn on transition tiles) is split into fragments by the
    # colour split, and its blurred field stays below the ground round it: measure each layer against its own local
    # peak, so a line whose fragments reach PEAK_FLOOR or more runs on as one strip, while a stray speck stays a speck.
    if line_radius_px > 0:
        r = max(1, int(round(line_radius_px / CELL_PX)))
        for i in range(len(names)):
            peak = blur(local_max(fields[i], r), 2.0)
            fields[i] = np.minimum(fields[i] / np.maximum(peak, peak_floor), 1.0)
    # how much the outline may bend here: laid patterns (bend < 1) keep straighter edges against anything
    present = fields > 0.15
    factor = np.ones((h, w))
    for i, k in enumerate(names):
        f = float((bend or {}).get(k, 1.0))
        if f < 1.0:
            factor = np.where(present[i], np.minimum(factor, f), factor)
    norm = sum(a for _, a in BEND_WAVELENGTHS_PX)
    bent = np.empty_like(fields)
    for i, k in enumerate(names):
        noise = sum(a * value_noise(gx, gy, wl, layer_seed(k) + j) for j, (wl, a) in enumerate(BEND_WAVELENGTHS_PX)) / norm
        # a slow octave grows some patches and shrinks others, some away (evenly sized, evenly spaced patches read as
        # a pattern); only for the layers `vary` names (scattered patches, not paths, ledges or the ground round them)
        slow = PATCH_VARIATION * float((vary or {}).get(k, 0.0)) * value_noise(gx, gy, PATCH_WAVELENGTH_PX, layer_seed(k) + 97)
        bent[i] = fields[i] * (1.0 + slow) + amplitude * factor * noise * 4.0 * fields[i] * (1.0 - fields[i])
    bent = np.where(fields > 1e-3, bent, -np.inf)    # a layer that is not there cannot win, however the noise falls
    # `fixed` layers (the water bed: wet sand drawn under the 1997 water tiles) never spread onto other 1997 ground: on
    # land they would show as a dark patch beside the water (726); the water shapes lay the bed to the drawn waterline
    for i, k in enumerate(names):
        if k in fixed:
            bent[i] = np.where(labels == i, bent[i], -np.inf)
    # the new outline: the layer with the largest bent field wins a cell, but only within max_shift_px of a 1997
    # boundary; farther away every cell keeps its 1997 layer
    cap = int(math.ceil(max_shift_px / CELL_PX)) + 2
    dist = boundary_distance_px(labels, cap)
    pick = np.where(np.isfinite(bent).any(axis=0), np.argmax(bent, axis=0), labels)
    won = np.where(dist <= max_shift_px, pick, labels)
    # a 1997 region stays one region and two stay two (keep_connected: necks along a split path's centreline)
    if connected:
        won = keep_connected(won, labels, len(names), region, report, sources=region_sources(stack, labels))
    # feather: the winners' outline blurred (a partition of one: only layers that win a cell nearby get weight)
    sigma = feather_px / CELL_PX
    out = np.stack([blur((won == i).astype(np.float64), sigma) for i in range(len(names))])
    out /= np.maximum(out.sum(axis=0, keepdims=True), 1e-6)
    return {k: out[i] for i, k in enumerate(names)}


# --- connectivity (owner review of 16 Nov 2026: a one-tile path that turns must stay one path) --------------------------
SOURCE_FLOOR = 0.25                # a 1997 region of a layer: cells where its tile weight is at least this (a path drawn
                                   # on transition tiles is one region though its colour split rarely wins a cell)
LOST_MIN_CELLS = 16                # a 1997 region this big (a quarter tile) that no cell wins any more counts as split
NECK_RADIUS_CELLS = 1.6            # half width of the neck restored along a split region's centreline (about 20 px wide)
_N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _shift(a: np.ndarray, dy: int, dx: int, fill) -> np.ndarray:
    h, w = a.shape
    out = np.full_like(a, fill)
    out[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)] = a[max(0, -dy):h + min(0, -dy), max(0, -dx):w + min(0, -dx)]
    return out


def components(mask: np.ndarray) -> np.ndarray:
    """8-connected component labels of a boolean grid (-1 outside the mask; a label is the largest flat index of its
    component). Label propagation, pure numpy."""
    lab = np.where(mask, np.arange(mask.size).reshape(mask.shape), -1)
    while True:
        best = lab.copy()
        for dy, dx in _N8:
            np.maximum(best, _shift(lab, dy, dx, -1), out=best)
        best = np.where(mask, best, -1)
        if np.array_equal(best, lab):
            return lab
        lab = best


def skeleton(mask: np.ndarray) -> np.ndarray:
    """Zhang-Suen thinning of a boolean grid: the centreline of each region, one cell wide, connected as the region is."""
    img = np.pad(mask.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            p = [np.roll(np.roll(img, -dy, 0), -dx, 1) for dy, dx in ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))]
            b = sum(p)
            a = sum(((p[i] == 0) & (p[(i + 1) % 8] == 1)).astype(np.uint8) for i in range(8))
            if step == 0:
                c1 = p[0] * p[2] * p[4]; c2 = p[2] * p[4] * p[6]
            else:
                c1 = p[0] * p[2] * p[6]; c2 = p[0] * p[4] * p[6]
            kill = (img == 1) & (b >= 2) & (b <= 6) & (a == 1) & (c1 == 0) & (c2 == 0)
            if kill.any():
                img[kill] = 0
                changed = True
        if not changed:
            return img[1:-1, 1:-1].astype(bool)


def dilate(mask: np.ndarray, radius_cells: float) -> np.ndarray:
    r = int(math.floor(radius_cells))
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy * dy + dx * dx <= radius_cells * radius_cells:
                out |= _shift(mask, dy, dx, False)
    return out


def connectivity_faults(source: np.ndarray, result: np.ndarray, region: np.ndarray | None = None):
    """For one layer: (split, merged) = source components (1997, 8-connected) whose cells the result's layer cells
    reach as two or more result components; result components that join two or more source components. Only
    components with a cell in `region` count (a screen's own cells)."""
    src, res = components(source), components(result)
    region = np.ones(source.shape, bool) if region is None else region
    split = merged = 0
    both = source & result
    for c in np.unique(src[source & region]):
        parts = np.unique(res[(src == c) & both])
        if len(parts) > 1 or (len(parts) == 0 and int((src == c).sum()) >= LOST_MIN_CELLS):
            split += 1
    for r in np.unique(res[result & region]):
        if len(np.unique(src[(res == r) & both])) > 1:
            merged += 1
    return split, merged


def region_sources(frac: np.ndarray, labels: np.ndarray) -> list:
    """layer -> its 1997 regions: the cells it wins, and for every layer but the screen's ground (the largest) also the
    cells where its tile weight is at least SOURCE_FLOOR (a path drawn on transition tiles is one region)."""
    n = frac.shape[0]
    ground = int(np.argmax(frac.reshape(n, -1).sum(axis=1)))
    # a cell where two features both reach the floor belongs to the stronger (the regions never overlap)
    feat = frac.copy(); feat[ground] = -1.0
    strongest = np.argmax(feat, axis=0)
    out = [(labels == i) | (((frac[i] >= SOURCE_FLOOR) & (strongest == i) & ((labels == i) | (labels == ground))) if i != ground else False)
           for i in range(n)]
    # the ground is what the features leave: a path across a meadow divides it, as the 1997 tiles draw it
    others = np.zeros(labels.shape, bool)
    for i in range(n):
        if i != ground:
            others |= out[i]
    out[ground] = out[ground] & ~others
    return out


def fill_from_neighbours(won: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Give the cells of `mask` the winner of a neighbouring cell outside it, growing inwards."""
    won = won.copy()
    todo = mask.copy()
    for _ in range(max(won.shape)):
        if not todo.any():
            break
        for dy, dx in _N8:
            nb = _shift(won, dy, dx, -1)
            nb_ok = ~_shift(todo, dy, dx, True) & (nb >= 0)
            take = todo & nb_ok
            won[take] = nb[take]
            todo &= ~take
    return won


def keep_connected(won: np.ndarray, labels: np.ndarray, n_layers: int, region: np.ndarray | None = None, report: dict | None = None,
                   no_cut: np.ndarray | None = None, sources: list | None = None):
    """The winners `won` of smooth_fields with every 1997 region (`labels`, 8-connected per layer) still in one piece
    and no two of them joined: a split region gets a neck along its 1997 centreline (skeleton, NECK_RADIUS_CELLS, inside
    the 1997 region, so within the 1997 outline); two regions the smoothing joined are cut apart again on the line where
    the cells nearest to each meet (those cells take their 1997 layer). `report` counts faults before and after."""
    won = won.copy()
    claimed = np.zeros(won.shape, bool)       # necks already laid: a later layer does not paint over them
    srcs = [labels == i if sources is None else sources[i] for i in range(n_layers)]
    for i in sorted(range(n_layers), key=lambda j: int(srcs[j].sum())):     # thin features first
        source = srcs[i]
        if not source.any():
            continue
        before = connectivity_faults(source, won == i, region)
        for _ in range(3):
            src, res = components(source), components(won == i)
            fixed = False
            for c in np.unique(src[source]):
                cmask = src == c
                parts = len(np.unique(res[cmask & (won == i)]))
                if parts > 1 or (parts == 0 and int(cmask.sum()) >= LOST_MIN_CELLS):
                    neck = dilate(skeleton(cmask), NECK_RADIUS_CELLS) & cmask & ~claimed
                    won[neck] = i
                    claimed |= neck
                    # pieces of the layer in this region that still do not touch the neck go (no stray specks)
                    res2 = components(won == i)
                    keep = np.unique(res2[neck])
                    stray = (won == i) & cmask & ~claimed & ~np.isin(res2, keep) & ~np.isin(res2, np.unique(res2[(won == i) & ~cmask]))
                    if stray.any():
                        won = fill_from_neighbours(won, stray)
                    fixed = True
            # joined regions: grow each 1997 region's id through the result's cells, cut where two ids meet
            res = components(won == i)
            for r in np.unique(res[won == i]):
                ids = np.unique(src[(res == r) & source])
                if len(ids) < 2:
                    continue
                rmask = res == r
                own = np.where(rmask & source, src, -1)
                while True:
                    grown = own.copy()
                    for dy, dx in _N8:
                        nb = _shift(own, dy, dx, -1)
                        grown = np.where((grown < 0) & rmask & (nb >= 0), nb, grown)
                    if np.array_equal(grown, own):
                        break
                    own = grown
                cut = np.zeros(won.shape, bool)
                for dy, dx in _N8:
                    nb = _shift(own, dy, dx, -1)
                    cut |= (own >= 0) & (nb >= 0) & (nb != own) & ~source
                cut &= (labels >= 0) & ~claimed
                if no_cut is not None:
                    cut &= ~no_cut
                won[cut] = labels[cut]
                fixed = True
            if not fixed:
                break
        after = connectivity_faults(source, won == i, region)
        if report is not None:
            report["split_before"] = report.get("split_before", 0) + before[0]
            report["merged_before"] = report.get("merged_before", 0) + before[1]
            report["split"] = report.get("split", 0) + after[0]
            report["merged"] = report.get("merged", 0) + after[1]
    return won


def connected_weights(weights: dict, own: dict, margin: float = 0.05, report: dict | None = None) -> dict:
    """The final per-texel weights (layer -> h x w, sum 1) of a screen with keep_connected applied to their winners
    against the screen's own 1997 tile weights (`own`, same grid): where a texel's winner has to change (a neck, a cut),
    the new winner's weight is raised to `margin` above the strongest other layer and the texel renormalised, so the
    written mask's winners keep every 1997 region in one piece and apart from the others. Layers of `own` that the
    weights no longer carry (folded) are not checked."""
    names = sorted(weights)
    stack = np.stack([np.asarray(weights[k], dtype=np.float64) for k in names])
    won = np.argmax(stack, axis=0)
    own_names = sorted(own)
    own_stack = np.stack([np.asarray(own[k], dtype=np.float64) for k in own_names])
    own_stack = own_stack / np.maximum(own_stack.sum(axis=0, keepdims=True), 1e-6)
    src = np.array(own_names)[np.argmax(own_stack, axis=0)]
    labels = np.full(won.shape, -1)
    for i, k in enumerate(names):
        labels[src == k] = i
    own_src = region_sources(own_stack, np.argmax(own_stack, axis=0))
    sources = [own_src[own_names.index(k)] if k in own_names else np.zeros(won.shape, bool) for k in names]
    fixed = keep_connected(won, labels, len(names), None, report, sources=sources)
    for _ in range(4):      # a neck of one layer can cut another: repeat while a region is split (counted once above)
        if not any(connectivity_faults(sources[i], fixed == i)[0] for i in range(len(names)) if sources[i].any()):
            break
        fixed = keep_connected(fixed, labels, len(names), sources=sources)
    change = fixed != won
    if change.any():
        ys, xs = np.nonzero(change)
        for y, x in zip(ys, xs):
            k = fixed[y, x]
            others = np.delete(stack[:, y, x], k)
            stack[k, y, x] = max(stack[k, y, x], float(others.max()) + margin)
        stack /= np.maximum(stack.sum(axis=0, keepdims=True), 1e-6)
    return {k: stack[i] for i, k in enumerate(names)}


def edge_aligned(field: np.ndarray, margin: int, h: int = MASK_H, w: int = MASK_W) -> np.ndarray:
    """Sample a cell-centred window field (the screen's h x w cells with `margin` cells round it) at h x w points
    spread from edge to edge of the screen: texel 0 on the west/north edge, texel w-1/h-1 on the east/south edge."""
    cx = np.arange(w) * (w / (w - 1.0)) - 0.5 + margin
    cy = np.arange(h) * (h / (h - 1.0)) - 0.5 + margin
    x0 = np.clip(np.floor(cx).astype(int), 0, field.shape[1] - 2); fx = cx - x0
    y0 = np.clip(np.floor(cy).astype(int), 0, field.shape[0] - 2); fy = cy - y0
    top = field[y0][:, x0] * (1 - fx) + field[y0][:, x0 + 1] * fx
    bottom = field[y0 + 1][:, x0] * (1 - fx) + field[y0 + 1][:, x0 + 1] * fx
    return top * (1 - fy)[:, None] + bottom * fy[:, None]


def fill_missing(window: np.ndarray, known: np.ndarray) -> np.ndarray:
    """Fill the cells of `window` where `known` is False: first down/up each column from the nearest known cell, then
    along each row. A rule that only looks at the assembled screens (not at which screen the window is for), so two
    screens that share a corner without a diagonal neighbour fill it the same way."""
    out = window.copy()
    have = known.copy()
    for axis in (0, 1):
        n = out.shape[axis]
        pos = np.indices(out.shape)[axis]
        before = np.maximum.accumulate(np.where(have, pos, -1), axis=axis)
        after = np.flip(np.minimum.accumulate(np.flip(np.where(have, pos, n), axis=axis), axis=axis), axis=axis)
        use_before = (before >= 0) & ((after >= n) | (pos - before <= after - pos))
        src = np.where(use_before, before, after)
        ok = ~have & (src >= 0) & (src < n)
        idx = list(np.nonzero(ok))
        other = idx[1 - axis]
        take = (src[ok], other) if axis == 0 else (other, src[ok])
        out[ok] = out[take]
        have = have | ok
    return out


def screen_window(n: int, raw_by_screen: dict, neighbours: dict, margin: int = MARGIN_CELLS) -> dict:
    """layer -> (h + 2 margin) x (w + 2 margin) raw weights of screen n with `margin` cells of its world-adjacent
    neighbours round it (`neighbours`: export_import_bundle.world_neighbours(n)); blocks without a neighbour are
    filled from the assembled screens by one shared rule (fill_missing). A neighbour's layer that screen n lacks
    enters the window with zeros elsewhere."""
    own = raw_by_screen[n]
    h, w = MASK_H, MASK_W
    names = set(own)
    for other in neighbours.values():
        names |= set(raw_by_screen.get(other) or {})
    zero = np.zeros((h, w))
    known = np.zeros((h + 2 * margin, w + 2 * margin), bool)
    known[margin:margin + h, margin:margin + w] = True
    blocks = []
    for (dc, dr), other in neighbours.items():
        grid_set = raw_by_screen.get(other)
        if not grid_set:
            continue
        ys = slice(0, margin) if dr < 0 else slice(margin, margin + h) if dr == 0 else slice(margin + h, h + 2 * margin)
        xs = slice(0, margin) if dc < 0 else slice(margin, margin + w) if dc == 0 else slice(margin + w, w + 2 * margin)
        gy = slice(h - margin, h) if dr < 0 else slice(0, h) if dr == 0 else slice(0, margin)
        gx = slice(w - margin, w) if dc < 0 else slice(0, w) if dc == 0 else slice(0, margin)
        known[ys, xs] = True
        blocks.append((ys, xs, gy, gx, grid_set))
    out = {}
    for k in sorted(names):
        window = np.zeros((h + 2 * margin, w + 2 * margin))
        window[margin:margin + h, margin:margin + w] = own.get(k, zero)
        for ys, xs, gy, gx, grid_set in blocks:
            window[ys, xs] = grid_set.get(k, zero)[gy, gx]
        out[k] = fill_missing(window, known)
    return out


def smooth_screen_layers(n: int, raw_by_screen: dict, neighbours: dict, bend: dict | None = None,
                         min_weight: float = 0.02, vary: dict | None = None, report: dict | None = None, fixed=()) -> dict:
    """layer -> MASK_H x MASK_W edge-aligned natural weights of screen n (sum 1 per texel), computed in world space
    with its neighbours (screen_window, smooth_fields, edge_aligned). Layers that never reach `min_weight` on the
    screen are left out (and their weight shared out among the rest)."""
    m = MARGIN_CELLS
    window = screen_window(n, raw_by_screen, neighbours, m)
    ox, oy = screen_origin_px(n)
    region = np.zeros((MASK_H + 2 * m, MASK_W + 2 * m), bool)
    region[m:m + MASK_H, m:m + MASK_W] = True
    fields = smooth_fields(window, (ox - m * CELL_PX, oy - m * CELL_PX), bend, vary, region=region, report=report, fixed=fixed)
    sampled = {k: edge_aligned(v, m) for k, v in fields.items()}
    keep = {k: v for k, v in sampled.items() if float(v.max()) >= min_weight}
    if not keep:
        keep = {max(sampled, key=lambda k: float(sampled[k].sum())): np.ones((MASK_H, MASK_W))}
    total = sum(keep.values())
    return {k: v / np.maximum(total, 1e-6) for k, v in keep.items()}


def edge_aligned_own(weights: dict) -> dict:
    """The same edge-aligned sampling for a screen that is not smoothed (indoor floors): its own cells, edges
    repeated, so every mask follows one convention."""
    return {k: edge_aligned(np.pad(np.asarray(v, dtype=np.float64), 1, mode="edge"), 1) for k, v in weights.items()}
