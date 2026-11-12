"""Work-only Stonebrook interior vista candidate. Never writes source repos or runtime Data."""
import bpy,math,json,random,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
R=Path('<HOME>/Repos/Dink-Smallwood/DinkRemasterUE');W=Path(__file__).resolve().parent
ANCHOR=Vector((-183806.0975,393595.98,0));EXTERIOR_ANCHOR=Vector((97661.61092968748,37370.324198125,0))
ROOM=(-7.590625,7.284375,0.,13.125)
random.seed(1439);bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):bpy.data.collections.remove(c)
s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
instances=bpy.data.collections.new('Vista_ExistingAssetInstances');s.collection.children.link(instances)
reference=bpy.data.collections.new('Preview_ExistingInteriorReference');s.collection.children.link(reference)
provenance=[];placements=[];new_assets=[];templates={}

def load_templates(rel):
 path=R/rel;before=set(bpy.data.images)
 with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith('SM_') and ('_LOD' not in n or n.endswith('_LOD0'))]
 for im in set(bpy.data.images)-before:
  p=Path(bpy.path.abspath(im.filepath))
  if im.filepath.startswith('//'):p=(path.parent/im.filepath[2:]).resolve()
  if p.is_file():im.filepath=str(p)
 for o in dst.objects:
  if o:templates[o.name]=o
 provenance.append({'blend':rel,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mode':'append local datablocks; original file never saved'})
load_templates('SourceAssets/Art/Stonebrook/KIT_Stonebrook.blend')
load_templates('SourceAssets/Art/StonebrookExterior/KIT_StonebrookExterior.blend')
load_templates('SourceAssets/Art/StonebrookFields/PineRefinementV3/PineRefinementV3.blend')
# Shared material references are canonicalized locally, not edited in their source library.
canonical={}
for m in list(bpy.data.materials):
 base=m.name.split('.')[0]
 if base not in canonical:canonical[base]=m
for o in templates.values():
 for i,m in enumerate(o.data.materials):
  if m:o.data.materials[i]=canonical[m.name.split('.')[0]]
def get_template(name):
 return templates.get(name) or templates.get(name+'_LOD0')
def outside_room(box):
 return box[1].x<=ROOM[0]+.001 or box[0].x>=ROOM[1]-.001 or box[1].y<=.001 or box[0].y>=ROOM[3]-.001

mesh_bounds={}
def bounds(o):
 key=o.data.as_pointer()
 if key not in mesh_bounds:
  pts=[v.co for v in o.data.vertices]
  mesh_bounds[key]=(Vector(tuple(min(p[k] for p in pts) for k in range(3))),Vector(tuple(max(p[k] for p in pts) for k in range(3))))
 lo,hi=mesh_bounds[key]
 # Do not read stale matrix_world immediately after pure-data instance creation.
 transform=Matrix.LocRotScale(o.location,o.rotation_euler.to_quaternion(),o.scale)
 pts=[transform@Vector((x,y,z)) for x in [lo.x,hi.x] for y in [lo.y,hi.y] for z in [lo.z,hi.z]]
 return Vector(tuple(min(p[k] for p in pts) for k in range(3))),Vector(tuple(max(p[k] for p in pts) for k in range(3)))

def height(x,y):
 # Broad landscape rolls, a compacted lane and a level neighboring-house pad.
 t=max(abs(x)/32.,(-y)/32.,y/24.)
 a=max(0,min(1,(t-.62)/.30));a=a*a*(3-2*a)
 tail=max(0,min(1,(t-.92)/.08));tail=tail*tail*(3-2*tail)
 ridge=(1.85+.45*math.sin(x*.15)+.25*math.sin(y*.13))*a*(1-.25*tail)
 h=-.025+.065*math.sin(x*.18)*math.sin(y*.13)+ridge
 if -25<y<.3:
  center=.085+.012*max(0,-y);mix=math.exp(-((x-center)/2.0)**4)
  h=h*(1-mix)+(-.025-.0006*max(0,-y))*mix
 mix=math.exp(-((y+17)/1.8)**4) if abs(x)<28 else 0
 h=h*(1-mix)+(-.036)*mix
 # Keep the neighbor's real foundation seated without flattening the whole landscape.
 dx=max(0,abs(x-24)-5.5);dy=max(0,abs(y-4)-9.7);d=math.hypot(dx,dy)
 w=max(0,1-d/2.5);w=w*w*(3-2*w)
 h=h*(1-w)+.04*w
 dx=max(0,abs(x+12)-8.2);dy=max(0,abs(y+25)-4.6);d=math.hypot(dx,dy);w=max(0,1-d/2.5);w=w*w*(3-2*w)
 return h*(1-w)+.04*w

def instantiate(name,asset,pos,yaw=0,scale=(1,1,1),ref=False,source_row=None):
 template=get_template(asset)
 if template is None:raise RuntimeError('Missing source mesh '+asset)
 o=bpy.data.objects.new(name,template.data);(reference if ref else instances).objects.link(o)
 o.location=pos;o.rotation_euler=(0,0,yaw);o.scale=scale
 if not ref:
  # This candidate's only purpose is visual context outside the teleport room.
  placements.append({'name':name,'reused_asset':asset,'local_blender_m':list(pos),'blender_yaw_deg':math.degrees(yaw),'scale':list(scale),'collision':False,'camera_occluder':False,'source_row':source_row})
 return o

def rebase(p,anchor):return ((p[0]-anchor.x)/100.,-(p[1]-anchor.y)/100.,(p[2]-anchor.z)/100.)
# Reconstruct the actual interior only as a preview frame; it is never part of the vista proposal.
inside=json.loads((R/'Content/Dink/Data/Art/stonebrook.json').read_text())
window_rows=[]
for row in inside['elements']:
 asset=row['mesh'].split('.')[-1];pos=rebase(row['world_cm'],ANCHOR)
 o=instantiate('Reference_'+row['name'],asset,pos,-math.radians(row['rotation_deg'][1]),row['scale'],True)
 if 'Window' in asset:window_rows.append((row,o))
# Ground chunks follow kit_floor rules: <=8m, applied transforms, minXY0/topZ0,
# tiling UVs and one shared source PBR material. Unused custom hulls are source-only.
meadow=canonical['MI_Stonebrook_Meadow'];stone=canonical['MI_Stonebrook_Fieldstone']
def asset_collection(name):
 c=bpy.data.collections.new(name);s.collection.children.link(c);c['dink_class']='kit_floor';c['dink_path']='Stonebrook/InteriorVista';c['dink_tex_px']=1024;c['dink_source']='Original procedural vista terrain, seed1439; reused project PBR; no external assets';return c

def hull(c,name,lo,hi):
 bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,0));o=bpy.context.object
 o.data.transform(Matrix.Translation((Vector(lo)+Vector(hi))*.5)@Matrix.Diagonal(Vector((hi[0]-lo[0],hi[1]-lo[1],hi[2]-lo[2],1))))
 for old in list(o.users_collection):old.objects.unlink(o)
 c.objects.link(o);o.name='UCX_'+name+'_01';o.data.name=o.name;o.hide_render=True;o.display_type='WIRE';return o

