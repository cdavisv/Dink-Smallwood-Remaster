"""Five rigid-placement changes only. Geometry/material/UV/scale remain exact V4."""
import bpy,math,json,hashlib,struct,os,sys,traceback
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
Q=Path(__file__).resolve().parent;BASE=Path('/home/davisc/Work/DinkQA/PhotorealBrokenBarrelCurvatureV4');SRC=BASE/'PhotorealBrokenBarrelV4_CurvedSource.blend';PIN='b2aaaab79a101534b1f440aafa4463b76fce3f954e399d732e46417199fd5a26'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def geometry(o):
 me=o.data;h=hashlib.sha256()
 for v in me.vertices:h.update(struct.pack('<3f',*v.co))
 for p in me.polygons:h.update(struct.pack('<ii?',len(p.vertices),p.material_index,p.use_smooth));h.update(struct.pack('<'+'i'*len(p.vertices),*p.vertices))
 for layer in me.uv_layers:
  h.update(layer.name.encode())
  for d in layer.data:h.update(struct.pack('<2f',*d.uv))
 for n in me.corner_normals:h.update(struct.pack('<3f',*n.vector))
 h.update('|'.join(m.name for m in me.materials).encode());return h.hexdigest()
def data(o):
 me=o.data;me.calc_loop_triangles();return([o.matrix_world@v.co for v in me.vertices],[tuple(t.vertices)for t in me.loop_triangles])
def tree(o):return BVHTree.FromPolygons(*data(o),all_triangles=True,epsilon=0.0)
def samples(o):
 vs,ts=data(o);return vs+[(vs[a]+vs[b]+vs[c])/3 for a,b,c in ts]
def inside(p,t):
 direction=Vector((.927,.311,.203)).normalized();origin=p.copy();hits=0
 for i in range(128):
  hit=t.ray_cast(origin,direction,5)
  if hit[0]is None:return hits%2==1
  if hit[3]<1e-7:return True
  hits+=1;origin=hit[0]+direction*.000001
 raise RuntimeError('point-containment ray did not terminate')
def collides(o,others):
 t=tree(o);vs,_=data(o);pairs=[]
 for other in others:
  u=tree(other);ov=t.overlap(u)
  if ov:pairs.append({'object':other.name,'surface_triangle_pairs':len(ov)});continue
  vs2,_=data(other)
  if inside(vs[0],u)or inside(vs2[0],t):pairs.append({'object':other.name,'contained_volume':True})
 return pairs

