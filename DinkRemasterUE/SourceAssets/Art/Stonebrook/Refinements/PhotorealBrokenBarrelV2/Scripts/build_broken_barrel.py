"""Off-tree source-only broken barrel study. No FBX/Unreal export or collision."""
import bpy,bmesh,math,json,hashlib,os,sys,traceback,argparse
from pathlib import Path
from mathutils import Vector,Matrix
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
PROJECT=args.project_root.resolve();Q=args.output.resolve()
if not (PROJECT/'DinkRemaster.uproject').is_file():raise ValueError('Exact project root required')
if Q.exists() or Q==PROJECT or Q.is_relative_to(PROJECT) or PROJECT.is_relative_to(Q):raise ValueError('New disposable output outside project required')
SRC=PROJECT/'SourceAssets/Art/Stonebrook/Refinements/PhotorealBarrelV1/PhotorealBarrelV1_Source.blend'
LIBRARY=PROJECT/'SourceAssets/Art/SharedMaterials/OakLime2mV1/Shared2m_LibraryCandidate.blend'
for p,expected in [(SRC,'b0983eeb9eb6fdbbc4ea14d5b6528db7f9817530fa07b81f96cc40eb1b569350'),(LIBRARY,'561e921cd922cf143a834eda87038e2600c737bbdca58d81c7caeaafa6e54a2e')]:
 if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise ValueError('Hydrate exact tracked parent/library LFS objects')
