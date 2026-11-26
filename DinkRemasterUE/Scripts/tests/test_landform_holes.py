"""A10 (25 Nov 2026): Content/Dink/Data/Environment/landform_holes.json, the openings in the landforms' drawn ground
(format: doc/remaster/LANDFORM_HOLES.md). Rows are written by hand by the art side; this keeps every row loadable."""
import json
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
ENV = PROJECT / 'Content/Dink/Data/Environment'


class LandformHolesTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ENV / 'landform_holes.json').read_text())
        self.screens = {row['screen']: row for row in json.loads((ENV / 'landforms.json').read_text())['screens']}

    def test_schema(self):
        self.assertEqual(self.data['schema'], 'dink-landform-holes/1')
        self.assertIsInstance(self.data['holes'], list)

    def test_rows(self):
        ids = set()
        for row in self.data['holes']:
            name = row.get('id', '?')
            self.assertIsInstance(row.get('id'), str, 'every row has an id (the placement it opens, e.g. S089_P12)')
            self.assertNotIn(row['id'], ids, 'ids are unique')
            ids.add(row['id'])
            self.assertIn(row.get('screen'), self.screens, f'{name}: its screen has no landforms (flat ground sheets: nothing to open)')
            points = row.get('polygon_px')
            self.assertIsInstance(points, list, name)
            self.assertGreaterEqual(len(points), 3, f'{name}: a polygon needs three points or more')
            for p in points:
                self.assertEqual(len(p), 2, f'{name}: a point is [x, y]')
                self.assertTrue(0 <= p[0] <= 600 and 0 <= p[1] <= 400, f'{name}: {p} lies outside the 600 x 400 map screen')
            area = 0.5 * abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1])))
            self.assertGreater(area, 25.0, f'{name}: the polygon is smaller than a 5 px cell (cuts nothing at the near mesh step)')
            if 'floor_cm' in row:
                self.assertIsInstance(row['floor_cm'], (int, float), name)
                self.assertTrue(-500 <= row['floor_cm'] <= 900, f'{name}: floor_cm out of range')


if __name__ == '__main__':
    unittest.main()
