import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from RoofNative.closed_eaves_linear_color_restore import restore_imported_colors
from test_closed_eaves_geometry_compare import fixture


class NativeFake:
    def __init__(self,geometry,stale=False):
        self.geometry=copy.deepcopy(geometry);self.calls=0;self.stale=stale
    def inspect_static_mesh_geometry(self,mesh,lod):
        result=json.dumps(self.geometry)
        if self.stale:self.geometry['raw']['instances'][0][1]+=1
        return result
    def restore_candidate_static_mesh_linear_colors(self,mesh,before,ids,colors):
        self.calls+=1
        if before!=json.dumps(self.geometry):return json.dumps(dict(valid=False,error='stale_snapshot',mutated=False))
        by_id={int(row[0]):row for row in self.geometry['raw']['instances']}
        for instance,color in zip(ids,colors):by_id[instance][11:15]=color
        return json.dumps(self.geometry)


class ColorRestoreTests(unittest.TestCase):
    def test_exact_color_restoration_and_already_correct_noop(self):
        ref,g,frame=fixture();g['raw']['instances'][0][11]=.033
        bridge=NativeFake(g);U=SimpleNamespace(DinkMaterialArtLibrary=bridge,LinearColor=lambda *v:list(v))
        result=restore_imported_colors(U,object(),ref,['stone'],frame,lambda:None)
        self.assertTrue(result['changed']);self.assertFalse(result['saved']);self.assertTrue(result['comparison']['pass_raw'])
        self.assertEqual(bridge.calls,1)
        again=restore_imported_colors(U,object(),ref,['stone'],frame,lambda:None)
        self.assertFalse(again['changed']);self.assertEqual(bridge.calls,1)
        for before,after in zip(g['raw']['instances'],bridge.geometry['raw']['instances']):
            self.assertEqual(before[:11],after[:11]);self.assertEqual(before[15:],after[15:])
        self.assertEqual(g['raw']['triangles'],bridge.geometry['raw']['triangles'])

    def test_noncolor_failure_never_calls_mutator(self):
        for channel in (4,8,15):
            ref,g,frame=fixture();g['raw']['instances'][0][channel]+=.2
            bridge=NativeFake(g);U=SimpleNamespace(DinkMaterialArtLibrary=bridge,LinearColor=lambda *v:list(v))
            with self.subTest(channel=channel),self.assertRaises(ValueError):
                restore_imported_colors(U,object(),ref,['stone'],frame,lambda:None)
            self.assertEqual(bridge.calls,0)

    def test_stale_snapshot_failure_requires_discard_not_retry_or_acceptance(self):
        ref,g,frame=fixture();g['raw']['instances'][0][11]=.033
        bridge=NativeFake(g,stale=True);U=SimpleNamespace(DinkMaterialArtLibrary=bridge,LinearColor=lambda *v:list(v))
        with self.assertRaisesRegex(RuntimeError,'discard trial editor.*stale_snapshot'):
            restore_imported_colors(U,object(),ref,['stone'],frame,lambda:None)
        self.assertEqual(bridge.calls,1)


if __name__=='__main__':unittest.main()
