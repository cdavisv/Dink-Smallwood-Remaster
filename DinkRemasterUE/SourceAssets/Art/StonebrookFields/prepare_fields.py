"""Source-fitted screen terrain. Host Python3.14 + Shapely2.1.2; no UE writes.

Install pinned helper outside the project/system:
uv pip install --python /usr/bin/python3 --target /tmp/dink-fields-tools314 shapely==2.1.2
"""
import sys,json,math,random,hashlib
from pathlib import Path
from collections import deque
sys.path.insert(0,'/tmp/dink-fields-tools314')
import shapely
from shapely.geometry import box,Polygon,Point
from shapely.ops import unary_union,transform
from PIL import Image,ImageDraw
ART=Path(__file__).resolve().parent
ROOT=ART.parents[2] if (ART.parents[2]/'ImportData').exists() else Path(Path(__file__).resolve().parents[3])
screens=json.loads((ROOT/'ImportData/screens.json').read_text())['screens']
placements=json.loads((ROOT/'ImportData/placements.json').read_text())['placements']
coll=json.loads((ROOT/'ImportData/collision.json').read_text())['screens']
def polys(g):
 if g.is_empty:return []
 return [g] if g.geom_type=='Polygon' else [p for sub in g.geoms for p in polys(sub)]
def raster_polygon(mask):
 spans=[]
 for y,row in enumerate(mask):
  x=0
  while x<600:
   if not row[x]:x+=1;continue
   a=x
   while x<600 and row[x]:x+=1
   spans.append(box(a,y,x,y+1))
 return unary_union(spans)
