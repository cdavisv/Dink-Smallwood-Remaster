"""Build the dink's original outfit over the CC0 anatomical MakeHuman body.
Run after create_dink_base.py. The reference mannequin mesh is never delivered.
"""
import bpy,bmesh,math,json,random,sys,shutil
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(Path(__file__).resolve().parents[4])
ART=ROOT/'SourceAssets/Art/Characters/Dink';ART.mkdir(exist_ok=True);TEX=ART/'Textures';TEX.mkdir(parents=True,exist_ok=True)
DATA=ART.parent/'ThirdParty/MakeHuman'
bpy.ops.wm.open_mainfile(filepath='/tmp/dink-art/dink_base.blend')
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
random.seed(1997);rng=np.random.default_rng(1997)
body=bpy.data.objects['Dink_AnatomicalBody']
parts={'Eyes':bpy.data.objects['Human.low-poly'],'Hair':bpy.data.objects['Human.short02'],
       'Eyebrows':bpy.data.objects['Human.eyebrow001'],'Eyelashes':bpy.data.objects['Human.eyelashes01']}
with bpy.data.libraries.load('/tmp/dink-character-reference/Manny_Reference.blend',link=False) as (a,b):
    b.objects=[n for n in a.objects if n in ['Armature','SKM_Manny_Simple.001']]
reference=[]
for ob in b.objects:
    if ob:scene.collection.objects.link(ob);reference.append(ob)
arm=next(o for o in reference if o.type=='ARMATURE');ref=next(o for o in reference if o.type=='MESH')
arm.name='Armature';ref.name='Reference_Manny'
ref.hide_render=True;arm.hide_render=True
landmarks=json.loads(Path('/tmp/dink-art/dink_landmarks.json').read_text())
height=max(v.co.z for v in body.data.vertices)-min(v.co.z for v in body.data.vertices)
scale=1.80545/height
controls=[];targets=[]
mapping={'joint-pelvis':'pelvis','joint-neck':'neck_01','joint-head':'head'}
for side in ['l','r']:
    mapping.update({f'joint-{side}-clavicle':f'clavicle_{side}',f'joint-{side}-shoulder':f'upperarm_{side}',
                    f'joint-{side}-elbow':f'lowerarm_{side}',f'joint-{side}-hand':f'hand_{side}',
                    f'joint-{side}-upper-leg':f'thigh_{side}',f'joint-{side}-knee':f'calf_{side}',
                    f'joint-{side}-ankle':f'foot_{side}',f'joint-{side}-foot-1':f'ball_{side}'})
for source,target in mapping.items():
    controls.append(np.array(landmarks[source])*scale)
    targets.append(np.array(arm.matrix_world@arm.data.bones[target].head_local))
controls=np.array(controls);delta=np.array(targets)-controls
def fit(coords):
    points=np.array(coords)*scale
    distances=np.sum((points[:,None,:]-controls[None,:,:])**2,axis=2)
    weights=1/(distances+.0025)**2
    return points+(weights@delta)/weights.sum(axis=1)[:,None]
for ob in [body,*parts.values()]:
    old=ob.matrix_world.copy();co=[tuple(old@v.co) for v in ob.data.vertices]
    new=fit(co);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
    for v,p in zip(ob.data.vertices,new):v.co=p
    ob.data.update()
body_surface=BVHTree.FromPolygons([v.co.copy() for v in body.data.vertices],[list(p.vertices) for p in body.data.polygons],all_triangles=False)

