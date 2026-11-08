"""Source-only barrel candidate; exports/bakes intentionally absent pending root visual review."""
import bpy,bmesh,json,math,random,hashlib,sys,os
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent;P=O/'Inputs/PhotorealPropsV1_Input.blend';rng=random.Random(17401)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source_pin=sha(P)
bpy.ops.wm.open_mainfile(filepath=str(P));s=bpy.context.scene;bpy.context.preferences.filepaths.save_version=0
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=40;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=4;s.cycles.max_bounces=6
s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
name='SM_Barrel_Oak_01';original=bpy.data.meshes.get(name+'_Mesh');assert original
original.use_fake_user=True
instances=[o for o in s.objects if o.type=='MESH'and o.data==original];assert len(instances)==2
bounds=[[min(v.co[k]for v in original.vertices)for k in range(3)],[max(v.co[k]for v in original.vertices)for k in range(3)]];H=bounds[1][2];rx=bounds[1][0];ry=bounds[1][1];aspect=ry/rx
report={'original_source_sha256':source_pin,'original_local_bounds_m':bounds,'original_instances':[{'name':ob.name,'matrix':[list(v)for v in ob.matrix_world]}for ob in instances],'original_vertices':len(original.vertices),'original_triangles':sum(len(p.vertices)-2 for p in original.polygons),'original_collision_m':{'min':[-.375,-.375,0],'max':[.375,.375,1]},'source_sprite':'173_01 natural oak initial barrel, bonuses/barrels/barel-01.bmp;174_01/02 palette variants inspected'}
image=bpy.data.images.load(str(O/'Inputs/GeneratedOak_Albedo_V1.png'),check_existing=False);image.colorspace_settings.name='sRGB';image.pack();image.filepath='//Inputs/GeneratedOak_Albedo_V1.png'
# Technical sampler derivative only. The immutable original1254px reference and full prompt remain in Inputs.
sample=image.copy();sample.name='T_BarrelOak_SourceSampler_BC';sample.scale(2048,2048);sample.pack();sample.filepath='//Packed/T_BarrelOak_SourceSampler_BC.png'
wood=bpy.data.materials.new('MI_BarrelOak_PhotoSource');wood.use_nodes=True;N=wood.node_tree.nodes;L=wood.node_tree.links;N.clear()
def node(t,n):a=N.new(t);a.name=n;a.label=n;return a
def link(src,dst):L.new(src,dst)
def mathn(op,*args):
 n=node('ShaderNodeMath',op);n.operation=op
 for i,a in enumerate(args):
  if isinstance(a,(float,int)):n.inputs[i].default_value=a
  else:link(a,n.inputs[i])
 return n.outputs[0]
def attr(name):n=node('ShaderNodeAttribute',name);n.attribute_name=name;return n
coords=attr('WoodPhoto');tex=node('ShaderNodeTexImage','Faithful oak reference sampling');tex.image=sample;tex.extension='EXTEND';link(coords.outputs['Vector'],tex.inputs[0]);physical=attr('WoodMetric')
def noise(vec,label):
 scale=node('ShaderNodeVectorMath',label+' metres');scale.operation='MULTIPLY';scale.inputs[1].default_value=vec;link(physical.outputs['Vector'],scale.inputs[0]);n=node('ShaderNodeTexNoise',label);n.inputs['Scale'].default_value=1;n.inputs['Detail'].default_value=3;link(scale.outputs[0],n.inputs[0]);return n.outputs['Fac']
