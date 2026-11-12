import bpy,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parents[1];records=[]
for filename in ['SharedThinWavyGlass_Source.blend','GenericReuse_2m4m.blend']:
 bpy.ops.wm.open_mainfile(filepath=str(D/filename));m=bpy.data.materials['MI_Shared_ThinWavyGlass2m'];p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');assert abs(p.inputs['IOR'].default_value-1.48)<1e-6;assert p.inputs['Transmission Weight'].default_value==1;assert p.inputs['Thin Wall'].default_value==1;maps=[]
 for n in m.node_tree.nodes:
  assert n.type not in ['ATTRIBUTE','TEX_COORD'],'Private/world position mapping forbidden'
  if n.type=='TEX_IMAGE':
   im=n.image;path=D/'Textures'/im.name;assert path.is_file();assert im.packed_file;sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==hashlib.sha256(bytes(im.packed_file.data)).hexdigest();maps.append({'image':im.name,'sha256':sha,'packed':True,'file_local':True})
 assert len(maps)==3
 surfaces=[]
 if filename.startswith('Generic'):
  for name,width in [('Glass2m',2),('Glass4m',4)]:
   o=bpy.data.objects[name];assert o.data.materials[0]==m;u=o.data.uv_layers['UV0'];assert abs(max(x.uv.x for x in u.data)-width/2)<1e-6;surfaces.append(name)
 else:assert len(bpy.data.objects)==0
 records.append({'file':filename,'maps':maps,'surfaces':surfaces})
(D/'VERIFY_REGISTERED.json').write_text(json.dumps({'status':'PASS_packed_local_maps_parameters_and_independent_reuse','records':records,'scope':'Source-only; no native or final appearance acceptance'},indent=2)+'\n');print('REGISTERED_GLASS_VERIFY_PASS')