def ground(x,y,dx=8.,dy=8.,suffix=''):
 name='SM_VistaGround_8m_X'+('N' if x<0 else 'P')+str(abs(int(x)))+'_Y'+('N' if y<0 else 'P')+str(abs(int(y)))+suffix
 c=asset_collection(name);n=9;v=[];faces=[];heights=[height(x+i*dx/(n-1),y+j*dy/(n-1)) for j in range(n) for i in range(n)];top=max(heights)
 for layer in range(2):
  for j in range(n):
   for i in range(n):v.append((i*dx/(n-1),j*dy/(n-1),heights[j*n+i]-top-(.22 if layer else 0)))
 count=n*n
 for j in range(n-1):
  for i in range(n-1):
   a=j*n+i;faces.extend([(a,a+1,a+1+n,a+n),(a+count,a+n+count,a+n+1+count,a+1+count)])
 edge=list(range(n))+[j*n+n-1 for j in range(1,n)]+[(n-1)*n+i for i in range(n-2,-1,-1)]+[j*n for j in range(n-2,0,-1)]
 for a,b in zip(edge,edge[1:]+edge[:1]):faces.append((a+count,b+count,b,a))
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],faces);me.update();o=bpy.data.objects.new(name,me);c.objects.link(o);o.location=(x,y,top);me.materials.append(meadow)
 uv=me.uv_layers.new(name='UVMap')
 for p in me.polygons:
  p.use_smooth=p.index<(n-1)**2*2 and p.index%2==0
  for l in p.loop_indices:
   q=me.vertices[me.loops[l].vertex_index].co;uv.data[l].uv=(q.x/2,q.y/2)
 lo=(0,0,min(q[2] for q in v));hi=(dx,dy,0);h=hull(c,name,lo,hi);h.location=o.location
 new_assets.append({'name':name,'class':'kit_floor','triangles':sum(len(p.vertices)-2 for p in me.polygons),'dimensions_m':[dx,dy,hi[2]-lo[2]],'blender_translation_m':list(o.location),'source_hull':'unused; ALL future vista collision disabled','material':meadow.name})
 placements.append({'name':name,'new_mesh':name,'local_blender_m':list(o.location),'blender_yaw_deg':0,'scale':[1,1,1],'collision':False,'camera_occluder':False})
