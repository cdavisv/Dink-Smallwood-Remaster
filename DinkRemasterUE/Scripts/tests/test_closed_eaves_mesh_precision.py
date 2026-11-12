"""Storage-plan control flow; actual native settings/buffers need engine proof."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from RoofNative.closed_eaves_native_trial import apply_mesh_precision


class Settings:
    def __init__(self,values):self.values=copy.deepcopy(values)
    def copy(self):return Settings(self.values)
    def set_editor_property(self,key,value):self.values[key]=value
    def get_editor_property(self,key):return self.values[key]
    def to_dict(self):return copy.deepcopy(self.values)
    def export_text(self):return json.dumps(self.values,sort_keys=True)


class Subsystem:
    def __init__(self,corrupt=False):
        self.settings=Settings(dict(use_full_precision_u_vs=False,use_high_precision_tangent_basis=False,
            recompute_normals=False,recompute_tangents=False,generate_lightmap_u_vs=False,
            remove_degenerates=False,unrelated_future_setting={'value':[3,7]}))
        self.corrupt=corrupt;self.writes=0
    def get_lod_build_settings(self,mesh,lod):return self.settings.copy()
    def set_lod_build_settings(self,mesh,lod,settings):
        self.writes+=1;self.settings=settings.copy()
        if self.corrupt:self.settings.values['recompute_normals']=True


class MeshPrecisionTests(unittest.TestCase):
    def test_two_precision_fields_only_and_detached_copy(self):
        sub=Subsystem();before=sub.settings.copy();plan=dict(use_full_precision_u_vs=True,use_high_precision_tangent_basis=True)
        result=apply_mesh_precision(sub,object(),plan,lambda:None)
        expected=before.copy()
        for key,value in plan.items():expected.values[key]=value
        self.assertEqual(sub.settings.to_dict(),expected.to_dict());self.assertFalse(before.values['use_full_precision_u_vs'])
        self.assertEqual(sub.writes,1);self.assertEqual(result['flags'],plan)
    def test_native_unrelated_setting_change_refused(self):
        with self.assertRaisesRegex(RuntimeError,'unrelated settings'):
            apply_mesh_precision(Subsystem(corrupt=True),object(),dict(use_full_precision_u_vs=True,use_high_precision_tangent_basis=True),lambda:None)
    def test_revocation_refuses_before_write(self):
        sub=Subsystem()
        def denied():raise RuntimeError('revoked')
        with self.assertRaisesRegex(RuntimeError,'revoked'):
            apply_mesh_precision(sub,object(),dict(use_full_precision_u_vs=True,use_high_precision_tangent_basis=True),denied)
        self.assertEqual(sub.writes,0)
    def test_unsupported_snapshot_type_refused_before_write(self):
        sub=Subsystem();sub.settings.values['unsupported']=object()
        with self.assertRaisesRegex(ValueError,'Unsupported build-setting'):
            apply_mesh_precision(sub,object(),dict(use_full_precision_u_vs=True,use_high_precision_tangent_basis=True),lambda:None)
        self.assertEqual(sub.writes,0)
    def test_nonfinite_snapshot_refused_before_write(self):
        sub=Subsystem();sub.settings.values['distance_field_resolution_scale']=float('nan')
        with self.assertRaisesRegex(ValueError,'Nonfinite build setting'):
            apply_mesh_precision(sub,object(),dict(use_full_precision_u_vs=True,use_high_precision_tangent_basis=True),lambda:None)
        self.assertEqual(sub.writes,0)
    def test_unrequested_build_field_refused_before_write(self):
        sub=Subsystem()
        with self.assertRaisesRegex(ValueError,'Exact source-preserving'):
            apply_mesh_precision(sub,object(),dict(use_full_precision_u_vs=True,use_high_precision_tangent_basis=True,recompute_tangents=True),lambda:None)
        self.assertEqual(sub.writes,0)


if __name__=='__main__':unittest.main()
