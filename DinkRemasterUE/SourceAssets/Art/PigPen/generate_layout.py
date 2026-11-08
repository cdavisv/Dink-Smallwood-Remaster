"""Deterministic screen407 source dressing using existing validated environment kits."""
import json,math,random
from pathlib import Path
ART=Path(__file__).resolve().parent;ROOT=ART.parents[2]
screen=next(s for s in json.loads((ROOT/'ImportData/screens.json').read_text())['screens'] if s['screen']==407)
placements=[p for p in json.loads((ROOT/'ImportData/placements.json').read_text())['placements'] if p['screen']==407]
c=screen['corners'];nw,ne,se,sw=[c[k] for k in ['nw','ne','se','sw']]
def world(p):
 u,v=p[0]/600,p[1]/400
 return [nw[i]*(1-u)*(1-v)+ne[i]*u*(1-v)+se[i]*u*v+sw[i]*(1-u)*v for i in range(2)]
def pixel(p):
 q=[300.,200.]
 for _ in range(10):
  a=world(q);b=world([q[0]+1,q[1]]);d=world([q[0],q[1]+1]);j00,j10=b[0]-a[0],b[1]-a[1];j01,j11=d[0]-a[0],d[1]-a[1];det=j00*j11-j01*j10;dx,dy=a[0]-p[0],a[1]-p[1];q[0]-=(j11*dx-j01*dy)/det;q[1]-=(-j10*dx+j00*dy)/det
 return q
pig_ids=[p['id'] for p in placements if p['class_id']=='pig']
layout={'schema':'dink-art/1','screen':407,'hide_screen_visuals':[407],'authored_collision_screens':[407],'hide_origins':[p['id'] for p in placements if p['id'] not in pig_ids],'replacements':[],'elements':[],'lights':[], 'asset_paths':{name:'/Game/Dink/Kits/StonebrookExterior/'+name+'.'+name for name in ['SM_Ground_Meadow_20m_01','SM_Fence_SplitRail_4m_01','SM_Boulder_Fieldstone_01','SM_Grass_Meadow_01','SM_Path_Earth_8m_01']}}
def add(name,mesh,p,z=0,yaw=0,scale=(1,1,1),collision=False):
 layout['elements'].append({'name':name,'mesh':mesh,'source_pixel':p,'height_cm':z,'rotation_deg':[0,yaw,0],'scale':list(scale),'collision':collision})
minimum=[min(v[i] for v in c.values())-.02 for i in range(2)];maximum=[max(v[i] for v in c.values())+.02 for i in range(2)];width=(maximum[0]-minimum[0])/3;depth=(maximum[1]-minimum[1])/2
for row in range(2):
 for col in range(3):add(f'Meadow_{col}_{row}','SM_Ground_Meadow_20m_01',pixel([minimum[0]+(col+.5)*width,minimum[1]+(row+.5)*depth]),z=-9.8,scale=(width/20,depth/20,1),collision=True)
# Physical fence centre-lines preserve the pen, original west opening and outer screen limits.
segments=[('OuterWest',[23.5,99],[23.5,400]),('OuterNW',[23.5,99],[110,57.5]),('OuterNorth',[110,57.5],[432,57.5]),('OuterNE',[432,57.5],[516,106]),('OuterEastTop',[516,106],[600,111.5]),('PenNorth',[136.5,147.5],[476,147.5]),('PenEast',[476,147.5],[476,366.5]),('PenSouth',[136.5,366.5],[476,366.5]),('PenWestUpper',[136.5,147.5],[136.5,230]),('PenWestLower',[136.5,286],[136.5,366.5])]
fences=[]
for name,a,b in segments:
 wa,wb=world(a),world(b);dx,dy=wb[0]-wa[0],wb[1]-wa[1];length=math.hypot(dx,dy);count=math.ceil(length/4);part=length/count;yaw=math.degrees(math.atan2(dy,dx))
 for i in range(count):
  t=(i+.5)/count;p=pixel([wa[0]+dx*t,wa[1]+dy*t]);add(f'{name}_{i:02}','SM_Fence_SplitRail_4m_01',p,yaw=yaw,scale=(part/4.18,1,1),collision=True)
 fences.append({'name':name,'a_pixel':a,'b_pixel':b,'length_m':length,'modules':count})
