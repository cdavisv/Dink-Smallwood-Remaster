"""Original organic pig, compact quadruped rig and deterministic pose actions.
Blender 5.2 LTS. Source is metres; production exports are separate later step.
"""
import bpy,bmesh,math,json,random,sys,os
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path(__file__).resolve().parents[1];ROOT.mkdir(parents=True,exist_ok=True)
random.seed(407)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.fps=30
COLL=bpy.data.collections.new('SK_Pig_Stonebrook');scene.collection.children.link(COLL)
COLL['dink_class']='creature_quadruped';COLL['dink_path']='Pig';COLL['dink_tex_px']=2048

def move_collection(ob):
    for c in list(ob.users_collection):c.objects.unlink(ob)
    COLL.objects.link(ob)

def material(name,color,rough=.6):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough
    return mat
skin=material('MI_Pig_Skin',(.295,.20,.19),.68)
nodes=skin.node_tree.nodes;links=skin.node_tree.links;bs=nodes.get('Principled BSDF');bs.inputs['Subsurface Weight'].default_value=.055
coord=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=7;noise.inputs['Detail'].default_value=4;noise.inputs['Roughness'].default_value=.72
links.new(coord.outputs['Generated'],noise.inputs['Vector'])
ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.25;ramp.color_ramp.elements[0].color=(.14,.115,.11,1);ramp.color_ramp.elements[1].position=.72;ramp.color_ramp.elements[1].color=(.32,.215,.20,1)
links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs['Color'],bs.inputs['Base Color'])
pore=nodes.new('ShaderNodeTexNoise');pore.inputs['Scale'].default_value=180;pore.inputs['Detail'].default_value=2;links.new(coord.outputs['Generated'],pore.inputs['Vector'])
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.0025;links.new(pore.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
snout=material('MI_Pig_Muzzle',(.24,.125,.12),.48);snout.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value=.07
for n in [pore,bump]:pass
# Muzzle has its own subtle damp pores.
n=snout.node_tree.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=150
b=snout.node_tree.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.18;b.inputs['Distance'].default_value=.002
snout.node_tree.links.new(n.outputs['Fac'],b.inputs['Height']);snout.node_tree.links.new(b.outputs['Normal'],snout.node_tree.nodes.get('Principled BSDF').inputs['Normal'])
details=material('MI_Pig_HornBristle',(.075,.061,.049),.61)
eye_mat=material('MI_Pig_Eye',(.018,.014,.012),.16)
objects=[]
def mesh(name,verts,faces,mat=skin):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);COLL.objects.link(ob);me.materials.append(mat)
    for p in me.polygons:p.use_smooth=True
    if name.startswith('Folded ear'):
        tag=ob.vertex_groups.new(name='__ear_'+('r' if '-1' in name else 'l'));tag.add(list(range(len(me.vertices))),1,'REPLACE')
    elif name=='Flattened cloven horn toe':
        center=sum((Vector(v) for v in verts),Vector())/len(verts)
        tag=ob.vertex_groups.new(name='__'+('fore' if center.x>0 else 'hind')+'_foot_'+('l' if center.y>0 else 'r'));tag.add(list(range(len(me.vertices))),1,'REPLACE')
    elif name in ['Soft eyelid rim','Subtle mouth lip crease']:
        tag=ob.vertex_groups.new(name='__head');tag.add(list(range(len(me.vertices))),1,'REPLACE')
    objects.append(ob);return ob

def loft(name,stations,segments=32,mat=skin):
    # x,z, transverse radius, vertical radius; circumference joins smoothly.
    verts=[];faces=[]
    for x,z,ry,rz in stations:
        for i in range(segments):
            a=math.tau*i/segments;verts.append((x,ry*math.cos(a),z+rz*math.sin(a)))
    for j in range(len(stations)-1):
        for i in range(segments):a=j*segments+i;b=j*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
    faces.append(tuple(reversed(range(segments))));faces.append(tuple((len(stations)-1)*segments+i for i in range(segments)))
    return mesh(name,verts,faces,mat)

def ellipsoid(name,center,scale,mat=skin,segments=24,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=center)
    ob=bpy.context.object;ob.name=name;ob.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    move_collection(ob);ob.data.materials.append(mat)
    for p in ob.data.polygons:p.use_smooth=True
    if name=='Dew claw':
        tag=ob.vertex_groups.new(name='__'+('fore' if center[0]>0 else 'hind')+'_foot_'+('l' if center[1]>0 else 'r'));tag.add(list(range(len(ob.data.vertices))),1,'REPLACE')
    elif name in ['Small alert eye','Cartilage snout disk','Dark nostril interior']:
        tag=ob.vertex_groups.new(name='__head');tag.add(list(range(len(ob.data.vertices))),1,'REPLACE')
    objects.append(ob);return ob

