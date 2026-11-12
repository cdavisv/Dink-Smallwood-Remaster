import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sync_gameplay_data import hardness_layers

class RuntimeLayerSyncTests(unittest.TestCase):
    def test_legacy_absence_and_exact_bytes_with_bound_vision(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);(root/'hardness').mkdir()
            self.assertEqual(hardness_layers(root),{})
            packet=dict(schema='dinkex.runtime-hardness/2',width=600,height=400,vision=-3,skipped_tile_indices=[],editor_hard_flags=[0]*99)
            raw=(json.dumps(packet,indent=3)+'\n').encode()
            (root/'hardness/SCR_209_v-3_layers.json').write_bytes(raw)
            self.assertEqual(hardness_layers(root),{'Hardness/SCR_209_v-3_layers.json':raw})
    def test_unsupported_envelopes_refuse_before_any_project_writer(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);(root/'hardness').mkdir();file=root/'hardness/SCR_209_layers.json'
            good=dict(schema='dinkex.runtime-hardness/2',width=600,height=400,vision=0,skipped_tile_indices=[],editor_hard_flags=[0]*99)
            for field,value in [('vision',1),('vision',True),('width',True),('schema','legacy'),('skipped_tile_indices',[7]),('editor_hard_flags',None),('editor_hard_flags',[False]*99),('editor_hard_flags',[2**31]*99),('editor_hard_flags',[0]*98)]:
                packet=dict(good);packet[field]=value;file.write_text(json.dumps(packet))
                with self.assertRaises(ValueError):hardness_layers(root)

class IndependentEditorFlagsTests(unittest.TestCase):
    def test_flags_export_independent_of_layers_and_bound_source_record(self):
        from sync_gameplay_data import editor_hard_flags_files
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);(root/'screens').mkdir()
            f=root/'screens/SCR_010.json'
            f.write_text(json.dumps(dict(screen=10,map_record=8)))
            self.assertEqual(editor_hard_flags_files(root),{})
            flags=[0]*99;flags[12]=200
            good=dict(screen=10,map_record=8,editor_hard_flags=flags)
            f.write_text(json.dumps(good));out=editor_hard_flags_files(root)
            packet=json.loads(out['Hardness/SCR_010_editor_hard.json'])
            self.assertEqual(packet['editor_hard_flags'][12],200)
            self.assertEqual(packet['schema'],'dinkex.editor-hard/1')
            self.assertFalse((root/'hardness').exists())
            for value in [None,[0]*98,[False]*99,[2**31]*99]:
                f.write_text(json.dumps(dict(good,editor_hard_flags=value)))
                with self.assertRaises(ValueError):editor_hard_flags_files(root)
