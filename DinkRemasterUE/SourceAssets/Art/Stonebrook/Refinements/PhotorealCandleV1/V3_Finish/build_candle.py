"""QA-only turned iron holder and used wax candle; no exported flame/light changes."""
import bpy,bmesh,math,os,sys,json,hashlib,random,traceback
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent;P=O/'Inputs/KIT_Stonebrook_Input.blend';name='SM_Candle_Iron_01'
try:
 bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.name='CandleSource';s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;bpy.context.preferences.filepaths.save_version=0
 with bpy.data.libraries.load(str(P),link=False)as(src,dst):dst.collections=[name]
 c=dst.collections[0];s.collection.children.link(c);old=next(o for o in c.objects if o.type=='MESH'and not o.name.startswith('UCX_'));offset=old.location.copy()
 for o in c.objects:o.location-=offset
 low=[min(v.co[k]for v in old.data.vertices)for k in range(3)];high=[max(v.co[k]for v in old.data.vertices)for k in range(3)];old.name='Reference_Candle_Original';c.objects.unlink(old);ref=bpy.data.collections.new('Reference_Only');ref.objects.link(old)
 def material(label):
  m=bpy.data.materials.new(label);m.use_nodes=True;return m,m.node_tree.nodes,m.node_tree.links
 iron,N,L=material('MI_Candle_IronChar_PhotoSource');bs=N.get('Principled BSDF');noise=N.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=28;noise.inputs['Detail'].default_value=3;grain=N.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=750;grain.inputs['Detail'].default_value=2
 ramp=N.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.006,.007,.008,1);ramp.color_ramp.elements[1].color=(.017,.018,.019,1);L.new(noise.outputs['Fac'],ramp.inputs[0]);wick=N.new('ShaderNodeAttribute');wick.attribute_name='WickMask'
 color=N.new('ShaderNodeMixRGB');color.inputs[2].default_value=(.0018,.0012,.0008,1);L.new(wick.outputs['Fac'],color.inputs[0]);L.new(ramp.outputs[0],color.inputs[1]);L.new(color.outputs[0],bs.inputs['Base Color'])
 metal=N.new('ShaderNodeMath');metal.operation='SUBTRACT';metal.inputs[0].default_value=.93;L.new(wick.outputs['Fac'],metal.inputs[1]);metal.use_clamp=True;L.new(metal.outputs[0],bs.inputs['Metallic'])
 rough=N.new('ShaderNodeMix');rough.data_type='FLOAT';rough.inputs[2].default_value=.54;rough.inputs[3].default_value=.96;L.new(wick.outputs['Fac'],rough.inputs[0]);L.new(rough.outputs[0],bs.inputs['Roughness']);variation=N.new('ShaderNodeMapRange');variation.inputs['To Min'].default_value=.45;variation.inputs['To Max'].default_value=.62;L.new(noise.outputs['Fac'],variation.inputs[0]);L.new(variation.outputs[0],rough.inputs[2]);bump=N.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.000025;bump.inputs['Strength'].default_value=.18;L.new(grain.outputs['Fac'],bump.inputs['Height']);L.new(bump.outputs[0],bs.inputs['Normal'])
 coord=N.new('ShaderNodeTexCoord');L.new(coord.outputs['Object'],noise.inputs['Vector']);L.new(coord.outputs['Object'],grain.inputs['Vector'])
 wax,N,L=material('MI_Candle_Wax_PhotoSource');bs=N.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.48,.355,.18,1);bs.inputs['IOR'].default_value=1.44;bs.inputs['Specular IOR Level'].default_value=.30;bs.inputs['Subsurface Weight'].default_value=.12;bs.inputs['Subsurface Scale'].default_value=.008
 pool=N.new('ShaderNodeAttribute');pool.attribute_name='WaxPool';rough=N.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.45;rough.inputs['To Max'].default_value=.12;L.new(pool.outputs['Fac'],rough.inputs[0]);L.new(rough.outputs[0],bs.inputs['Roughness']);noise=N.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=460;noise.inputs['Detail'].default_value=2;bump=N.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00012;bump.inputs['Strength'].default_value=.22;L.new(noise.outputs['Fac'],bump.inputs['Height']);L.new(bump.outputs[0],bs.inputs['Normal'])
 coord=N.new('ShaderNodeTexCoord');L.new(coord.outputs['Object'],noise.inputs['Vector']);tone=N.new('ShaderNodeValToRGB');tone.color_ramp.elements[0].color=(.44,.32,.17,1);tone.color_ramp.elements[1].color=(.50,.38,.22,1);broad=N.new('ShaderNodeTexNoise');broad.inputs['Scale'].default_value=22;broad.inputs['Detail'].default_value=1;L.new(coord.outputs['Object'],broad.inputs['Vector']);L.new(broad.outputs['Fac'],tone.inputs[0]);L.new(tone.outputs[0],bs.inputs['Base Color'])
 verts=[];faces=[];slots=[];wickmask=[];poolmask=[]
 def vertex(p,wick=0,pool=0):i=len(verts);verts.append(tuple(p));wickmask.append(wick);poolmask.append(pool);return i
 def face(ids,slot):faces.append(tuple(ids));slots.append(slot)
 profile=[(.090,0),(.100,.004),(.099,.013),(.094,.025),(.065,.035),(.029,.045),(.016,.065),(.013,.220),(.021,.240),(.056,.250),(.073,.255),(.075,.265),(.070,.270),(.066,.267),(.060,.258),(.020,.254),(.014,.252)]
 seg=32
 for r,z in profile:
  for i in range(seg):a=i*math.tau/seg;vertex((r*math.cos(a),r*math.sin(a),z))
 for j in range(len(profile)-1):
  for i in range(seg):a=j*seg+i;b=j*seg+(i+1)%seg;face((a,b,b+seg,a+seg),0)
 face(tuple(reversed(range(seg))),0);face(tuple((len(profile)-1)*seg+i for i in range(seg)),0)
 # Integral wax surface with a rounded runout at each drip endpoint.
 seg=80;start=len(verts);levels=[.256,.280,.300,.315,.330,.355,.365,.375,.385,.405,.412,.418,.423,.428,.433,.437,.440,.443]
 drips=[]
 for j,z0 in enumerate(levels):
  for i in range(seg):
   a=i*math.tau/seg;z=z0+(j/(len(levels)-1))**7*(.0011*math.sin(3*a)+.0006*math.sin(7*a));r=.0435+.0006*math.sin(5*a+z*12)
   for angle,end,amount in drips:
    d=(a-angle+math.pi)%math.tau-math.pi;trail=1/(1+math.exp(max(-60,min(60,-(z-end)/.003))));drop=math.exp(-((z-end)/.005)**2)*.65;r+=amount*math.exp(-(d/.16)**2)*(trail+drop)
   vertex((r*math.cos(a),r*math.sin(a),z),pool=.15 if j==len(levels)-1 else 0)
 for j in range(len(levels)-1):
  for i in range(seg):a=start+j*seg+i;b=start+j*seg+(i+1)%seg;face((a,b,b+seg,a+seg),1)
 face(tuple(start+i for i in reversed(range(seg))),1)
 for radius,z in [(.042,.442),(.029,.433),(.012,.429)]:
  last=len(verts)-seg;first=len(verts)
  for i in range(seg):a=i*math.tau/seg;vertex((radius*math.cos(a),radius*math.sin(a),z+.0003*math.sin(4*a)),pool=1)
  for i in range(seg):face((last+i,last+(i+1)%seg,first+(i+1)%seg,first+i),1)
 last=len(verts)-seg;center=vertex((0,0,.4285),pool=1)
 for i in range(seg):face((last+i,last+(i+1)%seg,center),1)
 # Three gravity-fed wax rivulets, embedded at the back in the main wax wall.
 for angle,end,width in [(-1.1,.338,.0032),(-.35,.382,.0026),(-2.0,.365,.0028)]:
  start=len(verts);rings=8;sides=8
  for j in range(rings):
   t=[0,.025,.06,.18,.4,.65,.85,1][j];z=end+(.442-end)*t;a=angle+.035*math.sin(t*math.pi)
   r=.0435+.0006*math.sin(5*a+z*12)+width*.25
   # Rounded bottom termination; top blends into lip rather than ending in free space.
   radius=width*[.12,.8,1,.8,.65,.65,.75,.9][j]
   for k in range(sides):
    phase=k*math.tau/sides
    vertex(((r+radius*math.cos(phase))*math.cos(a),(r+radius*math.cos(phase))*math.sin(a),z+radius*math.sin(phase)),pool=.15)
  for j in range(rings-1):
   for k in range(sides):
    a=start+j*sides+k;b=start+j*sides+(k+1)%sides;face((a,b,b+sides,a+sides),1)
  face(tuple(start+k for k in reversed(range(sides))),1);face(tuple(start+(rings-1)*sides+k for k in range(sides)),1)
 # Charred curled wick, differentiated inside the iron material without a third slot.
 start=len(verts);points=[Vector((.002*k/4,-.001*math.sin(k*math.pi/4),.437+.0135*k/4))for k in range(5)];sides=6
 for i,p in enumerate(points):
  tangent=(points[min(i+1,4)]-points[max(i-1,0)]).normalized();u=tangent.cross(Vector((0,1,0))).normalized();v=tangent.cross(u)
  for k in range(sides):vertex(p+.0012*(u*math.cos(k*math.tau/sides)+v*math.sin(k*math.tau/sides)),wick=1)
 for j in range(4):
  for i in range(sides):a=start+j*sides+i;b=start+j*sides+(i+1)%sides;face((a,b,b+sides,a+sides),0)
 face(tuple(start+i for i in reversed(range(sides))),0);face(tuple(start+4*sides+i for i in range(sides)),0)
 rawlo=[min(v[k]for v in verts)for k in range(3)];rawhi=[max(v[k]for v in verts)for k in range(3)];verts=[tuple(low[k]+(p[k]-rawlo[k])*(high[k]-low[k])/(rawhi[k]-rawlo[k])for k in range(3))for p in verts]
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);c.objects.link(ob);me.materials.append(iron);me.materials.append(wax)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
 me.attributes.new('WickMask','FLOAT','POINT');me.attributes.new('WaxPool','FLOAT','POINT')
 for i in range(len(verts)):me.attributes['WickMask'].data[i].value=wickmask[i];me.attributes['WaxPool'].data[i].value=poolmask[i]
 for p in me.polygons:p.material_index=slots[p.index];p.use_smooth=True
 me.set_sharp_from_angle(angle=math.radians(70));bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.0,island_margin=.003);bpy.ops.object.mode_set(mode='OBJECT')
 c['dink_class']='prop_small';c['dink_path']='Stonebrook/PhotorealCandleV1';c['dink_nanite']='no';c['dink_tex_px']=2048;c['dink_source']='Project-authored addedroomprop; wax melt/drips and iron/char; originalbounds/lightanchor retained'
 refscene=bpy.data.scenes.new('CandleReference');refscene.collection.children.link(ref)
 for image in bpy.data.images:
  if image.source=='FILE':image.reload();image.pack()
 tri=sum(len(p.vertices)-2 for p in me.polygons);assert tri<=5000,tri
 (O/'source_report.json').write_text(json.dumps({'candidate':True,'triangles':tri,'materials':2,'original_bounds_m':[low,high],'original_reference':'Existing added candle table/mantel prop; no directoriginalsprite claimed','source_input_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'wax_subsurface_weight':.12,'wax_subsurface_scale_m':.008,'charredwick_metallic':0,'native_imported':False,'limits':['No flame exported or pointlights changed; nativeflame VFX remains required','Wax subsurface is source shader evidence; defaultLitBC/N/ORM alone cannot establish nativewax appearance','No universal cross-part intersection-free claim']},indent=2)+'\n')
 bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealCandleV1_Source.blend'));print('CANDLE_SOURCE_BUILT',tri,flush=True)
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
