from pathlib import Path
exec((Path(__file__).parent/'profile_milder.py').read_text().replace("bpy.ops.wm.save_as_mainfile(filepath='/tmp/dink-art/milder_body.blend')",''))
from mpfb.services.exportservice import ExportService
DATA=Path('/tmp/dink-mpfb-user/data')
HumanService.set_character_skin(str(DATA/'skins/young_caucasian_male/young_caucasian_male.mhmat'),body,skin_type='GAMEENGINE')
parts={}
for key,path in [('Eyes','eyes/low-poly/low-poly.mhclo'),('Hair','hair/short04/short04.mhclo'),('Eyebrows','eyebrows/eyebrow001/eyebrow001.mhclo'),('Eyelashes','eyelashes/eyelashes01/eyelashes01.mhclo')]:
    parts[key]=HumanService.add_mhclo_asset(str(DATA/path),body,asset_type=key,subdiv_levels=0,material_type='GAMEENGINE',set_up_rigging=False,import_weights=False)
mask=body.modifiers.get('Hide helpers');mask.show_viewport=False
de=bpy.context.evaluated_depsgraph_get();bpy.context.view_layer.update();ev=body.evaluated_get(de);full=ev.to_mesh()
groups={}
for g in body.vertex_groups:
    if g.name.startswith('joint-'):
        ids=[v.index for v in body.data.vertices if any(w.group==g.index for w in v.groups)]
        if ids:groups[g.name]=[sum(full.vertices[i].co[k] for i in ids)/len(ids) for k in range(3)]
ev.to_mesh_clear();mask.show_viewport=True
Path('/tmp/dink-art/milder_landmarks.json').write_text(json.dumps(groups,indent=2)+'\n')
ExportService.bake_modifiers_remove_helpers(body,bake_masks=True,remove_helpers=True)
# Bake phenotype once; retain a compact static source for clothing and armature transfer.
for obj in [body,*parts.values()]:
    bpy.context.view_layer.objects.active=obj
    if obj.data.shape_keys:
        final=obj.shape_key_add(name='FinalPhenotype',from_mix=True)
        coords=[v.co.copy() for v in final.data]
        obj.shape_key_clear()
        for v,p in zip(obj.data.vertices,coords):v.co=p
    for mod in list(obj.modifiers):
        if mod.type!='ARMATURE':bpy.ops.object.modifier_apply(modifier=mod.name)
body.name='Milder_AnatomicalBody'
print('CLEAN DINK',[(o.name,len(o.data.vertices),len(o.data.polygons)) for o in [body,*parts.values()]])
bpy.ops.wm.save_as_mainfile(filepath='/tmp/dink-art/milder_base.blend')
