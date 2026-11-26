"""Scripts/make_relaxed_hardboxes.py (physical play layer): the wall trim of A71, the audit tiles of A92 and the passage rule they share.
A trimmed wall keeps a strip that still parts the rooms on its two sides; a freed piece that would join two rooms keeps the whole box."""
from pathlib import Path
import csv
import os
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Scripts'))
import make_relaxed_hardboxes as M  # noqa: E402


def wall_row(screen, n, box, own, mesh='SM_Wall_Plaster_Straight_A', **kw):
    r = {'kinds': 'family', 'mesh': '/Game/X/%s.%s' % (mesh, mesh), 'script': '', 'warp': '0', 'type': '1', 'stamped_px': '100',
         'origin': 'S%03d_P%02d' % (screen, n)}
    r.update({k: str(v) for k, v in zip(('box_l', 'box_t', 'box_r', 'box_b'), box)})
    r.update({k: str(v) for k, v in zip(('own_l', 'own_t', 'own_r', 'own_b'), own)})
    r.update(kw)
    return r


def grid_with_box(box):
    """A 600 x 400 px screen (3 px cells) that is all walkable but the box's cells, which belong to placement 1."""
    l, t, r, b = box
    free = [[True] * M.GW for _ in range(M.GH)]
    owners = {1: []}
    for y in range(M.GH):
        for x in range(M.GW):
            px, py = x * M.CELL + 1, y * M.CELL + 1
            if l <= px < r and t <= py < b:
                free[y][x] = False
                owners[1].append((x, y))
    return free, owners


class WallCandidates(unittest.TestCase):
    def test_strip_runs_on_to_the_box_ends(self):
        # an east-west wall drawn on rows 202-206 of a box 293-408 x 152-207 (S003_P01's numbers)
        out = M.wall_candidates([wall_row(3, 1, (293, 152, 408, 207), (300, 202, 400, 206))], 3)
        self.assertEqual(out, [(1, (293, 202, 407, 206), (293, 152, 407, 206), (300, 202, 400, 206))])

    def test_north_south_wall(self):
        out = M.wall_candidates([wall_row(2, 14, (467, 299, 515, 399), (467, 349, 471, 399))], 2)
        self.assertEqual(out, [(14, (467, 299, 471, 398), (467, 299, 514, 398), (467, 349, 471, 399))])

    def test_left_alone(self):
        rows = [wall_row(3, 1, (0, 0, 100, 100), (10, 10, 90, 90)),                       # not a strip (a curve, a post)
                wall_row(3, 2, (0, 0, 100, 50), (0, 40, 100, 44), script='s3-door'),      # scripted
                wall_row(3, 3, (0, 0, 100, 50), (0, 40, 100, 44), warp='1'),              # a warp
                wall_row(3, 4, (0, 0, 100, 50), (0, 40, 100, 44), mesh='SM_Pine_Big'),    # not a wall
                wall_row(4, 5, (0, 0, 100, 50), (0, 40, 100, 44))]                        # another screen's placement
        self.assertEqual(M.wall_candidates(rows, 3), [])


class TrimWalls(unittest.TestCase):
    def run_trim(self, box, rect, fill=()):
        free, owners = grid_with_box(box)
        relaxed, feet, trimmed, kept = {}, {}, {}, []
        M.trim_walls(9, [(1, rect, box, rect)], free, owners, set(fill), relaxed, feet, trimmed, kept)
        return relaxed, feet, trimmed, kept

    def test_partition_between_two_rooms_is_trimmed(self):
        # a wall across the whole screen parts north from south; its strip still does after the trim
        relaxed, feet, trimmed, kept = self.run_trim((0, 150, 600, 210), (0, 200, 599, 204))
        self.assertEqual(list(trimmed.get('9', {})), ['1'])
        self.assertEqual(feet['9']['1'], [0, 200, 599, 204])
        self.assertEqual(kept, [])

    def test_a_short_strip_that_leaves_a_gap_keeps_the_box(self):
        # the strip does not reach the screen's east end: the freed cells beside it join the two rooms
        relaxed, feet, trimmed, kept = self.run_trim((0, 150, 600, 210), (0, 200, 400, 204))
        self.assertEqual(trimmed, {})
        self.assertEqual(len(kept), 1)

    def test_void_is_nobodys_ground(self):
        # north of the wall is the void round the room (an export fill): freeing towards it joins nothing
        fill = [(x, y) for y in range(0, 50) for x in range(M.GW)]
        relaxed, feet, trimmed, kept = self.run_trim((0, 150, 600, 210), (0, 150, 599, 154), fill)
        self.assertEqual(list(trimmed.get('9', {})), ['1'])


