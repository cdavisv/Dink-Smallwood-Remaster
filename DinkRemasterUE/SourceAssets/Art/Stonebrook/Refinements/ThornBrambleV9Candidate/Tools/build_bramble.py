import bpy,math,random,json,os
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[1];(P/'Review').mkdir(exist_ok=True);random.seed(9073)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1

def shader(name):
 m=bpy.data.materials.new(name);m.use_nodes=True;return m,m.node_tree.nodes,m.node_tree.links
library=Path(__file__).resolve().parents[4]/'SharedMaterials'/'ThornBarkBroadleafV1'/'SharedThornBroadleaf_LibraryCandidate.blend'
with bpy.data.libraries.load(str(library),link=False) as (data_from,data_to):data_to.materials=['MI_Shared_ThornBark2m','MI_Shared_BroadleafTrimV1']
wood=bpy.data.materials['MI_Shared_ThornBark2m'];leaf=bpy.data.materials['MI_Shared_BroadleafTrimV1']
C=bpy.data.collections.new('SM_ThornBramble_01');s.collection.children.link(C);C['dink_class']='foliage';C['dink_nanite']='no';C['families']='thorn_bush seq90/frame7 ONLY';C['dink_source']='Original procedural study9073; originalgrave-07.bmp guide; registered shared bark2m/broadleaftrim source candidate; native pending'
vs=[];fs=[];ms=[];uvs=[]
def add(v):vs.append(v);return len(vs)-1
def face(ids,mi,coords=None):fs.append(ids);ms.append(mi);uvs.append(coords)
def tube(points,r,sides=6):
 rings=[]
 for i,p in enumerate(points):
  axis=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized();u=axis.cross(Vector((0,0,1)))
  if u.length<.01:u=axis.cross(Vector((0,1,0)))
  u.normalize();v=axis.cross(u);rad=r*(1-.90*i/(len(points)-1));rings.append([add(p+rad*(u*math.cos(j*math.tau/sides)+v*math.sin(j*math.tau/sides))) for j in range(sides)])
 face(tuple(reversed(rings[0])),0);face(tuple(rings[-1]),0)
 distances=[0]
 for pa,pb in zip(points,points[1:]):distances.append(distances[-1]+(pb-pa).length)
 for seg,(a,b) in enumerate(zip(rings,rings[1:])):
  for j in range(sides):face((a[j],a[(j+1)%sides],b[(j+1)%sides],b[j]),0,[(j/sides*math.tau*r/2,distances[seg]/2),((j+1)/sides*math.tau*r/2,distances[seg]/2),((j+1)/sides*math.tau*r/2,distances[seg+1]/2),(j/sides*math.tau*r/2,distances[seg+1]/2)])
def thorn(p,d):tube([p,p+d*.65,p+d+Vector((0,0,-.008))],.004,3)
def blade(p,d,length):
 d=d.normalized();side=d.cross(Vector((0,0,1)))
 if side.length<.01:side=Vector((1,0,0))
 side.normalize();side*=length*.33;d*=length;curl=random.uniform(-.025,.025);outline=[];coords=[]
 for t,wide in [(0,0),(.17,.60),(.29,.82),(.39,.71),(.49,1),(.59,.85),(.72,.79),(.85,.42),(1,0),(.85,-.42),(.72,-.79),(.59,-.85),(.49,-1),(.39,-.71),(.29,-.82),(.17,-.6)]:
  outline.append(p+d*t+side*wide+Vector((0,0,curl*t*t)));coords.append((.5+wide*.5,t))
 if min(v.z for v in outline)<0:return
 outline=[add(v) for v in outline]
 center=add(p+d*.48+Vector((0,0,.006)));
 for i in range(len(outline)):j=(i+1)%len(outline);face((outline[i],outline[j],center),1,[coords[i],coords[j],(.5,.48)])
# A few basal stools generate intertwined canes, secondary twigs and scattered leaf groups.
roots=[Vector((random.uniform(-.32,.32),random.uniform(-.25,.25),0)) for _ in range(7)]
for k in range(26):
 root=roots[k%7];a=random.uniform(0,math.tau);h=random.uniform(.25,.66) if k%2==0 else random.uniform(.60,1.17);reach=random.uniform(.58,1.0);curl=random.uniform(-1.4,1.4);pts=[]
 for i in range(13):
  t=i/12;angle=a+curl*t+.65*math.sin(t*math.pi);rad=reach*math.sin(t*math.pi*.64);pts.append(root+Vector((math.cos(angle)*rad,math.sin(angle)*rad*.82,h*math.sin(t*math.pi*.90))))
 tube(pts,random.uniform(.008,.014),7)
 for i in [3,6,9]:
  p=pts[i];direction=Vector((math.cos(a+i*.6),math.sin(a+i*.6),random.uniform(-.5,.2)));thorn(p,direction*random.uniform(.018,.04))
 for branchindex in [1,4,8]:
  base=pts[branchindex];angle=a+random.choice([-1,1])*random.uniform(.6,1.8);length=random.uniform(.18,.40);end=base+Vector((math.cos(angle)*length,math.sin(angle)*length,random.uniform(-.08,.20)))
  twig=[base.lerp(end,t/7)+Vector((0,0,.055*math.sin(t/7*math.pi))) for t in range(8)];tube(twig,.0045,5)
  for j in range(1,8):
   pt=twig[j];direction=Vector((math.cos(angle+random.choice([-1,1])*1.1),math.sin(angle+random.choice([-1,1])*1.1),random.uniform(-.6,.35)));blade(pt,direction,random.uniform(.09,.15));
   if j==4:thorn(pt,Vector((0,0,.022)))
