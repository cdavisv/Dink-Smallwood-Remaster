"""Original3D pine-sprig atlas:pairedneedles, branchalbedo/normal/ORM, no photos."""
import bpy,math,random,json
from pathlib import Path
from mathutils import Vector
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];TEX=ROOT/'Textures';WORK=ROOT/'Working';WORK.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.cycles.use_denoising=False;scene.cycles.transparent_max_bounces=16;scene.render.film_transparent=True;scene.render.resolution_x=2048;scene.render.resolution_y=2048;scene.render.resolution_percentage=100
rnd=random.Random(471031);verts=[];faces=[];indices=[]
def tube(a,b,ra,rb,mat,sides=5):
 a=Vector(a);b=Vector(b);d=(b-a).normalized();ref=Vector((0,0,1))
 if abs(d.dot(ref))>.95:ref=Vector((0,1,0))
 u=d.cross(ref).normalized();v=d.cross(u).normalized();start=len(verts)
 for p,r in [(a,ra),(b,rb)]:
  for j in range(sides):verts.append(p+r*(math.cos(j*math.tau/sides)*u+math.sin(j*math.tau/sides)*v))
 faces.extend([tuple(start+j for j in reversed(range(sides))),tuple(start+sides+j for j in range(sides))]);indices.extend([mat,mat])
 for j in range(sides):faces.append((start+j,start+(j+1)%sides,start+sides+(j+1)%sides,start+sides+j));indices.append(mat)
def needle(p,d,length,width,mat):
 d=d.normalized();ref=Vector((0,0,1));u=d.cross(ref).normalized();v=d.cross(u).normalized();start=len(verts)
 for j in range(3):verts.append(p+width*(math.cos(j*math.tau/3)*u+math.sin(j*math.tau/3)*v))
 verts.append(p+d*length);faces.extend([(start+2,start+1,start),(start,start+1,start+3),(start+1,start+2,start+3),(start+2,start,start+3)]);indices.extend([mat]*4)
tube((-.30,0,0),(.30,0,.018),.006,.002,0)
needle_count=0
for twig in range(24):
 f=(twig+.5)/24;side=-1 if twig%2 else 1;root=Vector((-.27+f*.50,0,f*.016));end=root+Vector((.10+rnd.uniform(-.03,.03),side*(.08+rnd.uniform(.025,.065)),rnd.uniform(.018,.050)));tube(root,end,.0022,.0008,0,4)
 for sub in range(3):
  sr=root.lerp(end,.28+sub*.24);tip=sr+Vector((rnd.uniform(.015,.05),side*rnd.uniform(.028,.065),rnd.uniform(-.015,.035)));tube(sr,tip,.0011,.00035,0,3);axis=(tip-sr).normalized();u=axis.cross(Vector((0,0,1))).normalized();v=axis.cross(u).normalized()
  for k in range(44):
   q=(k+.5)/44;base=sr.lerp(tip,q);angle=rnd.uniform(0,math.tau);radial=u*math.cos(angle)+v*math.sin(angle)
   for pair in [-1,1]:
    d=(axis*.45+radial*.89+u*pair*.07).normalized();needle(base,d,rnd.uniform(.034,.061),rnd.uniform(.0006,.00105),rnd.randrange(1,6));needle_count+=1
me=bpy.data.meshes.new('Original pairedpine needle sprig');me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(me.name,me);scene.collection.objects.link(ob)
colors=[(.09,.045,.015),(.019,.050,.024),(.029,.070,.032),(.041,.086,.039),(.025,.062,.034),(.048,.096,.047)];materials=[]
for i,c in enumerate(colors):
 m=bpy.data.materials.new('Atlas bark' if i==0 else'Atlasneedle%02d'%i);m.use_nodes=True;n=m.node_tree.nodes;n.clear();out=n.new('ShaderNodeOutputMaterial');em=n.new('ShaderNodeEmission');em.inputs['Color'].default_value=(*c,1);m.node_tree.links.new(em.outputs[0],out.inputs['Surface']);me.materials.append(m);materials.append(m)
