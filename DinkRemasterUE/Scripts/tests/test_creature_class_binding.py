"""Class rows of creatures.json as Scripts/art_coverage.py reads them (the mirror of DinkCreatureClass / UDinkCreatureSubsystem)."""
import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import art_coverage  # noqa: E402
from creature_art_manifest import merge_runtime  # noqa: E402

G = '/Game/Dink/Creatures/Bug/'


def row(**changes):
    base = {
        'class': 'pillbug',
        'mesh': G + 'SK_Bug.SK_Bug',
        'locomotion': {'idle': G + 'AN_Idle.AN_Idle', 'gaits': [{'clip': G + 'AN_Walk.AN_Walk', 'speed_cm_s': 80},
                                                               {'clip': G + 'AN_Run.AN_Run', 'speed_cm_s': 400}]},
        'roles': {'walk': {'sequences': [131, 133], 'locomotion': True}},
        'corpses': [{'sequences': [141, 143], 'mesh': G + 'SM_Corpse.SM_Corpse'}],
    }
    base.update(changes)
    return base


def manifest(*rows):
    return {'schema': 'dink-creatures/1', 'assets': [], 'placements': [], 'classes': list(rows)}


def exists(_path):
    return True, 'ok'


class CreatureClassRows(unittest.TestCase):
    def rows(self, data, resolve=exists):
        notes = []
        return art_coverage.creature_class_rows(data, resolve, notes), notes

    def test_valid_row_binds_with_roles_sequences_and_corpse(self):
        rows, notes = self.rows(manifest(row()))
        self.assertEqual(notes, [])
        self.assertEqual(rows['pillbug']['roles'], ['walk'])
        self.assertEqual(rows['pillbug']['sequences'], [131, 133])
        self.assertEqual(rows['pillbug']['corpses'][0]['sequences'], [141, 143])

    def test_corpse_decal_is_an_asset_the_row_needs(self):
        data = row(corpses=[{'sequences': [141, 143], 'mesh': G + 'SM_Corpse.SM_Corpse', 'decal': {'material': G + 'M_Pool.M_Pool', 'size_cm': [440, 440]}}])
        rows, notes = self.rows(manifest(data))
        self.assertEqual(notes, [])
        self.assertEqual(rows['pillbug']['corpses'][0]['decal'], G + 'M_Pool.M_Pool')
        rows, notes = self.rows(manifest(data), lambda path: (not path.endswith('M_Pool.M_Pool'), 'file not found'))
        self.assertEqual(rows, {})
        self.assertIn('M_Pool', notes[0])

    def test_gore_rows_need_their_assets_a_bone_and_the_blood_drop(self):
        gore = {'bone': 'neck_02', 'drops_per_second': 90, 'trail': {'material': G + 'M_Puddle.M_Puddle'},
                'severed': {'flying': G + 'SM_Fly.SM_Fly', 'landed': G + 'SM_Head.SM_Head', 'decal': G + 'M_Puddle.M_Puddle', 'drops': 40}}
        roles = {'walk': {'sequences': [21, 23], 'locomotion': True}, 'headless': {'sequences': [111, 113], 'locomotion': True, 'gore': gore}}
        bursts = [{'sequences': [111, 113], 'brain': 3, 'decal': {'material': G + 'M_Burst.M_Burst', 'size_cm': 170}}]
        duck = row(**{'class': 'duck', 'roles': roles, 'bursts': bursts, 'blood_drop': G + 'SM_Drop.SM_Drop', 'corpses': []})
        rows, notes = self.rows(manifest(duck))
        self.assertEqual(notes, [])
        self.assertEqual(rows['duck']['roles'], ['headless', 'walk'])
        for missing in ('SM_Fly.SM_Fly', 'SM_Head.SM_Head', 'M_Puddle.M_Puddle', 'M_Burst.M_Burst', 'SM_Drop.SM_Drop'):
            rows, notes = self.rows(manifest(duck), lambda path, missing=missing: (not path.endswith(missing), 'file not found'))
            self.assertEqual(rows, {}, missing)
        for broken in (dict(duck, blood_drop=''), dict(duck, roles=dict(roles, headless=dict(roles['headless'], gore=dict(gore, bone='')))),
                       dict(duck, roles=dict(roles, headless=dict(roles['headless'], gore=dict(gore, severed={'flying': G + 'SM_Fly.SM_Fly'}))))):
            rows, notes = self.rows(manifest(broken))
            self.assertEqual(rows, {})
            self.assertEqual(len(notes), 1)

    def test_missing_asset_leaves_the_class_unbound(self):
        def resolve(path):
            return (not path.endswith('AN_Run.AN_Run')), 'file not found'
        rows, notes = self.rows(manifest(row()), resolve)
        self.assertEqual(rows, {})
        self.assertIn('AN_Run', notes[0])

    def test_rows_the_runtime_refuses_are_refused_here(self):
        bad = [
            row(mesh='Dink/SK_Bug'),                                                          # not a /Game/ path
            row(roles={'attack': {'sequences': [135], 'clip': G + 'AN_Attack.AN_Attack'}}),    # no locomotion role
            row(roles={'walk': {'sequences': [131], 'locomotion': True},
                       'attack': {'sequences': [131], 'clip': G + 'AN_Attack.AN_Attack'}}),    # a sequence in two roles
            row(roles={'walk': {'sequences': [], 'locomotion': True}}),                        # no sequences
            row(roles={'walk': {'sequences': [131], 'clip': 'AN_Walk'}}),                      # neither locomotion nor a clip
            row(locomotion={'idle': G + 'AN_Idle.AN_Idle', 'gaits': [{'clip': G + 'AN_Run.AN_Run', 'speed_cm_s': 400},
                                                                    {'clip': G + 'AN_Walk.AN_Walk', 'speed_cm_s': 80}]}),  # gaits not rising
            row(corpses=[{'sequences': [141]}]),                                               # corpse without mesh
            row(corpses=[{'sequences': [141], 'mesh': G + 'SM_Corpse.SM_Corpse', 'decal': {'material': G + 'M_Pool.M_Pool', 'size_cm': [440]}}]),  # decal without a size pair
            row(corpses=[{'sequences': [141], 'mesh': G + 'SM_Corpse.SM_Corpse', 'decal': {'size_cm': [440, 440]}}]),                               # decal without a material
            row(scale=0),
        ]
        for data in bad:
            rows, notes = self.rows(manifest(data))
            self.assertEqual(rows, {}, data)
            self.assertEqual(len(notes), 1, data)

    def test_role_with_its_own_locomotion_needs_no_row_set(self):
        data = row(roles={'walk': {'sequences': [131], 'locomotion': True},
                          'headless': {'sequences': [111, 113], 'mesh': G + 'SK_Headless.SK_Headless',
                                       'locomotion': {'idle': G + 'AN_HIdle.AN_HIdle', 'gaits': [{'clip': G + 'AN_HRun.AN_HRun', 'speed_cm_s': 300}]}}})
        rows, notes = self.rows(manifest(data))
        self.assertEqual(notes, [])
        self.assertEqual(rows['pillbug']['roles'], ['headless', 'walk'])
        del data['locomotion']
        rows, notes = self.rows(manifest(data))
        self.assertEqual(rows, {})  # the plain "locomotion": true role now has no set

    def test_first_row_of_a_class_wins_and_other_schemas_bind_nothing(self):
        rows, notes = self.rows(manifest(row(), row(mesh=G + 'SK_Other.SK_Other')))
        self.assertEqual(rows['pillbug']['mesh'], G + 'SK_Bug.SK_Bug')
        self.assertIn('bound twice', notes[0])
        self.assertEqual(self.rows({'schema': 'dink-art/1', 'classes': [row()]})[0], {})
        self.assertEqual(self.rows(None)[0], {})


