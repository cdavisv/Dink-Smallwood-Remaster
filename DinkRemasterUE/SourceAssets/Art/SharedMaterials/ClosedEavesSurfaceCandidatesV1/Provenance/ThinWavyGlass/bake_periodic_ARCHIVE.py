"""Bake authored seamless UV glass derivative; no cottage or native mutation."""
import bpy,json,hashlib
from pathlib import Path
from array import array
D=Path(__file__).resolve().parents[1];T=D/'PeriodicMaps';T.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(D/'Provenance/ThinWavyGlass2m_Source.blend'))
m=bpy.data.materials['MI_Candidate_ThinWavyGlass2m'];n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');out=n.get('Material Output');uv=n.get('UV Map');scale=n.get('Vector Math');sep=n.new('ShaderNodeSeparateXYZ');l.new(uv.outputs[0],sep.inputs[0]);weights=[]
for axis in ['X','Y']:
 r=n.new('ShaderNodeMapRange');r.interpolation_type='SMOOTHSTEP';r.clamp=True;l.new(sep.outputs[axis],r.inputs['Value']);weights.append(r.outputs[0])
def periodic_noise(freq):
 samples=[]
 for x,y in [(0,0),(-2,0),(0,-2),(-2,-2)]:
  offset=n.new('ShaderNodeVectorMath');offset.operation='ADD';offset.inputs[1].default_value=(x,y,0);l.new(scale.outputs[0],offset.inputs[0]);noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=freq;noise.inputs['Detail'].default_value=2;l.new(offset.outputs[0],noise.inputs['Vector']);samples.append(noise.outputs['Fac'])
 def mix(a,b,w):
  node=n.new('ShaderNodeMixRGB');node.blend_type='MIX';l.new(w,node.inputs[0]);l.new(a,node.inputs[1]);l.new(b,node.inputs[2]);return node.outputs[0]
 return mix(mix(samples[0],samples[1],weights[0]),mix(samples[2],samples[3],weights[0]),weights[1])
l.new(periodic_noise(65),n.get('Math').inputs[0]);l.new(periodic_noise(12),n.get('Bump').inputs['Height'])
for name in ['Noise Texture','Noise Texture.001']:n.remove(n[name])
bpy.ops.mesh.primitive_plane_add(size=2);obj=bpy.context.object;obj.name='Generic2mBakePlane';obj.data.uv_layers[0].name='UV0';obj.data.materials.append(m)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=8;s.render.threads_mode='FIXED';s.render.threads=2;s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0;s.view_settings.gamma=1;s.render.bake.margin=0;s.render.bake.use_clear=True
active=n.new('ShaderNodeTexImage');active.name='BakeTarget'
def target(role):
 im=bpy.data.images.new('T_Candidate_ThinGlass2m_'+role,width=1024,height=1024,float_buffer=True);im.colorspace_settings.name='Non-Color';active.image=im
 for node in n:node.select=False
 active.select=True;n.active=active;return im
def save(im,role):
 s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='16';im.save_render(str(T/('T_Candidate_ThinGlass2m_'+role+'.png')),scene=s)
p.inputs['Transmission Weight'].default_value=0;p.inputs['Thin Wall'].default_value=0
normal=target('N_GL');bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT');save(normal,'N_GL')
p.inputs['Transmission Weight'].default_value=1;p.inputs['Thin Wall'].default_value=1
em=n.new('ShaderNodeEmission');combine=n.new('ShaderNodeCombineColor');combine.inputs[0].default_value=1;combine.inputs[2].default_value=0;l.new(n.get('Math.001').outputs[0],combine.inputs[1]);l.new(combine.outputs[0],em.inputs[0]);l.new(em.outputs[0],out.inputs['Surface']);orm=target('ORM');bpy.ops.object.bake(type='EMIT');save(orm,'ORM')
em.inputs[0].default_value=(.96,.985,.97,1)
for link in list(em.inputs[0].links):l.remove(link)
bc=target('BC');bc.colorspace_settings.name='sRGB';bpy.ops.object.bake(type='EMIT');save(bc,'BC');l.new(p.outputs[0],out.inputs['Surface']);n.remove(active);n.remove(em);n.remove(combine)
# Preserve exact periodic procedural graph independently of map consumer.
bpy.data.objects.remove(obj,do_unlink=True);bpy.ops.wm.save_as_mainfile(filepath=str(D/'ThinWavyGlass2m_PeriodicProcedural.blend'),compress=True)
# Pixel map consumer; procedural source stays in its own immutable study artifact.
bpy.ops.wm.read_factory_settings(use_empty=True);m=bpy.data.materials.new('MI_Candidate_ThinWavyGlass2m_Baked');m.use_nodes=True;m.use_fake_user=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');p.inputs['Transmission Weight'].default_value=1;p.inputs['Thin Wall'].default_value=1;p.inputs['IOR'].default_value=1.48
for role in ['BC','N_GL','ORM']:
 im=bpy.data.images.load(str(T/('T_Candidate_ThinGlass2m_'+role+'.png')));im.colorspace_settings.name='sRGB'if role=='BC'else'Non-Color';im.pack();node=n.new('ShaderNodeTexImage');node.image=im;node.extension='REPEAT'
 if role=='BC':l.new(node.outputs['Color'],p.inputs['Base Color'])
 elif role=='N_GL':
  norm=n.new('ShaderNodeNormalMap');norm.uv_map='UV0';l.new(node.outputs['Color'],norm.inputs['Color']);l.new(norm.outputs[0],p.inputs['Normal'])
 else:
  sep=n.new('ShaderNodeSeparateColor');l.new(node.outputs['Color'],sep.inputs[0]);l.new(sep.outputs[1],p.inputs['Roughness']);l.new(sep.outputs[2],p.inputs['Metallic'])
bpy.ops.wm.save_as_mainfile(filepath=str(D/'ThinWavyGlass2m_BakedSource.blend'),compress=True)
(D/'PERIODIC_BAKE.json').write_text(json.dumps({'status':'BAKE_COMPLETE_PIXEL_AND_RENDER_REVIEW_PENDING','map_size':[1024,1024],'repeat_m':2,'normal_orientation':'OpenGL +Y tangent','normal_strength':1,'recipe':'Four 2m-offset Noise samples, smoothstep UV blends; matched value and first derivative at repeat boundaries','roughness_range_nominal':[.06,.115],'IOR':1.48,'transmission':1,'thin_wall':True,'BC_interpretation':'Authored near-clear tint, not measured transmittance','textures':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in T.glob('*.png')},'qualification':'Periodic derivative alters prior world-space noise correlation. No cottage/native mutation or appearance approval.'},indent=2)+'\n')