Q.mkdir(parents=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 bpy.ops.wm.open_mainfile(filepath=str(SRC),load_ui=False,use_scripts=False);bpy.context.preferences.filepaths.save_version=0
 source=bpy.data.objects['SM_Barrel_Oak_01'];source_pin=sha(SRC);me=source.data.copy();mats=list(me.materials)
 # Keep the accepted editable materials, their packed oak image and corner attributes.
 for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
 c=bpy.data.collections.new('SM_Barrel_Broken_SourceStudy');bpy.context.scene.collection.children.link(c)
 intact=bpy.data.objects.new('Accepted_Intact_Comparison',me.copy());c.objects.link(intact);intact.location=(0,0,0)
 working=bpy.data.objects.new('Source_components',me);c.objects.link(working);working.select_set(True);bpy.context.view_layer.objects.active=working
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.separate(type='LOOSE');bpy.ops.object.mode_set(mode='OBJECT')
 parts=list(bpy.context.selected_objects);staves=sorted([o for o in parts if len(o.data.vertices)==256],key=lambda o:math.atan2(sum(v.co.y for v in o.data.vertices),sum(v.co.x for v in o.data.vertices)))
 assert len(staves)==18
 report=[]
 for i,o in enumerate(staves):
  angle=math.atan2(sum(v.co.y for v in o.data.vertices),sum(v.co.x for v in o.data.vertices));t=Vector((-math.sin(angle),math.cos(angle),0));r=Vector((math.cos(angle),math.sin(angle),0))
  # Uneven oblique cut exposes believable fresh end-grain; retain original stave curvature.
  cut=.34+(i%5)*.073;bm=bmesh.new();bm.from_mesh(o.data)
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,cut),plane_no=(.13*math.cos(angle),.13*math.sin(angle),1),clear_outer=True)
  # Fracture follows the longitudinal grain with irregular stepped fibre tips.
  # The old clean oblique plane is retained only as a mean cut location.
  for v in bm.verts:
   if abs(v.co.z+.13*(v.co.x*math.cos(angle)+v.co.y*math.sin(angle))-cut)<2e-6:
    across=v.co.dot(t)
    v.co.z+=.024*math.sin(across*95+i*.71)+.013*math.sin(across*211+i*1.4)
  boundary=[e for e in bm.edges if e.is_boundary];bmesh.ops.holes_fill(bm,edges=boundary,sides=0);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
  for p in o.data.polygons:
   if p.normal.z>.85:
    for li in p.loop_indices:
     o.data.attributes['WoodEndMask'].data[li].value=1
     v=o.data.vertices[o.data.loops[li].vertex_index].co;o.data.attributes['WoodEnd'].data[li].vector=(v.dot(t),v.dot(r)-.35,0)
  center=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
  for v in o.data.vertices:
   d=v.co-center;v.co=(d.dot(t),-d.dot(r),d.z)
  a=i*math.tau/18+.17*math.sin(i*2.2);pitch=math.radians(7+(i%4)*6);direction=Vector((math.cos(a)*math.cos(pitch),math.sin(a)*math.cos(pitch),math.sin(pitch)));side=Vector((-math.sin(a),math.cos(a),0));normal=direction.cross(side);rot=Matrix((side,normal,direction)).transposed()
  for v in o.data.vertices:v.co=rot@v.co
  radius=.17+(i%3)*.052;o.location=(radius*math.cos(a),radius*math.sin(a),-min(v.co.z for v in o.data.vertices)+.001)
  o.name='Broken_coopered_stave_%02d'%i;report.append(dict(name=o.name,source_stave_angle=angle,cut_m=cut,floor_min_m=min(v.co.z for v in o.data.vertices)+o.location.z))
 # Dismantled head boards retain the original authored cross-cut wood and thickness.
 woodother=[o for o in parts if o not in staves and all(p.material_index==0 for p in o.data.polygons)]
 for i,o in enumerate(woodother):
  center=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
  for v in o.data.vertices:v.co-=center
  o.rotation_euler=(.04*(i%2),-.07*(i%3),i*.67);o.location=(-.25+i*.105,.10+(.06 if i%2 else -.02),0);bpy.context.view_layer.update();o.location.z=.004-min((o.matrix_world@v.co).z for v in o.data.vertices);o.name='Scattered_head_board_%02d'%i
 # The four original fitted straps are opened into flattened, irregular arcs—not torus debris.
 metal=[o for o in parts if o not in staves and o not in woodother]
 hoops=sorted([o for o in metal if len(o.data.vertices)==576],key=lambda o:min(v.co.z for v in o.data.vertices))
 for i,o in enumerate(hoops):
  # Remove a sector through a real cut, leaving solid strap ends.
  bm=bmesh.new();bm.from_mesh(o.data);remove=[v for v in bm.verts if v.co.x>.16 and v.co.y>-.15];bmesh.ops.delete(bm,geom=remove,context='VERTS');bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
  mid=sum(v.co.z for v in o.data.vertices)/len(o.data.vertices)
  for v in o.data.vertices:
   x,y,z=v.co;v.co=(x*(1+.08*i),y*.72,(z-mid)+.018*math.sin(math.atan2(y,x)*2+i))
  o.rotation_euler[2]=i*.73;o.location=((i-1.5)*.09,(i%2-.5)*.23,0);o.location.z=.003-min((o.matrix_world@v.co).z for v in o.data.vertices);o.name='Opened_forged_hoop_%02d'%i
 for o in metal:
  if o not in hoops:bpy.data.objects.remove(o,do_unlink=True)
 broken=[o for o in c.objects if o!=intact];intact.hide_render=True
 library=LIBRARY
 with bpy.data.libraries.load(str(library),link=False)as (available,loaded):
  loaded.materials=['MI_Shared_OakLonggrain2m','MI_Shared_OakEndgrain2m']
 longgrain,endgrain=loaded.materials;sharediron=bpy.data.materials['MI_Stonebrook_WroughtIron']
 assert longgrain and endgrain and sharediron
 for o in broken:
  me=o.data
  if o in hoops:
   me.materials.clear();me.materials.append(sharediron)
   for p in me.polygons:p.material_index=0
  else:
   me.materials.clear();me.materials.append(longgrain);me.materials.append(endgrain)
   uv=me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap');me.uv_layers.active=uv
   for p in me.polygons:
    end=sum(me.attributes['WoodEndMask'].data[li].value for li in p.loop_indices)/len(p.loop_indices)>.5;p.material_index=int(end)
    for li in p.loop_indices:
     v=me.attributes['WoodEnd' if end else 'WoodMetric'].data[li].vector
     uv.data[li].uv=(v.x/2,v.y/2)
 # The target material graphs themselves are appended unchanged from the approved library.
 # Intact private-material object is review-only and is not a proposed broken prop.
 material_proof=dict(library=str(library),library_sha256=sha(library),target_materials=sorted(set(m.name for o in broken for m in o.data.materials)),no_private_target_materials=all(m.name in ['MI_Shared_OakLonggrain2m','MI_Shared_OakEndgrain2m','MI_Stonebrook_WroughtIron']for o in broken for m in o.data.materials))
 (Q/'MATERIAL_PROVENANCE.json').write_text(json.dumps(material_proof,indent=2)+'\n')
 # Materials are inherited SOURCE materials. Their private/library-rule qualification remains explicit.
 # Repair only near-collapsed UV faces using physical dominant-axis projection.
 for o in broken:
  me=o.data;uv=me.uv_layers.get('UVMap')or me.uv_layers.new(name='UVMap');me.uv_layers.active=uv;me.calc_loop_triangles();bad=set()
  for t in me.loop_triangles:
   a,b,c=[uv.data[i].uv for i in t.loops]
   if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<2e-10:bad.add(t.polygon_index)
  for index in bad:
   p=me.polygons[index];drop=max(range(3),key=lambda k:abs(p.normal[k]));axes=[k for k in range(3)if k!=drop]
   for li in p.loop_indices:
    v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/2,v[axes[1]]/2)
  me.update()
 for im in bpy.data.images:
  if im.source=='FILE' and not im.packed_file:
   try:im.pack()
   except RuntimeError:pass
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=2;scene.cycles.max_bounces=6;scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
 scene.world=bpy.data.worlds.new('Neutral_source_review');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.16,.16,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
 scene.view_settings.view_transform='AgX';scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.001));floor=bpy.context.object;floor.name='REVIEW_ONLY_Floor';mat=bpy.data.materials.new('REVIEW_ONLY_NeutralFloor');mat.diffuse_color=(.14,.125,.105,1);floor.data.materials.append(mat)
 def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
 for name,pos,power,size in [('Key',(-2,-3,4),450,3),('Fill',(3,-1,2),180,2.5),('Rim',(1,3,3),300,2)]:
  l=bpy.data.lights.new(name,'AREA');l.energy=power;l.shape='DISK';l.size=size;o=bpy.data.objects.new(name,l);scene.collection.objects.link(o);o.location=pos;aim(o,(0,0,.25))
 camera=bpy.data.objects.new('Matched_review_camera',bpy.data.cameras.new('Matched_review_camera'));scene.collection.objects.link(camera);scene.camera=camera;camera.location=(1.8,-2.5,1.7);aim(camera,(0,0,.35));camera.data.type='ORTHO';camera.data.ortho_scale=2.15
 bpy.ops.wm.save_as_mainfile(filepath=str(Q/'PhotorealBrokenBarrelV2_Source.blend'))
 (Q/'Renders').mkdir(exist_ok=True)
 for mode in ['intact','broken']:
  intact.hide_render=mode!='intact'
  for o in broken:o.hide_render=mode!='broken'
  scene.render.filepath=str(Q/'Renders'/(mode+'_matched.png'));bpy.ops.render.render(write_still=True)
 intact.hide_render=True
 for o in broken:o.hide_render=False
 camera.location=(1.3,-1.6,2.6);aim(camera,(0,0,.12));camera.data.ortho_scale=1.8;scene.render.filepath=str(Q/'Renders/broken_top.png');bpy.ops.render.render(write_still=True)
 # Save returns the matched presentation and preserves individual editable debris.
 camera.location=(1.8,-2.5,1.7);aim(camera,(0,0,.35));camera.data.ortho_scale=2.15;bpy.ops.wm.save_as_mainfile(filepath=str(Q/'PhotorealBrokenBarrelV2_Source.blend'))
 allp=[o.matrix_world@v.co for o in broken for v in o.data.vertices];tri=sum(sum(len(p.vertices)-2 for p in o.data.polygons)for o in broken)
 r=dict(source=str(SRC),source_sha256=source_pin,source_unchanged=sha(SRC)==source_pin,original_reference='173/frame6 barel-06.bmp;174 palette variants NOT broken',candidate_sha256=sha(Q/'PhotorealBrokenBarrelV2_Source.blend'),debris_objects=len(broken),staves=report,opened_hoops=len(hoops),head_boards=len(woodother),triangles=tri,bounds_m=[[min(p[k]for p in allp)for k in range(3)],[max(p[k]for p in allp)for k in range(3)]],colliders_created=0,native_imported=False,runtime_bound=False,private_materials_inherited_source_only=False,material_provenance=material_proof,packed_images=[i.name for i in bpy.data.images if i.packed_file])
 (Q/'BUILD_RECEIPT.json').write_text(json.dumps(r,indent=2)+'\n')
try:run();sys.stdout.flush();os._exit(0)
except BaseException:traceback.print_exc();sys.stderr.flush();os._exit(1)
