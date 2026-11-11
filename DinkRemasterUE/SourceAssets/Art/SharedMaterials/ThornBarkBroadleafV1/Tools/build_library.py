"""Original shared bark tiling + broadleaf trim authoring and CPU PBR bake.
Blender --background --factory-startup -noaudio -t 2 --python build_library.py
Outputs beside Tools; --out <directory> after -- replays to a new directory.
"""
import bpy,math,json,sys,os,hashlib,argparse
from pathlib import Path
from mathutils import Vector
args=argparse.ArgumentParser();args.add_argument('--out',type=Path);a=args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
P=(a.out or Path(__file__).resolve().parents[1]).resolve();P.mkdir(parents=True,exist_ok=True);(P/'Textures').mkdir(exist_ok=True);(P/'Review').mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1;s.render.threads_mode='FIXED';s.render.threads=2;s.render.bake.use_clear=True;s.render.bake.margin=8;bpy.context.preferences.filepaths.save_version=0;bpy.context.preferences.filepaths.file_preview_type='NONE'

def shader(name):
 m=bpy.data.materials.new(name);m.use_nodes=True;return m,m.node_tree.nodes,m.node_tree.links

def mathnode(n,l,op,x,y=None):
 q=n.new('ShaderNodeMath');q.operation=op
 for i,v in enumerate([x,y]):
  if v is None:continue
  if hasattr(v,'node'):l.new(v,q.inputs[i])
  else:q.inputs[i].default_value=v
 return q.outputs[0]
roles={}
for role,size,spec,rough in [('ThornBark2m',2,.23,.81),('BroadleafTrimV1',.12,.28,.68)]:
 m,n,l=shader('MI_Shared_'+role);p=n.get('Principled BSDF');p.inputs['Roughness'].default_value=rough;p.inputs['Specular IOR Level'].default_value=spec;p.inputs['Metallic'].default_value=0;p.inputs['IOR'].default_value=1.5
 uv=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Detail'].default_value=4;noise.inputs['Roughness'].default_value=.72
 if role=='ThornBark2m':
  # 4D torus coordinates make both tiling axes periodic without edge blending.
  noise.noise_dimensions='4D';split=n.new('ShaderNodeSeparateXYZ');l.new(uv.outputs['UV'],split.inputs[0]);u=mathnode(n,l,'MULTIPLY',split.outputs['X'],math.tau);v=mathnode(n,l,'MULTIPLY',split.outputs['Y'],math.tau);combine=n.new('ShaderNodeCombineXYZ');l.new(mathnode(n,l,'MULTIPLY',mathnode(n,l,'COSINE',u),120/math.tau),combine.inputs['X']);l.new(mathnode(n,l,'MULTIPLY',mathnode(n,l,'SINE',u),120/math.tau),combine.inputs['Y']);l.new(mathnode(n,l,'MULTIPLY',mathnode(n,l,'COSINE',v),10/math.tau),combine.inputs['Z']);l.new(combine.outputs[0],noise.inputs['Vector']);l.new(mathnode(n,l,'MULTIPLY',mathnode(n,l,'SINE',v),10/math.tau),noise.inputs['W']);noise.inputs['Scale'].default_value=1
 else:l.new(uv.outputs['UV'],noise.inputs[0]);noise.inputs['Scale'].default_value=7;p.inputs['Subsurface Weight'].default_value=.055
 ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.012,.009,.004,1) if size==2 else (.004,.012,.002,1);ramp.color_ramp.elements[1].color=(.085,.060,.028,1) if size==2 else (.027,.067,.008,1);l.new(noise.outputs['Fac'],ramp.inputs[0]);color=ramp.outputs['Color'];height=noise.outputs['Fac']
 if size!=2:
  sep=n.new('ShaderNodeSeparateXYZ');l.new(uv.outputs['UV'],sep.inputs[0]);x=mathnode(n,l,'SUBTRACT',sep.outputs['X'],.5);ax=mathnode(n,l,'ABSOLUTE',x);mid=mathnode(n,l,'LESS_THAN',ax,.010);y=mathnode(n,l,'MULTIPLY',sep.outputs['Y'],7);phase=mathnode(n,l,'FRACT',mathnode(n,l,'SUBTRACT',y,mathnode(n,l,'MULTIPLY',ax,3)));veins=mathnode(n,l,'LESS_THAN',phase,.043);height=mathnode(n,l,'MAXIMUM',mid,veins);mix=n.new('ShaderNodeMixRGB');l.new(height,mix.inputs[0]);l.new(color,mix.inputs[1]);mix.inputs[2].default_value=(.034,.066,.008,1);color=mix.outputs[0]
 roughval=mathnode(n,l,'ADD',mathnode(n,l,'MULTIPLY',noise.outputs['Fac'],.14),rough-.07);l.new(color,p.inputs['Base Color']);l.new(roughval,p.inputs['Roughness']);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.35 if size==2 else .22;b.inputs['Distance'].default_value=.0007 if size==2 else .00016;l.new(height,b.inputs['Height']);l.new(b.outputs[0],p.inputs['Normal'])
 bpy.ops.mesh.primitive_plane_add(size=size);ob=bpy.context.object;ob.name='QA_Bake_'+role;ob.data.materials.append(m)
 roles[role]={'material':m,'object':ob,'size':size,'color':color,'rough':roughval,'p':p,'n':n,'l':l,'spec':spec,'height':height}
