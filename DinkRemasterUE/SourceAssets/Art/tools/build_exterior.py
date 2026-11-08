"""Original realistic Stonebrook exterior kit; Blender 5.2 background build.
Requires the first Stonebrook kit materials. Does not modify that kit.
"""
import bpy, bmesh, math, json, random, sys
from pathlib import Path
import numpy as np
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import conventions as C
from dinkasset import common, make_lods
ART=ROOT/'SourceAssets/Art/StonebrookExterior'
TEX=ART/'Textures'
ART.mkdir(parents=True,exist_ok=True);TEX.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/Art/Stonebrook/KIT_Stonebrook.blend'))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):bpy.data.collections.remove(c)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.world.color=(.2,.2,.2)
random.seed(439);rng=np.random.default_rng(439)
ASSETS={};current=None;pieces=[]
base=json.loads((ROOT/'SourceAssets/Art/Stonebrook/art_manifest.json').read_text())
MATERIALS=base['materials']
for m in MATERIALS.values():
 for suffix,path in m['textures'].items():m['textures'][suffix]='../Stonebrook/'+path
oak=bpy.data.materials['MI_Stonebrook_Oak'];plaster=bpy.data.materials['MI_Stonebrook_Limewash']
stone=bpy.data.materials['MI_Stonebrook_Fieldstone'];iron=bpy.data.materials['MI_Stonebrook_WroughtIron']
wicker=bpy.data.materials['MI_Stonebrook_Wicker'];linen=bpy.data.materials['MI_Stonebrook_Linen']

def noise2(n, frequency):
    """Smooth reproducible multi-scale value noise, no downloaded data."""
    small=rng.random((frequency+1,frequency+1))
    small[-1,:]=small[0,:];small[:,-1]=small[:,0]
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


def start(name, cls='prop'):
    global current,pieces
    current=bpy.data.collections.new(name); scene.collection.children.link(current)
    current['dink_class']=cls; current['dink_path']='StonebrookExterior'
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
                          'fbx':'Export/'+C.content_path(current['dink_class'],current.name,'StonebrookExterior').lstrip('/')+'.fbx','blend_collection':current.name,'pivot':'origin, ground center; kit modules follow companion CONVENTIONS.md'}
    return ob


thatch=material('Stonebrook_Thatch','wood',(.10,.070,.025),(.44,.35,.15),.94)
leaf=material('Stonebrook_OakLeaf','stone',(.018,.045,.009),(.20,.31,.055),.82)
meadow=material('Stonebrook_Meadow','stone',(.028,.043,.012),(.21,.25,.071),.97)
dirt=material('Stonebrook_Earth','stone',(.060,.039,.023),(.30,.21,.12),.95)
MATERIALS[leaf.name]['two_sided']=True

def mesh(name,verts,faces,mat):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);current.objects.link(ob);ob.data.materials.append(mat);pieces.append(ob)
    return ob

def tapered_branch(a,b,r0,r1,mat=oak,sides=12):
    a,b=Vector(a),Vector(b);delta=b-a;rot=delta.to_track_quat('Z','Y').to_matrix()
    verts=[]
    for center,r in [(a,r0),(b,r1)]:
        for i in range(sides):
            ang=i*math.tau/sides;verts.append(tuple(center+rot@Vector((r*math.cos(ang),r*math.sin(ang),0))))
    faces=[tuple(reversed(range(sides))),tuple(sides+i for i in range(sides))]
    for i in range(sides):j=(i+1)%sides;faces.append((i,j,j+sides,i+sides))
    ob=mesh('Branch',verts,faces,mat)
    for p in ob.data.polygons:p.use_smooth=True
    return ob

def roof_panel(y1,z1,y2,z2):
    # Sloping closed solid; source remains editable quads, exporter triangulates.
    x0,x1=-9.4,9.4
    verts=[(x0,y1,z1),(x1,y1,z1),(x1,y2,z2),(x0,y2,z2),
           (x0,y1,z1-.27),(x1,y1,z1-.27),(x1,y2,z2-.27),(x0,y2,z2-.27)]
    return mesh('ThatchedRoof',verts,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],thatch)