slow=noise((7,1.3,3),'Quiet weathered tonal change');pores=noise((1700,34,220),'Open oak pores, submillimetre')
seed=attr('WoodSeed');gain=mathn('MULTIPLY',.30,mathn('ADD',.86,mathn('MULTIPLY',slow,.22)));gain=mathn('MULTIPLY',gain,mathn('ADD',.72,mathn('MULTIPLY',seed.outputs['Fac'],.52)))
tone=node('ShaderNodeMixRGB','Dry brown oak, no varnish');tone.blend_type='MULTIPLY';tone.inputs[0].default_value=1;link(tex.outputs['Color'],tone.inputs[1]);link(gain,tone.inputs[2])
end=attr('WoodEnd');radius=node('ShaderNodeVectorMath','Actual end-grain growth radius');radius.operation='LENGTH';link(end.outputs['Vector'],radius.inputs[0]);rings=mathn('SINE',mathn('ADD',mathn('MULTIPLY',radius.outputs['Value'],2200),mathn('MULTIPLY',slow,2.3)))
endmask=attr('WoodEndMask');endbase=node('ShaderNodeRGB','Actual cross-cut oak, no side-grain photograph');endbase.outputs[0].default_value=(.145,.083,.038,1)
endgain=mathn('MULTIPLY',mathn('ADD',.88,mathn('MULTIPLY',rings,.12)),mathn('ADD',.82,mathn('MULTIPLY',slow,.21)));endgain=mathn('MULTIPLY',endgain,mathn('ADD',.80,mathn('MULTIPLY',seed.outputs['Fac'],.30)))
endcolor=node('ShaderNodeMixRGB','End-grain growth colour');endcolor.blend_type='MULTIPLY';endcolor.inputs[0].default_value=1;link(endbase.outputs[0],endcolor.inputs[1]);link(endgain,endcolor.inputs[2]);endt=node('ShaderNodeMixRGB','Cross-cut ends separate from longitudinal grain');link(endmask.outputs['Fac'],endt.inputs[0]);link(tone.outputs[0],endt.inputs[1]);link(endcolor.outputs[0],endt.inputs[2])
bs=node('ShaderNodeBsdfPrincipled','Dry unvarnished oak');link(endt.outputs[0],bs.inputs['Base Color']);link(mathn('ADD',.64,mathn('MULTIPLY',slow,.16)),bs.inputs['Roughness']);bs.inputs['Specular IOR Level'].default_value=.31
bump=node('ShaderNodeBump','Fine independently authored fibre relief');bump.inputs['Distance'].default_value=.00023;bump.inputs['Strength'].default_value=.34;link(mathn('ADD',mathn('MULTIPLY',pores,.9),mathn('MULTIPLY',mathn('MULTIPLY',rings,endmask.outputs['Fac']),.1)),bump.inputs['Height']);link(bump.outputs[0],bs.inputs['Normal']);out=node('ShaderNodeOutputMaterial','Material output');link(bs.outputs[0],out.inputs[0])
for i,n in enumerate(N):n.location=(-1400+i%6*230,600-i//6*170)
iron=bpy.data.materials.new('MI_Barrel_WornForgedIron');iron.use_nodes=True;ns=iron.node_tree.nodes;ls=iron.node_tree.links;ibs=ns.get('Principled BSDF');ibs.inputs['Metallic'].default_value=.86;ibs.inputs['Specular IOR Level'].default_value=.45
c=ns.new('ShaderNodeTexCoord');n=ns.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=11;n.inputs['Detail'].default_value=4;ls.new(c.outputs['Object'],n.inputs[0]);ramp=ns.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.25;ramp.color_ramp.elements[0].color=(.025,.029,.030,1);ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(.135,.11,.073,1);ls.new(n.outputs['Fac'],ramp.inputs[0]);ls.new(ramp.outputs[0],ibs.inputs['Base Color']);rough=ns.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=0;rough.inputs['From Max'].default_value=1;rough.inputs['To Min'].default_value=.42;rough.inputs['To Max'].default_value=.68;ls.new(n.outputs['Fac'],rough.inputs[0]);ls.new(rough.outputs[0],ibs.inputs['Roughness']);fine=ns.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=190;fine.inputs['Detail'].default_value=2;ls.new(c.outputs['Object'],fine.inputs[0]);bn=ns.new('ShaderNodeBump');bn.inputs['Distance'].default_value=.00022;bn.inputs['Strength'].default_value=.34;ls.new(fine.outputs['Fac'],bn.inputs['Height']);ls.new(bn.outputs[0],ibs.inputs['Normal'])
oxide=ns.new('ShaderNodeValToRGB');oxide.name='Restrained patchy oxide';oxide.color_ramp.elements[0].position=.57;oxide.color_ramp.elements[0].color=(0,0,0,1);oxide.color_ramp.elements[1].position=.80;oxide.color_ramp.elements[1].color=(.72,.72,.72,1);ls.new(n.outputs['Fac'],oxide.inputs[0])
metal=ns.new('ShaderNodeMapRange');metal.inputs['From Min'].default_value=0;metal.inputs['From Max'].default_value=1;metal.inputs['To Min'].default_value=.94;metal.inputs['To Max'].default_value=.12;ls.new(oxide.outputs[0],metal.inputs[0]);ls.new(metal.outputs[0],ibs.inputs['Metallic'])
parts=[]
def finish(ob,mat,axis=2,bevel=.0009,stave_angle=None):
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update()
 if bevel:
  b=ob.modifiers.new('Millimetre hand-eased edges','BEVEL');b.width=bevel;b.segments=2;b.limit_method='ANGLE';b.angle_limit=.5;bpy.ops.object.modifier_apply(modifier=b.name)
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update()
 ob.data.materials.clear();ob.data.materials.append(mat)
 if mat==wood:
  me=ob.data;me.update();lo=[min(v.co[k]for v in me.vertices)for k in range(3)];hi=[max(v.co[k]for v in me.vertices)for k in range(3)];seed=rng.random();other=[k for k in range(3)if k!=axis]
  for a,t in [('WoodPhoto','FLOAT_VECTOR'),('WoodMetric','FLOAT_VECTOR'),('WoodEnd','FLOAT_VECTOR'),('WoodEndMask','FLOAT'),('WoodSeed','FLOAT')]:me.attributes.new(a,t,'CORNER')
  for p in me.polygons:
   across=min(other,key=lambda k:abs(p.normal[k]));mask=max(0,min(1,(abs(p.normal[axis])-.75)/.2))
   for li in p.loop_indices:
    v=me.vertices[me.loops[li].vertex_index].co
    if stave_angle is not None:
     delta=(math.atan2(v.y/aspect,v.x)-stave_angle+math.pi)%math.tau-math.pi;cross=delta*.40+.074
    else:cross=v[across]-lo[across]
    along=v[axis]-lo[axis]
    for a,value in [('WoodPhoto',(cross+seed*.55,along/2+seed*.35,0)),('WoodMetric',(cross,along,seed)),('WoodEnd',(v[other[0]]-(lo[other[0]]+hi[other[0]])/2+.026,v[other[1]]-(lo[other[1]]+hi[other[1]])/2+.012,0))]:me.attributes[a].data[li].vector=value
    me.attributes['WoodEndMask'].data[li].value=mask;me.attributes['WoodSeed'].data[li].value=seed
 for p in ob.data.polygons:p.use_smooth=True
 if hasattr(ob.data,'set_sharp_from_angle'):ob.data.set_sharp_from_angle(angle=math.radians(38))
 parts.append(ob);return ob

def mesh(name,vertices,faces,mat,axis=2,bevel=.0009,angle=None):
 me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update();ob=bpy.data.objects.new(name,me);s.collection.objects.link(ob);return finish(ob,mat,axis,bevel,angle)

def profile(z):return .334+.074*math.sin(math.pi*max(0,min(1,z/H)))**.85
# Eighteen separate, continuous bent staves, tapered to rim and closed through solid thickness.
count=18;nr=13;nw=4
for index in range(count):
 center=index*math.tau/count;half=math.pi/count-.0011;vertices=[];faces=[]
 for side in [0,1]:
  for iz in range(nr):
   z=H*iz/(nr-1)
   for ia in range(nw):
    a=center-half+2*half*ia/(nw-1);r=profile(z)-side*.028
    # A fitted croze recess receives the head just below the stave end.
    if side and abs(z-(H-.035))<.018:r+=.0015
    vertices.append((r*math.cos(a),r*math.sin(a)*aspect,z))
 for side in [0,1]:
  off=side*nr*nw
  for iz in range(nr-1):
   for ia in range(nw-1):
    a=off+iz*nw+ia;f=(a,a+1,a+nw+1,a+nw);faces.append(f if side==0 else f[::-1])
 for iz in range(nr-1):
  for ia in [0,nw-1]:
   a=iz*nw+ia;b=a+nw;faces.append((a,b,b+nr*nw,a+nr*nw))
 for iz in [0,nr-1]:
  for ia in range(nw-1):
   a=iz*nw+ia;b=a+1;faces.append((a,b,b+nr*nw,a+nr*nw))
 mesh('Coopered stave %02d'%index,vertices,faces,wood,angle=center)
# Flat iron straps sit on the changing stave profile, never a thick torus outline.
for bi,(fraction,width)in enumerate([(.085,.034),(.29,.040),(.71,.038),(.915,.033)]):
 zc=H*fraction;segments=48;vertices=[];faces=[]
 for z,radd in [(zc-width/2,.0004),(zc+width/2,.0004),(zc-width/2,.0026),(zc+width/2,.0026)]:
  for i in range(segments):
   a=i*math.tau/segments;r=profile(z)+radd;vertices.append((r*math.cos(a),r*math.sin(a)*aspect,z))
 for i in range(segments):
  j=(i+1)%segments
  faces.extend([(i,j,j+segments,i+segments),(i+2*segments,i+3*segments,j+3*segments,j+2*segments),(i,i+2*segments,j+2*segments,j),(i+segments,j+segments,j+3*segments,i+3*segments)])
 mesh('Forged flat hoop %d'%bi,vertices,faces,iron,bevel=.0004)
 # Short overlapped scarf and two peened rivets on the rear quarter.
 a=math.radians(-40+bi*11);r=profile(zc)+.0032;pos=Vector((r*math.cos(a),r*math.sin(a)*aspect,zc))
 bpy.ops.mesh.primitive_cube_add(size=1,location=pos);ob=bpy.context.object;ob.dimensions=(.038,.0018,width*.93);ob.rotation_euler[2]=a+math.pi/2;finish(ob,iron,bevel=.0005)
 for dz in [-width*.25,width*.25]:
  bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=1,location=pos+Vector((math.cos(a)*.0014,math.sin(a)*.0014,dz)));ob=bpy.context.object;ob.scale=(.0038,.0038,.0013);ob.rotation_euler=(Vector((math.cos(a),math.sin(a),0)).to_track_quat('Z','Y').to_euler());finish(ob,iron,bevel=0)
