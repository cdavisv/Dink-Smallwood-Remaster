"""Independent original/candidate comparison; no originalfiles rewritten."""
import bpy,json,hashlib,struct
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];CHARS=ROOT.parents[1];original=CHARS/'Dink/SK_Dink.blend';candidate=ROOT/'SK_Dink_Hands.blend';land=json.loads((ROOT/'hand_landmarks.json').read_text())['sides']
def snapshot(path,prefix):
 bpy.ops.wm.open_mainfile(filepath=str(path));rows=[]
 for lod in range(4):
  ob=bpy.data.objects[prefix+'_LOD%d'%lod];rows.append({'verts':[(tuple(v.co),sorted((ob.vertex_groups[g.group].name,g.weight) for g in v.groups)) for v in ob.data.vertices],'uv':[[tuple(x.uv) for x in layer.data] for layer in ob.data.uv_layers],'materials':[s.material.name for s in ob.material_slots],'skin':{i for p in ob.data.polygons if ob.material_slots[p.material_index].material.name=='MI_Dink_Skin' for i in p.vertices}})
 a=bpy.data.objects['Armature'];bones={b.name:(b.parent.name if b.parent else None,tuple(tuple(r) for r in b.matrix_local)) for b in a.data.bones};return rows,bones
before,rb=snapshot(original,'SK_Dink');after,ra=snapshot(candidate,'SK_Dink_Hands');assert rb==ra,'Rest rigchanged';report={'passed':True,'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'unchanged_rest_bones':len(rb),'lods':[]}
def digest(rows):
 h=hashlib.sha256()
 for i,(co,weights) in rows:
  h.update(struct.pack('<I3f',i,*co))
  for n,w in weights:h.update(n.encode()+b'\0'+struct.pack('<f',w))
 return h.hexdigest()
for lod,(b,a) in enumerate(zip(before,after)):
 assert len(b['verts'])==len(a['verts']);assert b['uv']==a['uv'],'UVchanged';assert b['materials']==a['materials'],'Materialschanged';changed=[];outside=[];cross=0
 for i,(x,y) in enumerate(zip(b['verts'],a['verts'])):
  allowed=False;p=Vector(x[0])
  if i in b['skin']:
   for side,spec in land.items():
    w=Vector(spec['wrist_old']);d=(Vector(spec['digits']['middle']['old'][0])-w).normalized()
    allowed=allowed or((p-w).length<=.27 and(p-w).dot(d)>-.025 and((side=='r' and p.x<=-.34)or(side=='l' and p.x>=.34)))
  if x!=y:
   assert allowed,('Unexpectedoutsidechange',lod,i);changed.append(i)
  if not allowed:outside.append(i);assert x==y
  if allowed:
   families={n.split('_')[0] for n,w in y[1] if w>1e-6 and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))};cross+=len(families)>1
  assert len([w for n,w in y[1] if w>1e-6])<=4 and y[1]
 assert not cross
 h1=digest([(i,b['verts'][i]) for i in outside]);h2=digest([(i,a['verts'][i]) for i in outside]);assert h1==h2
 report['lods'].append({'lod':lod,'changed_vertex_ids':changed,'changed_vertices':len(changed),'outside_vertices':len(outside),'outside_position_weight_sha256_original':h1,'outside_position_weight_sha256_candidate':h2,'all_uvs_equal':True,'material_slots_equal':True,'cross_digit_contamination':cross})
(ROOT/'scope_verification.json').write_text(json.dumps(report,indent=2)+'\n');print('HANDV2 INDEPENDENT SCOPE PASS:4LODs outsidepositions/weights/UV/materials and89resttransforms identical')
