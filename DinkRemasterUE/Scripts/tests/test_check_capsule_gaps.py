"""Scripts/check_capsule_gaps.py (world-scale audit, 26 Nov 2026): where Dink's 28 cm capsule fits 1997 walkable ground at the reference
and at the enlarged layout scale, closed pockets (sealed in play), joins, and the shipped sealed_gaps.json."""
from pathlib import Path
import json
import sys
import unittest

import numpy as np

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Scripts'))
import check_capsule_gaps as G  # noqa: E402

REF = np.diag([0.0688, 0.0688])   # SCR_190 at the reference scale (m per px)
NEW = np.diag([0.0900, 0.0900])   # and at the enlarged one


def slit_screen():
    """SCR_190's pattern: two low lines (y 244-245, 254-255) with an 8 px slit between, closed at both ends; open floor below."""
    m = np.zeros((G.H, G.W), dtype=bool)
    m[244:246, 0:300] = True
    m[254:256, 0:300] = True
    m[246:254, 0:2] = True
    m[246:254, 298:300] = True
    m[0:2, :] = m[-2:, :] = True
    m[:, 0:2] |= True
    m[:, -2:] = True
    return m


class CapsuleFit(unittest.TestCase):
    def test_offsets_grow_with_fewer_cm_per_pixel(self):
        a, _ = G.disc_offsets(REF, 0.28)
        b, _ = G.disc_offsets(NEW, 0.28)
        self.assertGreater(len(a), len(b))
        self.assertIn((0, 0), b)
        self.assertNotIn((5, 0), b)   # 4.5 px = 40.5 cm from the centre: out of the capsule

    def test_slit_fits_only_at_the_enlarged_scale(self):
        blocked = {5: slit_screen()}
        lay_r, lay_n = {5: ('s', REF)}, {5: ('s', NEW)}
        self.assertFalse(G.capsule_fit(5, blocked, lay_r, 0.28)[246:254, 50:250].any())
        self.assertTrue(G.capsule_fit(5, blocked, lay_n, 0.28)[249:251, 50:250].all())

    def test_rows_to_rects(self):
        m = np.zeros((5, 10), dtype=bool)
        m[1:3, 2:6] = True
        m[3, 2:4] = True
        self.assertEqual(G.rows_to_rects(m), [[2, 1, 5, 2], [2, 3, 3, 3]])


class Pockets(unittest.TestCase):
    def run_audit(self, sealed=None):
        blocked = {5: slit_screen()}
        return G.audit_gaps(blocked, {5: ('s', REF)}, {5: ('s', NEW)}, 0.28, sealed=sealed)

    def test_closed_pocket_is_found(self):
        pockets = [f for f in self.run_audit() if f['kind'] == 'pocket']
        self.assertEqual(len(pockets), 1)
        self.assertTrue(pockets[0]['closed'])
        self.assertFalse(pockets[0]['sealed'])
        l, t, r, b = pockets[0]['screens'][5]
        self.assertTrue(t >= 246 and b <= 253 and l >= 2 and r <= 297)

    def test_sealed_rect_covers_it(self):
        pockets = [f for f in self.run_audit({5: [(2, 246, 297, 253)]}) if f['kind'] == 'pocket']
        self.assertTrue(pockets[0]['sealed'])

    def test_open_end_makes_it_a_join_not_a_pocket(self):
        # open the slit's east end onto the floor below and above: point Dink walks it in 1997, the capsule only at the enlarged scale
        m = slit_screen()
        m[246:254, 298:300] = False
        m[244:246, 280:300] = False
        m[254:256, 280:300] = False
        m[244:256, 300:] = False
        m[200:300, 300:302] = True   # a wall east of the slit's mouth so north and south meet only through the slit
        m[244:256, 300:302] = False
        blocked = {5: m}
        found = G.audit_gaps(blocked, {5: ('s', REF)}, {5: ('s', NEW)}, 0.28)
        self.assertFalse([f for f in found if f['kind'] == 'pocket' and f['closed']])


class ShippedSeals(unittest.TestCase):
    def test_sealed_gaps_json(self):
        d = json.loads((PROJECT / 'Content' / 'Dink' / 'Data' / 'Play' / 'sealed_gaps.json').read_text(encoding='utf-8'))
        self.assertEqual(d['schema'], 'dink-sealed-gaps/1')
        self.assertIn('190', d['screens'])
        self.assertIn('189', d['screens'])
        for s, rows in d['screens'].items():
            self.assertTrue(1 <= int(s) <= 768)
            for r in rows:
                l, t, rr, b = r['rect']
                self.assertTrue(0 <= l <= rr < G.W and 0 <= t <= b < G.H, (s, r))
                self.assertTrue(r['why'])


if __name__ == '__main__':
    unittest.main()