MATERIALS={}
def texture_material(name,imagepath,roughness=.5,masked=False,normal_path=None,orm_path=None):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=roughness
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    image=bpy.data.images.load(str(imagepath),check_existing=True)
    tex=nodes.new('ShaderNodeTexImage');tex.image=image;links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    if masked:
        links.new(tex.outputs['Alpha'],bs.inputs['Alpha']);mat.surface_render_method='DITHERED';mat.use_transparency_overlap=False
    if normal_path:
        im=bpy.data.images.load(str(normal_path),check_existing=True);im.colorspace_settings.name='Non-Color'
        t=nodes.new('ShaderNodeTexImage');t.image=im;n=nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.6
        links.new(t.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],bs.inputs['Normal'])
    if orm_path:
        im=bpy.data.images.load(str(orm_path),check_existing=True);im.colorspace_settings.name='Non-Color'
        t=nodes.new('ShaderNodeTexImage');t.image=im;sep=nodes.new('ShaderNodeSeparateColor');links.new(t.outputs['Color'],sep.inputs[0]);links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    MATERIALS[name]={'base_color':[.5,.5,.5],'roughness':roughness,'metallic':0,'masked':masked,'two_sided':masked,
                     'textures':{'BC':str(Path('Textures')/imagepath.name)},'normal_strength':.32,'normal_flip_green':True}
    if normal_path:MATERIALS[name]['textures']['N']='Textures/'+normal_path.name
    if orm_path:MATERIALS[name]['textures']['ORM']='Textures/'+orm_path.name
    return mat
for source,dest in [(DATA/'skins/young_caucasian_male/young_lightskinned_male_diffuse.png','T_Dink_Skin_BC.png'),
                    (DATA/'eyes/materials/brown_eye.png','T_Dink_Eyes_BC.png'),
                    (DATA/'hair/short02/short02_diffuse.png','T_Dink_Hair_BC.png')]:shutil.copyfile(source,TEX/dest)
skin=texture_material('MI_Dink_Skin',TEX/'T_Dink_Skin_BC.png',.49)
skin.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value=.08
MATERIALS[skin.name]['subsurface']=.08
eyes=texture_material('MI_Dink_Eyes',TEX/'T_Dink_Eyes_BC.png',.18)
hair=texture_material('MI_Dink_Hair',TEX/'T_Dink_Hair_BC.png',.66,True)

