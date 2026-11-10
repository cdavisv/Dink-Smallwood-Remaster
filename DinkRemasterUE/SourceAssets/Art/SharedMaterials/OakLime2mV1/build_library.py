"""Generic physically scaled 2m surface sources. CPU Cycles bake, no object atlas."""
import bpy,math,json,hashlib,os,sys
import numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent;T=O/'Textures';T.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=8;s.render.threads_mode='FIXED';s.render.threads=2
RAW=O/'Inputs/OakReference/AgedOak_Albedo_Raw.png';assert hashlib.sha256(RAW.read_bytes()).hexdigest()=='2475c5a8a57e5d85570934d76b4a6566486a88dddfd7dff085a52c3e4209799f'
raw=bpy.data.images.load(str(RAW));raw.colorspace_settings.name='sRGB';raw.pack();raw.filepath='//Inputs/OakReference/AgedOak_Albedo_Raw.png'
roles=['OakLonggrain2m','OakEndgrain2m','LimePlaster2m'];sources={};tileplanes=[]
def source(role):
 m=bpy.data.materials.new('SRC_Shared_'+role);m.use_nodes=True;m.use_fake_user=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');p.inputs['IOR'].default_value=1.46 if role=='LimePlaster2m' else 1.5;p.inputs['Specular IOR Level'].default_value=.25
 def node(k):return n.new(k)
 def calc(op,*values):
  q=node('ShaderNodeMath');q.operation=op
  for inp,x in zip(q.inputs,values):
   if isinstance(x,(int,float)):inp.default_value=x
   else:l.new(x,inp)
  return q.outputs[0]
 def mix(a,b,w):
  q=node('ShaderNodeMixRGB');q.blend_type='MIX';l.new(w,q.inputs[0]);l.new(a,q.inputs[1]);l.new(b,q.inputs[2]);return q.outputs[0]
 def ramp(x,a,b):
  q=node('ShaderNodeValToRGB');q.color_ramp.elements[0].color=(*a,1);q.color_ramp.elements[1].color=(*b,1);l.new(x,q.inputs[0]);return q.outputs[0]
 tc=node('ShaderNodeTexCoord');sp=node('ShaderNodeSeparateXYZ');l.new(tc.outputs['UV'],sp.inputs[0]);u,v=sp.outputs['X'],sp.outputs['Y']
 uu=calc('MULTIPLY',u,2*math.pi);vv=calc('MULTIPLY',v,2*math.pi)
 def noise(ax,ay,detail=3):
  xyz=node('ShaderNodeCombineXYZ')
  for inp,x in zip(xyz.inputs,[calc('MULTIPLY',calc('COSINE',uu),ax),calc('MULTIPLY',calc('SINE',uu),ax),calc('MULTIPLY',calc('COSINE',vv),ay)]):l.new(x,inp)
  q=node('ShaderNodeTexNoise');q.noise_dimensions='4D';q.inputs['Scale'].default_value=1;q.inputs['Detail'].default_value=detail;q.inputs['Roughness'].default_value=.7;l.new(xyz.outputs[0],q.inputs['Vector']);l.new(calc('MULTIPLY',calc('SINE',vv),ay),q.inputs['W']);return q.outputs['Fac']
 weather=noise(2.5,2.5);grain=noise(100,1.4,2);pores=noise(180,16,2)
 if role=='OakLonggrain2m':
  # All four albedo samples are from one immutable reference. Smooth periodic
  # shader blending gives identical boundary values; independent maps below.
  samples=[]
  for dx,dy in [(0,0),(.5,0),(0,.5),(.5,.5)]:
   add=node('ShaderNodeVectorMath');add.operation='ADD';add.inputs[1].default_value=(dx,dy,0);l.new(tc.outputs['UV'],add.inputs[0]);im=node('ShaderNodeTexImage');im.image=raw;im.extension='REPEAT';l.new(add.outputs[0],im.inputs[0]);samples.append(im.outputs[0])
  wu=calc('POWER',calc('MULTIPLY',calc('SUBTRACT',1,calc('COSINE',uu)),.5),.55);wv=calc('POWER',calc('MULTIPLY',calc('SUBTRACT',1,calc('COSINE',vv)),.5),.55)
  bc=mix(mix(samples[3],samples[2],wu),mix(samples[1],samples[0],wu),wv)
  tint=node('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[2].default_value=(.88,.82,.72,1);l.new(bc,tint.inputs[1]);l.new(tint.outputs[0],p.inputs['Base Color'])
  height=calc('ADD',calc('MULTIPLY',grain,.8),calc('MULTIPLY',pores,.2));rmin,rmax=.64,.84;distance=.00045;strength=.28
 elif role=='OakEndgrain2m':
  # A periodic field of softly warped annular bands, usable on any timber cap.
  # Cosine distances wrap continuously in both axes; broad rings under grain.
  radial=calc('SQRT',calc('ADD',calc('SUBTRACT',1,calc('COSINE',uu)),calc('SUBTRACT',1,calc('COSINE',vv))))
  warp=calc('ADD',calc('MULTIPLY',noise(3.2,3.2),20),calc('MULTIPLY',noise(13,13),3.8))
  rings=calc('MULTIPLY',calc('ADD',1,calc('SINE',calc('ADD',calc('MULTIPLY',radial,190),warp))),.5)
  endgrain_pores=noise(120,120,2);fibres=calc('ADD',calc('MULTIPLY',rings,.55),calc('MULTIPLY',endgrain_pores,.45));bc=ramp(fibres,(.095,.047,.019),(.145,.08,.033));l.new(bc,p.inputs['Base Color']);height=calc('ADD',calc('MULTIPLY',rings,.5),calc('MULTIPLY',endgrain_pores,.5));rmin,rmax=.69,.86;distance=.00022;strength=.20
 else:
  bc=ramp(weather,(.40,.35,.265),(.49,.445,.35));l.new(bc,p.inputs['Base Color']);height=noise(110,110,2);rmin,rmax=.82,.94;distance=.0007;strength=.3
 rough=node('ShaderNodeMapRange');rough.inputs['To Min'].default_value=rmin;rough.inputs['To Max'].default_value=rmax;l.new(weather,rough.inputs['Value']);l.new(rough.outputs[0],p.inputs['Roughness'])
 bump=node('ShaderNodeBump');bump.inputs['Strength'].default_value=strength;bump.inputs['Distance'].default_value=distance;l.new(height,bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
 m['repeat_m']=2.;m['normal_provenance']='Independent periodic 4D procedural microrelief; never from BC';return m
for i,role in enumerate(roles):
 sources[role]=source(role);mesh=bpy.data.meshes.new('Tile_'+role);mesh.from_pydata([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)],[],[(0,1,2,3)]);mesh.update();uv=mesh.uv_layers.new(name='UVMap')
 for a,b in zip(uv.data,[(0,0),(1,0),(1,1),(0,1)]):a.uv=b
 plane=bpy.data.objects.new('Reusable2m_'+role,mesh);s.collection.objects.link(plane);plane.location.x=i*2.4;plane.data.materials.append(sources[role]);tileplanes.append(plane)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Shared2m_ProceduralSources.blend'))
manifest={'status':'SOURCE_LIBRARY_CANDIDATE_NOT_PUBLISHED','resolution':1024,'repeat_m':2,'nominal_texels_per_m':512,'normal_orientation':'OpenGL +Y, flip green on UE import if approved','ORM':'R=1 material-only occlusion; G=independent roughness; B=0 dielectric','source_albedo':{'file':'Inputs/OakReference/AgedOak_Albedo_Raw.png','sha256':hashlib.sha256(RAW.read_bytes()).hexdigest(),'origin':'existing built-in imagegen reference; not measured scan; no new service calls'},'materials':[]}
for role,plane in zip(roles,tileplanes):
 for o in s.objects:o.hide_render=o!=plane
 mat=sources[role];maps={}
 for suffix,socket in [('BC','Base Color'),('N_GL',None),('R','Roughness')]:
  im=bpy.data.images.new('T_Shared_'+role+'_'+suffix,width=1024,height=1024,alpha=False);im.colorspace_settings.name='sRGB' if suffix=='BC' else 'Non-Color';work=mat.copy();nodes=work.node_tree.nodes;links=work.node_tree.links;p=nodes.get('Principled BSDF');out=nodes.get('Material Output')
  if socket:
   inp=p.inputs[socket];src=inp.links[0].from_socket if inp.is_linked else None;em=nodes.new('ShaderNodeEmission')
   if src:links.new(src,em.inputs[0])
   else:em.inputs[0].default_value=inp.default_value
   links.new(em.outputs[0],out.inputs[0])
  target=nodes.new('ShaderNodeTexImage');target.image=im;nodes.active=target;plane.data.materials[0]=work;bpy.ops.object.select_all(action='DESELECT');plane.select_set(True);bpy.context.view_layer.objects.active=plane;s.render.bake.use_selected_to_active=False;s.render.bake.margin=0;s.render.bake.use_clear=True
  print('BAKE',role,suffix,flush=True);bpy.ops.object.bake(type='NORMAL' if suffix=='N_GL' else 'EMIT');maps[suffix]=im;plane.data.materials[0]=mat;bpy.data.materials.remove(work)
 arr=np.empty(1024*1024*4,np.float32);maps['R'].pixels.foreach_get(arr);rough=arr[0::4].copy();arr[0::4]=1;arr[1::4]=rough;arr[2::4]=0;arr[3::4]=1
 orm=bpy.data.images.new('T_Shared_'+role+'_ORM',width=1024,height=1024,alpha=False);orm.colorspace_settings.name='Non-Color';orm.pixels.foreach_set(arr);maps['ORM']=orm;bpy.data.images.remove(maps.pop('R'));files={}
 for suffix,im in maps.items():
  path=T/(im.name+'.png');im.filepath_raw=str(path);im.file_format='PNG';im.save();im.pack();im.filepath='//Textures/'+path.name;files[suffix]={'file':str(path.relative_to(O)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'colorspace':im.colorspace_settings.name}
 new=bpy.data.materials.new('MI_Shared_'+role);new.use_nodes=True;new.use_fake_user=True;new['repeat_m']=2.;new['candidate_only']=True;n=new.node_tree.nodes;l=new.node_tree.links;p=n.get('Principled BSDF');p.inputs['IOR'].default_value=1.46 if role=='LimePlaster2m' else 1.5;p.inputs['Specular IOR Level'].default_value=.25;ims={}
 for suffix,im in maps.items():q=n.new('ShaderNodeTexImage');q.image=im;q.extension='REPEAT';q.label=suffix;ims[suffix]=q
 l.new(ims['BC'].outputs[0],p.inputs['Base Color']);sep=n.new('ShaderNodeSeparateColor');l.new(ims['ORM'].outputs[0],sep.inputs[0]);l.new(sep.outputs['Green'],p.inputs['Roughness']);l.new(sep.outputs['Blue'],p.inputs['Metallic']);nm=n.new('ShaderNodeNormalMap');nm.uv_map='UVMap';l.new(ims['N_GL'].outputs[0],nm.inputs['Color']);l.new(nm.outputs[0],p.inputs['Normal']);plane.data.materials[0]=new
 manifest['materials'].append({'role':role,'material':new.name,'files':files,'IOR':p.inputs['IOR'].default_value,'specular_IOR_level':.25,'roughness_linear_range':[float(rough.min()),float(rough.max())]})
 (O/'material_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for o in s.objects:o.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Shared2m_LibraryCandidate.blend'));print('LIBRARY_COMPLETE',flush=True);sys.stdout.flush();os._exit(0)
