import copy
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from RoofNative.closed_eaves_geometry_compare import compare_raw


def fixture():
    ref=dict(position_m=np.array([[0.,0,0],[1,0,0],[0,1,0]]),
             normal=np.tile([0.,0,1],(3,1)),tangent=np.tile([1.,0,0],(3,1)),
             bitangent_sign=np.ones(3),uv0=np.array([[0.,0],[1,0],[0,1]]),
             uv1=np.tile([.3,.7],(3,1)),color_linear_rgba=np.tile([.2,.4,.6,.8],(3,1)),
             triangles=np.array([[0,1,2]]),triangle_material=np.array([0]))
    frame=dict(source_to_native_direction=[[1,0,0],[0,-1,0],[0,0,1]],position_scale=100,
               uv_v_flip=True,reverse_winding=False,provenance='Synthetic explicitly declared test frame')
    rotation=np.array(frame['source_to_native_direction'])
    uv=np.concatenate((ref['uv0'],ref['uv1']),axis=1);uv[:,[1,3]]=1-uv[:,[1,3]]
    rows=np.column_stack(([30,10,20],ref['position_m']@rotation.T*100,
        ref['normal']@rotation.T,ref['tangent']@rotation.T,ref['bitangent_sign'],ref['color_linear_rgba'],uv))
    geometry=dict(schema='dink-static-mesh-geometry/1',valid=True,
                  slots=[dict(slot=0,imported_name='stone')],
                  raw=dict(uv_channels=2,instances=rows.tolist(),triangles=[[10,20,30,0]]))
    return ref,geometry,frame


class GeometryComparisonTests(unittest.TestCase):
    def test_reordered_corner_ids_and_cyclic_triangle_pass(self):
        ref,g,f=fixture();report=compare_raw(ref,['stone'],g,f)
        self.assertTrue(report['pass_raw']);self.assertEqual(report['source_corner_by_native_instance'],{30:0,10:1,20:2})

    def test_color_import_conversion_is_failure_not_tolerance_waiver(self):
        ref,g,f=fixture();g['raw']['instances'][0][11]=.033
        report=compare_raw(ref,['stone'],g,f)
        self.assertFalse(report['pass_raw']);self.assertAlmostEqual(report['max_linear_RGBA_error'][0],.167)

    def test_uv_geometry_winding_material_and_frame_corruption_rejected(self):
        for defect in ('uv','position','winding','material','frame'):
            ref,g,f=fixture()
            if defect=='uv':g['raw']['instances'][0][16]+=.01
            elif defect=='position':g['raw']['instances'][0][1]+=.01
            elif defect=='winding':g['raw']['triangles'][0][:3]=[10,30,20]
            elif defect=='material':g['slots'][0]['imported_name']='wrong'
            else:f['provenance']=''
            with self.subTest(defect=defect),self.assertRaises(ValueError):compare_raw(ref,['stone'],g,f)

    def test_tangent_normal_and_sign_changes_fail(self):
        for channel in (4,8,10):
            ref,g,f=fixture();g['raw']['instances'][0][channel]=1 if channel!=10 else -1
            with self.subTest(channel=channel):self.assertFalse(compare_raw(ref,['stone'],g,f)['pass_raw'])

    def test_ambiguous_overlapping_triangles_are_not_arbitrarily_assigned(self):
        ref,g,f=fixture()
        for key in ('position_m','normal','tangent','bitangent_sign','uv0','uv1','color_linear_rgba'):
            ref[key]=np.concatenate((ref[key],ref[key]))
        ref['color_linear_rgba'][3,0]=.9
        ref['triangles']=np.array([[0,1,2],[3,4,5]]);ref['triangle_material']=np.array([0,0])
        extra=copy.deepcopy(g['raw']['instances'])
        for row in extra:row[0]+=100
        g['raw']['instances']+=extra;g['raw']['triangles'].append([110,120,130,0])
        with self.assertRaisesRegex(ValueError,'Ambiguous'):compare_raw(ref,['stone'],g,f)


if __name__=='__main__':unittest.main()
