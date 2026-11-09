import bpy,json,time,hashlib,struct,traceback
import numpy as np
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];args=sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[];assert '--out'in args,'Specify --out outside frozen packet';D=Path(args[args.index('--out')+1]).resolve();assert not D.is_relative_to(ROOT),'Output must be outside packet';P=ROOT;T=D/'Textures';T.mkdir(parents=True,exist_ok=True);S=ROOT/'Source/Helpers/Trousers_CoarseProcedural.blend';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pin=sha(S);bpy.ops.wm.open_mainfile(filepath=str(S));scene=bpy.context.scene;ob=bpy.data.objects['NEW_Dink_Trousers_LOD0'];m=ob.data;mat=m.materials[0];bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL');surface=out.inputs['Surface'].links[0].from_socket;arm=bpy.data.objects['Armature'];poseposition=arm.data.pose_position;view={k:getattr(scene.view_settings,k)for k in ['view_transform','look','exposure','gamma']};imagefmt={k:getattr(scene.render.image_settings,k)for k in ['file_format','color_mode','color_depth']};arm.data.pose_position='REST';scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=2;scene.cycles.samples=16;scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=False;scene.render.bake.margin=8;scene.render.bake.margin_type='EXTEND';scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';m.uv_layers.active_index=m.uv_layers.find('WardrobeAtlasUV')
for uv in m.uv_layers:uv.active_render=uv.name=='WardrobeAtlasUV'
bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.hide_viewport=False;ob.select_set(True);bpy.context.view_layer.objects.active=ob;ns=mat.node_tree.nodes;links=mat.node_tree.links;tex=ns.new('ShaderNodeTexImage');tex.name='OWN_TEMPORARY_2K_BAKE_TARGET'
for n in ns:n.select=False
tex.select=True;ns.active=tex;temporary=[];reports=[];loaded={};started=time.time();size=2048
attrs={name:{'min':min(x.value for x in m.attributes[name].data),'max':max(x.value for x in m.attributes[name].data)}for name in ['GarmentSeamDistance','GarmentSeamArc','ClothTexelsPerMeter']};assert attrs['ClothTexelsPerMeter']['min']>800 and attrs['GarmentSeamDistance']['max']>.02

def progress(stage,**data):
 row={'stage':stage,'elapsed_seconds':time.time()-started,**data};(D/'bake_progress.json').write_text(json.dumps(row,indent=2)+'\n');print('WOVEN_BAKE',json.dumps(row),flush=True)
def image_for(kind,bg):
 im=bpy.data.images.new('Dink_PantsV31_'+kind,width=size,height=size,float_buffer=True,is_data=kind!='BC');im.colorspace_settings.name='Linear Rec.709'if kind=='BC'else'Non-Color';im.generated_color=bg;pixels=np.empty((size*size,4),dtype=np.float32);pixels[:]=bg;im.pixels.foreach_set(pixels.ravel());del pixels;im.update();tex.image=im;ns.active=tex;return im
def restore():links.new(surface,out.inputs['Surface'])
def emission(kind):
 em=ns.new('ShaderNodeEmission');temporary.append(em);em.inputs['Strength'].default_value=1
 if kind=='BC':links.new(bs.inputs['Base Color'].links[0].from_socket,em.inputs['Color'])
 else:
  comb=ns.new('ShaderNodeCombineColor');comb.mode='RGB';comb.inputs['Red'].default_value=1.;comb.inputs['Green'].default_value=bs.inputs['Roughness'].default_value;comb.inputs['Blue'].default_value=0.;links.new(comb.outputs[0],em.inputs['Color']);temporary.append(comb)
 links.new(em.outputs[0],out.inputs['Surface'])
def save_validate(kind,im,bits):
 scene.render.image_settings.color_depth=str(bits);path=T/('T_Dink_Trousers_V31_'+kind+'.png');im.save_render(str(path),scene=scene);head=path.read_bytes()[:33];assert head[:8]==b'\x89PNG\r\n\x1a\n';w,h,depth,ctype,_,_,inter=struct.unpack('>IIBBBBB',head[16:29]);assert(w,h,depth,ctype)==(size,size,bits,2);src=np.empty(size*size*4,dtype=np.float32);im.pixels.foreach_get(src);src=src.reshape(-1,4);re=bpy.data.images.load(str(path),check_existing=False);re.colorspace_settings.name='sRGB'if kind=='BC'else'Non-Color';raw=np.empty(src.size,dtype=np.float32);re.pixels.foreach_get(raw);raw=raw.reshape(-1,4);assert np.isfinite(src).all()and np.isfinite(raw).all();decoded=raw.copy()
 if kind=='BC':decoded[:,:3]=np.where(raw[:,:3]<=.04045,raw[:,:3]/12.92,((raw[:,:3]+.055)/1.055)**2.4)
 err=np.abs(decoded[:,:3]-src[:,:3]);tol=.0045 if kind=='BC'else(1/65535+.000001 if kind=='N'else 1/255+.000001);assert err.max()<=tol,(kind,float(err.max()),tol);row={'map':kind,'path':str(path),'sha256':sha(path),'width':w,'height':h,'bits':depth,'PNG_color_type':ctype,'color_space':re.colorspace_settings.name,'all_pixels_checked':size*size,'maximum_linear_roundtrip_error':float(err.max()),'mean_linear_roundtrip_error':float(err.mean()),'source_RGB_min':src[:,:3].min(axis=0).tolist(),'source_RGB_max':src[:,:3].max(axis=0).tolist()}
 if kind=='N':
  vectors=src[:,:3]*2-1;length=np.linalg.norm(vectors,axis=1);row.update({'tangent_convention':'OpenGL +Y full RGB16; no channel reconstruction/clamp','normal_length_min':float(length.min()),'normal_length_max':float(length.max())})
 if kind=='ORM':assert raw[:,2].max()==0;assert raw[:,0].min()==1;row['AO_all_pixels_exact_one']=True;row['metallic_all_pixels_exact_zero']=True
 re.pack();assert hashlib.sha256(bytes(re.packed_file.data)).hexdigest()==row['sha256'];re.filepath='//Textures/'+path.name;loaded[kind]=re;reports.append(row);(D/'map_validation.json').write_text(json.dumps(reports,indent=2)+'\n');bpy.data.images.remove(im);progress('SAVED_'+kind,report=row)