# The closed head is five clipped oak boards, retained in the croze with tiny joints.
head_radius=.316;head_z=H-.035;head_thickness=.021
for index in range(5):
 ya=-head_radius+index*(2*head_radius/5)+.0008;yb=-head_radius+(index+1)*(2*head_radius/5)-.0008
 outline=[]
 for step in range(65):
  a=step*math.tau/64;x=head_radius*math.cos(a);y=head_radius*math.sin(a)
  if ya+.004<=y<=yb-.004:outline.append((x,y))
 for y in [ya,yb]:
  if abs(y)<head_radius:
   x=math.sqrt(head_radius**2-y**2);outline.extend([(x,y),(-x,y)])
 cx=sum(p[0]for p in outline)/len(outline);cy=sum(p[1]for p in outline)/len(outline);outline.sort(key=lambda p:math.atan2(p[1]-cy,p[0]-cx));n=len(outline)
 vertices=[(x,y*aspect,z)for z in [head_z-head_thickness,head_z]for x,y in outline];faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)];mesh('Croze-fitted head board%d'%index,vertices,faces,wood,axis=0,bevel=.0011)
# A flush wooden bung, not modern hardware or an invented tap.
bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.017,depth=.004,location=(-.075,.045,head_z+.001));finish(bpy.context.object,wood,axis=2,bevel=.0006)
# Join editable source into the single asset mesh, retain two clear material slots.
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();candidate=bpy.context.object;candidate.name=name;candidate.data.name=name+'_PhotorealSource'
bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
# Exact existing local bounds, without expanding footprint/height or moving placement origins.
lo=[min(v.co[k]for v in candidate.data.vertices)for k in range(3)];hi=[max(v.co[k]for v in candidate.data.vertices)for k in range(3)]
for v in candidate.data.vertices:
 for k in range(3):v.co[k]=bounds[0][k]+(v.co[k]-lo[k])/(hi[k]-lo[k])*(bounds[1][k]-bounds[0][k])
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bm=bmesh.from_edit_mesh(candidate.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.update_edit_mesh(candidate.data);bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.006,area_weight=.1);bpy.ops.object.mode_set(mode='OBJECT')
collection=bpy.data.collections.new(name);s.collection.children.link(collection);collection['dink_class']='prop';collection['dink_path']='Stonebrook/PhotorealBarrelV1';collection['dink_tex_px']=2048;collection['dink_source']='Original Blender coopered geometry; natural Dink173_01 guide; unchanged approved oak source reference, sampler derivative declared; first visual gate pending'
for c in list(candidate.users_collection):c.objects.unlink(candidate)
collection.objects.link(candidate);candidate.hide_render=True
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,.5));collider=bpy.context.object;collider.dimensions=(.75,.75,1);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);collider.name='UCX_'+name+'_01';collider.hide_render=True;collider.display_type='WIRE'
for c in list(collider.users_collection):c.objects.unlink(collider)
collection.objects.link(collider)
# Source-original room matrices stay exact; only in-memory presentation mesh references change.
for ob in instances:ob.data=candidate.data
for im in bpy.data.images:
 if im.source=='FILE'and not im.packed_file:im.pack()