for x in range(-32,32,8):
 for y in range(-32,24,8):
  if x in [-8,0] and y in [0,8]:continue
  ground(x,y)
# Partial8x2.5m modules close the landscape behind north windows, without entering the room.
for x in [-8,0]:ground(x,13.5,8,2.5,'R')
# Exact original439 placement references for rail fences, oaks, boulders and grass.
exterior=json.loads((R/'Content/Dink/Data/Art/stonebrook_exterior.json').read_text())
for row in exterior['elements']:
 name=row['name'];asset=row['mesh'].split('.')[-1]
 if not name.startswith(('Fence','Oak','Boulder','Grass','DirtPath')):continue
 pos=list(rebase(row['world_cm'],EXTERIOR_ANCHOR));adjust=[]
 if name=='OakWest':pos[1]=8.5;adjust.append('shifted1.9m to frame existing west window without intersecting room')
 if name=='OakEast':pos[1]=20;adjust.append('northward to keep its canopy clear of proposed neighbor roof')
 if name=='OakNorth':pos[1]=22;adjust.append('root moved inside rear landscape extent')
 if name.startswith('DirtPath'):pos[2]=height(pos[0]+1,pos[1]-4)+.006
 else:pos[2]=height(pos[0],pos[1])
 o=instantiate('Vista_'+name,asset,pos,-math.radians(row['rotation_deg'][1]),row['scale'],source_row=name)
 lo,hi=bounds(o)
 if not outside_room((lo,hi)) or (name.startswith('Fence') and (lo.x<-32 or hi.x>32 or lo.y<-32 or hi.y>24)):
  placements.pop();bpy.data.objects.remove(o,do_unlink=True);continue
 placements[-1]['adjustment']=adjust
# The existing missingFenceSouth6 leaves the canonical four-metre gateway intact.
# Extend its dirt lane into a modest cross-street using the existing8x2m path assets.
for i,x in enumerate([-24,-16,-8,0,8,16,24]):instantiate('Vista_Street_'+str(i),'SM_Path_Earth_8m_01',(x,-18,height(x+4,-17)+.008))
instantiate('Vista_Neighbor_East','SM_Cottage_Stonebrook_01',(24,4,.04),-math.pi/2,source_row='new context proposal; DinksCottage deliberately omitted')
instantiate('Vista_Neighbor_SouthWest','SM_Cottage_Stonebrook_01',(-12,-25,.04),math.pi,(.85,.85,.85),source_row='new across-street context; existing cottage geometry reused, own house omitted')
instantiate('Vista_Neighbor_Access','SM_Path_Earth_8m_01',(-17.5,-17.5,.048),-math.pi/2,(.5,1,1))
for i,(x,y,sc) in enumerate([(-3,-13.7,.78),(8,-23,.85)]):
 instantiate('Vista_LayeredOak_'+str(i),'SM_Oak_Stonebrook_01',(x,y,height(x,y)),i*.7,(sc,sc,sc),source_row='new layered courtyard context; existing oak geometry reused')
