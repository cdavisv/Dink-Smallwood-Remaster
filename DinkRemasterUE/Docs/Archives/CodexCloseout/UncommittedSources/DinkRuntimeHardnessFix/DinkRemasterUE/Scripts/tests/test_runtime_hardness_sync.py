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
            packet=dict(schema='dinkex.runtime-hardness/1',width=600,height=400,vision=-3,skipped_tile_indices=[])
            raw=(json.dumps(packet,indent=3)+'\n').encode()
            (root/'hardness/SCR_209_v-3_layers.json').write_bytes(raw)
            self.assertEqual(hardness_layers(root),{'Hardness/SCR_209_v-3_layers.json':raw})
    def test_unsupported_envelopes_refuse_before_any_project_writer(self):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);(root/'hardness').mkdir();file=root/'hardness/SCR_209_layers.json'
            good=dict(schema='dinkex.runtime-hardness/1',width=600,height=400,vision=0,skipped_tile_indices=[])
            for field,value in [('vision',1),('vision',True),('width',True),('schema','legacy'),('skipped_tile_indices',[7])]:
                packet=dict(good);packet[field]=value;file.write_text(json.dumps(packet))
                with self.assertRaises(ValueError):hardness_layers(root)
