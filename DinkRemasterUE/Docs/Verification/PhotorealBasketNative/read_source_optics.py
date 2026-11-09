import bpy,json,hashlib,os
from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=root/'SourceAssets/Art/Stonebrook/Refinements/PhotorealBasketV1'
rows=[]
for name in ['PhotorealBasketV1_Source.blend','PhotorealBasketV1_Export.blend']:
 path=source/name;before=hashlib.sha256(path.read_bytes()).hexdigest()
 bpy.ops.wm.open_mainfile(filepath=str(path))
 obj=bpy.data.objects['SM_Basket_Wicker_01']
 assert len(obj.data.materials)==1
 mat=obj.data.materials[0]
 nodes=[n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED']
 assert len(nodes)==1
 bs=nodes[0]; fields={}
 for key in ['IOR','Specular IOR Level','Metallic','Coat Weight','Transmission Weight','Sheen Weight','Subsurface Weight']:
  socket=bs.inputs[key]
  fields[key]={'linked':socket.is_linked,'default':float(socket.default_value)}
 assert not fields['IOR']['linked'] and abs(fields['IOR']['default']-1.46)<1e-6
 assert not fields['Specular IOR Level']['linked'] and abs(fields['Specular IOR Level']['default']-.25)<1e-6
 for key in ['Coat Weight','Transmission Weight','Sheen Weight','Subsurface Weight']:
  assert not fields[key]['linked'] and fields[key]['default']==0,(name,key,fields)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==before
 rows.append({'file':str(path.relative_to(root)),'sha256':before,'material':mat.name,'fields':fields})
result={'passed':True,'read_only':True,'source_materials':rows,'ue_specular_normal_incidence':((1.46-1)/(1.46+1))**2*(2*.25)/.08,'scope':'Normal incidence dielectric F0 mapping only; no exact full BRDF/render parity claim.'}
(root/'Saved/BasketReviewed/source_optics.json').write_text(json.dumps(result,indent=2)+'\n')
print('SOURCE_OPTICS_PASS',flush=True);os._exit(0)
