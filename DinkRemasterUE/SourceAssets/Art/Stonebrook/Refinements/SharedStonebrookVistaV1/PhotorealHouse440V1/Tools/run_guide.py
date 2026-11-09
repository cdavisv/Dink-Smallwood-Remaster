"""Run the copied actual guide; retain raw exceptions and return failure honestly."""
from pathlib import Path
import argparse,json,sys,os,runpy,traceback
sys.dont_write_bytecode=True
def main():
 p=argparse.ArgumentParser();p.add_argument('--bundle',default=str(Path(__file__).resolve().parents[1]));p.add_argument('--report',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[]);B=Path(a.bundle).resolve();out=Path(a.report).resolve();assert not out.is_relative_to(B),'Report must be outside frozen source';h=json.loads((B/'HANDOFF.json').read_text());sys.path.insert(0,str(B/'Tools'));tool=B/'Tools/dinkasset/validate.py';sys.argv=[str(tool),'--','--blend',str(B/h['source_file']),'--collection','SM_Shared_House440_01','--report',str(out)];runpy.run_path(str(tool),run_name='__main__')
code=0
try:main()
except SystemExit as e:code=e.code if isinstance(e.code,int)else 1
except BaseException:traceback.print_exc();code=1
finally:sys.stdout.flush();sys.stderr.flush();os._exit(code)
