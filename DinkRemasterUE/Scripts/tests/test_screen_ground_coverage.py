"""The audit rule for a screen's ground: Scripts/art_coverage.py screen_ground_state()."""
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Scripts'))
from art_coverage import ENV_TERRAIN, ENV_TEXTURES, ground_rule_enabled, load_ground, screen_ground_state  # noqa: E402


def facts(**over):
    row = {'indoor': False, 'classes': {'grass': 80, 'path': 16}, 'layer_of': {'grass': 'MeadowTurf', 'path': 'EarthPath'},
           'layers': ['MeadowTurf', 'EarthPath'], 'painted_ground': False, 'unmapped_tiles': 0, 'dropped': {}, 'water_surface': False}
    row.update(over)
    return row


def review(**classes):
    out = {'schema': 'dink-environment-ground-review/1', 'date': '13 Nov 2026', 'rule': {'count_reviewed_grounds_final': True},
           'classes': {}, 'conditions': {}, 'screens': {}}
    for name, verdict in classes.items():
        cls, _, where = name.partition('__')
        out['classes'].setdefault(cls, {})[where or 'outdoor'] = (
            {'verdict': 'pass'} if verdict is True else {'verdict': 'fail', 'reason': verdict})
    return out


def all_exist(path):
    return (True, '')


