"""Read-only whole-cottage native trial contract; no Unreal actions on import."""
from pathlib import Path
import hashlib,json,struct
from house439_opaque_material import validate_graph

SOURCE=Path('SourceAssets/Art/Stonebrook/Refinements/House439SharedExteriorV1')
LIBRARY=Path('SourceAssets/Art/SharedMaterials')
TRIAL='/Game/Dink/Refinements/House439SharedExteriorV1/'
ROLES=('FieldstoneSeed2m','FieldstoneWall2m','WeatheredTimber2m','IronLead2m',
       'LimeMortarSoot2m','DressedReed2m','ThinWavyGlass2m')
NAME='SM_Cottage_Stonebrook_01'
IMPORTER_FILES=tuple(Path(p)for p in (
    'Scripts/RoofNative/house439_contract.py','Scripts/RoofNative/house439_native.py',
    'Scripts/RoofNative/house439_material_readback.py',
    'Scripts/RoofNative/house439_glass_material.py','Scripts/RoofNative/house439_opaque_material.py',
    'Scripts/RoofNative/native_mesh_tools_v11c.py','Scripts/RoofNative/native_texture_tools_v11.py',
    'Scripts/RoofNative/shared_roof_native.py','Scripts/RoofNative/native_material_slots_v11.py',
    'Scripts/RoofNative/relative_source_metadata.py',
    'Plugins/DinkImport/Source/DinkImport/Public/DinkRoofSourceMetadataLibrary.h',
    'Plugins/DinkImport/Source/DinkImport/Private/DinkRoofSourceMetadataLibrary.cpp'))



