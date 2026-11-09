import bpy,json,hashlib
import OpenImageIO
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parents[1];args=__import__('sys').argv;assert '--out'in args,'Specify --out outside frozen packet';O=Path(args[args.index('--out')+1]).resolve();assert not O.is_relative_to(P);O.mkdir(parents=True,exist_ok=True);authority=P/'Evidence/Authority/original35_pose_authority.json';poses=json.loads(authority.read_text())['pose_authority'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source=P/'Source/SK_Dink_Trousers_MetricArtV32_Context.blend';jobs=[('source_metric_detail',source,'rest','detail')];rows=[]
def depth(b):
 d=0
 while b.parent:d+=1;b=b.parent
 return d
for label,file,pose,framing in jobs:
 pin=sha(file);target=next(x['bone_world_matrices']for x in poses if x['pose']==pose);bpy.ops.wm.open_mainfile(filepath=str(file));s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_percentage=100
 for ob in list(s.objects):
  if ob.type in ['LIGHT','CAMERA']:bpy.data.objects.remove(ob,do_unlink=True)
 s.world=bpy.data.worlds.new('Matched Cloth Control World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.1,.12,.14,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.65
 for n,pos,power in [('Key',(3,-4,4),650),('Fill',(-3,-2,3),300),('Rim',(0,3,4),500)]:
  l=bpy.data.lights.new(n,'AREA');l.energy=power;l.size=3;o=bpy.data.objects.new(n,l);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
 cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO'
 if framing=='detail':pos=(.01,-4,1.5);look=(.01,-.16,.90);scale=.10;s.render.resolution_x=s.render.resolution_y=800
 else:pos=(3,-4,5);look=(0,0,.95);scale=3.8;s.render.resolution_x=900;s.render.resolution_y=1100
 cam.location=pos;cam.rotation_euler=(Vector(look)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;arm=bpy.data.objects['Armature'];arm.data.pose_position='POSE';arm.animation_data_create();arm.animation_data.action=None
 for track in arm.animation_data.nla_tracks:track.mute=True
 for b in arm.pose.bones:b.matrix_basis=Matrix.Identity(4)
 bpy.context.view_layer.update()
 for b in sorted(arm.pose.bones,key=depth):b.matrix=arm.matrix_world.inverted()@Matrix(target[b.name]);bpy.context.view_layer.update()
 ev=arm.evaluated_get(bpy.context.evaluated_depsgraph_get());delta=max(abs(a-b)for bone in ev.pose.bones for aa,bb in zip(ev.matrix_world@bone.matrix,target[bone.name])for a,b in zip(aa,bb));assert delta<1e-5;path=O/(label+'.png');s.render.filepath=str(path);bpy.ops.render.render(write_still=True);row={'label':label,'source':str(file),'source_sha256':pin,'pose':pose,'actual89_max_delta':delta,'framing':framing,'camera':list(pos),'look_at':list(look),'ortho_scale':scale,'resolution':[s.render.resolution_x,s.render.resolution_y],'material':bpy.data.objects['NEW_Dink_Trousers_LOD0'].data.materials[0].name,'image':str(path),'image_sha256':sha(path)};rows.append(row);(O/'receipt.json').write_text(json.dumps({'scope':'Source-only material fidelity controls, NOT native/game runtime screenshots or motion acceptance. Exact selected V19 geometry and original optics. Game framing matches render_baked269 camera/scale/resolution.','authority_sha256':sha(authority),'views':rows},indent=2)+'\n');assert sha(file)==pin;print('CLOTH_CONTROL_VIEW',label,flush=True)
