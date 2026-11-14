"""npc_trace_plot.py <out.png> <title> <label=trace.csv> [<label=trace.csv> ...]: per rendered frame, the speed of the shown body
along its scripted heading and the shown facing, for the longest steady walk and the first about-turn of each trace."""
import csv, math, sys
from PIL import Image, ImageDraw, ImageFont
out, title = sys.argv[1], sys.argv[2]; traces = [a.split('=', 1) for a in sys.argv[3:]]
F = ImageFont.load_default(size=15); FS = ImageFont.load_default(size=13)
W, PH, M = 1500, 250, 60
def load(fn):
    R = list(csv.DictReader(open(fn))); h = R[0]['handle']; return [r for r in R if r['handle'] == h]
def f(r, k): return float(r[k])
def walk_stretch(R):
    best = (0, 0); i = 0
    while i < len(R):
        j = i
        while j < len(R) and R[j]['action'] == '2' and R[j]['dir'] == R[i]['dir'] and R[i]['action'] == '2': j += 1
        if j - i > best[1] - best[0]: best = (i, j)
        i = max(j, i + 1)
    return best
def along(R, i0, i1):
    hx = f(R[i1 - 1], 'actor_x') - f(R[i0], 'actor_x'); hy = f(R[i1 - 1], 'actor_y') - f(R[i0], 'actor_y'); n = math.hypot(hx, hy) or 1; hx /= n; hy /= n
    return [((f(R[i], 'body_x') - f(R[i - 1], 'body_x')) * hx + (f(R[i], 'body_y') - f(R[i - 1], 'body_y')) * hy) / max(1e-4, f(R[i], 'dt')) for i in range(i0 + 1, i1)]
def turn_window(R):
    for i in range(1, len(R)):
        d = abs((f(R[i], 'actor_yaw') - f(R[i - 1], 'actor_yaw') + 180) % 360 - 180)
        if d > 120 and i > 30 and i + 60 < len(R): return i - 20, i + 60
    for i in range(1, len(R)):
        d = abs((f(R[i], 'actor_yaw') - f(R[i - 1], 'actor_yaw') + 180) % 360 - 180)
        if d > 60 and i > 30 and i + 60 < len(R): return i - 20, i + 60
    return None
def unwrap(a):
    o = [a[0]]
    for v in a[1:]: o.append(o[-1] + ((v - o[-1] + 180) % 360 - 180))
    return o
panels = []
for label, fn in traces:
    R = load(fn); i0, i1 = walk_stretch(R); i0 += 30; i1 = min(i1, i0 + 150)
    panels.append(('%s: speed of the shown body along her walk, cm/s per rendered frame (a steady stretch of %d frames)' % (label, i1 - i0 - 1), along(R, i0, i1), (-450, 500), [0, 120]))
    tw = turn_window(R)
    if tw:
        y0_ = f(R[tw[0]], 'body_yaw')
        panels.append(('%s: how far the shown body has turned from its old facing through a scripted about-turn, degrees per rendered frame' % label,
                       [abs((f(r, 'body_yaw') - y0_ + 180) % 360 - 180) for r in R[tw[0]:tw[1]]], (0, 190), [90, 180]))
im = Image.new('RGB', (W, 40 + len(panels) * (PH + 50)), (250, 250, 248)); d = ImageDraw.Draw(im); d.text((M, 10), title, fill=(20, 20, 20), font=F)
for k, (name, ys, rng, marks) in enumerate(panels):
    y0 = 40 + k * (PH + 50) + 26; d.text((M, y0 - 22), name, fill=(40, 40, 40), font=FS)
    lo, hi = rng if rng else (min(ys) - 10, max(ys) + 10)
    d.rectangle((M, y0, W - 20, y0 + PH), outline=(150, 150, 150))
    def Y(v): return y0 + PH - (min(max(v, lo), hi) - lo) / (hi - lo) * PH
    for mk in marks + [lo, hi]:
        d.line((M, Y(mk), W - 20, Y(mk)), fill=(205, 205, 205)); d.text((8, Y(mk) - 8), '%g' % mk, fill=(90, 90, 90), font=FS)
    n = len(ys); X = lambda i: M + 6 + i * (W - 32 - M) / max(1, n - 1)
    col = (190, 40, 30) if ('before' in name.lower() or 'off' in name.lower()) else (20, 110, 60)
    for i in range(1, n): d.line((X(i - 1), Y(ys[i - 1]), X(i), Y(ys[i])), fill=col, width=2)
    for i in range(n): d.ellipse((X(i) - 2, Y(ys[i]) - 2, X(i) + 2, Y(ys[i]) + 2), fill=col)
im.save(out); print(out, im.size)
