"""Exact fresh35 fireplace trial contract; source/ledger read-only, no Unreal import."""
from pathlib import Path
import ast,hashlib,json,struct,importlib.util
from fireplace_material import validate_graph,ROLE_SPEC
SOURCE=Path('SourceAssets/Art/Stonebrook/Refinements/FireplaceFiredClayV4')
LIBRARY=Path('SourceAssets/Art/SharedMaterials')
TRIAL='/Game/Dink/Refinements/FireplaceFiredClayV4/'
GRAPH=Path('Docs/Verification/FireplaceNativePreparation/ACTUAL_SOURCE_GRAPHS.json')
NAMES=('SM_Chimney_Stonebrook_V8',)+tuple('SM_Fireplace_Stonebrook_V3Contact_LOD'+str(i)for i in range(3))
COUNTS=dict(zip(NAMES,[(1486,92),(57296,16),(37908,0),(19998,0)]))
ROLES=tuple(n.removeprefix('MI_Shared_')for n in ROLE_SPEC)
IMPORTER_FILES=tuple(Path(p)for p in ('Scripts/RoofNative/fireplace_contract.py','Scripts/RoofNative/fireplace_native.py','Scripts/RoofNative/fireplace_material.py','Scripts/RoofNative/fireplace_material_readback.py','Scripts/RoofNative/fireplace_mesh_readback.py','Scripts/RoofNative/house439_mesh_readback.py','Scripts/RoofNative/native_mesh_tools_v11c.py','Scripts/RoofNative/native_texture_tools_v11.py','Scripts/RoofNative/shared_roof_native.py','Scripts/RoofNative/native_material_slots_v11.py','Scripts/RoofNative/native_collision_readback_v11.py','Scripts/RoofNative/geometry_only_match_v11.py','Scripts/RoofNative/relative_source_metadata.py','Plugins/DinkImport/Source/DinkImport/Public/DinkMaterialArtLibrary.h','Plugins/DinkImport/Source/DinkImport/Private/DinkStaticMeshGeometryInspection.cpp','Plugins/DinkImport/Source/DinkImport/Public/DinkRoofSourceMetadataLibrary.h','Plugins/DinkImport/Source/DinkImport/Private/DinkRoofSourceMetadataLibrary.cpp'))
def require(ok,message):
    if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dependency_files(root):
    """Pin local Python import closure and editor plugin implementation bytes."""
    pending=list(IMPORTER_FILES);seen=set()
    while pending:
        relative=pending.pop()
        if relative in seen:continue
        seen.add(relative)
        if relative.suffix!='.py':continue
        for node in ast.walk(ast.parse((root/relative).read_text())):
            names=[node.module]if isinstance(node,ast.ImportFrom)and node.module else[n.name for n in node.names]if isinstance(node,ast.Import)else[]
            for name in names:
                for directory in ('Scripts/RoofNative','Scripts'):
                    candidate=Path(directory)/(name.replace('.','/')+'.py')
                    if (root/candidate).is_file():pending.append(candidate);break
    plugin=root/'Plugins/DinkImport/Source'
    seen.update(p.relative_to(root)for p in plugin.rglob('*')if p.is_file()and p.suffix in {'.h','.cpp','.cs'})
    return tuple(sorted(seen))