# Low curled crossing runners redistribute the tiny-thorn budget into bramble mass.
for k in range(12):
 a=random.uniform(0,math.tau);center=Vector((random.uniform(-.45,.45),random.uniform(-.35,.35),.025));u=Vector((math.cos(a),math.sin(a),0));v=Vector((-math.sin(a),math.cos(a),0));radius=random.uniform(.28,.58);height=random.uniform(.22,.58)
 pts=[center+u*(radius*math.sin(t/16*math.pi*1.8))+v*(radius*.5*math.sin(t/16*math.pi*2.7))+Vector((0,0,height*math.sin(t/16*math.pi))) for t in range(17)];tube(pts,random.uniform(.004,.008),5)
 for j in [4,7,10,13]:
  blade(pts[j],u*random.choice([-1,1])+Vector((0,0,.2)),random.uniform(.08,.12))
vs=[Vector((v.x*.78,v.y*.78,v.z*.90)) for v in vs]
xmid=(min(v.x for v in vs)+max(v.x for v in vs))/2;ymid=(min(v.y for v in vs)+max(v.y for v in vs))/2;zmin=min(v.z for v in vs)
vs=[v-Vector((xmid,ymid,zmin)) for v in vs]
me=bpy.data.meshes.new('BrambleLOD0');me.from_pydata(vs,[],fs);me.materials.append(wood);me.materials.append(leaf)
for poly,mi in zip(me.polygons,ms):poly.material_index=mi;poly.use_smooth=True
layer=me.uv_layers.new(name='UV0_SharedLeafAndMetricBark')
for poly,coords in zip(me.polygons,uvs):
 for j,li in enumerate(poly.loop_indices):
  co=me.vertices[me.loops[li].vertex_index].co;layer.data[li].uv=coords[j] if coords else (co.x/2,co.z/2)
base=bpy.data.objects.new('SM_ThornBramble_01_LOD0',me);C.objects.link(base);report=[]
for lod,ratio in [(0,1),(1,.52),(2,.24)]:
 ob=base if lod==0 else base.copy()
 if lod:ob.data=me.copy();C.objects.link(ob);ob.name='SM_ThornBramble_01_LOD'+str(lod);bpy.context.view_layer.objects.active=ob;mod=ob.modifiers.new('AuthoredGeometryReduction','DECIMATE');mod.ratio=ratio;bpy.ops.object.modifier_apply(modifier=mod.name)

 shiftz=min(vert.co.z for vert in ob.data.vertices)
 for vert in ob.data.vertices:vert.co.z-=shiftz
 ob.data.calc_loop_triangles();bpy.context.view_layer.update();report.append({'lod':lod,'triangles':len(ob.data.loop_triangles),'bounds_min':[min(v.co[i] for v in ob.data.vertices) for i in range(3)],'bounds_max':[max(v.co[i] for v in ob.data.vertices) for i in range(3)],'dimensions_m':list(ob.dimensions)});ob.hide_render=lod!=0;ob.hide_set(lod!=0)
(P/'geometry_report.json').write_text(json.dumps(report,indent=2))
# Neutral studio only, outside export collection.
m,n,l=shader('QA_Ground');n.get('Principled BSDF').inputs['Base Color'].default_value=(.17,.18,.15,1);bpy.ops.mesh.primitive_plane_add(size=200);bpy.context.object.data.materials.append(m)
s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.50,.58,.68,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.35
for loc,power,size in [((1,-3,5),650,4),((-3,1,3),400,3)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,.6))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(2.9,-3.8,2.1));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=2.8;s.camera=cam
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=24;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=1000;s.render.resolution_y=800;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX';cam.rotation_euler=(Vector((0,0,.55))-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.preferences.filepaths.save_version=0;bpy.context.preferences.filepaths.file_preview_type='NONE';bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThornBramble_SharedSourceV1.blend'))
for i,loc in enumerate([(2.9,-3.8,2.1),(-3,-2,1.6),(0,0,5)]):
 cam.location=loc;cam.rotation_euler=(Vector((0,0,.55))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(P/'Review'/('shared_%02d.png'%i));bpy.ops.render.render(write_still=True)
# Temporary studio floor is only a render helper, never a delivered source mesh/material.
for ob in list(bpy.data.objects):
 if ob.type=='MESH' and any(m and m.name=='QA_Ground' for m in ob.data.materials):bpy.data.objects.remove(ob,do_unlink=True)
if bpy.data.materials.get('QA_Ground'):bpy.data.materials.remove(bpy.data.materials['QA_Ground'])
for image in bpy.data.images:
 if image.packed_file:image.filepath='//../../../SharedMaterials/ThornBarkBroadleafV1/Textures/'+Path(image.filepath).name
bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThornBramble_SharedSourceV1.blend'))
print('SOURCE_RENDER_COMPLETE',flush=True);os._exit(0)
