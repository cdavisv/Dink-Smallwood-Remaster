import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gate2_backlog import (SCREEN_FAMILY, build_backlog, claim_strings, compact_ids, load_photoreal_claims,
                           render, sheet_for)


def row(oid, t, state, cls='', fam='', screen='SCR_001'):
    return {'origin_id': oid, 'type': t, 'screen': screen, 'region': 'stonebrook', 'sprite_family': fam,
            'art_kind': 'prop', 'state': state, 'evidence': '', '_cls': cls}


BY_FRAME = {(92, 1): {'class_id': 'beach_pebbles', 'name': 'Shell and pebble scatter', 'family': 'beach',
                      'pixel_size': '6x4'},
            (31, 23): {'class_id': 'int_wall_plaster_side', 'name': 'Plaster side wall', 'family': 'interior_plaster_kit',
                       'pixel_size': '18x100'}}
BY_CLASS = {v['class_id']: v for v in BY_FRAME.values()}


class Gate2BacklogTests(unittest.TestCase):
    def rows(self):
        return [
            row('S001_P01', 'placement', 'placeholder', 'beach_pebbles', '92 lands/details/beach-'),
            row('S001_P02', 'placement', 'placeholder', 'beach_pebbles', '92 lands/details/beach-'),
            row('S002_P01', 'placement', 'placeholder', '', '31 inside/innwalls/walls/inn-', 'SCR_002'),
            row('S002_P02', 'placement', 'final', 'int_wall_plaster_side', '31 inside/innwalls/walls/inn-', 'SCR_002'),
            row('S002_P03', 'placement', 'cut', 'int_wall_plaster_side', '31 inside/innwalls/walls/inn-', 'SCR_002'),
            row('S002_P01', 'warp', 'placeholder', '', '31 inside/innwalls/walls/inn-', 'SCR_002'),
            row('SW_s1-hole_L21@S001_P02', 'warp', 'placeholder'),
            row('SCR_001', 'screen', 'placeholder'),
            row('SCR_002', 'screen', 'final'),
            row('S003_P01', 'placement', 'reviewing', 'beach_pebbles', '92 lands/details/beach-', 'SCR_003'),
        ]

    def test_open_ids_are_placeholder_or_unclassified_grouped_by_class_and_sorted_by_placements(self):
        frames = {'S001_P01': (92, 1), 'S001_P02': (92, 1), 'S002_P01': (31, 23), 'S002_P02': (31, 23),
                  'S002_P03': (31, 23), 'S003_P01': (92, 1), 'S004_P09': (92, 1)}
        groups, totals = build_backlog(self.rows(), frames, BY_FRAME)
        self.assertEqual([g['family'] for g in groups], ['beach_pebbles', 'int_wall_plaster_side', SCREEN_FAMILY])
        beach = groups[0]
        # S003_P01 has an unknown state and S004_P09 is missing from coverage: both unclassified, both open.
        # The script warp hosted on S001_P02 is its own ID in its host's family, not a placement.
        self.assertEqual(beach['ids'], {'S001_P01', 'S001_P02', 'S003_P01', 'S004_P09', 'SW_s1-hole_L21@S001_P02'})
        self.assertEqual(beach['placements'], 4)
        self.assertEqual(beach['states']['unclassified'], 2)
        # A class-less placement falls back to sprite_classes by (seq, frame); its sprite warp shares the ID.
        wall = groups[1]
        self.assertEqual(wall['ids'], {'S002_P01'})
        self.assertEqual((wall['placements'], wall['closed']['final'], wall['closed']['cut']), (1, 1, 1))
        self.assertEqual((groups[2]['ids'], groups[2]['screens'], groups[2]['placements']), ({'SCR_001'}, 1, 0))
        self.assertEqual((totals['families'], totals['ids'], totals['placements'], totals['screens']), (3, 7, 5, 1))
        self.assertEqual(totals['missing_from_coverage'], ['S004_P09'])
        self.assertEqual(totals['unclassified_states'], {'reviewing': 1})

    def test_photoreal_claims_ignore_inventory_and_not_built_clauses(self):
        props = {'schema': 'dink-props/1',
                 'inventory': {'placeholder_prop_classes': [{'class_id': 'starfish', 'families': ['starfish']}]},
                 'assets': [{'name': 'SM_Bed', 'families': ['64 inside/details/inacc- frame 3', 'bed (12 placements)']}]}
        structures = {'schema': 'dink-structures/1',
                      'families': {'424 struct/island/isle-': 'hut_round -> SM_Hut; island_spear_pole NOT built'}}
        terrain = {'schema': 'dink-terrain-sets/1', 'sets': [{'tile_classes': ['grass']}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for stream, data in (('Props', props), ('Structures', structures), ('Terrain', terrain)):
                (root / stream).mkdir()
                (root / stream / 'manifest.json').write_text(json.dumps(data), encoding='utf-8')
            (root / 'Props' / 'Bed').mkdir()
            (root / 'Props' / 'Bed' / 'manifest.json').write_text(json.dumps({'families': ['starfish']}), encoding='utf-8')
            claims, notes = load_photoreal_claims(str(root), {'bed', 'starfish', 'hut_round', 'island_spear_pole'})
        self.assertEqual(claims, {'bed': ['Props'], 'hut_round': ['Structures'], SCREEN_FAMILY: ['Terrain']})
        self.assertEqual(notes, [])
        self.assertIn('424 struct/island/isle-', claim_strings(structures))
        missing, notes = load_photoreal_claims('/nonexistent/photoreal', {'bed'})
        self.assertEqual(missing, {})
        self.assertIn('not found', notes[0])

    def test_sheets_ids_and_markdown(self):
        self.assertEqual(sheet_for('92 lands/details/beach-'), 'sheet_lands.png')
        self.assertEqual(sheet_for('23 animals/duck/dk3w-'), 'sheet_foes.png')
        self.assertEqual(sheet_for('56 bonuses/bottles/botl-r'), 'sheet_items.png')
        self.assertEqual(sheet_for(SCREEN_FAMILY), 'sheet_tiles.png')
        self.assertEqual(sheet_for('seq 999'), '')
        self.assertEqual(compact_ids({'S001_P02', 'S001_P01', 'S010_P05', 'SCR_007', 'SCR_001', 'SW_x_L1@S001_P01'}),
                         'S001: P01 P02 · S010: P05 · SCR 001 007 · SW_x_L1@S001_P01')
        frames = {'S001_P01': (92, 1), 'S001_P02': (92, 1), 'S002_P01': (31, 23), 'S002_P02': (31, 23),
                  'S002_P03': (31, 23), 'S003_P01': (92, 1)}
        groups, totals = build_backlog(self.rows(), frames, BY_FRAME)
        text = render(groups, totals, {'beach_pebbles': ['Terrain']}, BY_CLASS,
                      {'date': '2026-11-12', 'source': 'fixture', 'closed': 'n/a', 'notes': []})
        self.assertIn('| sprite families | 3 |', text)
        self.assertIn('| 1 | [`beach_pebbles`](#f1-beach-pebbles) | Shell and pebble scatter (beach, 6x4 px) · '
                      'sheet_lands.png | 92 lands/details/beach- (3) | 4 | 3 | Terrain |', text)
        self.assertIn('**1 families, 4 origin IDs, 3 placements**', text)
        self.assertIn('<a id="f2-int-wall-plaster-side"></a>', text)
        self.assertTrue(text.endswith('\n') and not text.endswith('\n\n'))


if __name__ == '__main__':
    unittest.main()
