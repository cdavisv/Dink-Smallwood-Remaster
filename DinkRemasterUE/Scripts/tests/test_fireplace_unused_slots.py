"""Verified source declarations versus legitimate exact used-only native inventory."""
import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'Scripts/RoofNative'))
from fireplace_contract import load_contract
from fireplace_mesh_readback import source_used_role_packages,audit_source_and_native_slot_inventory,decode_source
from shared_roof_native import bind_named_materials
from types import SimpleNamespace
UNUSED=['Fieldstone','Lime','Oak'];USED=['Soot','Iron','Masonry'];DECLARED=['Fieldstone','Lime','Soot','Oak','Iron','Masonry']
def fixture(used=None):
    used=USED if used is None else used;declared=DECLARED if used==USED else used
    source=[dict(material=n)for n in used for _ in range(2)]
    record=dict(material_slots=list(declared),triangles=len(source),FBX_metadata=dict(used_materials=list(used),unused_materials=[n for n in declared if n not in used]))
    snapshot=dict(valid=True,slots=[dict(slot=i,imported_name=n)for i,n in enumerate(used)],built=dict(sections=[dict(slot=i,triangles=2)for i in range(len(used))]))
    bindings=dict(valid=True,slots=[dict(slot_index=i,imported_slot_name=n)for i,n in enumerate(used)],groups=[dict(polygon_group_id=i,slot_index=i,imported_slot_name=n)for i,n in enumerate(used)],triangles=[dict(polygon_group_id=i,slot_index=i)for i in range(len(used))for _ in range(2)])
    for index,triangle in enumerate(bindings['triangles']):triangle['triangle_id']=index
    return record,source,snapshot,bindings
