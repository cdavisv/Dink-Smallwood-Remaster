"""Isolated per-digit corrective hand candidate; originalhero assets never overwritten.
Original bodywide fit used wrist-only controls. Here each anatomical digit is fitted to
its existing fixed89-bone counterpart, with explicit isolated skinning and wrist falloff.
"""
import bpy,json,math,hashlib,struct
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];CHARS=ROOT.parents[1];ORIG=CHARS/'Dink/SK_Dink.blend'
for folder in ['Previews','Export']: (ROOT/folder).mkdir(parents=True,exist_ok=True)
land=json.loads((ROOT/'hand_landmarks.json').read_text())['sides']
bpy.ops.wm.open_mainfile(filepath=str(ORIG));scene=bpy.context.scene;arm=bpy.data.objects['Armature'];arm.animation_data_create();arm.animation_data.action=None;arm.data.pose_position='REST'
for im in bpy.data.images:
 if im.filepath:im.filepath=bpy.path.abspath(im.filepath)
coll=bpy.data.collections['SK_Dink'];coll.name='SK_Dink_Hands';coll['dink_class']='character_hero';coll['dink_path']='Hero/Refinements';coll['dink_source']='ExistingCC0-basedDink plus original isolatedper-digit handfit/weights; existingtexture/rigreferences retained.'
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
def project(p,a,b):
 d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));c=a+d*t;return t,c,(p-c).length

def path_map(p,old,new):
 rows=[];cumulative=0
 for i in range(len(old)-1):
  t,c,dist=project(p,old[i],old[i+1]);q=(old[i+1]-old[i]).rotation_difference(new[i+1]-new[i]);mapped=new[i].lerp(new[i+1],t)+q@(p-c)
  progress=cumulative+t*(old[i+1]-old[i]).length-(old[1]-old[0]).length;rows.append((dist,mapped,progress,i,t));cumulative+=(old[i+1]-old[i]).length
 best=min(rows,key=lambda x:x[0]);weights=[1/(row[0]**2+.000035)**3 for row in rows];mapped=sum((row[1]*w for row,w in zip(rows,weights)),Vector())/sum(weights)
 return best[0],mapped,best[2],best[3],best[4]

def fingerprint(mesh,indices):
 h=hashlib.sha256()
 for i in indices:
  v=mesh.data.vertices[i];h.update(struct.pack('<I3f',i,*v.co))
  for name,w in sorted((mesh.vertex_groups[g.group].name,g.weight) for g in v.groups):h.update(name.encode()+b'\0'+struct.pack('<f',w))
 return h.hexdigest()
def uv_hash(mesh):
 h=hashlib.sha256()
 for layer in mesh.data.uv_layers:
  for uv in layer.data:h.update(struct.pack('<2f',*uv.uv))
 return h.hexdigest()

def set_weights(mesh,v,values):
 values={n:w for n,w in values.items() if w>1e-6};items=sorted(values.items(),key=lambda x:-x[1])[:4];total=sum(w for _,w in items)
 for g in mesh.vertex_groups:g.remove([v.index])
 for n,w in items:
  if n not in mesh.vertex_groups:mesh.vertex_groups.new(name=n)
  mesh.vertex_groups[n].add([v.index],w/total,'REPLACE')

