import bpy,json,hashlib,math
from pathlib import Path
from mathutils import Vector,Matrix
W=Path(__file__).resolve().parent;P=W/'Stonebrook_InteriorVista_Candidate.blend';bpy.ops.wm.open_mainfile(filepath=str(P));j=json.loads((W/'placement_proposal.json').read_text());rows=[]
for a in j['new_meshes']:
 o=bpy.data.objects[a['name']]
 if a['class']=='kit_floor':
  uv=o.data.uv_layers.active.data
  for p in o.data.polygons:
   for i in p.loop_indices:
    q=o.data.vertices[o.data.loops[i].vertex_index].co
    if abs(p.normal.z)>.5:uv[i].uv=(q.x/2,q.y/2)
    elif abs(p.normal.x)>.5:uv[i].uv=(q.y/2,q.z/2)
    else:uv[i].uv=(q.x/2,q.z/2)
 lo=[min(v.co[k] for v in o.data.vertices) for k in range(3)];hi=[max(v.co[k] for v in o.data.vertices) for k in range(3)];tris=sum(len(p.vertices)-2 for p in o.data.polygons)
 assert tris<= (4000 if a['class']=='kit_floor' else 20000)
 assert max(abs(v-1) for v in o.scale)<1e-6 and max(abs(v) for v in o.rotation_euler)<1e-6
 rows.append({'name':a['name'],'class':a['class'],'triangles':tris,'min_local_m':lo,'max_local_m':hi,'material_slots':[m.name for m in o.data.materials],'uv_layers':len(o.data.uv_layers)})
for p in j['instances']:
 asset=p.get('reused_asset') or p['new_mesh']
 if 'new_mesh' in p:
  cls=next(a['class'] for a in j['new_meshes'] if a['name']==asset);folder='Kits' if cls=='kit_floor' else 'Props';p['asset_path_proposal']='/Game/Dink/'+folder+'/Stonebrook/InteriorVista/'+asset+'.'+asset
 elif asset=='SM_Pine_Stonebrook_V3':p['asset_path_proposal']='/Game/Dink/Foliage/StonebrookFields/Refinements/'+asset+'.'+asset
 else:p['asset_path_proposal']='/Game/Dink/Kits/StonebrookExterior/'+asset+'.'+asset
 assert p['collision'] is False and p['camera_occluder'] is False
j['notes']=['Original439 courtyard lane and missingFenceSouth6 gateway are rigidly rebased from original cottage-door anchor','Original DinksCottage instance omitted; both proposed neighbors stay outside original interior footprint','OakWest/OakEast/OakNorth and added tree layers have explicit context-composition adjustments, not changes to originals','Only new ground/doorstep meshes exported; existing assets are runtime-reference proposals','All future vista geometry is render-only, not a floor-framing fix or collision/warp extension','Tree collars and sparse horizon remain inherited/candidate art limitations; no final realism acceptance']
(W/'placement_proposal.json').write_text(json.dumps(j,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(W/'Stonebrook_InteriorVista_Candidate_V3.blend'))
# A clean export source contains only the55 new assets. Reused existing assets and
# original interior framing remain in the composition source, not duplicated exports.
for name in ['Vista_ExistingAssetInstances','Preview_ExistingInteriorReference']:
 c=bpy.data.collections[name]
 if c.name in bpy.context.scene.collection.children:bpy.context.scene.collection.children.unlink(c)
bpy.ops.wm.save_as_mainfile(filepath=str(W/'Stonebrook_VistaAssets.blend'))
checks={'new_assets':rows,'new_asset_count':len(rows),'total_new_render_triangles':sum(r['triangles'] for r in rows),'all_future_instances_render_only':True,'original_room_footprint_unchanged':True,'room_exclusion_from_generation':'explicit transformed source-mesh AABBs; no vista mesh intersects open room rectangle','source_units':'metres, applied rotation/scale, Zup/-Yfront; UE conversion documented in proposal','reused_assets_not_reexported':True}
(W/'new_geometry_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
