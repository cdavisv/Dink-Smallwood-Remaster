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
        self.assertEqual(out, [(1, (293, 202, 407, 206), (293, 152, 407, 206))])

    def test_north_south_wall(self):
        out = M.wall_candidates([wall_row(2, 14, (467, 299, 515, 399), (467, 349, 471, 399))], 2)
        self.assertEqual(out, [(14, (467, 299, 471, 398), (467, 299, 514, 398))])

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
        M.trim_walls(9, [(1, rect, box)], free, owners, set(fill), relaxed, feet, trimmed, kept)
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