for p,i in zip(me.polygons,indices):p.material_index=i;p.use_smooth=False
cd=bpy.data.cameras.new('Atlas orthographic');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=(0,-.62,.95);cam.rotation_euler=(Vector((.02,0,.02))-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=.76;scene.camera=cam
world=bpy.data.worlds.new('Atlas transparentworld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[1].default_value=0;scene.world=world
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'NeedleSprig_High.blend'))
scene.view_settings.view_transform='Standard';scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.filepath=str(WORK/'NeedleSprig_BC.png');bpy.ops.render.render(write_still=True)
# Tangentcard coordinates arecameraX/Y andcamera-facingZ; OpenGL normaltexture.
for m in materials:
 n=m.node_tree.nodes;l=m.node_tree.links;em=next(x for x in n if x.type=='EMISSION');geo=n.new('ShaderNodeNewGeometry');transform=n.new('ShaderNodeVectorTransform');transform.vector_type='NORMAL';transform.convert_from='WORLD';transform.convert_to='CAMERA';l.new(geo.outputs['Normal'],transform.inputs['Vector']);scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=.5;l.new(transform.outputs[0],scale.inputs[0]);add=n.new('ShaderNodeVectorMath');add.operation='ADD';add.inputs[1].default_value=(.5,.5,.5);l.new(scale.outputs[0],add.inputs[0]);l.new(add.outputs[0],em.inputs['Color'])
scene.view_settings.view_transform='Raw';scene.render.filepath=str(WORK/'NeedleSprig_N.png');bpy.ops.render.render(write_still=True)
# Keep transparentRGB filledwithneedlecolor for cleanmips; normalbackgroundflatblue.
bc=np.asarray(Image.open(WORK/'NeedleSprig_BC.png').convert('RGBA')).copy();norm=np.asarray(Image.open(WORK/'NeedleSprig_N.png').convert('RGBA')).copy();alpha=bc[:,:,3].astype('float32')/255
for channel,value in enumerate([44,72,48]):bc[:,:,channel]=np.where(alpha>0,bc[:,:,channel],value)
normalrgb=norm[:,:,:3].astype('float32');normalrgb=normalrgb*alpha[:,:,None]+np.array([128,128,255])[None,None,:]*(1-alpha[:,:,None]);normalrgb=np.clip(normalrgb,0,255).astype('uint8')
orm=np.empty_like(normalrgb);orm[:,:,0]=230;orm[:,:,1]=198;orm[:,:,2]=0
for stem in ['T_PineV3_Needles','T_PineV3_Sprays']:
 Image.fromarray(bc,'RGBA').save(TEX/(stem+'_BC.png'));Image.fromarray(normalrgb,'RGB').save(TEX/(stem+'_N.png'));Image.fromarray(orm,'RGB').save(TEX/(stem+'_ORM.png'))
# Pack the originalfrond tightly toavoidtransparent-bordermip dilution.
bounds=Image.fromarray(bc[:,:,3],'L').getbbox();pad=8;bounds=(max(0,bounds[0]-pad),max(0,bounds[1]-pad),min(2048,bounds[2]+pad),min(2048,bounds[3]+pad))
for stem in ['T_PineV3_Needles','T_PineV3_Sprays']:
 for channel in ['BC','N','ORM']:
  p=TEX/(stem+'_'+channel+'.png');im=Image.open(p);im=im.crop(bounds).resize((2048,2048),Image.Resampling.BICUBIC);im.save(p)
alpha=np.asarray(Image.open(TEX/'T_PineV3_Sprays_BC.png'))[:,:,3].astype('float32')/255
materials=json.loads((ROOT/'pine_materials.json').read_text());materials['MI_PineV3_Sprays'].update(alpha_clip=.12,preserve_alpha_coverage=True);(ROOT/'pine_materials.json').write_text(json.dumps(materials,indent=2)+'\n')
coverage=float(alpha.mean());(ROOT/'needle_alpha_coverage.json').write_text(json.dumps({'coverage':coverage,'opacity_clip':.12,'original_modeled_needles':needle_count,'sprig_size_m':.76,'source':'Working/NeedleSprig_High.blend','note':'Original3Dpairedneedle sprig, emission-albedo +cameratangentnormal. No downloadedimages. AlphaMips must remainaboveclip.'},indent=2)+'\n')
print('PINE ORIGINAL3D NEEDLE ATLAS',needle_count,'needles coverage',coverage,flush=True)