# The continuous torso/profile is sculpted as lofts, then all anatomical masses are voxel fused.
body=loft('Organic torso',[
(-.66,.67,.055,.10),(-.59,.66,.22,.25),(-.47,.65,.29,.30),(-.28,.65,.325,.315),(-.05,.66,.33,.31),
(.14,.68,.30,.295),(.30,.69,.245,.26),(.44,.71,.18,.21),(.52,.72,.13,.17)])
head=loft('Wedge head and cheek',[(.35,.71,.13,.17),(.48,.72,.185,.205),(.62,.69,.175,.19),(.76,.64,.14,.13),(.90,.60,.11,.09),(.99,.59,.105,.085)])
# Jowls and full hind hams merge into the same skin rather than remaining separate balls.
for side in [-1,1]:
    ellipsoid('Ham muscle',(-.44,side*.205,.56),(.23,.19,.29))
    ellipsoid('Shoulder muscle',(.22,side*.18,.59),(.20,.16,.255))
    ellipsoid('Cheek jowl',(.54,side*.105,.59),(.17,.115,.125))
    # Limb sections follow a real elbow/stifle/hock silhouette, tapering into pasterns.
    for fore,stations in [(True,[(.25,.65,.13),(.16,.48,.095),(.12,.40,.072),(.23,.23,.051),(.28,.14,.046),(.30,.065,.043)]),
                            (False,[(-.45,.65,.14),(-.30,.48,.12),(-.20,.42,.09),(-.36,.27,.065),(-.45,.20,.047),(-.40,.075,.044)])]:
        verts=[];faces=[];seg=20
        for x,z,r in stations:
            for i in range(seg):
                a=i*math.tau/seg;verts.append((x+r*math.cos(a),side*.235+r*.82*math.sin(a),z))
        for j in range(len(stations)-1):
            for i in range(seg):a=j*seg+i;b=j*seg+(i+1)%seg;faces.append((a,b,b+seg,a+seg))
        faces.append(tuple(reversed(range(seg))));faces.append(tuple((len(stations)-1)*seg+i for i in range(seg)))
        mesh(('Fore' if fore else 'Hind')+' leg tissue',verts,faces)