# A source no-hard rail southwest of the enclosure is intentionally retired: a new solid
# rail there would seal the original approach corridor. Its origin remains in hide_origins.
# Path asset is corner-anchored: BlenderX0..8m and importedY-2..0m.
# Offset its anchor by half the chosen width to centre each intended dirt span.
def dirt_span(name,a,b,width_m=2.8,z_cm=.4):
 wa,wb=world(a),world(b);dx,dy=wb[0]-wa[0],wb[1]-wa[1];length=math.hypot(dx,dy);ux,uy=dx/length,dy/length;anchor=pixel([wa[0]-uy*width_m/2,wa[1]+ux*width_m/2])
 add(name,'SM_Path_Earth_8m_01',anchor,z=z_cm,yaw=math.degrees(math.atan2(dy,dx)),scale=(length/8,width_m/2,1))
for row in range(7):
 for col in range(4):dirt_span(f'TroddenEarth_{col}_{row}',[155+col*75,172+row*27],[238+col*75,172+row*27],4.0,z_cm=.4+row*.015+col*.002)
# Nonblocking west-gate approach follows the original accessible corridor.
for i,(a,b,w) in enumerate([([90,400],[90,258],3.0),([90,258],[225,258],3.0),([90,390],[420,390],2.4)]):dirt_span(f'AccessDirt_{i}',a,b,w)
rng=random.Random(407)
for p in placements:
 xy=[p['map_x'],p['map_y']]
 if p['category']=='rock':
  k=rng.uniform(.10,.22);add(p['id']+'_Pebble','SM_Boulder_Fieldstone_01',xy,yaw=rng.uniform(0,360),scale=(k,k,rng.uniform(.06,.12)))
 elif p['category']=='flora_grass':
  k=rng.uniform(.65,1.05);add(p['id']+'_Grass','SM_Grass_Meadow_01',xy,yaw=rng.uniform(0,360),scale=(k,k,k))
 elif p['class_id']=='seed_scatter':add(p['id']+'_Feed','SM_FeedScatter_Wheat_01',xy,z=.6,yaw=rng.uniform(0,360))
# Restrained meadow accents around the outer fence; keep west gate, feeding box and
# Milder's eastern approach clear. All accents are nonblocking.
for i in range(50):
 x,y=rng.uniform(45,575),rng.uniform(75,385)
 if 70<x<160 and 230<y<400:continue
 if 120<x<490 and 135<y<380:continue
 if x>500 and 160<y<250:continue
 k=rng.uniform(.65,1.15);add(f'MeadowAccent_{i:02}','SM_Grass_Meadow_01',[x,y],yaw=rng.uniform(0,360),scale=(k,k,k))
(ART/'pigpen_layout.json').write_text(json.dumps(layout,indent=2)+'\n')
inventory={'screen':407,'source_screen':screen,'raw_count':len(placements),'visible_count':sum(p['type'] in [0,1] for p in placements),'pig_origins_preserved':pig_ids,'hidden_nonpig_origins':layout['hide_origins'],'placements':[{k:p[k] for k in ['id','type','kind','class_id','category','map_x','map_y','brain','script','seq','frame','hardness']} for p in placements]}
(ART/'source_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
gate_a,gate_b=world([136.5,230]),world([136.5,286]);gate=math.dist(gate_a,gate_b)
checks={'status':'source-layout candidate; not yet imported or physically verified','schema':'dink-art/1','fences':fences,'gate':{'west_x_pixel':136.5,'north_pixel':230,'south_pixel':286,'width_m':gate,'capsule_diameter_m':.56,'clearance_m':gate-.56,'route_center_pixel':[136.5,258]},'feeding_scatter_box':[200,180,400,306],'feeding_player_fixture':[300,250],'milder_corridor':{'from_pixel':[680,200],'to_pixel':[542,338],'coordinate_space':'original DinkC engine pixels; x includes20px margin','canonical_from_pixel':[660,200],'canonical_to_pixel':[522,338],'keep_clear_x_min':500,'keep_clear_coordinate_space':'canonical source screen pixels','direction':1},'retired_visual_only_fences':['S407_P18','S407_P23'],'source_type2_overlapping_hardness':['S407_P60','S407_P62'],'original_scripts_preserved':True,'new_environment_colliders':'ground and fence only','asset_dependencies':{'new':'art_manifest.json','existing':'../StonebrookExterior/exterior_manifest.json'},'element_count':len(layout['elements']),'grain_bottom_cm':.6,'max_soil_surface_cm':max(e['height_cm'] for e in layout['elements'] if e['mesh']=='SM_Path_Earth_8m_01')}
(ART/'layout_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print('PIGPEN LAYOUT:',len(layout['elements']),'elements;',len(layout['hide_origins']),'hidden non-pig origins; gate',round(gate,3),'m')
