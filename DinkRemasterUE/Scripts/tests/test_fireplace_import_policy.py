"""Saved policy drift must fail even when unchanged mesh buffers still match."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'RoofNative'))
from fireplace_mesh_readback import inspect_import_policy

def fixture():
 U=NS(FBXNormalImportMethod=NS(FBXNIM_IMPORT_NORMALS='normals'),FBXNormalGenerationMethod=NS(MIKK_T_SPACE='mikk'),VertexColorImportOption=NS(REPLACE='replace'))
 values=dict(combine_meshes=False,import_mesh_lo_ds=False,remove_degenerates=False,normal_import_method='normals',normal_generation_method='mikk',vertex_color_import_option='replace',auto_generate_collision=False,one_convex_hull_per_ucx=True,generate_lightmap_u_vs=False,convert_scene=True,convert_scene_unit=True,force_front_x_axis=False,import_uniform_scale=1.,transform_vertex_to_absolute=True,bake_pivot_in_vertex=False,import_translation=NS(x=45.9375,y=597.1875,z=0.),import_rotation=NS(pitch=0.,yaw=0.,roll=0.))
 def mutate(*a):raise AssertionError('Readback mutated native metadata')
 data=NS(get_editor_property=values.__getitem__,set_editor_property=mutate)
 return U,data,values,dict(import_translation_cm=[45.9375,597.1875,0.])

class FireplaceImportPolicyTests(unittest.TestCase):
 def test_reviewed_saved_profile_is_read_only(self):
  U,data,values,record=fixture();result=inspect_import_policy(U,data,record)
  self.assertTrue(result['passed']);self.assertEqual(len(result['checked_properties']),15)
 def test_each_saved_policy_field_drift_refuses(self):
  changes=dict(combine_meshes=True,import_mesh_lo_ds=True,remove_degenerates=True,normal_import_method='compute',normal_generation_method='builtin',vertex_color_import_option='ignore',auto_generate_collision=True,one_convex_hull_per_ucx=False,generate_lightmap_u_vs=True,convert_scene=False,convert_scene_unit=False,force_front_x_axis=True,import_uniform_scale=100.,transform_vertex_to_absolute=False,bake_pivot_in_vertex=True)
  for key,value in changes.items():
   with self.subTest(property=key):
    U,data,values,record=fixture();values[key]=value
    with self.assertRaisesRegex(ValueError,key):inspect_import_policy(U,data,record)
 def test_each_rotation_component_drift_refuses(self):
  for component in ['pitch','yaw','roll']:
   with self.subTest(component=component):
    U,data,values,record=fixture();setattr(values['import_rotation'],component,90.)
    with self.assertRaisesRegex(ValueError,'rotation'):inspect_import_policy(U,data,record)
 def test_pivot_translation_drift_refuses(self):
  U,data,values,record=fixture();values['import_translation'].y=-597.1875
  with self.assertRaisesRegex(ValueError,'compensation'):inspect_import_policy(U,data,record)

if __name__=='__main__':unittest.main()
