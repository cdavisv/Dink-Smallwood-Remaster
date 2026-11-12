"""Re-save every source .blend under Unclaimed with scrubbed paths (tools/bl.sh resave.py)."""
import bpy, glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
for p in sorted(glob.glob(os.path.join(L.UNC, '*', '*', '*.blend'))):
    bpy.ops.wm.open_mainfile(filepath=p); L.save_blend(); print('RESAVED', p)