# One wardrobe atlas keeps dress, apron and footwear within the five-slot NPC budget.
n=2048;half=n//2;atlas=np.ones((n,n,4),dtype=np.float32);normal=np.ones_like(atlas);normal[:,:,:3]=(.5,.5,1);orm=np.ones_like(atlas)
for index,(low,high,rough) in enumerate([((.22,.045,.025),(.48,.15,.082),.86),((.23,.17,.095),(.53,.42,.26),.91),((.035,.020,.010),(.14,.08,.04),.72),((.12,.13,.14),(.28,.29,.30),.44)]):
    yy,xx=np.mgrid[:half,:half]/half
    coarse=.5+.17*np.sin(xx*17+np.sin(yy*9))*np.sin(yy*19+.3)+.06*np.sin(xx*111)*np.sin(yy*95)
    weave=.015*np.sin(xx*math.pi*740)*np.sin(yy*math.pi*740)
    field=.55+.12*coarse+.04*rng.random((half,half))+weave
    color=np.array(low)[None,None,:]+field[:,:,None]*(np.array(high)-np.array(low))[None,None,:]
    x=(index%2)*half;y=(index//2)*half;atlas[y:y+half,x:x+half,:3]=color
    orm[y:y+half,x:x+half,0]=1;orm[y:y+half,x:x+half,1]=rough;orm[y:y+half,x:x+half,2]=1 if index==3 else 0
    h=field;dx,dy=np.gradient(h);norm=np.dstack((-dy*2,-dx*2,np.ones_like(h)));norm/=np.linalg.norm(norm,axis=2)[:,:,None]
    normal[y:y+half,x:x+half,:3]=norm*.5+.5
def save_image(name,pixels,linear=False):
    im=bpy.data.images.new(name,width=pixels.shape[1],height=pixels.shape[0],alpha=True)
    im.colorspace_settings.name='Non-Color' if linear else 'sRGB';im.pixels.foreach_set(pixels.ravel())
    im.filepath_raw=str(TEX/(name+'.png'));im.file_format='PNG';im.save();return im
save_image('T_Dink_Wardrobe_BC',atlas);save_image('T_Dink_Wardrobe_N',normal,True);save_image('T_Dink_Wardrobe_ORM',orm,True)
cloth=texture_material('MI_Dink_Wardrobe',TEX/'T_Dink_Wardrobe_BC.png',.86,False,TEX/'T_Dink_Wardrobe_N.png',TEX/'T_Dink_Wardrobe_ORM.png')

# Atlas the two alpha details instead of adding a material per brow/lash asset.
brow_atlas=np.zeros((1024,1024,4),dtype=np.float32)
for part,index in [('Eyebrows',0),('Eyelashes',1)]:
    path=DATA/('eyebrows/eyebrow001/eyebrow001.png' if part=='Eyebrows' else 'eyelashes/eyelashes01/eyelashes01.png')
    im=bpy.data.images.load(str(path));im.scale(512,1024);pix=np.array(im.pixels[:],dtype=np.float32).reshape(1024,512,4)
    brow_atlas[:,index*512:(index+1)*512]=pix
    for uv in parts[part].data.uv_layers.active.data:uv.uv.x=uv.uv.x*.5+index*.5
save_image('T_Dink_BrowLash_BC',brow_atlas)
brows=texture_material('MI_Dink_BrowLash',TEX/'T_Dink_BrowLash_BC.png',.65,True)
for ob,mat in [(body,skin),(parts['Eyes'],eyes),(parts['Hair'],hair),(parts['Eyebrows'],brows),(parts['Eyelashes'],brows)]:
    ob.data.materials.clear();ob.data.materials.append(mat)

garments=[]
def garment(name,verts,faces,region=0,uvs=None,solid=.003):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);me.materials.append(cloth)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    if uvs is None:
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
    else:
        layer=me.uv_layers.new(name='UVMap')
        for p in me.polygons:
            for loop in p.loop_indices:layer.data[loop].uv=uvs[me.loops[loop].vertex_index]
    for uv in me.uv_layers.active.data:uv.uv=uv.uv*.48+Vector(((region%2)*.5+.01,(region//2)*.5+.01))
    for p in me.polygons:p.use_smooth=True
    if solid:
        mod=ob.modifiers.new('Tailored cloth thickness','SOLIDIFY');mod.thickness=solid;mod.offset=0;bpy.ops.object.modifier_apply(modifier=mod.name)
    garments.append(ob);return ob
def distance_segment(p,a,b):
    a=np.array(a);b=np.array(b);p=np.array(p);t=np.clip(np.dot(p-a,b-a)/np.dot(b-a,b-a),0,1)
    return np.linalg.norm(p-(a+t*(b-a))),t
def covered_top(p):
    x,y,z=p
    if .96<z<1.59 and abs(x)<.28:return True
    for side in ['l','r']:
        a=arm.matrix_world@arm.data.bones['upperarm_'+side].head_local;b=arm.matrix_world@arm.data.bones['lowerarm_'+side].head_local;c=arm.matrix_world@arm.data.bones['hand_'+side].head_local
        d,t=distance_segment(p,a,b)
        if d<.10:return True
        d,t=distance_segment(p,b,c)
        if d<.085 and t<.84:return True
    return False
top_faces=[];shoe_faces=[];pants_faces=[];hide=set()
for p in body.data.polygons:
    center=sum((body.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
    if covered_top(center):
        top_faces.append(list(p.vertices))
        neck_underlay = abs(center.x)<.115 and center.z>1.42 and any(body.data.vertices[i].co.z>1.47 for i in p.vertices)
        if center.z<1.51 and not neck_underlay:hide.add(p.index)
    if .14<center.z<1.04 and abs(center.x)<.36:pants_faces.append(list(p.vertices));hide.add(p.index)
    if center.z<.23:shoe_faces.append(list(p.vertices));hide.add(p.index)
    if center.z<1.02 and abs(center.x)<.35:hide.add(p.index)
coords=[tuple(v.co+v.normal*.012) for v in body.data.vertices]
def subset(name,faces,region,offset=0):
    used=sorted({i for f in faces for i in f});lookup={old:new for new,old in enumerate(used)}
    verts=[coords[i] for i in used]
    return garment(name,verts,[[lookup[i] for i in f] for f in faces],region)
coat=subset('Rust red linen shirt and sleeves',top_faces,0)
bpy.context.view_layer.objects.active=coat
smooth=coat.modifiers.new('Soft woven bodice drape','SMOOTH');smooth.factor=.65;smooth.iterations=24
bpy.ops.object.modifier_apply(modifier=smooth.name)
for vertex in coat.data.vertices:
    p=vertex.co
    if abs(p.x)<.23 and 1.06<p.z<1.47:
        t=math.sin((p.z-1.06)/.41*math.pi)
        p.y+=(-1 if p.y<-.02 else 1)*.022*t
        if p.y<-.04:p.y-=.004*t*math.sin(p.x*65+p.z*7)
        p.x+=.006*t*math.tanh(p.x/.08)
dec=coat.modifiers.new('Cloth game topology','DECIMATE');dec.ratio=.5
bpy.ops.object.modifier_apply(modifier=dec.name)
# Cut the real neck surface at one plane rather than approximating it with a floating collar.
bm=bmesh.new();bm.from_mesh(coat.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,1.52),plane_no=(0,0,1),clear_outer=True,dist=1e-6)
bm.faces.ensure_lookup_table()
slit=[f for f in bm.faces if f.calc_center_median().y<-.025 and 1.45<f.calc_center_median().z<1.53 and abs(f.calc_center_median().x)<.026*(f.calc_center_median().z-1.45)/.08]
if slit:bmesh.ops.delete(bm,geom=slit,context='FACES_ONLY')
bm.to_mesh(coat.data);bm.free();coat.data.update()
# Smoothing must not shrink shoulder cloth inside the retained neckline skin.
for vertex in coat.data.vertices:
    if vertex.co.z>1.42 and abs(vertex.co.x)<.145:
        hit=body_surface.find_nearest(vertex.co)
        if hit[0] is not None and (vertex.co-hit[0]).dot(hit[1])<.018:
            vertex.co=hit[0]+hit[1]*.018
coat.data.update()
# Closed, hand-built leather shoes avoid individual-toe "foot glove" silhouettes.
for side in [-1,1]:
    cx=side*.145;verts=[];faces=[];sections=12
    stations=[(.075,.044,.022,.10),(.025,.062,.015,.17),(-.055,.066,.015,.115),(-.145,.064,.015,.085),(-.22,.035,.022,.065)]
    for y,width,bottom,top in stations:
        for k in range(sections):
            a=k*math.tau/sections;verts.append((cx+width*math.cos(a),y,(bottom+top)/2+(top-bottom)/2*math.sin(a)-.015))
    for j in range(len(stations)-1):
        for k in range(sections):a=j*sections+k;b=j*sections+(k+1)%sections;faces.append((a,b,b+sections,a+sections))
    faces.append(tuple(reversed(range(sections))));faces.append(tuple((len(stations)-1)*sections+k for k in range(sections)))
    garment('Worn leather shoe',verts,faces,2,solid=0)

# Separate trouser legs follow anatomical topology and preserve the crotch for walking.
pants=subset('Tan wool trousers',pants_faces,1)
bpy.context.view_layer.objects.active=pants
smooth=pants.modifiers.new('Soft trouser drape','SMOOTH');smooth.factor=.6;smooth.iterations=6
bpy.ops.object.modifier_apply(modifier=smooth.name)
dec=pants.modifiers.new('Trouser game topology','DECIMATE');dec.ratio=.55
bpy.ops.object.modifier_apply(modifier=dec.name)
# Conforming leather belt and a physically modeled small iron buckle.
verts=[];faces=[];segments=64
for i in range(segments+1):
    angle=math.tau*i/segments;direction=Vector((math.cos(angle),math.sin(angle),0))
    for z in [1.005,1.045]:
        hit=body_surface.ray_cast(Vector((0,-.02,z)),direction,1)
        if hit[0] is None:raise RuntimeError('Belt surface ray missed')
        verts.append(tuple(hit[0]+hit[1]*.018))
for i in range(segments):a=i*2;faces.append((a,a+1,a+3,a+2))
garment('Worn leather belt',verts,faces,2,solid=.004)
# Leather boot shafts grow out of each shoe rather than exposing bare ankles.
for side in [-1,1]:
    cx=side*.145;verts=[];faces=[];rings=9;segments=24
    for j in range(rings):
        z=.09+j/(rings-1)*.23
        for i in range(segments):
            angle=math.tau*i/segments
            radiusx=.063+.007*math.sin(j/(rings-1)*math.pi)
            radiusy=.070+.012*math.cos(j/(rings-1)*math.pi)
            verts.append((cx+radiusx*math.cos(angle),.005+radiusy*math.sin(angle),z+.003*math.sin(angle*5+j)))
    for j in range(rings-1):
        for i in range(segments):a=j*segments+i;b=j*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
    garment('Supple leather boot shaft',verts,faces,2)

# Close every open cut-neck edge with a sewn binding down to the real skin surface.
# This joins the neckline physically instead of hiding a void with another floating collar.
bm=bmesh.new();bm.from_mesh(coat.data);verts=[];faces=[]
for edge in bm.edges:
    if not edge.is_boundary or min(v.co.z for v in edge.verts)<1.46 or max(abs(v.co.x) for v in edge.verts)>.20:continue
    a,b=[v.co.copy() for v in edge.verts];inner=[]
    for point in [a,b]:
        hit=body_surface.find_nearest(point)
        inner.append(hit[0]+hit[1]*.001 if hit[0] is not None else point)
    if (a-inner[0]).length<.002 and (b-inner[1]).length<.002:continue
    offset=len(verts);verts.extend([tuple(a),tuple(b),tuple(inner[1]),tuple(inner[0])]);faces.append(tuple(offset+i for i in range(4)))
bm.free()
if faces:garment('Sewn continuous neckline binding',verts,faces,1,solid=0)

# Sewn placket edges and rolled cuffs break the smooth modern-shirt silhouette.
def surface_front(x,z,clearance=.037):
    hit=body_surface.ray_cast(Vector((x,-.7,z)),Vector((0,1,0)),1.4)
    return hit[0].y-clearance if hit[0] else -.18
for side in [-1,1]:
    verts=[];faces=[]
    for row in range(13):
        t=row/12;z=1.405+t*.115;x=side*(.012+.020*max(0,(z-1.45)/.07))
        for shift in [-.006,.006]:
            xx=x+shift;verts.append((xx,surface_front(xx,z),z))
    for row in range(12):a=row*2;faces.append((a,a+1,a+3,a+2))
    garment('Shirt stitched split placket edging',verts,faces,1,solid=.002)
for side in ['l','r']:
    wrist=arm.matrix_world@arm.data.bones['hand_'+side].head_local
    elbow=arm.matrix_world@arm.data.bones['lowerarm_'+side].head_local
    direction=(wrist-elbow).normalized();u=direction.cross(Vector((0,1,0))).normalized();v=direction.cross(u).normalized()
    verts=[];faces=[];segments=24
    for row in range(4):
        center=wrist-direction*(.035+row*.012)
        for i in range(segments):
            angle=i*math.tau/segments;radius=.039+.002*math.sin(row/3*math.pi)
            point=center+(u*math.cos(angle)+v*math.sin(angle))*radius
            hit=body_surface.find_nearest(point)
            if hit[0] is not None:point=hit[0]+hit[1]*(.014+.001*math.sin(row/3*math.pi))
            verts.append(tuple(point))
    for row in range(3):
        for i in range(segments):a=row*segments+i;b=row*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
    garment('Turned woven wrist cuff',verts,faces,0,solid=.003)
# An iron frame and pin are geometry, sharing the iron quadrant of the wardrobe atlas.
def box_detail(name,center,size,region):
    c=Vector(center);h=Vector(size)*.5
    verts=[tuple(c+Vector((x*h.x,y*h.y,z*h.z))) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return garment(name,verts,faces,region,solid=0)
hit=body_surface.ray_cast(Vector((0,-.7,1.025)),Vector((0,1,0)),1.4)
buckle_y=hit[0].y-.039
for x in [-.030,.030]:box_detail('Iron belt buckle side',(x,buckle_y,1.025),(.008,.009,.050),3)
for z in [1.004,1.046]:box_detail('Iron belt buckle crossbar',(0,buckle_y,z),(.062,.009,.008),3)
box_detail('Iron belt buckle tongue',(0,buckle_y-.004,1.025),(.050,.006,.005),3)
# Narrow seam welts track each boot shaft; restrained modeled ridges, not painted stripes.
for side in [-1,1]:
    cx=side*.145;verts=[];faces=[];segments=8
    for row in range(12):
        t=row/11;z=.10+t*.21;radiusx=.063+.007*math.sin((z-.09)/.23*math.pi)
        for i in range(segments):
            angle=i*math.tau/segments
            verts.append((cx+side*(radiusx+.0015)+.0018*math.cos(angle),.006+.0018*math.sin(angle),z))
    for row in range(11):
        for i in range(segments):a=row*segments+i;b=row*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
    garment('Boot stitched side welt',verts,faces,2,solid=0)

# Retain only visible anatomical skin. Clothing replaces covered body geometry.
me=body.data;bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[bm.faces[i] for i in sorted(hide)],context='FACES')
loose=[v for v in bm.verts if not v.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bm.to_mesh(me);bm.free();me.update()
for ob in [body,*parts.values()]:
    for p in ob.data.polygons:p.use_smooth=True

# Source character consists of true anatomical skin, fitted hair/eyes and original clothes.
coll=bpy.data.collections.new('SK_Dink');scene.collection.children.link(coll)
coll['dink_class']='character_hero';coll['dink_path']='Stonebrook';coll['dink_source']='CC0 MakeHuman body/eyes/hair plus original red shirt, trousers and boots; see Provenance'
for ob in [body,*parts.values(),*garments,arm]:
    for c in list(ob.users_collection):c.objects.unlink(ob)
    coll.objects.link(ob)
ref.hide_set(True)
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1100;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.32,.37,.43,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
stage=bpy.data.collections.new('Preview_Stage');scene.collection.children.link(stage)
for pos,power,color,size in [((2,-3,3.5),350,(1,.84,.69),3),((-2,-1,2.2),210,(.65,.78,1),2),((0,2,3),280,(1,.75,.5),2)]:
    ld=bpy.data.lights.new('PortraitLight','AREA');ld.energy=power;ld.color=color;ld.shape='DISK';ld.size=size
    ob=bpy.data.objects.new('PortraitLight',ld);stage.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,0,1))-ob.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('PortraitCamera');cam=bpy.data.objects.new('PortraitCamera',camera);stage.objects.link(cam);cam.location=(2.3,-4.6,2.0);cam.rotation_euler=(Vector((0,0,1))-cam.location).to_track_quat('-Z','Y').to_euler();camera.lens=70;scene.camera=cam
scene.view_settings.view_transform='AgX';scene.render.filepath=str(ART/'preview_dink.png')
(ART/'dink_materials.json').write_text(json.dumps(MATERIALS,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'Dink_Working.blend'))
bpy.ops.render.render(write_still=True)
print('DINK ART:',len(body.data.polygons),'visible skin faces;',len(garments),'authored clothing meshes')
