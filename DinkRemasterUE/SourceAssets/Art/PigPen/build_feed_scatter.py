"""Original small wheat-feed scatter. Blender 5.2; metre units; no collision."""
import bpy,math,random,json
from pathlib import Path
from mathutils import Vector
ART=Path(__file__).resolve().parent
random.seed(407431)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for col in list(bpy.data.collections):bpy.data.collections.remove(col)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
name='SM_FeedScatter_Wheat_01';col=bpy.data.collections.new(name);scene.collection.children.link(col)
col['dink_class']='prop_small';col['dink_path']='PigPen';col['dink_nanite']='no';col['dink_source']='Original project wheat kernels; procedural source seed407431, CC0 project-authored.'
mat=bpy.data.materials.new('MI_PigPen_Wheat');mat.use_nodes=True
bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(.48,.31,.12,1);bsdf.inputs['Roughness'].default_value=.84;bsdf.inputs['Metallic'].default_value=0;bsdf.inputs['Specular IOR Level'].default_value=.25
verts=[];faces=[]
def add(v,f):
 offset=len(verts);verts.extend(v);faces.extend(tuple(offset+i for i in face) for face in f)
for k in range(80):
 a=random.random()*math.tau;r=math.sqrt(random.random())*.88;x=.125*r*math.cos(a);y=.09*r*math.sin(a);z=.001+.011*max(0,1-r*r)
 angle=random.random()*math.tau;length=random.uniform(.007,.009);width=random.uniform(.0027,.0036);height=random.uniform(.0024,.0031)
 if k<4:
  x,y,angle=[(-.121,0,0),(.121,0,0),(0,-.086,math.pi/2),(0,.086,math.pi/2)][k];length=.008
 z=0
 local=[(-length*.5,0,0)]
 for along in [-.28,.28]:
  for yy,zz in [(width*.5,0),(0,height*.5),(-width*.5,0),(0,-height*.5)]:local.append((length*along,yy,zz))
 local.append((length*.5,0,0));v=[(x+xx*math.cos(angle)-yy*math.sin(angle),y+xx*math.sin(angle)+yy*math.cos(angle),z+zz+height*.5) for xx,yy,zz in local];f=[]
 for i in range(4):
  j=(i+1)%4;f.extend([(0,1+j,1+i),(1+i,1+j,5+j,5+i),(9,5+i,5+j)])
 add(v,f)
mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(mat);mesh.update()
obj=bpy.data.objects.new(name+'_LOD0',mesh);col.objects.link(obj);bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False) if hasattr(bpy.ops.mesh,'normals_make_consistent') else None
bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
# Four real grains anchor the25x18cm bounds; there is no opaque disc under them.
for lod,stride in [(1,2),(2,8)]:
 chosen=[k for k in range(80) if k<4 or k%stride==0];vv=[];ff=[]
 for k in chosen:
  index=len(vv);vv.extend(verts[k*10:(k+1)*10]);ff.extend(tuple(index+i-k*10 for i in face) for face in faces[k*12:(k+1)*12])
 lm=bpy.data.meshes.new(name+'_LOD'+str(lod));lm.from_pydata(vv,[],ff);lm.materials.append(mat);lm.update();lo=bpy.data.objects.new(name+'_LOD'+str(lod),lm);col.objects.link(lo)
 bpy.context.view_layer.objects.active=lo;obj.select_set(False);lo.select_set(True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT');lo.hide_render=True
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
tris=sum(len(p.vertices)-2 for p in mesh.polygons);dims=list(obj.dimensions)
assert tris<=1500,(tris,'triangle budget');assert abs(dims[0]-.25)<1e-6 and abs(dims[1]-.18)<1e-6,dims
spec={'schema':'dink-stonebrook-art/1','units':'metres; FBX UnitScaleFactor100 imports centimetres','source':'KIT_PigPen.blend','seed':407431,'assets':{name:{'class':'prop_small','dimensions_m':dims,'materials':[mat.name],'fbx':'Export/Game/Dink/Props/PigPen/'+name+'.fbx','blend_collection':name,'pivot':'base_center; groundZ0; centred25x18cm footprint','triangles':tris,'expected_lods':3,'collision':False,'nanite':False}},'materials':{mat.name:{'base_color':[.48,.31,.12],'roughness':.84,'metallic':0,'textures':{}}},'notes':['Original authored grain, informed by source431_04.png.','80individual7-9mm loose kernels; no opaque backing disc or collision geometry.','Uses one constant rough PBR material; no downloaded textures.']}
(ART/'art_manifest.json').write_text(json.dumps(spec,indent=2)+'\n')
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.device='CPU';scene.render.resolution_x=600;scene.render.resolution_y=450;scene.render.resolution_percentage=100;scene.world.color=(.18,.18,.18)
preview=bpy.data.collections.new('Preview');scene.collection.children.link(preview)
light=bpy.data.lights.new('Softbox','AREA');light.energy=14;light.shape='DISK';light.size=.4;lo=bpy.data.objects.new('Softbox',light);preview.objects.link(lo);lo.location=(.1,-.15,.4)
cam=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',cam);preview.objects.link(co);co.location=(.22,-.35,.32);co.rotation_euler=(Vector((0,0,0))-co.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=.36;scene.camera=co
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'KIT_PigPen.blend'))
scene.render.filepath=str(ART/'preview_feed_scatter.png');bpy.ops.render.render(write_still=True)
print('PIGPEN FEED SOURCE OK',tris,dims)
