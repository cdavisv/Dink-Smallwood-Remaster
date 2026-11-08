"""PineV3 from pinned Sapling0.4.0 small_pine branching and original3Dneedle atlas.
Generator code livesonlyin/tmp, registeredperprocess; no userBlenderprefs touched.
Every sourcebranch and needle-spray placement survives allthree authoredLODs.
"""
import bpy,bmesh,json,math,sys,os,importlib.util,types,hashlib,struct
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];FIELDS=ROOT.parent;NAME='SM_Pine_Stonebrook_V3';TOOL=Path(os.environ.get('DINK_SAPLING_TOOL','/tmp/dink-qa-tools/sapling'))
if not(TOOL/'blender_manifest.toml').is_file():raise RuntimeError('Install pinnedSapling0.4.0 in/tmp/dink-qa-tools/sapling; seeREADME')
for p in ['Previews','Export','Working']: (ROOT/p).mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('dink_sapling_tool',TOOL/'__init__.py',submodule_search_locations=[str(TOOL)]);mod=importlib.util.module_from_spec(spec);sys.modules['dink_sapling_tool']=mod;spec.loader.exec_module(mod)
from dink_sapling_tool.generator import TreeGenerator
from dink_sapling_tool.model.tree import TreeGrower
from dink_sapling_tool.build.tree_record import TreeRecord
from dink_sapling_tool.settings import TreeSettings
captured={};grow=TreeGrower.grow
def record_growth(self,*args,**kwargs):
 out=grow(self,*args,**kwargs);captured['grown']=out;return out
