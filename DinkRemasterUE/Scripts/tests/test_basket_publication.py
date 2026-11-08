"""Synthetic fixtures exercise real publisher file guards; no Unreal/LFS dependency."""
import copy,json,shutil,tempfile,unittest,struct,zlib
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import basket_contract as C
import publish_photoreal_basket as P


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent);self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'project';self.root.mkdir();self.source=Path(self.temp.name)/'source';self.source.mkdir();self.tools=Path(self.temp.name)/'tools';self.tools.mkdir()
        for name in ['basket_contract.py','import_photoreal_basket.py','publish_photoreal_basket.py','basket_fbxparse.py','prepare_photoreal_basket_plan.py']:(self.tools/name).write_text('synthetic tool '+name)
        (self.source/'Export').mkdir();(self.source/'PhotorealBasketV1_Source.blend').write_bytes(b'synthetic source blend');(self.source/'PhotorealBasketV1_Export.blend').write_bytes(b'synthetic export blend')
        exportsha=C.sha(self.source/'PhotorealBasketV1_Export.blend');assets=[]
        for name,(hulls,tris)in C.COUNTS.items():
            tex=[]
            for role in C.ROLES:
                filename=name+'_'+role+'.png';(self.source/'Export'/filename).write_bytes(b'synthetic pixel payload '+filename.encode())
                tex.append({'role':role,'file':filename,'name':'T_'+name[3:]+'_Photo_'+role,'srgb':role=='BC','normal_green_flip':role=='N','size':[2048,2048]})
            for suffix in ['fbx','glb']:(self.source/'Export'/(name+'.'+suffix)).write_bytes(b'synthetic exported geometry')
            assets.append({'name':name,'content_path':C.MESH_FOLDER+'/'+name,'source':{'sha256':exportsha},'pivot_rule':'base_center','lod_count':1,'nanite':True,'collision':['UCX_SM_Basket_Wicker_01_01'],'tris':{'LOD0':tris},'material_slots':['MI_Basket_Wicker_01_PhotoBaked'],'validation':{'errors':0,'forced':False},'textures':tex,'files':{'fbx':name+'.fbx','glb':name+'.glb'},'bounds_cm':{'size_cm':[114.4,94.2,67.2],'unreal_min_cm':[-57.2,-47.1,0.],'unreal_max_cm':[57.2,47.1,67.2]}})
        (self.source/'Export/manifest.json').write_text(json.dumps({'assets':assets}))
        (self.source/'texture_payload_validation.json').write_text('{}')
        frozen={'schema':'dink-photoreal-basket-source/1','source_sha256':C.sha(self.source/'PhotorealBasketV1_Source.blend'),'export_source_sha256':exportsha,'status':'Frozen source/export candidate approved for source publication only','native_imported':False,'runtime_published':False,'frozen_files':{str(p.relative_to(self.source)):C.sha(p)for p in self.source.rglob('*')if p.is_file()}}
        (self.source/'final_handoff.json').write_text(json.dumps(frozen))
        # This publisher fixture has synthetic geometry bytes; only its pure FBX
        # reader is stubbed. Separate actual-source audit reads the frozen realFBX.
        hull_stub=patch.object(C,'source_hulls',return_value=[[list(p)for p in C.authored_box_points()]]);hull_stub.start();self.addCleanup(hull_stub.stop)
        import basket_fbxparse
        fbx_stub=patch.object(basket_fbxparse,'inspect',return_value={'models':{'SM_Basket_Wicker_01':{},'UCX_SM_Basket_Wicker_01_01':{}},'coord_axis':[0,1]});fbx_stub.start();self.addCleanup(fbx_stub.stop)
        self.plan=C.load_plan(self.source,check_pixels=False)
        self.house=self.root/C.HOUSE;self.house.parent.mkdir(parents=True);self.other=self.root/'Content/Dink/Data/AI/test.ini';self.other.parent.mkdir();self.other.write_bytes(b'brain unchanged\n')
        document={'schema':'dink-art/1','screen':1,'assets':[],'replacements':[],'elements':[],'lights':[{'lumens':40}],'warp_overrides':[{'extent_cm':[65,30,150]}],'authored_collision_screens':[1],'hidden_policy':['unchanged']}
        for a in self.plan['assets']:document['assets'].append({'mesh':a['old'],'expected_size_cm':[250,150,100]})
        basket=self.plan['assets'][0]
        for i in range(1):document['elements'].append({'name':'WickerBasket','mesh':basket['old'],'world_cm':[100,200+i*30,0],'collision':True,'camera_occluder':False,'script':'unchanged'})
        document['assets'].append({'mesh':'/Game/Dink/Kits/Stonebrook/SM_FeedSack_Jute_01.SM_FeedSack_Jute_01','expected_size_cm':[72.2828388,55.4685414,75]})
        document['replacements'].append({'origin':'S001_P52','script':'s1-sack','mesh':'/Game/Dink/Kits/Stonebrook/SM_FeedSack_Jute_01.SM_FeedSack_Jute_01','offset_cm':[0,0,0],'rotation_deg':[0,0,0],'scale':[1,1,1]})
        self.document=document;self.house.write_text(json.dumps(document,indent=2)+'\n');self.original=self.house.read_bytes()
        originals={}
        for a in self.plan['assets']:
            rel=C.package_file(a['old'].split('.')[0]);p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'original native mesh');originals[rel]=C.sha(p)
        self.protected=C.pins(self.root,'Content');saved={}
        for rel in C.packages(self.plan):
            p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(('saved candidate '+rel).encode());saved[rel]=C.sha(p)
        self.package=self.root/next(iter(saved));self.verification=self.root/'verify.json'
        baseline={a['name']:{'triangles':9692}for a in self.plan['assets']}
        native={a['name']:{'triangles':a['triangles'],'UCX_hulls':a['hulls'],'source_normals_imported_and_Mikk_tangents_generated':True,'native_front_normal_evidence':{'checked_triangles':a['triangles'],'minimum_dot_source_geometric_front':1.,'minimum_dot_authored_source':1.,'convention':'reflectY,keepFBXcornerorder,front=cross(C-A,B-A)'},'collision_policy':'complex-as-simple'}for a in self.plan['assets']}
        recipe={a['name']:{'direct_BC_N_ORM':True,'specular':C.UE_SPECULAR,'all_native_material_property_ids_checked':list(range(6))}for a in self.plan['assets']}
        self.receipt={'schema':C.SCHEMA,'passed':True,'mode':'verify','project':str(self.root.resolve()),'source':str(self.source.resolve()),'verified_old_baseline':True,'protected_changes':[],'runtime_data_changes':[],'plan':self.plan,'plan_sha256':C.canonical_hash(self.plan),'tool_sha256':C.tool_pins(self.tools),'module_sha256':C.module_pins(self.root),'runtime_data_sha256':C.pins(self.root,'Content/Dink/Data'),'saved_package_sha256':saved,'protected_content_sha256':self.protected,'baseline_package_sha256':originals,'baseline_native':baseline,'native_assets':native,'material_recipes':recipe,'house_baseline_semantic_sha256':C.canonical_hash(self.document),'native_texture_source_pixels':{a['name']+'/'+r:'a'*64 for a in self.plan['assets']for r in C.ROLES}}
        self.receipt['native_source_filenames']={}
        for a in self.plan['assets']:
            for role in ('FBX',)+C.ROLES:
                relative=a['fbx']if role=='FBX'else a['texture_files'][role]
                self.receipt['native_source_filenames'][a['name']+'/'+role]=C.validate_native_source_filename(self.source,relative,[str(self.source/relative)],self.plan['source_sha256'][relative])
        self.write_receipt();self.ledger=self.root/'SourceAssets/asset-ledger.jsonl';self.ledger.parent.mkdir();self.ledger.write_bytes(b'{"raw prior ledger":true}\r\n')
    def write_receipt(self):self.verification.write_text(json.dumps(self.receipt))
    def run_publish(self,apply=False):return P.publication(self.root,self.source,self.verification,apply,tool_folder=self.tools)
    def rejected_without_house_mutation(self):
        before=self.house.read_bytes()
        with self.assertRaises((ValueError,FileNotFoundError,KeyError)):self.run_publish(True)
        self.assertEqual(self.house.read_bytes(),before)
    def test_dry_run_zero_writes(self):
        before={str(p):p.read_bytes()for p in Path(self.temp.name).rglob('*')if p.is_file()};r=self.run_publish();self.assertFalse(r['applied']);self.assertEqual(before,{str(p):p.read_bytes()for p in Path(self.temp.name).rglob('*')if p.is_file()})
    def test_exact_two_path_changes_and_all_other_semantics_and_ledger_preserved(self):
        self.run_publish(True);expected=C.rewrite_house(self.document,self.plan);self.assertEqual(json.loads(self.house.read_text()),expected);self.assertEqual(self.ledger.read_bytes(),b'{"raw prior ledger":true}\r\n');self.assertEqual(self.other.read_bytes(),b'brain unchanged\n')
    def test_idempotent_apply_and_checks_preserve_success_receipt_bytes(self):
        self.run_publish(True);p=self.root/'Saved/Art/photoreal_basket_publication.json';before=p.read_bytes();house=self.house.read_bytes()
        for apply in [False,False,True,False]:self.run_publish(apply);self.assertEqual(p.read_bytes(),before);self.assertEqual(self.house.read_bytes(),house)
    def test_house_transform_collision_light_warp_visibility_script_drift(self):
        mutations=[lambda d:d['elements'][0]['world_cm'].__setitem__(0,44),lambda d:d['elements'][0].__setitem__('collision',False),lambda d:d['lights'][0].__setitem__('lumens',400),lambda d:d['warp_overrides'][0]['extent_cm'].__setitem__(0,99),lambda d:d.__setitem__('hidden_policy',[]),lambda d:d['elements'][0].__setitem__('script','changed')]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                d=copy.deepcopy(self.document);mutation(d);self.house.write_text(json.dumps(d));self.rejected_without_house_mutation()
    def test_other_runtime_data_mutation_addition_deletion(self):
        self.other.write_text('changed');self.rejected_without_house_mutation();self.other.write_bytes(b'brain unchanged\n');extra=self.other.with_name('new.ini');extra.write_text('new');self.rejected_without_house_mutation();extra.unlink();self.other.unlink();self.rejected_without_house_mutation()
    def test_saved_package_drift_and_missing(self):
        self.package.write_bytes(b'new native bytes');self.rejected_without_house_mutation();self.package.unlink();self.rejected_without_house_mutation()
    def test_orphan_candidate_sidecar_rejected(self):
        self.package.with_suffix('.ubulk').write_bytes(b'extra candidate payload');self.rejected_without_house_mutation()
    def test_protected_original_package_mutation(self):
        path=self.root/next(iter(self.receipt['baseline_package_sha256']));path.write_bytes(b'changed old mesh');self.rejected_without_house_mutation()
    def test_source_texture_mutation_even_unchanged_handoff_and_manifest(self):
        (self.source/'Export/SM_Basket_Wicker_01_BC.png').write_bytes(b'new pixels');self.rejected_without_house_mutation()
    def test_importer_and_contract_and_publisher_and_fbx_reader_drift(self):
        for p in self.tools.iterdir():
            before=p.read_bytes();p.write_bytes(before+b' changed');self.rejected_without_house_mutation();p.write_bytes(before)
    def test_wrong_mode_scope_or_native_graph_receipt(self):
        for key,value in [('mode','import'),('project','/different'),('source','/different'),('verified_old_baseline',False),('protected_changes',['x'])]:
            old=self.receipt[key];self.receipt[key]=value;self.write_receipt();self.rejected_without_house_mutation();self.receipt[key]=old
        self.receipt['material_recipes']['SM_Basket_Wicker_01']['specular']=.8;self.write_receipt();self.rejected_without_house_mutation()
    def test_wrong_candidate_package_set(self):
        self.receipt['saved_package_sha256'].pop(next(iter(self.receipt['saved_package_sha256'])));self.write_receipt();self.rejected_without_house_mutation()
    def test_identity_count_mismatch_rejected_even_with_fresh_runtime_pin(self):
        d=copy.deepcopy(self.document);d['elements'][0]['name']='DifferentChair';self.house.write_text(json.dumps(d));digest=C.sha(self.house);self.receipt['runtime_data_sha256'][C.HOUSE]=digest;self.receipt['protected_content_sha256'][C.HOUSE]=digest;self.write_receipt();self.rejected_without_house_mutation()
    def test_postpublication_semantic_edit_rejects_idempotence(self):
        self.run_publish(True);d=json.loads(self.house.read_text());d['elements'][0]['collision']=False;self.house.write_text(json.dumps(d));self.rejected_without_house_mutation()
    def test_rewritten_prior_after_hash_cannot_authorize_new_semantics(self):
        self.run_publish(True);d=json.loads(self.house.read_text());d['elements'][0]['collision']=False;self.house.write_text(json.dumps(d));p=self.root/'Saved/Art/photoreal_basket_publication.json';prior=json.loads(p.read_text());prior['after_sha256']=C.sha(self.house);prior['verified_baseline_semantic_sha256']=C.canonical_hash(C.rewrite_house(d,self.plan,from_new=True));p.write_text(json.dumps(prior));self.rejected_without_house_mutation()
    def test_missing_or_changed_prior_publication_receipt(self):
        self.run_publish(True);p=self.root/'Saved/Art/photoreal_basket_publication.json';p.unlink();self.rejected_without_house_mutation()
    def test_drift_between_preflight_and_atomic_replace_is_rejected(self):
        original=C.pins;counter=[0]
        def racing(root,directory):
            if directory=='Content/Dink/Data':
                counter[0]+=1
                if counter[0]==2:self.other.write_text('concurrent modification')
            return original(root,directory)
        with patch.object(C,'pins',side_effect=racing):self.rejected_without_house_mutation()
        self.assertFalse(list(self.house.parent.glob('.photoreal-basket-*')))
    def test_missing_native_winding_confirmation_is_rejected(self):
        self.receipt['native_assets']['SM_Basket_Wicker_01']['native_front_normal_evidence']['checked_triangles']=0;self.write_receipt();self.rejected_without_house_mutation()
    def test_missing_native_pixel_proof_is_rejected(self):
        self.receipt['native_texture_source_pixels'].pop(next(iter(self.receipt['native_texture_source_pixels'])));self.write_receipt();self.rejected_without_house_mutation()
    def test_symlinked_content_child_is_rejected(self):
        target=Path(self.temp.name)/'outside';target.mkdir();link=self.root/'Content/External';link.symlink_to(target,target_is_directory=True);self.rejected_without_house_mutation()
    def test_closed_convex_indices_reject_open_reversed_and_out_of_range_faces(self):
        points=[[0,0,0],[1,0,0],[0,1,0],[0,0,1]];indices=[0,2,1,0,1,3,0,3,2,1,2,3];self.assertTrue(C.validate_closed_indices(points,indices))
        for bad in [[],indices[:-3],[0,1,2]+indices[3:],[9]+indices[1:],indices+indices[:3]]:
            with self.assertRaises(ValueError):C.validate_closed_indices(points,bad)
    def test_png_exported_opaque_rgba_and_rgb_decode_same_pixels(self):
        def chunk(kind,payload):return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
        def png(color,pixels):return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,1,8,color,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00'+bytes(pixels)))+chunk(b'IEND',b'')
        rgb=self.source/'rgb.png';rgba=self.source/'rgba.png';rgb.write_bytes(png(2,[255,60,0,255,80,0]));rgba.write_bytes(png(6,[255,60,0,255,255,80,0,255]));self.assertEqual(C.png_rgb(rgb),C.png_rgb(rgba));rgba.write_bytes(png(6,[255,60,0,0,255,80,0,255]))
        with self.assertRaises(ValueError):C.png_rgb(rgba)
    def test_mixed_or_unreceipted_candidate_references_rejected(self):
        d=copy.deepcopy(self.document);d['elements'][0]['mesh']=C.object_path(self.plan['assets'][0]['mesh']);self.house.write_text(json.dumps(d));digest=C.sha(self.house);self.receipt['runtime_data_sha256'][C.HOUSE]=digest;self.receipt['protected_content_sha256'][C.HOUSE]=digest;self.write_receipt();self.rejected_without_house_mutation()
    def test_postpublication_same_semantics_different_bytes_rejected(self):
        self.run_publish(True);self.house.write_bytes(self.house.read_bytes()+b' ');self.rejected_without_house_mutation()
    def test_source_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):C.inside(self.source,'../escape')
    def test_nonfinite_degenerate_and_interior_hull_vertices_rejected(self):
        box=[[x,y,z]for x in [-1,1]for y in [-1,1]for z in [-1,1]];self.assertTrue(C.validate_convex_points(box))
        for points in [box+[[0,0,0]],[[0,0,0],[1,0,0],[0,1,0],[1,1,0]],box+[[float('nan'),0,0]],box+[box[0]]]:
            with self.assertRaises(ValueError):C.validate_convex_points(points)


if __name__=='__main__':unittest.main()
