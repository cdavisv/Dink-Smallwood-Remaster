import copy
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from RoofNative.closed_eaves_convex_compare import compare_convex


def fixture():
    cube=np.array([[x,y,z] for x in (0,1) for y in (0,1) for z in (0,1)],dtype=float)
    ref={str(i)+'_position_m':cube+[i*2,0,0] for i in range(6)}
    metadata=dict(hulls=[dict(name='UCX_'+str(i),array_prefix=str(i)) for i in range(6)])
    frame=dict(source_to_native_direction=[[1,0,0],[0,-1,0],[0,0,1]],position_scale=100,provenance='Synthetic explicit frame')
    matrix=np.asarray(frame['source_to_native_direction'])
    hulls=[dict(mesh_vertices=(ref[str(i)+'_position_m'][::-1]@matrix.T*100).tolist(),indices=[]) for i in reversed(range(6))]
    return ref,metadata,hulls,frame


class ConvexTests(unittest.TestCase):
    def test_six_permuted_hulls_and_vertices_match_without_physics_claim(self):
        report=compare_convex(*fixture())
        self.assertTrue(report['pass_convex_source_vertices']);self.assertFalse(report['cooked_physics_acceptance'])
        self.assertEqual(len(report['matched']),6)

    def test_count_shape_transform_indices_and_ambiguity_fail(self):
        for defect in ('count','shape','transform','indices','ambiguous'):
            ref,meta,hulls,frame=fixture()
            if defect=='count':hulls.pop()
            elif defect=='shape':hulls[0]['mesh_vertices'][0][0]+=.1
            elif defect=='transform':frame['source_to_native_direction']=[[2,0,0],[0,1,0],[0,0,1]]
            elif defect=='indices':hulls[0]['indices']=[0,1,99]
            else:ref['4_position_m']=ref['5_position_m'].copy()
            with self.subTest(defect=defect),self.assertRaises(ValueError):compare_convex(ref,meta,hulls,frame)


if __name__=='__main__':unittest.main()
