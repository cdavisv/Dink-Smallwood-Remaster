"""Review renders of the head under backlight (never saves the .blend).
blender -b <file.blend> -P render_head.py -- <out.png> <atlas dir> [backlit|skylit|roughness]
<atlas dir> holds T_Dink_Atlas_{BC,N,ORM}.png to use instead of the file's own (e.g. box-reduced copies that stand in
for the mip level the game samples); roughness shows the ORM G channel the shader reads, as emission."""
import bpy, sys
from mathutils import Vector
argv = sys.argv[sys.argv.index('--')+1:]
out, atlas = argv[0], argv[1]
mode = argv[2] if len(argv) > 2 else 'backlit'
s = bpy.context.scene
for img in bpy.data.images:
    if img.filepath.endswith(('T_Dink_Atlas_BC.png','T_Dink_Atlas_N.png','T_Dink_Atlas_ORM.png')):
        img.filepath = atlas + '/' + img.filepath.split('/')[-1]; img.reload()
for m in bpy.data.materials:
    if m.node_tree:
        for n in m.node_tree.nodes:
            if n.type=='TEX_IMAGE': n.interpolation='Linear'
for o in list(bpy.data.objects):
    if o.type=='LIGHT': bpy.data.objects.remove(o)
lod0 = next(o for o in bpy.data.objects if o.type=='MESH' and o.name.endswith('_LOD0'))
for o in bpy.data.objects:
    if o.type=='MESH': o.hide_render = (o is not lod0)
bpy.data.objects['Armature'].data.pose_position='REST'
s.render.engine='CYCLES'; s.cycles.samples=96; s.cycles.use_denoising=True
s.render.resolution_x=900; s.render.resolution_y=1000
w = s.world or bpy.data.worlds.new('w'); s.world=w; w.use_nodes=True
w.node_tree.nodes['Background'].inputs[0].default_value=(0.35,0.25,0.18,1); w.node_tree.nodes['Background'].inputs[1].default_value=0.08
cam = s.camera
cam.location=Vector((0.45,-0.55,1.64)); cam.rotation_euler=(Vector((0,0,1.62))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.lens=85
def add_light(loc, tgt, energy, size):
    ld = bpy.data.lights.new('L','AREA'); ld.energy=energy; ld.size=size
    lo = bpy.data.objects.new('L', ld); s.collection.objects.link(lo); lo.location=Vector(loc)
    lo.rotation_euler=(Vector(tgt)-lo.location).to_track_quat('-Z','Y').to_euler()
add_light((-0.45,0.8,1.75),(0,0,1.65),900,0.8)   # strong light behind his head (a bright window)
add_light((0.6,-1.0,1.6),(0,0,1.6),1.5,1.0)     # weak front fill
# a bright backdrop card behind him, like the lit wall in the game frame
bpy.ops.mesh.primitive_plane_add(size=4, location=(-1.0,1.6,1.6), rotation=(1.5708,0,0.55))
card = bpy.context.active_object
mat = bpy.data.materials.new('wall'); mat.use_nodes=True
e = mat.node_tree.nodes.new('ShaderNodeEmission'); e.inputs[0].default_value=(1,0.85,0.6,1); e.inputs[1].default_value=6
mat.node_tree.links.new(e.outputs[0], mat.node_tree.nodes['Material Output'].inputs[0]); card.data.materials.append(mat)
if mode == 'roughness':
    # show what the shader reads as roughness (ORM G) at this mip, as plain emission
    for m in bpy.data.materials:
        if not m.node_tree or m.name == 'wall': continue
        nt = m.node_tree; orm = next((n for n in nt.nodes if n.type=='TEX_IMAGE' and n.image and 'ORM' in n.image.name), None)
        if orm is None: continue
        sep = nt.nodes.new('ShaderNodeSeparateColor'); em = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(orm.outputs['Color'], sep.inputs[0]); nt.links.new(sep.outputs[1], em.inputs[0])
        nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL').inputs[0])
    for o in list(bpy.data.objects):
        if o.type=='LIGHT' or o.name.startswith('Plane'): bpy.data.objects.remove(o)
    w.node_tree.nodes['Background'].inputs[1].default_value=0.0
    s.cycles.samples=16
elif mode == 'skylit':
    # bright surroundings (like the lit room/sky the game's reflections see), light behind him
    w.node_tree.nodes['Background'].inputs[0].default_value=(1,0.95,0.9,1); w.node_tree.nodes['Background'].inputs[1].default_value=1.0
s.render.filepath=out
bpy.ops.render.render(write_still=True)
print('RENDERED', out)
