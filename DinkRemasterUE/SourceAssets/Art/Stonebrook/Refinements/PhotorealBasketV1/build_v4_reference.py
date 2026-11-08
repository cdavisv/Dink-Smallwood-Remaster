"""Isolated source-only split-willow basket, with exact existing bounds/pivot/collider."""
import bpy,bmesh,math,json,hashlib,random,os,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent;P=O/'Inputs/KIT_Stonebrook_Input.blend';name='SM_Basket_Wicker_01';rng=random.Random(1997146)
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.name='BasketSource';s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(P),link=False)as(src,dst):dst.collections=[name]
c=bpy.data.collections[name];s.collection.children.link(c)
old=next(o for o in c.objects if o.type=='MESH' and not o.name.startswith('UCX_'))
low=[min(v.co[k]for v in old.data.vertices)for k in range(3)];high=[max(v.co[k]for v in old.data.vertices)for k in range(3)]
oldtri=sum(len(p.vertices)-2 for p in old.data.polygons)
offset=old.location.copy()
for obj in c.objects:obj.location-=offset
old.name='Reference_Basket_Original';c.objects.unlink(old)
ref=bpy.data.collections.new('Reference_Only');ref.objects.link(old)
material=bpy.data.materials.new('MI_Basket_Willow_PhotoSource');material.use_nodes=True;N=material.node_tree.nodes;L=material.node_tree.links;N.clear()
def node(t,label):n=N.new(t);n.name=label;n.label=label;return n
out=node('ShaderNodeOutputMaterial','Output');bs=node('ShaderNodeBsdfPrincipled','Dry split willow');L.new(bs.outputs['BSDF'],out.inputs['Surface']);bs.inputs['Metallic'].default_value=0;bs.inputs['IOR'].default_value=1.46
attr=node('ShaderNodeAttribute','ReedMetric');attr.attribute_name='ReedMetric'
scale=node('ShaderNodeVectorMath','Long fibres in metres');scale.operation='MULTIPLY';scale.inputs[1].default_value=(9,1400,55);L.new(attr.outputs['Vector'],scale.inputs[0])
fine=node('ShaderNodeTexNoise','Restrained fibrous pores');fine.inputs['Scale'].default_value=1;fine.inputs['Detail'].default_value=3;L.new(scale.outputs[0],fine.inputs[0])
slow=node('ShaderNodeTexNoise','Natural tanning');slow.inputs['Scale'].default_value=3;slow.inputs['Detail'].default_value=2;L.new(attr.outputs['Vector'],slow.inputs[0])
seed=node('ShaderNodeAttribute','Per reed variation');seed.attribute_name='ReedSeed'
mix=node('ShaderNodeMath','Tanning plus per reed tone');mix.operation='MULTIPLY_ADD';mix.inputs[1].default_value=.6;L.new(seed.outputs['Fac'],mix.inputs[0]);L.new(slow.outputs['Fac'],mix.inputs[2])
ramp=node('ShaderNodeValToRGB','Warm unvarnished willow');ramp.color_ramp.elements[0].position=.18;ramp.color_ramp.elements[0].color=(.024,.009,.0028,1);ramp.color_ramp.elements[1].position=1.2;ramp.color_ramp.elements[1].color=(.25,.115,.035,1);L.new(mix.outputs[0],ramp.inputs[0]);L.new(ramp.outputs[0],bs.inputs['Base Color'])
fibertone=node('ShaderNodeValToRGB','Individual fine split fibres');fibertone.color_ramp.elements[0].position=.28;fibertone.color_ramp.elements[0].color=(.30,.24,.19,1);fibertone.color_ramp.elements[1].position=.72;fibertone.color_ramp.elements[1].color=(1,1,1,1);L.new(fine.outputs['Fac'],fibertone.inputs[0])
fibermix=node('ShaderNodeMixRGB','Fibre colour within each reed');fibermix.blend_type='MULTIPLY';fibermix.inputs[0].default_value=.44;L.new(ramp.outputs[0],fibermix.inputs[1]);L.new(fibertone.outputs[0],fibermix.inputs[2]);L.new(fibermix.outputs[0],bs.inputs['Base Color']);bs.inputs['Specular IOR Level'].default_value=.25
rough=node('ShaderNodeMapRange','Dry fibre roughness');rough.inputs['To Min'].default_value=.56;rough.inputs['To Max'].default_value=.86;L.new(fine.outputs['Fac'],rough.inputs[0]);L.new(rough.outputs[0],bs.inputs['Roughness'])
bump=node('ShaderNodeBump','Submillimetre raised fibres');bump.inputs['Distance'].default_value=.00032;bump.inputs['Strength'].default_value=.28;L.new(fine.outputs['Fac'],bump.inputs['Height']);L.new(bump.outputs[0],bs.inputs['Normal'])
verts=[];faces=[];metric=[];seeds=[];parts=[]
def ribbon(points,width,thickness,axis,closed=False,rounded=False):
 start=len(verts);count=len(points);distance=0;sd=rng.random()
 profile=[(math.cos(k*math.tau/6),math.sin(k*math.tau/6))for k in range(6)] if rounded else [(-1,-1),(1,-1),(1,1),(-1,1)]
 sides=len(profile)
 for i,p in enumerate(points):
  if i:distance+=(Vector(p)-Vector(points[i-1])).length
  nxt=(i+1)%count if closed else min(i+1,count-1)
  prev=(i-1)%count if closed else max(i-1,0)
  tangent=(Vector(points[nxt])-Vector(points[prev])).normalized()
  u=Vector(axis(p,i));u=(u-tangent*u.dot(tangent)).normalized();v=tangent.cross(u).normalized()
  for a,b in profile:
   verts.append(tuple(Vector(p)+u*a*width/2+v*b*thickness/2));metric.append((distance,a*width/2,sd));seeds.append(sd)
 for i in range(count if closed else count-1):
  j=(i+1)%count
  for k in range(sides):faces.append((start+i*sides+k,start+i*sides+(k+1)%sides,start+j*sides+(k+1)%sides,start+j*sides+k))
 if not closed:faces.extend([tuple(start+k for k in reversed(range(sides))),tuple(start+(count-1)*sides+k for k in range(sides))])
 parts.append({'first_vertex':start,'vertices':count*sides,'closed':closed,'width_m':width,'thickness_m':thickness})
