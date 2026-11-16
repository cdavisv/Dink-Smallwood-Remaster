from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export_presentation_data import DEST, SOURCE, build_rows, display_name, render


class ExportPresentationDataTests(unittest.TestCase):
    def test_display_names(self):
        self.assertEqual(display_name('Dink'), 'Dink')
        self.assertEqual(display_name('cave prisoner'), 'Cave Prisoner')
        self.assertEqual(display_name('old man 2'), 'Old Man')
        self.assertEqual(display_name('dragon (spell caster)'), 'Dragon')
        self.assertEqual(display_name('Cast agent / bar thug'), 'Cast Agent')
        self.assertEqual(display_name('Mr. SmileStein'), 'Mr. SmileStein')
        self.assertEqual(display_name('voice behind a door 2'), 'Voice Behind a Door')
        self.assertEqual(display_name('rogue Royal Guard (dying)'), 'Rogue Royal Guard')
        self.assertEqual(display_name(''), '')

    def test_only_spoken_kinds_get_a_name(self):
        text = ('id,script,say,spk,col,dynamic,chars,text,character,voice,kind,tts_text\n'
                's1-h1-m.talk.005,s1-h1-m,say_stop,&current_sprite,13,0,5,Hi.,Mother,mother,dialogue,Hi.\n'
                'sign1.talk.001,sign1,say_stop,&current_sprite,14,0,5,Hi.,sign,,object,\n'
                'end.main.001,end,say,1,14,0,5,Hi.,end card,,narration,\n'
                '1gold.touch.001,1gold,say,1,14,1,17,I found <N> gold.,Dink,,system,\n'
                'x.main.001,x,say,1,14,0,5,Saved.,game message,,system,\n')
        self.assertEqual(build_rows(text), [('1gold.touch.001', 'Dink'), ('s1-h1-m.talk.005', 'Mother')])
        self.assertEqual(render(build_rows(text)).splitlines()[0], 'line_id,name')

    def test_checked_in_file_is_current(self):
        if not SOURCE.exists():
            self.skipTest('voice ledger not present')
        self.assertTrue(DEST.exists(), 'run Scripts/export_presentation_data.py')
        self.assertEqual(DEST.read_text(encoding='utf-8'), render(build_rows(SOURCE.read_text(encoding='utf-8'))))
        self.assertIn('s1-h1-m.talk.005,Mother', DEST.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