start('SM_Cottage_Stonebrook_01','building')
# Front is -Y in Blender, +Y after FBX axis conversion. Door is intentionally off centre.
door_x=5.3
box((0,0,.11),(18,9,.22),stone,.02)
for face_y in [-4.5,4.5]:
    for course in range(4):
        z=.25+course*.29
        x=-9.0
        while x<8.95:
            width=min(random.uniform(.65,1.15),9-x)
            cx=x+width/2
            if face_y>0 or abs(cx-door_x)>1.0:
                box((cx,face_y,z),(width-.02,.50,.275),stone,.032)
            x+=width
    # Upper limewashed panels, each fitted between real timber posts.
    for i in range(12):
        x=-8.25+i*1.5
        if face_y<0 and abs(x-door_x)<1.5:continue
        box((x,face_y,2.40),(1.40,.25,2.35),plaster,.018)
    for i in range(13):
        x=-9+i*1.5
        if face_y<0 and abs(x-door_x)<.72:continue
        box((x,face_y-.04,2.39),(.17,.38,2.5),oak,.015)
    for z in [1.24,3.53]:
        if face_y<0 and z<2.5:
            left_end=door_x-.85;right_start=door_x+.85
            box(((-9+left_end)/2,face_y,z),(left_end+9,.38,.20),oak,.018)
            box(((right_start+9)/2,face_y,z),(9-right_start,.38,.20),oak,.018)
        else:box((0,face_y,z),(18,.38,.20),oak,.018)
for face_x in [-9,9]:
    for course in range(4):
        for i in range(10):box((face_x,-4.05+i*.9,.25+course*.29),(.5,.87,.275),stone,.03)
    box((face_x,0,2.4),(.25,9,2.3),plaster,.012)
    for i in range(7):box((face_x,-4.5+i*1.5,2.4),(.38,.17,2.5),oak,.016)
    for z in [1.24,3.53]:box((face_x,0,z),(.38,9,.20),oak,.016)
    # Closed, plastered triangular gable and a stout central king post.
    verts=[(face_x-.13,-4.5,3.5),(face_x-.13,4.5,3.5),(face_x-.13,0,7.0),
           (face_x+.13,-4.5,3.5),(face_x+.13,4.5,3.5),(face_x+.13,0,7.0)]
    mesh('Gable',verts,[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],plaster)
    beam((face_x,0,3.5),(face_x,0,6.9),.22,.22)
    beam((face_x,-4.5,3.55),(face_x,0,7.0),.20,.20)
    beam((face_x,0,7.0),(face_x,4.5,3.55),.20,.20)
for x in [-7.5,-3,1.5,7.5]:
    if abs(x-door_x)<1.8:continue
    for y in [-4.72,4.72]:
        # Shuttered windows avoid a bright black painted square on the house wall.
        box((x,y,2.28),(1.15,.11,1.25),iron,.01)
        for dx in [-.61,.61]:box((x+dx,y-.06,2.28),(.11,.18,1.40),oak,.01)
        for z in [1.61,2.95]:box((x,y-.06,z),(1.35,.22,.12),oak,.01)
        box((x,y-.07,2.28),(.055,.09,1.2),oak,.005)
        box((x,y-.07,2.28),(1.2,.09,.055),oak,.005)
        for side in [-1,1]:
            for dx in range(3):box((x+side*(.80+dx*.14),y,2.28),(.13,.08,1.17),oak,.006)
