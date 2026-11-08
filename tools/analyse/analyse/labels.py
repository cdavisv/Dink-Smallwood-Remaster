"""4-connected component labelling of a boolean image with numpy only.

Works on horizontal runs: runs in adjacent rows that overlap are joined, then
labels are settled by min-propagation with pointer jumping. Labels are
renumbered 1..n in raster order of each component's first pixel (so they are
deterministic); 0 means "not in the mask".
"""

import numpy as np


def runs(mask):
    """Return (row, start, end) int arrays of the True runs, end exclusive."""
    h, w = mask.shape
    pad = np.zeros((h, w + 2), dtype=np.int8)
    pad[:, 1:-1] = mask
    d = np.diff(pad, axis=1)
    rs, ss = np.nonzero(d == 1)
    re_, es = np.nonzero(d == -1)
    # nonzero is row-major so both lists are in (row, col) order and pair up
    assert np.array_equal(rs, re_)
    return rs.astype(np.int64), ss.astype(np.int64), es.astype(np.int64)


def label(mask):
    """Return (labels int32 image, count)."""
    h, w = mask.shape
    r, s, e = runs(mask)
    n = len(r)
    if n == 0:
        return np.zeros((h, w), np.int32), 0
    K = 1 << 12
    key_start = r * K + s
    key_end = r * K + e
    # for run i in row y: candidate runs j in row y+1 with end_j > start_i and start_j < end_i
    lo = np.searchsorted(key_end, (r + 1) * K + s, side="right")
    hi = np.searchsorted(key_start, (r + 1) * K + e, side="left")
    cnt = np.maximum(hi - lo, 0)
    a = np.repeat(np.arange(n), cnt)
    off = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
    b = np.repeat(lo, cnt) + off
    lab = np.arange(n)
    if len(a):
        while True:
            m = np.minimum(lab[a], lab[b])
            new = lab.copy()
            np.minimum.at(new, a, m)
            np.minimum.at(new, b, m)
            for _ in range(8):
                new = new[new]
            if np.array_equal(new, lab):
                break
            lab = new
    roots, inv = np.unique(lab, return_inverse=True)
    # roots are min run indices = raster order of first pixel
    runlab = (inv + 1).astype(np.int32)
    img = np.zeros(h * w, np.int32)
    lens = e - s
    flat_start = r * w + s
    idx = np.repeat(flat_start - np.cumsum(lens) + lens, lens) + np.arange(lens.sum())
    img[idx] = np.repeat(runlab, lens)
    return img.reshape(h, w), len(roots)
