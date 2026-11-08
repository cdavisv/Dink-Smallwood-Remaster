"""Deterministic Stonebrook cottage asset kit. Run in Blender 5.2 background mode.

blender -b --factory-startup -P SourceAssets/Art/tools/build_stonebrook.py
Sources use metres, Z up, front -Y. The companion dinkasset validator/exporter gates FBX.
"""
import bpy
import math
import json
import random
import sys
from pathlib import Path
import numpy as np
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import conventions as C
ART = ROOT / 'SourceAssets/Art/Stonebrook'
TEX = ART / 'Textures'
ART.mkdir(parents=True, exist_ok=True)
TEX.mkdir(parents=True, exist_ok=True)
random.seed(1997)
rng = np.random.default_rng(1997)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1400
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
scene.world.color = (.12,.12,.12)
MATERIALS = {}
ASSETS = {}
current = None
pieces = []

def noise2(n, frequency):
    """Smooth reproducible multi-scale value noise, no downloaded data."""
    small=rng.random((frequency+1,frequency+1))
    q=np.linspace(0,frequency,n,endpoint=False)
    lo=q.astype(int); f=q-lo; f=f*f*(3-2*f)
    a=small[lo[:,None],lo[None,:]]
    b=small[lo[:,None]+1,lo[None,:]]
    c=small[lo[:,None],lo[None,:]+1]
    d=small[lo[:,None]+1,lo[None,:]+1]
    return (a*(1-f[:,None])+b*f[:,None])*(1-f[None,:])+(c*(1-f[:,None])+d*f[:,None])*f[None,:]

def image(name, rgb, linear=False):
    n=rgb.shape[0]
    im=bpy.data.images.new(name,width=n,height=n,alpha=True)
    rgba=np.ones((n,n,4),dtype=np.float32); rgba[:,:,:3]=np.clip(rgb,0,1)
    im.colorspace_settings.name='Non-Color' if linear else 'sRGB'
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw=str(TEX/(name+'.png')); im.file_format='PNG'; im.save()
    return im

def material(name, kind, dark, light, rough=.7, metal=0):
    n=1024
    yy,xx=np.mgrid[:n,:n]/n
    broad=noise2(n,9); medium=noise2(n,64); fine=rng.random((n,n))
    if kind=='wood':
        bend=.025*np.sin(yy*12)+.008*np.sin(yy*39)+.013*(broad-.5)
        knots=np.zeros_like(xx)
        for cx,cy in [(.21,.3),(.72,.77),(.43,.9)]:
            r=np.sqrt(((xx-cx)*3)**2+((yy-cy)*.65)**2)
            knots += .05*np.exp(-r*18)*np.sin(r*260)
        grain=np.sin((xx+bend+knots)*860)*.5+.5
        pores=(np.sin((xx+bend)*2600)>.92)*(.2+.8*medium)
        h=.4*broad+.12*medium+.07*fine+.21*grain-.12*pores
        tone=.5*broad+.23*medium+.14*grain-.12*pores+.07*fine
    elif kind=='cloth':
        weave=(np.sin(xx*n*math.pi)*np.sin(yy*n*math.pi))
        # Uneven coarse woven warp and weft, not screen-space noise.
        warp=(np.sin(xx*math.pi*360)>.15).astype(float)
        weft=(np.sin(yy*math.pi*360)>.15).astype(float)
        h=.13*medium+.08*fine+.08*warp+.08*weft
        tone=.45+.25*broad+.12*medium+.10*warp+.08*weft
    else:
        h=.30*broad+.30*medium+.15*fine
        if kind=='stone': h += .09*np.sin(xx*38+medium*7)*np.sin(yy*28)
        tone=.35+.35*broad+.20*medium+.10*fine
    bc=np.array(dark)[None,None,:]+tone[:,:,None]*(np.array(light)-np.array(dark))[None,None,:]
    dx,dy=np.gradient(h)
    normal=np.dstack((-dy*5,-dx*5,np.ones_like(h)))
    normal/=np.linalg.norm(normal,axis=2)[:,:,None]; normal=normal*.5+.5
    orm=np.dstack((np.clip(.8+h*.3,.5,1),np.clip(rough+(medium-.5)*.15,0,1),np.full_like(h,metal)))
    imgs={s:image('T_'+name+'_'+s,v,s!='BC') for s,v in [('BC',bc),('N',normal),('ORM',orm)]}
    mat=bpy.data.materials.new('MI_'+name); mat.use_nodes=True
    nodes=mat.node_tree.nodes; links=mat.node_tree.links; bs=nodes.get('Principled BSDF')
    bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
    for suffix,im in imgs.items():
        node=nodes.new('ShaderNodeTexImage'); node.image=im; node.label=suffix
        if suffix=='BC': links.new(node.outputs['Color'],bs.inputs['Base Color'])
        if suffix=='N':
            norm=nodes.new('ShaderNodeNormalMap'); norm.inputs['Strength'].default_value=.38
            links.new(node.outputs['Color'],norm.inputs['Color']); links.new(norm.outputs['Normal'],bs.inputs['Normal'])
        if suffix=='ORM':
            sep=nodes.new('ShaderNodeSeparateColor'); links.new(node.outputs['Color'],sep.inputs[0])
            links.new(sep.outputs['Green'],bs.inputs['Roughness']); links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    MATERIALS[mat.name]={'name':mat.name,'base_color':list((np.array(dark)+np.array(light))*.5),'roughness':rough,'metallic':metal,
                         'textures':{s:str(Path('Textures')/(im.name+'.png')) for s,im in imgs.items()},'normal_flip_green':True,'normal_strength':.38}
    return mat

