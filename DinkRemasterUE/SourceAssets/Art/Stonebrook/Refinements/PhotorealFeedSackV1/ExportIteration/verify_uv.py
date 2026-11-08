import bpy,sys,json,os,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O/'Pipeline'))
from dinkasset.validate import uv_stats
try:
 rows={}
 for kind in ['Source','Export']:
  p=O/('PhotorealFeedSackV1_'+kind+'.blend');bpy.ops.wm.open_mainfile(filepath=str(p));ob=bpy.data.objects['SM_FeedSack_Jute_01'];s=uv_stats(ob.data,max_pairs=10000000)
  assert not s['truncated'],s
  assert s['overlapping_tris']==s['degenerate_tris']==s['tris_out_of_range']==0,s
  rows[kind]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'uv':s}
 (O/'uv_verification.json').write_text(json.dumps({'passed':True,'files':rows},indent=2)+'\n')
except BaseException:
 import traceback;traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
