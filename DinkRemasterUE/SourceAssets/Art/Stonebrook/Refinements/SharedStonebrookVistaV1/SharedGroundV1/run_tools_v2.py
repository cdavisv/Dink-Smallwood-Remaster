import sys,os,runpy,traceback
from pathlib import Path
sys.dont_write_bytecode=True;O=Path(__file__).resolve().parent;mode=os.environ.get('GROUND_TOOL','validate');tool=O/'Tools/dinkasset'/('validate.py'if mode=='validate'else'export_ue.py');args=['--blend',str(O/'SharedGroundGameV2.blend'),'--report',str(O/('guide_raw_v2.json'if mode=='validate'else'export_report_v2.json'))]
if mode!='validate':
 import json,hashlib
 receipt=json.loads((O/'qualified_terrain_policy_v2.json').read_text());assert receipt['source_sha256']==hashlib.sha256((O/'SharedGroundGameV2.blend').read_bytes()).hexdigest()and receipt['unexpected_errors']==0 and receipt['expected_policy_error_count']==130
 assert receipt['raw_guide_sha256']==hashlib.sha256((O/'guide_raw_v2.json').read_bytes()).hexdigest()
 assert receipt['geometry_audit_sha256']==hashlib.sha256((O/'geometry_audit_v2.json').read_bytes()).hexdigest()
if mode!='validate':args+=['--out',str(O/'ExportV2'),'--formats','fbx','--source-root',str(O),'--force']
sys.argv=[str(tool),'--']+args;code=0
try:runpy.run_path(str(tool),run_name='__main__')
except SystemExit as e:code=e.code if isinstance(e.code,int)else 1
except BaseException:traceback.print_exc();code=2
finally:sys.stdout.flush();sys.stderr.flush();os._exit(code)
