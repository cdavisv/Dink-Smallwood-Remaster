"""Original bespoke Stonebrook pillbug. Deterministic Blender5.2 source, metres.
Anatomy: seven tergites,14 walking legs, lateral compound eyes, jointed antennae.
Procedural project-authored geometry/materials only; reference biology is not geometry.
"""
import bpy,bmesh,math,json,random,sys,os
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path(__file__).resolve().parents[1]
for p in ['Working','Textures','Export','Previews']: (ROOT/p).mkdir(parents=True,exist_ok=True)
random.seed(438)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.render.fps=40
coll=bpy.data.collections.new('SK_Pillbug');scene.collection.children.link(coll)
coll['dink_class']='creature';coll['dink_path']='Pillbug';coll['dink_tex_px']=2048
objects=[]
def mat(name,lo,hi,rough,scale=16,bump=.0015):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Roughness'].default_value=rough;bs.inputs['Specular IOR Level'].default_value=.3
 coord=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=scale;noise.inputs['Detail'].default_value=4;noise.inputs['Roughness'].default_value=.75;l.new(coord.outputs['Object'],noise.inputs['Vector'])
 ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.19;ramp.color_ramp.elements[0].color=(*lo,1);ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(*hi,1);l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Base Color'])
 fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=340;fine.inputs['Detail'].default_value=2;l.new(coord.outputs['Object'],fine.inputs['Vector']);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.26;b.inputs['Distance'].default_value=bump;l.new(fine.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],bs.inputs['Normal'])
 rr=n.new('ShaderNodeMapRange');rr.inputs['From Min'].default_value=0;rr.inputs['From Max'].default_value=1;rr.inputs['To Min'].default_value=rough-.08;rr.inputs['To Max'].default_value=rough+.09;l.new(noise.outputs['Fac'],rr.inputs['Value']);l.new(rr.outputs[0],bs.inputs['Roughness']);return m
shell=mat('MI_Pillbug_Carapace',(.018,.048,.055),(.085,.175,.16),.57,11,.0013)
rim=mat('MI_Pillbug_Ochre',(.09,.064,.027),(.30,.21,.083),.64,35,.0009)
joint=mat('MI_Pillbug_Joints',(.015,.021,.018),(.052,.064,.048),.72,24,.0008)
eye=mat('MI_Pillbug_Eyes',(.006,.009,.007),(.022,.030,.018),.24,40,.00025)

def mesh(name,vs,fs,material,bone):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();ob=bpy.data.objects.new(name,me);coll.objects.link(ob);me.materials.append(material)
 for p in me.polygons:p.use_smooth=True
 group=ob.vertex_groups.new(name=bone);group.add(list(range(len(vs))),1,'REPLACE');objects.append(ob);return ob

def tube(name,points,radii,material,bone,n=10):
 pts=[Vector(p) for p in points];vs=[];fs=[]
 for i,p in enumerate(pts):
  tangent=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized();ref=Vector((0,0,1))
  if abs(tangent.dot(ref))>.9:ref=Vector((0,1,0))
  u=tangent.cross(ref).normalized();v=tangent.cross(u).normalized()
  if name in ['Tapered femoral cuticle','Tibial walkingsegment']:u*=.73;v*=1.13
  for j in range(n):a=math.tau*j/n;vs.append(p+radii[i]*(math.cos(a)*u+math.sin(a)*v))
 for i in range(len(pts)-1):
  for j in range(n):a=i*n+j;b=i*n+(j+1)%n;fs.append((a,b,b+n,a+n))
 vs.extend([pts[0],pts[-1]]);cap=len(vs)-2
 for j in range(n):fs.extend([(cap,(j+1)%n,j),(cap+1,(len(pts)-1)*n+j,(len(pts)-1)*n+(j+1)%n)])
 return mesh(name,vs,fs,material,bone)

def ellipsoid(name,center,scale,material,bone,n=24,rings=12):
 vs=[(center[0],center[1],center[2]+scale[2])];fs=[]
 for i in range(1,rings):
  p=math.pi*i/rings
  for j in range(n):a=math.tau*j/n;vs.append((center[0]+scale[0]*math.sin(p)*math.cos(a),center[1]+scale[1]*math.sin(p)*math.sin(a),center[2]+scale[2]*math.cos(p)))
 bottom=len(vs);vs.append((center[0],center[1],center[2]-scale[2]))
 for j in range(n):fs.append((0,1+j,1+(j+1)%n));fs.append((bottom,1+(rings-2)*n+(j+1)%n,1+(rings-2)*n+j))
 for i in range(rings-2):
  for j in range(n):a=1+i*n+j;b=1+i*n+(j+1)%n;fs.append((a,a+n,b+n,b))
 return mesh(name,vs,fs,material,bone)

