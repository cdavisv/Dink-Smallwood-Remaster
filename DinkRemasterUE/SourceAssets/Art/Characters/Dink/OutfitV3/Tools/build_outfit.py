"""Isolated wardrobe-only candidate. Never exports/imports or edits old sources.
Four original anatomical LODs/hand corrections and89restbones are preserved.
"""
import bpy,bmesh,json,math,random,hashlib,struct
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
from mathutils.geometry import barycentric_transform
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
ART=Path(__file__).resolve().parents[1];PROJECT=ART.parents[4]
SOURCE=ART.parent/'HandBindingV2/SK_Dink_Hands.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));scene=bpy.context.scene;arm=bpy.data.objects['Armature'];arm.data.pose_position='REST';arm.animation_data_create();arm.animation_data.action=None
for image in bpy.data.images:
 if image.filepath:image.filepath=bpy.path.abspath(image.filepath)
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
oldcollection=bpy.data.collections['SK_Dink_Hands'];oldcollection.name='SK_Dink_OutfitV3';oldcollection['dink_class']='character_hero';oldcollection['dink_path']='Hero/Refinements';oldcollection['dink_source']='Original layered Dink wardrobe V3, over unchanged frozen CC0-based HandBindingV2 anatomy and fixed89bone rig; no original sources overwritten.'
before_rig={b.name:{'parent':b.parent.name if b.parent else None,'matrix':[list(r) for r in b.matrix_local]} for b in arm.data.bones}
assert len(before_rig)==89
originals=[bpy.data.objects[f'SK_Dink_Hands_LOD{i}'] for i in range(4)]
high=originals[0]
snapshot=[]
for ob in originals:
 snapshot.append({'coords':[tuple(v.co) for v in ob.data.vertices],'weights':[[(g.group,g.weight) for g in v.groups] for v in ob.data.vertices],
  'polys':[tuple(p.vertices) for p in ob.data.polygons],'materials':[p.material_index for p in ob.data.polygons],'smooth':[p.use_smooth for p in ob.data.polygons],
  'uvs':[[tuple(v.uv) for v in layer.data] for layer in ob.data.uv_layers],'uvnames':[layer.name for layer in ob.data.uv_layers],
  'looseedges':[tuple(e.vertices) for e in ob.data.edges if e.is_loose],'groupnames':[g.name for g in ob.vertex_groups]})
protected_materials=[high.data.materials[i] for i in range(4)]
cloth_ids=[p.index for p in high.data.polygons if p.material_index==4]
# The original shirt shell is the connected3305-face component, not detached collar trim.
shirt_ids=[i for i in cloth_ids if 9834<=i<=13138]
high.data.calc_loop_triangles();shirt_triangles=[tuple(t.vertices) for t in high.data.loop_triangles if t.polygon_index in set(shirt_ids)]
shirt_surface=BVHTree.FromPolygons([v.co.copy() for v in high.data.vertices],shirt_triangles,all_triangles=True)
surface=BVHTree.FromPolygons([v.co.copy() for v in high.data.vertices],[list(high.data.polygons[i].vertices) for i in cloth_ids],all_triangles=False)
kd=KDTree(len(high.data.vertices))
for v in high.data.vertices:kd.insert(v.co,v.index)
kd.balance()
source_weights=[{high.vertex_groups[g.group].name:g.weight for g in v.groups} for v in high.data.vertices]
torso_ids=[]
for index in cloth_ids:
 poly=high.data.polygons[index];center=poly.center
 amount=sum(sum(w for n,w in source_weights[i].items() if n.startswith('spine_') or n=='pelvis') for i in poly.vertices)/len(poly.vertices)
 if 1.0<center.z<1.54 and abs(center.x)<.245 and amount>(.10 if abs(center.x)<.20 and center.z>1.33 else .48):torso_ids.append(index)
