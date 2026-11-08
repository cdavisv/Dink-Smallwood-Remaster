"""Portable deterministic texture rebuild from the contained clean source.
blender -b -noaudio -t 4 --python-exit-code 1 -P rebake_from_clean_source.py -- --source WornOakFloorV5_Source.blend --output /new/directory
Output must not exist; input source is never saved or modified.
"""
import bpy,json,hashlib,sys,argparse
from pathlib import Path
import numpy as np
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);SOURCE=a.source.resolve();O=a.output.resolve();assert not O.exists(),'Preserve existing output; choose a newdirectory'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();SOURCE_SHA=sha(SOURCE);manifest=json.loads((SOURCE.parent/'material_manifest.json').read_text());assert SOURCE_SHA==manifest['source_files']['editable_clean_source']['sha256'];O.mkdir();(O/'Textures').mkdir()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));scene=next(s for s in bpy.data.scenes if s.name=='FloorOakV1_SourceAsset');bpy.context.window.scene=scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=4;scene.cycles.samples=1
asset=next(o for o in scene.objects if o.type=='MESH' and not o.name.startswith('UCX_'));original_mesh=asset.data;master=bpy.data.materials['M_Floor_WornOak_V5'];iron=original_mesh.materials[1]
def fingerprint(m):return hashlib.sha256(json.dumps({'vertices':[tuple(v.co) for v in m.vertices],'polygons':[list(p.vertices) for p in m.polygons],'UVs':[[tuple(l.uv) for l in uv.data] for uv in m.uv_layers]},separators=(',',':')).encode()).hexdigest()
geometry_hash=fingerprint(original_mesh);assert geometry_hash==manifest['geometry']['geometry_UV_sha256'];indices=[p.material_index for p in original_mesh.polygons];assert len(original_mesh.materials)==2 and iron.name=='MI_Stonebrook_WroughtIron'
visibility=[(o,o.hide_render) for o in scene.objects]
for obj,_ in visibility:obj.hide_render=True;obj.select_set(False)
col=bpy.data.collections.new('TEMP_BAKE_FIXTURE');scene.collection.children.link(col);mesh=original_mesh.copy();obj=bpy.data.objects.new('Temporary_Bake_Floor',mesh);col.objects.link(obj);obj.select_set(True);bpy.context.view_layer.objects.active=obj
floor_temp=master.copy();floor_temp.name='TEMP_FloorBakeMaterial';mesh.materials[0]=floor_temp
# Slot1 uses neutral unused texture-island fill only in this disposable bake fixture.
# Delivered meshes/material indices and original WroughtIron1 remain unchanged.
fill=bpy.data.materials.new('TEMP_UnusedNailUVFill');fill.use_nodes=True;mesh.materials[1]=fill
bake=scene.render.bake;bake.use_selected_to_active=False;bake.use_clear=False;bake.margin=4;bake.margin_type='EXTEND';bake.normal_space='TANGENT';bake.normal_r='POS_X';bake.normal_g='POS_Y';bake.normal_b='POS_Z'
bs=floor_temp.node_tree.nodes['Matte worn oak'];output=next(n for n in floor_temp.node_tree.nodes if n.type=='OUTPUT_MATERIAL');bc_socket=bs.inputs['Base Color'].links[0].from_socket;rough_socket=bs.inputs['Roughness'].links[0].from_socket
fill_bs=fill.node_tree.nodes.get('Principled BSDF');fill_output=fill.node_tree.nodes.get('Material Output')
targets=[]
for material in [floor_temp,fill]:
 n=material.node_tree.nodes.new('ShaderNodeTexImage');n.name='TEMP_BakeTarget';material.node_tree.nodes.active=n;targets.append(n)
def emission(material,socket=None,color=None):
 n=material.node_tree.nodes.get('TEMP_Emission') or material.node_tree.nodes.new('ShaderNodeEmission');n.name='TEMP_Emission';n.inputs['Strength'].default_value=1
 if socket:material.node_tree.links.new(socket,n.inputs['Color'])
 elif color is not None:
  for link in list(n.inputs['Color'].links):material.node_tree.links.remove(link)
  n.inputs['Color'].default_value=(*color,1)
 out=next(n for n in material.node_tree.nodes if n.type=='OUTPUT_MATERIAL');material.node_tree.links.new(n.outputs[0],out.inputs['Surface'])
textures={};rows=[]
for role,background in [('BC',(.34,.24,.13)),('N',(.5,.5,1)),('ORM',(1,.82,0))]:
 name='T_Stonebrook_FloorOakV1_'+role;image=bpy.data.images.new(name,width=2048,height=2048,alpha=False,float_buffer=False);image.colorspace_settings.name='sRGB' if role=='BC' else 'Non-Color'
 pixels=np.ones((2048,2048,4),dtype=np.float32);pixels[:,:,:3]=background;image.pixels.foreach_set(pixels.ravel());del pixels
 for n in targets:n.image=image
 if role=='BC':emission(floor_temp,bc_socket);emission(fill,color=background);kind='EMIT'
 elif role=='ORM':
  c=floor_temp.node_tree.nodes.new('ShaderNodeCombineColor');c.inputs['Red'].default_value=1;c.inputs['Blue'].default_value=0;floor_temp.node_tree.links.new(rough_socket,c.inputs['Green']);emission(floor_temp,c.outputs[0]);emission(fill,color=background);kind='EMIT'
 else:
  floor_temp.node_tree.links.new(bs.outputs[0],output.inputs['Surface']);fill.node_tree.links.new(fill_bs.outputs[0],fill_output.inputs['Surface']);kind='NORMAL'
 print('BAKE_START',role,flush=True);bpy.ops.object.bake(type=kind);path=O/'Textures'/(name+'.png');image.filepath_raw=str(path);image.file_format='PNG';image.save();textures[role]={'file':str(path.relative_to(O)),'sha256':sha(path)};rows.append({'role':role,'kind':kind,'image_colorspace':image.colorspace_settings.name,'margin_px':4,'original_mesh_unchanged':fingerprint(original_mesh)==geometry_hash});print('BAKE_DONE',role,flush=True)
 (O/'bake_progress.json').write_text(json.dumps({'textures':textures,'passes':rows},indent=2)+'\n')
bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh);bpy.data.collections.remove(col)
for obj,hidden in visibility:obj.hide_render=hidden
assert fingerprint(original_mesh)==geometry_hash and [p.material_index for p in original_mesh.polygons]==indices and original_mesh.materials[1]==iron

assert sha(SOURCE)==SOURCE_SHA
matches={role:textures[role]['sha256']==manifest['textures'][role]['sha256'] for role in textures}
result={'source_file_sha256':SOURCE_SHA,'source_unchanged':True,'textures':textures,'byte_identical_to_reference':matches,'complete':all(matches.values()),'original_geometry_UV_indices_nails_unchanged':fingerprint(original_mesh)==geometry_hash and [p.material_index for p in original_mesh.polygons]==indices and original_mesh.materials[1]==iron}
(O/'rebuild_receipt.json').write_text(json.dumps(result,indent=2)+'\n');assert result['complete'],matches
print('PORTABLE_REBAKE_IDENTICAL',flush=True)