# Source shaders retain named procedural graphs, editable physical bake coupons.
bpy.ops.wm.save_as_mainfile(filepath=str(P/'SharedThornBroadleaf_ProceduralSource.blend'))
records={}
for role,d in roles.items():
 ob=d['object'];bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;ob.hide_render=False
 n=d['n'];l=d['l'];out=n.get('Material Output');p=d['p'];images={}
 for kind in ['BC','N_GL','ORM']:
  image=bpy.data.images.new('T_Shared_'+role+'_'+kind,width=1024,height=1024,alpha=False);image.colorspace_settings.name='sRGB' if kind=='BC' else 'Non-Color';target=n.new('ShaderNodeTexImage');target.name='BAKE_TARGET_'+kind;target.image=image
  for node in n:node.select=False
  target.select=True;n.active=target
  if kind=='N_GL':
   l.new(p.outputs['BSDF'],out.inputs['Surface']);bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',normal_r='POS_X',normal_g='POS_Y',normal_b='POS_Z')
  else:
   emission=n.new('ShaderNodeEmission')
   if kind=='BC':l.new(d['color'],emission.inputs['Color'])
   else:
    combine=n.new('ShaderNodeCombineColor');combine.mode='RGB';combine.inputs['Red'].default_value=1;combine.inputs['Blue'].default_value=0;l.new(d['rough'],combine.inputs['Green']);l.new(combine.outputs[0],emission.inputs['Color'])
   l.new(emission.outputs[0],out.inputs['Surface']);bpy.ops.object.bake(type='EMIT')
  path=P/'Textures'/('T_Shared_'+role+'_'+kind+'.png');image.filepath_raw=str(path);image.file_format='PNG';image.save();images[kind]=image;print('BAKED',role,kind,flush=True)
 l.new(p.outputs['BSDF'],out.inputs['Surface'])
 # Separate texture-backed shared role, same physical optical settings; packed maps.
 lib,nn,ll=shader('MI_Shared_'+role+'_Baked');pp=nn.get('Principled BSDF');pp.inputs['IOR'].default_value=1.5;pp.inputs['Specular IOR Level'].default_value=d['spec'];pp.inputs['Subsurface Weight'].default_value=.055 if role=='BroadleafTrimV1' else 0
 texnodes={}
 for kind,img in images.items():
  node=nn.new('ShaderNodeTexImage');node.image=img;node.extension='REPEAT' if role=='ThornBark2m' else 'EXTEND';texnodes[kind]=node;img.pack();img.filepath='//Textures/'+Path(img.filepath).name
 ll.new(texnodes['BC'].outputs['Color'],pp.inputs['Base Color']);sep=nn.new('ShaderNodeSeparateColor');sep.mode='RGB';ll.new(texnodes['ORM'].outputs['Color'],sep.inputs[0]);ll.new(sep.outputs['Green'],pp.inputs['Roughness']);ll.new(sep.outputs['Blue'],pp.inputs['Metallic']);normal=nn.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=1;ll.new(texnodes['N_GL'].outputs['Color'],normal.inputs['Color']);ll.new(normal.outputs['Normal'],pp.inputs['Normal']);ob.data.materials.clear();ob.data.materials.append(lib)
 records[role]={'material':'MI_Shared_'+role,'repeat_m':2 if role=='ThornBark2m' else None,'trim_dimensions_m':[.12,.12] if role=='BroadleafTrimV1' else None,'IOR':1.5,'specular_IOR_level':d['spec'],'dielectric_F0':.04*d['spec']/.5,'unreal_specular':d['spec'],'normal_orientation':'OpenGL +Y','native_flip_green':True,'source_authored_not_measured':True,'textures':{('N' if kind=='N_GL' else kind):{'file':'Textures/'+Path(img.filepath).name,'sha256':hashlib.sha256((P/'Textures'/Path(img.filepath).name).read_bytes()).hexdigest(),'size':[1024,1024],'srgb':kind=='BC'} for kind,img in images.items()}}
# Keep real canonical library material names. Remove old procedural copies from this baked scene.
for role,d in roles.items():
 original=d['material'];baked=bpy.data.materials['MI_Shared_'+role+'_Baked'];original.name='SOURCE_'+original.name;baked.name='MI_Shared_'+role
bpy.ops.wm.save_as_mainfile(filepath=str(P/'SharedThornBroadleaf_LibraryCandidate.blend'))
(P/'registry_candidate.json').write_text(json.dumps(records,indent=2))
print('LIBRARY_BAKES_COMPLETE',flush=True);os._exit(0)
