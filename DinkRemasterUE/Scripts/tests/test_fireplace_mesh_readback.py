"""Three UV channels, RAW color representation, alpha and stored signed-frame negatives."""
from pathlib import Path
import sys,unittest,copy
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'Scripts/RoofNative'))
from fireplace_mesh_readback import compare_snapshot,fbx_color_to_raw_linear
N='MI_Shared_FiredClay2m';ROLES={N:'/Game/Test/Clay'};TOL=dict(position_cm=.0001,normal_component=.0001,UV=.0001,raw_color=.0001,built_color=1/255,frame_unit=.001,frame_dot=.001)
def fixture():
    points=[[0.,0.,0.],[10.,0.,0.],[0.,10.,0.]];uv=[[0.,1.],[1.,1.],[0.,0.]];rgba=[.5,.44,1.,.5];rawcolor=fbx_color_to_raw_linear(rgba);source=[dict(material=N,corners=[dict(position_cm=p,normal=[0.,0.,1.],UV0=u,UV1=[1.,1.],UVMap=u,color=rgba,raw_color=rawcolor)for p,u in zip(points,uv)])]
    raw=[[i]+p+[0.,0.,1.]+[1.,0.,0.]+[1.]+rawcolor+u+[1.,1.]+u for i,(p,u)in enumerate(zip(points,uv))];built=[p+[0.,0.,1.]+[1.,0.,0.]+[0.,1.,0.]+[1.]+[127,112,255,127]+u+[1.,1.]+u for p,u in zip(points,uv)]
    snap=dict(schema='dink-static-mesh-geometry/1',valid=True,slots=[dict(slot=0,imported_name=N,material_path=ROLES[N]+'.Clay')],raw=dict(uv_channels=3,instances=raw,triangles=[[0,1,2,0]]),built=dict(uv_channels=3,color0_present=True,full_precision_uvs=True,vertices=built,indices=[0,1,2],sections=[dict(first_index=0,triangles=1,slot=0)]));return snap,source
class FireplaceMeshReadbackTests(unittest.TestCase):
    def test_raw_and_built_three_uv_and_alpha(self):
        a,b=fixture();self.assertTrue(compare_snapshot(a,b,ROLES,TOL)['passed'])
    def test_hdr_original_is_not_silently_clamped_in_built_reference(self):
        a,b=fixture()
        for row,corner in zip(a['raw']['instances'],b[0]['corners']):
            corner['color'][0]=1.0197542905807495
            corner['raw_color']=fbx_color_to_raw_linear(corner['color'])
            row[11:15]=corner['raw_color']
        for row in a['built']['vertices']:row[13]=255
        with self.assertRaisesRegex(ValueError,'corner attributes differ'):
            compare_snapshot(a,b,ROLES,TOL)
    def corrupt(self,change):
        a,b=fixture();change(a)
        with self.assertRaises(ValueError):compare_snapshot(a,b,ROLES,TOL)
    def test_raw_rgb_cannot_be_original_semantic(self):self.corrupt(lambda a:a['raw']['instances'][0].__setitem__(11,.5))
    def test_raw_alpha_is_not_srgb_decoded(self):self.corrupt(lambda a:a['raw']['instances'][0].__setitem__(14,.2122307574))
    def test_built_rgb_cannot_be_srgb_decoded_raw(self):self.corrupt(lambda a:a['built']['vertices'][0].__setitem__(13,54))
    def test_uv1_flip_required(self):self.corrupt(lambda a:a['raw']['instances'][0].__setitem__(18,0.))
    def test_uvmap_alias_cannot_disappear_or_change(self):self.corrupt(lambda a:a['built']['vertices'][0].__setitem__(22,.1))
    def test_zero_native_tangent_fails_even_for_qualified_source(self):
        def change(a):a['built']['vertices'][0][6:9]=[0.,0.,0.]
        self.corrupt(change)
    def test_actual_tangent_y_sign_required(self):self.corrupt(lambda a:a['built']['vertices'][0].__setitem__(12,-1.))
    def test_material_or_pivot_shift_rejected(self):self.corrupt(lambda a:a['raw']['instances'][0].__setitem__(1,1.))
    def test_ambiguous_geometry_cannot_use_uv_or_color_to_match(self):
        a,b=fixture();b.append(copy.deepcopy(b[0]));a['raw']['triangles']*=2;a['built']['indices']*=2;a['built']['sections'][0]['triangles']=2
        with self.assertRaisesRegex(ValueError,'ambiguous'):compare_snapshot(a,b,ROLES,TOL)
if __name__=='__main__':unittest.main()
