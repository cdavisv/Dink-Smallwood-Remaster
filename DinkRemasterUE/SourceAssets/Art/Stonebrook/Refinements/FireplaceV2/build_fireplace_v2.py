"""Original procedural FireplaceV2 candidate, metres/Z-up/-Y-front. CPU preview only."""
import bpy, math, random, json, sys
import numpy as np
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent; TEX=OUT/'Textures';TEX.mkdir(exist_ok=True)
R=random.Random(87261); N=2048; NAME='SM_Fireplace_Stonebrook_V2'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):bpy.data.collections.remove(c)
s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
coll=bpy.data.collections.new(NAME);s.collection.children.link(coll)
coll['dink_class']='prop_large';coll['dink_path']='Stonebrook/Refinements';coll['dink_nanite']='yes';coll['dink_tex_px']=N;coll['dink_source']='Original project procedural art; build_fireplace_v2.py seed87261; no external assets'
parts=[];component=[]
def adopt(o,kind):
 for c in list(o.users_collection):c.objects.unlink(o)
 coll.objects.link(o);o.name='Part_'+str(len(parts));o.data.name=o.name
 a=o.data.attributes.new('surface_kind','INT','FACE')
 for x in a.data:x.value=kind
 component.append({'part':o.name,'kind':kind,'center_m':list(o.location),'dimensions_m':list(o.dimensions)})
 v=o.data.attributes.new('surface_tint','FLOAT','FACE');tint=R.uniform(.94,1.06) if kind==0 else 1
 for f in v.data:f.value=tint
 v=o.data.attributes.new('surface_center','FLOAT_VECTOR','FACE')
 for f in v.data:f.vector=o.location
 v=o.data.attributes.new('surface_axis','FLOAT_VECTOR','FACE')
 for f in v.data:f.vector=(1,0,0)
 parts.append(o);return o
def box(pos,dim,kind=0,bevel=.018):
 bpy.ops.mesh.primitive_cube_add(size=1,location=pos);o=bpy.context.object;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if kind==0:
  for v in o.data.vertices:
   v.co+=Vector((R.uniform(-.0025,.0025),R.uniform(-.0025,.0025),R.uniform(-.0025,.0025)))
 if bevel:
  b=o.modifiers.new('WornEdges','BEVEL');b.width=bevel*(R.uniform(.75,1.18) if kind==0 else 1);b.segments=2;b.affect='EDGES';bpy.ops.object.modifier_apply(modifier=b.name)
 return adopt(o,kind)
def cylinder_between(a,b,r,kind=4,verts=12):
 a,b=Vector(a),Vector(b);d=b-a;bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=d.length,end_fill_type='NGON',location=(a+b)*.5);o=bpy.context.object;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);return adopt(o,kind)
# 18cm hearth, 250x112cm; thin joints and restrained dimensional variation, closed stone solids.
for ix in range(5):
 for iy in range(2):box((-1+.5*ix,-.28+.56*iy,.09),(.493,.552,.18),0,.012)
# Firebox has its own continuous sooted firebrick back and side cheeks, not a window through the house.
box((0,.44,.76),(1.46,.22,1.16),6,.01)
for row in range(7):
 for i in range(5):
  x=-.584+i*.292
  box((x,.318,.26+row*.154),(.284,.028,.147),1,.006)
# Side cheeks and heavy fieldstone piers. Inner opening x[-.59,.59], z[.18,1.24].
for side in [-1,1]:
 box((side*.66,.04,.71),(.14,.64,1.06),1,.009)
 for row in range(6):
  z=.18+(row+.5)*.177
  for depth in range(2):
   box((side*.925,-.23+depth*.4,z),(.65+R.uniform(-.008,.008),.393,.168),0,.014)
# Wedge-shaped sloped throat rises behind the lintel; solid backing remains behind it.
box((0,.365,1.47),(1.46,.35,.47),6,.012)
for i in range(5):box((-.944+i*.472,-.015,1.365),(.463,.85,.25),0,.02)
# Projecting mantel and tapered stone chimney breast.
box((0,-.015,1.58),(2.48,1.02,.17),0,.024)
for row in range(8):
 width=2.1-.052*row
 edges=[-width/2,-width*.26,width*.02,width*.27,width/2] if row%2 else [-width/2,-width*.36,-width*.08,width*.18,width/2]
 for left,right in zip(edges,edges[1:]):
  box(((left+right)/2,.115,1.705+row*.171),(right-left-.009,.72,.164),0,.009)