# Open door, not a wall-sized single convex hull. No decorative leaf blocks the trigger.
for x in [door_x-.85,door_x+.85]:box((x,-4.57,1.26),(.20,.45,2.52),oak,.018)
box((door_x,-4.57,2.62),(1.92,.45,.22),oak,.018)
box((door_x,-4.5,3.13),(1.55,.25,.80),plaster,.012)
roof_panel(-5.0,3.50,0,7.25);roof_panel(0,7.25,5,3.50)
# Layered, modeled thatch courses and individual stalk bundles follow both roof slopes.
for side in [-1,1]:
    for row in range(18):
        t=(row+.5)/18;y=side*(5-t*5);z=3.5+t*3.75+.06
        for col in range(86):
            x=-9.25+col*.215+(.09 if row%2 else 0)+random.uniform(-.04,.04)
            a=(x,y-side*.32,z+.23);b=(x,y+side*.36,z-.27+random.uniform(-.025,.025))
            # Low-sided reed bundles give glancing-light relief without a texture-only roof.
            tapered_branch(a,b,.10,.09,thatch,5)
for x in np.arange(-9.2,9.3,.28):
    box((float(x),0,7.25),(.30,.55,.22),thatch,.03)
    beam((float(x),-.45,7.0),(float(x),.45,7.0),.035,.035,oak)
# Stone chimney, pot and smoke-blackened throat, kept entirely within the cottage footprint.
for course in range(12):
    for col in range(3):
        box((-5.8+col*.38,1.9,4.55+course*.27),(.36,.9,.25),stone,.025)
box((-5.4,1.9,7.78),(1.42,1.13,.22),stone,.025)
box((-5.4,1.9,7.90),(.75,.55,.06),iron,.01)
finish([((0,4.5,1.75),(18,.5,3.5)),((-9,0,1.75),(.5,9,3.5)),((9,0,1.75),(.5,9,3.5)),
        (((-9+door_x-.75)/2,-4.5,1.75),(door_x-.75+9,.5,3.5)),(((door_x+.75+9)/2,-4.5,1.75),(9-door_x-.75,.5,3.5)),
        ((door_x,-4.5,3.0),(1.5,.5,1.0))])

start('SM_Fence_SplitRail_4m_01','prop_large')
for x in [-2,0,2]:
    box((x,0,.70),(.16,.18,1.4),oak,.022)
    # Flat bevels and a raised end grain cap keep the fence silhouette hand hewn.
    box((x,0,1.40),(.18,.19,.08),oak,.02)
for z in [.47,.98]:
    beam((-2,0,z),(0,0,z+.025),.13,.12)
    beam((0,0,z+.025),(2,0,z-.015),.13,.12)
finish([((0,0,.7),(4.2,.22,1.4))])

start('SM_Boulder_Fieldstone_01','prop')
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4,radius=1)
ob=bpy.context.object
for v in ob.data.vertices:
    r=1+.10*math.sin(v.co.x*13+v.co.y*7)*math.sin(v.co.z*11)
    v.co.x*=1.0*r;v.co.y*=.78*r;v.co.z=max(-.40,v.co.z*.72*r)
ob.location=(0,0,.40);add(ob,stone)
for p in ob.data.polygons:p.use_smooth=True
finish([((0,0,.49),(1.9,1.45,.98))])

start('SM_Oak_Stonebrook_01','foliage')
# A continuous irregular trunk and branching crown, not crossed sprite planes.
trunk=[(0,0,0),(.15,.05,1.3),(.05,.08,2.8),(.28,.02,4.1),(.4,-.1,5.5),(.55,-.05,6.4)]
for i in range(len(trunk)-1):tapered_branch(trunk[i],trunk[i+1],.46-i*.065,.40-i*.065,oak,16)
for i in range(7):
    a=i*math.tau/7;tapered_branch((.1,0,.55),(math.cos(a)*1.1,math.sin(a)*.95,0),.22,.07,oak,10)
crowns=[]
for i in range(11):
    angle=i*math.tau/11; z=4.8+random.uniform(-.5,1.7)
    reach=random.uniform(2.3,3.4)
    end=Vector((math.cos(angle)*reach,math.sin(angle)*reach,z+1.1))
    origin=Vector(trunk[2+i%3]);joint=(origin+end)*.5+Vector((0,0,.25))
    tapered_branch(origin,joint,.20,.115,oak,12);tapered_branch(joint,end,.115,.035,oak,10)
    crowns.append(end)
    for j in range(3):
        a=angle+(j-1)*.7;tip=end+Vector((math.cos(a)*.75,math.sin(a)*.75,random.uniform(.1,.8)))
        tapered_branch(joint,tip,.08,.018,oak,8)
        crowns.append(tip)
