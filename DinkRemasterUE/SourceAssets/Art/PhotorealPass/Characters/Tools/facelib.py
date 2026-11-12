"""facelib: landmark-relative head reshaping that keeps vertex order, UVs, weights and the neck seam.
ops (JSON lists), positions in metres relative to the nose tip ('o': 'nose', default) or to each eye centre ('o': 'eye'),
scaled by the head's eye spacing; x is mirrored for the second side when 'sym' is true (default):
  {"t": "n", "p": [x, y, z], "r": r, "a": amount}                 move along the vertex normal (gaussian blob)
  {"t": "m", "p": [x, y, z], "r": r, "d": [dx, dy, dz]}           translate (dx mirrors with the side)
  {"t": "s", "p": [x, y, z], "r": [rx, ry, rz], "k": [sx, sy, sz]} scale about p with an anisotropic gaussian weight
'eye': true lets an op move the eyelids; otherwise the eye sockets are protected so the eyeballs keep fitting."""
import numpy as np
def reshape(co, vn, nose, eyes, ops, head_mask, log=print):
    co = co.copy(); k = abs(eyes[1][0][0]) / .031; out = co.copy()
    neck = np.clip((co[:, 2] - (nose[2] - .175 * k)) / (.05 * k), 0, 1); neck = neck * neck * (3 - 2 * neck)
    prot = np.ones(len(co))
    for sgn in (1, -1):
        e = eyes[sgn][0]; prot *= 1 - np.exp(-(((co - e) ** 2).sum(1)) / (.0155 * k) ** 2)
    for op in ops:
        sides = (1, -1) if op.get('sym', True) and (abs(op['p'][0]) > 1e-9 or op.get('o') == 'eye') else (1,)
        for sgn in sides:
            org = nose if op.get('o', 'nose') == 'nose' else eyes[sgn][0]
            p = np.array(op['p'], float) * k
            if op.get('o') != 'eye': p[0] *= sgn
            else: p[0] *= sgn
            c = org + p; w0 = head_mask * neck * (1.0 if op.get('eye') else prot)
            if op.get('side') and sgn != op['side']: continue
            if op['t'] == 's':
                r = np.array(op['r'], float) * k; w = np.exp(-(((out - c) / r) ** 2).sum(1)) * w0
                out = out + (out - c) * (np.array(op['k'], float) - 1)[None, :] * w[:, None]
            else:
                r = op['r'] * k; w = np.exp(-(((out - c) ** 2).sum(1)) / r ** 2) * w0
                if op['t'] == 'n': out = out + vn * (w * op['a'] * k)[:, None]
                else:
                    d = np.array(op['d'], float) * k; d[0] *= sgn; out = out + d[None, :] * w[:, None]
    log('face2 ops', len(ops), 'max displacement mm', float(np.linalg.norm(out - co, axis=1).max() * 1000))
    return out