oak=material('Stonebrook_Oak','wood',(.09,.045,.018),(.44,.28,.13),.72)
plaster=material('Stonebrook_Limewash','plaster',(.42,.36,.26),(.83,.77,.62),.89)
stone=material('Stonebrook_Fieldstone','stone',(.17,.15,.12),(.49,.43,.34),.87)
linen=material('Stonebrook_Linen','cloth',(.27,.28,.19),(.64,.62,.43),.94)
iron=material('Stonebrook_WroughtIron','stone',(.035,.026,.02),(.15,.13,.10),.58,.82)
wicker=material('Stonebrook_Wicker','wood',(.15,.08,.023),(.55,.36,.12),.83)
soot=material('Stonebrook_Soot','stone',(.012,.009,.007),(.075,.055,.032),.98)

def start(name, cls='prop'):
    global current,pieces
    current=bpy.data.collections.new(name); scene.collection.children.link(current)
    current['dink_class']=cls; current['dink_path']='Stonebrook'
    current['dink_source']='Original deterministic Blender geometry and procedural textures; build_stonebrook.py seed 1997; no third-party images or meshes'
    pieces=[]

def add(ob,mat,bevel=0):
    for c in list(ob.users_collection): c.objects.unlink(ob)
    current.objects.link(ob)
    ob.data.materials.append(mat)
    bpy.context.view_layer.objects.active=ob
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    if bevel:
        mod=ob.modifiers.new('Worn hand-worked edges','BEVEL'); mod.width=bevel; mod.segments=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    pieces.append(ob)
    return ob

def box(pos,dim,mat=oak,bevel=.008,angle=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos)
    ob=bpy.context.object; ob.dimensions=dim; ob.rotation_euler[2]=angle
    return add(ob,mat,bevel)

def cyl(pos,radius,depth,mat=iron,vertices=12,rotation=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=pos,rotation=rotation or (0,0,0))
    return add(bpy.context.object,mat,0 if depth<.02 else min(.002,depth*.15,radius*.15))

def torus(pos,major,minor,mat=iron,segments=32,rotation=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major,minor_radius=minor,major_segments=segments,minor_segments=6,location=pos,rotation=rotation)
    return add(bpy.context.object,mat)

def beam(a,b,width,depth,mat=oak):
    mid=(Vector(a)+Vector(b))*.5; delta=Vector(b)-Vector(a)
    ob=box(mid,(width,depth,delta.length),mat,min(.008,width*.18,depth*.18))
    ob.rotation_euler=delta.to_track_quat('Z','Y').to_euler()
    bpy.context.view_layer.objects.active=ob; bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    return ob

def uv_sphere(pos,scale,mat=linen):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=1,location=pos)
    ob=bpy.context.object; ob.scale=scale
    add(ob,mat)
    for p in ob.data.polygons:p.use_smooth=True
    return ob

