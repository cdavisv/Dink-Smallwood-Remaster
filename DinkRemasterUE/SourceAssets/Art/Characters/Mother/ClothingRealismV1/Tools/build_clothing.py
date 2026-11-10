"""Blender5.2 source-only Mother clothing successor. No original source/import files are overwritten.
CPU invocation: taskset -c 2 nice -n 12 blender -b -t 1 --python Tools/build_clothing.py
Authoring uses original unique UVs, topology, skin weights and all89 rest bones.
"""
import bpy,math,json,hashlib,sys,struct
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parents[1];ART=HERE.parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Mother.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1;scene.render.threads_mode='FIXED';scene.render.threads=1
arm=bpy.data.objects['Armature'];arm.data.pose_position='REST';meshes=[bpy.data.objects['SK_Mother_LOD%d'%i]for i in range(4)]

def digest(values):return hashlib.sha256(json.dumps(values,separators=(',',':')).encode()).hexdigest()
def snapshot():
 wardrobe={o.name:{i for p in o.data.polygons if p.material_index==4 for i in p.vertices}for o in meshes}
 return {'rig':digest([(b.name,b.parent.name if b.parent else None,[list(r)for r in b.matrix_local])for b in arm.data.bones]),'meshes':{o.name:{'topology':digest([list(p.vertices)for p in o.data.polygons]),'uv':digest([[list(v.uv)for v in u.data]for u in o.data.uv_layers]),'weights':digest([[(g.group,g.weight)for g in v.groups]for v in o.data.vertices]),'nonwardrobe':digest([(v.index,list(v.co))for v in o.data.vertices if v.index not in wardrobe[o.name]]),'materials':[s.material.name for s in o.material_slots],'triangles':sum(len(p.vertices)-2 for p in o.data.polygons)}for o in meshes}}
before=snapshot();changes=[]
for o in meshes:
 me=o.data;vs={i for p in me.polygons if p.material_index==4 for i in p.vertices};adj={i:set()for i in vs}
 for p in me.polygons:
  if p.material_index==4:
   for i in p.vertices:adj[i].update(p.vertices)
 original={i:me.vertices[i].co.copy()for i in vs};changed=0;maximum=0
 for i in vs:
  v=me.vertices[i];x,y,z=original[i];delta=Vector()
  # Ease fitted chest into a sewn panel rather than anatomy-tight rubber.
  if .99<z<1.55 and abs(x)<.22 and y<-.035:
   w=max(0,1-abs(x)/.22)*math.sin(math.pi*max(0,min(1,(z-1.10)/.42)))**2
   target=-.154+.48*x*x
   delta.y+=min(0,target-y)*w
  # Millimetre-scale drape, strongest below waist; endpoints stay supported.
  if .24<z<1.0:
   amount=.0018*math.sin(math.pi*(z-.24)/.76)**2
   delta+=v.normal*amount*math.sin(x*43+z*11)*math.sin(z*23+y*9)
  # Take angular fold peaks down gently, normal-only; UVs/indices/weights stay exact.
  if .20<z<.46 and len(adj[i])>2:
   average=sum((original[j]for j in adj[i]),Vector())/len(adj[i]);d=(average-original[i]).dot(v.normal)
   delta+=v.normal*max(-.007,min(.007,d*.55))*math.sin(math.pi*(z-.20)/.26)
  if delta.length>1e-9:v.co+=delta;changed+=1;maximum=max(maximum,delta.length)
 # Thin inherited cloth has closely spaced inner/outer fold faces. Backtrack
 # ONLY local proposed cloth moves that reverse an original triangle or collapse it.
 import numpy as np
 tri=[]
 for face in me.polygons:
  if face.material_index==4:
   for k in range(1,len(face.vertices)-1):tri.append((face.vertices[0],face.vertices[k],face.vertices[k+1]))
 t=np.asarray(tri);base=np.asarray([tuple(v.co)for v in me.vertices])
 for i,co in original.items():base[i]=co
 normal0=np.cross(base[t[:,1]]-base[t[:,0]],base[t[:,2]]-base[t[:,0]]);area0=np.linalg.norm(normal0,axis=1);backtracked=set()
 for attempt in range(40):
  actual=np.asarray([tuple(v.co)for v in me.vertices]);n=np.cross(actual[t[:,1]]-actual[t[:,0]],actual[t[:,2]]-actual[t[:,0]]);bad=(area0>1e-12)&((np.sum(normal0*n,axis=1)<0)|(np.linalg.norm(n,axis=1)<=1e-12))
  if not bad.any():break
  for i in set(t[bad].ravel().tolist()):
   backtracked.add(i);me.vertices[i].co=original[i]+(me.vertices[i].co-original[i])*.5
 else:raise RuntimeError('Clothing fold winding could not be preserved')
 changed=sum((me.vertices[i].co-original[i]).length>1e-9 for i in vs);maximum=max((me.vertices[i].co-original[i]).length for i in vs)
 me.update();changes.append({'mesh':o.name,'changed_clothing_vertices':changed,'max_displacement_m':maximum,'locally_backtracked_fold_vertices':len(backtracked)})