# Each weft alternates around the straight uprights with an explicit physical clearance.
stakes=32;rows=22
for j in range(stakes):
 a=j*math.tau/stakes;points=[]
 for k in range(3):
  z=.035+k*.55/2;r=.300+(.440-.300)*(z-.035)/.55
  points.append((r*math.cos(a),r*math.sin(a),z))
 ribbon(points,.012,.006,lambda p,i,a=a:(-math.sin(a),math.cos(a),0))
for row in range(rows):
 z=.040+row*(.534/21);points=[]
 for k in range(stakes*2):
  a=k*math.tau/(stakes*2);r=.300+(.440-.300)*(z-.035)/.55+.008*math.cos(stakes*a/2+row*math.pi)
  points.append((r*math.cos(a),r*math.sin(a),z+.0008*math.sin(3*a+row*.73)))
 ribbon(points,.023,.004,lambda p,i:(0,0,1),True)
# Broad base reeds interweave; lower ring reaches ground, never a floating solid disc.
for orientation in range(2):
 for j in range(12):
  cross=(j-5.5)*.05;extent=math.sqrt(max(0,.303**2-(abs(cross)+.0225)**2));points=[]
  for k in range(9):
   along=-extent+2*extent*k/8;z=.021+(.004 if orientation==0 else -.004)*math.cos(math.pi*(along/.05+5.5)+j*math.pi)
   points.append((along,cross,z)if orientation==0 else(cross,along,z))
  ribbon(points,.045,.003,lambda p,i,o=orientation:(0,1,0)if o==0 else(1,0,0),rounded=True)
# Split-cane structural rim, foot and bound handle loops.
for z,r,w,t in [(.009,.303,.018,.018),(.586,.442,.026,.018),(.566,.438,.012,.008)]:
 pts=[(r*math.cos(k*math.tau/64),r*math.sin(k*math.tau/64),z)for k in range(64)]
 ribbon(pts,w,t,lambda p,i:(0,0,1),True,rounded=True)
