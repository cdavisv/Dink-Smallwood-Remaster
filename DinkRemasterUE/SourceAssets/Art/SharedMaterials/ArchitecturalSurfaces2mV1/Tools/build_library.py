"""Material-only source extraction and independent reuse scene; output inside this library."""
import bpy,json,hashlib,math,sys
from pathlib import Path
from mathutils import Vector
D=Path(__file__).resolve().parents[1];config=json.load((D/'registry.json').open());external='--donor'in sys.argv;donor=Path(sys.argv[sys.argv.index('--donor')+1]).resolve()if external else D/'SharedArchitecturalSurfaces_Source.blend';donor_sha=hashlib.sha256(donor.read_bytes()).hexdigest();bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(donor),link=False)as(a,b):b.materials=list(config['source_material_aliases'])if external else list(config['source_material_aliases'].values())
def fingerprint(m):
 rows=[]
 for n in m.node_tree.nodes:
  vals=[]
  for s in n.inputs:
   value=getattr(s,'default_value',None)
   if value is None:continue
   try:value=list(value)
   except TypeError:
    try:value=float(value)
    except (TypeError,ValueError):value=str(value)
   vals.append((s.name,value))
  rows.append((n.name,n.type,getattr(n,'operation',None),getattr(n,'uv_map',None),getattr(n,'layer_name',None),getattr(n,'attribute_name',None),vals,hashlib.sha256(bytes(n.image.packed_file.data)).hexdigest()if n.type=='TEX_IMAGE'and n.image and n.image.packed_file else None))
 links=[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name)for l in m.node_tree.links];return hashlib.sha256(json.dumps([rows,links],sort_keys=True).encode()).hexdigest()
proof=[];mats={}
for old,new in config['source_material_aliases'].items():
 m=bpy.data.materials[old if external else new];before=fingerprint(m);key=new.removeprefix('MI_Shared_');entry=config['roles'][key];allowed={info['sha256']:D.parent/info['file']for var in entry['variants'].values()for info in var['textures'].values()}
 for n in m.node_tree.nodes:
  if n.type=='ATTRIBUTE':assert not n.attribute_name.startswith('House439')
  if n.type=='TEX_IMAGE'and n.image:
   im=n.image;sha=hashlib.sha256(bytes(im.packed_file.data)).hexdigest();path=allowed[sha];assert path.is_file()and hashlib.sha256(path.read_bytes()).hexdigest()==sha;im.filepath=bpy.path.relpath(str(path),start=str(D));im.name=path.name
 m.name=new;m.use_fake_user=True;m['repeat_m']=2.;m['nominal_texels_per_m']=512;after=fingerprint(m);assert before==after;proof.append({'old_name':old,'registered_material':new,'shader_pixel_fingerprint_exact':before});mats[key]=m
if external:bpy.ops.wm.save_as_mainfile(filepath=str(D/'SharedArchitecturalSurfaces_Source.blend'),compress=True)
# Independent 2m and4m surfaces, both at1024px/2m physicalscale; compositeroles exercised separately.
variants=[(k,v['selector'],name)for k,r in config['roles'].items()for name,v in r['variants'].items()];receipt=[]
for index,(key,selector,name)in enumerate(variants):
 col=index%3;row=index//3
 for width,yoff in [(2.,1.3),(4.,-1.3)]:
  x=col*5.;y=row*5.5+yoff;verts=[(x-width/2,y-1,0),(x+width/2,y-1,0),(x+width/2,y+1,0),(x-width/2,y+1,0)];mesh=bpy.data.meshes.new(f'{key}_{name}_{width}m');mesh.from_pydata(verts,[],[(0,1,2,3)]);mesh.update();o=bpy.data.objects.new(mesh.name,mesh);bpy.context.scene.collection.objects.link(o);mesh.materials.append(mats[key]);uv=mesh.uv_layers.new(name='UV0');role=mesh.uv_layers.new(name='UV1_SharedData');c=mesh.color_attributes.new(name='SharedSurfaceData',type='FLOAT_COLOR',domain='CORNER')
  for i,xy in enumerate([(0,0),(width/2,0),(width/2,1),(0,1)]):uv.data[i].uv=xy;role.data[i].uv=(selector,0);c.data[i].color=(.5,1,1,1)if key=='FieldstoneSeed2m'else(.44,.41,.35,1)if key=='LimeMortarSoot2m'and selector==0 else(1,1,1,1)
  receipt.append({'object':o.name,'material':mats[key].name,'variant':name,'width_m':width,'height_m':2,'UV0_extent':[width/2,1],'UV1_role':selector})
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=1600;s.render.resolution_y=1600;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('ReuseNeutral');s.world.use_nodes=True;s.world.node_tree.nodes.get('Background').inputs[0].default_value=(.5,.5,.5,1);s.world.node_tree.nodes.get('Background').inputs[1].default_value=.7;light=bpy.data.lights.new('ReuseKey','AREA');light.energy=6000;light.size=10;o=bpy.data.objects.new('ReuseKey',light);s.collection.objects.link(o);o.location=(1,-3,15);o.rotation_euler=(Vector((5,5.5,0))-o.location).to_track_quat('-Z','Y').to_euler();camdata=bpy.data.cameras.new('ReuseCamera');cam=bpy.data.objects.new('ReuseCamera',camdata);s.collection.objects.link(cam);cam.location=(5,-1,26);cam.rotation_euler=(Vector((5,5.5,0))-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=19;s.camera=cam
bpy.ops.wm.save_as_mainfile(filepath=str(D/'GenericReuse_2m4m.blend'),compress=True);(D/'Review').mkdir(exist_ok=True);s.render.filepath=str(D/'Review/generic_2m4m.png');bpy.ops.render.render(write_still=True);assert hashlib.sha256(donor.read_bytes()).hexdigest()==donor_sha
(D/'NORMALIZATION.json').write_text(json.dumps({'status':'PASS_material_graphs_and_packed_pixels_exact_onlynames_pathsnormalized','donor_sha256_unchanged':donor_sha,'materials':proof,'reuse_surfaces':receipt,'scope':'Independent18planes/9variants; no cottagegeometry/UVatlas inlibrary. Actualrenderneedsinspection; notnativeacceptance.','recipe_qualification':'Extractionuseshistoricaldonor forrebuild; packedlibrary/reuse scenes selfcontained andrelocatable. No fakefullyreproducibleexternal scanprocessing claim.'},indent=2)+'\n')
