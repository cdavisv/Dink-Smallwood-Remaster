"""Published clone workflow: synthetic actual files, no private author Saved state."""
import copy,json,shutil,unittest
from pathlib import Path
import feedsack_contract as C
import publish_photoreal_feedsack as P
import test_feedsack_publication as fixtures


class PublishedCloneTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PublicationTests('test_dry_run_zero_writes');self.f.setUp();self.addCleanup(self.f.doCleanups)
        f=self.f;f.house.write_text(json.dumps(C.rewrite_house(f.document,f.plan),indent=2)+'\n')
        self.absent_import=f.root/'Saved/Art/photoreal_feedsack_import.json'
        self.refresh_receipt()
    def context(self,mode='verify'):
        f=self.f
        return C.verification_context(f.root,f.plan,json.loads(f.house.read_text()),C.pins(f.root,'Content'),C.pins(f.root,'Content/Dink/Data'),mode,self.absent_import)
    def refresh_receipt(self):
        f=self.f;self.ctx=self.context();self.entry=copy.deepcopy(self.ctx['entry_package_sha256'])
        r=f.receipt;r.update(publication_state='published',verification_basis='published_entry_state',scene_data_approval=False,writer_scope='none',verification_scope='saved_feedsack_assets_with_current_pinned_Data_context',runtime_data_sha256=C.pins(f.root,'Content/Dink/Data'),protected_content_sha256={p:h for p,h in C.pins(f.root,'Content').items()if p not in C.candidate_files(f.plan)},saved_package_sha256=self.entry,house_baseline_semantic_sha256=C.canonical_hash(json.loads(f.house.read_text())))
        f.write_receipt()
    def publish(self,apply=False):
        f=self.f;return P.publication(f.root,f.source,f.verification,apply,tool_folder=f.tools)
    def inventory(self):return {str(p):p.read_bytes()for p in Path(self.f.temp.name).rglob('*')if p.is_file()}
    def reject_unchanged(self,apply=True):
        before=self.inventory()
        with self.assertRaises((ValueError,KeyError,FileNotFoundError)):self.publish(apply)
        self.assertEqual(self.inventory(),before)
    def test_normal_published_clone_without_any_private_Saved_receipt_verifies_context(self):
        self.assertFalse((self.f.root/'Saved').exists());self.assertIsNone(self.ctx['prior']);self.assertEqual(self.ctx['verification_basis'],'published_entry_state');self.assertEqual(self.ctx['publication_state'],'published');self.assertEqual(len(self.entry),6)
    def test_fresh_published_check_and_idempotent_apply_write_nothing(self):
        before=self.inventory()
        for apply in [False,True,False,True]:
            result=self.publish(apply);self.assertTrue(result['already_published']);self.assertFalse(result['applied']);self.assertEqual(result['writer_scope'],'none');self.assertFalse(result['scene_data_approval']);self.assertEqual(result['changed_mesh_references'],0)
            self.assertEqual(self.inventory(),before);self.assertFalse((self.f.root/'Saved').exists())
    def test_preflight_and_import_reject_already_published_clone(self):
        for mode in ['preflight','import']:
            with self.assertRaises(ValueError):self.context(mode)
    def test_mixed_old_new_state_rejects_verify_and_publisher(self):
        f=self.f;d=json.loads(f.house.read_text());d['elements'][0]['mesh']=f.plan['assets'][0]['old'];f.house.write_text(json.dumps(d))
        with self.assertRaises(ValueError):self.context()
        self.reject_unchanged()
    def test_unpublished_missing_import_receipt_remains_rejected(self):
        f=self.f;f.house.write_text(json.dumps(f.document))
        with self.assertRaises(FileNotFoundError):self.context()
    def test_unpublished_with_real_import_receipt_context_retains_prior_baseline(self):
        f=self.f;f.house.write_bytes(f.original);path=self.absent_import;path.parent.mkdir(parents=True)
        prior={'passed':True,'mode':'import','project':str(f.root.resolve()),'runtime_data_sha256':C.pins(f.root,'Content/Dink/Data'),'protected_content_sha256':{p:h for p,h in C.pins(f.root,'Content').items()if p not in C.candidate_files(f.plan)},'saved_package_sha256':dict(self.entry)};path.write_text(json.dumps(prior));ctx=self.context();self.assertEqual(ctx['verification_basis'],'import_receipt');self.assertEqual(ctx['prior'],prior)
    def test_preflight_import_require_all_old_and_empty_candidate_files(self):
        f=self.f;f.house.write_bytes(f.original)
        for mode in ['preflight','import']:
            with self.assertRaises(ValueError):self.context(mode)
        for relative in C.candidate_files(f.plan):(f.root/relative).unlink(missing_ok=True)
        for mode in ['preflight','import']:self.assertEqual(self.context(mode)['verification_basis'],'import_creation')
        ghost=f.package.with_suffix('.ubulk');ghost.write_bytes(b'orphan unpublished sidecar')
        with self.assertRaises(ValueError):self.context('preflight')
    def test_published_Data_file_addition_or_deletion_after_verify_rejects(self):
        f=self.f;extra=f.other.with_name('new.json');extra.write_text('{}');self.reject_unchanged();extra.unlink();f.other.unlink();self.reject_unchanged()
    def test_candidate_mutation_during_fresh_verification_cannot_be_adopted(self):
        f=self.f;f.package.write_bytes(b'changed during native inspection')
        with self.assertRaises(ValueError):C.verify_candidate_packages(f.root,f.plan,self.ctx['entry_package_sha256'])
        self.assertEqual(self.ctx['entry_package_sha256'],self.entry)
    def test_candidate_addition_deletion_during_fresh_verification_rejects(self):
        f=self.f;side=f.package.with_suffix('.ubulk');side.write_bytes(b'new sidecar')
        with self.assertRaises(ValueError):C.verify_candidate_packages(f.root,f.plan,self.entry)
        side.unlink();f.package.unlink()
        with self.assertRaises(ValueError):C.verify_candidate_packages(f.root,f.plan,self.entry)
    def test_published_house_transform_or_story_Data_tamper_after_verify_rejects(self):
        f=self.f;original=f.house.read_bytes();d=json.loads(original);d['elements'][0]['world_cm'][0]+=10;f.house.write_text(json.dumps(d));self.reject_unchanged();f.house.write_bytes(original);f.other.write_text('new story or AI data');self.reject_unchanged()
    def test_published_package_tamper_after_verify_rejects(self):
        self.f.package.write_bytes(b'changed saved native asset');self.reject_unchanged()
    def test_published_source_pixel_tamper_rejects(self):
        (self.f.source/'ExportIteration/Export/SM_FeedSack_Jute_01_BC.png').write_bytes(b'changed source pixels');self.reject_unchanged()
    def test_published_tool_tamper_rejects(self):
        p=self.f.tools/'import_photoreal_feedsack.py';p.write_text('changed verifier');self.reject_unchanged()
    def test_fresh_asset_context_is_not_scene_approval_or_writer_authority(self):
        f=self.f;d=json.loads(f.house.read_text());d['elements'][0]['world_cm'][0]+=17;d['postprocess']=[{'separate_reviewed_context':True}];f.house.write_text(json.dumps(d));extra=f.other.with_name('approved_context.json');extra.write_text('{"controlledMerge":true}');self.refresh_receipt();before=self.inventory();r=self.publish(True);self.assertFalse(r['scene_data_approval']);self.assertEqual(r['writer_scope'],'none');self.assertEqual(self.inventory(),before)
    def test_new_receipt_cannot_label_all_old_state_as_published(self):
        self.f.house.write_bytes(self.f.original);self.reject_unchanged()
    def test_fresh_published_receipt_cannot_grant_scene_approval_or_writer_scope(self):
        f=self.f;f.receipt['scene_data_approval']=True;f.write_receipt();self.reject_unchanged();f.receipt['scene_data_approval']=False;f.receipt['writer_scope']='two_mesh_paths';f.write_receipt();self.reject_unchanged()


class NativeSourceFilenameTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PublicationTests('test_dry_run_zero_writes');self.f.setUp();self.addCleanup(self.f.doCleanups);self.relative=self.f.plan['assets'][0]['fbx'];self.expected=self.f.source/self.relative;self.digest=C.sha(self.expected)
    def test_native_getter_resolved_own_clone_source_is_accepted(self):
        r=C.validate_native_source_filename(self.f.source,self.relative,[str(self.expected)],self.digest);self.assertTrue(r['native_getter_resolved_selected_source'])
    def test_stored_relative_text_is_not_guessed_as_native_resolved_output(self):
        with self.assertRaises(ValueError):C.validate_native_source_filename(self.f.source,self.relative,[self.relative],self.digest)
    def test_same_basename_and_bytes_in_author_or_other_clone_are_rejected(self):
        other=Path(self.f.temp.name)/'other_clone'/self.relative;other.parent.mkdir(parents=True);shutil.copyfile(self.expected,other)
        with self.assertRaises(ValueError):C.validate_native_source_filename(self.f.source,self.relative,[str(other)],self.digest)
    def test_missing_extra_filenames_and_source_hash_drift_reject(self):
        for names in [[],[str(self.expected),str(self.expected)]]:
            with self.assertRaises(ValueError):C.validate_native_source_filename(self.f.source,self.relative,names,self.digest)
        self.expected.write_bytes(b'changed actual source')
        with self.assertRaises(ValueError):C.validate_native_source_filename(self.f.source,self.relative,[str(self.expected)],self.digest)


if __name__=='__main__':unittest.main()
