"""Independent reopening comparison against the untouched input pie and authored collider state."""
import bpy,json,os,sys,hashlib,math
from pathlib import Path
O=Path(__file__).resolve().parent;name='SM_Pie_Rustic_01';P=O/'Inputs/KIT_Stonebrook_Input.blend'
try:
 bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealPieV1_Source.blend'))
 c=bpy.data.collections[name];candidate=next(o for o in c.objects if o.type=='MESH'and o.name.endswith('_LOD0'))
 with bpy.data.libraries.load(str(P),link=False)as(src,dst):dst.collections=[name]
 reference=dst.collections[0];bpy.context.scene.collection.children.link(reference);bpy.context.view_layer.update();old=next(o for o in reference.objects if o.type=='MESH'and not o.name.startswith('UCX_'))
 bounds=lambda ob:[[min(v.co[k]for v in ob.data.vertices)for k in range(3)],[max(v.co[k]for v in ob.data.vertices)for k in range(3)]]
 a,b=bounds(candidate),bounds(old);delta=max(abs(a[i][k]-b[i][k])for i in range(2)for k in range(3));assert delta<1e-6,delta
 hulls=lambda coll,origin:[{'vertices':[list(v.co)for v in ob.data.vertices],'relative_matrix':[list(row)for row in __import__('mathutils').Matrix.Translation(-origin)@ob.matrix_world]}for ob in coll.objects if ob.name.startswith('UCX_')]
 h1=hulls(c,candidate.location);h2=hulls(reference,old.location)
 (O/'collision_comparison.json').write_text(json.dumps({'candidate':h1,'reference':h2},indent=2)+'\n')
 assert h1==h2,'Collider vertices or relative transform changed'
 assert all(math.isfinite(x)for v in candidate.data.vertices for x in v.co)
 assert all(i.packed_file is not None for i in bpy.data.images if i.source=='FILE' and i.users and i in [n.image for mat in candidate.data.materials for n in mat.node_tree.nodes if n.type=='TEX_IMAGE']),'Candidate external images'
 result={'schema':'dink-pie-independent-source-audit/1','passed':True,'source_sha256':hashlib.sha256((O/'PhotorealPieV1_Source.blend').read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'max_bounds_delta_m':delta,'ground_center_pivot_preserved':list(candidate.location)==[0,0,0],'collider_local_vertices_and_relative_transform_exact':True,'collider_count':len(h1),'source_triangles':sum(len(p.vertices)-2 for p in candidate.data.polygons),'finite_positions':True,'native_imported':False,'limits':['No universal intersection-free or native game acceptance claim.','Pastry lattice, crimp and filling contacts intentionally meet or overlap.','Dedicated glazed dish/pastry/fruit shaders need native material review; original food script and native references unchanged.']}
 (O/'independent_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));sys.stdout.flush();os._exit(0)
except BaseException:
 import traceback
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