# Neutral diagnostic studio is separate from the immutable in-memory room context.
studio=bpy.data.scenes.new('BarrelStudio');studio.unit_settings.system='METRIC';studio.unit_settings.scale_length=1;studio.render.engine='CYCLES';studio.cycles.device='CPU';studio.cycles.samples=48;studio.cycles.use_denoising=True;studio.render.threads_mode='FIXED';studio.render.threads=4;studio.world=bpy.data.worlds.new('Neutral photographic world');studio.world.color=(.055,.055,.055)
show=bpy.data.objects.new('Studio source instance',candidate.data);studio.collection.objects.link(show)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.001));plane=bpy.context.object
for c in list(plane.users_collection):c.objects.unlink(plane)
studio.collection.objects.link(plane);floor=bpy.data.materials.new('Studio matte backdrop');floor.diffuse_color=(.10,.115,.13,1);floor.use_nodes=True;floor.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.10,.115,.13,1);floor.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.85;plane.data.materials.append(floor)
for label,pos,power,size in [('Large window key',(-2.8,-3.5,3.4),600,3.2),('Soft neutral fill',(2.3,-.5,2.1),190,2.0),('Gentle edge',(1.0,2.8,2.8),270,2.2)]:
 data=bpy.data.lights.new(label,'AREA');data.energy=power;data.shape='DISK';data.size=size;ob=bpy.data.objects.new(label,data);studio.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,0,.5))-ob.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('DiagnosticCamera');cam=bpy.data.objects.new('DiagnosticCamera',camdata);studio.collection.objects.link(cam);studio.camera=cam;cam.location=(1.6,-2.3,1.55);cam.rotation_euler=(Vector((0,0,.49))-cam.location).to_track_quat('-Z','Y').to_euler();camdata.lens=58
for scene in [s,studio]:scene.render.resolution_x=1100;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
bpy.context.window.scene=studio
report.update(candidate_vertices=len(candidate.data.vertices),candidate_triangles=sum(len(p.vertices)-2 for p in candidate.data.polygons),candidate_bounds_m=[[min(v.co[k]for v in candidate.data.vertices)for k in range(3)],[max(v.co[k]for v in candidate.data.vertices)for k in range(3)]],materials=[m.name for m in candidate.data.materials],staves=18,flat_hoops=4,head_boards=5,collision_copied_exact=True,source_reference_sha256=sha(O/'Inputs/GeneratedOak_Albedo_V1.png'),root_first_visual_gate='pending',baked=False,exported=False,CPU_threads=4)
assert sha(P)==source_pin
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealBarrelV1_Source.blend'));(O/'source_report.json').write_text(json.dumps(report,indent=2)+'\n');print('BARREL_SOURCE_READY',report['candidate_triangles'],flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(0)
