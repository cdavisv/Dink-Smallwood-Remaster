"""Re-save every source .blend under Unclaimed with scrubbed paths and texture datablocks named T_<Name>_<BC|N|ORM> (tools/bl.sh resave.py)."""
import bpy, glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
for p in sorted(glob.glob(os.path.join(L.UNC, '*', '*', '*.blend'))):
    bpy.ops.wm.open_mainfile(filepath=p)
    for im in bpy.data.images:
        if im.name.startswith('T_') and im.name.lower().endswith('.png'):
            im.name = im.name[:-4]
    L.save_blend(); print('RESAVED', p)
