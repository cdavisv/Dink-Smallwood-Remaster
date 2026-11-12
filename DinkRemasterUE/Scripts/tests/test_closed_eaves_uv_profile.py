import copy
import json
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from test_closed_eaves_geometry_compare import fixture
from test_closed_eaves_built_geometry_compare import built_fixture
from RoofNative.closed_eaves_built_geometry_compare import compare_built
from RoofNative.closed_eaves_geometry_compare import compare_raw
from RoofNative.closed_eaves_linear_color_restore import restore_imported_colors
from RoofNative.closed_eaves_uv_profile import canonical_guard, reference_uvs, GUARDED


def guarded():
    ref,g,f=fixture()
    ref['uv2_weld_seam_guard']=canonical_guard(ref)[0]
    guard=ref['uv2_weld_seam_guard'].copy();guard[:,1]=1-guard[:,1]
    for row,tag in zip(g['raw']['instances'],guard):row.extend(tag.tolist())
    g['raw']['uv_channels']=3
    return ref,g,f


class UV2Controls(unittest.TestCase):
    def test_valid_explicit_profile_passes(self):
        ref,g,f=guarded()
        self.assertTrue(compare_raw(ref,['stone'],g,f,transport_profile=GUARDED)['pass_raw'])

    def test_legacy_default_stays_strict(self):
        ref,g,f=guarded()
        with self.assertRaises(ValueError):compare_raw(ref,['stone'],g,f)
        ref,g,f=fixture()
        self.assertTrue(compare_raw(ref,['stone'],g,f)['pass_raw'])

    def test_unknown_profile_refused(self):
        ref,g,f=guarded()
        with self.assertRaises(ValueError):compare_raw(ref,['stone'],g,f,transport_profile='unknown')

    def test_distinct_bits_and_signed_zero_get_distinct_ids(self):
        ref,g,f=fixture()
        ref['uv0']=np.array([[0.,0.],[-0.,0.],[np.nextafter(np.float32(0),np.float32(1)),0]],dtype=np.float32)
        guard,ids=canonical_guard(ref)
        self.assertEqual(len(set(ids.tolist())),3)

    def test_corruptions_refused_before_native_write(self):
        for defect in ('missing','reference_alias','fractional','negative','overflow','inventory','reassociation','dropped','original_uv'):
            ref,g,f=guarded()
            if defect=='missing':del ref['uv2_weld_seam_guard']
            elif defect=='reference_alias':ref['uv2_weld_seam_guard'][0]=ref['uv2_weld_seam_guard'][1]
            elif defect=='fractional':g['raw']['instances'][0][-2]+=.5
            elif defect=='negative':g['raw']['instances'][0][-2]=-1
            elif defect=='overflow':g['raw']['instances'][0][-2]=1024
            elif defect=='inventory':g['raw']['instances'][0][-2:]=g['raw']['instances'][1][-2:]
            elif defect=='reassociation':
                a,b=g['raw']['instances'][:2];a[-2:],b[-2:]=b[-2:],a[-2:]
            elif defect=='dropped':g['raw']['uv_channels']=2
            elif defect=='original_uv':g['raw']['instances'][0][15]+=.00001
            class Library:
                writes=0
                @staticmethod
                def inspect_static_mesh_geometry(mesh,lod):return json.dumps(g)
                @classmethod
                def restore_candidate_static_mesh_linear_colors(cls,*args):
                    cls.writes+=1
                    raise AssertionError('Invalid seam data reached native write')
            class Native:
                DinkMaterialArtLibrary=Library
                @staticmethod
                def LinearColor(*args):return args
            with self.subTest(defect=defect):
                with self.assertRaises(ValueError):restore_imported_colors(Native,None,ref,['stone'],f,lambda:None,transport_profile=GUARDED)
                self.assertEqual(Library.writes,0)

    def test_built_three_channel_pass_and_original_or_guard_corruption_fails(self):
        for defect in ('none','original','guard','reassociation','dropped'):
            ref,g,f=built_fixture()
            ref['uv2_weld_seam_guard']=canonical_guard(ref)[0]
            tags=ref['uv2_weld_seam_guard'].copy();tags[:,1]=1-tags[:,1]
            for row,tag in zip(g['raw']['instances'],tags):row.extend(tag.tolist())
            for row,tag in zip(g['built']['vertices'],tags):row.extend(tag.tolist())
            g['raw']['uv_channels']=g['built']['uv_channels']=3
            if defect=='original':g['built']['vertices'][0][17]+=.00001
            elif defect=='guard':g['built']['vertices'][0][-2]+=.00001
            elif defect=='reassociation':
                a,b=g['built']['vertices'][:2];a[-2:],b[-2:]=b[-2:],a[-2:]
            elif defect=='dropped':g['built']['uv_channels']=2
            with self.subTest(defect=defect):
                if defect=='none':self.assertTrue(compare_built(ref,['stone'],g,f,transport_profile=GUARDED)['pass_built_structure_and_encoding'])
                else:
                    with self.assertRaises(ValueError):compare_built(ref,['stone'],g,f,transport_profile=GUARDED)

class SourceEpochControls(unittest.TestCase):
    def test_exact_source_epoch_and_each_pin_tamper(self):
        import tempfile
        from pathlib import Path
        from RoofNative.closed_eaves_guarded_epoch import load_guarded_epoch,PROFILE
        source=Path(__file__).resolve().parents[2]/'SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1/UV2WeldSeamGuardV1'
        members=['FBX/SM_Cottage_Stonebrook_01.fbx','Reference/REFERENCE.json','Reference/SOURCE_GEOMETRY_WITH_UV2_GUARD.npz','Evidence/SERIALIZED_UV2_GUARD_READBACK_V2.json']
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            folder=root/'SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1/UV2WeldSeamGuardV1'
            for name in members:
                dst=folder/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.symlink_to(source/name)
            epoch=load_guarded_epoch(root)
            self.assertEqual(epoch['transport_profile'],PROFILE)
            self.assertEqual(epoch['expected_uv_channels'],3)
            for name in members:
                dst=folder/name;dst.unlink();dst.write_bytes(b'corrupted')
                with self.subTest(member=name),self.assertRaises(ValueError):load_guarded_epoch(root)
                dst.unlink();dst.symlink_to(source/name)

    def test_native_plan_selects_profile_without_changing_legacy_pins(self):
        import tempfile
        from pathlib import Path
        from RoofNative.closed_eaves_native_trial import prepare_trial
        project=Path(__file__).resolve().parents[2]
        legacy=prepare_trial(project)
        self.assertEqual(legacy['expected_uv_channels'],2)
        self.assertEqual(legacy['transport_profile'],'legacy_2uv')
        with self.assertRaises(ValueError):prepare_trial(project,transport_profile='unknown')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'Docs').symlink_to(project/'Docs')
            (root/'SourceAssets/Art').mkdir(parents=True)
            (root/'SourceAssets/Art/SharedMaterials').symlink_to(project/'SourceAssets/Art/SharedMaterials')
            target=root/'SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1/UV2WeldSeamGuardV1'
            target.parent.mkdir(parents=True)
            target.symlink_to(project/'SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1/UV2WeldSeamGuardV1')
            guarded=prepare_trial(root,transport_profile=GUARDED)
            self.assertEqual(guarded['expected_uv_channels'],3)
            self.assertEqual(guarded['mesh_sha256'],'d3cdb0dc1ded99283873481c3ee310ec8486358a75cf66cc589d24e420da5a6c')
            self.assertEqual(guarded['graphs'],legacy['graphs'])
            self.assertEqual(guarded['mesh_precision'],legacy['mesh_precision'])
