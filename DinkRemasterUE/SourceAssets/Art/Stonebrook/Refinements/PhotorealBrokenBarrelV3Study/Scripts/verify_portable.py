"""Independent Blender reopen; no save, render, export or source mutation."""
import bpy,bmesh,json,hashlib,math,os,sys,argparse,ast
from pathlib import Path
import traceback
def failed(t,v,b):
 traceback.print_exception(t,v,b);sys.stderr.flush();os._exit(1)
sys.excepthook=failed
parser=argparse.ArgumentParser();parser.add_argument('--input');parser.add_argument('--output',required=True);parser.add_argument('--compare')
a=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);bundle=Path(__file__).resolve().parents[1]
p=Path(a.input).resolve()if a.input else bundle/'portable.source.blend';out=Path(a.output).resolve();assert not out.exists();assert not out.is_relative_to(Path(__file__).resolve().parents[6]),'Evidence output must be outside project'
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
tree=ast.parse((bundle/'Evidence/original_refine.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='material_signature');exec(compile(ast.Module(body=[fn],type_ignores=[]),'<pure signature>','exec'))
before=sha(p);bpy.ops.wm.open_mainfile(filepath=str(p),load_ui=False,use_scripts=False);bpy.context.view_layer.update()
assert not bpy.data.libraries
external=[i.name for i in bpy.data.images if i.source=='FILE'and not i.packed_file];assert not external,external
names=['MI_Shared_OakLonggrain2m','MI_Shared_OakEndgrain2m','MI_Stonebrook_WroughtIron'];rows={};world=[]
for o in sorted(bpy.data.collections['V3_Editable_SplitStaves_SharedPBR'].objects,key=lambda x:x.name):
 assert o.type=='MESH'and all(m.name in names for m in o.data.materials)
 me=o.data;me.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(me);bad=sum(not e.is_manifold for e in bm.edges);vol=bm.calc_volume(signed=True);bm.free()
 assert bad==0 and vol>0
 assert all(math.isfinite(c)for v in me.vertices for c in v.co)
 assert all(math.isfinite(c)for layer in me.uv_layers for v in layer.data for c in v.uv)
 assert all(math.isfinite(c)for n in me.corner_normals for c in n.vector)
 zero=sum((me.vertices[t.vertices[1]].co-me.vertices[t.vertices[0]].co).cross(me.vertices[t.vertices[2]].co-me.vertices[t.vertices[0]].co).length<1e-12 for t in me.loop_triangles);assert zero==0
 data={'positions':[list(v.co)for v in me.vertices],'polygons':[list(f.vertices)for f in me.polygons],'uv':[[list(v.uv)for v in l.data]for l in me.uv_layers],'normals':[list(n.vector)for n in me.corner_normals],'matrix':[list(r)for r in o.matrix_world],'material_slots':[m.name for m in me.materials],'material_indices':[f.material_index for f in me.polygons]}
 rows[o.name]={'sha256':hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'triangles':len(me.loop_triangles),'signed_volume':vol,'nonmanifold_edges':bad,'zero_area_triangles':zero}
 world.extend(o.matrix_world@v.co for v in me.vertices)
assert len(rows)==36 and sum(v['triangles']for v in rows.values())==9928
lo=[min(v[k]for v in world)for k in range(3)];hi=[max(v[k]for v in world)for k in range(3)];assert lo[2]>=0
materials=json.loads(json.dumps({n:material_signature(bpy.data.materials[n])for n in names}))
images={i.name:hashlib.sha256(bytes(i.packed_file.data)).hexdigest()for i in bpy.data.images if i.packed_file and any(n.type=='TEX_IMAGE'and n.image==i for m in [bpy.data.materials[x]for x in names]for n in m.node_tree.nodes)};assert len(images)==9
r={'input_sha256':before,'source_unchanged':sha(p)==before,'geometry':rows,'triangles':9928,'objects':36,'minimum_m':lo,'dimensions_m':[hi[k]-lo[k]for k in range(3)],'shared_material_graphs':materials,'shared_packed_maps':images,'no_linked_libraries':True,'no_unpacked_file_images':True,'CPU_affinity':list(os.sched_getaffinity(0)),'scope':'Source geometry/shared graphs only; no native/export/LOD/runtime/final appearance approval'}
if a.compare:
 old=json.loads(Path(a.compare).read_text());assert r['geometry']==old['geometry'],'Reproduced geometry differs';assert r['shared_material_graphs']==old['shared_material_graphs'];assert r['shared_packed_maps']==old['shared_packed_maps'];r['compared_geometry_graphs_maps_exact']=True
assert r['source_unchanged'];out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps({'PASS':True,'objects':36,'triangles':9928,'output':str(out)}));sys.stdout.flush();os._exit(0)