def largest_blue(im):
 rgb=list(im.convert('RGB').get_flattened_data());mask=[b>r*1.28 and b>g*1.04 and b>55 for r,g,b in rgb]
 best=[]
 for i in range(len(mask)):
  if not mask[i]:continue
  q=[i];mask[i]=False;component=[]
  while q:
   p=q.pop();component.append(p);x,y=p%600,p//600
   for n in ([p-1] if x else [])+([p+1] if x<599 else [])+([p-600] if y else [])+([p+600] if y<399 else []):
    if mask[n]:mask[n]=False;q.append(n)
  if len(component)>len(best):best=component
 out=[[False]*600 for _ in range(400)]
 for i in best:out[i//600][i%600]=True
 # Painting highlights leave tiny holes; the largest outline is the shoreline.
 p=max(polys(raster_polygon(out)),key=lambda p:p.area)
 return Polygon(p.exterior).simplify(1.2,preserve_topology=True)
report={'schema':'dink-fields-source/1','status':'source-only candidate; UE import and physical QA pending','screens':{}}
for sid in [471,438]:
 s=next(s for s in screens if s['screen']==sid);ps=[p for p in placements if p['screen']==sid];c=s['corners'];nw,ne,se,sw=[c[k] for k in ['nw','ne','se','sw']]
 def world(p):
  u,v=p[0]/600,p[1]/400
  return [nw[i]*(1-u)*(1-v)+ne[i]*u*(1-v)+se[i]*u*v+sw[i]*(1-u)*v for i in range(2)]
 def pixel(p):
  q=[300.,200.]
  for _ in range(12):
   a=world(q);b=world([q[0]+1,q[1]]);d=world([q[0],q[1]+1]);j00,j10=b[0]-a[0],b[1]-a[1];j01,j11=d[0]-a[0],d[1]-a[1];det=j00*j11-j01*j10;dx,dy=a[0]-p[0],a[1]-p[1];q[0]-=(j11*dx-j01*dy)/det;q[1]-=(-j10*dx+j00*dy)/det
  return [round(v,7) for v in q]
 def to_world(g):return transform(lambda x,y:tuple(world((x,y))),g)
 sourcewater=largest_blue(Image.open(ROOT/f'ImportData/ground/SCR_{sid}.png'))
 low=unary_union([box(*r) for r in coll[f'SCR_{sid:03}']['low']])
 if sid==471:
  outer=unary_union([box(*r) for r in coll['SCR_471']['fill_water']]+[p for p in polys(low) if p.area>1000])
  outer=max(polys(outer.buffer(.01)),key=lambda p:p.area)
  outer=Polygon(outer.exterior).simplify(.7,preserve_topology=True)
 else:
  ring=max(polys(low),key=lambda p:p.area)
  outer=Polygon(ring.exterior).simplify(.7,preserve_topology=True)
 # Never let painted water extend beyond its physical source envelope.
 sourcewater=sourcewater.intersection(outer.buffer(-.1))
 quad=Polygon([nw,ne,se,sw]);hazard=to_world(outer).intersection(quad);water=to_world(sourcewater).intersection(hazard)
 dry=quad.difference(hazard);bank=hazard.difference(water)
 layout={'schema':'dink-art/1','screen':sid,'hide_screen_visuals':[sid],
  'authored_collision_screens':[sid],'preserve_low_collision_screens':[sid],
  'hide_origins':[p['id'] for p in ps if p['category']!='creature'],'replacements':[],'elements':[],'lights':[],
  'asset_paths':{n:'/Game/Dink/Kits/StonebrookExterior/'+n+'.'+n for n in ['SM_Oak_Stonebrook_01','SM_Boulder_Fieldstone_01','SM_Grass_Meadow_01']}}
 # Explicit actors, not category heuristics, protect every pillbug including vision1.
 protected=[p['id'] for p in ps if p['class_id']=='pillbug'];layout['hide_origins']=[p['id'] for p in ps if p['id'] not in protected]
 def add(name,mesh,p,z=0,yaw=0,scale=(1,1,1),collision=False):
  layout['elements'].append({'name':name,'mesh':mesh,'source_pixel':p,'height_cm':z,'rotation_deg':[0,yaw,0],'scale':list(scale),'collision':collision})
 chunks=[];minx,miny,maxx,maxy=quad.bounds
 # Each6m tile has its own source-fitted vertices and SW pivot. Blender+Y
 # imports as Unreal-Y, so mirrored localY is intentional, not an offset hack.
 for role,area in [('Land',dry),('Bank',bank),('Water',water)]:
  for ix in range(math.ceil((maxx-minx)/6)):
   for iy in range(math.ceil((maxy-miny)/6)):
    clipped=area.intersection(box(minx+ix*6,miny+iy*6,minx+(ix+1)*6,miny+(iy+1)*6)).simplify(.025,preserve_topology=True)
    if clipped.is_empty or clipped.area<.008:continue
    for part,p in enumerate(polys(clipped)):
     if p.area<.008:continue
     name=f'SM_Fields_{sid}_{role}_{ix:02}_{iy:02}_{part:02}'
     x0,y0,x1,y1=p.bounds;anchor=[x0,y1]
     def height(x,y):
      if role=='Water':return -.8
      if role=='Land':return 0.
      q=Point(x,y);a=q.distance(hazard.boundary);b=q.distance(water.boundary)
      return -.85*a/(a+b) if a+b>1e-9 else 0.
     triangles=[]
     for tri in shapely.constrained_delaunay_triangles(p).geoms:
      xy=list(tri.exterior.coords)[:3]
      triangles.append([[round(x-x0,6),round(y1-y,6),round(height(x,y),6)] for x,y in xy])
     ztop=max(v[2] for t in triangles for v in t)
     for t in triangles:
      for v in t:v[2]=round(v[2]-ztop,6)
     # Isolated bank slivers may be smaller than floor minimum; this is a
     # documented shoreline-fitting exception, not a new source class.
     chunks.append({'name':name,'role':role,'anchor_world_m':anchor,'height_m':ztop,'triangles':triangles,
       'world_polygon':shapely.to_geojson(p),'dimensions_xy_m':[x1-x0,y1-y0]})
     add(name,name,pixel(anchor),ztop*100,collision=role=='Land')
 rng=random.Random(sid)
 for p in ps:
  xy=[p['map_x'],p['map_y']];cl=p['class_id']
  if cl=='pillbug':continue
  if 'pine' in cl:add(p['id']+'_Pine','SM_Pine_Stonebrook_01',xy,yaw=rng.uniform(0,360))
  elif p['category']=='flora_tree':
   add(p['id']+'_Tree','SM_Oak_Stonebrook_01',xy,yaw=rng.uniform(0,360),scale=(1.1,1.1,1.1),collision=sid==438)
  else:
   add(p['id']+'_Grass','SM_Grass_Meadow_01',xy,z=-80 if water.contains(Point(world(xy))) else 0,yaw=rng.uniform(0,360),scale=(.8,.8,.8))
 # Dress source low-rock islands with fitted nonblocking fieldstones. The
 # original Low collider remains authoritative, so projectiles retain parity.
 rockgroups=[]
 for n,p in enumerate(polys(low)):
  if p.area<50 or p.area>1000:continue
  if sid==438 and p.intersection(outer).area>p.area*.5:continue
  r=to_world(p);a,b,d,e=r.bounds;center=[(a+d)/2,(b+e)/2]
  add(f'SourceLowRock_{n}','SM_Boulder_Fieldstone_01',pixel(center),yaw=0,scale=((d-a)/2.12042,(e-b)/1.69344,max(.35,min(1.15,(d-a)*.26))))
  rockgroups.append({'pixel_bounds':list(p.bounds),'area_px':p.area,'new_collision':False})
 for n in range(70 if sid==438 else 55):
  q=[rng.uniform(15,585),rng.uniform(15,385)]
  if not dry.buffer(-.65).contains(Point(world(q))):continue
  k=rng.uniform(.55,1.05);add(f'MeadowAccent_{n:03}','SM_Grass_Meadow_01',q,yaw=rng.uniform(0,360),scale=(k,k,k))
 (ART/f'fields_{sid}_layout.json').write_text(json.dumps(layout,indent=2)+'\n')
 (ART/f'geometry_{sid}.json').write_text(json.dumps({'screen':sid,'chunks':chunks},separators=(',',':'))+'\n')
 inv={'screen':s,'placements':ps,'collision_rectangles':coll[f'SCR_{sid:03}'],'protected_actor_ids':protected,
   'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'ImportData/screens.json',ROOT/'ImportData/placements.json',ROOT/'ImportData/collision.json',ROOT/f'ImportData/ground/SCR_{sid}.png']}}
 (ART/f'inventory_{sid}.json').write_text(json.dumps(inv,indent=2)+'\n')
 # Quantified source geometry, without claiming physical/rendered acceptance.
 report['screens'][str(sid)]={'corners':c,'protected_actor_ids':protected,'hidden_origins':layout['hide_origins'],
  'source_collision_counts':s['rect_counts'],'original_low_and_fill_water_retained':True,
  'land_m2':dry.area,'bank_m2':bank.area,'water_m2':water.area,'water_top_m':-.8,
  'max_chunk_xy_m':max(max(ch['dimensions_xy_m']) for ch in chunks),'chunks':len(chunks),
  'rock_groups':rockgroups,'source_bridge':False,'new_warp_or_fact_changes':False,
  'terrain_partition_error_m2':quad.symmetric_difference(unary_union([dry,bank,water])).area,
  'dry_land_over_source_water_m2':dry.intersection(hazard).area,
  'water_runtime_collision':False,'bank_runtime_collision':False,'land_runtime_collision':True,
  'source_aquatic_accents':[{'name':e['name'],'height_cm':e['height_cm']} for e in layout['elements'] if e['name'].startswith('S') and e['mesh']=='SM_Grass_Meadow_01' and e['height_cm']<0]}
 im=Image.new('RGB',(1200,800),'#1f2823');draw=ImageDraw.Draw(im)
 for area,color in [(dry,'#46683e'),(bank,'#76644a'),(water,'#245c65')]:
  # inverse-transform each contour to original screen coordinates for faithful map preview.
  for p in polys(area):
   draw.polygon([(pixel(v)[0]*2,pixel(v)[1]*2) for v in p.exterior.coords],fill=color)
 for e in layout['elements']:
  if 'Pine' in e['mesh'] or 'Oak' in e['mesh'] or 'Boulder' in e['mesh']:
   x,y=e['source_pixel'];draw.ellipse((x*2-7,y*2-7,x*2+7,y*2+7),fill='#c6ac76')
 for p in ps:
  if p['id'] in protected:
   x,y=p['map_x'],p['map_y'];draw.text((x*2,y*2),p['id'],fill='white')
 draw.text((12,12),f'Screen{sid}: source-fitted candidate, water nonphysical; original Low retained',fill='white')
 im.save(ART/f'preview_layout_{sid}.png')
 assert report['screens'][str(sid)]['terrain_partition_error_m2']<.001
 assert report['screens'][str(sid)]['max_chunk_xy_m']<=6.001
 assert set(protected).isdisjoint(layout['hide_origins'])
(ART/'layout_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print('FIELDS SOURCE:',{s:(v['chunks'],round(v['water_m2'],1)) for s,v in report['screens'].items()})
