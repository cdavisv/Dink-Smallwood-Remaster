"""Checks the hand-classification tables against a fresh scan of bin/dink.

Run: cd tools/data && python3 -m unittest discover -s tests
"""
import csv
import os
import re
import sys
import unittest
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(DATA, 'scripts'))

import dinkdata as d  # noqa: E402
import sprite_labels  # noqa: E402
import tile_labels  # noqa: E402

SNAKE = re.compile(r'^[a-z][a-z0-9_]*$')
CONF = {'high', 'medium', 'low'}


def read(name):
    with open(os.path.join(DATA, name), newline='') as f:
        return list(csv.DictReader(f))


class Scan:
    tiles = None
    pairs = None
    nplace = None
    nscreens = None

    @classmethod
    def get(cls):
        if cls.tiles is None:
            cls.tiles = Counter()
            cls.nscreens = 0
            for _n, blk, _ in d.iter_screens():
                cls.nscreens += 1
                cls.tiles.update(d.screen_tiles(blk))
            P = d.all_placements()
            cls.nplace = len(P)
            cls.pairs = Counter((p.seq, p.frame) for p in P)
            cls.types = Counter(((p.seq, p.frame), p.type) for p in P)
        return cls


class TestData(unittest.TestCase):
    def test_known_totals(self):
        s = Scan.get()
        self.assertEqual(s.nscreens, 644)
        self.assertEqual(sum(s.tiles.values()), 644 * 96)
        self.assertEqual(s.nplace, 5846)
        self.assertEqual(len(s.pairs), 559)


class TestTileTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read('tile_classes.csv')
        cls.scan = Scan.get()

    def test_one_row_per_used_tile(self):
        nums = [int(r['tile_num']) for r in self.rows]
        self.assertEqual(len(nums), len(set(nums)), 'duplicate tile rows')
        self.assertEqual(set(nums), set(self.scan.tiles))

    def test_counts_match_scan_and_total(self):
        for r in self.rows:
            self.assertEqual(int(r['use_count']), self.scan.tiles[int(r['tile_num'])], r['tile_num'])
        self.assertEqual(sum(int(r['use_count']) for r in self.rows), 644 * 96)

    def test_tileset_cell(self):
        for r in self.rows:
            n = int(r['tile_num'])
            self.assertEqual(int(r['tileset']), n // 128 + 1)
            self.assertEqual(int(r['cell']), n % 128)

    def test_vocabulary(self):
        for r in self.rows:
            self.assertIn(r['terrain'], tile_labels.TERRAIN, r['tile_num'])
            self.assertIn(r['walkable_hint'], {'yes', 'no', 'partial'})
            self.assertIn(r['confidence'], CONF)
            self.assertIn(r['is_transition'], {'0', '1'})
            if r['is_transition'] == '1':
                a, b = r['blend_classes'].split('|')
                self.assertEqual(a, r['terrain'])
                self.assertIn(b, tile_labels.TERRAIN)
                self.assertNotEqual(a, b)
            else:
                self.assertEqual(r['blend_classes'], '')

    def test_animated_ranges(self):
        for r in self.rows:
            n = int(r['tile_num'])
            exp = 'water' if 896 <= n <= 1023 else ('fire' if 2304 <= n <= 2431 else '')
            self.assertEqual(r['animated'], exp)


class TestSpriteTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read('sprite_classes.csv')
        cls.scan = Scan.get()

    def test_one_row_per_placed_pair(self):
        keys = [(int(r['seq']), int(r['frame'])) for r in self.rows]
        self.assertEqual(len(keys), len(set(keys)), 'duplicate sprite rows')
        self.assertEqual(set(keys), set(self.scan.pairs))

    def test_counts(self):
        tot = 0
        for r in self.rows:
            k = (int(r['seq']), int(r['frame']))
            n = int(r['placement_count'])
            self.assertEqual(n, self.scan.pairs[k])
            by_type = [int(r['type0_background']), int(r['type1_live']), int(r['type2_hardness_only'])]
            self.assertEqual(sum(by_type), n, k)
            for t in range(3):
                self.assertEqual(by_type[t], self.scan.types.get((k, t), 0))
            tot += n
        self.assertEqual(tot, 5846)

    def test_sorted_by_placement_count(self):
        c = [int(r['placement_count']) for r in self.rows]
        self.assertEqual(c, sorted(c, reverse=True))

    def test_vocabulary(self):
        for r in self.rows:
            k = (r['seq'], r['frame'])
            self.assertIn(r['category'], sprite_labels.CATEGORIES, k)
            self.assertIn(r['treatment'], sprite_labels.TREATMENTS, k)
            self.assertRegex(r['class_id'], SNAKE)
            self.assertIn(r['confidence'], CONF)
            self.assertTrue(r['name'], k)
            if r['family']:
                self.assertRegex(r['family'], SNAKE)

    def test_class_id_consistent(self):
        """A class_id must always map to one category and one treatment."""
        seen = {}
        for r in self.rows:
            v = (r['category'], r['treatment'])
            self.assertEqual(seen.setdefault(r['class_id'], v), v, r['class_id'])

    def test_sources_resolved(self):
        for r in self.rows:
            if r['seq'] == '0':
                continue
            self.assertTrue(r['source_file'], (r['seq'], r['frame']))
            self.assertRegex(r['pixel_size'], r'^\d+x\d+$')


if __name__ == '__main__':
    unittest.main()
