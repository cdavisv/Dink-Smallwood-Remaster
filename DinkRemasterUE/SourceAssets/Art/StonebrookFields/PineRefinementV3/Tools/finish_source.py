import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(ROOT/'PineRefinementV3.blend'))
for im in bpy.data.images:
 if im.filepath:im.name=Path(im.filepath).stem
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'PineRefinementV3.blend'),relative_remap=False)
