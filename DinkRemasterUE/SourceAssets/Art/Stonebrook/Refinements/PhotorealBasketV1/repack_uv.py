"""UV-only strip atlas; preserve source geometry, attributes, materials and collider."""
import bpy,json,math,os,sys,hashlib,traceback
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent;S=O.parent;BASE=O/'Inputs/V4_Source.blend'
try:
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.preferences.filepaths.save_version=0
 ob=bpy.data.objects['SM_Basket_Wicker_01'];me=ob.data;uv=me.uv_layers.active
 def geom():return hashlib.sha256(json.dumps({'v':[list(v.co)for v in me.vertices],'p':[list(p.vertices)for p in me.polygons],'a':{a.name:[list(v.vector)for v in a.data]if a.data_type=='FLOAT_VECTOR'else[float(v.value)for v in a.data]for a in me.attributes if a.name in ['ReedMetric','ReedSeed']}},sort_keys=True).encode()).hexdigest()
 before=geom();parent=list(range(len(me.vertices)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for edge in me.edges:
  a,b=map(find,edge.vertices);parent[a]=b
 groups={}
 for v in me.vertices:groups.setdefault(find(v.index),[]).append(v.index)
 grouped_faces={}
 for f in me.polygons:grouped_faces.setdefault(find(f.vertices[0]),[]).append(f)
 charts=[];metric=me.attributes['ReedMetric'].data
 def chart(w,h):
  c={'w':max(w,1e-6),'h':max(h,1e-6),'loops':[]};charts.append(c);return c
 for key,indices in groups.items():
  indices.sort();start=indices[0];assert indices==list(range(start,start+len(indices)))
  sides=1
  while sides<len(indices)and abs(metric[indices[sides]].vector.x-metric[start].vector.x)<1e-9:sides+=1
  assert sides in [4,6],sides
  count=len(indices)//sides;assert count*sides==len(indices)
  centers=[sum((me.vertices[start+i*sides+k].co for k in range(sides)),Vector())/sides for i in range(count)]
  d=[0.]
  for i in range(1,count):d.append(d[-1]+(centers[i]-centers[i-1]).length)
  total=d[-1]+(centers[0]-centers[-1]).length
  cross=[me.vertices[start+k].co for k in range(sides)];per=[0.]
  for k in range(sides):per.append(per[-1]+(cross[(k+1)%sides]-cross[k]).length)
  # Deliberately split long curved charts at <=25cm to avoid huge empty convex hulls.
  sections={};cuts=[0]
  for i in range(1,count-1):
   if d[i]-d[cuts[-1]]>=.25:cuts.append(i)
  cuts.append(count-1)
  for j in range(len(cuts)-1):
   a,b=cuts[j:j+2];c=chart(d[b]-d[a],per[-1])
   for i in range(a,b):sections[i]=(c,d[a])
  closed_chart=None
  for f in grouped_faces[key]:
   locals=[v-start for v in f.vertices];rings={i//sides for i in locals}
   if len(rings)==1:
    # End cap: separate planar chart, never stacked onto the tube chart.
    points=[me.vertices[v].co for v in f.vertices];base=points[0];u=(points[1]-base).normalized();normal=f.normal.normalized();v=normal.cross(u).normalized();xy=[((p-base).dot(u),(p-base).dot(v))for p in points];lo=[min(p[k]for p in xy)for k in range(2)];hi=[max(p[k]for p in xy)for k in range(2)];c=chart(hi[0]-lo[0],hi[1]-lo[1]);c['loops']=[(li,x-lo[0],y-lo[1])for li,(x,y)in zip(f.loop_indices,xy)]
   else:
    assert len(rings)==2 and len(locals)==4
    ring=min(rings);closing=rings=={0,count-1}
    if closing:
     if closed_chart is None:closed_chart=chart(total-d[-1],per[-1])
     c,offset=closed_chart,d[-1]
    else:c,offset=sections[ring]
    ks={i%sides for i in locals};seam=ks=={0,sides-1}
    for li,local in zip(f.loop_indices,locals):
     ri,k=divmod(local,sides);x=(total if closing and ri==0 else d[ri])-offset;y=per[-1]if seam and k==0 else per[k]
     c['loops'].append((li,x,y))
 # Height-sorted shelves, using rectangles in physical metres and a4px island gap.
 ordered=sorted(charts,key=lambda c:(-c['h'],-c['w']))
 def pack(side,commit=False):
  gap=4*side/2048;x=gap;y=gap;row=0
  for c in ordered:
   if x+c['w']+gap>side:x=gap;y+=row+gap;row=0
   if y+c['h']+gap>side:return False
   if commit:c['x']=x;c['y']=y
   x+=c['w']+gap;row=max(row,c['h'])
  return True
 low=max(max(c['w'],c['h'])for c in charts);high=10.
 for _ in range(36):
  mid=(low+high)/2
  if pack(mid):high=mid
  else:low=mid
 side=high*1.00001;assert pack(side,True)
 assigned=set()
 for c in charts:
  for li,x,y in c['loops']:uv.data[li].uv=((c['x']+x)/side,(c['y']+y)/side);assigned.add(li)
 assert len(assigned)==len(me.loops);assert geom()==before,'Non-UV mutation'
 # Identical source shader makes this a clean bake-density experiment.
 bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealBasketV1_Source.blend'))
 sys.path.insert(0,str(O/'Pipeline'));from dinkasset.validate import uv_stats
 stats=uv_stats(me);stats['density_px_per_m']=2048*math.sqrt(stats['uv_area']/stats['area_3d'])
 report={'source_geometry_attributes_sha256_before_after':before,'geometry_and_attributes_unchanged':True,'parts':len(groups),'charts':len(charts),'atlas_side_m':side,'nominal_gap_pixels':4,'stats':stats,'source_before_sha256':hashlib.sha256((BASE).read_bytes()).hexdigest(),'source_after_sha256':hashlib.sha256((O/'PhotorealBasketV1_Source.blend').read_bytes()).hexdigest()}
 (O/'uv_repack_receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));sys.stdout.flush();sys.stderr.flush();os._exit(0)
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
