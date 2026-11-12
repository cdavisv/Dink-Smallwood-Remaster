"""Safety regressions for an unexecuted source-only native glass adapter."""
import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).resolve().parents[1]/'RoofNative/house439_glass_material.py'
spec=importlib.util.spec_from_file_location('house439_glass',P)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def valid():
    return dict(profile='thin_transmissive_surface_2m',front_back_policy='closed_panes_front_faces_only',
                native_policy_reviewed=True,physical_uv_reviewed=True,uv_channel=2,transmission=1,
                surface_coverage=1,top_material_coverage=0,IOR=1.48,unreal_specular=.4682622268470343,
                textures={'BC':'/Game/Test/BC','N':'/Game/Test/N','ORM':'/Game/Test/ORM'},
                two_sided=False,substrate_enabled=False)

class ForbiddenEngine:
    def __getattr__(self,key):
        raise AssertionError('Engine must not be touched before recipe rejection: '+key)

class GlassContractTests(unittest.TestCase):
    def reject_before_engine(self,key,value):
        r=valid();r[key]=value
        with self.assertRaises(ValueError):
            module.build_graph(ForbiddenEngine(),None,r,{},lambda:None)
    def test_registered_fresnel(self):
        self.assertAlmostEqual(module.validate_recipe(valid()),.037460978147762745,places=14)
    def test_opaque_top_layer_rejected(self):
        self.reject_before_engine('top_material_coverage',1)
    def test_unreviewed_closed_panes_rejected(self):
        self.reject_before_engine('native_policy_reviewed',False)
    def test_unreviewed_coordinate_rejected(self):
        self.reject_before_engine('physical_uv_reviewed',False)
    def test_unsupported_substrate_rejected(self):
        self.reject_before_engine('substrate_enabled',True)
    def test_two_sided_closed_panes_rejected(self):
        self.reject_before_engine('two_sided',True)
    def test_opaque_profile_rejected(self):
        self.reject_before_engine('profile','opaque_surface_2m')
    def test_wrong_ior_or_fresnel_rejected(self):
        self.reject_before_engine('IOR',1.5)
        self.reject_before_engine('unreal_specular',.5)
    def test_invalid_coordinate_rejected(self):
        for bad in [-1,8,True,None]:self.reject_before_engine('uv_channel',bad)

if __name__=='__main__':unittest.main()