TreeGrower.grow=record_growth
settings=json.loads((ROOT/'sapling_settings.json').read_text());settings.update(leafShape='rect',leaves=8,showLeaves=True,leafScale=1.20,leafScaleX=.62,leafScaleV=.25,leafMaterial=False)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
result=TreeGenerator(types.SimpleNamespace(**settings),bpy.context,[scene.collection]).generate();TreeRecord.tag(result,TreeSettings(settings));grown=captured['grown'];tree=result.tree;leaf=result.role('leaves')
(ROOT/'sapling_settings.json').write_text(json.dumps(settings,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Working/Sapling_Source.blend'))
# Sample realWeber-Penn Bezierbranch geometry; levels preserved from generator.
branches=[]
for si,spline in enumerate(tree.data.splines):
 points=spline.bezier_points;dense=[]
 for i in range(len(points)-1):
  a=points[i];b=points[i+1]
  for k in range(8):
   t=k/8;p=(1-t)**3*a.co+3*(1-t)**2*t*a.handle_right+3*(1-t)*t*t*b.handle_left+t**3*b.co;radius=a.radius*(1-t)+b.radius*t;dense.append((p.copy(),max(.0007,radius)))
 dense.append((points[-1].co.copy(),max(.0007,points[-1].radius)));branches.append({'id':si,'level':grown.level_of(si),'dense':dense})
leaves=[[leaf.matrix_world@leaf.data.vertices[i].co for i in poly.vertices] for poly in leaf.data.polygons];assert all(len(p)==4 for p in leaves)
for quad in leaves:
 anchor=(quad[0]+quad[3])*.5;z=sum(v.z for v in quad)/4;scale=1+.30*max(0,min(1,(8.0-z)/6.0))
 for i in range(4):quad[i]=anchor+(quad[i]-anchor)*scale
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
coll=bpy.data.collections.new(NAME);scene.collection.children.link(coll);coll['dink_class']='foliage';coll['dink_path']='StonebrookFields/PineRefinementV3';coll['dink_nanite']='no';coll['dink_tex_px']=2048
allmats=json.loads((ROOT/'pine_materials.json').read_text());materialspec={n:allmats[n] for n in ['MI_PineV3_Bark','MI_PineV3_Sprays']};materialspec['MI_PineV3_Sprays'].update(alpha_clip=.12,preserve_alpha_coverage=True);mats=[]
for name,row in materialspec.items():
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Specular IOR Level'].default_value=.25
 for channel in ['BC','N','ORM']:
  node=n.new('ShaderNodeTexImage');im=bpy.data.images.load(str(ROOT/row['textures'][channel]),check_existing=True);im.name=Path(row['textures'][channel]).stem;im.colorspace_settings.name='sRGB' if channel=='BC' else'Non-Color';node.image=im
  if channel=='BC':
   l.new(node.outputs['Color'],bs.inputs['Base Color'])
   if row.get('masked'):
    mask=n.new('ShaderNodeMath');mask.operation='GREATER_THAN';mask.inputs[1].default_value=.12;l.new(node.outputs['Alpha'],mask.inputs[0]);l.new(mask.outputs[0],bs.inputs['Alpha']);m.surface_render_method='DITHERED';m.use_transparency_overlap=False
  elif channel=='N':normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.5;l.new(node.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],bs.inputs['Normal'])
  else:sep=n.new('ShaderNodeSeparateColor');l.new(node.outputs['Color'],sep.inputs[0]);l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 mats.append(m)

def resample(samples,count):
 lengths=[0.]
 for i in range(1,len(samples)):lengths.append(lengths[-1]+(samples[i][0]-samples[i-1][0]).length)
 if lengths[-1]<1e-5:return[samples[0],samples[-1]]
 out=[]
 for k in range(count):
  wanted=lengths[-1]*k/(count-1);j=next((i for i in range(1,len(lengths)) if lengths[i]>=wanted),len(lengths)-1);t=(wanted-lengths[j-1])/max(1e-8,lengths[j]-lengths[j-1]);out.append((samples[j-1][0].lerp(samples[j][0],t),samples[j-1][1]*(1-t)+samples[j][1]*t))
 return out

def frame(axis):
 axis=axis.normalized();ref=Vector((0,0,1))
 if abs(axis.dot(ref))>.95:ref=Vector((0,1,0))
 u=axis.cross(ref).normalized();v=axis.cross(u).normalized();return u,v
raw=[];levels=[]
for lod in range(3):
 vs=[];fs=[];uvs=[];material_ids=[];smooth=[];tags=[];branch_ids=[];spray_ids=[];active_branch=-1;active_spray=-1
 def vertex(p,kind):vs.append(Vector(p));tags.append(kind);branch_ids.append(active_branch);spray_ids.append(active_spray);return len(vs)-1
 def face(ids,mat,coords=None,sm=True):fs.append(tuple(ids));material_ids.append(mat);smooth.append(sm);uvs.append(coords or[(vs[i].x,vs[i].z) for i in ids])
 for branch in branches:
  active_branch=branch['id'];active_spray=-1
  level=branch['level'];samples=branch['dense'];count=(24 if level==0 else(5 if level==1 else 3)) if lod==0 else(12 if level==0 else(3 if level==1 else 2));side=(12 if level==0 else(5 if level==1 else 4)) if lod==0 else((8 if lod==1 else 6) if level==0 else(4 if lod==1 and level==1 else 3));points=resample(samples,count);rings=[];along=0
  for k,(p,radius) in enumerate(points):
   along+=(p-points[k-1][0]).length if k else 0
   # Allthinbranches terminateinonepoint atlowerLODs; theirsourceidentity isretained.
   pole=lod>0 and level>0 and k==len(points)-1
   if pole:rings.append(([vertex(p,'wood')],along/2));continue
   d=points[min(k+1,len(points)-1)][0]-points[max(0,k-1)][0];u,v=frame(d);rings.append(([vertex(p+radius*(math.cos(j*math.tau/side)*u+math.sin(j*math.tau/side)*v),'trunk' if level==0 else'wood') for j in range(side)],along/2))
  face(tuple(reversed(rings[0][0])),0)
  if len(rings[-1][0])>1:face(rings[-1][0],0)
  for k in range(len(rings)-1):
   a,t0=rings[k];b,t1=rings[k+1]
   for j in range(side):
    if len(b)==1:face((a[j],a[(j+1)%side],b[0]),0,[(j/side,t0),((j+1)/side,t0),((j+.5)/side,t1)])
    else:face((a[j],a[(j+1)%side],b[(j+1)%side],b[j]),0,[(j/side,t0),((j+1)/side,t0),((j+1)/side,t1),(j/side,t1)])
 for lid,quad in enumerate(leaves):
  active_branch=-1;active_spray=lid
  # Retain everygeneratedspray placement; curvature only is simplified atLOD2.
  a,b,c,d=quad;normal=(b-a).cross(d-a).normalized()
  if lod<2:
   middle0=(a+b)*.5+normal*.055;middle1=(c+d)*.5+normal*.055;ids=[vertex(p,'foliage') for p in [a,d,middle0,middle1,b,c]];face((ids[0],ids[1],ids[3],ids[2]),1,[(0,0),(0,1),(.5,1),(.5,0)]);face((ids[2],ids[3],ids[5],ids[4]),1,[(.5,0),(.5,1),(1,1),(1,0)])
  else:
   ids=[vertex(p,'foliage') for p in [a,d,c,b]];face(ids,1,[(0,0),(0,1),(1,1),(1,0)])
 raw.append({'verts':vs,'faces':fs,'uv':uvs,'materials':material_ids,'smooth':smooth,'tags':tags,'branch_ids':branch_ids,'spray_ids':spray_ids})
# Oneglobal source->game transform gives theexactoldLOD0footprint and13mheight.
base=raw[0];lo=[min(p[k] for p in base['verts']) for k in range(3)];hi=[max(p[k] for p in base['verts']) for k in range(3)];target=[5.780095100402832,5.865981578826904,13.];sx=target[0]/(hi[0]-lo[0]);sy=target[1]/(hi[1]-lo[1]);cx=(lo[0]+hi[0])/2;cy=(lo[1]+hi[1])/2;folmin=min(p.z for p,t in zip(base['verts'],base['tags']) if t=='foliage');folmax=hi[2]
def remap(p,tag):
 x=(p.x-cx)*sx;y=(p.y-cy)*sy
 if p.z<folmin:z=(p.z-lo[2])*1.0746300220489502/max(1e-5,folmin-lo[2])
 else:z=1.0746300220489502+(p.z-folmin)*(13-1.0746300220489502)/(folmax-folmin)
 if tag=='trunk' and z<3:
  blend=max(0,min(1,(z-1.5)/1.5));x=(p.x+.11579096)*(1-blend)+x*blend;y=(p.y+.06273317)*(1-blend)+y*blend
 return(x,y,max(0,min(13,z)))
for lod,row in enumerate(raw):
 coords=[remap(p,t) for p,t in zip(row['verts'],row['tags'])];me=bpy.data.meshes.new(NAME+'_LOD%d'%lod);me.from_pydata(coords,[],row['faces']);me.update()
 for mat in mats:me.materials.append(mat)
 for poly,mat,sm in zip(me.polygons,row['materials'],row['smooth']):poly.material_index=mat;poly.use_smooth=sm
 for attr,values in [('source_branch_id',row['branch_ids']),('source_spray_id',row['spray_ids'])]:
  data=me.attributes.new(attr,'INT','POINT');data.data.foreach_set('value',values)
 uv=me.uv_layers.new(name='UVMap')
 for poly,values in zip(me.polygons,row['uv']):
  for li,value in zip(poly.loop_indices,values):uv.data[li].uv=value
 # Consistent winding whilepreserving UVs andsourceIDs.
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update();ob=bpy.data.objects.new(me.name,me);coll.objects.link(ob);ob.hide_render=lod>0;ob['source_branch_splines']=len(branches);ob['source_needle_sprays']=len(leaves);ob['source_whorl_rings']=settings['nrings'];me.calc_loop_triangles()
 levels.append({'lod':lod,'triangles':len(me.loop_triangles),'vertices':len(me.vertices),'branch_splines_retained':len(branches),'primary_branch_splines_retained':grown.level_ends[1]-grown.level_ends[0],'needle_sprays_retained':len(leaves),'whorl_rings_retained':settings['nrings'],'bounds_min_m':[min(v.co[k] for v in me.vertices) for k in range(3)],'bounds_max_m':[max(v.co[k] for v in me.vertices) for k in range(3)]})
oldname='UCX_SM_Pine_Stonebrook_01_LOD0_01'
with bpy.data.libraries.load(str(FIELDS/'KIT_StonebrookFields.blend'),link=False) as (available,loaded):loaded.objects=[oldname]
co=loaded.objects[0];coll.objects.link(co);co.name='UCX_'+NAME+'_LOD0_01';co.data.name=co.name;co.hide_render=True;co.display_type='WIRE';h=hashlib.sha256()
for p in co.data.vertices:h.update(struct.pack('<3f',*p.co))
for p in co.data.polygons:h.update(struct.pack('<I',len(p.vertices)));h.update(struct.pack('<'+'I'*len(p.vertices),*p.vertices))
report={'schema':'dink-pine-refinement/3','candidate':NAME,'method':'Sapling0.4.0 Weber-Penn small_pine parameters +original modeledpairedneedle atlas +authoredper-splineLODretention','source_original_modified':False,'dimensions_m':target,'lods':levels,'collision':{'vertex_face_sha256':h.hexdigest(),'bounds_min_m':[min(v.co[k] for v in co.data.vertices) for k in range(3)],'bounds_max_m':[max(v.co[k] for v in co.data.vertices) for k in range(3)]},'sapling_level_ends':grown.level_ends,'source_whorls':settings['nrings'],'lower_crown_spray_enlargement_max':1.30,'blender_alpha_mode':'GREATER_THAN.12 matchesUEhardmask','material_policy':'2slots:originalbarkPBR andmaskedtwo-sidedmodeledneedle-sprays; no greenopaqueclumpcores','lod_policy':'Allbranchsplines and allneedle-spray placements retained atall3LODs; woodcrosssections/curve sampling andspraybow simplified only.'}
(ROOT/'pine_geometry_report.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'pine_materials_used.json').write_text(json.dumps(materialspec,indent=2)+'\n')

# Photographicneutralstudio, separatefromassetcollection.
stage=bpy.data.collections.new('Preview_Stage');scene.collection.children.link(stage)
def stageob(o):
 for c in list(o.users_collection):c.objects.unlink(o)
 stage.objects.link(o)
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;stageob(floor);fm=bpy.data.materials.new('Studio ground');fm.use_nodes=True;fm.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.12,.13,.14,1);fm.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.9;floor.data.materials.append(fm)
world=bpy.data.worlds.new('Pine review environment');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.30,.36,.45,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;scene.world=world
sun=bpy.data.lights.new('Neutral daylight','SUN');sun.energy=2.0;o=bpy.data.objects.new(sun.name,sun);stage.objects.link(o);o.rotation_euler=(.55,-.45,-.6)
d=bpy.data.lights.new('Softlargekey','AREA');d.energy=5000;d.shape='DISK';d.size=12;o=bpy.data.objects.new(d.name,d);stage.objects.link(o);o.location=(4,-8,14);o.rotation_euler=(Vector((0,0,6))-o.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Pine review');cam=bpy.data.objects.new(cd.name,cd);stage.objects.link(cam);cam.location=(17,-24,13);cam.rotation_euler=(Vector((0,0,6.5))-cam.location).to_track_quat('-Z','Y').to_euler();cd.lens=55;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.transparent_max_bounces=32;scene.cycles.use_denoising=True;scene.render.resolution_x=1100;scene.render.resolution_y=1300;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
for im in bpy.data.images:
 if im.filepath:im.filepath='//Textures/'+Path(im.filepath).name
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'PineRefinementV3.blend'),relative_remap=False)
scene.render.filepath=str(ROOT/'Previews/pine_v3_portrait.png');bpy.ops.render.render(write_still=True)
# Independentrenders give eachLOD exactlythesamecamera andlighting.
from PIL import Image,ImageDraw,ImageFont
original=bpy.data.objects[NAME+'_LOD0'];cam.location=(17,-24,13);cam.rotation_euler=(Vector((0,0,6.5))-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=15.5;scene.render.resolution_x=600;scene.render.resolution_y=1000
for lod in range(3):
 for i in range(3):bpy.data.objects[NAME+'_LOD%d'%i].hide_render=i!=lod
 scene.render.filepath=str(ROOT/'Working'/('Pine_LOD%d.png'%lod));bpy.ops.render.render(write_still=True)
canvas=Image.new('RGB',(1800,1040),(27,31,34));draw=ImageDraw.Draw(canvas)
try:font=ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf',22)
except OSError:font=ImageFont.load_default()
for lod in range(3):
 im=Image.open(ROOT/'Working'/('Pine_LOD%d.png'%lod)).convert('RGB');canvas.paste(im,(lod*600,0));draw.text((lod*600+25,1007),'LOD%d  %s triangles'%(lod,format(levels[lod]['triangles'],',')),fill=(235,235,235),font=font)
canvas.save(ROOT/'Previews/pine_v3_lod_comparison.png')
canvas.resize((450,260),Image.Resampling.LANCZOS).save(ROOT/'Previews/pine_v3_distance_thumbnail.png')
for i in range(3):bpy.data.objects[NAME+'_LOD%d'%i].hide_render=i!=0
original.hide_render=False;cd.type='PERSP';cd.lens=70;scene.render.resolution_x=1300;scene.render.resolution_y=1000;cam.location=(2,-5.2,4.6);cam.rotation_euler=(Vector((.2,-1.8,3.7))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/'Previews/pine_v3_bough_close.png');bpy.ops.render.render(write_still=True)
print('PINE V3 SOURCE REVIEW READY',[(r['lod'],r['triangles']) for r in levels],flush=True)