for i,(x,y,sc) in enumerate([(-23,-29,.8),(-13,-30,.75),(-3,-29,.85),(3,-30,.7),(14,-29,.83),(25,-27,.72),(-28,7,.8),(-28,15,.88)]):
 instantiate('Vista_PineLayer_'+str(i),'SM_Pine_Stonebrook_V3',(x,y,height(x,y)),random.uniform(-math.pi,math.pi),(sc,sc,sc),source_row='new irregular treeline layer; existing PineV3 geometry reused')
for i in range(44):
 y=random.uniform(-17,-2);x=(.085+.012*(-y))+random.choice([-1,1])*random.uniform(1.2,1.9);sc=random.uniform(.035,.12)
 instantiate('Vista_LanePebble_'+str(i),'SM_Boulder_Fieldstone_01',(x,y,height(x,y)),random.uniform(-math.pi,math.pi),(sc,sc,sc))
# Sparse backdrop trees have actual trunks/branches/needles, not camera-facing cards.
for i,(x,y,scale) in enumerate([(-28,-28,.72),(-18,-30,.83),(-8,-29,.9),(8,-30,.8),(20,-28,.75),(29,-19,.9),(-28,19,.8),(-7,22,.9),(5,22,.84),(18,22,.76)]):
 instantiate('Vista_Pine_'+str(i),'SM_Pine_Stonebrook_V3',(x,y,height(x,y)),random.uniform(-math.pi,math.pi),(scale,scale,scale),source_row='new context, existing PineV3 mesh/materials')
# Extra grasses unify the doorway verge and fence posts; reject any leaf bounds in the room.
for i in range(90):
 x=random.uniform(-27,28);y=random.uniform(-26,22)
 if -8.6<x<8.6 and -.1<y<14:continue
 if abs(x-(.085+.012*max(0,-y)))<1.2 and -17<y<0:continue
 if 18<x<30 and -7<y<15:continue
 o=instantiate('Vista_GrassExtra_'+str(i),'SM_Grass_Meadow_01',(x,y,height(x,y)),random.uniform(-math.pi,math.pi),(1,1,random.uniform(.65,1.05)))
 if not outside_room(bounds(o)):placements.pop();bpy.data.objects.remove(o,do_unlink=True)
# Small new stone threshold, top flush with existing roomZ0. No geometry crosses y0.
name='SM_Doorstep_StonebrookVista_01';c=bpy.data.collections.new(name);s.collection.children.link(c);c['dink_class']='prop';c['dink_path']='Stonebrook/InteriorVista';c['dink_tex_px']=1024;c['dink_source']='Original procedural split flagstones; source Fieldstone PBR reused';pieces=[]
for i in range(3):
 bpy.ops.mesh.primitive_cube_add(size=1,location=(-.67+i*.67,0,.05));o=bpy.context.object;o.dimensions=(.66,1.5,.1);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);b=o.modifiers.new('StoneEdges','BEVEL');b.width=.009;b.segments=2;bpy.ops.object.modifier_apply(modifier=b.name);pieces.append(o)
