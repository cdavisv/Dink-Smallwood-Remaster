"""The photoreal people: every NPC source and colour twin is consistent, and creatures.json binds them as class rows
(presentation only), never as origin rows of characters.json (which would change how they are talked to and hit)."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NPC = ROOT / 'SourceAssets/Art/PhotorealPass/Characters/NPC'
CREATURES = json.loads((ROOT / 'Content/Dink/Data/Art/creatures.json').read_text())
CHARS = json.loads((ROOT / 'Content/Dink/Data/Art/characters.json').read_text())
PREFIX = '/Game/Dink/Photoreal/Characters/NPC/'
PEOPLE = [r for r in CREATURES['classes'] if r['mesh'].startswith(PREFIX)]


class PeopleClassBinding(unittest.TestCase):
    def test_ported_sources_are_complete(self):
        manifests = sorted(NPC.glob('*/manifest.json'))
        self.assertGreaterEqual(len(manifests), 6)
        for mf in manifests:
            m = json.loads(mf.read_text())
            self.assertEqual(m['schema'], 'dink-photoreal-character/1')
            self.assertEqual(m['bone_count'], 89, mf)
            self.assertEqual(m['asset'], f'SK_{mf.parent.name}_Photoreal')
            self.assertEqual(len(m['fbx']), 4)
            for rel in m['fbx']:
                self.assertTrue((mf.parent / rel).is_file(), rel)
            self.assertLessEqual(len(m['materials']), 5)
            for name, row in m['materials'].items():
                self.assertIn(name, m['material_slots'])
                for role in ('BC', 'N', 'ORM'):
                    self.assertTrue((mf.parent / row['textures'][role]).is_file(), f'{name} {role}')
                if 'Hair' in name:
                    self.assertIn('masked', row['shading'].lower())
            self.assertTrue(all(lod['unweighted'] == 0 and lod['max_influences'] <= 8 for lod in m['lods']), mf)
            self.assertIn(m['animation_set'], ('NpcF', 'NpcM'))
            self.assertTrue(0.4 < m['placement_scale'] <= (1.5 if mf.parent.name == 'Seth' else 1.05))   # Seth stands a head over everyone

    def test_variants_name_a_base_and_existing_maps(self):
        variants = json.loads((NPC / 'variants.json').read_text())['variants']
        for name, row in variants.items():
            base = ROOT / 'SourceAssets/Art/PhotorealPass/Characters' / row['base']
            self.assertTrue((base / 'manifest.json').is_file(), name)
            slots = json.loads((base / 'manifest.json').read_text())['material_slots']
            for slot, change in row['materials'].items():
                self.assertIn(slot, slots, name)
                for rel in change.get('textures', {}).values():
                    self.assertTrue((NPC / rel).is_file(), rel)

    def test_class_rows_are_what_the_generator_writes(self):
        done = subprocess.run([sys.executable, '-I', str(ROOT / 'Scripts/bind_people_classes.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, 'creatures.json people rows differ from Scripts/bind_people_classes.py:\n' + done.stdout + done.stderr)

    def test_people_rows_name_known_figures_and_real_walk_pictures(self):
        known = {p.parent.name for p in NPC.glob('*/manifest.json')} | set(json.loads((NPC / 'variants.json').read_text())['variants'])
        ini = (ROOT.parent / 'bin/dink/dink.ini')
        loaded = {int(m.group(1)) for m in re.finditer(r'^\s*load_sequence(?:_now)?\s+\S+\s+(\d+)', ini.read_text(errors='replace'), re.I | re.M)} if ini.is_file() else None
        self.assertGreaterEqual(len(PEOPLE), 18)
        for r in PEOPLE:
            self.assertIn(r['mesh'][len(PREFIX):].split('/')[0], known, r['class'])
            self.assertEqual(r['rotation_deg'][0], 0)
            self.assertTrue(0.4 < r['scale'] <= (1.5 if r['class'] == 'seth' else 1.05), r['class'])
            gaits = r['locomotion']['gaits']
            self.assertTrue(all(a['speed_cm_s'] < b['speed_cm_s'] for a, b in zip(gaits, gaits[1:])), r['class'])
            seqs = r['roles']['walk']['sequences']
            if r['class'] == 'king_on_throne':
                self.assertTrue(loaded is None or not set(seqs) & loaded, 'the King binds by class id: his row must name no real picture (421 is the food sheet)')
            elif loaded is not None:
                self.assertTrue(set(seqs) - {580} <= loaded, r['class'])   # 580: the number Seth is made with (s7-mil.c:97)
                self.assertFalse([q for q in seqs if q % 10 == 5], 'base + 5 is the death picture: ' + r['class'])
        self.assertIn('seth', {r['class'] for r in PEOPLE})

    def test_old_man_keeps_his_stoop_walking(self):
        """Takeover A4: the old man's walk set lays his idle's stoop (AN_Stoop_Stand) over the shared walk; nobody else's does."""
        rows = {r['class']: r for r in PEOPLE}
        loco = rows['npc_old_man']['locomotion']
        self.assertTrue(loco['idle'].endswith('AN_Stoop_Stand.AN_Stoop_Stand'))
        self.assertEqual(loco.get('posture'), {'weight': 1.0})
        self.assertEqual([c for c, r in rows.items() if 'posture' in r.get('locomotion', {})], ['npc_old_man'])

    def test_no_person_is_an_origin_row(self):
        """An origin row of characters.json gives the actor a body that replaces the 1997 talk, hit and touch boxes."""
        self.assertEqual([r['origin'] for r in CHARS['placements'] if r['mesh'].startswith(PREFIX)], [])
        self.assertEqual([k for k, r in CHARS.get('script_profiles', {}).items() if r['mesh'].startswith(PREFIX)], [])


if __name__ == '__main__':
    unittest.main()
