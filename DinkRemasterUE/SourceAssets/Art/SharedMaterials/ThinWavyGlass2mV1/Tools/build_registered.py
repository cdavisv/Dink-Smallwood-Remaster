import bpy,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(D/'Provenance/ThinWavyGlass2m_BakedSource.blend'))
m=bpy.data.materials['MI_Candidate_ThinWavyGlass2m_Baked'];before={}
for node in m.node_tree.nodes:
 if node.type=='TEX_IMAGE':
  im=node.image;role='N_GL'if'N_GL'in im.name else'ORM'if'ORM'in im.name else'BC';p=D/'Textures'/f'T_Shared_ThinWavyGlass2m_{role}.png';sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha==hashlib.sha256(bytes(im.packed_file.data)).hexdigest();before[role]=sha;im.filepath=bpy.path.relpath(str(p),start=str(D));im.name=p.name
m.name='MI_Shared_ThinWavyGlass2m';m['repeat_m']=2.;m['native_status']='pending';m['optics']='physical thin wall; closed pane front/back policy requires review';bpy.ops.wm.save_as_mainfile(filepath=str(D/'SharedThinWavyGlass_Source.blend'),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(D/'Provenance/ThinGlassBakedReuse_2m4m.blend'))
with bpy.data.libraries.load(str(D/'SharedThinWavyGlass_Source.blend'),link=False)as(a,b):b.materials=['MI_Shared_ThinWavyGlass2m']
m=bpy.data.materials['MI_Shared_ThinWavyGlass2m']
for name in ['Glass2m','Glass4m']:bpy.data.objects[name].data.materials[0]=m
for material in list(bpy.data.materials):
 if material.name.startswith('MI_Candidate_'):bpy.data.materials.remove(material,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(D/'GenericReuse_2m4m.blend'),compress=True)
(D/'REGISTRATION.json').write_text(json.dumps({'status':'SOURCE_REGISTERED_NATIVE_PENDING','material':m.name,'maps_bytes_identical_to_reviewed_bake':before,'reuse_objects':['Glass2m','Glass4m'],'scope':'Only material names/resource paths normalized; no cottage or native changes.'},indent=2)+'\n')