class UsedSlotTests(unittest.TestCase):
    def test_three_native_roles_preserve_all_six_source_declarations(self):
        r,s,g,b=fixture();before=copy.deepcopy(r);roles=source_used_role_packages(r,{n:'/Game/'+n for n in DECLARED},s)
        self.assertEqual(set(roles),set(USED));result=audit_source_and_native_slot_inventory(g,b,r,s)
        self.assertEqual(result['declared_roles'],DECLARED);self.assertEqual(result['source_unused_roles'],sorted(UNUSED));self.assertEqual(r,before)
    def test_five_used_roles_each_lod(self):
        for lod in range(3):
            r,s,g,b=fixture(['Clay','Lime','Soot','Oak','Iron']);self.assertEqual(len(source_used_role_packages(r,{n:n for n in r['material_slots']},s)),5);self.assertTrue(audit_source_and_native_slot_inventory(g,b,r,s)['passed'])
    def test_bad_source_partitions_duplicates_missing_parent_and_facecounts(self):
        changes=[lambda r,s:r['material_slots'].append('Soot'),lambda r,s:r['FBX_metadata']['used_materials'].append('Soot'),lambda r,s:r['FBX_metadata']['unused_materials'].append('Oak'),lambda r,s:r['FBX_metadata']['unused_materials'].append('Soot'),lambda r,s:r['FBX_metadata']['unused_materials'].remove('Oak'),lambda r,s:r.update(triangles=99),lambda r,s:s.pop(),lambda r,s:s[0].update(material='Unknown'),lambda r,s:r['FBX_metadata']['used_materials'].remove('Soot')]
        for change in changes:
            r,s,g,b=fixture();change(r,s)
            with self.subTest(change=change),self.assertRaises(ValueError):source_used_role_packages(r,{n:n for n in DECLARED},s)
        r,s,g,b=fixture()
        with self.assertRaises(ValueError):source_used_role_packages(r,{n:n for n in USED},s)
    def test_missing_unknown_duplicate_unused_or_noncontiguous_native_slots(self):
        changes=[lambda g:g['slots'].pop(),lambda g:g['slots'][0].update(imported_name='Unknown'),lambda g:g['slots'][0].update(imported_name='Iron'),lambda g:g['slots'].append(dict(slot=3,imported_name='Oak')),lambda g:g['slots'][0].update(slot=9)]
        for change in changes:
            r,s,g,b=fixture();change(g)
            with self.subTest(change=change),self.assertRaises(ValueError):audit_source_and_native_slot_inventory(g,b,r,s)
    def test_unknown_duplicate_or_mismatched_binding_inventory(self):
        for change in [lambda b:b['slots'].append(copy.deepcopy(b['slots'][0])),lambda b:b['slots'][0].update(imported_slot_name='Unknown'),lambda b:b['groups'].append(copy.deepcopy(b['groups'][0])),lambda b:b['groups'][0].update(imported_slot_name='Oak'),lambda b:b['triangles'][0].update(slot_index=1)]:
            r,s,g,b=fixture();change(b)
            with self.assertRaises(ValueError):audit_source_and_native_slot_inventory(g,b,r,s)
    def test_missing_face_and_redistributed_role_facecounts_fail(self):
        for change in [lambda b:b['triangles'].pop(),lambda b:b['triangles'][0].update(polygon_group_id=1,slot_index=1),lambda b:b['triangles'][0].update(triangle_id=1)]:
            r,s,g,b=fixture();change(b)
            with self.assertRaises(ValueError):audit_source_and_native_slot_inventory(g,b,r,s)
    def test_missing_used_group_and_section_fail(self):
        r,s,g,b=fixture();b['groups'].pop()
        with self.assertRaises((ValueError,KeyError)):audit_source_and_native_slot_inventory(g,b,r,s)
        r,s,g,b=fixture();g['built']['sections'].pop()
        with self.assertRaisesRegex(ValueError,'section'):audit_source_and_native_slot_inventory(g,b,r,s)
    def test_section_facecount_fraction_negative_and_role_drift_fail(self):
        for count in [1,3,-1,.5]:
            r,s,g,b=fixture();g['built']['sections'][0]['triangles']=count
            with self.assertRaises(ValueError):audit_source_and_native_slot_inventory(g,b,r,s)
    def test_slot_reordering_with_consistent_semantics_is_allowed_without_mutation(self):
        r,s,g,b=fixture();g['slots'][0]['imported_name'],g['slots'][2]['imported_name']=g['slots'][2]['imported_name'],g['slots'][0]['imported_name'];b['slots'][0]['imported_slot_name'],b['slots'][2]['imported_slot_name']=b['slots'][2]['imported_slot_name'],b['slots'][0]['imported_slot_name']
        for group in b['groups']:group['slot_index']=2-group['slot_index']
        for triangle in b['triangles']:triangle['slot_index']=2-triangle['slot_index']
        before=copy.deepcopy((r,s,g,b));self.assertTrue(audit_source_and_native_slot_inventory(g,b,r,s)['passed']);self.assertEqual((r,s,g,b),before)
    def test_unchanged_shared_binder_gets_exact_used_roles_and_never_constructs_slots(self):
        r,s,g,b=fixture();roles=source_used_role_packages(r,{n:'/Game/'+n for n in DECLARED},s);writes=[]
        class Material:pass
        slots=[SimpleNamespace(get_editor_property=lambda k,n=n:n)for n in USED]
        mesh=SimpleNamespace(get_editor_property=lambda k:slots,set_material=lambda i,m:writes.append(i))
        u=SimpleNamespace(Material=Material,load_asset=lambda p:Material())
        with patch('shared_roof_native.inspect_slots',return_value={'passed':True}):self.assertTrue(bind_named_materials(u,mesh,roles,6,lambda:None)['passed'])
        self.assertEqual(writes,[0,1,2])
        for names in [USED[:2],USED+['Unknown'],USED+[UNUSED[0]],[USED[0],USED[0],USED[2]]]:
            writes.clear();slots[:]=[SimpleNamespace(get_editor_property=lambda k,n=n:n)for n in names]
            with self.assertRaises(ValueError):bind_named_materials(u,mesh,roles,6,lambda:None)
            self.assertEqual(writes,[])
    def test_actual_hash_verified_fbx_partitions_and_counts_all_four_meshes(self):
        contract=load_contract(P);all_roles={r['source_material']:r['package']for r in contract['materials']};self.assertEqual(len(all_roles),7)
        for record in contract['meshes']:
            source,_=decode_source(P,record);roles=source_used_role_packages(record,all_roles,source);self.assertEqual(len(roles),3 if 'Chimney' in record['name']else 5)
            if 'Chimney' in record['name']:
                from collections import Counter
                self.assertEqual(sorted(Counter(row['material']for row in source).values()),[176,628,682])
if __name__=='__main__':unittest.main()