def collision(pos,dim,index):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos)
    ob=bpy.context.object;ob.dimensions=dim
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    for c in list(ob.users_collection):c.objects.unlink(ob)
    current.objects.link(ob)
    ob.name='UCX_'+current.name+'_'+str(index).zfill(2)
    scene.cursor.location=(0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    ob.hide_render=True; ob.display_type='WIRE'
    return ob

def finish(collisions):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in pieces:ob.select_set(True)
    bpy.context.view_layer.objects.active=pieces[0]; bpy.ops.object.join()
    ob=bpy.context.object;ob.name=current.name; ob.data.name=current.name+'_Mesh'
    # Collection render pivot at origin; kit floors use their walking surface as Z=0.
    scene.cursor.location=(0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.dissolve_degenerate(bm,dist=1e-6,edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.005)
    bpy.ops.object.mode_set(mode='OBJECT')
    for i,(pos,dim) in enumerate(collisions,1):collision(pos,dim,i)
    # Class-specific pivots must also be shared by every UCX hull.
    coords=[v.co for v in ob.data.vertices]
    mn=Vector(tuple(min(v[i] for v in coords) for i in range(3)))
    mx=Vector(tuple(max(v[i] for v in coords) for i in range(3)))
    cls=current['dink_class']
    if cls in ['kit_floor','kit_ceiling']:
        delta=Vector((mn.x,mn.y,mx.z if cls=='kit_floor' else mn.z))
    elif cls=='kit_wall':delta=Vector((mn.x,(mn.y+mx.y)/2,mn.z))
    elif cls=='kit_piece':delta=Vector((0,0,mn.z))
    else:delta=Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,mn.z))
    for child in current.objects:
        for v in child.data.vertices:v.co-=delta
    dims=list(ob.dimensions)
    ASSETS[current.name]={'class':current['dink_class'],'dimensions_m':dims,'materials':[s.material.name for s in ob.material_slots],
                          'fbx':'Export/'+C.content_path(current['dink_class'],current.name,'Stonebrook').lstrip('/')+'.fbx','blend_collection':current.name,'pivot':'origin, ground center; kit modules follow companion CONVENTIONS.md'}
    return ob

# Heavily used furniture follows plausible hand-built dimensions rather than billboard extents.
start('SM_Table_Oak_01')
for x in [-1.08,1.08]:
    for y in [-.48,.48]:
        box((x,y,.405),(.14,.14,.81),bevel=.015)
        cyl((x,y,.83),.022,.014,iron,10)
for y in [-.5,.5]:box((0,y,.68),(2.37,.12,.21))
for x in [-1.08,1.08]:box((x,0,.68),(.12,1.02,.21))
box((0,0,.24),(2.28,.10,.11))
for i in range(7):
    y=-.65+i*.215
    box((0,y,.85+random.uniform(-.003,.003)),(2.65,.208,.095),bevel=.012)
    for x in [-1.08,1.08]:cyl((x,y,.902),.014,.008,iron,8)
finish([((0,0,.85),(2.65,1.5,.1)),((-1.08,0,.4),(.18,1.1,.8)),((1.08,0,.4),(.18,1.1,.8))])

start('SM_Bed_Oak_01')
for x in [-1.15,1.15]:
    for y in [-.58,.58]:
        box((x,y,.52),(.14,.14,1.04),bevel=.018)
        uv_sphere((x,y,1.04),(.105,.105,.08),oak)
for y in [-.62,.62]:box((0,y,.36),(2.4,.13,.25))
for x in [-1.15,1.15]:
    for z in [.52,.70,.88]:box((x,0,z),(.12,1.2,.13))
for i in range(10):box((-1.05+i*.23,0,.37),(.17,1.12,.065))
uv_sphere((0,0,.52),(1.15,.58,.18),linen)
uv_sphere((-.82,0,.72),(.31,.45,.12),linen)
# Soft draped bedcover; double surface closes the cloth and catches the lamp light.
verts=[]; faces=[]; nx=29; ny=19
for side in [0,1]:
    for i in range(nx):
        for j in range(ny):
            x=-.5+i/(nx-1)*1.55;y=-.67+j/(ny-1)*1.34
            drop=max(0,abs(y)-.51)*1.0
            z=.69-drop+.018*math.sin(x*18+y*5)+.012*math.sin(y*34+x*3)-side*.018
            verts.append((x,y,z))
for side in [0,1]:
    ofs=side*nx*ny
    for i in range(nx-1):
        for j in range(ny-1):
            a=ofs+i*ny+j; f=(a,a+ny,a+ny+1,a+1)
            faces.append(f if side==0 else tuple(reversed(f)))