# Domed soft sternum is a continuous flattened organic support beneath the armor.
ellipsoid('Continuous ventral abdomen',(-.05,0,.255),(.59,.27,.17),joint,'pelvis',32,16)
segments=[]
def plate(name,cx,width,length,height,zbase,bone):
 # Closed sculpted arched tergite:9 longitudinal stations, curved bowed edges,
 # continuous rolled perimeter, inward closed lower face. Never a flat sprite card.
 vs=[];fs=[];NU=8;NV=32
 def point(u,a,inner=False):
  y=width*math.sin(a);arch=max(0,math.cos(a));bow=.028*math.sin(a)**2
  x=cx+(u-.5)*length+bow
  z=zbase+height*arch+.010*math.sin(math.pi*u)*arch+.0016*math.sin(a*18+cx*13)*arch*math.sin(math.pi*u)
  if inner:z-=.016
  return Vector((x,y,z))
 for inner in [False,True]:
  for u in range(NU+1):
   for j in range(NV+1):a=-math.pi/2+math.pi*j/NV;vs.append(point(u/NU,a,inner))
 size=(NU+1)*(NV+1)
 for k in range(2):
  for i in range(NU):
   for j in range(NV):a=k*size+i*(NV+1)+j;face=(a,a+NV+1,a+NV+2,a+1);fs.append(face if k==0 else tuple(reversed(face)))
 for i in [0,NU]:
  for j in range(NV):a=i*(NV+1)+j;fs.append((a,a+1,a+1+size,a+size))
 for j in [0,NV]:
  for i in range(NU):a=i*(NV+1)+j;fs.append((a,a+NV+1,a+NV+1+size,a+size))
 ob=mesh(name,vs,fs,shell,bone)
 # Fine raised worn rim and secondary growth ridge follow the front edge in3D.
 for u,rad in [(0,.0048),(.12,.0018)]:
  pts=[point(u,-math.pi/2+math.pi*j/32)+Vector((0,0,.001)) for j in range(33)]
  tube('Rolled worn tergite edge',pts,[rad]*33,rim if u==0 else shell,bone,6)
 for side in [-1,1]:
  # Lateral epimera points are integral armorextensions, compact anddownturned.
  p=point(.20,side*math.pi/2);tip=p+Vector((-.035,side*.036,-.034));tube('Epimeral ochre spur',[p,(p+tip)*.5,tip],[.018,.012,.001],rim,bone,8)
 return ob
for i,cx in enumerate([.39,.245,.10,-.045,-.19,-.335,-.47]):
 width=[.265,.315,.345,.35,.338,.305,.25][i];height=[.23,.255,.275,.28,.265,.235,.195][i]
 name='tergite_%02d'%(i+1);segments.append((name,cx,width));plate('Articulated thoracic tergite %02d'%(i+1),cx,width,.19,height,.215,name)
# Pleon shield and triangular terminal telson tuck under final thoracicsegment.
plate('Posterior pleotelson',-.61,.165,.19,.125,.22,'tail')
for side in [-1,1]:tube('Short protected uropod',[(-.64,side*.11,.22),(-.73,side*.14,.205),(-.77,side*.15,.195)],[.022,.015,.002],rim,'tail',10)
# Head is a broad flattened cephalic shield, naturally embedded beneath firstplate.
ellipsoid('Flattened cephalon',(.54,0,.28),(.15,.215,.155),shell,'head',32,16)
# Frontal clypeus and sheltered mouthparts distinguish the facefrom a smooth dome.
ellipsoid('Clypeus brow',(.654,0,.285),(.047,.145,.073),shell,'head',24,10)
for s in [-1,1]:
 ellipsoid('Inlaid lateral eye socket',(.59,s*.18,.335),(.046,.030,.035),shell,'head',20,10)
 ellipsoid('Inset compound lateral eye',(.606,s*.197,.34),(.033,.013,.024),eye,'head',20,10)
 # Smallfacets are nearlyflush, not bulging eyeballs.
 for k in range(7):
  a=math.tau*k/7;ellipsoid('Compound eye facet',(.611+.013*math.cos(a),s*(.208+.001*math.cos(a)),.341+.012*math.sin(a)),(.008,.004,.007),eye,'head',8,6)
 tube('Sheltered mandible',[(.635,s*.073,.19),(.691,s*.047,.168),(.68,s*.012,.177)],[.025,.019,.004],rim,'head',10)
 tube('Maxillary palp',[(.652,s*.105,.203),(.704,s*.12,.183),(.719,s*.095,.18)],[.012,.009,.0015],joint,'head',8)