# Join and voxel remesh the skin into a single organic surface, smoothing muscle transitions.
bpy.ops.object.select_all(action='DESELECT')
for ob in objects:ob.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
body.name='Pig anatomical skin'
rem=body.modifiers.new('Unified organic sculpt surface','REMESH');rem.mode='VOXEL';rem.voxel_size=.012;rem.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=rem.name)
smooth=body.modifiers.new('Sculpted muscle blending','SMOOTH');smooth.factor=.7;smooth.iterations=5;bpy.ops.object.modifier_apply(modifier=smooth.name)
body.data.calc_loop_triangles();dec=body.modifiers.new('Anatomy game topology','DECIMATE');dec.ratio=min(1,11500/len(body.data.loop_triangles));bpy.ops.object.modifier_apply(modifier=dec.name)
objects=[body]
# Broad flattened snout disk with physically recessed paired nostrils.
disk=ellipsoid('Cartilage snout disk',(1.003,0,.590),(.045,.123,.087),snout,32,16)
for side in [-1,1]:
    cut=ellipsoid('Nostril cutter',(1.034,side*.055,.611),(.052,.022,.016),details,20,12)
    bpy.context.view_layer.objects.active=disk
    mod=disk.modifiers.new('True recessed nostril','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cut
    bpy.ops.object.modifier_apply(modifier=mod.name);objects.remove(cut);bpy.data.objects.remove(cut,do_unlink=True)
    ellipsoid('Dark nostril interior',(1.009,side*.055,.611),(.012,.017,.012),details,16,8)
# Narrow anatomical lip crease, traced along the actual head surface.
from mathutils.bvhtree import BVHTree
surface=BVHTree.FromPolygons([v.co.copy() for v in body.data.vertices],[list(p.vertices) for p in body.data.polygons])
for side in [-1,1]:
    verts=[];faces=[];segments=6;count=22
    for j in range(count):
        t=j/(count-1);x=.59+.39*t;z=.545+.018*t
        hit=surface.ray_cast(Vector((x,side*.5,z)),Vector((0,-side,0)),1)
        if hit[0] is None:point=Vector((x,side*.10,z));normal=Vector((0,side,0))
        else:point=hit[0]+hit[1]*.0005;normal=hit[1]
        for i in range(segments):
            a=i*math.tau/segments;r=.0019*math.sin(math.pi*(.05+.9*t))
            verts.append(tuple(point+normal*(r*math.cos(a))+Vector((0,0,r*math.sin(a)))))
    for j in range(count-1):
        for i in range(segments):a=j*segments+i;b=j*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
    mesh('Subtle mouth lip crease',verts,faces,details)

# Flexible leaf ears with thickness and an asymmetrical folded tip.
for side in [-1,1]:
    verts=[];faces=[];rows=9;columns=9
    for j in range(rows):
        t=j/(rows-1);width=.075*math.sin(math.pi*(.12+.88*t))+.008
        for i in range(columns):
            u=(i/(columns-1)-.5)*2
            verts.append((.51+u*width+.065*t,side*(.13+.165*t+.02*math.sin(t*math.pi)),.835+.155*t-.11*t**3+.023*(1-u*u)*math.sin(math.pi*t)))
    for j in range(rows-1):
        for i in range(columns-1):a=j*columns+i;faces.append((a,a+1,a+1+columns,a+columns))
    ear=mesh('Folded ear '+str(side),verts,faces,snout)
    bpy.context.view_layer.objects.active=ear;mod=ear.modifiers.new('Ear flesh thickness','SOLIDIFY');mod.thickness=.006;mod.offset=-.5;bpy.ops.object.modifier_apply(modifier=mod.name)
# Small deeply placed eyes and an anatomical raised eyelid rim.
for side in [-1,1]:
    center=Vector((.625,side*.158,.755));ellipsoid('Small alert eye',center,(.021,.009,.017),eye_mat,20,12)
    verts=[];faces=[];seg=24
    for j in range(3):
        radius=1+j*.16
        for i in range(seg):
            a=i*math.tau/seg;verts.append((center.x+.026*radius*math.cos(a),center.y+side*(.006-.004*j),center.z+.020*radius*math.sin(a)))
    for j in range(2):
        for i in range(seg):a=j*seg+i;b=j*seg+(i+1)%seg;faces.append((a,b,b+seg,a+seg))
    mesh('Soft eyelid rim',verts,faces,skin)
# Each foot has two separate weight-bearing horn toes and small rear dewclaws.
for fore in [True,False]:
    x=.315 if fore else -.39
    for side in [-1,1]:
        for toe in [-1,1]:
            verts=[];faces=[];seg=16;cy=side*.235+toe*.023
            for z,rx,ry,shift in [(0,.060,.018,.008),(.012,.073,.021,.004),(.053,.065,.019,-.004),(.075,.046,.016,-.016)]:
                for i in range(seg):
                    a=i*math.tau/seg;verts.append((x+shift+rx*math.cos(a),cy+ry*math.sin(a),z))
            for row in range(3):
                for i in range(seg):a=row*seg+i;b=row*seg+(i+1)%seg;faces.append((a,b,b+seg,a+seg))
            faces.append(tuple(reversed(range(seg))));faces.append(tuple(3*seg+i for i in range(seg)))
            mesh('Flattened cloven horn toe',verts,faces,details)
        for digit in [-1,1]:ellipsoid('Dew claw',(x-.052,side*.235+digit*.042,.119),(.017,.012,.022),details,12,8)
# Fine curled tail, closed tapered tube; no disconnected torus.
verts=[];faces=[];rings=42;segments=8
for j in range(rings):
    t=j/(rings-1);angle=t*math.tau*1.35
    center=Vector((-.65-.12*t,.035+.055*t*math.sin(angle),.79+.075*math.sin(t*math.pi)+.05*t*math.cos(angle)))
    radius=.012*(1-.8*t)
    for i in range(segments):
        a=i*math.tau/segments;verts.append(tuple(center+Vector((0,radius*math.cos(a),radius*math.sin(a)))))
for j in range(rings-1):
    for i in range(segments):a=j*segments+i;b=j*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
faces.append(tuple(reversed(range(segments))));faces.append(tuple((rings-1)*segments+i for i in range(segments)))
mesh('Curled tapered tail',verts,faces,skin)
# Restrained sparse bristles grow directly from skin, not broad alpha cards.
body.data.update();verts=[];faces=[]
candidates=[v for v in body.data.vertices if v.co.z>.60 and abs(v.co.y)>.06 and v.normal.z>-.1 and v.co.x<.5]
for v in random.sample(candidates,min(150,len(candidates))):
    n=v.normal.normalized();p=v.co+n*.001;axis=n.cross(Vector((1,0,0)))
    if axis.length<.01:axis=n.cross(Vector((0,1,0)))
    axis.normalize();other=n.cross(axis);length=random.uniform(.004,.010);r=.0007
    index=len(verts)
    for k in range(3):a=k*math.tau/3;verts.append(tuple(p+(axis*math.cos(a)+other*math.sin(a))*r))
    verts.append(tuple(p+n*length+Vector((-.002,0,0))))
    faces.extend([(index,index+1,index+3),(index+1,index+2,index+3),(index+2,index,index+3)])
mesh('Sparse natural bristles',verts,faces,details)
# Join all visible parts; shared UV atlas is generated at the bake stage.
bpy.ops.object.select_all(action='DESELECT')
for ob in objects:ob.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join();ob=body;ob.name='SK_Pig_Stonebrook_LOD0';ob.data.name=ob.name
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for vertex in ob.data.vertices:
    if vertex.co.x>.57:vertex.co.x=.57+(vertex.co.x-.57)*.8
for p in ob.data.polygons:p.use_smooth=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False) if hasattr(bpy.ops.mesh,'normals_make_consistent') else None
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.003,area_weight=.3);bpy.ops.object.mode_set(mode='OBJECT')
# Own quadruped skeleton; identity root points along +Y, geometry faces +X.
bpy.ops.object.armature_add(enter_editmode=True,location=(0,0,0));arm=bpy.context.object;arm.name='Armature';move_collection(arm)
arm.data.edit_bones.remove(arm.data.edit_bones[0]);bone_defs=[]
def bone(name,head,tail,parent=None):
    b=arm.data.edit_bones.new(name)
    head=Vector(head);tail=Vector(tail)
    if head.x>.57:head.x=.57+(head.x-.57)*.8
    if tail.x>.57:tail.x=.57+(tail.x-.57)*.8
    b.head=head;b.tail=tail;b.roll=0
    if parent:b.parent=arm.data.edit_bones[parent]
    bone_defs.append(name);return b