def main():
 assert sha(SRC)==PIN
 frozen=json.loads((BASE/'READY.json').read_bytes());beforepins={n:sha(BASE/n)for n in frozen['files_sha256']};assert beforepins==frozen['files_sha256']
 bpy.ops.wm.open_mainfile(filepath=str(SRC),load_ui=False,use_scripts=False);bpy.context.preferences.filepaths.save_version=0
 c=bpy.data.collections['V4_CooperedFragments_Editable'];obs=list(c.objects);bpy.context.view_layer.update()
 beforegeo={o.name:geometry(o)for o in obs};beforepose={o.name:{'location':list(o.location),'rotation_euler':list(o.rotation_euler),'scale':list(o.scale),'matrix_world':[list(row)for row in o.matrix_world]}for o in obs}
 # This dependency-closed subset contains both upper staves and the small head fragments resting on them.
 moves={
 'V4_Curved_coopered_stave_01':(-.060,-.060,30),
 'V4_Curved_coopered_stave_07':(.100,-.080,23),
 'V4_Curved_coopered_stave_08':(.010,-.050,-62),
 'V4_Split_head_board_01':(-.025,-.110,-29),
 'V4_Split_head_board_02':(.050,-.085,37)}
 baseline=json.loads((Q/'BASELINE_CONTACTS.json').read_bytes());changed=set(moves)
 for row in baseline:
  if row['object']not in changed:assert not(changed&set(row['supports_below_within_8mm'])),row['object']
 fixed=[o for o in obs if o.name not in changed];placed=fixed.copy();reports=[]
 for name,(dx,dy,degrees)in moves.items():
  o=bpy.data.objects[name];old=o.rotation_euler.to_matrix();o.rotation_euler=(Matrix.Rotation(math.radians(degrees),3,'Z')@old).to_euler();o.location.x+=dx;o.location.y+=dy;o.location.z=0
  bpy.context.view_layer.update();vs,ts=data(o);floor=.001-min(v.z for v in vs);lift=floor
  supportvs=[];supportts=[]
  for other in placed:
   a,b=data(other);off=len(supportvs);supportvs+=a;supportts+=[tuple(off+i for i in t)for t in b]
  st=BVHTree.FromPolygons(supportvs,supportts,all_triangles=True,epsilon=0.0);nt=tree(o)
  # Both vertex sets and actual triangle centres constrain height, not just a guessed bounding box.
  for v in samples(o):
   hit=st.ray_cast(Vector((v.x,v.y,2)),Vector((0,0,-1)),4)
   if hit[0]is not None:lift=max(lift,hit[0].z+.0015-v.z)
  for v in supportvs:
   hit=nt.ray_cast(Vector((v.x,v.y,-2)),Vector((0,0,1)),4)
   if hit[0]is not None:lift=max(lift,v.z+.0015-hit[0].z)
  o.location.z=lift;bpy.context.view_layer.update();extra=0;bad=collides(o,placed)
  # Resolve residual triangle-edge crossings, keeping only the minimal upward correction.
  while bad and extra<.010:
   extra+=.00025;o.location.z=lift+extra;bpy.context.view_layer.update();bad=collides(o,placed)
  assert not bad,('unresolved moved-piece intersection',name,bad)
  mindistance=min(v.z for v in data(o)[0]);support='review floor';point_from=None;point_to=None
  for v in samples(o):
   hit=st.find_nearest(v)
   if hit[0]is not None and hit[3]<mindistance:mindistance=hit[3];support='existing mesh triangles';point_from=list(v);point_to=list(hit[0])
  assert 0<=mindistance<=.005,('unsupported/floating placement',name,mindistance)
  reports.append({'object':name,'delta_xy_m':[dx,dy],'delta_world_yaw_degrees':degrees,'new_z_m':o.location.z,'residual_clearance_lift_m':extra,'actual_surface_intersections_with_previously_placed':0,'contained_volume_pairs':0,'nearest_actual_surface_gap_m':mindistance,'support':support,'support_point_on_moved_surface':point_from,'nearest_support_surface_point':point_to})
  placed.append(o)
 # Recheck every changed pair after the later pieces are placed.
 finalpairs={name:collides(bpy.data.objects[name],[o for o in obs if o.name!=name])for name in moves};assert all(not v for v in finalpairs.values()),finalpairs
 bpy.context.view_layer.update();aftergeo={o.name:geometry(o)for o in obs};assert aftergeo==beforegeo
 for o in obs:
  assert list(o.scale)==beforepose[o.name]['scale']
  if o.name not in changed:assert [list(row)for row in o.matrix_world]==beforepose[o.name]['matrix_world']
 allv=[o.matrix_world@v.co for o in obs for v in o.data.vertices];lo=[min(v[k]for v in allv)for k in range(3)];hi=[max(v[k]for v in allv)for k in range(3)];size=[hi[k]-lo[k]for k in range(3)]
 assert lo[2]>=0 and size[2]<=.230,('height beyond low-pile scope',size)
 c.name='V4_AsymmetricRigidVariant_Editable'
 # The inherited hidden metric collection depicts frozen V4, not this variant.
 if bpy.data.collections.get('REVIEW_ONLY_V4_IntactVsBroken'):bpy.data.collections['REVIEW_ONLY_V4_IntactVsBroken'].name='ARCHIVE_FrozenV4Metric_NotVariant'
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.render.threads_mode='FIXED';scene.render.threads=2
 out=Q/'PhotorealBrokenBarrelV4_AsymmetricComposition.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out));(Q/'Renders').mkdir(exist_ok=True)
 scene.render.filepath=str(Q/'Renders/02_asymmetric_matched.png');bpy.ops.render.render(write_still=True)
 cam=scene.camera;saved=(cam.location.copy(),cam.rotation_euler.copy(),cam.data.ortho_scale);cam.location=(1.4,-1.8,.8);cam.rotation_euler=(Vector((0,0,.1))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.55;scene.render.filepath=str(Q/'Renders/03_asymmetric_low_detail.png');bpy.ops.render.render(write_still=True)
 cam.location,cam.rotation_euler,cam.data.ortho_scale=saved;bpy.ops.wm.save_as_mainfile(filepath=str(out))
 assert {n:sha(BASE/n)for n in beforepins}==beforepins
 r={'source_v4_sha256':PIN,'variant_sha256':sha(out),'source_frozen_files_unchanged':True,'geometry_UV_local_normals_material_slots_exact_all25':True,'geometry_fingerprints':beforegeo,'object_scales_exact_all25':True,'rigid_changes':reports,'untouched_object_matrices_exact':20,'bounds':{'min_m':lo,'max_m':hi,'size_m':size},'final_changed_piece_surface_intersections':finalpairs,'unchanged_support_graph_preserved':True,'contact_scope':'Moved pieces vs all others tested with actual triangle-BVH intersections plus volume-containment rays; sampled actual surface gap <=5mm. Unchanged20 use exact original geometry/matrices/support partners; no full baseline collision certification or dynamic simulation claim.','before_transforms':{n:beforepose[n]for n in moves},'after_transforms':{n:{'location':list(bpy.data.objects[n].location),'rotation_euler':list(bpy.data.objects[n].rotation_euler),'scale':list(bpy.data.objects[n].scale)}for n in moves},'CPU_affinity':list(os.sched_getaffinity(0)),'threads':2,'device':'CPU','export_native_runtime':False}
 (Q/'VARIANT_RECEIPT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'PASS':True,'size_m':size,'changes':len(moves)}));sys.stdout.flush();os._exit(0)
try:main()
except BaseException:traceback.print_exc();sys.stderr.flush();os._exit(1)