box((0,.115,2.965),(1.85,.79,.07),0,.012)
# Firebed: soot-dark floor and non-uniform coal chunks, inside the raised hearth.
box((0,.015,.195),(1.16,.66,.03),6,.006)
for i in range(52):
 x=R.uniform(-.48,.48);y=R.uniform(-.27,.23);z=.245+R.uniform(-.012,.025)
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=R.uniform(.025,.055),location=(x,y,z));o=bpy.context.object;o.scale=(1.25,.9,.65);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);adopt(o,5)
def charred_log(a,b,r):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1))).normalized();v=axis.cross(u);verts=[];faces=[];phase=R.random()*6.28;segments=32;rings=6
 for k in range(rings):
  t=k/(rings-1);center=a.lerp(b,t)+v*(.008*math.sin(t*math.pi))
  for j in range(segments):
   ang=j*2*math.pi/segments
   rr=r*(1+.08*math.sin(ang*3+phase)+.045*math.sin(ang*9+phase*2)+.025*math.sin(t*8+ang*2))
   rr*=1-.12*max(0,math.cos(ang*5+phase))**14
   verts.append(center+(u*math.cos(ang)+v*math.sin(ang))*rr)
 for k in range(rings-1):
  for j in range(segments):faces.append((k*segments+j,k*segments+(j+1)%segments,(k+1)*segments+(j+1)%segments,(k+1)*segments+j))
 faces.extend([tuple(reversed(range(segments))),tuple((rings-1)*segments+j for j in range(segments))])
 me=bpy.data.meshes.new('Billet');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('Billet',me);bpy.context.collection.objects.link(o);adopt(o,2)
 for f in me.polygons:f.use_smooth=len(f.vertices)==4
 # Coordinates are authored in world space at zero origin, retain actual log centre for endgrain baking.
 for f in me.attributes['surface_center'].data:f.vector=(a+b)*.5
 return o
# Charred oak billets: real closed cylindrical volumes and visible endgrain; varied placement.
for a,b,r in [((-.49,-.13,.34),(.43,-.03,.34),.082),((-.43,.16,.37),(.43,.15,.37),.087),((-.32,-.05,.47),(.31,.14,.45),.072)]:
 o=charred_log(a,b,r)
 for f in o.data.attributes['surface_axis'].data:f.vector=(Vector(b)-Vector(a)).normalized()
 # End polygons receive their own end-grain surface code.
 attr=o.data.attributes['surface_kind']
 for p in o.data.polygons:
  if len(p.vertices)>4:attr.data[p.index].value=3
# A low basket/grate: slender wrought-iron members, no giant traversable floor box.
for x in [-.46,.46]:
 for y in [-.245,.22]:cylinder_between((x,y,.19),(x,y,.37),.016)
 cylinder_between((x,-.26,.36),(x,.24,.36),.018)
for i in range(9):
 x=-.47+i*.1175;cylinder_between((x,-.255,.33),(x,.235,.33),.012)
 cylinder_between((x,-.27,.30),(x,-.31,.52),.012)
cylinder_between((-.49,-.31,.52),(.49,-.31,.52),.015)
# One closed render mesh/LOD, actual unique UV atlas (not overlapping box projections).
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();m=bpy.context.object;m.name=NAME+'_LOD0';m.data.name=m.name;s.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.002,area_weight=.5,correct_aspect=True,scale_to_bounds=False);bpy.ops.object.mode_set(mode='OBJECT')
m.data.calc_loop_triangles();uv=m.data.uv_layers.active.data
# Rasterize surface colour/roughness/metal and restrained emissive coal cracks into one unique atlas.
bc=np.zeros((N,N,4),np.float32);bc[:]=(.20,.18,.15,1);orm=np.ones_like(bc);orm[:,:,1]=.9;orm[:,:,2]=0
em=np.zeros_like(bc);em[:,:,3]=1;mask=np.zeros((N,N),bool)
kinds=m.data.attributes['surface_kind'];pal=np.array([[.30,.275,.235],[.115,.062,.035],[.047,.036,.027],[.13,.075,.037],[.065,.06,.052],[.055,.035,.024],[.036,.028,.022]])
def noise3(x,y,z,scale):
 x=x*scale;y=y*scale;z=z*scale;ix=np.floor(x);iy=np.floor(y);iz=np.floor(z);fx=x-ix;fy=y-iy;fz=z-iz;fx=fx*fx*(3-2*fx);fy=fy*fy*(3-2*fy);fz=fz*fz*(3-2*fz)
 result=np.zeros_like(x)
 for a in [0,1]:
  for b in [0,1]:
   for c in [0,1]:
    h=np.sin((ix+a)*127.1+(iy+b)*311.7+(iz+c)*74.7)*43758.5453;h=h-np.floor(h)
    result+=h*(fx if a else 1-fx)*(fy if b else 1-fy)*(fz if c else 1-fz)
 return result