boundary=[j for j in range(ny)]+[i*ny+ny-1 for i in range(1,nx)]+[(nx-1)*ny+j for j in range(ny-2,-1,-1)]+[i*ny for i in range(nx-2,0,-1)]
for k,a in enumerate(boundary):b=boundary[(k+1)%len(boundary)];faces.append((a,b,b+nx*ny,a+nx*ny))
me=bpy.data.meshes.new('Blanket');me.from_pydata(verts,[],faces);me.update()
ob=bpy.data.objects.new('Blanket',me);current.objects.link(ob);ob.data.materials.append(linen);pieces.append(ob)
for p in me.polygons:p.use_smooth=True
finish([((0,0,.4),(2.45,1.35,.8))])

start('SM_Chair_Oak_01')
for x in [-.24,.24]:
    for y in [-.23,.23]:
        box((x,y,.23),(.07,.07,.46))
        if y>.0:box((x,y,.68),(.065,.065,.65))
for y in [-.18,0,.18]:box((0,y,.47),(.65,.175,.065),bevel=.012)
for z in [.25,.89]:box((0,.24,z),(.53,.06,.10))
for x in [-.13,0,.13]:box((x,.24,.72),(.05,.05,.32))
for x in [-.24,.24]:box((x,0,.19),(.05,.48,.055))
finish([((0,0,.25),(.62,.60,.5)),((0,.24,.77),(.6,.08,.50))])

start('SM_Fireplace_Fieldstone_01','prop_large')
# Separate solid stones preserve the open firebox; no full rectangular collision hull.
for x in [-1.52,1.52]:
    for course in range(7):
        z=.15+course*.28
        for dy in [-.34,0,.34]:
            box((x+random.uniform(-.018,.018),dy,z),(.54+random.uniform(-.03,.03),.33,.265),stone,.025)
for row in range(2):
    for i in range(8):
        box((-1.65+i*.47,0,2.10+row*.27),(.46,.95,.265),stone,.024)
box((0,0,2.48),(4.02,1.16,.20),oak,.028)
for course in range(6):
    for i in range(5):box((-1.24+i*.62,.2,2.72+course*.26),(.60,.80,.25),stone,.02)
box((0,.48,.96),(2.55,.12,1.90),soot,.005)
for i in range(8):box((-1.65+i*.47,-.19,.06),(.46,1.5,.12),stone,.02)
for y in [-.18,.13]:
    for x in [-.7,-.35,0,.35,.7]:cyl((x,y,.21),.025,.28,iron,8)
for y in [-.18,.13]:beam((-.9,y,.30),(.9,y,.30),.04,.04,iron)
for x,rot in [(-.25,.28),(.23,-.22)]:box((x,-.13,.35),(1.15,.16,.16),oak,.025,rot)
finish([((-1.52,0,1),(.65,1.1,2)),((1.52,0,1),(.65,1.1,2)),((0,0,3.2),(3.5,1.1,2.4))])

start('SM_Basket_Wicker_01')
# Woven ribs are modeled, so close views show a real open basket rather than a textured cube.
cyl((0,0,.045),.34,.09,wicker,32)
for i in range(32):
    a=i*math.tau/32
    beam((.30*math.cos(a),.30*math.sin(a),.06),(.44*math.cos(a),.44*math.sin(a),.57),.016,.018,wicker)
for i in range(13):
    z=.08+i*.039;r=.30+z*.24
    torus((0,0,z),r,.015,wicker,32)
torus((0,0,.59),.443,.028,wicker,32)
for x in [-.43,.43]:torus((x,0,.53),.12,.022,wicker,20,(math.pi/2,0,0))
finish([((0,0,.30),(.88,.88,.60))])

start('SM_FeedSack_Jute_01')
verts=[];faces=[];rings=24;segs=36
for j in range(rings):
    t=j/(rings-1); z=.02+t*.75
    r=.08+.27*math.sin(math.pi*t)**.58
    if t>.8:r*=.65
    for i in range(segs):
        a=i*math.tau/segs;rr=r*(1+.045*math.sin(a*9+t*7)+.025*math.sin(a*17-t*11))
        verts.append((rr*math.cos(a),rr*.78*math.sin(a),z))
for j in range(rings-1):
    for i in range(segs):a=j*segs+i;b=j*segs+(i+1)%segs;faces.append((a,b,b+segs,a+segs))
