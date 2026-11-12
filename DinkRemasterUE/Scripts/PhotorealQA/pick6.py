#!/usr/bin/env python3
"""pick6.py <out dir> <prefix> [name substrings...]: a capture script made of the ingame5 camera blocks whose shot name
contains one of the substrings (all when none given). Sources: ingame5a.txt, ingame5b.txt. Prints the script."""
import sys, os, re
here = os.path.dirname(os.path.abspath(__file__))
out, prefix, picks = sys.argv[1], sys.argv[2], sys.argv[3:]
def blocks(path):
    lines = open(path).read().split('\n')
    head, cur, res, seen_head = [], [], [], False
    for l in lines:
        if not seen_head:
            head.append(l)
            if l.startswith('r.VSync'): seen_head = True
            continue
        cur.append(l)
        if l.startswith('shot '):
            res.append(cur); cur = []
    return head, res, cur
head, a, _ = blocks(os.path.join(here, 'ingame5a.txt'))
_, b, tail = blocks(os.path.join(here, 'ingame5b.txt'))
print('\n'.join(head))
for blk in a:
    name = os.path.basename(blk[-1].split(' ', 1)[1])[:-4]
    if picks and not any(p in name for p in picks): continue
    for l in blk:
        if l.startswith('shot '): l = 'shot %s/%s%s.png' % (out, prefix, name)
        if l.startswith('fps '): l = 'fps %s%s' % (prefix, name)
        print(l)
print('wait 1\nquit')
