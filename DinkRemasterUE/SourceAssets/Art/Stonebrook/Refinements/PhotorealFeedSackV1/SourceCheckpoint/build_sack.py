"""Source-only original422_12 grain sack: full cloth, seams, stitches and fitted tie."""
import bpy,bmesh,math,json,hashlib,random,os,sys,traceback
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent;P=O/'Inputs/KIT_Stonebrook_Input.blend';name='SM_FeedSack_Jute_01';rng=random.Random(42212)
try:
 bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.name='SackSource';s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;bpy.context.preferences.filepaths.save_version=0
 with bpy.data.libraries.load(str(P),link=False)as(src,dst):dst.collections=[name]
 c=dst.collections[0];s.collection.children.link(c);old=next(o for o in c.objects if o.type=='MESH'and not o.name.startswith('UCX_'));offset=old.location.copy()
 for o in c.objects:o.location-=offset
 lo=[min(v.co[k]for v in old.data.vertices)for k in range(3)];hi=[max(v.co[k]for v in old.data.vertices)for k in range(3)];old.name='Reference_Sack_Original';c.objects.unlink(old);reference=bpy.data.collections.new('Reference_Only');reference.objects.link(old)
 def mat(name):
  m=bpy.data.materials.new(name);m.use_nodes=True;return m,m.node_tree.nodes,m.node_tree.links
 cloth,N,L=mat('MI_FeedSack_Jute_PhotoSource');bs=N.get('Principled BSDF');bs.inputs['Metallic'].default_value=0;bs.inputs['Specular IOR Level'].default_value=.22;bs.inputs['IOR'].default_value=1.46
 attr=N.new('ShaderNodeAttribute');attr.attribute_name='FabricMetric';sep=N.new('ShaderNodeSeparateXYZ');L.new(attr.outputs['Vector'],sep.inputs[0])
 def mathn(op,*args):
  n=N.new('ShaderNodeMath');n.operation=op
  for i,a in enumerate(args):
   if isinstance(a,(int,float)):n.inputs[i].default_value=a
   else:L.new(a,n.inputs[i])
  return n.outputs[0]
 warp=mathn('COSINE',mathn('MULTIPLY',sep.outputs['X'],math.tau/.0072));weft=mathn('COSINE',mathn('MULTIPLY',sep.outputs['Y'],math.tau/.0072));woven=mathn('MULTIPLY_ADD',mathn('MULTIPLY',warp,weft),.5,.5)
 scale=N.new('ShaderNodeVectorMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=(220,22,9);L.new(attr.outputs['Vector'],scale.inputs[0]);fine=N.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=1;fine.inputs['Detail'].default_value=2;L.new(scale.outputs[0],fine.inputs[0])
 macro=N.new('ShaderNodeTexNoise');macro.inputs['Scale'].default_value=4;macro.inputs['Detail'].default_value=3;L.new(attr.outputs['Vector'],macro.inputs[0]);ramp=N.new('ShaderNodeValToRGB');ramp.name='Original muted olive-tan jute';ramp.color_ramp.elements[0].color=(.048,.035,.018,1);ramp.color_ramp.elements[1].color=(.18,.14,.073,1);L.new(macro.outputs['Fac'],ramp.inputs[0])
 fibre=mathn('MULTIPLY_ADD',woven,.40,.60);mix=N.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;L.new(ramp.outputs[0],mix.inputs[1]);L.new(fibre,mix.inputs[2]);L.new(mix.outputs[0],bs.inputs['Base Color'])
 panel=N.new('ShaderNodeAttribute');panel.attribute_name='PanelTone';slub=mathn('MULTIPLY_ADD',fine.outputs['Fac'],.24,.86);panelmix=N.new('ShaderNodeMixRGB');panelmix.name='Per-panel natural jute and yarn slub';panelmix.blend_type='MULTIPLY';panelmix.inputs[0].default_value=1;L.new(mix.outputs[0],panelmix.inputs[1]);L.new(mathn('MULTIPLY',panel.outputs['Fac'],slub),panelmix.inputs[2])
 base_mask=mathn('MINIMUM',1,mathn('MAXIMUM',0,mathn('DIVIDE',mathn('SUBTRACT',.22,sep.outputs['Z']),.22)));wear=mathn('MULTIPLY_ADD',mathn('MULTIPLY',base_mask,macro.outputs['Fac']),-.34,1);soil=N.new('ShaderNodeMixRGB');soil.name='Restrained base soil and handling wear';soil.blend_type='MULTIPLY';soil.inputs[0].default_value=1;L.new(panelmix.outputs[0],soil.inputs[1]);L.new(wear,soil.inputs[2]);L.new(soil.outputs[0],bs.inputs['Base Color'])
 rough=mathn('MULTIPLY_ADD',fine.outputs['Fac'],.15,.70);L.new(rough,bs.inputs['Roughness']);height=mathn('ADD',mathn('MULTIPLY',woven,.82),mathn('MULTIPLY',fine.outputs['Fac'],.18));bump=N.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.0009;bump.inputs['Strength'].default_value=.60;L.new(height,bump.inputs['Height']);L.new(bump.outputs[0],bs.inputs['Normal'])
 cord,ns,ls=mat('MI_FeedSack_Cord_PhotoSource');pb=ns.get('Principled BSDF');pb.inputs['Base Color'].default_value=(.12,.08,.035,1);pb.inputs['Roughness'].default_value=.8;pb.inputs['Specular IOR Level'].default_value=.22
 noise=ns.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=300;bn=ns.new('ShaderNodeBump');bn.inputs['Distance'].default_value=.0003;bn.inputs['Strength'].default_value=.25;ls.new(noise.outputs['Fac'],bn.inputs['Height']);ls.new(bn.outputs[0],pb.inputs['Normal'])
 cm=ns.new('ShaderNodeAttribute');cm.attribute_name='CordMetric';split=ns.new('ShaderNodeSeparateXYZ');ls.new(cm.outputs['Vector'],split.inputs[0])
 def rope_math(op,*args):
  n=ns.new('ShaderNodeMath');n.operation=op
  for i,value in enumerate(args):
   if isinstance(value,(int,float)):n.inputs[i].default_value=value
   else:ls.new(value,n.inputs[i])
  return n.outputs[0]
 phase=rope_math('SUBTRACT',rope_math('MULTIPLY',rope_math('ARCTAN2',split.outputs['Y'],split.outputs['Z']),3),rope_math('MULTIPLY',split.outputs['X'],math.tau/.012));ply=rope_math('MULTIPLY_ADD',rope_math('COSINE',phase),.5,.5);ls.new(rope_math('ADD',rope_math('MULTIPLY',ply,.8),rope_math('MULTIPLY',noise.outputs['Fac'],.2)),bn.inputs['Height']);bn.inputs['Distance'].default_value=.00045;bn.inputs['Strength'].default_value=.55
 verts=[];faces=[];slots=[];uvs=[];cord_fields={};cord_groups=[]
 def face(indices,slot=0,uv=None):faces.append(tuple(indices));slots.append(slot);uvs.append(uv)
 keys=[(0,.19),(.035,.28),(.16,.335),(.4,.35),(.65,.30),(.80,.21),(.88,.085),(.94,.11),(.995,.07),(1,.015)]
 widths=[b[0]-a[0]for a,b in zip(keys,keys[1:])];rates=[(b[1]-a[1])/w for a,b,w in zip(keys,keys[1:],widths)];slopes=[rates[0]]
 for i in range(1,len(keys)-1):
  if rates[i-1]*rates[i]<=0:slopes.append(0.)
  else:
   w1=2*widths[i]+widths[i-1];w2=widths[i]+2*widths[i-1];slopes.append((w1+w2)/(w1/rates[i-1]+w2/rates[i]))
 slopes.append(rates[-1])
 def radius(t):
  for i,((a,x),(b,y))in enumerate(zip(keys,keys[1:])):
   if a<=t<=b:
    u=(t-a)/(b-a);h=b-a;return (2*u**3-3*u*u+1)*x+(u**3-2*u*u+u)*h*slopes[i]+(-2*u**3+3*u*u)*y+(u**3-u*u)*h*slopes[i+1]
  return keys[-1][1]
 def point(t,a,extra=0):
  r=radius(t)+.024*math.exp(-((t-.84)/.15)**2)*math.cos(10*a+.4*math.cos(5*t))*(1-.85*math.exp(-((t-.882)/.020)**2))+.008*math.sin(7*a+9*t)*(.2+.8*math.exp(-((t-.15)/.17)**2))+.004*math.sin(3*a+8*t)
  r-=.004*math.exp(-(math.sin(a)/.045)**2)*max(0,math.sin(math.pi*t))**.6
  r+=extra;x=.012*math.sin(math.pi*t);y=.007*math.sin(2*math.pi*t)
  return Vector((x+r*math.cos(a),y+r*.78*math.sin(a),t*.75+.003*math.sin(6*a)*t*(1-t)))
 segs=104;rings=65
 for j in range(rings):
  for i in range(segs):verts.append(tuple(point(j/(rings-1),i*math.tau/segs)))
 for j in range(rings-1):
  for i in range(segs):
   a=j*segs+i;b=j*segs+(i+1)%segs
   face((a,b,b+segs,a+segs),0,[(.02+.70*i/segs,.02+.68*j/(rings-1)),(.02+.70*(i+1)/segs,.02+.68*j/(rings-1)),(.02+.70*(i+1)/segs,.02+.68*(j+1)/(rings-1)),(.02+.70*i/segs,.02+.68*(j+1)/(rings-1))])
 for j,reverse in [(0,True),(rings-1,False)]:
  ids=[j*segs+i for i in range(segs)];ids=ids[::-1]if reverse else ids;center=(.85,.16 if reverse else .4)
  face(ids,0,[(center[0]+.09*math.cos((v%segs)*math.tau/segs),center[1]+.09*math.sin((v%segs)*math.tau/segs))for v in ids])
 body_faces=len(faces)
 def tube(points,w,h,slot=1,closed=False,sides=6,frame_axis=None):
  start=len(verts);count=len(points);previous_u=None;dist=0.;distances=[0.]
  for j in range(1,count):distances.append(distances[-1]+(Vector(points[j])-Vector(points[j-1])).length)
  total=distances[-1]+((Vector(points[0])-Vector(points[-1])).length if closed else 0.)
  for i,p in enumerate(points):
   tangent=(Vector(points[(i+1)%count if closed else min(i+1,count-1)])-Vector(points[(i-1)%count if closed else max(i-1,0)])).normalized();axis=Vector((0,0,1))
   if abs(tangent.dot(axis))>.94:axis=Vector((0,1,0))
   u=Vector(frame_axis(i)) if frame_axis else (previous_u if previous_u is not None else tangent.cross(axis))
   u=(u-tangent*u.dot(tangent)).normalized();v=tangent.cross(u).normalized();previous_u=u
   for k in range(sides):
    if slot==1:cord_fields[len(verts)]=(distances[i],math.sin(k*math.tau/sides),math.cos(k*math.tau/sides))
    verts.append(tuple(Vector(p)+u*w*math.cos(k*math.tau/sides)/2+v*h*math.sin(k*math.tau/sides)/2))
  for i in range(count if closed else count-1):
   for k in range(sides):face((start+i*sides+k,start+i*sides+(k+1)%sides,start+((i+1)%count)*sides+(k+1)%sides,start+((i+1)%count)*sides+k),slot)
  if slot==1:cord_groups.append({'start':start,'end':len(verts),'count':count,'sides':sides,'closed':closed,'total':total})
  if not closed:face(tuple(start+k for k in reversed(range(sides))),slot);face(tuple(start+(count-1)*sides+k for k in range(sides)),slot)
 # Two rolled stitched side seams follow the cloth, not detached vertical rails.
 for a in [0,math.pi]:
  tube([point(.025+.79*k/55,a,.0015)for k in range(56)],.009,.004,0,frame_axis=lambda i,a=a:(-math.sin(a),.78*math.cos(a),0))
  for j in range(36):
   t=.035+j*.0215;points=[point(t-.003,a-.014,.004),point(t,a,.006),point(t+.003,a+.014,.004)];tube(points,.0024,.0024,1,sides=4)
 # Two fitted neck wraps, an overhand knot and two descending ends.
 for t in [.874,.890]:
  ring=[point(t,k*math.tau/96)for k in range(96)];center=Vector(((min(p.x for p in ring)+max(p.x for p in ring))/2,(min(p.y for p in ring)+max(p.y for p in ring))/2,t*.75));rx=(max(p.x for p in ring)-min(p.x for p in ring))/2+.0045;ry=(max(p.y for p in ring)-min(p.y for p in ring))/2+.0045
  tube([center+Vector((rx*math.cos(k*math.tau/96),ry*math.sin(k*math.tau/96),0))for k in range(96)],.008,.008,1,True)
 knot=point(.884,-math.pi/2,.014)
 tube([knot+Vector((.018*math.sin(k*math.tau/40),-.006*math.cos(k*math.tau/20),.011*math.cos(k*math.tau/40)))for k in range(40)],.008,.008,1,True)
 for side in [-1,1]:
  tail=[point(.882-.20*k/20,-math.pi/2+side*(.08+.24*k/20),.012+.006*math.sin(k*math.pi/20))for k in range(21)]
  tube(tail,.007,.007,1)
  for j in range(3):
   end=tail[-1]+Vector(((j-1)*.0014,-.002,-.008-.002*j));tube([tail[-1],end],.0012,.0012,1,sides=4)

 rawlo=[min(v[k]for v in verts)for k in range(3)];rawhi=[max(v[k]for v in verts)for k in range(3)];verts=[tuple(lo[k]+(p[k]-rawlo[k])*(hi[k]-lo[k])/(rawhi[k]-rawlo[k])for k in range(3))for p in verts]
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);c.objects.link(ob);me.materials.append(cloth);me.materials.append(cord)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
 for i,p in enumerate(me.polygons):p.material_index=slots[i];p.use_smooth=True
 me.attributes.new('FabricMetric','FLOAT_VECTOR','POINT');me.attributes.new('PanelTone','FLOAT','POINT');me.attributes.new('CordMetric','FLOAT_VECTOR','CORNER')
 for i,v in enumerate(me.vertices):
  angle=math.atan2(v.co.y/.78,v.co.x);me.attributes['FabricMetric'].data[i].vector=(angle*.32,v.co.z,v.co.z/.75);me.attributes['PanelTone'].data[i].value=.94+.10*(.5+.5*math.tanh(10*math.sin(angle)))
 for poly in me.polygons:
  if poly.material_index!=1:continue
  group=next(g for g in cord_groups if g['start']<=poly.vertices[0]<g['end']);closing=group['closed']and min(poly.vertices)<group['start']+group['sides']and max(poly.vertices)>=group['start']+(group['count']-1)*group['sides']
  for li in poly.loop_indices:
   vi=me.loops[li].vertex_index;value=list(cord_fields[vi])
   if closing and vi<group['start']+group['sides']:value[0]=group['total']
   me.attributes['CordMetric'].data[li].vector=value

 me.set_sharp_from_angle(angle=math.radians(85));layer=me.uv_layers.new(name='UVMap')
 # Coherent principal cloth chart. Small attachments get a separate packed region.
 for i,p in enumerate(me.polygons):
  if uvs[i]:
   # Normal recalculation can reverse polygon loops; match UVs by vertex identity.
   byid={v:uv for v,uv in zip(faces[i],uvs[i])}
   for li in p.loop_indices:layer.data[li].uv=byid[me.loops[li].vertex_index]
 bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.context.tool_settings.mesh_select_mode=(False,False,True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
 for p in me.polygons:p.select=p.index>=body_faces
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.uv.smart_project(angle_limit=1.0,island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT');me=ob.data;layer=me.uv_layers.active
 for p in me.polygons:
  if p.index>=body_faces:
   for li in p.loop_indices:layer.data[li].uv=(.02+layer.data[li].uv.x*.94,.74+layer.data[li].uv.y*.24)
 c['dink_class']='prop';c['dink_path']='Stonebrook/PhotorealFeedSackV1';c['dink_nanite']='yes';c['dink_tex_px']=2048;c['dink_source']='Original422_12 grain sack/S001_P52/s1-sack; project authoredcloth and cord'
 for o in c.objects:
  if o.name.startswith('UCX_'):o.hide_render=True
 refscene=bpy.data.scenes.new('SackReference');refscene.collection.children.link(reference)
 for image in bpy.data.images:
  if image.source=='FILE':image.reload();image.pack()
 tri=sum(len(p.vertices)-2 for p in me.polygons);assert tri<20000,tri
 report={'candidate':True,'reference':'Originalsprite422_12 +s1-sack script grain/feedpickup S001_P52','input_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'triangles':tri,'old_bounds_m':[lo,hi],'materials':['jute','cord'],'construction':'Bounded finish: monotonic smooth shoulders/compressed seams/coarse jute slub/panel tone/taut three-ply cord with exposed ends; full cloth body with gathered pleats, flattened footing, rolled side seams,72stitches, fittedtwowraptie/knot/ends','native_imported':False,'remaining':['Sourceguide/UV/physicalcontact review','Matchedoriginal/current source renders','Bake/export/roundtrip and native tests']}
 (O/'source_report.json').write_text(json.dumps(report,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealFeedSackV1_Source.blend'));print('SACK_SOURCE_BUILT',tri,flush=True)
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