bpy.ops.object.select_all(action='DESELECT')
for o in pieces:o.select_set(True)
bpy.context.view_layer.objects.active=pieces[0];bpy.ops.object.join();o=bpy.context.object;o.name=name;o.data.name=name;s.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
for old in list(o.users_collection):old.objects.unlink(o)
c.objects.link(o);o.data.materials.clear();o.data.materials.append(stone);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT');o.location=(0,-.75,-.1)
h=hull(c,name,(-1,-.75,0),(1,.75,.1));h.location=o.location
new_assets.append({'name':name,'class':'prop','triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'blender_translation_m':list(o.location),'material':stone.name,'source_hull':'unused; all future vista collision disabled'})
placements.append({'name':name,'new_mesh':name,'local_blender_m':list(o.location),'blender_yaw_deg':0,'scale':[1,1,1],'collision':False,'camera_occluder':False})
# Final independent placement guard: preview reference is not vista geometry.
violations=[]
for coll in [instances]+[bpy.data.collections[a['name']] for a in new_assets]:
 for ob in coll.objects:
  if ob.type=='MESH' and not ob.name.startswith('UCX_') and not outside_room(bounds(ob)):violations.append(ob.name)
assert not violations,violations
proposal={'schema':'dink-vista-source-proposal/1','status':'Work-only source preview; no runtime publication or import','interior_anchor_world_cm':list(ANCHOR),'reference_exterior_door_world_cm':list(EXTERIOR_ANCHOR),'blender_to_UE':'World=(anchorX+100*x,anchorY-100*y,100*z); yawUE=-yawBlender; source assets already metres','room_clear_rectangle_blender_m':ROOM,'new_meshes':new_assets,'instances':placements,'original_sources':provenance,'policy':{'collision':False,'camera_occluder':False,'original_warps_scripts_gameplay_unchanged':True,'new_vista_does_not_fix_native_camera_floor_framing':'independent context art only','own_cottage_duplicated':False}}
for p in proposal['instances']:
 x,y,z=p['local_blender_m'];p['world_cm_proposal']=[ANCHOR.x+x*100,ANCHOR.y-y*100,z*100];p['UE_yaw_deg']=-p['blender_yaw_deg']
(W/'placement_proposal.json').write_text(json.dumps(proposal,indent=2)+'\n')
# Store the full inspectable source scene; the reference collection is explicitly excluded from publishing.
bpy.ops.wm.save_as_mainfile(filepath=str(W/'Stonebrook_InteriorVista_Candidate.blend'))
# CPU daylight previews from actual architectural openings. These are source renders, not game screenshots.
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=32;s.cycles.use_denoising=True;s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=.8
world=bpy.data.worlds.new('VistaPreview_Daylight') if not s.world else s.world;s.world=world;world.use_nodes=True;bg=world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.40,.55,.80,1);bg.inputs['Strength'].default_value=.45
bpy.ops.object.light_add(type='SUN',location=(0,-10,20));sun=bpy.context.object;sun.data.energy=2.2;sun.data.angle=math.radians(4);sun.rotation_euler=(math.radians(-35),math.radians(-25),0)
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.lens=25.7;cam.data.sensor_width=36;cam.data.clip_end=200
views=[('inside-door',(0,1.55,1.65),(.25,-8,.1))]
# Source window centres are obtained from the actual reused source object transform.
for side,xsign in [('west',-1),('east',1)]:
 options=[(row,ob) for row,ob in window_rows if (ob.location.x<ROOM[0]+.3 if xsign<0 else ob.location.x>ROOM[1]-.3)]
 row,ob=min(options,key=lambda p:abs((p[1].matrix_world@Vector((1,0,1.85))).y-4.7));center=ob.matrix_world@Vector((1,0,1.85))
 loc=(center.x-xsign*1.3,center.y,1.7);target=(center.x+xsign*18,center.y,1.5);views.append(('inside-'+side+'-window',loc,target))
poses=[]
for label,loc,target in views:
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();preview=W/'PreviewV2';preview.mkdir(exist_ok=True);s.render.filepath=str(preview/(label+'.png'));bpy.ops.render.render(write_still=True);poses.append({'label':label,'camera_blender_m':loc,'target_blender_m':target,'lens_mm':cam.data.lens,'source_only':True})
(W/'preview_poses.json').write_text(json.dumps(poses,indent=2)+'\n');print('VISTA_SOURCE_PREVIEW_COMPLETE')