def fbx_model_metadata(root,record):
    """Pin known cm header/model transforms, never assume cottage identity or rewrite FBX."""
    parser=Path(root)/SOURCE/'Tools/fbxparse.py';spec=importlib.util.spec_from_file_location('fireplace_fbx_metadata',parser);F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
    _,nodes=F.parse(Path(root)/SOURCE/record['file']);top={n.name:n for n in nodes};g=F._p70(top['GlobalSettings']);expected=dict(UpAxis=2,UpAxisSign=1,FrontAxis=1,FrontAxisSign=1,CoordAxis=0,CoordAxisSign=-1,UnitScaleFactor=1.)
    require(all(g.get(k)==v for k,v in expected.items()),'Unreviewed FBX axis/unit header')
    name=record['name'];translation=[0.,0.,350.]if name==NAMES[0]else[45.9375,-597.1875,0.];models={}
    for n in top['Objects'].children:
        if n.name!='Model':continue
        key=n.props[1].split('\0')[0];p=F._p70(n);require(key==name or key.startswith('UCX_'+name+'_'),'Unexpected FBX model')
        require(p.get('Lcl Translation')==translation and p.get('Lcl Scaling')==[100.,100.,100.]and p.get('Lcl Rotation')==[0.,-0.,180.00000500895632],'Unreviewed source model translation/rotation/scale')
        for prop in ('GeometricTranslation','GeometricRotation','RotationPivot','ScalingPivot','PreRotation','PostRotation'):require(prop not in p or p[prop]==[0.,0.,0.],'Unreviewed source pivot/geometric transform')
        require('GeometricScaling'not in p or p['GeometricScaling']==[1.,1.,1.],'Unreviewed geometric scale');models[key]=p
    require(len(models)==1+record['UCX']and name in models,'FBX model/UCX scope differs')
    objects={n.props[0]:n for n in top['Objects'].children};model=next(n for n in objects.values()if n.name=='Model'and n.props[1].split('\0')[0]==name);links=[c for c in top['Connections'].children if len(c.props)>2 and c.props[0]=='OO'and c.props[2]==model.props[0]and c.props[1]in objects]
    geometry=next(objects[c.props[1]]for c in links if objects[c.props[1]].name=='Geometry');slots=[objects[c.props[1]].props[1].split('\0')[0]for c in links if objects[c.props[1]].name=='Material'];require(slots==record['material_slots'],'Serialized source slot table differs')
    ids=geometry.first('LayerElementMaterial').first('Materials').props[0];require(ids and all(type(i)is int and 0<=i<len(slots)for i in ids),'Invalid source face material ID');used={slots[i]for i in ids};unused=set(slots)-used
    colors=geometry.first('LayerElementColor').first('Colors').props[0];rgba=[colors[i:i+4]for i in range(0,len(colors),4)];ranges=[[min(c[i]for c in rgba),max(c[i]for c in rgba)]for i in range(4)];clipped=sum(any(v<0 or v>1 for v in c)for c in rgba);loss=max(abs(v-max(0.,min(1.,v)))for c in rgba for v in c)
    expected_used={'MI_Shared_Soot2m','MI_Shared_IronLead2m','MI_Shared_FiredClayMasonry2m'}if name==NAMES[0]else set(slots);require(used==expected_used,'Actual used source face roles differ')
    return dict(axis_header=expected,models=models,color0_ranges=ranges,out_of_unit_range_direct_colors=clipped,max_clipping_loss=loss,used_materials=sorted(used),unused_materials=sorted(unused),import_translation_cm=[0.,0.,-350.]if name==NAMES[0]else[45.9375,597.1875,0.],pivot_policy='absolute FBX transform with explicit authoring-translation compensation; RAW/built and UCX must match local source metres*100/Yreflection before save; actual native proof pending')
