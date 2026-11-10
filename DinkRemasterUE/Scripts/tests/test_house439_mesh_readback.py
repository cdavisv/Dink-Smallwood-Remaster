"""Concrete attribute matching failures; no native-runtime acceptance claim."""
from pathlib import Path
import sys,unittest,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'RoofNative'))
from house439_mesh_readback import compare_snapshot
NAMES=['MI_Shared_'+x for x in ['FieldstoneSeed2m','FieldstoneWall2m','WeatheredTimber2m','IronLead2m','LimeMortarSoot2m','DressedReed2m','ThinWavyGlass2m']]
ROLES={n:'/Game/Test/'+n for n in NAMES};TOL=dict(position_cm=.0001,normal_component=.0001,UV=.0001,raw_color=.0001,built_color=1/255,frame_unit=.001,frame_dot=.001)
def fixture():
    points=[[0.,0.,0.],[10.,0.,0.],[0.,10.,0.]];uv=[[0.,0.],[1.,0.],[0.,1.]];rgba=[.2,.4,.6,.8];source=[dict(material=NAMES[0],corners=[dict(position_cm=p,normal=[0.,0.,1.],UV0=u,UV1=[0.,.99],color=rgba)for p,u in zip(points,uv)])]
    raw=[[i]+p+[0.,0.,1.]+[1.,0.,0.]+[1.]+rgba+u+[0.,.99]for i,(p,u)in enumerate(zip(points,uv))];built=[p+[0.,0.,1.]+[1.,0.,0.]+[0.,1.,0.]+[1.]+[51,102,153,204]+u+[0.,.99]for p,u in zip(points,uv)]
    snap=dict(schema='dink-static-mesh-geometry/1',valid=True,slots=[dict(slot=i,imported_name=n,material_path=ROLES[n]+'.'+n)for i,n in enumerate(NAMES)],raw=dict(uv_channels=2,instances=raw,triangles=[[0,1,2,0]]),built=dict(uv_channels=2,color0_present=True,full_precision_uvs=True,vertices=built,indices=[0,1,2],sections=[dict(first_index=0,triangles=1,slot=0)]));return snap,source
class MeshReadbackTests(unittest.TestCase):
    def test_raw_and_built_correspondence(self):
        snap,source=fixture();r=compare_snapshot(snap,source,ROLES,TOL);self.assertTrue(r['passed']);self.assertTrue(r['raw_Color0_import_passed'])
    def test_uv1_v_flip_must_be_present(self):
        snap,source=fixture();snap['raw']['instances'][0][18]=.01
        with self.assertRaises(ValueError):compare_snapshot(snap,source,ROLES,TOL)
    def test_color0_gamma_change_rejected(self):
        snap,source=fixture();snap['built']['vertices'][0][13]=124
        with self.assertRaises(ValueError):compare_snapshot(snap,source,ROLES,TOL)
    def test_uvs_cannot_choose_ambiguous_geometry(self):
        snap,source=fixture();source.append(copy.deepcopy(source[0]));snap['raw']['triangles']*=2;snap['built']['indices']*=2;snap['built']['sections'][0]['triangles']=2
        with self.assertRaisesRegex(ValueError,'ambiguous'):compare_snapshot(snap,source,ROLES,TOL)
    def test_wrong_stored_tangent_sign_rejected(self):
        snap,source=fixture();snap['built']['vertices'][0][12]=-1
        with self.assertRaisesRegex(ValueError,'handedness'):compare_snapshot(snap,source,ROLES,TOL)
    def test_missing_actual_color_buffer_rejected(self):
        snap,source=fixture();snap['built']['color0_present']=False
        with self.assertRaises(ValueError):compare_snapshot(snap,source,ROLES,TOL)
    def test_large_color_tolerance_is_not_a_waiver(self):
        snap,source=fixture();tol=dict(TOL,built_color=.3)
        with self.assertRaisesRegex(ValueError,'quantization'):compare_snapshot(snap,source,ROLES,tol)
if __name__=='__main__':unittest.main()
