"""Render unrelated metric bark panels and broadleaf trim coupons, CPU2threads."""
import bpy,math,os,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parents[1];bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
with bpy.data.libraries.load(str(P/'SharedThornBroadleaf_LibraryCandidate.blend'),link=False) as (f,t):t.materials=['MI_Shared_ThornBark2m','MI_Shared_BroadleafTrimV1']
bark=bpy.data.materials['MI_Shared_ThornBark2m'];leaf=bpy.data.materials['MI_Shared_BroadleafTrimV1'];s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;groups={'bark':[],'leaf':[]};metrics=[]
for side,x in [(2,-2.2),(4,1.1)]:
 bpy.ops.mesh.primitive_plane_add(size=side,location=(x,0,side/2));o=bpy.context.object;o.name='QA_Bark_%dm'%side;o.rotation_euler[0]=math.pi/2;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);o.data.materials.append(bark)
 for uv in o.data.uv_layers[0].data:uv.uv*=side/2
 groups['bark'].append(o);metrics.append({'object':o.name,'dimensions_m':[side,side],'uv_repeats':[side/2,side/2],'material':bark.name})
# Differing generic broadleaf specimen geometries share one trim; no per-specimen texture.
for k in range(6):
 length=.12 if k<3 else .18;pos=Vector(((k%3-.9)*.15,0,(k//3)*.22));width=length*(.23+.045*(k%3));verts=[pos+Vector((0,0,0)),pos+Vector((-width,0,length*.45)),pos+Vector((0,0,length)),pos+Vector((width,0,length*.45)),pos+Vector((0,-.01,length*.48))];faces=[(0,1,4),(1,2,4),(2,3,4),(3,0,4)];me=bpy.data.meshes.new('GenericBlade');me.from_pydata(verts,[],faces);me.materials.append(leaf);uv=me.uv_layers.new();coords=[(.5,0),(0,.45),(.5,1),(1,.45),(.5,.48)]
 for p in me.polygons:
  p.use_smooth=True
  for li in p.loop_indices:uv.data[li].uv=coords[me.loops[li].vertex_index]
 o=bpy.data.objects.new('QA_BroadleafSpecimen_%02d'%k,me);s.collection.objects.link(o);groups['leaf'].append(o);metrics.append({'object':o.name,'blade_length_m':length,'uv':[0,1],'material':leaf.name,'nominal_trim_length_m':.12,'leaf_variation_stretches_trim':k>=3})
s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.28,.32,.38,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.65
lights=[]
for loc,power,size in [((2,-4,6),1500,4),((-3,-2,3),800,3)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.size=size;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler();lights.append(o)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';s.camera=cam;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=24;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=1000;s.render.resolution_y=700;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX';bpy.context.preferences.filepaths.save_version=0;bpy.context.preferences.filepaths.file_preview_type='NONE'
for group in ['bark','leaf']:
 for name,obs in groups.items():
  for ob in obs:ob.hide_render=name!=group
 if group=='bark':cam.location=(0,-10,3.3);target=Vector((0,0,1.9));cam.data.ortho_scale=7.0
 else:
  cam.location=(.1,-1.4,.55);target=Vector((.02,0,.2));cam.data.ortho_scale=.57
  for o in lights:o.data.energy*=.04;o.location*=.18
 cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(P/'Review'/('generic_'+group+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'GenericReuse.blend'));(P/'ReuseMetrics.json').write_text(json.dumps(metrics,indent=2));print('GENERIC_REUSE_COMPLETE',flush=True);os._exit(0)