def load_contract(root):
    root=Path(root);require(root.is_absolute()and root.resolve()==root,'Explicit resolved project root required');pins={}
    def local(folder,relative):
        p=root/folder/relative;require(p.resolve().is_relative_to(root/folder)and p.is_file()and not p.is_symlink(),'Missing/escaped source '+str(p));return p
    for folder in (SOURCE,SOURCE.parent/'FireplaceFiredClayV3',LIBRARY):
        p=local(folder,'SHA256SUMS.json');pins[str(p.relative_to(root))]=sha(p)
        for relative,digest in json.loads(p.read_text()).items():
            f=local(folder,relative);require(sha(f)==digest,'Immutable source bytes differ: '+relative);pins[str(f.relative_to(root))]=digest
    for path in (*dependency_files(root),GRAPH,Path('SourceAssets/asset_ledger.csv')):pins[str(path)]=sha(local(Path('.'),path))
    for data in sorted((root/'Content/Dink/Data/Art').glob('*.json')):
        require(not data.is_symlink(),'Symlink runtime Art manifest');pins[str(data.relative_to(root))]=sha(data)
    registry=json.loads(local(LIBRARY,'manifest.json').read_text())['materials'];manifest=json.loads(local(SOURCE,'source_manifest.json').read_text());proof=json.loads(local(SOURCE,'Evidence/FBX_ROUNDTRIP.json').read_text());graphs=json.loads(local(Path('.'),GRAPH).read_text())
    require(manifest['source_sha256']==graphs['source_sha256']==sha(local(SOURCE,manifest['source'])),'Actual source graph extraction stale')
    require(set(graphs['materials'])==set(ROLE_SPEC),'Exactly seven source parents required');assets={a['name']:a for a in manifest['assets']};require(set(assets)==set(NAMES)and len(proof)==4,'Exactly four source meshes required')
    textures={};materials=[];packages={};images_by_hash={}
    for role in ROLES:
        entry=registry[role];require(entry['material']=='MI_Shared_'+role and entry['repeat_m']==2 and entry['nominal_texels_per_m']==512,'Shared physical role differs')
        variants=entry.get('variants',{'Default':{'textures':entry['textures']}})
        for variant in variants.values():
            require(set(variant['textures'])=={'BC','N','ORM'},'Complete registered set required')
            for kind,image in variant['textures'].items():
                p=local(LIBRARY,image['file']);require(sha(p)==image['sha256'],'Texture hash differs');data=p.read_bytes();require(data[:8]==b'\x89PNG\r\n\x1a\n','PNG required');w,h,bits,color,*_=struct.unpack('>IIBBBBB',data[16:29]);require((w,h)==(1024,1024)and bits in(8,16)and color in(2,6),'Unreviewed PNG size/format')
                require(image['srgb']is(kind=='BC')and image['native_flip_green']is(kind=='N'),'Source texture flags differ')
                package=TRIAL+'Textures/'+p.stem;r=dict(package=package,source_file=str(p.relative_to(root)),source_sha256=image['sha256'],srgb=kind=='BC',flip_green=kind=='N',compression='TC_NORMALMAP'if kind=='N'else'TC_DEFAULT'if kind=='BC'else'TC_MASKS',address='Wrap',size=1024,bit_depth=bits)
                require(package not in textures or textures[package]==r,'Texture package collision');textures[package]=r;packages[package]='Texture2D';images_by_hash.setdefault(image['sha256'],set()).add(package)
    for role in ROLES:
        name='MI_Shared_'+role;g=graphs['materials'][name];validate_graph(g,name);typed={}
        for n in g['nodes']:
            if n['type']!='TEX_IMAGE':continue
            candidates=images_by_hash.get(n['image']['packed_sha256'],set())
            if len(candidates)>1:
                # Two registered clay ORM files deliberately share exact pixels; retain their explicit source names.
                image_name=n['image']['name'].split('.png')[0]+'.png';candidates={p for p in candidates if Path(textures[p]['source_file']).name==image_name}
            require(len(candidates)==1,'Missing/ambiguous actual source image bytes/name');target=next(iter(candidates));r=textures[target];require((n['image']['colorspace']=='sRGB')is r['srgb'],'Actual image colour space differs');typed[n['image']['name']]=target
        recipe=dict(package=TRIAL+'Materials/'+name,source_material=name,textures=typed,profile='fireplace_opaque_source_graph_2m',source_graph=g,source_graph_reviewed=False,uv1_semantic_decode='U,1-V',implicit_image_vector='UV0',IOR=1.5,specular_ior_level=ROLE_SPEC[name],native_unreal_specular=ROLE_SPEC[name]);materials.append(recipe);packages[recipe['package']]='Material'
    meshes=[]
    for name in NAMES:
        a=assets[name];r=next(p for p in proof if p['name']==name);require((r['source']['triangles'],r['hulls'])==COUNTS[name]and a['triangles']==r['source']['triangles']and a['collision_hulls']==r['hulls'],'Source triangle/UCX counts differ');require(r['file']=='FBX/'+name+'.fbx'and r['sha256']==sha(local(SOURCE,r['file']))and all(r['checks'].values()),'Actual FBX roundtrip proof/hash differs')
        record=dict(name=name,package=TRIAL+'Meshes/'+name,file=r['file'],source_sha256=r['sha256'],triangles=r['source']['triangles'],UCX=r['hulls'],material_slots=r['source']['materials'],UV_channels=['UV0','UV1_SharedData','UVMap'],color0='SharedSurfaceData',collision='SIMPLE_AND_COMPLEX',nanite=False,known_source_zero_TB=5 if name==NAMES[0]else 0)
        require(set(record['material_slots'])<=set(ROLE_SPEC),'Unknown source slot parent');record['FBX_metadata']=fbx_model_metadata(root,record);record['import_translation_cm']=record['FBX_metadata']['import_translation_cm'];meshes.append(record);packages[record['package']]='StaticMesh'
    require(len(textures)==24 and len(materials)==7 and len(meshes)==4 and len(packages)==35,'Exact fresh35 scope differs')
    blockers=[dict(mesh=r['name'],reason='Source Color0 exceeds representable native FColor; source review required',max_clipping_loss=r['FBX_metadata']['max_clipping_loss'])for r in meshes if r['FBX_metadata']['out_of_unit_range_direct_colors']]
    result=dict(source_blockers=blockers,schema='dink-fireplace-native-trial/1',source_pins=pins,textures=list(textures.values()),materials=materials,meshes=meshes,trial_packages=packages,production_activated=False,native_review_required=True,source_Mikk_direction='NOT_INDEPENDENTLY_COMPARED_NATIVE',known_source_chimney_invalid_frames=5)
    result['digest']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest();return result
def trial_package_file(root,package):
    root=Path(root);require(root.is_absolute()and root.resolve()==root,'Explicit resolved project root required')
    require(package.startswith(TRIAL)and '..'not in package and '.'not in package,'Escaped fresh package')
    p=root/('Content/'+package.removeprefix('/Game/')+'.uasset')
    for ancestor in (p,*p.parents):
        if ancestor==root:break
        require(not ancestor.is_symlink(),'Symlinked trial package path: '+str(ancestor))
    require(p.resolve().is_relative_to(root),'Trial package escaped project root')
    return p

def assert_trial_absent(root,contract):
    for package in contract['trial_packages']:
        p=trial_package_file(root,package);require(not p.exists(),'Existing fresh target refuses overwrite: '+package)
