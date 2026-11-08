import bpy,json
from pathlib import Path
root = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root / 'Inputs/Original_OakFurnitureV1.blend'))
r={}
for n in ['SM_Table_Oak_01','SM_Chair_Oak_01','SM_Bed_Oak_01']:
 m=bpy.data.meshes[n+'_Mesh'];r[n]={'instances':[{ 'name':o.name,'location':list(o.location),'collections':[c.name for c in o.users_collection],'hide_render':o.hide_render}for o in bpy.data.objects if o.type=='MESH' and o.data==m], 'collections': [c.name for c in bpy.data.collections if n in c.name]}
(root / 'inspection.json').write_text(json.dumps(r,indent=2))