for side in [-1,1]:
 pts=[(side*(.500+.050*math.sin(k*math.pi/32)),-.105*math.cos(k*math.pi/32),.465+.190*math.sin(k*math.pi/32))for k in range(33)]
 ribbon(pts,.022,.018,lambda p,i:(0,0,1),rounded=True)
 for end in [-1,1]:
  # Bent willow anchor lugs physically bridge the wall and upright hand loop.
  anchor=[(side*.400,end*.105,.475),(side*.450,end*.105,.478),(side*.500,end*.105,.465)]
  ribbon(anchor,.022,.012,lambda p,i:(0,1,0),rounded=True)
  pts=[]
  for k in range(17):
   t=k/16;angle=t*math.tau*4
   pts.append((side*(.500+.012*math.cos(angle)),end*.105+.012*math.sin(angle),.445+t*.043))
  ribbon(pts,.004,.002,lambda p,i:(0,0,1))
# Continuous cane binding winds around the rounded upper structural rim.
pts=[]
for k in range(192):
 a=k*math.tau/192;phi=24*a;r=.442+.011*math.cos(phi)
 pts.append((r*math.cos(a),r*math.sin(a),.586+.015*math.sin(phi)))
ribbon(pts,.004,.002,lambda p,i:(0,0,1),True)
newlow=[min(v[k]for v in verts)for k in range(3)];newhigh=[max(v[k]for v in verts)for k in range(3)]
verts=[tuple(low[k]+(v[k]-newlow[k])*(high[k]-low[k])/(newhigh[k]-newlow[k])for k in range(3))for v in verts]
me=bpy.data.meshes.new(name+'_PhotoMesh');me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);c.objects.link(ob);ob.data.materials.append(material)
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
ma=me.attributes.new('ReedMetric','FLOAT_VECTOR','POINT');sa=me.attributes.new('ReedSeed','FLOAT','POINT')
for i in range(len(verts)):ma.data[i].vector=metric[i];sa.data[i].value=seeds[i]
for p in me.polygons:p.use_smooth=True
me.set_sharp_from_angle(angle=math.radians(85))
bpy.context.view_layer.objects.active=ob;ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.0,island_margin=.001);bpy.ops.object.mode_set(mode='OBJECT')
c['dink_class']='prop';c['dink_path']='Stonebrook/PhotorealBasketV1';c['dink_tex_px']=2048;c['dink_source']='Project-authored split willow; added room prop, not a claimed direct sprite replacement'
for o in c.objects:
 if o.name.startswith('UCX_'):o.hide_render=True
# Reference comparison scene retains only the exact old basket and its original materials.
reference=bpy.data.scenes.new('BasketReference');reference.collection.children.link(ref)
# Portable source material uses nodes only. Pack inherited reference images for review.
for image in bpy.data.images:
 if image.source=='FILE':
  try:image.reload();image.pack()
  except RuntimeError:pass
report={'schema':'dink-basket-source/1','candidate':True,'input_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'reference_identity':'Existing authored decorative WickerBasket in room1, no direct original sprite mapping claimed','original_bounds_m':[low,high],'original_triangles':oldtri,'candidate_triangles':sum(len(p.vertices)-2 for p in me.polygons),'candidate_bounds_m':[[min(v.co[k]for v in me.vertices)for k in range(3)],[max(v.co[k]for v in me.vertices)for k in range(3)]],'parts':len(parts),'stakes':stakes,'weft_rows':rows,'construction':'Alternating over/under split willow with woven base, foot/rim and wrapped handle bindings','collision':[{'name':o.name,'vertices':[list(v.co)for v in o.data.vertices],'matrix':[list(row)for row in o.matrix_world]}for o in c.objects if o.name.startswith('UCX_')],'native_imported':False,'limits':['Source candidate only; no Unreal import, texture bakes or gameplay changes.','Geometry intersection/UV guide and visual review remain required.']}
assert report['candidate_triangles']<=20000,report['candidate_triangles']
(O/'source_report.json').write_text(json.dumps(report,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(O/'Inputs/V4_Source_Rebuilt.blend'))
print('BASKET_SOURCE_BUILT',report['candidate_triangles'],flush=True)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