faces.append(tuple(reversed(range(segs))));faces.append(tuple((rings-1)*segs+i for i in range(segs)))
me=bpy.data.meshes.new('JuteSack');me.from_pydata(verts,[],faces);me.update()
ob=bpy.data.objects.new('JuteSack',me);current.objects.link(ob);ob.data.materials.append(linen);pieces.append(ob)
for p in me.polygons:p.use_smooth=True
for z in [.65,.67,.69]:torus((0,0,z),.135,.012,wicker,24)
finish([((0,0,.38),(.65,.52,.75))])

start('SM_Floor_Oak_2m_01','kit_floor')
for i in range(8):
    for j in range(2):
        box((.125+i*.25,.5+j,-.055),(.244,.992,.11),oak,.006)
        for y in [.07+j,.93+j]:cyl((.125+i*.25,y,-.002),.006,.004,iron,8)
finish([((1,1,-.07),(2,2,.14))])

start('SM_Wall_Limewash_2m_01','kit_wall')
box((1,0,1.75),(1.8,.22,3.5),plaster,.018)
for x in [.1,1.9]:box((x,0,1.75),(.20,.30,3.5),oak,.012)
for z in [.12,2.2,3.38]:box((1,-.045,z),(2,.27,.24),oak,.012)
beam((.19,-.17,2.3),(.82,-.17,3.29),.12,.08)
beam((1.18,-.17,3.29),(1.81,-.17,2.3),.12,.08)
finish([((1,0,1.75),(2,.30,3.5))])

start('SM_Doorway_Limewash_4m_01','kit_piece')
for x in [.625,3.375]:box((x,0,1.75),(1.25,.22,3.5),plaster,.018)
box((2,0,3.0),(1.5,.22,1.0),plaster,.018)
for x in [.1,1.25,2.75,3.9]:box((x,0,1.75 if x in [.1,3.9] else 1.25),(.18,.32,3.5 if x in [.1,3.9] else 2.5),oak,.015)
for z in [2.5,3.38]:box((2,0,z),(4,.3,.24),oak,.015)
finish([((.625,0,1.75),(1.25,.32,3.5)),((3.375,0,1.75),(1.25,.32,3.5)),((2,0,3.0),(1.5,.32,1))])

start('SM_Ceiling_Oak_2m_01','kit_ceiling')
for i in range(8):box((.125+i*.25,1,.10),(.247,2,.20),oak,.006)
box((1,1,.05),(.16,2,.10),oak,.012)
finish([((1,1,.10),(2,2,.20))])

start('SM_Window_Limewash_2m_01','kit_wall')
box((1,0,.55),(2,.22,1.10),plaster,.012)
box((1,0,3.05),(2,.22,.90),plaster,.012)
for x in [.25,1.75]:box((x,0,1.85),(.50,.22,1.5),plaster,.01)
for x in [.1,1.9]:box((x,0,1.75),(.20,.30,3.5),oak,.012)
for x in [.50,1.5]:box((x,0,1.85),(.12,.36,1.62),oak,.009)
for z in [1.1,2.6]:box((1,-.02,z),(1.2,.42,.14),oak,.012)
box((1,0,1.85),(.055,.1,1.4),oak,.005)
box((1,0,1.85),(.95,.1,.055),oak,.005)
finish([((1,0,.55),(2,.30,1.1)),((1,0,3.05),(2,.30,.90)),((.25,0,1.85),(.5,.30,1.5)),((1.75,0,1.85),(.5,.30,1.5))])

start('SM_Barrel_Oak_01')
for i in range(18):
    angle=i*math.tau/18
    for j in range(4):
        z=.14+j*.24;r=.32+.075*math.sin(z/1.0*math.pi)
        ob=box((r*math.cos(angle),r*math.sin(angle),z),(.115,.060,.238),oak,.006,angle+math.pi/2)
for z in [.12,.30,.72,.91]:torus((0,0,z),.33+.075*math.sin(z*math.pi),.025,iron,36)
for i in range(5):
    y=-.26+i*.13;l=2*math.sqrt(max(.01,.32**2-y**2))
    box((0,y,.985),(l,.123,.045),oak,.005)
cyl((0,0,.035),.33,.07,oak,36)
finish([((0,0,.50),(.75,.75,1.0))])

start('SM_Candle_Iron_01','prop_small')
cyl((0,0,.018),.10,.036,iron,20)
cyl((0,0,.14),.018,.25,iron,12)
cyl((0,0,.255),.07,.02,iron,20)
cyl((0,0,.345),.045,.17,plaster,16)
cyl((0,0,.438),.003,.025,iron,8)
finish([])

