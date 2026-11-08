"""Build the dink's original outfit over the CC0 anatomical MakeHuman body.
Run after create_dink_base.py. The reference mannequin mesh is never delivered.
"""
import bpy,bmesh,math,json,random,sys,shutil
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path('/home/artist/Repos/Dink-Smallwood/DinkRemasterUE')
ART=ROOT/'SourceAssets/Art/Characters/Milder';ART.mkdir(exist_ok=True);TEX=ART/'Textures';TEX.mkdir(parents=True,exist_ok=True)
DATA=ART.parent/'ThirdParty/MakeHuman'
bpy.ops.wm.open_mainfile(filepath='/tmp/dink-art/milder_base.blend')
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
random.seed(401);rng=np.random.default_rng(401)
body=bpy.data.objects['Milder_AnatomicalBody']
parts={'Eyes':bpy.data.objects['Human.low-poly'],'Hair':bpy.data.objects['Human.short04'],
       'Eyebrows':bpy.data.objects['Human.eyebrow001'],'Eyelashes':bpy.data.objects['Human.eyelashes01']}
with bpy.data.libraries.load('/tmp/dink-character-reference/Manny_Reference.blend',link=False) as (a,b):
    b.objects=[n for n in a.objects if n in ['Armature','SKM_Manny_Simple.001']]
reference=[]
for ob in b.objects:
    if ob:scene.collection.objects.link(ob);reference.append(ob)
arm=next(o for o in reference if o.type=='ARMATURE');ref=next(o for o in reference if o.type=='MESH')
arm.name='Armature';ref.name='Reference_Manny'
ref.hide_render=True;arm.hide_render=True
landmarks=json.loads(Path('/tmp/dink-art/milder_landmarks.json').read_text())
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
# Distinct adult proportions: broad face, mature macro phenotype and a slightly taller head silhouette.
for part in [body,*parts.values()]:
    for vertex in part.data.vertices:
        p=vertex.co
        if p.z>1.45:
            t=max(0,min(1,(p.z-1.45)/.35));t=t*t*(3-2*t);p.z+=.045*t
            p.x*=1+.075*t
            p.x*=1+.12*math.exp(-((p.z-1.665)/.085)**2)
    part.data.update()
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
for source,dest in [(DATA/'skins/young_caucasian_male/young_lightskinned_male_diffuse.png','T_Milder_Skin_BC.png'),
                    (DATA/'eyes/materials/brown_eye.png','T_Milder_Eyes_BC.png'),
                    (ART/'ThirdParty/MakeHuman/hair/short04/short04_diffuse.png','T_Milder_Hair_BC.png')]:shutil.copyfile(source,TEX/dest)
skin=texture_material('MI_Milder_Skin',TEX/'T_Milder_Skin_BC.png',.49)
skin.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value=.08
MATERIALS[skin.name]['subsurface']=.08
eyes=texture_material('MI_Milder_Eyes',TEX/'T_Milder_Eyes_BC.png',.18)
hair=texture_material('MI_Milder_Hair',TEX/'T_Milder_Hair_BC.png',.66,True)

# One wardrobe atlas keeps dress, apron and footwear within the five-slot NPC budget.
n=2048;half=n//2;atlas=np.ones((n,n,4),dtype=np.float32);normal=np.ones_like(atlas);normal[:,:,:3]=(.5,.5,1);orm=np.ones_like(atlas)
for index,(low,high,rough) in enumerate([((.022,.047,.085),(.09,.19,.32),.86),((.075,.070,.060),(.22,.21,.19),.91),((.035,.020,.010),(.14,.08,.04),.72),((.18,.20,.23),(.52,.57,.63),.39)]):
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
save_image('T_Milder_Wardrobe_BC',atlas);save_image('T_Milder_Wardrobe_N',normal,True);save_image('T_Milder_Wardrobe_ORM',orm,True)
cloth=texture_material('MI_Milder_Wardrobe',TEX/'T_Milder_Wardrobe_BC.png',.86,False,TEX/'T_Milder_Wardrobe_N.png',TEX/'T_Milder_Wardrobe_ORM.png')