#14 independentlyrigged legs, coherent short coxa,femur,tibia/tarsus silhouettes.
legs=[]
for i,(seg,cx,w) in enumerate(segments):
 for s,label in [(1,'l'),(-1,'r')]:
  direction=(3-i)*.024;hip=Vector((cx,s*(w-.045),.245));knee=Vector((cx+direction,s*(w+.16),.28));foot=Vector((cx+direction*1.8,s*(w+.19),.017))
  upper='leg_%02d_upper_%s'%(i+1,label);lower='leg_%02d_lower_%s'%(i+1,label);legs.append((upper,lower,seg,hip,knee,foot,i,label))
  ellipsoid('Protected coxal ball',hip,(.032,.038,.03),joint,upper,12,8)
  tube('Tapered femoral cuticle',[hip,hip.lerp(knee,.20)+Vector((.005,0,.01)),hip.lerp(knee,.65)+Vector((0,0,.006)),knee],[.026,.035,.022,.020],shell,upper,10)
  ellipsoid('Inset knee membrane',knee,(.020,.022,.020),shell,lower,12,8)
  tube('Tibial walkingsegment',[knee,knee.lerp(foot,.3)+Vector((-.008,0,0)),knee.lerp(foot,.77),foot],[.021,.025,.011,.006],rim,lower,10)
  tip=foot+Vector((.018,s*.018,-.012));tube('Hooked paired walkingclaw',[foot,tip,tip+Vector((.009,-s*.005,-.003))],[.009,.006,.001],joint,lower,8)
  # Closelyfitted longitudinal carina and transverse tarsal sutures breakup smoothrods.
  hp=hip.lerp(knee,.15)+Vector((0,0,.027));kp=hip.lerp(knee,.88)+Vector((0,0,.020))
  tube('Femoral cuticle ridge',[hp,hp.lerp(kp,.5)+Vector((0,0,.005)),kp],[.003,.0035,.001],rim,upper,6)
  for q in [.68,.78,.87]:
   p=knee.lerp(foot,q);d=(foot-knee).normalized();tube('Fine tarsal articulation',[p-d*.0012,p+d*.0012],[.014*(1-q)+.003]*2,joint,lower,8)
  # Tiny cuticular ridges keeplimbs readablewithout gross prickles.
  for q in [.36,.55,.72]:
   p=knee.lerp(foot,q);tube('Tibial sensor spur',[p,p+Vector((-.02,s*.012,.008))],[.004,.0008],joint,lower,5)
# Jointed antennae rootatfrontalhead, broadbase then taperedflagellum.
antennae=[]
for s,label in [(1,'l'),(-1,'r')]:
 a=Vector((.645,s*.115,.315));b=Vector((.78,s*.26,.34));c=Vector((1.005,s*.355,.26));antennae.append((label,a,b,c))
 ellipsoid('Antennal socket',a,(.032,.033,.028),joint,'antenna_01_'+label,16,8)
 tube('Antennal peduncle',[a,a.lerp(b,.3)+Vector((0,0,.015)),b],[.022,.023,.013],rim,'antenna_01_'+label,10)
 tube('Tapered sensory flagellum',[b,b.lerp(c,.3)+Vector((0,0,.015)),b.lerp(c,.7)+Vector((0,0,.01)),c],[.014,.012,.007,.0012],shell,'antenna_02_'+label,10)
 for q in [.20,.34,.48,.62,.76,.88]:
  p=b.lerp(c,q)+Vector((0,0,.01*math.sin(q*math.pi)));d=(c-b).normalized();tube('Flagellar annulation',[p-d*.0015,p+d*.0015],[.014*(1-q)+.001]*2,rim,'antenna_02_'+label,8)

