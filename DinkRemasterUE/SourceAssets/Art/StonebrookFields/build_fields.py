"""Original source-fitted terrain + true3D conifer; Blender5.2 background.
Run after prepare_fields.py. Only StonebrookFields files are written.
"""
import bpy,bmesh,json,math,random,sys
from pathlib import Path
from mathutils import Vector
from types import SimpleNamespace
ART=Path(__file__).resolve().parent;ROOT=ART.parents[2]
sys.path.insert(0,str(ROOT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import common,conventions as C,export_ue,validate,fbxparse
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/Art/StonebrookExterior/KIT_StonebrookExterior.blend'))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):bpy.data.collections.remove(c)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.view_settings.view_transform='AgX'
ASSETS={};MATS={}
ext=json.loads((ROOT/'SourceAssets/Art/StonebrookExterior/exterior_manifest.json').read_text())
for name in ['MI_Stonebrook_Meadow','MI_Stonebrook_Earth','MI_Stonebrook_Oak','MI_Stonebrook_OakLeaf']:
 spec=json.loads(json.dumps(ext['materials'][name]))
 for k,v in spec.get('textures',{}).items():spec['textures'][k]='../StonebrookExterior/'+v
 MATS[name]=spec
water=bpy.data.materials.new('MI_Fields_StreamWater');water.use_nodes=True
bs=water.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.014,.065,.075,1);bs.inputs['Roughness'].default_value=.19
bs.inputs['IOR'].default_value=1.333
# Tiny normal ripples, opaque depth colour: no transparent sorting or physical sheet.
nodes=water.node_tree.nodes;links=water.node_tree.links
tex=nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=7;tex.inputs['Detail'].default_value=3;tex.inputs['Roughness'].default_value=.55
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.035
links.new(tex.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
MATS[water.name]={'name':water.name,'base_color':[.014,.065,.075],'roughness':.19,'metallic':0,'normal_strength':.12,'uv_pan_speed':[.006,.001],'note':'Opaque source water. Runtime collision disabled. Normal texture baked below.'}
# Bake original deterministic ripple texture explicitly for the existing PBR importer.
import numpy as np
td=ART/'Textures';td.mkdir(exist_ok=True)
n=256;yy,xx=np.mgrid[0:n,0:n]/n
h=.4*np.sin(xx*2*math.pi*9+np.sin(yy*2*math.pi*3))+.2*np.sin((xx+yy)*2*math.pi*17)
dx,dy=np.gradient(h);normal=np.dstack((-dx*1.2,-dy*1.2,np.ones_like(h)));normal/=np.linalg.norm(normal,axis=2)[:,:,None]
arrays={'BC':np.broadcast_to(np.array([.014,.065,.075]),(n,n,3)), 'N':normal*.5+.5,'ORM':np.broadcast_to(np.array([1,.19,0]),(n,n,3))}
for suffix,arr in arrays.items():
 im=bpy.data.images.new('T_Fields_StreamWater_'+suffix,width=n,height=n,alpha=True)
 im.colorspace_settings.name='sRGB' if suffix=='BC' else 'Non-Color'
 rgba=np.ones((n,n,4),np.float32);rgba[:,:,:3]=arr;im.pixels.foreach_set(rgba.ravel())
 im.filepath_raw=str(td/(im.name+'.png'));im.file_format='PNG';im.save()
 MATS[water.name].setdefault('textures',{})[suffix]='Textures/'+im.name+'.png'
MATS[water.name]['normal_flip_green']=True
def collection(name,cls):
 c=bpy.data.collections.new(name);scene.collection.children.link(c)
 c['dink_class']=cls;c['dink_path']='StonebrookFields';c['dink_source']='Original deterministic geometry; source screen contours + build_fields.py; existing project PBR sources; no external assets'
 return c
def mesh(c,name,verts,faces,materials,indices=None,uv_origin=None):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.materials.clear()
 for m in materials:me.materials.append(m)
 ob=bpy.data.objects.new(name,me);c.objects.link(ob)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 if indices:
  for p,i in zip(me.polygons,indices):p.material_index=i
 uv=me.uv_layers.new(name='UVMap')
 for poly in me.polygons:
  for li in poly.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co
   axis=max(range(3),key=lambda i:abs(poly.normal[i]));axes=[i for i in range(3) if i!=axis]
   uv.data[li].uv=((v[axes[0]]+(uv_origin[axes[0]] if uv_origin else 0))/2,(v[axes[1]]+(uv_origin[axes[1]] if uv_origin else 0))/2)
 return ob
def register(c,ob):
 coords=[v.co for v in ob.data.vertices];lo=[min(v[i] for v in coords) for i in range(3)];hi=[max(v[i] for v in coords) for i in range(3)]
 ASSETS[c.name]={'class':c['dink_class'],'dimensions_m':[hi[i]-lo[i] for i in range(3)],'bounds_min_m':lo,'bounds_max_m':hi,
 'materials':[s.material.name for s in ob.material_slots],'blend_collection':c.name,'expected_lods':3 if c['dink_class']=='foliage' else 1,
 'fbx':'Export/'+C.content_path(c['dink_class'],c.name,'StonebrookFields').lstrip('/')+'.fbx'}
for sid in [471,438]:
 data=json.loads((ART/f'geometry_{sid}.json').read_text())
 for chunk in data['chunks']:
  name=chunk['name'];role=chunk['role'];c=collection(name,'kit_floor');verts=[];faces=[];lookup={}
  def index(v):
   q=tuple(round(x,6) for x in v)
   if q not in lookup:lookup[q]=len(verts);verts.append(q)
   return lookup[q]
  for tri in chunk['triangles']:faces.append(tuple(index(v) for v in tri))
  top_count=len(faces)
  # Triangle boundaries only become walls; shared internal edges stay welded.
  counts={}
  for f in faces:
   for a,b in zip(f,f[1:]+f[:1]):
    key=tuple(sorted((a,b)));counts[key]=counts.get(key,0)+1
  depth=.13;bottom={}
  def lower(i):
   if i not in bottom:bottom[i]=len(verts);x,y,z=verts[i];verts.append((x,y,z-depth))
   return bottom[i]
  original=list(faces)
  for a,b in [edge for edge,count in counts.items() if count==1]:faces.append((a,b,lower(b),lower(a)))
  for f in original:faces.append(tuple(lower(i) for i in reversed(f)))
  mat=bpy.data.materials['MI_Stonebrook_Meadow' if role=='Land' else 'MI_Stonebrook_Earth'] if role!='Water' else water
  ob=mesh(c,name,verts,faces,[mat],uv_origin=(chunk['anchor_world_m'][0],-chunk['anchor_world_m'][1],chunk['height_m']));register(c,ob)
  ASSETS[name]['role']=role
  # Triangular prisms preserve concavities/holes; never a box across water.
  # Bank hulls satisfy kit_floor source policy but runtime bank collision is OFF.
  if role!='Water':
   for j,tri in enumerate(chunk['triangles'],1):
    vv=[tuple(v) for v in tri]+[(v[0],v[1],v[2]-depth) for v in tri]
    hull=mesh(c,f'UCX_{name}_{j:02}',vv,[(0,1,2),(5,4,3),(0,3,4,1),(1,4,5,2),(2,5,3,0)],[])
    hull.hide_render=True;hull.display_type='WIRE'
# Three independently modelled conifer LODs. Solid needle-bearing twigs, no flat alpha cards.
name='SM_Pine_Stonebrook_01';c=collection(name,'foliage');c['dink_nanite']='no'
for lod,(levels,branches,clumps,sides) in enumerate([(16,7,5,6),(11,6,4,4),(7,5,3,3)]):
 rng=random.Random(471+lod);vv=[];ff=[];mi=[]
 def tube(a,b,ra,rb,mat=0,ns=8):
  a,b=Vector(a),Vector(b);direction=(b-a).normalized();u=direction.cross(Vector((0,1,0))).normalized();v=direction.cross(u).normalized();start=len(vv)
  for p,r in [(a,ra),(b,rb)]:
   for i in range(ns):vv.append(tuple(p+r*(math.cos(i*2*math.pi/ns)*u+math.sin(i*2*math.pi/ns)*v)))
  ff.append(tuple(start+i for i in reversed(range(ns))));mi.append(mat)
  ff.append(tuple(start+ns+i for i in range(ns)));mi.append(mat)
  for i in range(ns):ff.append((start+i,start+(i+1)%ns,start+ns+(i+1)%ns,start+ns+i));mi.append(mat)
 def needle_bough(center,length,width,heading):
  # Individually modelled tapering needles arranged around a short green twig.
  # Each needle is a closed four-face tetrahedral blade, not an alpha card or leaf lump.
  axis=Vector((math.cos(heading),math.sin(heading),.16)).normalized();cross=Vector((-math.sin(heading),math.cos(heading),0));origin=Vector(center)
  # Dense opaque needle-bearing branchlet core. Narrow, pointed and irregular;
  # the individually modelled needles break its edge silhouette at close range.
  base=len(vv);vv.append(tuple(origin-axis*length*.55))
  for k in range(6):
   a=k*2*math.pi/6;radius=width*rng.uniform(.65,.95)
   vv.append(tuple(origin+cross*math.cos(a)*radius+Vector((0,0,1))*math.sin(a)*radius*.72))
  vv.append(tuple(origin+axis*length*.58))
  for k in range(6):
   ff.extend([(base,base+1+k,base+1+(k+1)%6),(base+7,base+1+(k+1)%6,base+1+k)]);mi.extend([1,1])
  for j in range(sides):
   f=(j+.5)/sides;side=-1 if j%2 else 1
   p=origin+axis*(f-.5)*length
   direction=(axis*.45+cross*side*.85+Vector((0,0,rng.uniform(-.12,.38)))).normalized()
   needle_length=(.20+.16*(1-abs(f-.5)*2))*(.65+length)
   thickness=.009+needle_length*.025
   tangent=direction.cross(Vector((0,0,1))).normalized();normal=direction.cross(tangent).normalized();base=len(vv)
   vv.extend([tuple(p-tangent*thickness),tuple(p+tangent*thickness),tuple(p+normal*thickness),tuple(p+direction*needle_length)])
   ff.extend([(base,base+1,base+2),(base,base+3,base+1),(base+1,base+3,base+2),(base+2,base+3,base)]);mi.extend([1]*4)
 tube((0,0,0),(0,0,13),.27,.035,ns=12 if lod==0 else 8)
 for row in range(levels):
  t=row/(levels-1);z=1.8+t*10.8+rng.uniform(-.18,.18);radius=2.55*(1-t)**.85+.12
  for b in range(branches):
   a=b*2*math.pi/branches+row*1.37+rng.uniform(-.09,.09);r=radius*rng.uniform(.85,1.08)
   tip=(math.cos(a)*r,math.sin(a)*r,z-.7*(1-t)+rng.uniform(-.13,.13))
   tube((0,0,z+.12),tip,.047*(1-t)+.008,.007,ns=6 if lod==0 else 4)
   for k in range(clumps):
    f=(k+.7)/clumps;center=(tip[0]*f,tip[1]*f,z+.12+(tip[2]-z-.12)*f+.08*math.sin(f*math.pi))
    needle_bough(center,.65*(1-t)+.22,.20*(1-t)+.05,a+rng.uniform(-.35,.35))
 ob=mesh(c,name+'_LOD'+str(lod),vv,ff,[bpy.data.materials['MI_Stonebrook_Oak'],bpy.data.materials['MI_Stonebrook_OakLeaf']],mi)
 for p in ob.data.polygons:p.use_smooth=True
 if lod==0:
  # Ground-centred pivot, not crown-centred, shared across all LODs.
  coords=[v.co for v in ob.data.vertices];shift=Vector(((min(v.x for v in coords)+max(v.x for v in coords))/2,(min(v.y for v in coords)+max(v.y for v in coords))/2,0))
 for vertex in ob.data.vertices:vertex.co-=shift
 if lod==0:register(c,ob)
# Pine collision is the visible lower trunk only. Offscreen source471 tree elements disable it.
vv=[(.23*math.cos(i*2*math.pi/10),.23*math.sin(i*2*math.pi/10),z) for z in [0,2] for i in range(10)]
faces=[tuple(reversed(range(10))),tuple(range(10,20))]+[(i,(i+1)%10,(i+1)%10+10,i+10) for i in range(10)]
co=mesh(c,'UCX_'+name+'_LOD0_01',vv,faces,[]);co.hide_render=True;co.display_type='WIRE'
for v in co.data.vertices:v.co-=shift
pine=[bpy.data.objects[name+'_LOD'+str(i)] for i in range(3)]
lo=[min(v.co[k] for ob in pine for v in ob.data.vertices) for k in range(3)]
hi=[max(v.co[k] for ob in pine for v in ob.data.vertices) for k in range(3)]
ASSETS[name]['lod_union_dimensions_m']=[hi[k]-lo[k] for k in range(3)]
ASSETS[name]['collision_mode']='simple'
ASSETS[name]['trunk_collision_bounds_m']=[[min(v.co[k] for v in co.data.vertices) for k in range(3)],[max(v.co[k] for v in co.data.vertices) for k in range(3)]]
foliage_vertices={i for poly in pine[0].data.polygons if poly.material_index==1 for i in poly.vertices}
ASSETS[name]['lowest_foliage_m']=min(pine[0].data.vertices[i].co.z for i in foliage_vertices)
ASSETS[name]['budget_note']='Needle-bearing opaque boughs and individually modeled needles exceed preferred8k but remain below hard25k foliage budget. Three independent LODs reduce distant cost.'
manifest={'schema':'dink-stonebrook-art/1','source':'KIT_StonebrookFields.blend','units':'metres; FBX UnitScaleFactor100','assets':ASSETS,'materials':MATS,
 'notes':['Source-only candidate. Ground follows original blocked-water envelope. Low+fill_water retained at runtime.',
 'Water assets intentionally carry no collision. kit_floor missing-UCX is a narrowly documented source-policy exception.',
 'Clipped shoreline slivers may be below minimum0.5m; every chunk is ≤6m. No new source class invented.',
 'Bank source UCX are never enabled by the layout; original Low controls projectile/walking semantics.']}
(ART/'art_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'KIT_StonebrookFields.blend'))
result=validate.validate_scene();(ART/'validation_raw.json').write_text(json.dumps(result,indent=2)+'\n')
print('FIELDS BUILT:',len(ASSETS),'assets; raw validation',result['summary'])
