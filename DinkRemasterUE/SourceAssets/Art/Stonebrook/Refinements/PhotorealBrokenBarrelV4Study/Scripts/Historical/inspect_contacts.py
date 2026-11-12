import bpy,json,os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
Q=Path(__file__).resolve().parent;P=Path('<HOME>/Work/DinkQA/PhotorealBrokenBarrelCurvatureV4/PhotorealBrokenBarrelV4_CurvedSource.blend');bpy.ops.wm.open_mainfile(filepath=str(P),load_ui=False,use_scripts=False);bpy.context.view_layer.update();obs=list(bpy.data.collections['V4_CooperedFragments_Editable'].objects)
def data(o):
 me=o.data;me.calc_loop_triangles();vs=[o.matrix_world@v.co for v in me.vertices];ts=[tuple(t.vertices)for t in me.loop_triangles];return vs,ts
allData={o.name:data(o)for o in obs};trees={n:BVHTree.FromPolygons(*a,all_triangles=True)for n,a in allData.items()};rows=[]
for o in obs:
 me=o.data;world=o.matrix_world;rot=world.to_3x3().inverted().transposed();samples=[]
 for p in me.polygons:
  if(rot@p.normal).z<-.2:samples+=[world@p.center]+[world@me.vertices[j].co for j in p.vertices]
 support={};floor=min(v.z for v in allData[o.name][0])
 for name,tree in trees.items():
  if name==o.name:continue
  gap=1e9
  for v in samples:
   hit=tree.ray_cast(v+Vector((0,0,.00001)),Vector((0,0,-1)),.5)
   if hit[0]is not None:gap=min(gap,hit[3]-.00001)
  if gap<.008:support[name]=gap
 rows.append({'object':o.name,'floor_gap':floor,'supports_below_within_8mm':support,'location':list(o.location),'rotation':list(o.rotation_euler)})
(Q/'BASELINE_CONTACTS.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps([{x['object']:list(x['supports_below_within_8mm'])}for x in rows]));os._exit(0)
