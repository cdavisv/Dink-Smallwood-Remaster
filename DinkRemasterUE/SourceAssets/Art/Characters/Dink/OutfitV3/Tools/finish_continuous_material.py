import bpy,bmesh,json,numpy as np
from pathlib import Path
from mathutils import Vector
ART=Path('<HOME>/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));report=json.loads((ART/'continuous_shirt_report.json').read_text());tiles=[tuple(v) for v in report['allocated_tiles']];tile_indices={v:i for i,v in enumerate(tiles)};count=report['shirt_faces'];rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];m=ob.data;remove=[]
 for p in m.polygons:
  if p.material_index!=4:continue
  uv=sum((m.uv_layers[0].data[i].uv for i in p.loop_indices),Vector((0,0)))/len(p.vertices);key=(int(uv.y*4096)//8,int((uv.x-1)*4096)//8);idx=tile_indices.get(key,-1)
  if 0<=idx<count and p.center.z<1.275 and abs(p.center.x)<.21:remove.append(p.index)
 bm=bmesh.new();bm.from_mesh(m);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[i] for i in remove],context='FACES_ONLY');bm.to_mesh(m);bm.free();rows.append(len(remove))
for suffix in ['BC','N','ORM']:
 image=bpy.data.images['T_Dink_WardrobeV3_'+suffix];data=np.empty(4096*4096*4,np.float32);image.pixels.foreach_get(data);data=data.reshape(4096,4096,4)
 for i,(y,x) in enumerate(tiles):
  blue=i<count
  color=(.0675,.105,.1375,1) if blue else (.070,.036,.016,1)
  if suffix=='N':color=(.5,.5,1,1)
  if suffix=='ORM':color=(1,.84 if blue else .72,0,1)
  block=np.empty((8,8,4),np.float32);block[:]=color
  if suffix=='BC':
   yy,xx=np.mgrid[:8,:8];grain=1+.012*np.sin(xx*1.7+yy*2.3+x*.31+y*.21);block[:,:,:3]*=grain[:,:,None]
  data[y*8:(y+1)*8,x*8:(x+1)*8]=block
 image.pixels.foreach_set(data.ravel());image.save()
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'continuous_material_finish.json').write_text(json.dumps({'scope':'Only newly allocated wardrobe atlas cells changed: approved blue/brown palette, subtle grain, flat tangent normals and dielectric roughness eliminate donor-buckle metallic artifacts. Hidden shirt torso ends inside the leather jerkin. No protected material changes.','hidden_torso_faces_removed':rows,'cloth_linear_rgb':[.0675,.105,.1375],'strap_linear_rgb':[.070,.036,.016]},indent=2)+'\n')