# Only the wardrobe material is replaced; skin/eyes/hair/brows keep original image bytes and shader graphs.
m=meshes[0].data.materials[4];m=m.copy();m.name='MI_Mother_ClothingRealismV1';nodes=m.node_tree.nodes;links=m.node_tree.links
bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');bc=next(n for n in nodes if n.type=='TEX_IMAGE'and n.image.name=='T_Mother_Atlas_BC')
normal=next(n for n in nodes if n.type=='NORMAL_MAP');oldnormal=normal.outputs['Normal'];oldrough=bs.inputs['Roughness'].links[0].from_socket
def node(kind,name):n=nodes.new(kind);n.label=name;n.name=name;return n
def mathn(op,a,b=None,name=''):
 n=node('ShaderNodeMath',name or op);n.operation=op
 for i,v in enumerate([a,b]if b is not None else[a]):
  if hasattr(v,'node'):links.new(v,n.inputs[i])
  else:n.inputs[i].default_value=v
 return n.outputs[0]
def mix(a,b,f,name):
 n=node('ShaderNodeMixRGB',name);n.blend_type='MIX';links.new(f,n.inputs[0])if hasattr(f,'node')else setattr(n.inputs[0],'default_value',f)
 for i,v in [(1,a),(2,b)]:
  if hasattr(v,'node'):links.new(v,n.inputs[i])
  else:n.inputs[i].default_value=v
 return n.outputs[0]
