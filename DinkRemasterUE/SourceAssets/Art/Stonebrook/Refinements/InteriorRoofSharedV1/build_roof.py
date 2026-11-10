"""Material-only shared conversion with inherited UV density audit; all geometry/TRS/custom normals protected."""
import bpy,numpy as np,json,hashlib,os,sys
from pathlib import Path
O=Path(__file__).resolve().parent;PROJECT=O.parents[4];F=O.parent/'RoofChimneyV12d/ExportV12d_Run01/Source/RoofChimney_ArtistRepair_v12d.blend';bpy.ops.wm.open_mainfile(filepath=str(F))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snap(o):
 m=o.data
 return dict(vertices=[tuple(v.co)for v in m.vertices],polygons=[tuple(p.vertices)for p in m.polygons],matrix=[list(r)for r in o.matrix_world],parent=o.parent.name if o.parent else None,modifiers=[x.type for x in o.modifiers],normals=[tuple(n.vector)for n in m.corner_normals],smooth=[p.use_smooth for p in m.polygons],UV={u.name:[tuple(x.uv)for x in u.data]for u in m.uv_layers})
before={o.name:snap(o)for o in bpy.data.objects if o.type=='MESH'}
protected_materials={o.name:[m.name if m else None for m in o.data.materials]for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('SM_IndoorRoof')}
with bpy.data.libraries.load(str(PROJECT/'SourceAssets/Art/SharedMaterials/OakLime2mV1/Shared2m_LibraryCandidate.blend'),link=False)as(src,dst):dst.materials=[x for x in src.materials if x.startswith('MI_Shared_')]
rolemap={'OakLonggrain':'OakLonggrain2m','RoofBoards':'OakLonggrain2m','OakEndgrain':'OakEndgrain2m','GablePlaster':'LimePlaster2m'}
rows=[]
for o in bpy.data.objects:
 if not o.name.startswith('SM_IndoorRoof'):continue
 m=o.data;old_names=[x.name for x in m.materials];uv=m.uv_layers.active;v=np.array([x.co[:]for x in m.vertices])
 # Preserve original continuous UV charts; see rejected metric experiment.
 for i,name in enumerate(old_names):
  role=next(rolemap[r]for r in rolemap if r in name);m.materials[i]=bpy.data.materials['MI_Shared_'+role]
 # Quantify every triangle's metric UV Jacobian after float32 storage.
 metrics=[];areas=[]
 for p in m.polygons:
  a,b,c=v[list(p.vertices)];e=b-a;f=c-a;L=np.linalg.norm(e);x=np.dot(e,f)/L;y=np.linalg.norm(np.cross(e,f))/L;ts=np.array([uv.data[l].uv[:]for l in p.loop_indices]);D=np.stack([ts[1]-ts[0],ts[2]-ts[0]],axis=1);J=D@np.linalg.inv(np.array([[L,x],[0,y]]));metrics.append(np.linalg.svd(J,compute_uv=False));areas.append(L*y/2)
 metrics=np.array(metrics);areas=np.array(areas);err=np.max(abs(metrics-.5),axis=1);rows.append(dict(name=o.name,polygons=len(m.polygons),materials_before=old_names,materials_after=[x.name for x in m.materials],UV_per_m_min_max=[float(metrics.min()),float(metrics.max())],nominal_texels_per_m=512,UV_per_m_percentile=np.percentile(metrics,[0,50,95,100],axis=0).tolist(),triangles_over_1pct_metric_error=int((err>.005).sum()),area_fraction_over_1pct=float(areas[err>.005].sum()/areas.sum()),UV0_sha256=hashlib.sha256(np.array([u.uv[:]for u in uv.data],dtype='<f4').tobytes()).hexdigest()))
 assert np.isfinite(metrics).all() and metrics.min()>0
after={o.name:snap(o)for o in bpy.data.objects if o.type=='MESH'}
assert before==after,'Protected geometry/TRS/normals changed'
assert protected_materials=={o.name:[m.name if m else None for m in o.data.materials]for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('SM_IndoorRoof')}
# Remove unused roof-private resources only; protected chimney/fireplace resources stay packed.
for m in list(bpy.data.materials):
 if m.name.startswith('MI_InteriorRoof_') and m.users==0:bpy.data.materials.remove(m)
for im in list(bpy.data.images):
 if im.users==0:bpy.data.images.remove(im)
for im in bpy.data.images:
 if im.name.startswith('T_Shared_'):
  path=PROJECT/'SourceAssets/Art/SharedMaterials/OakLime2mV1/Textures'/(im.name+'.png');assert path.exists(),im.name
  # Library append preserves packed pixels; rebind relative path to this source directory.
  im.pack();im.filepath='//'+os.path.relpath(path,O)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.render.threads_mode='FIXED';s.render.threads=2;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
P=O/'InteriorRoof_Shared2mCandidate.blend';bpy.ops.wm.save_as_mainfile(filepath=str(P),relative_remap=False)
report=dict(passed=True,source_sha256=sha(F),candidate_sha256=sha(P),mesh_objects=len(before),UCX_objects=sum(n.startswith('UCX')for n in before),geometry_TRS_parent_modifiers_smooth_corner_normals_exact=True,all_original_UVs_exact=True,protected_material_slots_exact=True,UV_scope='All original roof UVs retained exactly after failed metric-chart experiment. Nominal 2m scale on broad faces; inherited bevel/edge compression explicitly measured. Intentional repeat/overlap allowed.',UV_rows=rows)
(O/'SOURCE_PRESERVATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));sys.stdout.flush();os._exit(0)
