import bpy,bmesh,math,json,hashlib,os,sys
from pathlib import Path
from mathutils import Vector
Q=Path(__file__).resolve().parent;OUT=Q/'PhotorealBrokenBarrelV3_Refinement.blend'
PARENT=Path('<HOME>/Work/DinkPhotorealBrokenBarrelSourceDelivery/DinkRemasterUE/SourceAssets/Art/Stonebrook/Refinements/PhotorealBarrelV1/PhotorealBarrelV1_Source.blend')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(PARENT)=='2cab573f8f40a99a2b513a454b8d0e006e73353171e3a25bc94254580cf9c0f7'
bpy.ops.wm.open_mainfile(filepath=str(OUT),load_ui=False,use_scripts=False);bpy.context.preferences.filepaths.save_version=0
c=bpy.data.collections['V3_Editable_SplitStaves_SharedPBR'];parts=list(c.objects)
def bounds(obs):
 vs=[o.matrix_world@v.co for o in obs for v in o.data.vertices];lo=[min(v[k]for v in vs)for k in range(3)];hi=[max(v[k]for v in vs)for k in range(3)];return {'min_m':lo,'max_m':hi,'dimensions_m':[hi[k]-lo[k]for k in range(3)]}
meshproof=[]
for o in parts:
 bm=bmesh.new();bm.from_mesh(o.data);v=bm.calc_volume(signed=True);bad=sum(not e.is_manifold for e in bm.edges);bm.free();o.data.calc_loop_triangles()
 zero=sum((o.data.vertices[t.vertices[1]].co-o.data.vertices[t.vertices[0]].co).cross(o.data.vertices[t.vertices[2]].co-o.data.vertices[t.vertices[0]].co).length<1e-12 for t in o.data.loop_triangles)
 assert not bad and not zero and math.isfinite(v) and v>1e-12,(o.name,bad,zero,v)
 meshproof.append({'name':o.name,'signed_volume_m3':v,'nonmanifold_edges':bad,'zero_area_triangles':zero})
broken=bounds(parts)
with bpy.data.libraries.load(str(PARENT),link=False)as(a,b):b.objects=['SM_Barrel_Oak_01']
intact=b.objects[0];assert intact
context=bpy.data.collections.new('REVIEW_ONLY_MetricIntactVsBroken');bpy.context.scene.collection.children.link(context);context.objects.link(intact);intact.hide_render=False;intact.hide_viewport=False;intact.hide_set(False)
bpy.context.view_layer.update();intact_dimensions=bounds([intact]);intact.location.x=-.98
for o in parts:
 n=o.copy();n.name='CONTEXT_'+o.name;context.objects.link(n);n.location.x+=.72
c.hide_render=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=2;scene.cycles.samples=32
cam=scene.camera;old=(cam.location.copy(),cam.rotation_euler.copy(),cam.data.ortho_scale);cam.location=(1.9,-3.3,2.2);cam.rotation_euler=(Vector((-.10,0,.35))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=3.2
scene.render.filepath=str(Q/'Renders/05_intact_vs_broken_real_scale.png');bpy.ops.render.render(write_still=True)
context.hide_render=True;context.hide_viewport=True;c.hide_render=False
cam.location,cam.rotation_euler,cam.data.ortho_scale=old
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
r={'reopened_candidate_checks':meshproof,'broken_real_dimensions':broken,'parent_intact_dimensions':intact_dimensions,'intact_parent_sha256':sha(PARENT),'candidate_sha256':sha(OUT),'metric_context':'Original intact real-scale geometry on left; candidate pile on right. Translated horizontally only; no rescaling. Scene metres scale1.','private_comparison_only':True,'native_game_scale_unproven':True,'no_billboard_dimensions_inherited':True,'CPU_affinity':list(os.sched_getaffinity(0))}
(Q/'METRIC_CONTEXT_AND_REOPEN_CHECK.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'broken':broken,'intact':intact_dimensions,'verified':len(parts)}));sys.stdout.flush();os._exit(0)