class ScreenGroundCoverageTests(unittest.TestCase):
    def test_final_when_every_tile_class_passed_and_every_layer_exists(self):
        state, evidence = screen_ground_state(facts(), review(grass=True, path=True), all_exist)
        self.assertEqual(state, 'final')
        self.assertTrue(evidence.startswith('ground-layers: tile classes grass 80, path 16 -> photoreal terrain layers MeadowTurf, EarthPath'))
        self.assertIn('in-game review of 13 Nov 2026', evidence)

    def test_one_failed_or_unreviewed_class_keeps_the_screen_placeholder_with_every_reason(self):
        state, evidence = screen_ground_state(facts(classes={'grass': 60, 'cliff_face': 30, 'path': 6}),
                                              review(grass=True, cliff_face='a flat rock picture where a cliff should stand'), all_exist)
        self.assertEqual(state, 'placeholder')
        self.assertIn('tile class cliff_face (30 tiles, outdoor): a flat rock picture where a cliff should stand', evidence)
        self.assertIn('tile class path (6 tiles, outdoor): not reviewed in the game', evidence)
        self.assertNotIn('tile class grass', evidence)

    def test_a_verdict_given_outdoors_does_not_pass_the_class_indoors(self):
        indoor = facts(indoor=True, classes={'stone_floor': 96}, layers=['DungeonFlagstone'])
        self.assertEqual(screen_ground_state(indoor, review(stone_floor=True), all_exist)[0], 'placeholder')
        self.assertEqual(screen_ground_state(indoor, review(stone_floor__indoor=True), all_exist)[0], 'final')

    def test_a_dropped_layer_fails_and_a_merged_one_does_not(self):
        dropped = facts(classes={'grass': 80, 'path': 8, 'sand': 4, 'cliff_face': 4}, layers=['MeadowTurf', 'EarthPath', 'DrySand'], dropped={'CliffRock': 4.0})
        ok = review(grass=True, path=True, sand=True, cliff_face=True)
        state, evidence = screen_ground_state(dropped, ok, all_exist)
        self.assertEqual(state, 'placeholder')
        self.assertIn('layer CliffRock (4.0 tiles) is not drawn, the mask carries 3 layers', evidence)
        # the later data format names what draws the tiles instead
        dropped['dropped'] = {'CliffRock': {'tiles': 4.0, 'drawn_as': 'EarthPath'}}
        self.assertIn('shown as EarthPath', screen_ground_state(dropped, ok, all_exist)[1])
        merged = facts(classes={'grass': 80, 'grass_rocky': 16}, layers=['MeadowTurf'], merged={'RockyGrass': {'tiles': 16.0, 'drawn_as': 'MeadowTurf'}})
        state, evidence = screen_ground_state(merged, review(grass=True, grass_rocky=True), all_exist)
        self.assertEqual(state, 'final')
        self.assertIn('RockyGrass drawn as a layer of its family', evidence)

    def test_painted_ground_unmapped_tiles_and_missing_assets_fail(self):
        ok = review(grass=True, path=True)
        self.assertIn('keeps the 1997 painted ground picture', screen_ground_state(facts(painted_ground=True, layers=[]), ok, all_exist)[1])
        self.assertIn('12 tiles of a class without a terrain layer', screen_ground_state(facts(unmapped_tiles=12), ok, all_exist)[1])
        no_normal = lambda path: (path != ENV_TEXTURES + 'T_Env_EarthPath_N', '')
        state, evidence = screen_ground_state(facts(), ok, no_normal)
        self.assertEqual(state, 'placeholder')
        self.assertIn('layer EarthPath lacks its N texture', evidence)
        self.assertIn('terrain master material is not imported', screen_ground_state(facts(), ok, lambda path: (path != ENV_TERRAIN, ''))[1])

    def test_water_tiles_need_a_water_surface(self):
        wet = facts(classes={'grass': 60, 'water': 36}, layers=['MeadowTurf', 'WetSand'])
        ok = review(grass=True, water=True)
        state, evidence = screen_ground_state(wet, ok, all_exist)
        self.assertEqual(state, 'placeholder')
        self.assertIn('36 water tiles without a water surface', evidence)
        self.assertEqual(screen_ground_state(dict(wet, water_surface=True), ok, all_exist)[0], 'final')
        ok['conditions']['water_without_surface'] = {'verdict': 'pass'}
        self.assertEqual(screen_ground_state(wet, ok, all_exist)[0], 'final')

    def test_the_rule_is_one_switch_and_off_when_absent(self):
        on = review(grass=True, path=True)
        self.assertEqual(screen_ground_state(facts(), on, all_exist)[0], 'final')
        for rule in ({'count_reviewed_grounds_final': False}, {}, None):
            off = dict(on, rule=rule)
            state, evidence = screen_ground_state(facts(), off, all_exist)
            self.assertEqual(state, 'placeholder')
            self.assertIn('switched off', evidence)
        notes = []
        _, forced = load_ground(notes, 'off')
        self.assertFalse(ground_rule_enabled(forced))
        _, forced = load_ground(notes, 'on')
        self.assertTrue(ground_rule_enabled(forced))

    def test_no_facts_or_no_review_is_placeholder(self):
        self.assertEqual(screen_ground_state(None, review(grass=True), all_exist)[0], 'placeholder')
        self.assertEqual(screen_ground_state(facts(), None, all_exist)[0], 'placeholder')
        self.assertEqual(screen_ground_state(facts(), {}, all_exist)[0], 'placeholder')

    def test_the_committed_data_covers_every_screen_and_every_class_of_the_review_exists(self):
        env = PROJECT / 'Content/Dink/Data/Environment'
        screens = json.loads((env / 'ground_classes.json').read_text())['screens']
        self.assertEqual(len(screens), 644)
        self.assertTrue(all(sum(row['classes'].values()) == 96 for row in screens.values()))
        self.assertTrue(all(len(row['layers']) <= 4 and not row['painted_ground'] for row in screens.values()))
        rev = json.loads((env / 'ground_review.json').read_text())
        used = {(c, 'indoor' if row['indoor'] else 'outdoor') for row in screens.values() for c in row['classes']}
        listed = {(c, where) for c, row in rev['classes'].items() for where in row}
        self.assertEqual(listed - used, set(), 'the review names a class no screen has')
        for cls, row in rev['classes'].items():
            for where, v in row.items():
                self.assertIn(v['verdict'], ('pass', 'fail'))
                self.assertTrue(v.get('seen'), '%s %s: a verdict needs the screens that were looked at' % (cls, where))
                if v['verdict'] == 'fail':
                    self.assertTrue(v.get('reason'), '%s %s: a failed class needs its reason' % (cls, where))
        for number, finding in rev.get('screens', {}).items():
            self.assertIn(number, screens)
            self.assertTrue(finding.get('reason'))


if __name__ == '__main__':
    unittest.main()
