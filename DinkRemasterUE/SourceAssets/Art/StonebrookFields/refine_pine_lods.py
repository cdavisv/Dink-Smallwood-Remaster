"""Retain the full pine canopy in lower LODs; source geometry only.
Run after build_fields.py, before export_fields.py. LOD0 and UCX are untouched.
"""
import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector
ART=Path(__file__).resolve().parent;ROOT=ART.parents[2]
sys.path.insert(0,str(ROOT.parent/'Dink-Smallwood-Remaster/tools/blender'))
sys.path.insert(0,str(ROOT/'SourceAssets/Art/tools'))
from dinkasset import common,validate
from repair_foliage_normals import repair_collapsed_components
bpy.ops.wm.open_mainfile(filepath=str(ART/'KIT_StonebrookFields.blend'))
name='SM_Pine_Stonebrook_01';collection=bpy.data.collections[name];high=bpy.data.objects[name+'_LOD0']
assert sum(len(p.vertices)-2 for p in high.data.polygons)==22444,'Unexpected source pine topology'
# build_fields.py emits14 trunk polygons, followed by112 branches, each with
#8 bark polygons then5 needle boughs. A bough has12 opaque core polygons and
#24 fine-needle polygons. Retain every branch/core, omit only the thin needles.
selected=list(range(14))
for branch in range(16*7):
 start=14+branch*(8+5*36);selected.extend(range(start,start+8))
 for bough in range(5):selected.extend(range(start+8+bough*36,start+8+bough*36+12))
assert max(selected)<len(high.data.polygons)
repairs=[];levels=[]
for lod in [1,2]:
 old=bpy.data.objects.get(name+'_LOD'+str(lod))
 if old:
  old_mesh=old.data;bpy.data.objects.remove(old,do_unlink=True)
  if old_mesh.users==0:bpy.data.meshes.remove(old_mesh)
 polygons=[];materials=[]
 def keep_poly(index):
  poly=high.data.polygons[index];polygons.append(tuple(poly.vertices));materials.append(poly.material_index)
 for index in range(14):keep_poly(index)
 for branch in range(112):
  start=14+branch*(8+5*36)
  for index in range(start,start+8):keep_poly(index)
  for bough in range(5):
   first=start+8+bough*36
   if lod==1:
    for index in range(first,first+12):keep_poly(index)
   else:
    # Preserve every source bough. Simplify each six-sided closed core to
    # four sides explicitly, rather than letting a global reducer delete it.
    ring=[high.data.polygons[first+2*k].vertices[1] for k in [0,2,3,5]]
    bottom=high.data.polygons[first].vertices[0];top=high.data.polygons[first+1].vertices[0]
    for k in range(4):
     polygons.extend([(bottom,ring[k],ring[(k+1)%4]),(top,ring[(k+1)%4],ring[k])]);materials.extend([1,1])
 used=sorted({v for f in polygons for v in f});remap={v:i for i,v in enumerate(used)}
 mesh=bpy.data.meshes.new(name+'_LOD'+str(lod));mesh.from_pydata([high.data.vertices[i].co[:] for i in used],[],[[remap[v] for v in f] for f in polygons])
 for mat in high.data.materials:mesh.materials.append(mat)
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
 uv=mesh.uv_layers.new(name='UVMap')
 for poly,material in zip(mesh.polygons,materials):
  poly.material_index=material;poly.use_smooth=True
  axis=max(range(3),key=lambda k:abs(poly.normal[k]));axes=[k for k in range(3) if k!=axis]
  for loop in poly.loop_indices:
   v=mesh.vertices[mesh.loops[loop].vertex_index].co;uv.data[loop].uv=(v[axes[0]]/2,v[axes[1]]/2)
 ob=bpy.data.objects.new(mesh.name,mesh);collection.objects.link(ob)
 repairs.append(repair_collapsed_components(ob))
 levels.append({'lod':lod,'triangles':sum(len(f.vertices)-2 for f in ob.data.polygons),'source_whorls_retained':16,'source_branches_retained':112,'source_bough_cores_retained':560,'core_cross_section_sides':6 if lod==1 else 4})
spec=json.loads((ART/'art_manifest.json').read_text());a=spec['assets'][name]
a['triangles_per_lod']={ob.name:sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in collection.objects if not ob.name.startswith('UCX_')}
renders=[bpy.data.objects[name+'_LOD'+str(i)] for i in range(3)]
mn=[min(v.co[k] for ob in renders for v in ob.data.vertices) for k in range(3)];mx=[max(v.co[k] for ob in renders for v in ob.data.vertices) for k in range(3)]
a['lod_union_dimensions_m']=[mx[k]-mn[k] for k in range(3)];a['lod_policy']='Lower LODs derive from all16 source whorls/112 branches/560 bough cores; fine needles removed, each closed bough core explicitly simplified. All560cores retained; no whole branch/bough deletion.'
folder='Export/Game/Dink/Foliage/StonebrookFields/'
a['lod_fbx']=[folder+name+'_LOD'+str(i)+'.fbx' for i in range(3)];a['fbx']=a['lod_fbx'][0]
(ART/'art_manifest.json').write_text(json.dumps(spec,indent=2)+'\n')
raw=validate.validate_scene();(ART/'validation_raw.json').write_text(json.dumps(raw,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'KIT_StonebrookFields.blend'))
(ART/'pine_lod_refinement.json').write_text(json.dumps({'status':'source-only; rendered LOD check pending','lod0_geometry_unchanged':True,'ucx_unchanged':True,'levels':levels,'repairs':repairs,'validation_summary':raw['summary']},indent=2)+'\n')
print('PINE FULL CANOPY LODS:',levels)
