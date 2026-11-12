import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sync_gameplay_data import hardness_layers

class RuntimeLayerSyncTests(unittest.TestCase):
    def source_without_variants(self, root):
        (root/'hardness').mkdir();(root/'screens').mkdir()
        packet=dict(schema='dinkex.runtime-hardness/2',width=600,height=400,vision=0,
                    skipped_tile_indices=[],editor_hard_flags=[0]*99,
                    tile_base_rle=[[[600,0]]]*400,ordered_stamps=[])
        (root/'hardness/SCR_276_layers.json').write_text(json.dumps(packet))
        (root/'screens/SCR_276.json').write_text(json.dumps({'hardness':{'vision_variants':{}}}))
        return packet
    def test_required_unused_visions_preserve_original_overlay(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);packet=self.source_without_variants(root)
            source=(root/'hardness/SCR_276_layers.json').read_bytes()
            result=hardness_layers(root,{276:{1,2}})
            for vision in (1,2):
                self.assertEqual(json.loads(result[f'Hardness/SCR_276_v{vision}_layers.json']),dict(packet,vision=vision))
            self.assertEqual((root/'hardness/SCR_276_layers.json').read_bytes(),source)
    def test_retained_unused_vision_must_match_source_and_keeps_exact_bytes(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);packet=self.source_without_variants(root);retained=root/'reviewed';retained.mkdir()
            file=retained/'SCR_276_v1_layers.json';raw=json.dumps(dict(packet,vision=1),indent=3).encode();file.write_bytes(raw)
            self.assertEqual(hardness_layers(root,{276:{1}},retained)['Hardness/SCR_276_v1_layers.json'],raw)
            changed=dict(packet,vision=1,ordered_stamps=[{'owner':3}]);file.write_text(json.dumps(changed));before=file.read_bytes()
            with self.assertRaisesRegex(ValueError,'retained vision differs'):hardness_layers(root,{276:{1}},retained)
            self.assertEqual(file.read_bytes(),before)
    def test_declared_vision_cannot_be_inferred_when_source_sidecar_is_missing(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);self.source_without_variants(root)
            (root/'screens/SCR_276.json').write_text(json.dumps({'hardness':{'vision_variants':{'1':'hardness/SCR_276_v1.png'}}}))
            with self.assertRaisesRegex(ValueError,'missing declared source vision'):hardness_layers(root,{276:{1}})
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