bone('root',(0,0,0),(0,.1,0))
bone('pelvis',(-.42,0,.67),(-.13,0,.68),'root');bone('spine',(-.13,0,.68),(.15,0,.70),'pelvis');bone('chest',(.15,0,.70),(.40,0,.74),'spine')
bone('neck',(.40,0,.74),(.62,0,.70),'chest');bone('head',(.62,0,.70),(.98,0,.59),'neck');bone('jaw',(.57,0,.56),(.96,0,.55),'head')
for side,label in [(1,'l'),(-1,'r')]:
    bone('ear_'+label,(.50,side*.13,.835),(.57,side*.29,.89),'head')
    bone('fore_upper_'+label,(.25,side*.235,.67),(.12,side*.235,.40),'chest')
    bone('fore_lower_'+label,(.12,side*.235,.40),(.28,side*.235,.14),'fore_upper_'+label)
    bone('fore_foot_'+label,(.28,side*.235,.14),(.38,side*.235,.045),'fore_lower_'+label)
    bone('hind_upper_'+label,(-.43,side*.235,.66),(-.20,side*.235,.42),'pelvis')
    bone('hind_lower_'+label,(-.20,side*.235,.42),(-.45,side*.235,.20),'hind_upper_'+label)
    bone('hind_foot_'+label,(-.45,side*.235,.20),(-.34,side*.235,.045),'hind_lower_'+label)
for i in range(3):bone('tail_%02d'%i,(-.65-.04*i,0,.80),(-.69-.04*i,0,.80),'pelvis' if i==0 else 'tail_%02d'%(i-1))
bpy.ops.object.mode_set(mode='OBJECT');arm.show_in_front=True
# Bone-heat skinning follows the connected anatomical surface, avoiding Euclidean belly webs.
feature_tags={v.index:[ob.vertex_groups[g.group].name[2:] for g in v.groups if ob.vertex_groups[g.group].name.startswith('__') and g.weight>.5] for v in ob.data.vertices}
ob.vertex_groups.clear();arm.data.bones['root'].use_deform=False
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
for name in bone_defs:
    if name not in ob.vertex_groups:ob.vertex_groups.new(name=name)
for v in ob.data.vertices:
    tags=feature_tags[v.index];name=tags[0] if tags else None
    if v.co.x<-.64 and v.co.z>.74:name='tail_%02d'%min(2,max(0,int((-v.co.x-.65)/.04)))
    if name:
        for group in ob.vertex_groups:group.remove([v.index])
        ob.vertex_groups[name].add([v.index],1,'REPLACE')