# Atlas the two alpha details instead of adding a material per brow/lash asset.
brow_atlas=np.zeros((1024,1024,4),dtype=np.float32)
for part,index in [('Eyebrows',0),('Eyelashes',1)]:
    path=DATA/('eyebrows/eyebrow001/eyebrow001.png' if part=='Eyebrows' else 'eyelashes/eyelashes01/eyelashes01.png')
    im=bpy.data.images.load(str(path));im.scale(512,1024);pix=np.array(im.pixels[:],dtype=np.float32).reshape(1024,512,4)
    brow_atlas[:,index*512:(index+1)*512]=pix
    for uv in parts[part].data.uv_layers.active.data:uv.uv.x=uv.uv.x*.5+index*.5
save_image('T_Milder_BrowLash_BC',brow_atlas)
brows=texture_material('MI_Milder_BrowLash',TEX/'T_Milder_BrowLash_BC.png',.65,True)
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
        neck_underlay = center.z>1.39 and any(body.data.vertices[i].co.z>1.41 for i in p.vertices)
        if center.z<1.51 and not neck_underlay:hide.add(p.index)
    if .14<center.z<1.04 and abs(center.x)<.36:pants_faces.append(list(p.vertices));hide.add(p.index)
    if center.z<.23:shoe_faces.append(list(p.vertices));hide.add(p.index)
    if center.z<1.02 and abs(center.x)<.35:hide.add(p.index)
coords=[tuple(v.co+v.normal*.012) for v in body.data.vertices]
def subset(name,faces,region,offset=0):
    used=sorted({i for f in faces for i in f});lookup={old:new for new,old in enumerate(used)}
    verts=[coords[i] for i in used]
    return garment(name,verts,[[lookup[i] for i in f] for f in faces],region)
coat=subset('Blue padded gambeson and sleeves',top_faces,0)
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
dec=coat.modifiers.new('Cloth game topology','DECIMATE');dec.ratio=.4
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
dec=pants.modifiers.new('Trouser game topology','DECIMATE');dec.ratio=.45
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
if faces:garment('Sewn continuous neckline binding',verts,faces,0,solid=0)

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

# Original forged plate armor follows the real body surface, with modeled thickness and rim details.
# Smooth measured ellipse profiles avoid reproducing skin muscles/dents in forged steel.
profile_z=np.linspace(1.045,1.51,12);profile_rx=[];profile_ry=[];profile_cy=[]
for z in profile_z:
    hits=[]
    for direction in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0)]:
        hit=body_surface.ray_cast(Vector((0,-.02,float(z))),Vector(direction),1)
        if hit[0] is None:raise RuntimeError('Armor profile ray missed')
        hits.append(hit[0])
    profile_rx.append((hits[0].x-hits[1].x)/2+.026)
    profile_ry.append((hits[2].y-hits[3].y)/2+.033)
    profile_cy.append((hits[2].y+hits[3].y)/2)
fit_rx=np.polyfit(profile_z,profile_rx,3);fit_ry=np.polyfit(profile_z,profile_ry,3);fit_cy=np.polyfit(profile_z,profile_cy,3)
def torso_plate(name,angle_center,z_low,z_high,half_angle,rows=13,columns=25):
    verts=[];faces=[];uvs=[]
    for row in range(rows):
        t=row/(rows-1)
        for col in range(columns):
            u=col/(columns-1)*2-1;z=z_low+(z_high-z_low)*t-(.045 if z_high-z_low>.2 else 0)*(1-abs(u))*t**7
            angle=angle_center+u*half_angle
            rx=float(np.polyval(fit_rx,z));ry=float(np.polyval(fit_ry,z));cy=float(np.polyval(fit_cy,z))
            if z_high-z_low<.2:
                padding=.018-.1*(z_low-1.055);rx+=padding;ry+=padding
            verts.append((rx*math.cos(angle),cy+ry*math.sin(angle),z));uvs.append((col/(columns-1),t))
    for row in range(rows-1):
        for col in range(columns-1):a=row*columns+col;faces.append((a,a+1,a+1+columns,a+columns))
    plate=garment(name,verts,faces,3,uvs,solid=.005);plate['armor_rows']=rows;plate['armor_cols']=columns;return plate