verts=[];faces=[]
for center in crowns:
    for i in range(95):
        # Distribute separate cupped leaves through the volume, with varied orientation.
        delta=Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(-.65,.8)))
        if delta.length>1:delta.normalize()
        pos=center+delta*random.uniform(.3,1.25)
        length=random.uniform(.15,.26);width=length*.40
        local=[Vector((0,-length/2,0)),Vector((-width,0,-.012)),Vector((0,length/2,0)),Vector((width,0,-.012)),Vector((0,0,.025))]
        rot=Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(.15,1))).to_track_quat('Z','Y').to_matrix()
        n=len(verts);verts.extend(tuple(pos+rot@v) for v in local)
        faces.extend([(n,n+1,n+4),(n+1,n+2,n+4),(n+2,n+3,n+4),(n+3,n,n+4)])
mesh('CuppedOakLeaves',verts,faces,leaf)
finish([((0,0,2.5),(.85,.85,5.0))])

start('SM_Grass_Meadow_01','foliage')
verts=[];faces=[]
for i in range(170):
    a=random.random()*math.tau;r=random.random()**.5*.45
    pos=Vector((math.cos(a)*r,math.sin(a)*r,0));h=random.uniform(.16,.55);w=random.uniform(.012,.035)
    lean=Vector((random.uniform(-.2,.2),random.uniform(-.2,.2),h))
    cross=Vector((math.cos(a)*w,math.sin(a)*w,0));n=len(verts)
    verts.extend([tuple(pos-cross),tuple(pos+cross),tuple(pos+lean*.65+cross*.4),tuple(pos+lean*.65-cross*.4),tuple(pos+lean)])
    faces.extend([(n,n+1,n+2,n+3),(n+3,n+2,n+4)])
mesh('GrassBlades',verts,faces,leaf)
finish([])

start('SM_Ground_Meadow_20m_01','building')
box((0,0,.05),(20,20,.10),meadow,0)
ground=finish([((0,0,.05),(20,20,.10))])
for uv in ground.data.uv_layers.active.data:uv.uv*=8

start('SM_Path_Earth_8m_01','kit_floor')
# Opaque, irregular edged path patches sit just above the meadow, with real earthy roughness.
verts=[];faces=[]
for z in [0,-.025]:
    for i in range(17):
        x=i*.5
        left=0 if i in [0,16] else random.uniform(.02,.17)
        right=2 if i in [0,16] else random.uniform(1.83,1.98)
        verts.extend([(x,left,z),(x,right,z)])
for i in range(16):
    a=i*2;b=a+2;faces.append((a,b,b+1,a+1));faces.append((a+34,a+35,b+35,b+34))
    faces.append((a,a+34,b+34,b));faces.append((a+1,b+1,b+35,a+35))
faces.extend([(0,1,35,34),(32,66,67,33)])
mesh('OrganicDirtPath',verts,faces,dirt)
finish([((4,1,-.05),(8,2,.1))])

# Build conventional foliage LOD chains while preserving all source meshes and collision.
normal_repairs=[]
for asset in common.find_assets():
    if asset.cls_name=='foliage':
        make_lods.make_lods(asset,[.5,.25]);asset.refresh()
        sys.path.insert(0,str(Path(__file__).parent))
        from repair_foliage_normals import repair_collapsed_components
        for render in asset.renders:normal_repairs.append(repair_collapsed_components(render))
        bounds=[common.world_bounds(o) for o in asset.renders]
        mn=Vector(tuple(min(b[0][i] for b in bounds) for i in range(3)))
        mx=Vector(tuple(max(b[1][i] for b in bounds) for i in range(3)))
        ASSETS[asset.name]['lod_union_dimensions_m']=list(mx-mn)

(ART/'foliage_normal_repair.json').write_text(json.dumps({'passed':True,'meshes':normal_repairs},indent=2)+'\n')