torso_surface=BVHTree.FromPolygons([v.co.copy() for v in high.data.vertices],[list(high.data.polygons[i].vertices) for i in torso_ids],all_triangles=False)
torso_bones={'pelvis',*[f'spine_{i:02}' for i in range(1,6)],'clavicle_l','clavicle_r'}
def weights(p,kind='surface',side=None):
 values={}
 if kind=='surface' and side is None:
  point,normal,face,dist=shirt_surface.find_nearest(Vector(p));tri=shirt_triangles[face]
  a,b,c=[high.data.vertices[i].co for i in tri]
  factors=barycentric_transform(point,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
  for index,factor in zip(tri,factors):
   for name,w in source_weights[index].items():values[name]=values.get(name,0)+w*max(0,factor)
  values=sorted(values.items(),key=lambda x:-x[1])[:4];total=sum(v for n,v in values)
  if total>1e-8:return [(n,v/total) for n,v in values]
  values={}
 for co,index,dist in kd.find_n(p,4):
  factor=1/max(dist,.002)**2
  for name,w in source_weights[index].items():
   allowed=(kind=='surface' or name in torso_bones) if side is None else (name in ['lowerarm_'+side,'lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side,'hand_'+side])
   if allowed:values[name]=values.get(name,0)+w*factor
 if not values:values={'spine_04':1} if side is None else {'lowerarm_'+side:1}
 values=sorted(values.items(),key=lambda x:-x[1])[:4];total=sum(v for n,v in values)
 return [(n,v/total) for n,v in values]
def fit(p,clearance=.016):
 origin=Vector((0,-.015,1.20));direction=(Vector(p)-origin).normalized()
 point,normal,face,dist=shirt_surface.ray_cast(origin,direction,1)
 if point is None:point,normal,face,dist=shirt_surface.find_nearest(Vector(p))
 if point is None:raise RuntimeError('Garment fitting missed shirt')
 return point+direction*clearance
def radial(z,angle,clearance=.016):
 direction=Vector((math.cos(angle),math.sin(angle),0));point,normal,face,dist=torso_surface.ray_cast(Vector((0,-.015,z)),direction,1)
 if point is None:return fit((math.cos(angle)*.18,math.sin(angle)*.13,z),clearance)
 return point+direction*clearance

# New original nine-region PBR atlas; the four immutable material refs are reused.
TEX=ART/'Textures';TEX.mkdir(exist_ok=True)
N=4096;T=N//3;rng=np.random.default_rng(1997)
bc=np.ones((N,N,4),np.float32);normal=np.ones_like(bc);normal[:,:,:3]=(.5,.5,1);orm=np.ones_like(bc)
palettes=[((.045,.075,.105),(.09,.135,.17),.83,'cloth'),((.055,.070,.026),(.13,.15,.062),.9,'cloth'),
 ((.065,.029,.011),(.18,.088,.035),.65,'leather'),((.018,.010,.006),(.055,.028,.012),.72,'leather'),
 ((.13,.015,.009),(.28,.045,.022),.68,'leather'),((.065,.032,.012),(.16,.078,.031),.69,'leather'),
 ((.22,.145,.06),(.37,.27,.13),.86,'cloth'),((.07,.08,.09),(.15,.17,.19),.39,'metal'),((.025,.017,.011),(.065,.04,.022),.9,'cloth')]
for tile,(low,hi,rough,kind) in enumerate(palettes):
 yy,xx=np.mgrid[0:T,0:T].astype(np.float32)/T
 grain=.5+.14*np.sin(xx*29+np.sin(yy*17))*.5+.08*np.sin(yy*57+xx*11)+rng.random((T,T),dtype=np.float32)*.12
 if kind=='cloth':height=.006*np.sin(xx*math.tau*195)*np.sin(yy*math.tau*260)+.002*(grain-.5);tone=grain+.035*np.sin(xx*math.tau*195)*np.sin(yy*math.tau*260)
 elif kind=='leather':height=.012*(grain-.5)+.0018*np.sin(xx*math.tau*330)*np.sin(yy*math.tau*257);tone=grain
 else:height=.002*np.sin(xx*math.tau*80)+.001*(grain-.5);tone=grain
 x=(tile%3)*T;y=(tile//3)*T;color=np.array(low,np.float32)+tone[:,:,None]*(np.array(hi,np.float32)-np.array(low,np.float32))
 bc[y:y+T,x:x+T,:3]=color;orm[y:y+T,x:x+T,0]=.97;orm[y:y+T,x:x+T,1]=np.clip(rough+(grain-.5)*.09,0,1);orm[y:y+T,x:x+T,2]=float(kind=='metal')
 dy,dx=np.gradient(height);n=np.dstack((-dx*65,-dy*65,np.ones_like(height)));n/=np.linalg.norm(n,axis=2)[:,:,None];normal[y:y+T,x:x+T,:3]=n*.5+.5
images={}
for suffix,pixels in [('BC',bc),('N',normal),('ORM',orm)]:
 image=bpy.data.images.new('T_Dink_WardrobeV3_'+suffix,width=N,height=N,alpha=True);image.colorspace_settings.name='sRGB' if suffix=='BC' else 'Non-Color';image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(TEX/(image.name+'.png'));image.file_format='PNG';image.save();images[suffix]=image
del bc,normal,orm
wardrobe=bpy.data.materials.new('MI_Dink_WardrobeV3');wardrobe.use_nodes=True;nodes=wardrobe.node_tree.nodes;links=wardrobe.node_tree.links;bs=nodes.get('Principled BSDF');bs.inputs['Specular IOR Level'].default_value=.3
for suffix,image in images.items():
 node=nodes.new('ShaderNodeTexImage');node.image=image
 if suffix=='BC':links.new(node.outputs['Color'],bs.inputs['Base Color'])
 elif suffix=='ORM':
  sep=nodes.new('ShaderNodeSeparateColor');links.new(node.outputs['Color'],sep.inputs[0]);links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 else:
  nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.45;links.new(node.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bs.inputs['Normal'])

def tileuv(tile,uv):return ((tile%3+.018+.964*uv[0])/3,(tile//3+.018+.964*uv[1])/3)
metal_image=bpy.data.images.get('T_Dink_Atlas_ORM')
metal_pixels=None
if metal_image:
 metal_pixels=np.empty(metal_image.size[0]*metal_image.size[1]*4,dtype=np.float32);metal_image.pixels.foreach_get(metal_pixels)
reports=[]
for lod,ob in enumerate(originals):
 src=snapshot[lod];newverts=[];newfaces=[];newtiles=[];newweights=[];tags=[]
 def addmesh(verts,faces,tile,kind='torso',side=None,tag='detail'):
  assert all(0<=i<len(verts) for face in faces for i in face),('Partindexoutside',tag)
  # Recalculate onlynew closed garment pieces; originalanatomical shading untouched.
  temporary=bpy.data.meshes.new('NewWardrobePartNormals');temporary.from_pydata(verts,[],faces)
  bm=bmesh.new();bm.from_mesh(temporary);tiny=[f for f in bm.faces if f.calc_area()<1e-8];bmesh.ops.delete(bm,geom=tiny,context='FACES_ONLY') if tiny else None;bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(temporary);bm.free()
  verts=[tuple(v.co) for v in temporary.vertices];faces=[tuple(p.vertices) for p in temporary.polygons];bpy.data.meshes.remove(temporary)
  start=len(newverts);newverts.extend([tuple(v) for v in verts]);newfaces.extend([tuple(start+i for i in f) for f in faces]);newtiles.extend([tile]*len(faces));newweights.extend([weights(Vector(v),kind,side) for v in verts]);tags.extend([tag]*len(verts))
 def ribbon(points,width,tile,clearance=.027,tag='strap',closed=False):
  centers=[fit(p,clearance) for p in points];verts=[]
  for i,p in enumerate(centers):
   tangent=(centers[(i+1)%len(centers)]-centers[(i-1)%len(centers)]).normalized() if closed else (centers[min(i+1,len(centers)-1)]-centers[max(0,i-1)]).normalized();point,normal,_,_=shirt_surface.find_nearest(p);normal=(p-Vector((0,-.015,1.20))).normalized();out=normal
   if normal.dot(out)<0:normal=-normal
   cross=normal.cross(tangent).normalized()
   left=fit(p-cross*width/2,clearance);right=fit(p+cross*width/2,clearance)
   verts.extend([left,right,left-normal*.003,right-normal*.003])
  faces=[]
  for i in range(len(centers) if closed else len(centers)-1):
   a=i*4;b=((i+1)%len(centers))*4;faces.extend([(a,a+1,b+1,b),(a+2,b+2,b+3,a+3),(a,b,b+2,a+2),(a+1,a+3,b+3,b+1)])
  if not closed:faces.extend([(0,2,3,1),(len(verts)-4,len(verts)-3,len(verts)-1,len(verts)-2)])
  addmesh(verts,faces,tile,kind="surface",tag=tag)
 def surface_strip(side,center,width,tile,offset,zmin,tag):
  # Clip the authoritative shirt triangles into an attached strip. No free loft.
  vv=[];ff=[]
  lo=center-width/2;hi=center+width/2
  def clip(poly,axis,bound,keep_above):
   result=[]
   for a,b in zip(poly,poly[1:]+poly[:1]):
    da=a[0][axis]-bound;db=b[0][axis]-bound;ina=da>=0 if keep_above else da<=0;inb=db>=0 if keep_above else db<=0
    if ina:result.append(a)
    if ina!=inb:
     t=da/(da-db);result.append((a[0].lerp(b[0],t),a[1].lerp(b[1],t)))
   return result
  for tri in shirt_triangles:
   points=[high.data.vertices[i].co.copy() for i in tri];centerpoint=sum(points,Vector())/3;normal=(points[1]-points[0]).cross(points[2]-points[0]).normalized()
   if normal.dot(centerpoint-Vector((0,-.015,1.2)))<0:continue
   poly=[(Vector((side*p.x-.2333333*(p.z-1.5),p.y,p.z)),high.data.vertices[i].normal.copy()) for p,i in zip(points,tri)]
   for axis,bound,above in [(0,lo,True),(0,hi,False),(2,zmin,True)]:
    poly=clip(poly,axis,bound,above)
    if not poly:break
   if len(poly)<3:continue
   start=len(vv)
   for point,n in poly:
    point.x=(point.x+.2333333*(point.z-1.5))*side;clearance=(-.025+.046*max(0,min(1,(point.z-1.29)/.065))-.010*max(0,min(1,(point.z-1.35)/.15))) if tag=='backpack_strap' else (.018-.010*max(0,min(1,(point.z-1.40)/.10))-.048*max(0,min(1,(1.38-point.z)/.045)));vv.append(point+n.normalized()*clearance)
   ff.append(tuple(range(start,len(vv))))
  temp=bpy.data.meshes.new('SurfaceStrip');temp.from_pydata(vv,[],ff);bm=bmesh.new();bm.from_mesh(temp);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bm.to_mesh(temp);bm.free()
  addmesh([v.co.copy() for v in temp.vertices],[tuple(p.vertices) for p in temp.polygons],tile,kind='surface',tag=tag);bpy.data.meshes.remove(temp)
 def box(center,size,tile,tag='pack',bevel=.008):
  bpy.ops.mesh.primitive_cube_add(size=1,location=center);temp=bpy.context.object;temp.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
  if bevel:
   mod=temp.modifiers.new('Rounded worn leather edges','BEVEL');mod.width=bevel;mod.segments=2 if lod<2 else 1;bpy.ops.object.modifier_apply(modifier=mod.name)
  addmesh([temp.matrix_world@v.co for v in temp.data.vertices],[tuple(p.vertices) for p in temp.data.polygons],tile,tag=tag);bpy.data.objects.remove(temp,do_unlink=True)
 # Sleeveless fitted leather jerkin with a real openV exposing blue undercloth.
 segments=[48,32,24,16][lod];rings=[13,10,8,6][lod];outer=[]
 for row in range(rings):
  t=row/(rings-1)
  for i in range(segments):
   angle=i*math.tau/segments;u=abs(math.cos(angle));top=1.34+.075*math.sin(angle)**2-.065*max(0,-math.sin(angle))**6
   z=1.01+(top-1.01)*t;p=radial(z,angle,.016+.0025*math.sin(t*math.pi)*math.sin(angle*7+t*5));outer.append(p)
 verts=outer+[p-Vector((p.x,p.y+.015,0)).normalized()*.004 for p in outer];count=len(outer);faces=[]
 for r in range(rings-1):
  for i in range(segments):
   a=r*segments+i;b=r*segments+(i+1)%segments;c=b+segments;d=a+segments;faces.extend([(a,b,c,d),(a+count,d+count,c+count,b+count)])
 for r in [0,rings-1]:
  for i in range(segments):
   a=r*segments+i;b=r*segments+(i+1)%segments;faces.append((a,a+count,b+count,b))
 addmesh(verts,faces,2,tag='jerkin')
 # Narrow sewnedge welts follow the actualopen neckline/hem; nofloating trim.
 for row in [0,rings-1]:
  curve=outer[row*segments:(row+1)*segments];vv=[];ff=[]
  for i,p in enumerate(curve):
   tangent=(curve[(i+1)%segments]-curve[(i-1)%segments]).normalized();normal=Vector((p.x,p.y+.015,.03)).normalized();normal=(normal-tangent*normal.dot(tangent)).normalized();cross=tangent.cross(normal).normalized();center=p+normal*.001
   for k in range(4):vv.append(center+(normal*math.cos(k*math.pi/2)+cross*math.sin(k*math.pi/2))*.0015)
  for i in range(segments):
   for k in range(4):ff.append((i*4+k,i*4+(k+1)%4,((i+1)%segments)*4+(k+1)%4,((i+1)%segments)*4+k))
  addmesh(vv,ff,3,tag='jerkin_seam')
 # Shoulder bridges sewfront/back panels into a single worn vest silhouette.
 for side in [-1,1]:
  pts=[]
  for i in range([15,11,9,7][lod]):
   t=i/([15,11,9,7][lod]-1);pts.append((side*.155,-.13+.26*t,1.36+.17*math.sin(t*math.pi)))
  surface_strip(side,.20,.052,2,.008,1.30,'jerkin_shoulder')
 # Continuous soft cloth collar, a smooth turned edge over the old shirt opening.
 collar_n=[64,48,32,24][lod];vv=[];ff=[]
 for row in range(4):
  t=row/3
  for i in range(collar_n):
   a=i*math.tau/collar_n;rx=.182*(1-t)+.092*t;ry=.124*(1-t)+.068*t
   vv.append(Vector((rx*math.cos(a),.012+ry*math.sin(a),1.492+.039*t-.013*max(0,-math.sin(a)))))
 for row in range(3):
  for i in range(collar_n):
   a=row*collar_n+i;b=row*collar_n+(i+1)%collar_n;ff.append((a,b,b+collar_n,a+collar_n))
 collar_count=len(vv);vv.extend([p-Vector((p.x,p.y-.012,0)).normalized()*.003 for p in vv])
 for face in list(ff):ff.append(tuple(i+collar_count for i in reversed(face)))
 for row in [0,3]:
  for i in range(collar_n):
   a=row*collar_n+i;b=row*collar_n+(i+1)%collar_n;ff.append((a,b,b+collar_count,a+collar_count))
 addmesh(vv,ff,0,kind='surface',tag='shirt_collar')
 # Small rounded backpack; its backcorners stay within the28cm torso capsule.
 back=radial(1.27,math.pi/2,.015).y;depth=.075;bagfront=back+.005;bagcenter=bagfront+depth/2
 box((0,bagcenter,1.275),(.238,depth,.30),5,tag='backpack',bevel=.014)
 box((0,bagcenter+.005,1.43),(.242,depth+.013,.055),5,tag='backpack_flap',bevel=.012)
 for side in [-1,1]:
  # Continuous close-fitting shoulder loops: front, over the shoulder, back.
  pts=[];n=[25,19,15,11][lod]
  for i in range(n):
   t=i/(n-1);angle=-math.pi/2+math.pi*t;pts.append((side*(.155+.005*math.sin(t*math.pi)),.15*math.sin(angle),1.18+.292*math.cos(angle)))
  for i in range(1,max(5,n//2)):
   t=i/max(5,n//2);pts.append((side*(.155+.070*math.sin(t*math.pi)),.15-.30*t,1.18-.035*math.sin(t*math.pi)))
  surface_strip(side,.20,.027,3,.023,1.28,'backpack_strap')
  # Packfastening tongues/buckles arefixed to the softpack surface.
  y=bagfront+depth+.006
  box((side*.060,y,1.285),(.020,.009,.20),3,tag='pack_tongue',bevel=.002)
  for x in [side*.060-.014,side*.060+.014]:box((x,y+.006,1.285),(.004,.005,.028),7,tag='pack_buckle',bevel=.001)
  for z in [1.272,1.298]:box((side*.060,y+.006,z),(.031,.005,.004),7,tag='pack_buckle',bevel=.001)
 # Mutedred forearmbracers outside sleeve, following existing unchanged forearmrig.
 for side in ['l','r']:
  wrist=arm.data.bones['hand_'+side].head_local;elbow=arm.data.bones['lowerarm_'+side].head_local;axis=(wrist-elbow).normalized();u=axis.cross(Vector((0,1,0))).normalized();v=axis.cross(u).normalized();sides=[24,18,14,10][lod];rows=[6,5,4,3][lod];outer=[]
  for row in range(rows):
   t=row/(rows-1);center=wrist-axis*(.025+.15*t)
   for i in range(sides):
    angle=i*math.tau/sides;p=center+(u*math.cos(angle)+v*math.sin(angle))*(.045+.006*t);point,normal,_,_=surface.find_nearest(p)
    direction=(p-center).normalized()
    if point is not None:p=point+direction*.007
    outer.append(p)
  vv=outer+[p-(p-(wrist-axis*(.025+.15*(i//sides)/(rows-1)))).normalized()*.003 for i,p in enumerate(outer)];count=len(outer);ff=[]
  for row in range(rows-1):
   for i in range(sides):
    a=row*sides+i;b=row*sides+(i+1)%sides;c=b+sides;d=a+sides;ff.extend([(a,b,c,d),(a+count,d+count,c+count,b+count)])
  for row in [0,rows-1]:
   for i in range(sides):
    a=row*sides+i;b=row*sides+(i+1)%sides;ff.append((a,a+count,b+count,b))
  addmesh(vv,ff,4,side=side,tag='red_bracer')
 # Buildnewdata inoriginalface/vertex order: immutable anatomical arrays stayfirst.
 base=len(src['coords']);allverts=src['coords']+newverts;allfaces=src['polys']+[tuple(base+i for i in f) for f in newfaces]
 data=bpy.data.meshes.new('SK_Dink_OutfitV3_LOD'+str(lod));data.from_pydata(allverts,src['looseedges'],allfaces);data.update()
 for material in [*protected_materials,wardrobe]:data.materials.append(material)
 oldcount=len(src['polys'])
 for i,p in enumerate(data.polygons):p.material_index=src['materials'][i] if i<oldcount else 4;p.use_smooth=src['smooth'][i] if i<oldcount else True
 # NewwardrobeplanarUVs permaterial-region; protectedUVloops copied bitexact.
 tile_ids=[]
 for poly in data.polygons[:oldcount]:
  center=poly.center;tile=0
  if poly.material_index==4:
   if center.z<.34:tile=3
   elif center.z<1.005 and abs(center.x)<.34:tile=1
   elif center.z<1.055 and abs(center.x)<.25:tile=3
   # Originalironbuckle is recognized byits authoritative baked metallic channel.
   oldpoly=ob.data.polygons[poly.index];oldUV=ob.data.uv_layers.active.data[oldpoly.loop_start].uv
   if metal_pixels is not None:
    x=min(metal_image.size[0]-1,max(0,int(oldUV.x*metal_image.size[0])));y=min(metal_image.size[1]-1,max(0,int(oldUV.y*metal_image.size[1])))
    if metal_pixels[(y*metal_image.size[0]+x)*4+2]>.3:tile=7
  tile_ids.append(tile)
 tile_ids.extend(newtiles)
 for layer_index,name in enumerate(src['uvnames']):
  uv=data.uv_layers.new(name=name)
  for poly in data.polygons:
   axis=max(range(3),key=lambda k:abs(poly.normal[k]));axes=[k for k in range(3) if k!=axis]
   for loop in poly.loop_indices:
    if poly.index<oldcount and poly.material_index!=4:uv.data[loop].uv=src['uvs'][layer_index][loop]
    else:
     p=data.vertices[data.loops[loop].vertex_index].co
     limits={0:(-.56,.56),1:(-.31,.28),2:(0,1.82)}
     if tile_ids[poly.index]==0:limits[2]=(.98,1.55)
     if tile_ids[poly.index]==1:limits[2]=(.30,1.04)
     if tile_ids[poly.index]==2:limits[0]=(-.26,.26);limits[1]=(-.20,.20);limits[2]=(1.0,1.51)
     if tile_ids[poly.index] in [3,5]:limits[0]=(-.28,.28);limits[1]=(-.30,.27)
     coords=[max(0,min(1,(p[k]-limits[k][0])/(limits[k][1]-limits[k][0]))) for k in axes];uv.data[loop].uv=tileuv(tile_ids[poly.index],coords)
 olddata=ob.data;ob.data=data;ob.name=data.name
 for name in src['groupnames']:ob.vertex_groups.new(name=name)
 for index,values in enumerate(src['weights']):
  for group,weight in values:ob.vertex_groups[group].add([index],weight,'REPLACE')
 for index,values in enumerate(newweights,base):
  for name,weight in values:ob.vertex_groups[name].add([index],weight,'REPLACE')
 ob.hide_render=lod!=0
 # Set the old wardrobe opening beneath the new turned cuff, leaving shirt continuity.
 protected_ids={i for p in data.polygons if p.material_index<4 for i in p.vertices}
 cloth_ids_local={i for p in data.polygons[:oldcount] if p.material_index==4 for i in p.vertices}
 assert not protected_ids & cloth_ids_local
 for index in cloth_ids_local:
  v=data.vertices[index];c=v.co
  if abs(c.x)<.14 and -.11<c.y<.11 and c.z>1.49:v.co.z=1.49
 data.update()
 counts={tag:tags.count(tag) for tag in set(tags)}
 reports.append({'lod':lod,'triangles':sum(len(p.vertices)-2 for p in data.polygons),'original_vertices':base,'new_vertices':len(newverts),'original_faces':oldcount,'new_faces':len(newfaces),'new_vertices_by_part':counts,'backpack_max_radius_m':max(math.hypot(p[0],p[1]) for p,tag in zip(newverts,tags) if tag.startswith(('backpack','pack_'))),'new_influence_max':max(len(v) for v in newweights)})
 assert reports[-1]['triangles']<=40000,'Preferredhero budget exceeded'
 assert len(data.materials)==5
 assert max(len([g for g in v.groups if g.weight>1e-6]) for v in data.vertices)<=4
 assert all(any(g.weight>1e-6 for g in v.groups) for v in data.vertices)
# No armature, anatomical coordinate, oldweight orprotectedUV edits are permitted.
assert before_rig=={b.name:{'parent':b.parent.name if b.parent else None,'matrix':[list(r) for r in b.matrix_local]} for b in arm.data.bones}
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.frame_set(1);arm.data.pose_position='REST'
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'construction_report.json').write_text(json.dumps({'stage':'SOURCE REVIEW ONLY; nofinalexport/import/manifest/ledger untilrootvisualgate','source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'rest_bones':89,'protected_material_refs':[m.name for m in protected_materials],'new_material':wardrobe.name,'lods':reports},indent=2)+'\n')
print('OUTFIT V3 SOURCE BUILT',reports,flush=True)