class WallJoints(unittest.TestCase):
    """SCR_713 at the enlarged scale (26 Nov 2026): P06 drawn at y 206-213 in its box x 145-271, P13 drawn at y 222-229 in its box x 246-369,
    both boxes y 190-250; the boxes overlap at x 246-271, where P13's box owns the pixels. Trimming both opened the slot between the strips."""
    WALLS = [(13, (246, 222, 369, 229), (246, 190, 369, 250), (258, 222, 357, 229)),
             (6, (145, 206, 271, 213), (145, 190, 271, 250), (158, 206, 257, 213))]

    def grid(self):
        # a corridor wall across the whole screen: west of P06 and east of P13 the line is closed by other (kept) boxes
        free = [[True] * M.GW for _ in range(M.GH)]
        owners = {6: [], 13: [], 99: []}
        for y in range(M.GH):
            for x in range(M.GW):
                px, py = x * M.CELL + 1, y * M.CELL + 1
                if 190 <= py <= 250:
                    free[y][x] = False
                    owners[13 if 246 <= px <= 369 else 6 if 145 <= px <= 245 else 99].append((x, y))
        return free, owners

    def test_joint_rects(self):
        out = M.wall_joints(6, self.WALLS, {'13': [246, 190, 369, 250]})
        self.assertIn((246, 206, 257, 213), out)   # P06's drawn end over P13's box
        self.assertIn((258, 222, 271, 229), out)   # P13's drawn start over the overlap
        self.assertIn((257, 213, 259, 222), out)   # the plug across the slot where the modules meet
        self.assertEqual(M.wall_joints(6, self.WALLS, {}), [])  # no trimmed neighbour: nothing to join

    def test_aligned_strips_need_no_joint(self):
        walls = [(13, (246, 206, 369, 213), (246, 190, 369, 250), (258, 206, 357, 213)), self.WALLS[1]]
        self.assertEqual(M.wall_joints(6, walls, {'13': [1]}), [])

    def test_staggered_wall_is_trimmed_with_a_joint_that_closes_the_slot(self):
        free, owners = self.grid()
        relaxed, feet, trimmed, kept, joints = {}, {}, {}, [], {}
        M.trim_walls(713, self.WALLS, free, owners, set(), relaxed, feet, trimmed, kept, joints)
        self.assertEqual(sorted(trimmed['713']), ['13', '6'])
        self.assertEqual(kept, [])
        self.assertEqual(len(joints['713']), 3)
        # replay the play hardness on 1 px: box pixels stay where a feet strip or a joint covers them; the south side of the line must
        # not reach the north side
        H, Wd = 400, 600
        solid = [[False] * Wd for _ in range(H)]
        keep = [tuple(feet['713'][k]) for k in feet['713']] + [tuple(j) for j in joints['713']]
        for y in range(190, 251):
            for x in range(Wd):
                if not (145 <= x <= 369) or any(l <= x <= r and t <= y <= b for l, t, r, b in keep):
                    solid[y][x] = True
        seen, stack = {(200, 240)}, [(200, 240)]
        while stack:
            x, y = stack.pop()
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= q[0] < Wd and 189 <= q[1] < 252 and q not in seen and not solid[q[1]][q[0]]:
                    seen.add(q)
                    stack.append(q)
        self.assertNotIn((300, 196), seen)
        self.assertIn((250, 217), seen)   # the slot's west part is the south side's nook

    def test_without_joints_the_staggered_wall_keeps_its_box(self):
        free, owners = self.grid()
        relaxed, feet, trimmed, kept = {}, {}, {}, []
        M.trim_walls(713, self.WALLS, free, owners, set(), relaxed, feet, trimmed, kept)
        self.assertEqual(list(trimmed['713']), ['13'])
        self.assertEqual([k['origin'] for k in kept], ['S713_P06'])


class AuditTiles(unittest.TestCase):
    def test_reads_low_tiles_above_the_share(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'phys_mismatches.csv'), 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['category', 'severity', 'screen', 'subject', 'detail'])
                w.writerow(['1 invisible wall (tile low)', '1', '31', 'tile 3,2', 'grass tile: Dink stops up to 900 cm (p90) from anything drawn on 100% of 120 px of contact edge'])
                w.writerow(['1 invisible wall (tile low)', '1', '31', 'tile 4,2', 'grass tile: Dink stops up to 900 cm (p90) from anything drawn on 60% of 120 px of contact edge'])
                w.writerow(['1 invisible wall (tile solid)', '1', '31', 'tile 5,2', 'snow tile: Dink stops up to 900 cm (p90) from anything drawn on 100% of 120 px of contact edge'])
            self.assertEqual(M.read_audit_tiles(d, 0.9), {31: {2 * 12 + 3}})


if __name__ == '__main__':
    unittest.main()
