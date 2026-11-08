"""Pure guarded publisher. Default check writes no files; --apply changes two mesh paths."""
import argparse,json,os,tempfile
from pathlib import Path
import basket_contract as C


def publication(project, source, verification, apply=False, tool_folder=None):
    root=Path(project).resolve();source=Path(source).resolve();verification=Path(verification).resolve()
    C.require_owned_content(root)
    folder=Path(tool_folder or Path(__file__).parent).resolve();receipt=json.loads(verification.read_text())
    C.require(receipt.get('schema')==C.SCHEMA and receipt.get('passed') is True and receipt.get('mode')=='verify','Fresh saved-package verify receipt required')
    C.require(receipt['project']==str(root) and receipt['source']==str(source),'Verification scope differs')
    C.require(receipt['verified_old_baseline'] is True and not receipt['protected_changes'] and not receipt['runtime_data_changes'],'Baseline/verification failure')
    plan=C.load_plan(source,check_pixels=False)
    C.require(plan==receipt['plan'] and C.canonical_hash(plan)==receipt['plan_sha256'],'Source plan changed since verification')
    C.require(C.tool_pins(folder)==receipt['tool_sha256'],'Importer/contract/publisher code changed since verification')
    C.require(C.module_pins(root)==receipt['module_sha256'],'Native modules changed since verification')
    names={a['name']for a in plan['assets']}
    C.require(set(receipt['baseline_native'])==names and set(receipt['native_assets'])==names and set(receipt['material_recipes'])==names,'Incomplete native verification')
    C.require(set(receipt['baseline_package_sha256'])=={C.package_file(a['old'].split('.')[0])for a in plan['assets']},'Old baseline package set')
    for a in plan['assets']:
        native=receipt['native_assets'][a['name']];recipe=receipt['material_recipes'][a['name']]
        C.require(native['triangles']==a['triangles'] and native['UCX_hulls']==a['hulls'] and native['source_normals_imported_and_Mikk_tangents_generated'] is True and native['collision_policy']=='complex-as-simple','Native asset contract failed')
        front=native['native_front_normal_evidence']
        C.require(front['checked_triangles']==a['triangles'] and front['minimum_dot_source_geometric_front']>.99 and front['minimum_dot_authored_source']>0 and front['convention']=='reflectY,keepFBXcornerorder,front=cross(C-A,B-A)','Native winding/front-normal confirmation missing')
        C.require(recipe['direct_BC_N_ORM'] is True and C.valid_native_specular(recipe['specular']) and len(set(recipe['all_native_material_property_ids_checked']))==6,'Native saved graph check missing')
    pixel_keys={a['name']+'/'+r for a in plan['assets']for r in C.ROLES}
    C.require(set(receipt['native_texture_source_pixels'])==pixel_keys and all(len(v)==64 and set(v)<=set('0123456789abcdef')for v in receipt['native_texture_source_pixels'].values()),'Native texture source pixel verification missing')
    source_keys={a['name']+'/'+role for a in plan['assets']for role in ('FBX',)+C.ROLES}
    C.require(set(receipt['native_source_filenames'])==source_keys,'Native source filename proof missing')
    for a in plan['assets']:
        for role in ('FBX',)+C.ROLES:
            relative=a['fbx']if role=='FBX'else a['texture_files'][role];record=receipt['native_source_filenames'][a['name']+'/'+role]
            C.require(record['native_getter_resolved_selected_source']is True and record['file']==relative,'Native source filename role mismatch')
            C.validate_native_source_filename(source,relative,[record['resolved_filename']],plan['source_sha256'][relative])
    saved=receipt['saved_package_sha256'];required=C.packages(plan);scope=C.candidate_files(plan)
    C.require(required.issubset(saved) and set(saved).issubset(scope),'Wrong saved candidate package set')
    verification_hash=C.sha(verification);target=root/C.HOUSE;original=target.read_bytes();original_hash=C.sha(target)
    publication_path=root/'Saved/Art/photoreal_basket_publication.json'
    baseline=receipt['runtime_data_sha256'];C.require(C.HOUSE in baseline,'Missing verified house hash')
    fresh_published=receipt.get('verification_basis')=='published_entry_state'
    C.require(receipt.get('verification_basis','import_receipt')in {'import_receipt','published_entry_state'},'Unknown verification trust origin')
    already=True if fresh_published else original_hash!=baseline[C.HOUSE]
    prior=None
    if already and not fresh_published:
        C.require(publication_path.is_file(),'House differs from verified baseline without exact prior publication')
        prior=json.loads(publication_path.read_text())
        C.require(prior.get('passed') is True and prior.get('applied') is True,'Prior publication not successful')
        C.require(prior['verification_sha256']==verification_hash and prior['verified_baseline_sha256']==baseline[C.HOUSE] and prior['after_sha256']==original_hash,'Prior publication does not authorize current bytes')
        C.require(prior['tool_sha256']==receipt['tool_sha256'] and prior['plan_sha256']==receipt['plan_sha256'],'Prior code/source binding differs')
    document=json.loads(original)
    if fresh_published:
        C.require(receipt.get('publication_state')=='published' and receipt.get('scene_data_approval')is False and receipt.get('writer_scope')=='none','Fresh published receipt scope')
        C.require(original_hash==baseline[C.HOUSE],'Published house differs from entry-pinned verification')
        C.require(C.publication_state(document,plan)=='published','Fresh receipt requires exact all-new references')
        C.require(C.canonical_hash(document)==receipt['house_baseline_semantic_sha256'],'Published context semantic drift')
        proposed=document
    elif already:
        reverted=C.rewrite_house(document,plan,from_new=True)
        C.require(C.canonical_hash(reverted)==receipt['house_baseline_semantic_sha256']==prior['verified_baseline_semantic_sha256'],'Changed non-mesh semantics after publication')
        proposed=document
    else:
        C.require(C.canonical_hash(document)==receipt['house_baseline_semantic_sha256'],'Verified baseline semantic mismatch')
        proposed=C.rewrite_house(document,plan)
        C.require(C.rewrite_house(proposed,plan,from_new=True)==document,'Non-mesh mutation')
    proposed_bytes=(json.dumps(proposed,indent=2)+'\n').encode() if not already else original
    def guards(owned_temporary=None):
        C.require(C.sha(verification)==verification_hash,'Verification receipt changed')
        C.require(C.load_plan(source,check_pixels=False)==plan and C.tool_pins(folder)==receipt['tool_sha256'],'Source/tool drift')
        C.require(C.module_pins(root)==receipt['module_sha256'],'Native module drift')
        ignored=None
        if owned_temporary is not None:
            C.require(owned_temporary.parent==target.parent and owned_temporary.name.startswith('.photoreal-basket-') and owned_temporary.read_bytes()==proposed_bytes,'Owned temporary changed')
            ignored=str(owned_temporary.relative_to(root))
        actual_data=C.pins(root,'Content/Dink/Data');actual_data.pop(ignored,None);C.require(set(actual_data)==set(baseline),'Runtime Data file set changed')
        for relative,digest in baseline.items():
            C.require(relative.startswith('Content/Dink/Data/'),'Runtime key outside Data')
            C.require(actual_data[relative]==(original_hash if relative==C.HOUSE else digest),'Runtime Data drift: '+relative)
        actual_content=C.pins(root,'Content');actual_content.pop(ignored,None);protected=receipt['protected_content_sha256']
        C.require(set(actual_content)==set(protected)|set(saved),'Content file set drift')
        for relative,digest in protected.items():
            C.require(relative.startswith('Content/') and relative not in scope,'Protected package key scope')
            C.require(actual_content[relative]==(original_hash if relative==C.HOUSE else digest),'Protected Content drift: '+relative)
        for relative,digest in saved.items():
            C.require(C.inside(root,relative).is_relative_to(root/'Content') and actual_content[relative]==digest,'Saved package drift: '+relative)
        for relative,digest in receipt['baseline_package_sha256'].items():
            C.require(relative.startswith('Content/Dink/Kits/Stonebrook/') and relative not in scope and C.sha(C.inside(root,relative))==digest,'Original baseline package drift')
        C.require(target.read_bytes()==original,'House changed during publication')
    guards()
    result={'schema':C.SCHEMA,'passed':True,'applied':bool(apply)and not fresh_published,'apply_requested':bool(apply),'already_published':already,'verification_basis':receipt.get('verification_basis','import_receipt'),'writer_scope':'none'if fresh_published else 'two_mesh_paths','scene_data_approval':False,'changed_mesh_references':0 if already else 2,
        'only_mesh_references_changed':True,'asset_rows':1,'instance_rows':1,
        'before_sha256':original_hash,'after_sha256':__import__('hashlib').sha256(proposed_bytes).hexdigest() if apply else original_hash,
        'proposed_sha256':__import__('hashlib').sha256(proposed_bytes).hexdigest(),
        'verified_baseline_sha256':baseline[C.HOUSE],'verified_baseline_semantic_sha256':prior['verified_baseline_semantic_sha256']if prior is not None else C.canonical_hash(document),
        'verification_sha256':verification_hash,'tool_sha256':receipt['tool_sha256'],'plan_sha256':receipt['plan_sha256']}
    if apply and not already:
        lock=publication_path.with_suffix('.lock');lock.parent.mkdir(parents=True,exist_ok=True)
        descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        temporary=None
        try:
            os.write(descriptor,b'photoreal basket publisher\n');os.close(descriptor)
            fd,name=tempfile.mkstemp(prefix='.photoreal-basket-',suffix='.tmp',dir=target.parent);temporary=Path(name)
            with os.fdopen(fd,'wb')as stream:stream.write(proposed_bytes);stream.flush();os.fsync(stream.fileno())
            guards(temporary)  # Last check occurs after temporary output is concrete, before atomic replacement.
            os.replace(temporary,target);temporary=None
            C.require(C.sha(target)==result['after_sha256'],'Written house hash mismatch')
            fd,name=tempfile.mkstemp(prefix='.basket-receipt-',suffix='.tmp',dir=publication_path.parent)
            with os.fdopen(fd,'w')as stream:json.dump(result,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            os.replace(name,publication_path)
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)
            lock.unlink(missing_ok=True)
    # Idempotent checks/applies never rewrite the successful publication receipt.
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',required=True,type=Path);parser.add_argument('--source',required=True,type=Path);parser.add_argument('--verification',required=True,type=Path);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    print(json.dumps(publication(args.project,args.source,args.verification,args.apply),indent=2))


if __name__=='__main__':main()
