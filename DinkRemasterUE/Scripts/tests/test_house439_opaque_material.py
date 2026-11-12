"""Use actual registered Blender graph extraction to guard native source port."""
from pathlib import Path
import unittest,json,copy,importlib.util
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('house439_opaque',ROOT/'Scripts/RoofNative/house439_opaque_material.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
GRAPHS=json.loads((ROOT/'SourceAssets/Art/Stonebrook/Refinements/House439SharedExteriorV1/OPAQUE_GRAPH_SOURCE.json').read_text())['materials']
class OpaqueGraphTests(unittest.TestCase):
    def test_actual_six_graphs(self):
        self.assertEqual(len(GRAPHS),6)
        for name,g in GRAPHS.items():
            with self.subTest(material=name):module.validate_graph(g)
    def test_unknown_source_lobe_rejected(self):
        g=copy.deepcopy(next(iter(GRAPHS.values())));n=next(n for n in g['nodes']if n['type']=='BSDF_PRINCIPLED');next(x for x in n['inputs']if x['name']=='Transmission Weight')['value']=1
        with self.assertRaises(ValueError):module.validate_graph(g)
    def test_private_colour_field_rejected(self):
        g=copy.deepcopy(GRAPHS['MI_Shared_FieldstoneSeed2m']);next(n for n in g['nodes']if n['type']=='VERTEX_COLOR')['layer_name']='House439Private'
        with self.assertRaises(ValueError):module.validate_graph(g)
    def test_extra_disconnected_node_rejected(self):
        g=copy.deepcopy(next(iter(GRAPHS.values())));n=copy.deepcopy(next(n for n in g['nodes']if n['type']=='UVMAP'));n['name']='HiddenExtra';g['nodes'].append(n)
        with self.assertRaises(ValueError):module.validate_graph(g)
    def test_unknown_selector_operation_rejected(self):
        g=copy.deepcopy(GRAPHS['MI_Shared_IronLead2m']);next(n for n in g['nodes']if n['type']=='MATH')['operation']='LESS_THAN'
        with self.assertRaises(ValueError):module.validate_graph(g)
    def test_cyclic_shader_rejected(self):
        g=copy.deepcopy(GRAPHS['MI_Shared_FieldstoneSeed2m']);name=next(n['name']for n in g['nodes']if n['type']=='MATH');edge=next(e for e in g['links']if e['to_node']==name);edge['from_node']=name;edge['from_socket']=0
        with self.assertRaises(ValueError):module.validate_graph(g)
if __name__=='__main__':unittest.main()
