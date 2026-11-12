"""Generate the dink LODs and export the empirically verified UE skeleton format."""
import bpy,bmesh,json,sys,math,os
from pathlib import Path
from mathutils import Vector
ROOT=Path('<HOME>/Repos/Dink-Smallwood/DinkRemasterUE');ART=ROOT/'SourceAssets/Art/Characters/Dink'
sys.path.insert(0,str(ROOT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import common,make_lods,validate,export_ue
bpy.ops.wm.open_mainfile(filepath=str(ART/'Working/Dink_Baked.blend'))
coll=bpy.data.collections['SK_Dink'];arm=next(o for o in coll.objects if o.type=='ARMATURE');arm.name='Armature';arm.data.pose_position='REST'
coll['dink_class']='character_hero';coll['dink_path']='Dink';coll['dink_tex_px']=4096
ob=bpy.data.objects['SK_Dink_LOD0']
# Remove microscopic neck-cut slivers before LOD generation, preserving deform/UV layers.
bm=bmesh.new();bm.from_mesh(ob.data)
bad=[face for face in bm.faces if face.calc_area()<1e-8]
removed_zero_area=len(bad)
if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
wire=[edge for edge in bm.edges if not edge.link_faces]
if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
loose=[v for v in bm.verts if not v.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bm.to_mesh(ob.data);bm.free();ob.data.update()
asset=common.Asset(coll)
make_lods.make_lods(asset,[.5,.25,.12],replace=True,force=True);asset.refresh()
normal_fixes=[]
for mesh in asset.renders:
    # Open/thin cloth can acquire cancelling smooth normals after decimation.
    # Preserve geometry and weights, and use its finite polygon normals at those corners.
    data=mesh.data;bad={i for i,n in enumerate(data.corner_normals) if n.vector.length<1e-4}
    changed=0
    for p in data.polygons:
        if any(i in bad for i in p.loop_indices):p.use_smooth=False;changed+=1
    data.update()
    normal_fixes.append({'mesh':mesh.name,'flat_faces_for_cancelled_normals':changed,
                         'remaining_zero_normals':sum(n.vector.length<1e-4 for n in data.corner_normals)})
    for v in data.vertices:
        values=sorted([(g.group,g.weight) for g in v.groups if g.weight>1e-6],key=lambda p:-p[1])[:4]
        total=sum(w for _,w in values)
        if not total:raise RuntimeError(f'Unweighted vertex {v.index} in {mesh.name}')
        for g in mesh.vertex_groups:g.remove([v.index])
        for group,weight in values:mesh.vertex_groups[group].add([v.index],weight/total,'REPLACE')
    mesh.hide_render=mesh.name!='SK_Dink_LOD0'
for image in bpy.data.images:
    path=Path(bpy.path.abspath(image.filepath)) if image.filepath else None
    if path and path.parent==ART/'Textures':image.filepath='//Textures/'+path.name
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink.blend'),relative_remap=False)
verdict=validate.validate_scene(only=['SK_Dink'])
(ART/'dink_validation.json').write_text(json.dumps(verdict,indent=2)+'\n')
if verdict['summary']['errors']:
    print('DINK VALIDATION ERRORS',json.dumps(verdict['summary']),flush=True)
    for item in verdict['assets']:
        for finding in item['findings']:
            if finding['severity']=='error':print(finding['code'],finding['message'],flush=True)
    raise RuntimeError('Dink must pass the asset gate before export')
materials=json.loads((ART/'dink_materials.json').read_text())
bounds=[common.world_bounds(o) for o in asset.renders];mn=Vector(tuple(min(b[0][i] for b in bounds) for i in range(3)));mx=Vector(tuple(max(b[1][i] for b in bounds) for i in range(3)))
base_min,base_max=common.world_bounds(ob)
row={'class':'character_hero','fbx':'Export/SK_Dink_LOD0.fbx','lod_fbx':['Export/SK_Dink_LOD%d.fbx'%i for i in range(4)],
     'dimensions_m':list(base_max-base_min),'lod_union_dimensions_m':list(mx-mn),'materials':[s.material.name for s in ob.material_slots],
     'content_folder':'/Game/Dink/Hero','reference_skeleton':'/Game/Characters/Mannequins/Meshes/SK_Mannequin',
     'source_credits':'CC0 MakeHuman anatomical body/eyes/hair; original project-authored clothing. Epic skeletal reference transforms are separate UE project content, not CC0 geometry.',
     'source_blend':'SK_Dink.blend'}
manifest={'schema':'dink-character-art/1','assets':{'SK_Dink':row},'materials':materials,
    'replacements':[{'origin':'S001_P26','mesh':'SK_Dink','scale':[.9,.9,.9],'rotation_deg':[0,-90,0]}],
    'export_units':'Centimetre FBX, header1; source Blender metres. Geometry/bone positions scaled100 only in temporary export scene.',
    'bone_reference':'Epic Manny/SK_Mannequin; original89bone hierarchy and rest transforms, explicitidentityroot. Not a CC0 body asset.',
    'licence':'CC0 for MakeHuman source geometry/textures; original project-authored wardrobe; see Provenance for full separation.'}
shared_path=ART.parent/'character_manifest.json'
shared=json.loads(shared_path.read_text())
row['fbx']='Dink/'+row['fbx'];row['lod_fbx']=['Dink/'+p for p in row['lod_fbx']];row['source_blend']='Dink/'+row['source_blend']
for mat in materials.values():
    for key,path in mat.get('textures',{}).items():mat['textures'][key]='Dink/'+path
shared['assets']['SK_Dink']=row;shared['materials'].update(materials);shared['player']={'mesh':'SK_Dink'}
shared_path.write_text(json.dumps(shared,indent=2)+'\n')
(ART/'dink_lod_report.json').write_text(json.dumps({'validation':verdict['summary'],'removed_zero_area_faces':removed_zero_area,'normals':normal_fixes,
    'lods':[{'name':o.name,'triangles':common.tri_count(o),'vertices':len(o.data.vertices)} for o in asset.renders]},indent=2)+'\n')
# Source has already been saved in metres. Convert only this process's export copy.
for mesh in asset.renders:
    for v in mesh.data.vertices:v.co*=100
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='EDIT')
for bone in arm.data.edit_bones:bone.head*=100;bone.tail*=100
bpy.ops.object.mode_set(mode='OBJECT');bpy.context.scene.unit_settings.scale_length=.01
dest=ART/'Export';dest.mkdir(exist_ok=True)
# Manifest supplies every PNG; FBX needs only material slot names, avoiding texture-path warnings.
for material in bpy.data.materials:
    # Blender's exporter traverses retained nodes even with use_nodes=False.
    if material.node_tree:material.node_tree.nodes.clear()
    material.use_nodes=False
for lod in range(4):
    mesh=bpy.data.objects['SK_Dink_LOD%d'%lod]
    proxy=type('ExportAsset',(),{'renders':[mesh],'collision':[],'armatures':[arm],'sockets':[]})()
    with export_ue.unhidden([mesh,arm]):export_ue.export_fbx(proxy,str(dest/('SK_Dink_LOD%d.fbx'%lod)),'all','Armature')
print('DINK EXPORT:4LODs,89bones,5slots;VALIDATION',verdict['summary'],flush=True)
