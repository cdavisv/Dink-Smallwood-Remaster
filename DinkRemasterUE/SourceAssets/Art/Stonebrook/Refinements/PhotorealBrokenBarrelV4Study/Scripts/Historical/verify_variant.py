import bpy,json,hashlib,struct,ast,os,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
Q=Path(__file__).resolve().parent;BASE=Path('/home/davisc/Work/DinkQA/PhotorealBrokenBarrelCurvatureV4');SRC=BASE/'PhotorealBrokenBarrelV4_CurvedSource.blend';OUT=Q/'PhotorealBrokenBarrelV4_AsymmetricComposition.blend'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for script,funcs in [(Q/'build_variant.py',['geometry','data','tree','samples']), (Path('/home/davisc/Work/DinkQA/PhotorealBrokenBarrelRefinementV3/refine.py'),['material_signature'])]:
 t=ast.parse(script.read_text());nodes=[n for n in t.body if isinstance(n,ast.FunctionDef)and n.name in funcs];exec(compile(ast.Module(body=nodes,type_ignores=[]),'<purehelpers>','exec'),globals())
bpy.ops.wm.open_mainfile(filepath=str(SRC),load_ui=False,use_scripts=False);obs=list(bpy.data.collections['V4_CooperedFragments_Editable'].objects);bpy.context.view_layer.update();geo={o.name:geometry(o)for o in obs};poses={o.name:[list(x)for x in o.matrix_world]for o in obs};scales={o.name:list(o.scale)for o in obs}
names=['MI_Shared_OakLonggrain2m','MI_Shared_OakEndgrain2m','MI_Stonebrook_WroughtIron'];graphs={n:material_signature(bpy.data.materials[n])for n in names};ims={n.image.name for m in names for n in bpy.data.materials[m].node_tree.nodes if n.type=='TEX_IMAGE'};imfacts={n:(hashlib.sha256(bytes(bpy.data.images[n].packed_file.data)).hexdigest(),bpy.data.images[n].colorspace_settings.name,list(bpy.data.images[n].size))for n in ims}
bpy.ops.wm.open_mainfile(filepath=str(OUT),load_ui=False,use_scripts=False);obs=list(bpy.data.collections['V4_AsymmetricRigidVariant_Editable'].objects);bpy.context.view_layer.update();assert{ o.name:geometry(o)for o in obs}==geo
r=json.loads((Q/'VARIANT_RECEIPT.json').read_bytes());changed={x['object']for x in r['rigid_changes']};trees={o.name:tree(o)for o in obs};vertical=[]
for o in obs:
 assert list(o.scale)==scales[o.name]and o.matrix_world.to_3x3().determinant()>0
 if o.name not in changed:assert[list(x)for x in o.matrix_world]==poses[o.name]
 else:
  vs,ts=data(o);normal=o.matrix_world.to_3x3().inverted().transposed();best=min(v.z+.001 for v in vs);proof={'support':'review floor at z=-.001m','gap_m':best}
  for other in obs:
   if other==o:continue
   u=trees[other.name]
   for t in o.data.loop_triangles:
    if(normal@t.normal).z>=-.2:continue
    for p in [vs[i]for i in t.vertices]+[sum((vs[i]for i in t.vertices),Vector())/3]:
     hit=u.ray_cast(p+Vector((0,0,.00001)),Vector((0,0,-1)),.5)
     if hit[0]is not None and hit[1].z>.2 and 0<=hit[3]-.00001<best:
      best=hit[3]-.00001;proof={'support':other.name,'gap_m':best,'direction':'moved_bottom_down_to_support_top','from':list(p),'to':list(hit[0]),'support_normal_z':hit[1].z}
   ov,ot=data(other);orn=other.matrix_world.to_3x3().inverted().transposed()
   for t in other.data.loop_triangles:
    if(orn@t.normal).z<=.2:continue
    p=(ov[t.vertices[0]]+ov[t.vertices[1]]+ov[t.vertices[2]])/3
    hit=trees[o.name].ray_cast(p-Vector((0,0,.00001)),Vector((0,0,1)),.5)
    if hit[0]is not None and hit[1].z<-.2 and 0<=hit[3]-.00001<best:
     best=hit[3]-.00001;proof={'support':other.name,'gap_m':best,'direction':'support_top_up_to_moved_bottom','from':list(p),'to':list(hit[0]),'moved_bottom_normal_z':hit[1].z}
  assert 0<=best<=.005,(o.name,'no real downward support',proof);vertical.append({'object':o.name,**proof})
for n in names:assert material_signature(bpy.data.materials[n])==graphs[n]
for n,f in imfacts.items():
 i=bpy.data.images[n];assert i.packed_file and(hashlib.sha256(bytes(i.packed_file.data)).hexdigest(),i.colorspace_settings.name,list(i.size))==f
out={'variant_sha256':sha(OUT),'source_v4_sha256':sha(SRC),'all25_geometry_UV_local_normals_material_slots_exact':True,'all25_scales_exact':True,'unchanged20_world_matrices_exact':True,'three_shared_material_graphs_and9_packed_maps_exact':True,'real_vertical_surface_supports':vertical,'support_scope':'Actual opposed top/bottom triangle normals and vertical rays with gaps<=5mm. Not a rigidbody/centre-of-mass stability proof; changed mesh intersections/containment separately checked in VARIANT_RECEIPT.','no_export_native_runtime':True}
(Q/'FINAL_VERIFY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'PASS':True,'support_gaps_m':[x['gap_m']for x in vertical]}));sys.stdout.flush();os._exit(0)
