"""Check the cottage doorway against its actual Blender triangles before export."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'SourceAssets/Art/StonebrookExterior'
bpy.ops.wm.open_mainfile(filepath=str(ART/'KIT_StonebrookExterior.blend'))
ob=bpy.data.objects['SM_Cottage_Stonebrook_01']
tree=BVHTree.FromObject(ob,bpy.context.evaluated_depsgraph_get())
checks=[]
for x in [4.70,5.30,5.90]:
    for z in [.4,.9,1.3,1.8,2.25]:
        start=Vector((x,-5.3,z));hit=tree.ray_cast(start,Vector((0,1,0)),2.0)
        checks.append({'x_m':x,'height_m':z,'clear':hit[0] is None,'hit':list(hit[0]) if hit[0] else None})
report={'tool':'actual cottage mesh BVH doorway check','passed':all(c['clear'] for c in checks),'checks':checks}
(ART/'geometry_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print('COTTAGE DOORWAY:',sum(c['clear'] for c in checks),'/',len(checks),'rays clear')
if not report['passed']:raise RuntimeError('Cottage doorway contains blocking geometry')
