import bpy,math,random,json,hashlib,bmesh
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent; SRC=O/'Inputs/Original_OakFurnitureV1.blend'; rng=random.Random(72026)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SRC));s=bpy.context.scene;s.render.threads_mode='FIXED';s.render.threads=4;s.cycles.samples=32;s.cycles.use_denoising=True
names=['SM_Table_Oak_01','SM_Chair_Oak_01','SM_Bed_Oak_01'];old={n:bpy.data.meshes[n+'_Mesh'] for n in names};instances={n:[ob for ob in s.objects if ob.type=='MESH' and ob.data==old[n]] for n in names}
parts=[];hulls=[];coll=None

def finish(ob,mat,axis=0,bevel=0,collision=False):
 bpy.context.view_layer.objects.active=ob;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 if bevel:
  mod=ob.modifiers.new('Small eased oak edges','BEVEL');mod.width=bevel;mod.segments=4;bpy.ops.object.modifier_apply(modifier=mod.name)
 ob.data.materials.clear();ob.data.materials.append(mat)
 if not collision:
  me=ob.data;me.update();lo=[min(v.co[k] for v in me.vertices) for k in range(3)];hi=[max(v.co[k] for v in me.vertices)for k in range(3)];other=[k for k in range(3)if k!=axis];seed=rng.random()
  for attr in ['OakFurniturePhoto','OakFurniturePhysical','OakFurnitureEnd','OakFurnitureEndMask']:me.attributes.new(attr,'FLOAT' if attr.endswith('Mask')else'FLOAT_VECTOR','CORNER')
  for p in me.polygons:
   across=min(other,key=lambda k:abs(p.normal[k]));mask=max(0,min(1,(abs(p.normal[axis])-.72)/.23))
   for l in p.loop_indices:
    v=me.vertices[me.loops[l].vertex_index].co;cross=v[across]-lo[across];along=v[axis]-lo[axis]
    for attr,val in [('OakFurniturePhoto',(cross+.16*seed,along/2+.17*seed,seed)),('OakFurniturePhysical',(cross,along,seed)),('OakFurnitureEnd',(v[other[0]]-(lo[other[0]]+hi[other[0]])/2+.023,v[other[1]]-(lo[other[1]]+hi[other[1]])/2+.011,0))]:me.attributes[attr].data[l].vector=val
    me.attributes['OakFurnitureEndMask'].data[l].value=mask
  parts.append(ob)
 else:
  ob.name=f'UCX_{asset}_{len(hulls)+1:02d}';ob.hide_render=True;ob.display_type='WIRE';hulls.append(ob)
 return ob

def box(pos,dim,mat,axis=0,bevel=.003,solid=True):
 bpy.ops.mesh.primitive_cube_add(size=1,location=pos);ob=bpy.context.object;ob.dimensions=dim;finish(ob,mat,axis,bevel)
 if solid:
  bpy.ops.mesh.primitive_cube_add(size=1,location=pos);c=bpy.context.object;c.dimensions=dim;finish(c,mat,axis,0,True)
 return ob

def peg(pos,radius=.011,axis=1):
 rot=(math.pi/2,0,0) if axis==1 else ((0,math.pi/2,0)if axis==0 else(0,0,0))
 bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=radius,depth=.004,location=pos,rotation=rot);return finish(bpy.context.object,wood,axis,.0008)

def clothmat(name,col):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Roughness'].default_value=.89;bs.inputs['Sheen Weight'].default_value=.24;bs.inputs['Sheen Roughness'].default_value=.7
 tc=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=650;l.new(tc.outputs['Generated'],scale.inputs[0]);noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1;noise.inputs['Detail'].default_value=2;l.new(scale.outputs[0],noise.inputs[0]);b=n.new('ShaderNodeBump');b.inputs['Distance'].default_value=.00018;b.inputs['Strength'].default_value=.28;l.new(noise.outputs['Fac'],b.inputs['Height']);l.new(b.outputs[0],bs.inputs['Normal']);broad=n.new('ShaderNodeTexNoise');broad.inputs['Scale'].default_value=9;broad.inputs['Detail'].default_value=3;l.new(tc.outputs['Generated'],broad.inputs[0]);ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*[v*.72 for v in col],1);ramp.color_ramp.elements[1].color=(*[v*1.12 for v in col],1);l.new(broad.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],bs.inputs['Base Color']);return m