start('SM_Pie_Rustic_01','prop_small')
cyl((0,0,.025),.245,.05,iron,32)
uv_sphere((0,0,.068),(.23,.23,.045),wicker)
torus((0,0,.075),.223,.020,wicker,40)
for i in range(16):
    a=i*math.tau/16
    box((.223*math.cos(a),.223*math.sin(a),.08),(.022,.025,.016),wicker,.003,a)
for x in [-.14,-.07,0,.07,.14]:
    half=math.sqrt(.205**2-x*x)
    beam((x,-half,.103),(x,half,.103),.019,.013,wicker)
for y in [-.14,-.07,0,.07,.14]:
    half=math.sqrt(.205**2-y*y)
    beam((-half,y,.113),(half,y,.113),.018,.012,wicker)
finish([])

# Material/placement contract consumed by the Unreal Python dressing script.
manifest={'schema':'dink-stonebrook-art/1','units':'metres; exported FBX declares UnitScaleFactor=100 (Unreal converts to cm)',
          'seed':1997,'source':'KIT_Stonebrook.blend','assets':ASSETS,'materials':MATERIALS,
          'placements':[{'origin':'S001_P22','mesh':'SM_Table_Oak_01','source_pixel':[299,243],'yaw':0},
                        {'origin':'S001_P23','mesh':'SM_Bed_Oak_01','source_pixel':[215,298],'yaw':0},
                        {'origin':'S001_P24','mesh':'SM_Bed_Oak_01','source_pixel':[428,297],'yaw':0},
                        {'origin':'S001_P19','mesh':'SM_Fireplace_Fieldstone_01','source_pixel':[288,120],'yaw':0},
                        {'origin':'S001_P52','mesh':'SM_FeedSack_Jute_01','source_pixel':[448,130],'yaw':0}],
          'notes':['Assets are original procedural candidates for local playtest review, not a completed whole-game art pass.',
                   'Keep art components NoCollision until measured against gameplay hardness. FBX includes separate UCX hulls for future replacement.',
                   'No scale based on billboard pixel dimensions: intended furniture dimensions are explicitly recorded.']}