# Fine bristles are disconnected by design: copy their nearest skin surface's valid heat weights.
from mathutils.kdtree import KDTree
valid=[v for v in ob.data.vertices if any(g.weight>1e-6 for g in v.groups)]
kd=KDTree(len(valid))
for v in valid:kd.insert(v.co,v.index)
kd.balance();unweighted_before_surface_transfer=0
for v in ob.data.vertices:
    if any(g.weight>1e-6 for g in v.groups):continue
    unweighted_before_surface_transfer+=1;_,index,_=kd.find(v.co)
    for g in ob.data.vertices[index].groups:
        if g.weight>1e-6:ob.vertex_groups[g.group].add([v.index],g.weight,'REPLACE')
for v in ob.data.vertices:
    values=sorted([(g.group,g.weight) for g in v.groups if g.weight>1e-6],key=lambda p:-p[1])[:4]
    total=sum(w for _,w in values)
    if total<=0:raise RuntimeError('Unweighted pig vertex '+str(v.index))
    for group in ob.vertex_groups:group.remove([v.index])
    for group,weight in values:ob.vertex_groups[group].add([v.index],weight/total,'REPLACE')
sys.path.insert(0,str(Path(__file__).parent))
from pig_skin import refine_torso_weights
torso_report=refine_torso_weights(ob,arm)
mod=next(m for m in ob.modifiers if m.type=='ARMATURE');mod.object=arm
for pbone in arm.pose.bones:pbone.rotation_mode='QUATERNION'
from pig_actions import create_pig_actions
actions=create_pig_actions(arm,scene)
# Neutral studio preview, with posed frames saved before source export.
stage=bpy.data.collections.new('Preview_Stage');scene.collection.children.link(stage)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.003))
floor=bpy.context.object;floor.name='Preview ground';floor.data.materials.append(material('Preview ground material',(.15,.17,.19),.85))
for c in list(floor.users_collection):c.objects.unlink(floor)
stage.objects.link(floor)
world=bpy.data.worlds.new('PigStudio');scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.24,.28,.32,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
for pos,power,color,size in [((3,-3,4),450,(1,.86,.75),3),((-2,-2,2),220,(.65,.77,1),2),((0,3,3),350,(1,.80,.65),2)]:
    data=bpy.data.lights.new('Pig area','AREA');data.energy=power;data.color=color;data.size=size;light=bpy.data.objects.new('Pig area',data);stage.objects.link(light);light.location=pos;light.rotation_euler=(Vector((0,0,.5))-light.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Pig portrait');cam=bpy.data.objects.new('Pig portrait',camdata);stage.objects.link(cam);cam.location=(2.8,-3.5,1.65);cam.rotation_euler=(Vector((.1,0,.48))-cam.location).to_track_quat('-Z','Y').to_euler();camdata.lens=65;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
ob.data.calc_loop_triangles()
report={'schema':'dink-pig-source/1','bone_count':len(arm.data.bones),'bones':[{'name':b.name,'parent':b.parent.name if b.parent else None,'matrix_local':[list(row) for row in b.matrix_local]} for b in arm.data.bones],
        'torso_mask':torso_report,'skinning':'Bone heat on connected anatomy; rigid eye/ear/hoof masks; nearest-surface transfer for disconnected fine bristles',
        'surface_transfer_vertices':unweighted_before_surface_transfer,'unweighted_vertices':sum(not any(g.weight>1e-6 for g in v.groups) for v in ob.data.vertices),
        'max_influences':max(sum(g.weight>1e-6 for g in v.groups) for v in ob.data.vertices),
        'triangles_before_lods':len(ob.data.loop_triangles),'materials':[m.name for m in ob.data.materials],'forward':'+X','up':'+Z','units':'metres','actions':actions,
        'provenance':'Original project-authored anatomy, rig, procedural materials and actions. Anatomy reference only: USU-hosted South Dakota State University livestock judging manual, External Parts of Swine. No reference mesh or texture downloads.'}
(ROOT/'pig_rig_report.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Pig_Working.blend'))
for name,frame in [('Pig_Idle',1),('Pig_Walk',9),('Pig_Run',5),('Pig_Feed',7)]:
    if os.environ.get('PIG_PREVIEW_ACTIONS') and name not in os.environ['PIG_PREVIEW_ACTIONS'].split(','):continue
    arm.animation_data.action=bpy.data.actions[name];scene.frame_set(frame);scene.render.filepath=str(ROOT/('preview_'+name.lower()+'.png'));bpy.ops.render.render(write_still=True)
print('PIG SOURCE READY',len(ob.data.loop_triangles),'triangles',len(arm.data.bones),'bones',flush=True)