front=torso_plate('Forged steel breastplate',-math.pi/2,1.11,1.50,1.17)
back=torso_plate('Shaped steel backplate',math.pi/2,1.12,1.49,1.17,11,21)
# Plate panels for pauldrons, vambraces, and greaves use true anatomical patches rather than boxes.
def curved_limb_plate(name,bone_a,bone_b,t0,t1,r0,r1,angle_extent=2.84,shoulder=False):
    a=arm.matrix_world@arm.data.bones[bone_a].head_local;b=arm.matrix_world@arm.data.bones[bone_b].head_local;axis=(b-a).normalized()
    u=Vector((0,-1,0));u=(u-axis*u.dot(axis)).normalized();v=u.cross(axis).normalized()
    if shoulder and v.z<0:v=-v
    rows=7;columns=25;verts=[];faces=[];uvs=[]
    for row in range(rows):
        t=row/(rows-1);center=a.lerp(b,t0+(t1-t0)*t);radius=r0*(1-t)+r1*t+.004*math.sin(math.pi*t)
        if shoulder:
            radius=.035+.100*math.sin(min(1,t/.55)*math.pi/2) if t<.55 else .135+(.105-.135)*(t-.55)/.45
        for col in range(columns):
            q=col/(columns-1)
            angle=(-.12+q*(math.pi+.24)) if shoulder else (-angle_extent+q*2*angle_extent)
            point=center+(u*math.cos(angle)+v*math.sin(angle))*radius
            verts.append(tuple(point));uvs.append((q,t))
    for row in range(rows-1):
        for col in range(columns-1):a0=row*columns+col;faces.append((a0,a0+1,a0+1+columns,a0+columns))
    return garment(name,verts,faces,3,uvs,solid=.005)
for side in ['l','r']:
    curved_limb_plate('Smooth forged shoulder pauldron','upperarm_'+side,'lowerarm_'+side,-.12,.42,.130,.110,shoulder=True)
    curved_limb_plate('Tapered steel vambrace','lowerarm_'+side,'hand_'+side,.12,.90,.085,.048)
    curved_limb_plate('Curved steel greave','calf_'+side,'foot_'+side,.08,.92,.087,.058,angle_extent=1.82)
# Three overlapping fauld lames carry plate to the belt without a rigid barrel around the hips.
for index in range(3):
    torso_plate('Overlapping steel waist lame',-math.pi/2,1.055+index*.039,1.105+index*.039,1.25,3,25)
# Rivet heads and edge rolls are actual small metal geometry, all in the wardrobe slot.
for plate in [front,back]:
    verts=plate.data.vertices
    columns=int(plate['armor_cols']);rows=int(plate['armor_rows'])
    indices=[row*columns+col for row in range(1,rows-1,3) for col in [1,columns-2]]
    for vertex in [verts[index] for index in indices]:
        co=vertex.co;normal=vertex.normal
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=4,location=co+normal*.004)
        rivet=bpy.context.object;rivet.name='Hammered plate rivet';rivet.scale=(.0035,.0035,.0035);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        for collection in list(rivet.users_collection):collection.objects.unlink(rivet)
        scene.collection.objects.link(rivet);rivet.data.materials.append(cloth)
        for uv in rivet.data.uv_layers.active.data:uv.uv=uv.uv*.45+Vector((.53,.53))
        for face in rivet.data.polygons:face.use_smooth=True
        garments.append(rivet)
# Blue waist-cloth panels echo the original sprite's military colour block.
for front_side in [-1]:
    verts=[];faces=[];uvs=[];nx=9;ny=8
    for row in range(ny):
        t=row/(ny-1);z=.79+t*.25;width=.15+.025*t
        for col in range(nx):
            u=col/(nx-1)*2-1;x=u*width
            hit=body_surface.ray_cast(Vector((x,front_side*.7,1.04)),Vector((0,-front_side,0)),1.4)
            waist_y=hit[0].y if hit[0] else front_side*.15
            y=waist_y+front_side*(.025+.012*(1-t)-.012*u*u)
            y+=front_side*.008*math.sin(u*math.pi*4+t)*math.sin(math.pi*t)
            verts.append((x,y,z+.012*(1-t)*abs(u)));uvs.append((col/(nx-1),t))
    for row in range(ny-1):
        for col in range(nx-1):a=row*nx+col;faces.append((a,a+1,a+1+nx,a+nx))
    garment('Blue waist cloth skirt panel',verts,faces,0,uvs,solid=.003)
