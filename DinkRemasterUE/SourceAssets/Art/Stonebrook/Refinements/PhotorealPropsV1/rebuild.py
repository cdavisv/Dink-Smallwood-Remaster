#!/usr/bin/env python3
"""Rebuild this portable art candidate; requires Blender5.2.2. All writes stay in bundle."""
import argparse,subprocess,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--blender',default='blender');a=p.parse_args();root=a.root.resolve();env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='4';env['OMP_NUM_THREADS']='4';env.pop('PROPS_AFTER_ONLY',None)
for script in ['build_props.py','chamfer_table.py','bake_export.py','export_driver.py','render_props.py','roundtrip.py','finalize_validation.py','check_portable.py']:
 with (root/(Path(script).stem+'.rebuild.log')).open('w')as log:subprocess.run([a.blender,'-b','-t','4','-P',str(root/script)],stdout=log,stderr=subprocess.STDOUT,env=env,check=True,timeout=1200)
 print('Complete:',script,flush=True)
