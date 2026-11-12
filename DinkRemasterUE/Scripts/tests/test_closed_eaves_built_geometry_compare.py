from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from RoofNative.closed_eaves_built_geometry_compare import compare_built
from test_closed_eaves_geometry_compare import fixture


def built_fixture():
    ref,g,frame=fixture();raw=np.asarray(g['raw']['instances'])
    color=ref['color_linear_rgba']
    encoded=color.copy();encoded[:,:3]=np.where(color[:,:3]<=.0031308,color[:,:3]*12.92,1.055*color[:,:3]**(1/2.4)-.055)
    byte=np.floor(encoded*255+.5)
    expected=np.column_stack((raw[:,0],byte))
    g['raw']['expected_built_color_rgba8']=expected.tolist()
    y=np.cross(raw[:,4:7],raw[:,7:10])*raw[:,10,None]
    vertices=np.column_stack((raw[:,1:10],y,raw[:,10],byte,raw[:,15:19]))
    g['built']=dict(uv_channels=2,color0_present=True,vertices=vertices.tolist(),indices=[1,2,0],
                    sections=[dict(first_index=0,triangles=1,slot=0)])
    return ref,g,frame


class BuiltGeometryTests(unittest.TestCase):
    def test_reordered_built_indices_and_exact_native_color_bytes_pass(self):
        ref,g,f=built_fixture();report=compare_built(ref,['stone'],g,f)
        self.assertTrue(report['pass_built_structure_and_encoding'])
        self.assertTrue(report['exact_native_encoded_bytes'])
        self.assertFalse(report['pixel_or_appearance_acceptance'])
        self.assertGreater(max(report['decoded_quantization_RGBA_error']),0)

    def test_built_color_normal_uv_bitangent_and_section_corruption_refused(self):
        for defect in ('byte','normal','uv','bitangent','section','missing_color'):
            ref,g,f=built_fixture()
            if defect=='byte':g['built']['vertices'][0][13]+=1
            elif defect=='normal':g['built']['vertices'][0][3]=.2
            elif defect=='uv':g['built']['vertices'][0][18]+=.1
            elif defect=='bitangent':g['built']['vertices'][0][10]=-1
            elif defect=='section':g['built']['sections']=[]
            else:g['built']['color0_present']=False
            with self.subTest(defect=defect),self.assertRaises(ValueError):compare_built(ref,['stone'],g,f)


if __name__=='__main__':unittest.main()