try:
 progress('BEGIN_BC',CPU_threads=2,source_attributes=attrs);im=image_for('BC',(.117,.156,.043875,1));emission('BC');bpy.ops.object.bake(type='EMIT');restore();save_validate('BC',im,8)
 progress('BEGIN_NORMAL');im=image_for('N',(.5,.5,1,1));scene.render.bake.normal_space='TANGENT';scene.render.bake.normal_r='POS_X';scene.render.bake.normal_g='POS_Y';scene.render.bake.normal_b='POS_Z';bpy.ops.object.bake(type='NORMAL');save_validate('N',im,16)
 progress('BEGIN_ORM');im=image_for('ORM',(1,.83,0,1));emission('ORM');bpy.ops.object.bake(type='EMIT');restore();save_validate('ORM',im,8)
 for n in temporary:ns.remove(n)
 ns.remove(tex);new=mat.copy();new.name='ART_Dink_OliveHomespun_BAKED2K_V31';nn=new.node_tree.nodes;nn.clear();ll=new.node_tree.links;pbs=nn.new('ShaderNodeBsdfPrincipled');output=nn.new('ShaderNodeOutputMaterial');ll.new(pbs.outputs[0],output.inputs['Surface']);optics={}
 for sock in pbs.inputs:
  if sock.name not in bs.inputs or not hasattr(sock,'default_value'):continue
  origin=bs.inputs[sock.name]
  try:sock.default_value=origin.default_value
  except(TypeError,ValueError):continue
  if sock.name not in ['Base Color','Normal','Roughness','Metallic']:
   try:optics[sock.name]=float(origin.default_value)
   except(TypeError,ValueError):
    try:optics[sock.name]=list(origin.default_value)
    except TypeError:pass
 uv=nn.new('ShaderNodeUVMap');uv.uv_map='WardrobeAtlasUV';images={}
 for kind,im in loaded.items():
  node=nn.new('ShaderNodeTexImage');node.image=im;node.extension='EXTEND';node.interpolation='Linear';ll.new(uv.outputs['UV'],node.inputs['Vector']);images[kind]=node
 ll.new(images['BC'].outputs['Color'],pbs.inputs['Base Color']);sep=nn.new('ShaderNodeSeparateColor');sep.mode='RGB';ll.new(images['ORM'].outputs['Color'],sep.inputs['Color']);ll.new(sep.outputs['Green'],pbs.inputs['Roughness']);ll.new(sep.outputs['Blue'],pbs.inputs['Metallic']);normal=nn.new('ShaderNodeNormalMap');normal.space='TANGENT';normal.uv_map='WardrobeAtlasUV';normal.inputs['Strength'].default_value=1;ll.new(images['N'].outputs['Color'],normal.inputs['Color']);ll.new(normal.outputs['Normal'],pbs.inputs['Normal']);ob.data.materials[0]=new
 if mat.users==0:bpy.data.materials.remove(mat)
 arm.data.pose_position=poseposition
 for k,v in view.items():setattr(scene.view_settings,k,v)
 for k,v in imagefmt.items():setattr(scene.render.image_settings,k,v)
 ob['source_stage']='BAKED2K SOURCE EXPLORATION ONLY: exact V19 geometry; coarse component only; selected physical limitations remain; no export/native';target=D/'Dink_Trousers_Homespun_BAKED2K_SOURCE.blend';bpy.ops.wm.save_as_mainfile(filepath=str(target),relative_remap=False);assert sha(S)==pin;receipt={'scope':'SOURCE exploration only, exact V19 geometry/weights and 13-panel UV. No physical/motion/export/native acceptance. Fresh dedicated BC8sRGB / OpenGLfullRGBN16NonColor / ORM8NonColor. AO1 is neutral and not wired as painted lighting.','source_sha256':pin,'baked_source_sha256':sha(target),'maps':reports,'preserved_independent_optics':optics,'source_view_settings_restored':view,'source_attributes':attrs,'source_CPU_threads':2,'bake_padding_px':8,'bake_method':'Project bake_wardrobe252 IO validation adapted to RGB/2K/CPU2/pants-only, no AO bake; no forced process exit.','planned_portable_used_texture_groups_before_after':[9,12],'procedural_master_retains_editable_grain_uv':str(S),'elapsed_seconds':time.time()-started};(D/'bake_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');progress('COMPLETE',baked_source=str(target))
except Exception as e:
 restore();progress('FAILED',error=repr(e),traceback=traceback.format_exc());raise
