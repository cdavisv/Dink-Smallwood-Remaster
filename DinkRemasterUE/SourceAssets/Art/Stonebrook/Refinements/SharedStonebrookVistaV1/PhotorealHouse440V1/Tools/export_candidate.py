"""Export separately; waive ONLY the recorded render-only UCX error, never setup failures."""
from pathlib import Path
import argparse,json,sys,os,runpy,traceback
sys.dont_write_bytecode=True
def main():
 p=argparse.ArgumentParser();p.add_argument('--bundle',default=str(Path(__file__).resolve().parents[1]));p.add_argument('--out',required=True);p.add_argument('--report',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[]);B=Path(a.bundle).resolve();out=Path(a.out).resolve();report=Path(a.report).resolve();assert not out.is_relative_to(B)and not report.is_relative_to(B),'Write outputs outside frozen input';h=json.loads((B/'HANDOFF.json').read_text());sys.path.insert(0,str(B/'Tools'));import bpy
 from dinkasset import validate
 bpy.ops.wm.open_mainfile(filepath=str(B/h['source_file']));raw=validate.validate_scene(only=['SM_Shared_House440_01']);errors=[f for asset in raw['assets']for f in asset['findings']if f['severity']=='error'];assert len(errors)==1 and errors[0]['code']=='COLLISION_MISSING',errors;tool=B/'Tools/dinkasset/export_ue.py';sys.argv=[str(tool),'--','--blend',str(B/h['source_file']),'--collection','SM_Shared_House440_01','--out',str(out),'--formats','fbx,gltf','--force','--source-root',str(B),'--report',str(report)];runpy.run_path(str(tool),run_name='__main__')
code=0
try:main()
except SystemExit as e:code=e.code if isinstance(e.code,int)else 1
except BaseException:traceback.print_exc();code=1
finally:sys.stdout.flush();sys.stderr.flush();os._exit(code)