for t in m.data.loop_triangles:
 q=np.array([uv[i].uv[:] for i in t.loops])*N;xyz=np.array([m.data.vertices[i].co[:] for i in t.vertices]);k=kinds.data[t.polygon_index].value
 lo=np.maximum(np.floor(q.min(0)).astype(int),0);hi=np.minimum(np.ceil(q.max(0)).astype(int),N-1)
 if np.any(hi<lo):continue
 yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];px=xx+.5;py=yy+.5
 den=(q[1,1]-q[2,1])*(q[0,0]-q[2,0])+(q[2,0]-q[1,0])*(q[0,1]-q[2,1])
 if abs(den)<1e-10:continue
 a=((q[1,1]-q[2,1])*(px-q[2,0])+(q[2,0]-q[1,0])*(py-q[2,1]))/den
 b=((q[2,1]-q[0,1])*(px-q[2,0])+(q[0,0]-q[2,0])*(py-q[2,1]))/den;c=1-a-b;inside=(a>=-1e-5)&(b>=-1e-5)&(c>=-1e-5)
 x=a*xyz[0,0]+b*xyz[1,0]+c*xyz[2,0];y=a*xyz[0,1]+b*xyz[1,1]+c*xyz[2,1];z=a*xyz[0,2]+b*xyz[1,2]+c*xyz[2,2]
 fine=noise3(x,y,z,220)*2-1
 macro=noise3(x,y,z,17)*2-1
 tone=1+.085*macro+.055*fine
 if k==0:tone*=m.data.attributes['surface_tint'].data[t.polygon_index].value
 if k==1:tone*=np.clip(1.15-.48*z,.4,1.1)
 if k in [2,3]:
  ctr=m.data.attributes['surface_center'].data[t.polygon_index].vector;axis=m.data.attributes['surface_axis'].data[t.polygon_index].vector
  dx=x-ctr.x;dy=y-ctr.y;dz=z-ctr.z;along=dx*axis.x+dy*axis.y+dz*axis.z
  radius=np.sqrt(np.maximum(0,dx*dx+dy*dy+dz*dz-along*along));angle=np.arctan2(dz,dy)
  if k==3:
   rings=.5+.5*np.sin(radius*410+noise3(x,y,z,45)*2)
   fissure=np.sin(angle*11+noise3(x,y,z,60)*.6)>.96
   tone*=.65+.5*rings;tone*=np.where(fissure,.22,1.)
  else:
   grain=.5+.5*np.sin(angle*24+noise3(x,y,z,7)*2)
   tone*=.5+.8*grain;tone*=np.where(grain<.12,.30,1.)
 if k==0:
  smoke=np.exp(-(x/.64)**2)*np.exp(-((z-1.31)/.30)**2)*(y<-.25)
  tone*=1-.36*smoke
 color=np.clip(pal[k]*tone[:,:,None],0,1)
 patch=bc[lo[1]:hi[1]+1,lo[0]:hi[0]+1];patch[:,:,:3][inside]=color[inside];mask[lo[1]:hi[1]+1,lo[0]:hi[0]+1]|=inside
 patch=orm[lo[1]:hi[1]+1,lo[0]:hi[0]+1];patch[:,:,1][inside]=np.clip((.67 if k==4 else .91)+.04*fine[inside],0,1);patch[:,:,2][inside]=.85 if k==4 else 0
 if k==5:
  crack=(np.sin(x*173+y*139+z*117)>.8)&(np.sin(x*83-y*57)>.1)
  ep=em[lo[1]:hi[1]+1,lo[0]:hi[0]+1];col=np.zeros_like(ep[:,:,:3]);col[:]=(.7,.035,.002);ep[:,:,:3][inside&crack]=col[inside&crack]
# 5-pixel dilation into gutters preserves mip edge colours, no seam black halos.
for step in range(3):
 old=mask.copy()
 for dy,dx in [(1,0),(-1,0),(0,1),(0,-1)]:
  near=np.roll(old,(dy,dx),(0,1));take=near&~mask
  for ar in [bc,orm,em]:ar[take]=np.roll(ar,(dy,dx),(0,1))[take]
  mask|=take
normal=np.ones_like(bc);nrng=np.random.default_rng(87261);height=nrng.random((N,N)).astype(np.float32)
for _ in range(3):height=(height+np.roll(height,1,0)+np.roll(height,-1,0)+np.roll(height,1,1)+np.roll(height,-1,1))/5
hx,hy=np.gradient(height);normal[:,:,0]=.5-hy*.28;normal[:,:,1]=.5-hx*.28;normal[:,:,2]=np.sqrt(np.maximum(0,1-(hy*.56)**2-(hx*.56)**2))*.5+.5
images={}
for suffix,ar,linear in [('BC',bc,False),('N',normal,True),('ORM',orm,True),('E',em,False)]:
 im=bpy.data.images.new('T_FireplaceV2_Atlas_'+suffix,width=N,height=N,alpha=True);im.colorspace_settings.name='Non-Color' if linear else 'sRGB';im.pixels.foreach_set(ar.ravel());im.filepath_raw=str(TEX/(im.name+'.png'));im.file_format='PNG';im.save();images[suffix]=im