# Onebespoke root,43bones, rigid cuticle weights(1influence) avoidsoftbodyflaps.
bpy.ops.object.armature_add(enter_editmode=True);arm=bpy.context.object;arm.name='Armature'
for c in list(arm.users_collection):c.objects.unlink(arm)
coll.objects.link(arm);arm.data.edit_bones.remove(arm.data.edit_bones[0])
def bone(name,h,t,parent=None):
 b=arm.data.edit_bones.new(name);b.head=h;b.tail=t;b.roll=0
 if parent:b.parent=arm.data.edit_bones[parent]
 return b
bone('root',(0,0,0),(0,.1,0));bone('pelvis',(-.1,0,.255),(.1,0,.255),'root')
for name,cx,w in segments:bone(name,(cx,0,.255),(cx+.07,0,.26),'pelvis')
bone('tail',(-.55,0,.245),(-.71,0,.24),'pelvis');bone('head',(.46,0,.28),(.65,0,.28),'pelvis')
for upper,lower,seg,h,k,f,i,label in legs:bone(upper,h,k,seg);bone(lower,k,f,upper)
for label,a,b,c in antennae:bone('antenna_01_'+label,a,b,'head');bone('antenna_02_'+label,b,c,'antenna_01_'+label)
bpy.ops.object.mode_set(mode='OBJECT');arm.show_in_front=True
bpy.ops.object.select_all(action='DESELECT')
for ob in objects:ob.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='SK_Pillbug_LOD0'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
# Remove duplicate materialslotswhile retainingthe4semantic slots.
materials=[shell,rim,joint,eye];old=[s.material for s in ob.material_slots];indices=[materials.index(old[p.material_index]) for p in ob.data.polygons];ob.data.materials.clear()
for m in materials:ob.data.materials.append(m)
for p,index in zip(ob.data.polygons,indices):p.material_index=index
ob.parent=arm;mod=ob.modifiers.new('Own bespoke pillbug rig','ARMATURE');mod.object=arm
for b in arm.pose.bones:b.rotation_mode='QUATERNION'
sys.path.insert(0,str(Path(__file__).parent));from pillbug_actions import create_actions
actions=create_actions(arm,scene,legs)
# Neutral photographic review stage;notexported.
stage=bpy.data.collections.new('Preview_Stage');scene.collection.children.link(stage)
def stageob(o):
 for c in list(o.users_collection):c.objects.unlink(o)
 stage.objects.link(o)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.004));floor=bpy.context.object;floor.name='Review ground';stageob(floor)
m=bpy.data.materials.new('Review neutral ground');m.diffuse_color=(.10,.11,.12,1);m.use_nodes=True;m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.10,.11,.12,1);m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.9;floor.data.materials.append(m)
for name,pos,power,size in [('Large neutral key',(1,-3,4),420,3),('Soft warm fill',(-2,-1,1.5),110,2),('Cool outline',(0,3,2.4),240,2)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);stage.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.25))-o.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('Neutral review world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.18,.22,1);world.node_tree.nodes['Background'].inputs[1].default_value=.35;scene.world=world
cd=bpy.data.cameras.new('Pillbug review');cam=bpy.data.objects.new('Pillbug review',cd);stage.objects.link(cam);cam.location=(2.7,-3.3,2.1);cam.rotation_euler=(Vector((.08,0,.27))-cam.location).to_track_quat('-Z','Y').to_euler();cd.lens=68;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
arm.animation_data.action=None;arm.data.pose_position='REST';scene.frame_set(1)
ob.data.calc_loop_triangles();report={'schema':'dink-pillbug-source/1','units':'metres','forward':'+X','root_basis':'identity along+Y','bone_count':len(arm.data.bones),'bones':[{'name':b.name,'parent':b.parent.name if b.parent else None,'matrix_local':[list(r) for r in b.matrix_local]} for b in arm.data.bones],'triangles_before_lods':len(ob.data.loop_triangles),'actions':actions,'leg_chains':[{'upper':u,'lower':l,'segment':p,'rest_foot':list(f)} for u,l,p,h,k,f,i,s in legs]}
(ROOT/'pillbug_rig_report.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Working/Pillbug_Procedural.blend'))
arm.data.pose_position='POSE'
for key,frame in [('Idle',1),('Walk',5),('Run',5),('Run',9)]:
 arm.animation_data.action=bpy.data.actions['Pillbug_'+key];scene.frame_set(frame);scene.render.filepath=str(ROOT/'Previews'/('pillbug_'+key.lower()+'_%02d.png'%frame));bpy.ops.render.render(write_still=True)
print('PILLBUG SOURCE REVIEW READY',report['triangles_before_lods'],'triangles',report['bone_count'],'bones',flush=True)
