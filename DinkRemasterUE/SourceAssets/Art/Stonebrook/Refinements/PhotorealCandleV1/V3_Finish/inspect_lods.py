import bpy,json,sys,os
from pathlib import Path
O=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealCandleV1_LODs.blend'))
c=bpy.data.collections['SM_Candle_Iron_01'];rows=[]
for ob in c.objects:
 if ob.type!='MESH' or ob.name.startswith('UCX_'):continue
 ob.hide_render=not ob.name.endswith('_LOD0');me=ob.data
 rows.append({'name':ob.name,'triangles':sum(len(p.vertices)-2 for p in me.polygons),'bounds':[[min(v.co[k]for v in me.vertices)for k in range(3)],[max(v.co[k]for v in me.vertices)for k in range(3)]],'wick_vertices':sum(v.value>.9 for v in me.attributes['WickMask'].data),'wax_pool_vertices':sum(v.value>.8 for v in me.attributes['WaxPool'].data)})
(O/'lod_inspection.json').write_text(json.dumps(rows,indent=2)+'\n');bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealCandleV1_Source.blend'));print(json.dumps(rows,indent=2));sys.stdout.flush();os._exit(0)