def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_contract(root):
    """Validate source bytes, face roles, physical profiles and finite fresh package set.
    Returned recipes remain unapproved for native graph execution until Root review.
    """
    root=Path(root);require(root.is_absolute()and root.resolve()==root,'Resolved explicit project root required');pins={}
    def local(folder,relative):
        p=root/folder/relative
        require(p.resolve().is_relative_to(root/folder)and p.is_file()and not p.is_symlink(),'Missing/escaped source: '+str(p))
        return p
    for folder in (SOURCE,LIBRARY):
        p=local(folder,'SHA256SUMS.json');pins[p.relative_to(root).as_posix()]=sha(p)
        for relative,digest in json.loads(p.read_text()).items():
            file=local(folder,relative);require(sha(file)==digest,'Frozen source mismatch: '+relative);pins[file.relative_to(root).as_posix()]=digest
    for relative in IMPORTER_FILES:
        p=local(Path('.'),relative);pins[relative.as_posix()]=sha(p)
    registry=json.loads(local(LIBRARY,'manifest.json').read_text())['materials'];source=json.loads(local(SOURCE,'manifest.json').read_text());export=json.loads(local(SOURCE,'export_manifest.json').read_text());proof=json.loads(local(SOURCE,'FULL_FBX_REPORT.json').read_text());meta=json.loads(local(SOURCE,'EXPORTED_METADATA.json').read_text());graphs=json.loads(local(SOURCE,'OPAQUE_GRAPH_SOURCE.json').read_text())
    require(set(source['assets'])=={NAME},'Exactly one source cottage required');asset=source['assets'][NAME]
    identity=asset['sprite_identity'];require(identity['sequence']==63 and identity['frames']==[1]and identity['observed_screens']==[439,530,617],'Narrow original sprite identity differs')
    names={'MI_Shared_'+role for role in ROLES};require(set(asset['material_slots'])==set(meta['material_slots'])==names and len(meta['material_slots'])==7,'Exact seven used source slots required')
    require(asset['class']=='building'and asset['triangles']==194192 and asset['UCX_count']==6,'Cottage geometry budget/UCX differs')
    require(source['source_sha256']==export['source_sha256']==sha(local(SOURCE,source['source'])),'Registered source bytes differ')
    require(len(export['FBX'])==1,'Exactly one cottage FBX required');fbx=export['FBX'][0]
    require(fbx['name']==NAME and fbx['triangles']==194192 and fbx['UCX']==6 and fbx['file']==asset['fbx'],'Full cottage FBX scope differs')
    require(fbx['sha256']==asset['fbx_sha256']==meta['source_file_sha256']==proof['fbx_sha256']==sha(local(SOURCE,fbx['file'])),'Actual FBX proof hash differs')
    require(proof['pass']is True and proof['triangles_before_after']==[194192,194192]and proof['material_roles_exact']is True and set(proof['actual_material_slots'])==names,'Actual exported face roles/counts not established')
    require(proof['rawColor0']==[dict(geometry=proof['rawColor0'][0]['geometry'],layer0='SharedSurfaceData',corners=582576,RGBA_error=0.0)],'Actual raw linear Color0 differs')
    require(proof['max_position_error_m']==proof['linear_RGBA_import_error']==0 and all(v==0 for v in proof['UV_errors'].values()),'Actual source data mismatch')
    require(proof['normal_difference_degrees'][-1]<.05 and proof['Mikk_difference_degrees'][-1]<.05 and proof['zeroT_counts']==[0,0]and proof['bitangent_sign_changes']==0,'Actual FBX frame guards failed')
    require(len(proof['collision_hulls'])==6 and all(h['positions_shape_exact']and h['max_position_error_m']==h['max_TRS_error']==0 for h in proof['collision_hulls']),'Original hull correspondence missing')
    require(graphs['source_sha256']==sha(local(LIBRARY,'ArchitecturalSurfaces2mV1/SharedArchitecturalSurfaces_Source.blend')),'Opaque source graph extraction stale')
    textures={};materials=[];packages={}
    for role in ROLES:
        entry=registry[role];require(entry['material']=='MI_Shared_'+role and entry['repeat_m']==2 and entry['nominal_texels_per_m']==512,'Shared physical role differs')
        typed={}
        variants=entry.get('variants',{'Default':{'textures':entry['textures']}})
        for variant in variants.values():
            require(set(variant['textures'])=={'BC','N','ORM'},'Complete map set required')
            for kind,image in variant['textures'].items():
                p=local(LIBRARY,image['file']);require(sha(p)==image['sha256'],'Shared image hash differs');header=p.read_bytes()[:29];require(header[:8]==b'\x89PNG\r\n\x1a\n','PNG required');w,h,bits,color,*_=struct.unpack('>IIBBBBB',header[16:29]);require((w,h)==(1024,1024)and bits==image['bit_depth']and color==image['png_color_type'],'Actual PNG format differs')
                require(image['srgb']is(kind=='BC')and image['native_flip_green']is(kind=='N'),'Declared native texture flags differ')
                require(kind!='N'or image['normal_orientation']=='OpenGL +Y','Normal orientation differs')
                package=TRIAL+'Textures/'+p.stem;record=dict(package=package,source_file=p.relative_to(root).as_posix(),source_sha256=image['sha256'],srgb=kind=='BC',flip_green=kind=='N',compression='TC_NORMALMAP'if kind=='N'else'TC_DEFAULT'if kind=='BC'else'TC_MASKS',address='Wrap',size=1024,bit_depth=bits)
                require(package not in textures or textures[package]==record,'Texture target collision');textures[package]=record;packages[package]='Texture2D';typed[p.name]=package
        recipe={'package':TRIAL+'Materials/'+entry['material'],'source_material':entry['material'],'textures':typed,'profile':entry['shader_profile']}
        if role=='ThinWavyGlass2m':
            recipe.update(textures={kind:TRIAL+'Textures/'+Path(image['file']).stem for kind,image in entry['textures'].items()},native_policy_reviewed=False,physical_uv_reviewed=False,front_back_policy='closed_panes_front_faces_only',uv_channel=0,transmission=1,surface_coverage=1,top_material_coverage=0,IOR=1.48,unreal_specular=entry['unreal_specular'],two_sided=False,substrate_enabled=False)
            require(entry['IOR']==1.48 and entry['transmission']==1 and entry['thin_wall']is True,'Registered glass optical contract differs')
        else:
            g=graphs['materials'][entry['material']];validate_graph(g);images={n['image']['name']:n['image']['packed_sha256']for n in g['nodes']if n['type']=='TEX_IMAGE'};require(set(images)==set(typed),'Source shader images differ from registered variants')
            for name,digest in images.items():require(textures[typed[name]]['source_sha256']==digest,'Shader packed pixels differ')
            recipe.update(source_graph_reviewed=False,uv1_semantic_decode='U,1-V',source_graph=g,source_graph_sha256=hashlib.sha256(json.dumps(g,sort_keys=True).encode()).hexdigest())
        materials.append(recipe);packages[recipe['package']]='Material'
    mesh=dict(name=NAME,package=TRIAL+'Meshes/'+NAME,file=fbx['file'],source_sha256=fbx['sha256'],triangles=194192,UCX=6,material_slots=meta['material_slots'],UV_channels=['UV0','UV1_SharedData'],color0='SharedSurfaceData',normal_tangent_basis='UV0',native_UV_convention='LegacyFBX imports V=1-sourceV on allchannels; semanticUV1Y decoded byOneMinus inmaterial, UV0 stays texture convention',collision='SIMPLE_AND_COMPLEX',nanite=False)
    packages[mesh['package']]='StaticMesh';require(len(textures)==30 and len(materials)==7 and len(packages)==38,'Exact fresh38 trial scope differs')
    result=dict(schema='dink-house439-native-trial/1',source_pins=pins,textures=list(textures.values()),materials=materials,meshes=[mesh],trial_packages=packages,production_activated=False,native_review_required=True)
    result['digest']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest();return result


def assert_trial_absent(root,contract):
    for package in contract['trial_packages']:
        require(package.startswith(TRIAL)and '..'not in package and '.'not in package,'Trial package escaped')
        file=Path(root)/('Content/'+package.removeprefix('/Game/')+'.uasset')
        require(not file.exists()and not file.is_symlink(),'Refusing existing trial package: '+package)
