import bpy,sys,os,json,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O/'Pipeline'))
from dinkasset.validate import uv_stats
try:
 p=O/'PhotorealCandleV1_Source.blend';pin=hashlib.sha256(p.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(p));rows=[]
 for ob in bpy.data.collections['SM_Candle_Iron_01'].objects:
  if ob.type!='MESH':continue
  me=ob.data;s=uv_stats(me,max_pairs=10000000);assert not s['truncated'];assert s['degenerate_tris']==s['tris_out_of_range']==0,s
  if ob.name.endswith('_LOD0'):assert s['overlapping_tris']==0,s
  else:assert s['overlap_ratio']<=.002,s
  assert len(me.materials)==2
  wax=me.materials[1];bs=next(n for n in wax.node_tree.nodes if n.type=='BSDF_PRINCIPLED');assert abs(bs.inputs['IOR'].default_value-1.44)<1e-6;assert abs(bs.inputs['Subsurface Weight'].default_value-.12)<1e-6
  rows.append({'object':ob.name,'triangles':sum(len(p.vertices)-2 for p in me.polygons),'uv':s,'wax_IOR':bs.inputs['IOR'].default_value,'wax_SSS':bs.inputs['Subsurface Weight'].default_value})
 assert len(rows)==3;assert hashlib.sha256(p.read_bytes()).hexdigest()==pin
 (O/'finish_verification.json').write_text(json.dumps({'passed':True,'source_sha256':pin,'LODs':rows,'limits':'LOD0 requires zero overlap; decimated LODs use class threshold 0.2 percent and retain actual measured overlap. UV/material checks only; deliberate wax/drip contact is not universal intersection-free or native approval.'},indent=2)+'\n')
except BaseException:
 import traceback;traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
