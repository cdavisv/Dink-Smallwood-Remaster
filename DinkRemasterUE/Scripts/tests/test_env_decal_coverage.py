"""The audit rule for ground decals (environment.json `decals`): Scripts/art_coverage.py env_decal_cards()."""
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Scripts'))
from art_coverage import env_decal_cards  # noqa: E402


def env():
    return {'decals': {'note': 'text rows are skipped',
                       'blood_splat': {'size_cm': 90, 'materials': ['/Game/Dink/Photoreal/Props/MI_Decal_BloodSplat_0.MI_Decal_BloodSplat_0']},
                       'burn_hole_decal': {'size_cm': 120, 'materials': ['/Game/Dink/Photoreal/Props/MI_Decal_BurnHole_0.MI_Decal_BurnHole_0']}},
            'state_swaps': [{'screen': 439, 'vision': 2, 'hide_classes': ['burn_hole_decal']}]}


def row(origin, cls, seq=187, frame=4, brain=0, script=''):
    return {'origin': origin, 'screen': str(int(origin[1:4])), 'seq': str(seq), 'frame': str(frame), 'brain': str(brain), 'script': script, 'class_id': cls}


def all_exist(path):
    return (True, '')


def cards(rows, actors=(), screens=(), origins=(), resolve=all_exist, data=None):
    return env_decal_cards(env() if data is None else data, rows, {r['origin']: r['origin'] in actors for r in rows}, set(screens), set(origins), resolve)


class EnvDecalCoverageTests(unittest.TestCase):
    def test_an_unscripted_actor_placement_of_a_decal_class_is_final(self):
        out = cards([row('S005_P10', 'burn_hole_decal'), row('S005_P11', 'barrel')], actors={'S005_P10', 'S005_P11'})
        self.assertEqual(list(out), ['S005_P10'])
        self.assertTrue(out['S005_P10'].startswith('env-decal: environment.json decals burn_hole_decal -> MI_Decal_BurnHole_0'))
        self.assertIn('actor', out['S005_P10'])

    def test_a_scripted_or_animated_actor_keeps_its_card(self):
        rows = [row('S005_P10', 'burn_hole_decal', script='s1-hole'), row('S005_P11', 'burn_hole_decal', brain=6)]
        self.assertEqual(cards(rows, actors={'S005_P10', 'S005_P11'}), {})

    def test_background_placements_need_their_whole_decor_component(self):
        # three blood splats of one frame on one screen: all qualify, all final
        rows = [row('S091_P06', 'blood_splat'), row('S091_P07', 'blood_splat'), row('S091_P08', 'blood_splat')]
        out = cards(rows)
        self.assertEqual(sorted(out), ['S091_P06', 'S091_P07', 'S091_P08'])
        self.assertIn('instance', out['S091_P06'])
        # one of them is bound by an art manifest: the component keeps its cards, all three stay open
        self.assertEqual(cards(rows, origins={'S091_P07'}), {})
        # another frame of the same screen is its own component
        rows.append(row('S091_P09', 'blood_splat', frame=2))
        self.assertEqual(sorted(cards(rows, origins={'S091_P07'})), ['S091_P09'])

    def test_screens_of_an_art_manifest_and_state_swapped_classes_are_left_alone(self):
        self.assertEqual(cards([row('S001_P40', 'burn_hole_decal')], actors={'S001_P40'}, screens={1}), {})
        self.assertEqual(cards([row('S439_P20', 'burn_hole_decal')], actors={'S439_P20'}), {})
        self.assertEqual(sorted(cards([row('S439_P21', 'blood_splat')], actors={'S439_P21'})), ['S439_P21'])

    def test_a_class_whose_materials_are_all_missing_is_not_final(self):
        missing = lambda path: (False, 'missing')
        self.assertEqual(cards([row('S005_P10', 'burn_hole_decal')], actors={'S005_P10'}, resolve=missing), {})
        self.assertEqual(cards([row('S005_P10', 'burn_hole_decal')], actors={'S005_P10'}, data={}), {})


if __name__ == '__main__':
    unittest.main()