manifest={'schema':'dink-stonebrook-art/1','units':'metres; FBX UnitScaleFactor100 converts to Unreal cm','seed':439,
          'source':'KIT_StonebrookExterior.blend','assets':ASSETS,'materials':MATERIALS,
          'cottage_door_local_cm':[530,450,0],
          'notes':['First local exterior art candidate. No changes to original screenplay or quest facts.',
                   'Ground module bottom at0/top10cm: exterior_layout places at height_cm=-9.8, yielding top0.2cm.',
                   'Tree and grass use true modeled leaves/blades and three LOD levels; enable two-sided leaf material in Unreal.',
                   'Cottage front faces +Y in UE. Door opening localX530,Y450cm aligns source339,294 when cottagecenter285,248.5.']}
(ART/'exterior_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
layout={'schema':'dink-art/1','screen':439,'hide_screen_visuals':[439],'hide_origins':[],
        'authored_collision_screens':[439],'replacements':[],'elements':[],'lights':[]}
def element(name,mesh,px,py,z=0,yaw=0,scale=(1,1,1)):
    collision_enabled=not ('Grass' in mesh or 'Path' in mesh)
    layout['elements'].append({'name':name,'mesh':mesh,'source_pixel':[px,py],'height_cm':z,'rotation_deg':[0,yaw,0],'scale':list(scale),'collision':collision_enabled})
screen=next(s for s in json.loads((ROOT/'ImportData/screens.json').read_text())['screens'] if s['screen']==439)
corners=screen['corners'];nw,ne,sw,se=[corners[k] for k in ['nw','ne','sw','se']]
def world_point(px,py):
    u,v=px/600,py/400
    return np.array([nw[i]*(1-u)*(1-v)+ne[i]*u*(1-v)+sw[i]*(1-u)*v+se[i]*u*v for i in range(2)])
def pixel_for_world(point):
    pixel=np.array([300.,200.])
    for _ in range(8):
        value=world_point(*pixel)
        jac=np.column_stack((world_point(pixel[0]+1,pixel[1])-value,world_point(pixel[0],pixel[1]+1)-value))
        pixel-=np.linalg.solve(jac,value-point)
    return pixel.tolist()
minimum=[min(corners[k][i] for k in corners)-.02 for i in range(2)]
maximum=[max(corners[k][i] for k in corners)+.02 for i in range(2)]
tile_width=(maximum[0]-minimum[0])/3;tile_depth=(maximum[1]-minimum[1])/2
# Axis-aligned adjoining tiles cover the screen's full world AABB, including skewed corners.
for row in range(2):
    for col in range(3):
        px,py=pixel_for_world(np.array([minimum[0]+(col+.5)*tile_width,minimum[1]+(row+.5)*tile_depth]))
        element('Meadow_%d_%d'%(col,row),'SM_Ground_Meadow_20m_01',px,py,z=-9.8,scale=(tile_width/20,tile_depth/20,1))
element('DinksCottage','SM_Cottage_Stonebrook_01',285,248.5)
for i in range(2):element('DirtPath%d'%i,'SM_Path_Earth_8m_01',329,294+i*80.8,z=.4,yaw=90)
for i in [7,14,20,35,13,47,48,49,50,54]:layout['hide_origins'].append('S439_P%02d'%i)
for origin,mesh,px,py,yaw in [('S439_P06','SM_Barrel_Oak_01',52,247,0),('S439_P22','SM_Barrel_Oak_01',104,355,0),('S439_P45','SM_FeedSack_Jute_01',162,318,0)]:
    layout['replacements'].append({'origin':origin,'mesh':mesh,'source_pixel':[px,py],'rotation_deg':[0,yaw,0],'scale':[1,1,1]})
# Replace the oversized fence sprite chain with measured4m rails covering its original route.
for p in [1,2,10,12,15,16,17,18,19,39]:layout['hide_origins'].append('S439_P%02d'%p)
for i in range(7):element('FenceWest%d'%i,'SM_Fence_SplitRail_4m_01',24,24+i*40.5,yaw=90)
element('FenceWestCorner','SM_Fence_SplitRail_4m_01',51,286,yaw=35)
for i in range(2):element('FenceGarden%d'%i,'SM_Fence_SplitRail_4m_01',78,305+i*40.5,yaw=90)
for i in range(13):
    if i==6:continue  # 3D adaptation: a real4m farm gateway aligned with the dirt path.
    element('FenceSouth%d'%i,'SM_Fence_SplitRail_4m_01',100+i*40.5,366)
for p in [3,4,8,40,41,42,43,44,51,52]:layout['hide_origins'].append('S439_P%02d'%p)
for name,px,py,scale in [('OakWest',110,190,1),('OakEast',510,125,1.1),('OakNorth',180,45,.9)]:element(name,'SM_Oak_Stonebrook_01',px,py,scale=(scale,scale,scale))
for i,(px,py) in enumerate([(100,160),(520,180),(480,60),(145,355),(430,335)]):element('Boulder%d'%i,'SM_Boulder_Fieldstone_01',px,py,yaw=i*71,scale=(1,1,1))
for i in range(95):
    px=random.uniform(50,590);py=random.uniform(10,390)
    # Keep the house and its return path clear; accents are visual, not new barriers.
    if 185<px<385 and 190<py<296:continue
    if 320<px<360 and py>285:continue
    k=random.uniform(.65,1.25);element('Grass%03d'%i,'SM_Grass_Meadow_01',px,py,yaw=random.uniform(0,360),scale=(k,k,k))
(ART/'exterior_layout.json').write_text(json.dumps(layout,indent=2)+'\n')

# Preview the cottage with trees, fence and ground under natural afternoon light.
preview=bpy.data.collections.new('Preview_Stage');scene.collection.children.link(preview)
positions={'SM_Cottage_Stonebrook_01':(0,0,0),'SM_Fence_SplitRail_4m_01':(7,-8,0),
           'SM_Boulder_Fieldstone_01':(-7,-7,0),'SM_Oak_Stonebrook_01':(-13,1,0),
           'SM_Grass_Meadow_01':(-6,-6,0),'SM_Ground_Meadow_20m_01':(0,0,-.10),'SM_Path_Earth_8m_01':(-2,-9,.003)}
for name,pos in positions.items():
    for child in bpy.data.collections[name].objects:child.location+=Vector(pos)
for name in ['SM_Oak_Stonebrook_01','SM_Grass_Meadow_01']:
    for ob in bpy.data.collections[name].objects:
        if '_LOD1' in ob.name or '_LOD2' in ob.name:ob.hide_render=True
sun=bpy.data.lights.new('AfternoonSun','SUN');sun.energy=2.8;sun.angle=.12
sunob=bpy.data.objects.new('AfternoonSun',sun);preview.objects.link(sunob);sunob.rotation_euler=(.6,-.4,-.7)
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.55,.68,.85,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
ld=bpy.data.lights.new('SkyBounce','AREA');ld.energy=3500;ld.shape='DISK';ld.size=15;ld.color=(.7,.82,1)
lo=bpy.data.objects.new('SkyBounce',ld);preview.objects.link(lo);lo.location=(0,-6,12)
camera=bpy.data.cameras.new('Preview_Camera');cam=bpy.data.objects.new('Preview_Camera',camera);preview.objects.link(cam)
cam.location=(25,-32,14);cam.rotation_euler=(Vector((-1,0,3))-cam.location).to_track_quat('-Z','Y').to_euler();camera.lens=40;scene.camera=cam
scene.render.filepath=str(ART/'preview_exterior.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'KIT_StonebrookExterior.blend'))
bpy.ops.render.render(write_still=True)
print('STONEBROOK EXTERIOR: built',len(ASSETS),'assets')

# Runtime requires separate files: FBX siblings are not an Unreal LODGroup.
import runpy
runpy.run_path(str(Path(__file__).parent/'export_foliage_lods.py'),run_name='__main__')
