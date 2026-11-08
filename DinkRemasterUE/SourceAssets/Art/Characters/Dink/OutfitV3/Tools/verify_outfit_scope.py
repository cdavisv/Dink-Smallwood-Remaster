"""Independent reload comparison of frozen anatomy/hand/rig/material invariants."""
import bpy,json,hashlib,struct,math
from pathlib import Path
ART=Path(__file__).resolve().parents[1];PROJECT=ART.parents[4]
SOURCE=ART.parent/'HandBindingV2/SK_Dink_Hands.blend';CANDIDATE=ART/'SK_Dink_OutfitV3.blend'
def value(v):
 try:return list(v)
 except TypeError:return v if isinstance(v,(str,int,float,bool)) else str(v)
def material_fingerprint(material):
 nodes=[]
 for n in material.node_tree.nodes:
  row={'name':n.name,'type':n.bl_idname,'inputs':{s.name:value(s.default_value) for s in n.inputs if hasattr(s,'default_value')}}
  if hasattr(n,'image') and n.image:row['image']={'name':n.image.name,'path':str(Path(bpy.path.abspath(n.image.filepath)).resolve()),'colorspace':n.image.colorspace_settings.name}
  nodes.append(row)
 links=sorted((l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in material.node_tree.links)
 return hashlib.sha256(json.dumps({'name':material.name,'nodes':nodes,'links':links},sort_keys=True).encode()).hexdigest()
def snapshot(path,prefix):
 bpy.ops.wm.open_mainfile(filepath=str(path));arm=bpy.data.objects['Armature'];rig={b.name:(b.parent.name if b.parent else None,[list(r) for r in b.matrix_local]) for b in arm.data.bones};lods=[]
 materials={m.name:material_fingerprint(m) for m in bpy.data.objects[prefix+'_LOD0'].data.materials[:4]}
 for lod in range(4):
  o=bpy.data.objects[prefix+'_LOD'+str(lod)];protected=[p for p in o.data.polygons if p.material_index<4];vertices=sorted({i for p in protected for i in p.vertices});rank={v:i for i,v in enumerate(vertices)};h=hashlib.sha256();uv=hashlib.sha256();faces=hashlib.sha256()
  for i in vertices:
   v=o.data.vertices[i];h.update(struct.pack('<I3f',rank[i],*v.co))
   for name,w in sorted((o.vertex_groups[g.group].name,g.weight) for g in v.groups):h.update(name.encode()+b'\0'+struct.pack('<f',w))
  for protected_index,p in enumerate(protected):
   faces.update(struct.pack('<II?',protected_index,p.material_index,p.use_smooth));faces.update(struct.pack('<'+'I'*len(p.vertices),*(rank[v] for v in p.vertices)))
   for layer in o.data.uv_layers:
    for i in p.loop_indices:uv.update(struct.pack('<2f',*layer.data[i].uv))
  influences=[len([g for g in v.groups if g.weight>1e-6]) for v in o.data.vertices];maxerr=max(abs(sum(g.weight for g in v.groups)-1) for v in o.data.vertices)
  lods.append({'protected_position_weight_hash':h.hexdigest(),'protected_uv_hash':uv.hexdigest(),'protected_face_hash':faces.hexdigest(),'protected_vertex_old_to_new':json.loads(o.get('protected_original_vertex_indices','[]')),'protected_vertices':len(vertices),'protected_faces':len(protected),'slot_names':[m.name for m in o.data.materials],'total_vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'max_influences':max(influences),'unweighted':influences.count(0),'max_weight_sum_error':maxerr})
 return {'rig':rig,'materials':materials,'lods':lods}
before=snapshot(SOURCE,'SK_Dink_Hands');after=snapshot(CANDIDATE,'SK_Dink_OutfitV3');assert before['rig']==after['rig'],'Rest89rig changed';assert before['materials']==after['materials'],'Protected material graph/ref changed'
for index,(b,a) in enumerate(zip(before['lods'],after['lods'])):
 for key in ['protected_position_weight_hash','protected_uv_hash','protected_face_hash','protected_vertices','protected_faces']:assert b[key]==a[key],(index,key,b[key],a[key])
 assert a['slot_names'][:4]==b['slot_names'][:4] and a['slot_names'][4]=='MI_Dink_WardrobeV3' and len(a['slot_names'])==5
 assert a['max_influences']<=4 and not a['unweighted'] and a['max_weight_sum_error']<1e-5
 assert a['triangles']<=40000
scope=json.loads((ART/'scope_before.json').read_text());mismatches=[]
for rel,digest in scope['files'].items():
 if hashlib.sha256((PROJECT/rel).read_bytes()).hexdigest()!=digest:mismatches.append(rel)
assert not mismatches,('Protected oldledgerfiles changed',mismatches)
report={'passed':True,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),'rest_bones_unchanged':len(before['rig']),'protected_materials':before['materials'],'protected_old_files_checked':len(scope['files']),'protected_old_file_mismatches':mismatches,'before_lods':before['lods'],'candidate_lods':after['lods'],'scope':'Wardrobe material/UV/LODs rebuilt only; protected indices canonicalized by sorted original-index mapping, exact float32 coords/weights and perface topology/UV hashed independently;  allfourprotectedmaterialgeometry/weights/UV bitexact, all89restmatrices exact. NoUEclaim.'}
(ART/'scope_verification.json').write_text(json.dumps(report,indent=2)+'\n');print('OUTFIT INDEPENDENT SCOPE PASS',len(scope['files']),'oldfiles;89bones;4anatomicalLODs;4materialrefs')
