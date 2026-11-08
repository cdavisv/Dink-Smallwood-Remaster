"""FeedSack-only publication scope, five tool pins and concrete-output TOCTOU checks."""
import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
import feedsack_contract as C
import publish_photoreal_feedsack as P
import test_feedsack_publication as fixtures

class FeedSackScopeTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PublicationTests('test_dry_run_zero_writes');self.f.setUp();self.addCleanup(self.f.doCleanups)
    def test_feed_sack_asset_pickup_script_transforms_are_preserved(self):
        f=self.f;new=C.rewrite_house(f.document,f.plan)
        self.assertEqual(new['elements'],f.document['elements']);
        before=dict(f.document['replacements'][0]);after=dict(new['replacements'][0]);before.pop('mesh');after.pop('mesh');self.assertEqual(before,after)
        self.assertEqual(new['replacements'][0]['origin'],'S001_P52');self.assertEqual(new['replacements'][0]['script'],'s1-sack')
        self.assertEqual(C.rewrite_house(new,f.plan,from_new=True),f.document)
    def test_feed_sack_mutations_after_verify_reject_without_writes(self):
        f=self.f
        changes=[lambda d:d['elements'][0].__setitem__('mesh',f.plan['assets'][0]['old']),lambda d:d['replacements'][0].__setitem__('script','changed'),lambda d:d['replacements'][0].__setitem__('origin','S001_P53'),lambda d:d['replacements'][0]['offset_cm'].__setitem__(0,1),lambda d:d['replacements'][0]['scale'].__setitem__(0,2)]
        for mutate in changes:
            d=copy.deepcopy(f.document);mutate(d);f.house.write_text(json.dumps(d));f.rejected_without_house_mutation()
        f.house.write_bytes(f.original)
    def test_prepare_plan_is_fifth_pinned_production_tool(self):
        f=self.f;actual=C.tool_pins(f.tools);self.assertEqual(len(actual),5);self.assertIn('prepare_photoreal_feedsack_plan.py',actual)
        (f.tools/'prepare_photoreal_feedsack_plan.py').write_text('changed source audit policy');f.rejected_without_house_mutation()
    def test_source_ior_and_ue_f0_policy_is_bound_into_plan(self):
        optics=self.f.plan['material_optics'][0];self.assertEqual(optics['source_IOR'],1.46);self.assertEqual(optics['source_Specular_IOR_Level'],.22);self.assertEqual(optics['UE_specular'],C.UE_SPECULAR);self.assertTrue(optics['normal_incidence_F0_only'])
    def test_wrong_native_constant_publisher_rejects_source_level_and_old_barrel_value(self):
        f=self.f
        for scalar in [.25,.35,float('nan'),float('inf')]:
            f.receipt['material_recipes']['SM_FeedSack_Jute_01'][0]['specular']=scalar;f.write_receipt();f.rejected_without_house_mutation()
        import struct
        observed=struct.unpack('<f',struct.pack('<f',C.UE_SPECULAR))[0]
        self.assertNotEqual(observed,C.UE_SPECULAR)
        f.receipt['material_recipes']['SM_FeedSack_Jute_01'][0].update(specular=observed,expected_specular=C.UE_SPECULAR);f.write_receipt();self.assertTrue(f.run_publish()['passed'])
    def late_mutation(self,mutation):
        f=self.f;original=C.pins;ran=[]
        def racing(root,directory):
            if directory=='Content/Dink/Data' and list(f.house.parent.glob('.photoreal-feedsack-*.tmp')) and not ran:
                ran.append(True);mutation()
            return original(root,directory)
        with patch.object(C,'pins',side_effect=racing):f.rejected_without_house_mutation()
        self.assertTrue(ran);self.assertFalse(list(f.house.parent.glob('.photoreal-feedsack-*.tmp')))
    def test_late_candidate_replacement_after_temporary_is_concrete_rejects(self):
        self.late_mutation(lambda:self.f.package.write_bytes(b'late changed candidate'))
    def test_late_source_payload_after_temporary_is_concrete_rejects(self):
        # Source checks precede Data in the final guard, so trigger during the
        # second load_plan call (after temp creation), before it hashes payloads.
        f=self.f;original=C.load_plan;ran=[]
        def racing(*args,**kwargs):
            if list(f.house.parent.glob('.photoreal-feedsack-*.tmp')):
                ran.append(True);(f.source/'ExportIteration/Export/SM_FeedSack_Jute_01_BC.png').write_bytes(b'late source drift')
            return original(*args,**kwargs)
        with patch.object(C,'load_plan',side_effect=racing):f.rejected_without_house_mutation()
        self.assertTrue(ran)
    def test_late_prepare_plan_tool_after_concrete_temp_rejects(self):
        f=self.f;original=C.tool_pins;ran=[]
        def racing(folder):
            if list(f.house.parent.glob('.photoreal-feedsack-*.tmp')):
                ran.append(True);(f.tools/'prepare_photoreal_feedsack_plan.py').write_text('late tool drift')
            return original(folder)
        with patch.object(C,'tool_pins',side_effect=racing):f.rejected_without_house_mutation()
        self.assertTrue(ran)
    def test_late_verification_receipt_after_concrete_temp_rejects(self):
        f=self.f;original=C.sha;ran=[]
        def racing(path):
            if Path(path)==f.verification and list(f.house.parent.glob('.photoreal-feedsack-*.tmp')):
                ran.append(True);f.verification.write_text('{}')
            return original(path)
        with patch.object(C,'sha',side_effect=racing):f.rejected_without_house_mutation()
        self.assertTrue(ran)
    def test_exact_float32_authored_box_rejects_tiny_source_vertex_edits(self):
        f=self.f;cloud=[list(p)for p in C.authored_box_points()];cloud[0][0]+=1e-7
        with patch.object(C,'source_hulls',return_value=[cloud]),self.assertRaisesRegex(ValueError,'UCX box'):C.load_plan(f.source,check_pixels=False)

if __name__=='__main__':unittest.main()