(ART/'art_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

# Room placement plan is interpreted in the original 600x400 screen coordinates.
# Kit walls run along +X from their origin. Window and doorway openings remain genuine holes.
runtime={'schema':'dink-art/1','screen':1,'hide_screen_visuals':[1],
         'hide_origins':['S001_P%02d'%i for i in list(range(1,26))+[37,51,52]],
         'replacements':[{'origin':'S001_P51','mesh':'SM_Pie_Rustic_01','source_pixel':[302,223],'height_cm':90,'rotation_deg':[0,0,0],'scale':[1,1,1]}], 'elements':[], 'lights':[]}
def element(name,mesh,px,py,z=0,yaw=0,scale=(1,1,1)):
    runtime['elements'].append({'name':name,'mesh':mesh,'source_pixel':[px,py],'height_cm':z,'rotation_deg':[0,yaw,0],'scale':list(scale)})
for row in range(7):
    for col in range(8):
        element('Floor_%d_%d'%(col,row),'SM_Floor_Oak_2m_01',130+col*42.5,100+row*(300/7),scale=(.9296875,.9375,1))
        element('Ceiling_%d_%d'%(col,row),'SM_Ceiling_Oak_2m_01',130+col*42.5,100+row*(300/7),z=350,scale=(.9296875,.9375,1))
for i in range(8):
    element('NorthWall_%d'%i,'SM_Window_Limewash_2m_01' if i in [1,6] else 'SM_Wall_Limewash_2m_01',130+i*42.5,100,scale=(.9296875,1,1))
for side,x,yaw in [('West',130,90),('East',470,90)]:
    for i in range(7):element(side+'Wall_%d'%i,'SM_Window_Limewash_2m_01' if i in [2,4] else 'SM_Wall_Limewash_2m_01',x,100+i*(300/7),yaw=yaw,scale=(.9375,1,1))
# Door module spans4m, clear1.5m centered x305 at the original warp's y395.
element('SouthDoor','SM_Doorway_Limewash_4m_01',305-2/.04375,400,yaw=0)
left=(305-2/.04375)-130;right=470-(305+2/.04375)
for side,startpx,length in [('Left',130,left),('Right',305+2/.04375,right)]:
    n=math.ceil(length*.04375/2)
    for i in range(n):element('SouthWall_'+side+str(i),'SM_Wall_Limewash_2m_01',startpx+i*length/n,400,scale=(length*.04375/(2*n),1,1))
for origin,mesh,px,py,yaw in [('S001_P22','SM_Table_Oak_01',301,231,0),('S001_P23','SM_Bed_Oak_01',194.5,287.5,0),('S001_P24','SM_Bed_Oak_01',407.5,286.5,0),('S001_P19','SM_Fireplace_Fieldstone_01',289.5,113.5,0),('S001_P52','SM_FeedSack_Jute_01',448,130,0)]:
    runtime['replacements'].append({'origin':origin,'mesh':mesh,'source_pixel':[px,py],'rotation_deg':[0,yaw,0],'scale':[1,1,1]})
for name,mesh,px,py,z,yaw in [('Chair1','SM_Chair_Oak_01',301,207,0,180),('Chair2','SM_Chair_Oak_01',301,257,0,0),('WickerBasket','SM_Basket_Wicker_01',446,146,0,15),('Barrel1','SM_Barrel_Oak_01',148,120,0,0),('Barrel2','SM_Barrel_Oak_01',149,142,0,14),('Candle1','SM_Candle_Iron_01',300,231,90,0),('Candle2','SM_Candle_Iron_01',279,116,258,0)]:
    element(name,mesh,px,py,z,yaw)
for px,py,z,lumens,temp,radius in [(300,231,150,50,2700,520),(289,116,90,150,2700,390),(170,145,250,450,5000,420),(430,215,260,450,5000,440),(300,330,270,120,4000,480)]:
    runtime['lights'].append({'source_pixel':[px,py],'height_cm':z,'lumens':lumens,'kelvin':temp,'radius_cm':radius})
(ART/'room_layout.json').write_text(json.dumps(runtime,indent=2)+'\n')

# Preview arrangement is a separate non-asset collection. Exporter shifts assets to origin.
preview=bpy.data.collections.new('Preview_Stage');scene.collection.children.link(preview)
for i,(name,meta) in enumerate(ASSETS.items()):
    ob=bpy.data.objects[name]
    if 'Ceiling_' in name:
        ob.hide_render=True; pos=(8,5,0)
    elif 'Floor_' in name:pos=(-2.8,-2.6,0)
    elif 'Window_' in name:pos=(-6,2.4,0)
    elif 'Wall_' in name:pos=(-4,2.4,0)
    elif 'Doorway_' in name:pos=(0,2.4,0)
    elif 'Fireplace_' in name:pos=(0,1.4,0)
    elif 'Table_' in name:pos=(0,-1.6,0)
    elif 'Bed_' in name:pos=(-3,-.4,0)
    elif 'Chair_' in name:pos=(.3,-3.0,0)
    elif 'Basket_' in name:pos=(2.6,-.4,0)
    elif 'Barrel_' in name:pos=(2.8,-1.6,0)
    elif 'Candle_' in name:pos=(0,-1.6,.91)
    elif 'Pie_' in name:pos=(.6,-1.6,.91)
    else:pos=(1.8,-2.8,0)
    # Move all source assets as units. Exporter shifts their render/collision group to origin.
    for child in bpy.data.collections[name].objects: child.location+=Vector(pos)

def area(pos,power,color,size):
    ld=bpy.data.lights.new('Preview_Window','AREA');ld.energy=power;ld.color=color;ld.shape='DISK';ld.size=size
    ob=bpy.data.objects.new('Preview_Window',ld);preview.objects.link(ob);ob.location=pos
    ob.rotation_euler=(Vector((0,0,1))-ob.location).to_track_quat('-Z','Y').to_euler()
area((1,-3,7),1500,(1,.83,.64),5)
area((-6,-1,4),1000,(.62,.76,1),4)
area((0,2,3),400,(1,.54,.23),2)
camera=bpy.data.cameras.new('Preview_Camera');cam=bpy.data.objects.new('Preview_Camera',camera);preview.objects.link(cam)
cam.location=(8,-12,8);cam.rotation_euler=(Vector((0,0,1))-cam.location).to_track_quat('-Z','Y').to_euler();camera.lens=45;scene.camera=cam
scene.render.filepath=str(ART/'preview_kit.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'KIT_Stonebrook.blend'))
bpy.ops.render.render(write_still=True)
print('STONEBROOK ART: built',len(ASSETS),'assets;',len(MATERIALS),'PBR texture sets')
