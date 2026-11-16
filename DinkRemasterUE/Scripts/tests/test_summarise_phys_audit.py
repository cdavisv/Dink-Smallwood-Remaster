"""Scripts/summarise_phys_audit.py (physical mapping audit, 15 Nov 2026): the 1997 reach arithmetic and the mask decoding."""
import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import summarise_phys_audit as spa  # noqa: E402


class ReachTests(unittest.TestCase):
    def test_bare_hands_body_as_wide_as_the_box(self):
        # range 0 (fists): Dink's centre may stand 5 + 28 px west of the box; at 2.5 cm/px that is 82.5 cm, the fist reaches
        # 28 + 85 cm: the hit lands 30.5 cm inside before it registers
        far, miss = spa.attack_gaps((100, 100, 140, 120), (100, 100, 140, 120), 2.5, rng=0)['W']
        self.assertAlmostEqual(far, 0.0)
        self.assertAlmostEqual(miss, 113.0 - 33 * 2.5)

    def test_sword_range_40(self):
        # a sword (sp_range 40, item-sw1.c:42): 5 + 40 px registered; reach 28 + 85 * 40 / 28 cm
        g = spa.attack_gaps((0, 0, 10, 10), (0, 0, 10, 10), 1.0)
        reach = 28.0 + 85.0 * 40 / 28
        self.assertAlmostEqual(g['W'][1], reach - 45)
        self.assertAlmostEqual(g['E'][1], reach - 45)
        self.assertAlmostEqual(g['N'][1], reach - (5 + 40 + 6))
        self.assertAlmostEqual(g['S'][1], reach - (10 + 40 + 6))

    def test_small_body_in_a_big_box_hits_from_far(self):
        # a body 10 px wide in the middle of a 60 px box at 7 cm/px, sword: hit from (25 + 45) px * 7 cm west of the body
        far, miss = spa.attack_gaps((100, 100, 160, 120), (125, 100, 135, 120), 7.0)['W']
        self.assertAlmostEqual(far, (25 + 45) * 7.0 - (28.0 + 85.0 * 40 / 28))
        self.assertEqual(miss, 0.0)

    def test_touch_box_of_a_matching_pickup(self):
        far, miss = spa.touch_gaps((100, 100, 110, 110), (100, 100, 110, 110), 2.8)
        self.assertEqual(miss, 0.0)
        self.assertLessEqual(far, 2 * 2.8 + 2.8)


class DecodeTests(unittest.TestCase):
    def test_rle(self):
        self.assertEqual(''.join(spa.rle_decode('3F2BF')), 'FFFBBF')

    def test_end_to_end_on_a_tiny_audit(self):
        with tempfile.TemporaryDirectory() as d:
            header = None
            import importlib
            spa_mod = importlib.reload(spa)
            cols = ('screen,origin,handle,type,live,brain,script,seq,frame,size,touch_damage,nohit,warp,hard_flag,authored,fitted,class,'
                    'sprite_x,sprite_y,box_l,box_t,box_r,box_b,stamped_px,bare_stamped_px,cm_per_px,items,kinds,mesh,visible,'
                    'own_px,own_l,own_t,own_r,own_b,own_cx,own_cy,cover_own,overhang_own,iou_own,offset_x,offset_y,max_bare_px,cover_all,'
                    'body_px,body_l,body_t,body_r,body_b,inside_other,capsule_blocked,actor_dx,actor_dy').split(',')
            row = dict.fromkeys(cols, '0')
            row.update(screen='5', origin='S005_P01', type='0', **{'class': 'background'}, box_l='10', box_t='10', box_r='29', box_b='19',
                       stamped_px='200', bare_stamped_px='200', cm_per_px='6.9', kinds='', mesh='', max_bare_px='20', script='', inside_other='')
            with open(os.path.join(d, 'phys_origins.csv'), 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                w.writerow(row)
            spa_mod.main([d, '--out', d, '--repo', d])
            text = Path(d, 'phys_summary.md').read_text()
            # no 1997 hardness under --repo for a made-up screen: counted, nothing measurable at its contact edge
            self.assertIn('Sprite hardboxes: checked 1', text)
            self.assertIn('drawn by a mesh 0, card only 0, body 0, nothing 1', text)


if __name__ == '__main__':
    unittest.main()