# The diagonal leather baldric rests directly against the forged breastplate.
armor_vertices=[];armor_faces=[]
for plate in [front]+[g for g in garments if g.name.startswith('Overlapping steel waist lame')]:
    offset=len(armor_vertices);armor_vertices.extend(v.co.copy() for v in plate.data.vertices);armor_faces.extend([offset+i for i in face.vertices] for face in plate.data.polygons)
armor_surface=BVHTree.FromPolygons(armor_vertices,armor_faces)
verts=[];faces=[]
for row in range(24):
    t=row/23;x=-.15+.31*t;z=1.49-.40*t
    for shift in [-.021,.021]:
        xx=x+shift;hit=armor_surface.ray_cast(Vector((xx,-.8,z)),Vector((0,1,0)),1.6)
        y=hit[0].y-.004 if hit[0] is not None else surface_front(xx,z,.022)
        verts.append((xx,y,z))
for row in range(23):a=row*2;faces.append((a,a+1,a+3,a+2))
garment('Worn leather shoulder baldric',verts,faces,2,solid=.004)
# Remove redundant padded cloth directly beneath the rigid cuirass; retain overlap at the edges.
bm=bmesh.new();bm.from_mesh(coat.data)
covered=[]
for face in bm.faces:
    center=face.calc_center_median()
    if 1.14<center.z<1.39 and abs(center.x)<.15 and abs(center.y)>.07:covered.append(face)
if covered:bmesh.ops.delete(bm,geom=covered,context='FACES')
loose=[v for v in bm.verts if not v.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bm.to_mesh(coat.data);bm.free();coat.data.update()

# A continuous anatomical cloth cap follows the true shoulder/neck surface, not a floating cone.
neck_faces=[]
for polygon in body.data.polygons:
    center=sum((body.data.vertices[i].co for i in polygon.vertices),Vector())/len(polygon.vertices)
    if 1.40<center.z<1.64 and abs(center.x)<.31:neck_faces.append(list(polygon.vertices))
used=sorted({i for face in neck_faces for i in face});lookup={old:new for new,old in enumerate(used)}
vertices=[tuple(body.data.vertices[i].co+body.data.vertices[i].normal*.017) for i in used]
yoke=garment('Continuous fitted blue gambeson gorget',vertices,[[lookup[i] for i in face] for face in neck_faces],0,solid=.003)
bm=bmesh.new();bm.from_mesh(yoke.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,1.56),plane_no=(0,0,1),clear_outer=True,dist=1e-6)
bm.to_mesh(yoke.data);bm.free();yoke.data.update()

# Remove the old uneven cut-shirt rim beneath the new continuous yoke.
bm=bmesh.new();bm.from_mesh(coat.data)
faces=[face for face in bm.faces if face.calc_center_median().z>1.435 and abs(face.calc_center_median().x)<.275]
if faces:bmesh.ops.delete(bm,geom=faces,context='FACES')
loose=[v for v in bm.verts if not v.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bm.to_mesh(coat.data);bm.free();coat.data.update()

# Remove the civilian shirt placket hidden by armor, avoiding trim poking through metal.
for piece in list(garments):
    if piece.name.startswith('Shirt stitched split placket edging') or piece.name.startswith('Sewn continuous neckline binding'):
        garments.remove(piece);bpy.data.objects.remove(piece,do_unlink=True)

# Retain only visible anatomical skin. Clothing replaces covered body geometry.
me=body.data;bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[bm.faces[i] for i in sorted(hide)],context='FACES')
loose=[v for v in bm.verts if not v.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bm.to_mesh(me);bm.free();me.update()
for ob in [body,*parts.values()]:
    for p in ob.data.polygons:p.use_smooth=True

# Source character consists of true anatomical skin, fitted hair/eyes and original clothes.
coll=bpy.data.collections.new('SK_Milder');scene.collection.children.link(coll)
coll['dink_class']='character_humanoid';coll['dink_path']='Stonebrook';coll['dink_source']='CC0 MakeHuman body/eyes/hair plus original soldier plate armor, blue gambeson/waist cloth and leather equipment; see Provenance'
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
scene.view_settings.view_transform='AgX';scene.render.filepath=str(ART/'preview_milder.png')
(ART/'milder_materials.json').write_text(json.dumps(MATERIALS,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'Milder_Working.blend'))
bpy.ops.render.render(write_still=True)
print('DINK ART:',len(body.data.polygons),'visible skin faces;',len(garments),'authored clothing meshes')
