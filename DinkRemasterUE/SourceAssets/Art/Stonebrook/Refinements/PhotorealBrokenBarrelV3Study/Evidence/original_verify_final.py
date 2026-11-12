import bpy,bmesh,json,hashlib,math,os,sys,ast
from pathlib import Path
Q=Path(__file__).resolve().parent;SRC=Path('<HOME>/Work/DinkQA/PhotorealBrokenBarrelExportV1/SourceNodesAlternativeV2/PhotorealBrokenBarrelV2_MultiNodeLODs.blend');OUT=Q/'PhotorealBrokenBarrelV3_Refinement.blend'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# Reuse only the pure graph signature function, never execute the authoring module.
tree=ast.parse((Q/'refine.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='material_signature');exec(compile(ast.Module(body=[fn],type_ignores=[]),'<signature>','exec'))
bpy.ops.wm.open_mainfile(filepath=str(SRC),load_ui=False,use_scripts=False)
names=['MI_Shared_OakLonggrain2m','MI_Shared_OakEndgrain2m','MI_Stonebrook_WroughtIron'];graphs={n:material_signature(bpy.data.materials[n])for n in names};images={i.name:hashlib.sha256(bytes(i.packed_file.data)).hexdigest()for i in bpy.data.images if i.packed_file}
bpy.ops.wm.open_mainfile(filepath=str(OUT),load_ui=False,use_scripts=False)
c=bpy.data.collections['V3_Editable_SplitStaves_SharedPBR'];bpy.context.view_layer.update();rows=[];allvs=[]
for o in c.objects:
 assert all(m.name in names for m in o.data.materials)
 assert all(math.isfinite(k)for v in o.data.vertices for k in v.co)
 assert all(math.isfinite(k)for uv in o.data.uv_layers for v in uv.data for k in v.uv)
 bm=bmesh.new();bm.from_mesh(o.data);bad=sum(not e.is_manifold for e in bm.edges);vol=bm.calc_volume(signed=True);bm.free();o.data.calc_loop_triangles();zero=sum((o.data.vertices[t.vertices[1]].co-o.data.vertices[t.vertices[0]].co).cross(o.data.vertices[t.vertices[2]].co-o.data.vertices[t.vertices[0]].co).length<1e-12 for t in o.data.loop_triangles)
 assert bad==zero==0 and vol>0,(o.name,bad,zero,vol)
 assert all(math.isfinite(k)for n in o.data.corner_normals for k in n.vector)
 allvs.extend(o.matrix_world@v.co for v in o.data.vertices)
 rows.append({'name':o.name,'triangles':len(o.data.loop_triangles),'signed_volume_m3':vol,'nonmanifold_edges':bad,'zero_area_triangles':zero,'finite_positions_uv_corner_normals':True})
assert len(rows)==36
for n in names:assert material_signature(bpy.data.materials[n])==graphs[n],n
for n,pin in images.items():assert hashlib.sha256(bytes(bpy.data.images[n].packed_file.data)).hexdigest()==pin,n
lo=[min(v[k]for v in allvs)for k in range(3)];hi=[max(v[k]for v in allvs)for k in range(3)];assert lo[2]>=0,lo
r={'candidate_sha256':sha(OUT),'preferred_source_sha256':sha(SRC),'objects':rows,'triangles':sum(x['triangles']for x in rows),'dimensions_m':[hi[k]-lo[k]for k in range(3)],'minimum_m':lo,'maximum_m':hi,'shared_graphs_exact':names,'packed_shared_image_sha256_exact':images,'Cycles_device':bpy.context.scene.cycles.device,'render_threads':bpy.context.scene.render.threads,'CPU_affinity':list(os.sched_getaffinity(0)),'native_or_runtime_validation':False}
(Q/'FINAL_REOPEN_CHECK.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'PASS':True,'objects':len(rows),'triangles':r['triangles'],'dimensions_m':r['dimensions_m'],'ground_min_z':lo[2]}));sys.stdout.flush();os._exit(0)
