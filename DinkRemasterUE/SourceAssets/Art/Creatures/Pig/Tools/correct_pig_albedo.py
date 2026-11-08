"""Apply the reviewed0.5 linear Skin/Muzzle correction on unchanged stable geometry/UVs.
This is a migration of thev1 baked checkpoint. Fresh builds use thev2 procedural palette.
"""
import bpy,json,hashlib,shutil,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];REV='skin-muzzle-linear-half-v2';spec_path=ROOT/'pig_manifest.json'
spec=json.loads(spec_path.read_text())
if spec.get('appearance_revision')==REV and not (ROOT/'Working/AlbedoV1/Textures/T_Pig_Atlas_BC.png').exists():raise RuntimeError('Original atlas required to repeat the color migration safely')
BACKUP=ROOT/'Working/AlbedoV1';BACKUP.mkdir(parents=True,exist_ok=True)
for relative in ['Textures/T_Pig_Atlas_BC.png','SK_Pig.blend','pig_manifest.json','pig_materials.json','asset_ledger_rows.csv']:
    source=ROOT/relative;dest=BACKUP/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(source,dest)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
protected=[ROOT/'Textures/T_Pig_Atlas_N.png',ROOT/'Textures/T_Pig_Atlas_ORM.png',*sorted((ROOT/'Export').glob('*.fbx'))]
protected_before={str(path.relative_to(ROOT)):digest(path) for path in protected}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SK_Pig.blend'))
arm=bpy.data.objects['Armature'];ob=bpy.data.objects['SK_Pig_LOD0'];scene=bpy.context.scene

def geometry_signature():
    h=hashlib.sha256()
    for mesh in sorted((o for o in bpy.data.collections['SK_Pig'].objects if o.type=='MESH'),key=lambda o:o.name):
        h.update(mesh.name.encode())
        for vertex in mesh.data.vertices:
            h.update(struct.pack('<3f',*vertex.co))
            for group in vertex.groups:h.update(struct.pack('<If',group.group,group.weight))
        for face in mesh.data.polygons:
            h.update(struct.pack('<I',face.material_index));h.update(struct.pack('<'+'I'*len(face.vertices),*face.vertices))
        for layer in mesh.data.uv_layers:
            for loop in layer.data:h.update(struct.pack('<2f',*loop.uv))
    for bone in arm.data.bones:
        h.update((bone.name+'|'+(bone.parent.name if bone.parent else '')).encode())
        for row in bone.matrix_local:h.update(struct.pack('<4f',*row))
    for action in sorted(bpy.data.actions,key=lambda a:a.name):
        h.update(action.name.encode())
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag=strip.channelbag(slot)
                    if bag:
                        for curve in bag.fcurves:
                            h.update(curve.data_path.encode());h.update(struct.pack('<I',curve.array_index))
                            for key in curve.keyframe_points:h.update(struct.pack('<2f',*key.co))
    return h.hexdigest()
before=geometry_signature()
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
old_image=next(node.image for node in bpy.data.materials['MI_Pig_Skin'].node_tree.nodes if node.type=='TEX_IMAGE' and node.image.name.startswith('T_Pig_Atlas_BC'))
original_filepath=old_image.filepath;old_image.filepath=str(BACKUP/'Textures/T_Pig_Atlas_BC.png');old_image.reload()
interpolations=[]
for material in ob.data.materials:
    for node in material.node_tree.nodes:
        if node.type=='TEX_IMAGE' and node.image==old_image:
            interpolations.append((node,node.interpolation));node.interpolation='Closest'
new_image=bpy.data.images.new('PigAlbedoV2Temporary',width=2048,height=2048,alpha=True);new_image.colorspace_settings.name='sRGB'
changes=[]
for material in ob.data.materials:
    nodes=material.node_tree.nodes;links=material.node_tree.links;bs=nodes.get('Principled BSDF');out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
    prior=out.inputs['Surface'].links[0].from_socket;source=bs.inputs['Base Color'].links[0].from_socket
    multiplier=None
    if material.name in ['MI_Pig_Skin','MI_Pig_Muzzle']:
        multiplier=nodes.new('ShaderNodeVectorMath');multiplier.operation='SCALE';multiplier.inputs['Scale'].default_value=.5;links.new(source,multiplier.inputs[0]);source=multiplier.outputs['Vector']
    emit=nodes.new('ShaderNodeEmission');links.new(source,emit.inputs['Color']);links.new(emit.outputs[0],out.inputs['Surface'])
    target=nodes.new('ShaderNodeTexImage');target.image=new_image;nodes.active=target
    changes.append((material,prior,out,emit,multiplier,target))
scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=6;scene.render.bake.use_clear=True
bpy.ops.object.bake(type='EMIT')
new_image.filepath_raw=str(ROOT/'Textures/T_Pig_Atlas_BC.png');new_image.file_format='PNG';new_image.save()
for material,prior,out,emit,multiplier,target in changes:
    material.node_tree.links.new(prior,out.inputs['Surface']);material.node_tree.nodes.remove(emit);material.node_tree.nodes.remove(target)
    if multiplier:material.node_tree.nodes.remove(multiplier)
for node,interpolation in interpolations:node.interpolation=interpolation
old_image.filepath=original_filepath;old_image.reload();bpy.data.images.remove(new_image)
if geometry_signature()!=before:raise RuntimeError('Pig geometry/UV/weights/rest/actions changed during color-only correction')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SK_Pig.blend'),relative_remap=False)
materials=json.loads((ROOT/'pig_materials.json').read_text())
for name,color in [('MI_Pig_Skin',[.234,.166,.157]),('MI_Pig_Muzzle',[.2395,.125,.119])]:
    materials[name]['base_color']=color;materials[name]['appearance_revision']=REV
(ROOT/'pig_materials.json').write_text(json.dumps(materials,indent=2)+'\n')
spec['materials']=materials;spec['appearance_revision']=REV;spec['appearance_notes']='Skin/Muzzle linear albedo0.5 vs originalv1; geometry,rig,UV,eye/horn colors,normal,roughness unchanged; noSSS change.'
spec_path.write_text(json.dumps(spec,indent=2)+'\n')
protected_after={str(path.relative_to(ROOT)):digest(path) for path in protected}
if protected_after!=protected_before:raise RuntimeError('Protected normal/roughness/FBX bytes changed')
report={'appearance_revision':REV,'linear_factor':.5,'materials':['MI_Pig_Skin','MI_Pig_Muzzle'],'geometry_uv_weights_rest_actions_sha256_before':before,'geometry_uv_weights_rest_actions_sha256_after':geometry_signature(),
        'protected_sha256_before':protected_before,'protected_sha256_after':protected_after,'original_atlas_backup':'Working/AlbedoV1/Textures/T_Pig_Atlas_BC.png','sss_changed':False}
(ROOT/'Working/albedo_v2_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('PIG ALBEDOV2 BAKE OK:geometry/UV/rig/weights/actions identical; normal/roughness/7FBX bytes identical',flush=True)
