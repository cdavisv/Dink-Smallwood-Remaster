"""Isolated editable V3 study, shared materials unchanged; CPU-only, no export."""
import bpy,bmesh,numpy as np,math,json,hashlib,os,sys,traceback
from pathlib import Path
from mathutils import Vector,Matrix
Q=Path(__file__).resolve().parent
SRC=Path('<HOME>/Work/DinkQA/PhotorealBrokenBarrelExportV1/SourceNodesAlternativeV2/PhotorealBrokenBarrelV2_MultiNodeLODs.blend')
PIN='9d97fee5c8aa9cb923c85b001b59c74f54e77320f344d83a8a8d088f91651151'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def material_signature(m):
 return {'nodes':sorted((n.name,n.bl_idname,[(i.name,str(i.default_value[:])if hasattr(i.default_value,'__len__')else str(i.default_value))for i in n.inputs if hasattr(i,'default_value')],n.image.name if n.type=='TEX_IMAGE'and n.image else None)for n in m.node_tree.nodes),'links':sorted((l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name)for l in m.node_tree.links)}
def main():
 assert sha(SRC)==PIN
 bpy.ops.wm.open_mainfile(filepath=str(SRC),load_ui=False,use_scripts=False)
 bpy.context.preferences.filepaths.save_version=0
 mats={m.name:material_signature(m)for m in bpy.data.materials if not m.name.startswith('REVIEW_ONLY')}
 images={i.name:hashlib.sha256(bytes(i.packed_file.data)).hexdigest()for i in bpy.data.images if i.packed_file}
 original=bpy.data.collections['SM_Barrel_Broken_SourceStudy'];original.hide_viewport=False;original.hide_render=True
 for c in bpy.data.collections:
  if c.name.startswith('COMBINE_IMPORT_'):c.hide_render=True;c.hide_viewport=True
 candidate=bpy.data.collections.new('V3_Editable_SplitStaves_SharedPBR');bpy.context.scene.collection.children.link(candidate)
 pieces=[]
 for o in sorted(original.objects,key=lambda o:o.name):
  n=o.copy();n.data=o.data.copy();n.name='V3_'+o.name;candidate.objects.link(n);n.hide_set(False);n.hide_render=False;pieces.append(n)
 bpy.context.view_layer.update()
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=2
 scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
 (Q/'Renders').mkdir(exist_ok=True)
 # Matched baseline uses source pieces (same LOD0 geometry) and exactly this rig.
 candidate.hide_render=True;original.hide_render=False
 scene.render.filepath=str(Q/'Renders/01_before_matched.png');bpy.ops.render.render(write_still=True)
 original.hide_render=True;candidate.hide_render=False
 split_report=[]
 for index in [2,4,13,16]:
  o=next(x for x in pieces if x.name=='V3_Broken_coopered_stave_%02d'%index)
  coords=np.array([v.co[:]for v in o.data.vertices]);center=coords.mean(axis=0);vals,vecs=np.linalg.eigh(np.cov((coords-center).T));along=Vector(vecs[:,2]);side=Vector(vecs[:,1]);thin=Vector(vecs[:,0]);mid=Vector(center)
  # Keep the visible fracture longitudinal, not a cross-cut. Two closed halves with shared wood UV.
  old=o.data.copy();halves=[]
  for sign in [-1,1]:
   me=old.copy();bm=bmesh.new();bm.from_mesh(me)
   bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=mid+side*.008,plane_no=side,clear_outer=sign<0,clear_inner=sign>0)
   boundary=[e for e in bm.edges if e.is_boundary]
   boundaryverts={v for e in boundary for v in e.verts}
   # Shared irregular fibre boundary on both halves, then a real 7mm opening.
   for v in boundaryverts:
    t=(v.co-mid).dot(along);v.co+=side*(.0025*math.sin(t*65+index)+.0012*math.sin(t*151))
   caps=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)['faces'];uv=bm.loops.layers.uv.active
   for f in caps:
    f.material_index=0;f.smooth=False
    for loop in f.loops:
     d=loop.vert.co-mid;loop[uv].uv=(d.dot(thin)/2+.27,d.dot(along)/2+.31)
   bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
   n=bpy.data.objects.new(o.name+('_Split_A'if sign<0 else '_Split_B'),me);candidate.objects.link(n);n.matrix_world=o.matrix_world.copy();n.location+=side*(sign*.0035)+along*(.009 if sign>0 else 0)
   halves.append(n)
  pieces.remove(o);bpy.data.objects.remove(o,do_unlink=True);pieces+=halves
  split_report.append({'source_stave':index,'physical_gap_m':.007,'longitudinal_stagger_m':.009,'halves':[n.name for n in halves]})
 # Small slivers at broken stave tips; closed tapered solids, not alpha cards/private bakes.
 for j,index in enumerate([2,4,13,16]):
  o=next(x for x in pieces if x.name=='V3_Broken_coopered_stave_%02d_Split_B'%index)
  world=[o.matrix_world@v.co for v in o.data.vertices];coords=np.array([v[:]for v in world]);mid=Vector(coords.mean(axis=0));vals,vecs=np.linalg.eigh(np.cov((coords-coords.mean(axis=0)).T));along=Vector(vecs[:,2]);side=Vector(vecs[:,1]);normal=Vector(vecs[:,0]);along*=1 if along.dot(mid)>0 else -1
  tip=max(world,key=lambda v:v.dot(along));origin=tip-along*.018+normal*.003
  length=.039+j*.005;width=.0035+j*.0005;thick=.0025
  vs=[origin-side*width,origin+side*width,origin+normal*thick-side*width,origin+normal*thick+side*width,origin+along*length+side*(width*.3)+normal*(.004+j*.001)]
  faces=[(0,2,3,1),(0,1,4),(1,3,4),(3,2,4),(2,0,4)]
  me=bpy.data.meshes.new('Lengthwise_fibre_%02d'%j);me.from_pydata(vs,[],faces);me.materials.append(bpy.data.materials['MI_Shared_OakLonggrain2m']);me.materials.append(bpy.data.materials['MI_Shared_OakEndgrain2m']);uv=me.uv_layers.new(name='UVMap')
  for p in me.polygons:
   p.material_index=1 if p.index==0 else 0
   for li in p.loop_indices:
    d=me.vertices[me.loops[li].vertex_index].co-origin;uv.data[li].uv=(d.dot(side)/2+.27,d.dot(along)/2+.31)
  bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
  n=bpy.data.objects.new('V3_Fracture_fibre_%02d'%j,me);candidate.objects.link(n);pieces.append(n)
 # Unequal overlaps keep the original star silhouette but reduce the evenly spaced fan.
 for index,delta,yaw in [(3,(.026,-.012,.008),-.055),(9,(-.016,.014,.003),.045),(12,(.018,.018,.006),-.035)]:
  o=next(x for x in pieces if x.name=='V3_Broken_coopered_stave_%02d'%index)
  center=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices);rot=Matrix.Rotation(yaw,3,'Z')
  for v in o.data.vertices:v.co=center+rot@(v.co-center)
  o.location+=Vector(delta)
 # Forge strap tip bends only: retain original strap thickness/material/irregular arcs.
 hoop=next(x for x in pieces if x.name=='V3_Opened_forged_hoop_03')
 ys=[v.co.y for v in hoop.data.vertices];end=max(ys)
 for v in hoop.data.vertices:
  t=max(0,(v.co.y-(end-.075))/.075);v.co.z+=.018*t*t
 # Evaluate transforms before ground measurements, including newly split objects.
 bpy.context.view_layer.update()
 # Keep ground contact nonnegative after local additions; no dropping pieces onto lower boards.
 for o in pieces:
  lowest=min((o.matrix_world@v.co).z for v in o.data.vertices)
  if lowest<.001:o.location.z+=.001-lowest
 bpy.context.view_layer.update()
 for m in bpy.data.materials:
  if m.name in mats:assert material_signature(m)==mats[m.name],m.name
 assert images=={i.name:hashlib.sha256(bytes(i.packed_file.data)).hexdigest()for i in bpy.data.images if i.packed_file}
 scene.render.filepath=str(Q/'Renders/02_after_matched.png');bpy.ops.render.render(write_still=True)
 camera=scene.camera;saved=(camera.location.copy(),camera.rotation_euler.copy(),camera.data.ortho_scale)
 def aim(p):camera.rotation_euler=(Vector(p)-camera.location).to_track_quat('-Z','Y').to_euler()
 camera.location=(1.05,-1.4,1.6);aim((0,0,.12));camera.data.ortho_scale=1.38;scene.render.filepath=str(Q/'Renders/03_fracture_detail.png');bpy.ops.render.render(write_still=True)
 camera.location=(.6,-.85,2.8);aim((0,0,.10));camera.data.ortho_scale=1.85;scene.render.filepath=str(Q/'Renders/04_pile_overview.png');bpy.ops.render.render(write_still=True)
 camera.location,camera.rotation_euler,camera.data.ortho_scale=saved
 # New study contains original and preferredLOD archive hidden. Refinement is editable only LOD0.
 original.hide_viewport=True;candidate.hide_viewport=False
 bpy.ops.object.select_all(action='DESELECT')
 for o in pieces:o.select_set(True)
 bpy.context.view_layer.objects.active=pieces[0]
 out=Q/'PhotorealBrokenBarrelV3_Refinement.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out))
 metrics=[]
 for o in pieces:
  bm=bmesh.new();bm.from_mesh(o.data);bad=sum(not e.is_manifold for e in bm.edges);bm.free();o.data.calc_loop_triangles()
  metrics.append({'object':o.name,'triangles':len(o.data.loop_triangles),'nonmanifold_edges':bad,'materials':[m.name for m in o.data.materials]})
 r={'source':str(SRC),'source_sha256':PIN,'source_after_sha256':sha(SRC),'candidate_sha256':sha(out),'reference':'original173/6 barel-06.bmp.png','changes':split_report,'refined_objects':len(pieces),'triangles':sum(x['triangles']for x in metrics),'geometry':metrics,'shared_material_graphs_unchanged':True,'packed_image_sha256':images,'CPU_affinity':list(os.sched_getaffinity(0)),'render_threads':scene.render.threads,'cycles_device':scene.cycles.device,'native_exported':False,'runtime_activated':False,'limitations':['RefinementLOD0 only; preferred V2 LOD1/2 remain historical hidden comparison, not regenerated V3 LODs','No native import/TBN/collision/navigation/cook/gamecamera proof','Original generic shared-tiling UV/missingUCX findings remain; no invented collider or private bake']}
 (Q/'BUILD_RECEIPT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'triangles':r['triangles'],'objects':len(pieces),'bad_edges':sum(x['nonmanifold_edges']for x in metrics)}));sys.stdout.flush();os._exit(0)
try:main()
except BaseException:traceback.print_exc();sys.stderr.flush();os._exit(1)
