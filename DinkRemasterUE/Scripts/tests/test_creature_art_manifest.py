import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from creature_art_manifest import merge_runtime, validate_source


class CreatureManifestTests(unittest.TestCase):
    def test_incremental_import_keeps_pigs_and_removes_only_stale_reimported_origins(self):
        old = {'schema':'dink-creatures/1','assets':[{'mesh':'Pig'},{'mesh':'Pillbug'}],
               'placements':[{'origin':'S407_P02','mesh':'Pig','food_mesh':'Wheat'},
                             {'origin':'S438_P03','mesh':'Pillbug'},{'origin':'S438_P04','mesh':'Pillbug'}]}
        new = {'schema':'dink-creatures/1','assets':[{'mesh':'Pillbug','revision':2}],
               'placements':[{'origin':'S438_P03','mesh':'Pillbug'}]}
        before = copy.deepcopy(old)
        merged = merge_runtime(old,new)
        self.assertEqual(merged['placements'],[old['placements'][0],new['placements'][0]])
        self.assertEqual(merged['assets'],[old['assets'][0],new['assets'][0]])
        self.assertEqual(old,before)

    def test_conflicting_original_actor_and_duplicate_rows_are_rejected(self):
        old={'schema':'dink-creatures/1','assets':[{'mesh':'Pig'}],'placements':[{'origin':'S407_P02','mesh':'Pig'}]}
        new={'schema':'dink-creatures/1','assets':[{'mesh':'Pillbug'}],'placements':[{'origin':'S407_P02','mesh':'Pillbug'}]}
        with self.assertRaisesRegex(ValueError,'unrelated'):merge_runtime(old,new)
        new['placements']=[{'origin':'S438_P03','mesh':'Pillbug'}]*2
        with self.assertRaisesRegex(ValueError,'Duplicate'):merge_runtime(old,new)
        new['schema']='unknown'
        with self.assertRaisesRegex(ValueError,'schema'):merge_runtime(old,new)

    def test_nonfeeding_creature_has_no_pig_action_requirement_and_paths_stay_local(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'source';root.mkdir(); names=['LOD0.fbx','LOD1.fbx','LOD2.fbx','Idle.fbx','Walk.fbx']
            for name in names:(root/name).write_bytes(b'fixture input')
            spec={'schema':'dink-creature-art/1','assets':{'SK_Pillbug':{'class':'creature','fbx':'LOD0.fbx',
                 'lod_fbx':names[:3],'dimensions_m':[1.2,.95,.55],'bones':['root','head','pelvis'],
                 'body_boxes':[{'offset_cm':[0,0,20],'extent_cm':[50,30,20]}],'materials':['MI_Pillbug_Shell'],
                 'origins':['S438_P03']}},'materials':{'MI_Pillbug_Shell':{}},
                 'animations':{'Idle':{'fbx':'Idle.fbx','fps':40},'Walk':{'fbx':'Walk.fbx','fps':40,'nominal_speed_cm_s':80}}}
            validate_source(spec,root)
            spec['origins']=spec['assets']['SK_Pillbug'].pop('origins')
            validate_source(spec,root)
            spec['food_mesh']='Wheat'
            with self.assertRaisesRegex(ValueError,'Feed'):validate_source(spec,root)
            del spec['food_mesh']
            outside=Path(directory)/'escaped-creature-source.fbx';outside.write_bytes(b'outside')
            try:
                spec['animations']['Walk']['fbx']=str(outside)
                with self.assertRaisesRegex(ValueError,'escaped'):validate_source(spec,root)
            finally:outside.unlink()


if __name__=='__main__':unittest.main()