g=node('ShaderNodeNewGeometry','Metre-scale cloth coordinates');sep=node('ShaderNodeSeparateXYZ','Cloth position');links.new(g.outputs['Position'],sep.inputs[0]);colors=node('ShaderNodeSeparateColor','Existing cream-versus-red dye');links.new(bc.outputs['Color'],colors.inputs[0])
cream=mathn('GREATER_THAN',mathn('DIVIDE',colors.outputs['Green'],mathn('MAXIMUM',colors.outputs['Red'],.001)),.65)
garmentmask=mathn('GREATER_THAN',colors.outputs['Red'],.09);cream=mathn('MULTIPLY',cream,garmentmask)
noise=node('ShaderNodeTexNoise','Hand-spun yarn irregularity');links.new(g.outputs['Position'],noise.inputs['Vector']);noise.inputs['Scale'].default_value=65;noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.7
fiber=node('ShaderNodeTexNoise','Wool staple fibres');links.new(g.outputs['Position'],fiber.inputs['Vector']);fiber.inputs['Scale'].default_value=1500;fiber.inputs['Detail'].default_value=2
warp=node('ShaderNodeTexWave','Coarse homespun warp');warp.wave_type='BANDS';warp.bands_direction='X';warp.inputs['Scale'].default_value=170;warp.inputs['Distortion'].default_value=1.2;warp.inputs['Detail Scale'].default_value=.9;links.new(g.outputs['Position'],warp.inputs['Vector'])
weft=node('ShaderNodeTexWave','Coarse homespun weft');weft.wave_type='BANDS';weft.bands_direction='Z';weft.inputs['Scale'].default_value=145;weft.inputs['Distortion'].default_value=.9;links.new(g.outputs['Position'],weft.inputs['Vector'])
weave=mathn('MULTIPLY',warp.outputs['Fac'],weft.outputs['Fac']);woolweave=mathn('ADD',mathn('MULTIPLY',weave,.72),mathn('MULTIPLY',fiber.outputs['Fac'],.28));height=mix(woolweave,weave,cream,'Wool nap / linen interlace')
# Sewn centre-front bodice seam; narrow raised double stitch rather than a painted broad stripe.
xabs=mathn('ABSOLUTE',sep.outputs['X']);line=mathn('LESS_THAN',mathn('ABSOLUTE',mathn('SUBTRACT',xabs,.0024)),.00055)
window=mathn('MULTIPLY',mathn('GREATER_THAN',sep.outputs['Z'],1.08),mathn('LESS_THAN',sep.outputs['Z'],1.53));window=mathn('MULTIPLY',window,mathn('LESS_THAN',sep.outputs['Y'],-.04));stitches=mathn('GREATER_THAN',mathn('SINE',mathn('MULTIPLY',sep.outputs['Z'],2100)),.1);seam=mathn('MULTIPLY',mathn('MULTIPLY',line,window),stitches)
clothcolor=mix(bc.outputs['Color'],(.55,.46,.32,1),mathn('MULTIPLY',cream,.20),'Warm undyed flax keeps original cream identity')
variation=node('ShaderNodeMixRGB','Subtle yarn dye variation');variation.blend_type='MULTIPLY';variation.inputs[0].default_value=.24;links.new(clothcolor,variation.inputs[1]);links.new(noise.outputs['Fac'],variation.inputs[2]);dye=node('ShaderNodeMixRGB','Retain deep madder-red wool');dye.blend_type='MULTIPLY';dye.inputs[0].default_value=1;links.new(variation.outputs[0],dye.inputs[1]);dye.inputs[2].default_value=(.74,.54,.48,1);dyed=mix(dye.outputs[0],variation.outputs[0],cream,'Distinct wool and undyed linen');stitched=mix(dyed,(.24,.085,.045,1),mathn('MULTIPLY',seam,.45),'Madder dyed sewing thread');links.new(mix(bc.outputs['Color'],stitched,garmentmask,'Preserve original leather footwear'),bs.inputs['Base Color'])
rough=mix((.91,.91,.91,1),(.82,.82,.82,1),cream,'Measured dielectric wool/linen roughness');links.new(mix(oldrough,rough,garmentmask,'Retain footwear roughness'),bs.inputs['Roughness']);bs.inputs['Metallic'].default_value=0;bs.inputs['Specular IOR Level'].default_value=.28;links.new(mathn('MULTIPLY',garmentmask,.075),bs.inputs['Sheen Weight']);bs.inputs['Sheen Roughness'].default_value=.78
bump=node('ShaderNodeBump','Submillimetre yarn relief');bump.inputs['Distance'].default_value=.00065;bump.inputs['Strength'].default_value=.65;links.new(height,bump.inputs['Height']);links.new(oldnormal,bump.inputs['Normal'])
sewbump=node('ShaderNodeBump','Fine sewn centre panel');sewbump.inputs['Distance'].default_value=.00045;sewbump.inputs['Strength'].default_value=.5;links.new(seam,sewbump.inputs['Height']);links.new(bump.outputs['Normal'],sewbump.inputs['Normal']);links.new(mix(oldnormal,sewbump.outputs['Normal'],garmentmask,'Retain footwear normal'),bs.inputs['Normal'])
for o in meshes:o.data.materials[4]=m
# Save editable packed procedural master before making runtime atlases in a process-only copy.
for im in bpy.data.images:
 if im.source=='FILE'and im.size[0]:im.pack()
after=snapshot()
for name in before['meshes']:
 for k in ['topology','uv','weights','nonwardrobe','triangles']:assert before['meshes'][name][k]==after['meshes'][name][k],(name,k)
assert before['rig']==after['rig']
report={'schema':'dink-mother-clothing-source/1','baseline':'../../SK_Mother.blend','baseline_sha256':hashlib.sha256((ART/'SK_Mother.blend').read_bytes()).hexdigest(),'rig_bones':len(arm.data.bones),'before':before,'after':after,'changes':changes,'scope':'Only existing wardrobe vertex positions and wardrobe shader; original topology/UV/weights/nonwardrobe geometry and89 rest bones exact. New textile material source requires atlas bake and native animation/performance gates before activation.'}
(HERE/'source_scope.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'SK_Mother_ClothingRealismV1.blend'))
print('CLOTHING SOURCE COMPLETE',changes,flush=True)
