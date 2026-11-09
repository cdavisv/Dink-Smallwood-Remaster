import bpy,sys,os,json,hashlib,math
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O/'Pipeline'))
from dinkasset.validate import uv_stats
try:
 source=O/'PhotorealPieV1_Source.blend';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pin=sha(source);bpy.ops.wm.open_mainfile(filepath=str(source));rows=[]
 for ob in bpy.data.collections['SM_Pie_Rustic_01'].objects:
  if ob.type!='MESH':continue
  me=ob.data;assert all(math.isfinite(v)for p in me.vertices for v in p.co);st=uv_stats(me,max_pairs=10000000);assert not st['truncated'];assert st['degenerate_tris']==st['tris_out_of_range']==0,st
  if ob.name.endswith('_LOD0'):assert st['overlapping_tris']==0,st
  else:assert st['overlap_ratio']<=.002,st
  assert len(me.materials)==2;optics={}
  for mat in me.materials:
   bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');assert bs.inputs['Metallic'].default_value==0;optics[mat.name]={k:bs.inputs[k].default_value for k in ['IOR','Specular IOR Level','Coat Weight','Coat Roughness']}
  assert set(['FruitMask','Browning'])<=set(a.name for a in me.attributes)
  rows.append({'name':ob.name,'triangles':sum(len(p.vertices)-2 for p in me.polygons),'UV':st,'material_optics':optics})
 assert len(rows)==3 and sha(source)==pin
 (O/'finish_verification.json').write_text(json.dumps({'passed':True,'source_sha256':pin,'LODs':rows,'limits':'LOD0zerooverlap required; decimatedLODs use class0.2%overlap threshold with actual values retained. UV/material/finite checks are not universal contact or native approval.'},indent=2)+'\n')
except BaseException:
 import traceback;traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