report={'schema':'dink-hand-correction/1','source_original':str(ORIG),'source_original_sha256':hashlib.sha256(ORIG.read_bytes()).hexdigest(),'scope':'Skin hands and smoothwristseam only.89bindtransforms/materials/UVs and alloutside vertices/weights unchanged.','lods':[],'rig_before':{b.name:{'parent':b.parent.name if b.parent else None,'matrix':[list(r) for r in b.matrix_local]} for b in arm.data.bones}}
for lod in range(4):
 ob=bpy.data.objects['SK_Dink_LOD%d'%lod];ob.name='SK_Dink_Hands_LOD%d'%lod;ob.data.name=ob.name;beforeuv=uv_hash(ob);changes=[];masks={};digit_assign={};source_weights={v.index:{ob.vertex_groups[g.group].name:g.weight for g in v.groups} for v in ob.data.vertices};oldpositions={v.index:v.co.copy() for v in ob.data.vertices}
 skin_ids={i for p in ob.data.polygons if ob.material_slots[p.material_index].material.name=='MI_Dink_Skin' for i in p.vertices}
 for side in ['r','l']:
  spec=land[side];wold=Vector(spec['wrist_old']);wnew=Vector(spec['wrist_new']);forward=(Vector(spec['digits']['middle']['old'][0])-wold).normalized();paths={n:([wold,*[Vector(p) for p in row['old']]],[wnew,*[Vector(p) for p in row['new']]]) for n,row in spec['digits'].items()}
  for index in skin_ids:
   v=ob.data.vertices[index];p=oldpositions[index];long=(p-wold).dot(forward)
   if (p-wold).length>.27 or long<=-.025 or (side=='r' and p.x>-.34) or(side=='l' and p.x<.34):continue
   mask=smooth((long+.025)/.055)
   if mask<=0:continue
   maps={n:path_map(p,*path) for n,path in paths.items()}
   # Fingeridentity uses anatomicaldigit centerlines excluding commonpalmlink.
   true_dist={n:min(project(p,a,b)[2] for a,b in zip(path[0][1:],path[0][2:])) for n,path in paths.items()};digit=min(true_dist,key=true_dist.get);row=maps[digit];progress=row[2]
   # Smoothpalm deformation from anatomicallycorrespondingjoint displacements.
   controls=[(wold,Vector())]
   for path in paths.values():
    controls.extend((a,b-a) for a,b in zip(path[0][1:],path[1][1:]))
   ws=[1/((p-a).length_squared+.000025)**2 for a,d in controls];palmmapped=p+sum((d*w for (a,d),w in zip(controls,ws)),Vector())/sum(ws)
   fingerblend=smooth((progress+.004)/.022);mapped=palmmapped.lerp(row[1],fingerblend);newp=p.lerp(mapped,mask)
   v.co=newp;masks[index]=mask;changes.append(index)
   # Explicitper-digit chainweights. Nocopy of spatiallynear otherdigits.
   if progress>.003:
    old=paths[digit][0][1:];d01=(old[1]-old[0]).length;d12=(old[2]-old[1]).length
    rootblend=smooth((progress+.004)/.018);w12=smooth((progress-d01+.008)/.016);w23=smooth((progress-d01-d12+.007)/.014)
    vals={'hand_'+side:1-rootblend,digit+'_01_'+side:rootblend*(1-w12),digit+'_02_'+side:rootblend*w12*(1-w23),digit+'_03_'+side:rootblend*w12*w23};digit_assign[index]=digit
   else:vals={'hand_'+side:1.0}
   # Originalwrist weights retained at boundary; unwantedfingerfamilies never leak.
   oldvals=source_weights[index];cleanold={n:w for n,w in oldvals.items() if not n.startswith(('thumb_','index_','middle_','ring_','pinky_'))}
   if not cleanold:cleanold={'hand_'+side:1.0}
   total=sum(cleanold.values());cleanold={n:w/total for n,w in cleanold.items()};out={n:w*(1-mask) for n,w in cleanold.items()}
   for n,w in vals.items():out[n]=out.get(n,0)+w*mask
   set_weights(ob,v,out)
 outside=[i for i in range(len(ob.data.vertices)) if i not in masks]
 # Originalcopy for exactbitwise outside fingerprint; no positions/weights written there.
 after=fingerprint(ob,outside);original_hash=hashlib.sha256()
 for i in outside:
  original_hash.update(struct.pack('<I3f',i,*oldpositions[i]))
  for n,w in sorted(source_weights[i].items()):original_hash.update(n.encode()+b'\0'+struct.pack('<f',w))
 before=original_hash.hexdigest();assert before==after,'Outsidehandchanged'+ob.name;assert uv_hash(ob)==beforeuv
 maxinf=0;cross=0;unweighted=0
 for v in ob.data.vertices:
  gs=[(ob.vertex_groups[g.group].name,g.weight) for g in v.groups if g.weight>1e-6];maxinf=max(maxinf,len(gs));unweighted+=not bool(gs)
  if v.index in masks:
   families={n.split('_')[0] for n,w in gs if n.startswith(('thumb_','index_','middle_','ring_','pinky_'))};cross+=len(families)>1
 assert maxinf<=4 and not cross and not unweighted
 ob.data.update();ob.hide_render=lod!=0
 report['lods'].append({'name':ob.name,'vertices':len(ob.data.vertices),'changed_hand_vertices':len(masks),'outside_vertices':len(outside),'outside_position_weight_sha256_before':before,'outside_position_weight_sha256_after':after,'uv_sha256_unchanged':beforeuv,'maximum_displacement_cm':max((ob.data.vertices[i].co-oldpositions[i]).length*100 for i in masks),'max_influences':maxinf,'unweighted_vertices':unweighted,'changed_vertex_cross_digit_contamination':cross})
# Review with existing own authored sourcefist on the exact unchangedrig.
with bpy.data.libraries.load(str(CHARS/'Animations/Unarmed/Dink_Fist.blend'),link=False) as (a,b):b.actions=['Dink_Fist_Forward']
action=next(a for a in b.actions if a);arm.animation_data.action=action;arm.data.pose_position='POSE';scene.render.fps=40;scene.frame_start=1;scene.frame_end=17
for im in bpy.data.images:
 if im.filepath:im.filepath=bpy.path.relpath(im.filepath,start=str(ROOT))
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SK_Dink_Hands.blend'),relative_remap=False)
(ROOT/'hand_binding_report.json').write_text(json.dumps(report,indent=2)+'\n')
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
cam=scene.camera;cam.location=(2.4,-4.4,2.1);cam.rotation_euler=(Vector((0,-.10,1.0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=66
for key,frame in [('impact',8),('idle',1),('windup',4),('recoil',11)]:
 scene.frame_set(frame);scene.render.filepath=str(ROOT/'Previews'/('hands_'+key+'.png'));bpy.ops.render.render(write_still=True)
scene.frame_set(8);cam.location=(3.7,-.6,1.8);cam.rotation_euler=(Vector((0,-.15,1.05))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/'Previews/hands_impact_side.png');bpy.ops.render.render(write_still=True)
cam.location=(.6,-1.6,1.6);cam.rotation_euler=(Vector((-.08,-.63,1.32))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=90;scene.render.filepath=str(ROOT/'Previews/hands_fist_close.png');bpy.ops.render.render(write_still=True)
print('HANDV2 CANDIDATE REVIEW READY;ALL4LODS OUTSIDEHAND/UV FINGERPRINTS MATCH',flush=True)
