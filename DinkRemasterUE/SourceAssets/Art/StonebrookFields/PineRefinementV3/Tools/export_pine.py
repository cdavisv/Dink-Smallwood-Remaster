"""Export approved isolated pine candidate only; no currentFields/global writes."""
import bpy,json,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[3]
sys.path.insert(0,str(PROJECT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import common,export_ue,validate,fbxparse
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'PineRefinementV3.blend'));NAME='SM_Pine_Stonebrook_V3';asset=common.Asset(bpy.data.collections[NAME]);raw=validate.validate_scene(only=[NAME]);(ROOT/'pine_validation.json').write_text(json.dumps(raw,indent=2)+'\n')
if raw['summary']['errors']:raise RuntimeError('Pine sourceconvention errors:'+str(raw['assets']))
geometry=json.loads((ROOT/'pine_geometry_report.json').read_text());renders=[bpy.data.objects[NAME+'_LOD%d'%i] for i in range(3)];bounds=[common.world_bounds(o) for o in renders];lo,hi=bounds[0];unionlo=[min(b[0][i] for b in bounds) for i in range(3)];unionhi=[max(b[1][i] for b in bounds) for i in range(3)]
materials=json.loads((ROOT/'pine_materials_used.json').read_text());files=['Export/'+NAME+'_LOD%d.fbx'%i for i in range(3)]
row={'class':'foliage','fbx':files[0],'lod_fbx':files,'dimensions_m':list(hi-lo),'bounds_min_m':list(lo),'bounds_max_m':list(hi),'lod_union_dimensions_m':[unionhi[i]-unionlo[i] for i in range(3)],'materials':[s.material.name for s in renders[0].material_slots],'blend_collection':NAME,'source_blend':'PineRefinementV3.blend','expected_lods':3,'triangles_per_lod':{o.name:common.tri_count(o) for o in renders},'collision_mode':'simple','trunk_collision_bounds_m':[geometry['collision']['bounds_min_m'],geometry['collision']['bounds_max_m']],'trunk_collision_source_sha256':geometry['collision']['vertex_face_sha256'],'content_folder':'/Game/Dink/Foliage/StonebrookFields/Refinements','replaces_asset':'/Game/Dink/Kits/StonebrookFields/SM_Pine_Stonebrook_01.SM_Pine_Stonebrook_01','lod_policy':geometry['lod_policy'],'budget_note':'All584sourcebranches and1853sprays retainedperLOD;22270/10942/6784tris below25k/12k/7k;2materials,2048PBR,nonNanite. Maskedtwo-sidedneedles with.12clip andpreservealphaCoverage required.','lowest_foliage_m':1.0746300220489502}
manifest={'schema':'dink-art/1','assets':{NAME:row},'materials':materials,'status':'candidate','source_scope':'IsolatedPineRefinementV3 only. OriginalFields227artifacthashes/manifest/FBXs/ledger untouched; no runtime mapping or engine import here.','generator':'PinnedSapling0.4.0 small_pine Weber-Penn branches with originalprojectmodeledpairedneedlePBR; toolreceipt records sourceSHA/license.','render_review':'Fulltree equal-light3LOD comparison, lowercrown fill, closedneedleclusters anddistance thumbnail reviewed before export.'}
(ROOT/'art_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Discard materialgraphs only inthis exportprocess; full source.blend is already saved.
for mat in bpy.data.materials:
 if mat.node_tree:mat.node_tree.nodes.clear()
 mat.use_nodes=False
receipts=[]
for lod,(ob,filename) in enumerate(zip(renders,files)):
 proxy=SimpleNamespace(renders=[ob],collision=asset.collision if lod==0 else[],armatures=[],sockets=[])
 with export_ue.unhidden([ob,*proxy.collision]):export_ue.export_fbx(proxy,str(ROOT/filename),'all',None)
 version,nodes=fbxparse.parse(ROOT/filename);objects=next(n for n in nodes if n.name=='Objects');zero=0;normals=0
 for geo in objects.find('Geometry'):
  for layer in geo.find('LayerElementNormal'):
   a=layer.first('Normals').props[0];normals+=len(a)//3;zero+=sum(sum(v*v for v in a[i:i+3])<1e-8 for i in range(0,len(a),3))
 if zero:raise RuntimeError('ExportedzeroNormals '+filename)
 info=fbxparse.inspect(ROOT/filename)
 if abs(info['unit_scale_factor']-100)>1e-6:raise RuntimeError('Wrong staticmetre FBXheader')
 meshes=[m for n,m in info['models'].items() if m['type']=='Mesh' and not n.startswith('UCX_')]
 if len(meshes)!=1:raise RuntimeError('EachFBX mustcontainexactlyone renderLOD')
 if lod==0 and max(abs(a-b*100) for a,b in zip(meshes[0]['size_cm'],row['dimensions_m']))>.01:raise RuntimeError('FBXbounds differfromsource')
 receipts.append({'file':filename,'normals':normals,'zero_normals':zero,'fbx':info})
(ROOT/'fbx_inspection.json').write_text(json.dumps({'passed':True,'files':receipts},indent=2)+'\n')
print('PINEV3 EXPORT PASS3FBXs,staticheader100,zeroNormals0,oneLODperfile;sourceonly',flush=True)
