"""Placements cut because the 1997 engine never drew them (art row DS-06, Scripts/art_coverage.py NEVER_DRAWN).

get_box clips a sprite to the play field, which starts 20 px in from the window's left edge, and skips the sprite when
its right edge lies left of that (source/dink/dink.cpp:3170 and 3317, `if (pDstRect->right-1 < mplayl) goto nodraw`).
The check against the 1997 data needs the extracted screens of tools/dinkex (not tracked); it is skipped without them
(DINK_DINKEX_OUT names another extraction)."""
import json
import os
import struct
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Scripts'))
import art_coverage  # noqa: E402

DINKEX = Path(os.environ.get('DINK_DINKEX_OUT') or PROJECT.parent / 'tools/dinkex/out')
PLAY_FIELD_LEFT = 20


def png_width(path):
    with open(path, 'rb') as f:
        head = f.read(24)
    return struct.unpack('>I', head[16:20])[0]


class NeverDrawnTests(unittest.TestCase):
    def test_rows_are_origin_ids_with_a_cited_reason(self):
        self.assertEqual(sorted(art_coverage.NEVER_DRAWN), ['S001_P37', 'S045_P01'])
        for oid, reason in art_coverage.NEVER_DRAWN.items():
            self.assertRegex(oid, art_coverage.ORIGIN_RE)
            self.assertIn('dink.cpp:3170', reason)
            self.assertIn('never drawn in 1997', reason)

    @unittest.skipUnless((DINKEX / 'screens').is_dir(), 'tools/dinkex/out is not extracted here')
    def test_each_lies_wholly_under_the_left_border_and_nothing_can_move_it(self):
        for oid in art_coverage.NEVER_DRAWN:
            screen = json.loads((DINKEX / 'screens' / ('SCR_%s.json' % oid[1:4])).read_text())
            rows = [p for p in screen['placements'] if oid in (p.get('id'), p.get('origin_id'))]
            self.assertEqual(len(rows), 1, oid)
            p = rows[0]
            left = p['x'] - p['pic']['origin']['x']
            right = left + png_width(DINKEX / p['pic']['image'])
            self.assertLess(right - 1, PLAY_FIELD_LEFT, '%s: right edge at window x %d' % (oid, right))
            self.assertEqual((p['brain'], p['script'], p['vision'], p['size_percent']), (0, '', 0, 100), oid)

    @unittest.skipUnless((DINKEX / 'screens').is_dir(), 'tools/dinkex/out is not extracted here')
    def test_a_sparkle_inside_the_play_field_would_not_qualify(self):
        # The same picture one play-field border further right is drawn: the rule is the clip, not the sprite family.
        screen = json.loads((DINKEX / 'screens' / 'SCR_001.json').read_text())
        p = next(p for p in screen['placements'] if 'S001_P37' in (p.get('id'), p.get('origin_id')))
        right = (p['x'] + PLAY_FIELD_LEFT) - p['pic']['origin']['x'] + png_width(DINKEX / p['pic']['image'])
        self.assertGreaterEqual(right - 1, PLAY_FIELD_LEFT)


if __name__ == '__main__':
    unittest.main()
