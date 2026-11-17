"""families.json `scripted_scripts` as Scripts/art_coverage.py reads it (the mirror of DinkArtFamily::Decide).

A row that keeps scripted placements as cards may still dress the placements whose DinkC script is listed: scripts read
to never change, move or remove their own sprite. The shipped lists are checked against the scripts in bin/dink/story.
"""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
PROJECT = SCRIPTS.parent
STORY = PROJECT.parent / 'bin' / 'dink' / 'story'
sys.path.insert(0, str(SCRIPTS))

import art_coverage  # noqa: E402


class _Assets:
    def resolve(self, _path):
        return True, 'ok'


def rows_from(families):
    with tempfile.TemporaryDirectory() as root:
        art = Path(root, 'Content', 'Dink', 'Data', 'Art')
        art.mkdir(parents=True)
        (art / 'families.json').write_text(json.dumps({'schema': 'dink-art-families/1', 'families': families}))
        saved = art_coverage.PROJECT
        art_coverage.PROJECT = root
        try:
            rows, _origins, _screens = art_coverage.load_families(_Assets(), [])
        finally:
            art_coverage.PROJECT = saved
    return {r['family']: r for r in rows}


class ScriptAllowance(unittest.TestCase):
    def setUp(self):
        self.rows = rows_from([
            {'family': 'tree_pine_large', 'mesh': '/Game/A/SM_Pine', 'scripted_scripts': ['s2-sec2', ' Big ', '', 3]},
            {'family': 'cabinet_wood', 'mesh': '/Game/A/SM_Cabinet'},
            {'family': 'bush', 'mesh': '/Game/A/SM_Bush', 'scripted': True},
        ])

    def test_row_parse(self):
        self.assertEqual(self.rows['tree_pine_large']['scripted_scripts'], frozenset({'s2-sec2', 'big'}))
        self.assertFalse(self.rows['tree_pine_large']['scripted'])
        self.assertEqual(self.rows['cabinet_wood']['scripted_scripts'], frozenset())

    def test_decision(self):
        dresses = art_coverage.family_row_dresses_script
        pine, cabinet, bush = self.rows['tree_pine_large'], self.rows['cabinet_wood'], self.rows['bush']
        self.assertTrue(dresses(pine, 's2-sec2'), 'a listed script is dressed')
        self.assertTrue(dresses(pine, 'S2-SEC2'), 'names match without case, like FName')
        self.assertTrue(dresses(pine, 'big'), 'a trimmed listed name matches')
        self.assertFalse(dresses(pine, 's2-sec1'), 'the burnable pine keeps its card')
        self.assertFalse(dresses(cabinet, 's2-sec2'), 'a list opens only its own row')
        self.assertTrue(dresses(cabinet, ''), 'unscripted placements are dressed as before')
        self.assertTrue(dresses(cabinet, None), 'a placement missing from placements.csv counts as unscripted')
        self.assertTrue(dresses(bush, 'anything'), '`scripted` true still allows every script')


# A listed script must leave its own sprite's picture and place alone (DinkC on &current_sprite).
PICTURE_CALLS = re.compile(r'\b(sp_pseq|sp_pframe|sp_seq|sp_frame|sp_kill|sp_nodraw|sp_brain|sp_x|sp_y|move|move_stop|sp_size)\s*\(\s*&current_sprite\b', re.I)


class ShippedLists(unittest.TestCase):
    def setUp(self):
        data = json.loads((PROJECT / 'Content/Dink/Data/Art/families.json').read_text())
        self.lists = {r['family']: r['scripted_scripts'] for r in data['families'] if 'scripted_scripts' in r}

    def test_a202_rows(self):
        self.assertEqual(self.lists.get('tree_pine_large'), ['s2-sec2'])
        self.assertNotIn('tree_willow_large', self.lists, 'S149_P02 (`big`) draws no card at the play camera: left out')
        # the two scripted tables of SCR_003 are dressed by #194's sequence-and-frame rows (87 frames 1 and 7, the oak table)
        self.assertNotIn('cabinet_wood', self.lists)
        for family, names in self.lists.items():
            for script in ('s2-sec1', 's2-sec3', 's3-sec1', 's1-ntree', 's4-tree', 's2-fgate'):
                self.assertNotIn(script, names, '%s: %s changes its sprite or is owned by Fable packet VS-10' % (family, script))

    @unittest.skipUnless(STORY.is_dir(), 'bin/dink/story not present')
    def test_listed_scripts_leave_their_sprite_alone(self):
        for family, names in self.lists.items():
            for name in names:
                source = STORY / (name + '.c')
                if not source.exists():
                    # 1997 load_script finds neither .c nor .d: nothing runs
                    self.assertFalse((STORY / (name + '.d')).exists(), name)
                    continue
                text = source.read_text(errors='replace')
                self.assertIsNone(PICTURE_CALLS.search(text), '%s: %s changes its own sprite' % (family, name))
                self.assertNotIn('missile_target', text.lower(), '%s: %s acts on the missile target' % (family, name))


if __name__ == '__main__':
    unittest.main()