mat=bpy.data.materials.new('MI_FireplaceV2_Atlas');mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF')
for suffix,im in images.items():
 n=nodes.new('ShaderNodeTexImage');n.image=im;n.label=suffix
 if suffix=='BC':links.new(n.outputs['Color'],bs.inputs['Base Color'])
 if suffix=='N':
  v=nodes.new('ShaderNodeNormalMap');v.inputs['Strength'].default_value=.35;links.new(n.outputs['Color'],v.inputs['Color']);links.new(v.outputs['Normal'],bs.inputs['Normal'])
 if suffix=='ORM':
  sep=nodes.new('ShaderNodeSeparateColor');links.new(n.outputs['Color'],sep.inputs[0]);links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 if suffix=='E':links.new(n.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=1.2
m.data.materials.clear();m.data.materials.append(mat)
# Derived classic fallback LODs; collision remains independent and geometric.
lods=[m]
for idx,ratio in [(1,.52),(2,.27)]:
 o=m.copy();o.data=m.data.copy();coll.objects.link(o);o.name=NAME+'_LOD'+str(idx);o.data.name=o.name;bpy.context.view_layer.objects.active=o;d=o.modifiers.new('FallbackLOD','DECIMATE');d.ratio=ratio;bpy.ops.object.modifier_apply(modifier=d.name);o.hide_render=True;lods.append(o)
# Collision footprint follows only visible structure: hearth, piers, backing, lintel and chimney.
hulls=[]
for pos,dim in [((0,0,.09),(2.5,1.12,.18)),((-.925,-.015,.71),(.65,.8,1.06)),((.925,-.015,.71),(.65,.8,1.06)),((0,.44,.76),(1.46,.22,1.16)),((0,.0,1.365),(2.35,.8,.25)),((0,.115,2.29),(1.75,.70,1.40))]:
 bpy.ops.mesh.primitive_cube_add(size=1,location=pos);o=bpy.context.object;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 for c in list(o.users_collection):c.objects.unlink(o)
 coll.objects.link(o);o.name='UCX_'+m.name+'_'+str(len(hulls)+1).zfill(2);o.data.name=o.name;s.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');o.hide_render=True;o.display_type='WIRE';hulls.append(o)
# Save production source BEFORE adding preview-only floor/camera/lights.
bpy.ops.object.select_all(action='DESELECT');m.select_set(True);bpy.context.view_layer.objects.active=m
for im in images.values():im.filepath='//Textures/'+Path(im.filepath).name
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(NAME+'.blend')))
manifest={'name':NAME,'candidate_status':'source-only preview, not imported or runtime accepted','seed':87261,'dimensions_m':list(m.dimensions),'opening_m':{'width':1.18,'height':1.06,'floor_z':.18,'lintel_bottom_z':1.24},'lods':[{'name':o.name,'triangles':sum(len(p.vertices)-2 for p in o.data.polygons)} for o in lods],'collision_hulls':len(hulls),'collision_mode_proposal':'simple custom convex, verify actual capsule sweeps in editor before runtime','material':mat.name,'textures':{k:'Textures/'+v.name+'.png' for k,v in images.items()},'normal_flip_green':True,'emission_strength':1.2,'placement_proposal':{'origin':'S001_P19','offset_cm':[6.5625,-28.437499999941792,0],'rotation_deg':[0,0,0],'scale':[1,1,1],'original_script':'s1-h1-2','runtime_manifest_changed':False,'existing_light_reference':{'lumens':150,'z_cm':90},'light_candidate_proposal':{'lumens':150,'z_cm':55,'note':'Lower from existing90cm to55cm above hearth only if live emission/light/shadow gate passes; no runtime light changed'}},'component_inventory':component}
(OUT/'candidate_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Neutral studio/front/three-quarter/detail CPU evidence, never presented as game screenshots.
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=40;s.cycles.use_denoising=True;s.render.resolution_x=1100;s.render.resolution_y=1100;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX'
s.world.color=(.16,.16,.16)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.008));floor=bpy.context.object;floor.name='PreviewOnlyFloor';fm=bpy.data.materials.new('PreviewOnlyNeutral');fm.diffuse_color=(.18,.17,.15,1);floor.data.materials.append(fm)
for pos,power,size in [((1,-4,5),850,4),((-3,-1,3),550,3),((0,2,4),650,3)]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,1.3))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='PERSP';cam.data.lens=48
for name,pos,target,lens in [('preview-front',(0,-6.4,2.6),(0,0,1.45),48),('preview-threequarter',(3.6,-5.1,2.65),(0,0,1.4),48),('preview-firebox',(1.3,-2.8,1.25),(0,0,.65),58)]:
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens;s.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
print('FIREPLACE_V2_SOURCE_READY '+str(OUT))