linen=clothmat('MI_Photoreal_Flax',(.115,.14,.061));pillowmat=clothmat('MI_Photoreal_UndyedLinen',(.48,.43,.31))
report={};candidates={};allhulls={}
for asset in names:
 parts=[];hulls=[];wood=old[asset].materials[0].copy();wood.name='MI_Photo_'+asset[3:];bs=next(n for n in wood.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Specular IOR Level'].default_value=.3
 # Reduce chalky diffuse response; keep the unchanged generated oak image and its tone calibration.
 for n in wood.node_tree.nodes:
  if n.type=='MATH' and n.operation=='ADD' and abs(n.inputs[0].default_value-.76)<1e-5:n.inputs[0].default_value=.61
 if 'Table' in asset:
  for x in [-1.08,1.08]:
   for y in [-.48,.48]:
    box((x,y,.405),(.14,.14,.81),wood,2,.004)
    peg((x,y-.071,.703),.012,1);peg((x,y-.071,.635),.012,1)
  for y in [-.5,.5]:box((0,y,.68),(2.16,.12,.21),wood,0,.004)
  for x in [-1.08,1.08]:box((x,0,.68),(.12,.90,.21),wood,1,.004)
  box((0,0,.24),(2.16,.1,.11),wood,0,.003)
  for i in range(7):
   y=-.645+i*.215;z=.85+math.sin(i*1.71)*.0016
   box((0,y,z),(2.414,.208,.095),wood,0,.0035)
  for x in [-1.2675,1.2675]:
   box((x,0,.85),(.115,1.498,.095),wood,1,.0035)
   for y in [-.58,0,.58]:peg((x,y,.898),.01,2)
 elif 'Chair' in asset:
  for x in [-.24,.24]:
   for y in [-.23,.23]:
    ob=box((x,y,.23),(.07,.07,.46),wood,2,.0025)
    for v in ob.data.vertices:
     t=max(0,min(1,v.co.z/.46));v.co.x=x+(v.co.x-x)*(.78+.22*t);v.co.y=y+(v.co.y-y)*(.78+.22*t)
   box((x,.23,.68),(.065,.065,.65),wood,2,.003)
   box((x,0,.19),(.05,.48,.055),wood,1,.002)
  for y in [-.18,0,.18]:
   ob=box((0,y,.47),(.65,.175,.065),wood,0,.0035)
  for z in [.25,.89]:box((0,.24,z),(.53,.06,.10),wood,0,.003)
  for x in [-.13,0,.13]:box((x,.24,.72),(.05,.05,.32),wood,2,.002)
  for x in [-.24,.24]:
   for z in [.89,.25]:peg((x,.206,z),.008,1)
 else:
  # Preserve all original bed timber, including head/foot rails and turned post caps.
  me=old[asset].copy();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=0],context='FACES');bm.to_mesh(me);bm.free();me.materials.clear();me.materials.append(wood)
  ob=bpy.data.objects.new('Bed original timber',me);s.collection.objects.link(ob);parts.append(ob)
  for x in [-1.15,1.15]:
   for y in [-.58,.58]:
    peg((x,y-.071,.70),.012,1)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,.52));c=bpy.context.object;c.dimensions=(.14,.14,1.04);finish(c,wood,2,0,True)
  for y in [-.62,.62]:
   bpy.ops.mesh.primitive_cube_add(size=1,location=(0,y,.36));c=bpy.context.object;c.dimensions=(2.4,.13,.25);finish(c,wood,0,0,True)
  for x in [-1.15,1.15]:
   for z in [.52,.70,.88]:
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,0,z));c=bpy.context.object;c.dimensions=(.12,1.2,.13);finish(c,wood,1,0,True)
  mattress=box((0,0,.525),(2.20,1.10,.29),pillowmat,0,.08)
  for p in mattress.data.polygons:p.use_smooth=True
  # Pillow uses a rounded cushion with a seam indentation instead of an ellipsoid.
  bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=24,radius=1,location=(-.82,0,.736));ob=bpy.context.object
  for v in ob.data.vertices:
   q=v.co.copy();v.co=(math.copysign(abs(q.x)**.55,q.x)*.30,math.copysign(abs(q.y)**.55,q.y)*.44,math.copysign(abs(q.z)**.72,q.z)*.095)
   v.co.z+=.005*math.sin(q.x*21)*math.exp(-abs(q.z)*9)
  finish(ob,pillowmat,0)
  for p in ob.data.polygons:p.use_smooth=True
  # Irregular, gravity-led folds: pinned at mattress sides; broad tension field, quiet middle.
  verts=[];faces=[];nx=65;ny=45
  for side in [0,1]:
   for i in range(nx):
    for j in range(ny):
     x=-.49+i/(nx-1)*1.53;y=-.665+j/(ny-1)*1.33;edge=max(0,(abs(y)-.46)/.205)
     fold=.009*math.sin(x*18+y*5)+.004*math.sin(x*41-y*13)+.004*math.sin(y*29+x*3)
     fold+=.018*edge*math.sin(x*30+2*math.sin(x*7))
     z=.704-max(0,abs(y)-.50)*1.25+fold-side*.007
     # Folded-back upper edge carries a sewn weighted hem.
     z+=.018*math.exp(-((x+.455)/.026)**2)
     verts.append((x,y,z))
  for side in [0,1]:
   ofs=side*nx*ny
   for i in range(nx-1):
    for j in range(ny-1):
     a=ofs+i*ny+j;f=(a,a+ny,a+ny+1,a+1);faces.append(f if side==0 else tuple(reversed(f)))
  boundary=list(range(ny))+[i*ny+ny-1 for i in range(1,nx)]+[(nx-1)*ny+j for j in range(ny-2,-1,-1)]+[i*ny for i in range(nx-2,0,-1)]
  for k,a in enumerate(boundary):b=boundary[(k+1)%len(boundary)];faces.append((a,b,b+nx*ny,a+nx*ny))
  me=bpy.data.meshes.new('Weighted folded bedcover');me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new('Flax cover',me);s.collection.objects.link(ob);finish(ob,linen,0)
  for p in me.polygons:p.use_smooth=True
 bpy.ops.object.select_all(action='DESELECT')
 for ob in parts:ob.select_set(True)
 bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();ob=bpy.context.object;ob.name=asset;ob.data.name=asset+'_Photoreal_Mesh';bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008,area_weight=.2);bpy.ops.object.mode_set(mode='OBJECT')
 coll=bpy.data.collections.new(asset);s.collection.children.link(coll);coll['dink_class']='prop';coll['dink_path']='Stonebrook/PhotorealPropsV1';coll['dink_source']='Original Blender geometry; original Dink sequence87 table and461 chairs; immutable generated oak reference from FloorOakV1, see ART_BRIEF.txt';coll['dink_tex_px']=2048
 for part in [ob]+hulls:
  for c in list(part.users_collection):c.objects.unlink(part)
  coll.objects.link(part)
 ob.hide_render=True;candidates[asset]=ob;allhulls[asset]=hulls
 for inst in instances[asset]:inst['immutable_original_mesh']=old[asset].name
 report[asset]={'original_vertices':len(old[asset].vertices),'candidate_vertices':len(ob.data.vertices),'candidate_triangles':sum(len(p.vertices)-2 for p in ob.data.polygons),'collision_hulls':len(hulls),'candidate_bounds_m':[[min(v.co[k]for v in ob.data.vertices)for k in range(3)],[max(v.co[k]for v in ob.data.vertices)for k in range(3)]],'original_bounds_m':[[min(v.co[k]for v in old[asset].vertices)for k in range(3)],[max(v.co[k]for v in old[asset].vertices)for k in range(3)]],'instances':[{ 'name':i.name,'matrix_world':[list(r)for r in i.matrix_world]}for i in instances[asset]]}
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:im.pack()
# Source preview is set to improved presentation. Original meshes remain immutable datablocks.
for n in names:
 old[n].use_fake_user=True
 for inst in instances[n]:inst.data=candidates[n].data
s.render.resolution_x=1100;s.render.resolution_y=825;s.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealPropsV1.blend'))
(O/'geometry_report.json').write_text(json.dumps({'assets':report,'immutable_source':str(SRC),'immutable_source_sha256':sha(SRC),'CPU_threads':4,'native_imported':False},indent=2))
print('PROPS_BUILT',flush=True)

# Blender audio teardown hangs in this sandbox; all durable writes above are complete.
import os,sys
sys.stdout.flush();sys.stderr.flush();os._exit(0)