class CreatureClassDecision(unittest.TestCase):
    def setUp(self):
        self.rows = art_coverage.creature_class_rows(manifest(row()), exists, [])

    def bind(self, cls='pillbug', oid='S100_P05', precedence=(), is_actor=True, detail='live pillbug enemy'):
        return art_coverage.creature_class_binding(self.rows, cls, oid, set(precedence), is_actor, detail)

    def test_every_actor_placement_of_the_class_is_bound(self):
        self.assertEqual(self.bind()['class'], 'pillbug')
        self.assertEqual(self.bind(oid='S700_P91')['class'], 'pillbug')

    def test_origin_rows_and_other_manifests_keep_precedence(self):
        self.assertIsNone(self.bind(oid='S438_P03', precedence={'S438_P03'}))

    def test_other_classes_instances_and_pictureless_placements_are_not_bound(self):
        self.assertIsNone(self.bind(cls='duck'))
        self.assertIsNone(self.bind(cls=''))
        self.assertIsNone(self.bind(is_actor=False))  # a background instance has no sprite to follow
        self.assertIsNone(self.bind(detail='hardness_only pillbug enemy'))
        self.assertIsNone(self.bind(detail='live pillbug enemy; no picture'))


class ShippedManifest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((SCRIPTS.parent / 'Content/Dink/Data/Art/creatures.json').read_text())

    def test_shipped_class_rows_parse_and_do_not_shadow_origin_rows(self):
        notes = []
        rows = art_coverage.creature_class_rows(self.data, exists, notes)
        self.assertEqual(notes, [])
        self.assertIn('pillbug', rows)
        self.assertEqual(len(rows), len(self.data['classes']))
        claimed = {}
        for name, entry in rows.items():
            for seq in entry['sequences']:
                self.assertNotIn(seq, claimed, 'sequence %d is in %s and %s' % (seq, claimed.get(seq), name))
                claimed[seq] = name
        self.assertEqual(len(self.data['placements']), 11)  # the origin rows of the first creatures stay

    def test_reimporting_an_origin_creature_keeps_the_class_rows(self):
        current = {'schema': 'dink-creatures/1',
                   'assets': [a for a in self.data['assets'] if a['mesh'].endswith('SK_Pig.SK_Pig')],
                   'placements': [p for p in self.data['placements'] if p['mesh'].endswith('SK_Pig.SK_Pig')]}
        merged = merge_runtime(self.data, current)
        self.assertEqual(merged['classes'], self.data['classes'])
        self.assertEqual(len(merged['placements']), 11)


if __name__ == '__main__':
    unittest.main()
