"""The audit rule for the town-house kit (family 33): Scripts/art_coverage.py town_house_cards()."""
import csv
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Scripts'))
from art_coverage import TOWN_KIT, town_house_cards  # noqa: E402


def module(mesh):
    return {'mesh': mesh, 'px': [0, 0], 'offset_cm': [0, 0, 0], 'yaw': 0, 'scale': [1, 1, 1]}


def town():
    """Two screens: 506 has an assembled house, 474 above it only roof cards of the same building."""
    return {'schema': 'dink-town-houses/3',
            'buildings': [{'id': 'B1', 'screens': [474, 506], 'cards': 4, 'houses': ['S506_A1']}],
            'screens': {
                '506': {'houses': [{'id': 'S506_A1', 'modules': [module('SM_Town_Wall_Plain'), module('SM_Town_Roof_Slope')],
                                    'hide': ['S506_P01', 'S506_P02']}],
                        'stands_for': {'S506_P01': 'S506_A1', 'S506_P02': 'S506_A1'}},
                '474': {'houses': [{'id': 'S474_roofs_only', 'modules': [], 'hide': ['S474_P05', 'S474_P06']}],
                        'stands_for': {'S474_P05': 'S506_A1'}}}}


def all_exist(path):
    return (True, '')


class TownHouseCoverageTests(unittest.TestCase):
    def test_a_hidden_card_with_an_assembled_house_is_final_and_names_the_house(self):
        cards = town_house_cards(town(), all_exist)
        self.assertEqual(cards['S506_P01'][0], 'final')
        self.assertTrue(cards['S506_P01'][1].startswith('town-house: town_houses.json house S506_A1 of building B1 (2 modules of 2 kit meshes'))
        # a roof card on the screen above is stood for by the house of the screen below
        self.assertEqual(cards['S474_P05'][0], 'final')
        self.assertIn('house S506_A1', cards['S474_P05'][1])

    def test_a_hidden_card_nothing_stands_for_stays_placeholder(self):
        cards = town_house_cards(town(), all_exist)
        self.assertEqual(cards['S474_P06'][0], 'placeholder')
        self.assertIn('no assembled house stands for it', cards['S474_P06'][1])

    def test_a_card_that_is_not_hidden_on_its_own_screen_stays_placeholder(self):
        data = town()
        data['screens']['506']['houses'][0]['hide'].remove('S506_P02')
        cards = town_house_cards(data, all_exist)
        self.assertEqual(cards['S506_P02'][0], 'placeholder')
        self.assertIn('does not hide it', cards['S506_P02'][1])
        # hidden only by another screen's list: the runtime hides cards of the screen it applies, so this is not hidden
        data = town()
        data['screens']['506']['houses'][0]['hide'].remove('S506_P02')
        data['screens']['474']['houses'][0]['hide'].append('S506_P02')
        self.assertEqual(town_house_cards(data, all_exist)['S506_P02'][0], 'placeholder')

    def test_a_house_with_a_missing_kit_mesh_or_without_modules_is_not_final(self):
        missing_roof = lambda path: (not path.endswith('SM_Town_Roof_Slope'), 'missing')
        cards = town_house_cards(town(), missing_roof)
        self.assertEqual({cards[o][0] for o in ('S506_P01', 'S506_P02', 'S474_P05')}, {'placeholder'})
        self.assertIn('lacks kit mesh SM_Town_Roof_Slope', cards['S506_P01'][1])
        data = town()
        data['screens']['506']['houses'][0]['modules'] = []
        self.assertIn('has no modules', town_house_cards(data, all_exist)['S506_P01'][1])
        # the mesh name is looked up in the kit folder, a full path as it stands
        seen = []
        town_house_cards(town(), lambda path: (seen.append(path) or True, ''))
        self.assertIn(TOWN_KIT + 'SM_Town_Wall_Plain', seen)

    def test_a_house_that_failed_the_review_keeps_its_cards_placeholder_with_the_reason(self):
        data = town()
        data['screens']['506']['houses'][0]['review'] = {'state': 'placeholder', 'reason': 'roof floats above the wall'}
        cards = town_house_cards(data, all_exist)
        self.assertEqual(cards['S506_P01'][0], 'placeholder')
        self.assertIn('failed the in-game review: roof floats above the wall', cards['S506_P01'][1])
        self.assertEqual(cards['S474_P05'][0], 'placeholder')

    def test_a_hidden_card_no_house_body_covers_stays_placeholder_with_the_distance(self):
        data = town()
        data['screens']['474']['uncovered_m'] = {'S474_P05': 17.3}
        cards = town_house_cards(data, all_exist)
        self.assertEqual(cards['S474_P05'][0], 'placeholder')
        self.assertIn('no house body covers the ground this picture covered (nearest 17.3 m away)', cards['S474_P05'][1])
        self.assertEqual(cards['S506_P01'][0], 'final')   # the wall card of the same house is covered

    def test_unreadable_or_older_data_names_nothing(self):
        self.assertEqual(town_house_cards(None, all_exist), {})
        self.assertEqual(town_house_cards({'schema': 'dink-town-houses/2', 'screens': {'506': {'houses': [{'id': 'S506_A1', 'modules': [module('X')], 'hide': ['S506_P01']}]}}},
                                          all_exist)['S506_P01'][0], 'placeholder')

    def test_the_committed_file_accounts_for_every_family_33_placement(self):
        """Data integrity of the committed files: every placement of sequence 33 in the gameplay table is hidden on
        its own screen and stood for by a house that has modules, and nothing else is hidden."""
        data = json.loads((PROJECT / 'Content/Dink/Data/Art/town_houses.json').read_text())
        with open(PROJECT / 'Content/Dink/Data/Gameplay/placements.csv', newline='', encoding='utf-8') as f:
            family = {r['origin'] for r in csv.DictReader(f) if r['seq'] == '33'}
        cards = town_house_cards(data, all_exist)
        self.assertEqual(set(cards), family)
        self.assertEqual(len(family), 218)
        failed = {h['id'] for row in data['screens'].values() for h in row['houses'] if h.get('review')}
        open_cards = {o for row in data['screens'].values() for o, hid in row['stands_for'].items()
                      if hid in failed or o in row['uncovered_m']}
        self.assertEqual({o for o, (state, _) in cards.items() if state != 'final'}, open_cards)
        # every wall card stands on its own house front, so none of them is uncovered
        with open(PROJECT / 'Content/Dink/Data/Gameplay/placements.csv', newline='', encoding='utf-8') as f:
            wall_frames = {r['origin'] for r in csv.DictReader(f) if r['seq'] == '33' and int(r['frame']) not in
                           (7, 8, 9, 10, 12, 13, 24, 25, 26, 27, 29, 30, 31, 32)}
        self.assertEqual(len(wall_frames), 95)
        self.assertEqual(len(open_cards), 97)
        self.assertFalse(wall_frames & open_cards)
        for row in data['screens'].values():
            for origin in row['stands_for']:
                self.assertRegex(origin, r'^S\d{3}_P\d{2}$')
        self.assertEqual(sum(b['cards'] for b in data['buildings']), 218)


if __name__ == '__main__':
    unittest.main()
