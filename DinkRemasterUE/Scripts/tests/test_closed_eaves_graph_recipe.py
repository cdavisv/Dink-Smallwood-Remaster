import copy
import json
import hashlib
import sys
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Scripts'))
from RoofNative.closed_eaves_graph_recipe import active_recipe, build_with_adapter, validate_raw_normal_binding
from RoofNative.closed_eaves_graph_lowering import lower_recipe
from RoofNative.closed_eaves_graph_oracle import evaluate
SOURCE = ROOT / 'SourceAssets/Art/SharedMaterials/ClosedEavesSurfaceCandidatesV1/EXTRACTION.json'


class RecordingAdapter:
    def __init__(self, reject=False):
        self.events = []
        self.reject = reject

    def validate_recipe(self, recipe):
        if self.reject:
            raise ValueError('Native texture/BSDF semantics not qualified')
        self.events.append(('preflight', recipe['role']))

    def create_node(self, node):
        self.events.append(('create', node))
        return node['name']

    def connect(self, *args):
        self.events.append(('connect', args))


class GraphRecipeTests(unittest.TestCase):
    def test_on_disk_seven_recipe_and_lowered_artifacts_regenerate_exactly(self):
        q=ROOT/'Docs/Verification/House439ClosedEavesNative/MaterialProfile'
        active=json.loads((q/'ACTIVE_GRAPH_RECIPES.json').read_text())['roles']
        lowered=json.loads((q/'LOWERED_MATERIAL_OPERATIONS.json').read_text())['roles']
        self.assertEqual(set(active),set(self.roles))
        self.assertEqual(set(lowered),set(self.roles))
        for role,record in self.roles.items():
            recipe=active_recipe(role,record,self.semantics[role])
            self.assertEqual(active[role],recipe)
            self.assertEqual(lowered[role],lower_recipe(recipe))

    def numerical_fixture(self, role, roughness=.3):
        recipe = active_recipe(role, self.roles[role], self.semantics[role])
        samples = {n['image']['sha256']: [.2, roughness, .8]
                   for n in recipe['nodes'] if 'image' in n}
        images = {n['name']: n['image']['sha256'] for n in recipe['nodes'] if 'image' in n}
        return lower_recipe(recipe), samples, images

    def test_numerical_variant_boundary_and_photo_fractional_selector(self):
        for role in ('WeatheredTimber2m', 'IronLead2m'):
            graph, samples, images = self.numerical_fixture(role)
            samples[images['Image Texture']] = [.2, .3, .4]
            samples[images['Image Texture.001']] = [.8, .7, .6]
            for selector, expected in ((.49, [.2,.3,.4]), (.5, [.2,.3,.4]), (.51, [.8,.7,.6])):
                self.assertEqual(evaluate(graph, samples, uv1=(selector,0,0))['Base Color'], expected)
        graph, samples, images = self.numerical_fixture('LaidWeatheredPhotoCoatFrayedCut2m_SourceTrial')
        samples[images['Image Texture']] = [.2,.3,.4]
        samples[images['Image Texture.003']] = [.8,.7,.6]
        for selector in (.49,.5,.51):
            actual = evaluate(graph, samples, uv1=(selector,0,0))['Base Color']
            for a,x,y in zip(actual,[.2,.3,.4],[.8,.7,.6]):
                self.assertAlmostEqual(a,x+selector*(y-x))

    def test_numerical_roughness_clamps_only_where_source_does(self):
        for roughness in (-.2,1.4):
            for role in ('LimeMortarSoot2m','WeatheredTimber2m'):
                graph,samples,_ = self.numerical_fixture(role,roughness)
                actual = evaluate(graph,samples,uv1=(0,0,0))['Roughness']
                expected = min(1,max(0,roughness)) if role=='LimeMortarSoot2m' else roughness
                self.assertAlmostEqual(actual,expected)

    def test_numerical_fractional_normal_matches_actual_cycles_probe(self):
        graph,samples,images=self.numerical_fixture('LaidWeatheredPhotoCoatFrayedCut2m_SourceTrial')
        for name in ('Image Texture.001','Image Texture.004'):
            samples[images[name]]=[.75,.3,.85]
        probe=json.loads((ROOT/'Docs/Verification/House439ClosedEavesNative/MaterialProfile/NORMAL_STRENGTH_PROBE.json').read_text())
        for row in probe['rows']:
            actual=evaluate(graph,samples,uv1=(.37,0,0),vertex=(row['strength'],1,1,0))['Normal']
            self.assertLess(math.sqrt(sum((a-b)**2 for a,b in zip(actual,row['actual_normal']))),1e-6)

    def test_lowering_rejects_unqualified_mode_projection_math_and_mute(self):
        for kind,key,value in [('ShaderNodeSeparateColor','mode','HSV'),
                               ('ShaderNodeTexImage','projection','BOX'),
                               ('ShaderNodeMath','operation','SINE'),
                               ('ShaderNodeMath','mute',True)]:
            role='LimeMortarSoot2m' if kind=='ShaderNodeMath' else 'ThinWavyGlass2m'
            recipe=active_recipe(role,self.roles[role],self.semantics[role])
            next(n for n in recipe['nodes'] if n['type']==kind)['properties'][key]=value
            with self.subTest(kind=kind,key=key), self.assertRaises(ValueError):
                lower_recipe(recipe)

    @staticmethod
    def rehash(record):
        record['fingerprint'] = hashlib.sha256(json.dumps(record['graph'], sort_keys=True).encode()).hexdigest()

    def test_stale_fingerprint_rejected(self):
        record = copy.deepcopy(self.roles['FieldstoneWall2m'])
        record['graph']['nodes'][0]['inputs'][0][1] = [4, 5, 6]
        with self.assertRaisesRegex(ValueError, 'fingerprint mismatch'):
            active_recipe('wall', record)

    def test_invalid_socket_duplicate_and_cycle_rejected_after_valid_hash(self):
        for defect, expected in [('output', 'socket'), ('input', 'socket'),
                                 ('duplicate', 'duplicate'), ('cycle', 'Cycle')]:
            record = copy.deepcopy(self.roles['FieldstoneWall2m'])
            links = record['graph']['links']
            if defect == 'output':
                links[0][1] = 'NONEXISTENT_OUTPUT'
            elif defect == 'input':
                links[0][3] = 'NONEXISTENT_INPUT'
            elif defect == 'duplicate':
                links.append(copy.deepcopy(links[0]))
            else:
                links[:] = [e for e in links if e[2:] != ['Normal Map', 'Color']]
                links.append(['Normal Map', 'Normal', 'Normal Map', 'Color'])
            self.rehash(record)
            with self.subTest(defect=defect), self.assertRaisesRegex(ValueError, expected):
                active_recipe('wall', record)

    def test_raw_normals_reject_reconstructed_z_srgb_and_double_flip(self):
        valid = dict(srgb=False, sampler='linear_rgb', compression='retained_rgb',
                     source_orientation='OpenGL +Y', green_flip_count=1, retained_channels='RGB')
        validate_raw_normal_binding(valid)
        for key, value in [('sampler', 'Normal'), ('compression', 'TC_NORMALMAP'),
                           ('srgb', True), ('green_flip_count', 0),
                           ('green_flip_count', 2), ('retained_channels', 'RG')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_raw_normal_binding(dict(valid, **{key: value}))

    @classmethod
    def setUpClass(cls):
        cls.roles = json.loads(SOURCE.read_text())['roles']
        cls.semantics = json.loads((ROOT / 'Docs/Verification/House439ClosedEavesNative/MaterialProfile/NODE_SEMANTICS_SUPPLEMENT.json').read_text())['roles']

    def test_all_seven_roles_preserve_every_active_default_and_link(self):
        for role, record in self.roles.items():
            recipe = active_recipe(role, record, self.semantics[role])
            adapter = RecordingAdapter()
            build_with_adapter(recipe, adapter)
            self.assertEqual(adapter.events[0], ('preflight', role))
            created = [e[1] for e in adapter.events if e[0] == 'create']
            self.assertEqual(created, recipe['nodes'])
            self.assertEqual([list(e[1]) for e in adapter.events if e[0] == 'connect'], recipe['links'])

    def test_roof_excludes_historical_noise_and_retains_fractional_selector(self):
        role = 'LaidWeatheredPhotoCoatFrayedCut2m_SourceTrial'
        recipe = active_recipe(role, self.roles[role])
        types = {n['type'] for n in recipe['nodes']}
        self.assertNotIn('ShaderNodeBump', types)
        self.assertNotIn('ShaderNodeTexNoise', types)
        self.assertIn('Bump', recipe['excluded_disconnected_nodes'])
        self.assertIn(['Separate XYZ', 'X', 'Mix (Legacy).001', 'Fac'], recipe['links'])
        self.assertIn(['Separate Color.001', 'Red', 'Normal Map', 'Strength'], recipe['links'])
        self.assertFalse(any(n['type'] == 'ShaderNodeMath' for n in recipe['nodes']))

    def test_glass_preserves_transmission_ior_and_thin_wall(self):
        recipe = active_recipe('glass', self.roles['ThinWavyGlass2m'])
        node = next(n for n in recipe['nodes'] if n['type'] == 'ShaderNodeBsdfPrincipled')
        values = dict(node['inputs'])
        self.assertEqual(values['Transmission Weight'], 1)
        self.assertTrue(values['Thin Wall'])
        self.assertAlmostEqual(values['IOR'], 1.48, places=6)

    def test_unsupported_active_node_rejected_and_adapter_refusal_precedes_mutation(self):
        record = copy.deepcopy(self.roles['FieldstoneWall2m'])
        next(n for n in record['graph']['nodes'] if n['name'] == 'Normal Map')['type'] = 'UnknownShader'
        self.rehash(record)
        with self.assertRaisesRegex(ValueError, 'Unqualified active'):
            active_recipe('invalid', record)
        adapter = RecordingAdapter(reject=True)
        with self.assertRaises(ValueError):
            build_with_adapter(active_recipe('wall', self.roles['FieldstoneWall2m'], self.semantics['FieldstoneWall2m']), adapter)
        self.assertEqual(adapter.events, [])

    def test_actual_clamp_retained_and_missing_semantics_refuses_construction(self):
        role = 'LimeMortarSoot2m'
        recipe = active_recipe(role, self.roles[role], self.semantics[role])
        node = next(n for n in recipe['nodes'] if n['name'] == 'Math.001')
        self.assertTrue(node['properties']['use_clamp'])
        adapter = RecordingAdapter()
        with self.assertRaisesRegex(ValueError, 'mute/clamp'):
            build_with_adapter(active_recipe(role, self.roles[role]), adapter)
        self.assertEqual(adapter.events, [])

    def test_all_roles_lower_with_explicit_raw_normal_and_source_optics(self):
        for role, record in self.roles.items():
            with self.subTest(role=role):
                graph = lower_recipe(active_recipe(role, record, self.semantics[role]))
                by_id = {n['id']: n for n in graph['operations']}
                bsdf = by_id[graph['surface']]
                self.assertEqual(bsdf['operation'], 'source_principled')
                self.assertEqual(by_id[bsdf['ambient_occlusion']]['value'], 1)
                normal = by_id[bsdf['inputs']['Normal']]
                self.assertEqual(normal['operation'], 'normalize')
                blend = by_id[normal['source']]
                self.assertEqual(blend['operation'], 'lerp')
                self.assertEqual(by_id[blend['a']]['value'], [0, 0, 1])
                self.assertEqual(by_id[blend['b']]['operation'], 'add')
                self.assertTrue(all(n['retained_channels'] == 'RGB'
                                    for n in graph['operations'] if n['operation'] == 'texture_rgb'))

    def test_lowering_preserves_threshold_and_clamped_roughness(self):
        for role in ('LimeMortarSoot2m', 'WeatheredTimber2m', 'IronLead2m'):
            graph = lower_recipe(active_recipe(role, self.roles[role], self.semantics[role]))
            by_id = {n['id']: n for n in graph['operations']}
            predicates = [n for n in graph['operations'] if n['operation'] == 'greater_than']
            self.assertEqual(len(predicates), 1)
            self.assertEqual(by_id[predicates[0]['b']]['value'], .5)
            if role == 'LimeMortarSoot2m':
                roughness = by_id[by_id[graph['surface']]['inputs']['Roughness']]
                self.assertEqual(roughness['operation'], 'saturate')
                self.assertEqual(by_id[roughness['source']]['operation'], 'add')


if __name__ == '__main__':
    unittest.main()
