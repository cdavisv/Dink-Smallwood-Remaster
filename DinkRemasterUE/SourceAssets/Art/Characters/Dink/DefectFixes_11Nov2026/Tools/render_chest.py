"""Review renders of the 11 Nov 2026 chest fix (never saves the .blend).
blender -b <file.blend> -P render_chest.py -- <out.png> [lod] [clay|tex] [rake_r|rake_l|close_r|close_l|rake_top]
rake_r: front camera, a small area light almost grazing the chest from his right (-X); close_r/close_l: 160 mm
lens on one pectoral with the light grazing from that side; clay replaces every material with one matte colour."""
import bpy, sys, math
from mathutils import Vector
argv = sys.argv[sys.argv.index('--')+1:]
out = argv[0]; lod = int(argv[1]) if len(argv)>1 else 0; mode = argv[2] if len(argv)>2 else 'clay'; light = argv[3] if len(argv)>3 else 'rake_r'
s = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type=='LIGHT': bpy.data.objects.remove(o)
target = next(o for o in bpy.data.objects if o.type=='MESH' and o.name.endswith(f'_LOD{lod}'))
for o in bpy.data.objects:
    if o.type=='MESH': o.hide_render = (o is not target)
arm = bpy.data.objects['Armature']; arm.data.pose_position='REST'
if mode=='clay':
    m = bpy.data.materials.new('clay'); m.use_nodes=True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value=(0.55,0.25,0.2,1); b.inputs['Roughness'].default_value=0.6
    target.data.materials.clear() if False else None
    for i in range(len(target.material_slots)): target.material_slots[i].link='OBJECT'; target.material_slots[i].material=m
s.render.engine='CYCLES'; s.cycles.samples=64; s.cycles.use_denoising=True
s.render.resolution_x=900; s.render.resolution_y=900
w = s.world or bpy.data.worlds.new('w'); s.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.02,0.02,0.02,1)
cam = s.camera
if cam is None:
    cd = bpy.data.cameras.new('c'); cam = bpy.data.objects.new('c', cd); s.collection.objects.link(cam); s.camera=cam
def look(loc, tgt, lens):
    cam.location=Vector(loc); cam.rotation_euler=(Vector(tgt)-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.lens=lens
def add_light(loc, tgt, energy, size=0.05):
    ld = bpy.data.lights.new('L','AREA'); ld.energy=energy; ld.size=size
    lo = bpy.data.objects.new('L', ld); s.collection.objects.link(lo); lo.location=Vector(loc)
    lo.rotation_euler=(Vector(tgt)-lo.location).to_track_quat('-Z','Y').to_euler()
if light=='rake_r':
    look((0,-1.1,1.30),(0,0,1.29),70)
    add_light((-1.2,-0.25,1.40),(0,-0.1,1.3),120)   # raking from his right (-X), almost grazing the chest
    add_light((0.4,-1.5,1.6),(0,0,1.3),8,1.0)
elif light=='rake_l':
    look((0,-1.1,1.30),(0,0,1.29),70)
    add_light((1.2,-0.25,1.40),(0,-0.1,1.3),120)
    add_light((-0.4,-1.5,1.6),(0,0,1.3),8,1.0)
elif light in ('close_r','close_l'):
    sx = -1 if light=='close_r' else 1
    look((sx*0.09,-0.75,1.31),(sx*0.09,0,1.30),160)
    add_light((sx*1.2,-0.35,1.38),(sx*0.05,-0.1,1.3),120)
    add_light((0,-1.5,1.6),(0,0,1.3),4,1.0)
elif light=='rake_top':
    look((0,-1.1,1.30),(0,0,1.29),70)
    add_light((0,-0.3,2.6),(0,-0.1,1.3),300)
elif light=='back_head':
    # camera in front-left of the face, very strong light behind the head, dim fill
    look((0.35,-0.75,1.66),(0,0,1.64),85)
    add_light((-0.2,1.2,1.75),(0,0,1.65),900,0.6)
    add_light((0.6,-1.2,1.7),(0,0,1.65),3,1.0)
    w.node_tree.nodes['Background'].inputs[0].default_value=(0.6,0.5,0.35,1)
s.render.filepath=out
bpy.ops.render.render(write_still=True)
print('RENDERED', out)
