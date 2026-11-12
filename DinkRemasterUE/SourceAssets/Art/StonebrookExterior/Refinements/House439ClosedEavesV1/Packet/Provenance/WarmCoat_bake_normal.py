from pathlib import Path

import bpy

folder = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(folder.parent / 'WholeRoofWarmTilesV1/House439_WarmTiles.blend'))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 2
scene.render.compositor_device = 'CPU'
material = bpy.data.objects['RoofFamily_CoreShell'].data.materials[0].copy()
nodes = material.node_tree.nodes
bpy.ops.mesh.primitive_plane_add(size=2)
plane = bpy.context.object
plane.data.uv_layers.active.name = 'UV0'
mask = plane.data.uv_layers.new(name='UV1_SharedData',do_init=False)
for loop in mask.data:
    loop.uv = (0,0)
plane.data.uv_layers.active_index = 0
plane.data.materials.append(material)
image = bpy.data.images.new('T_WarmBundleCoat_N_GL',width=2048,height=2048,alpha=False)
image.colorspace_settings.name = 'Non-Color'
target = nodes.new('ShaderNodeTexImage')
target.image = image
nodes.active = target
scene.render.bake.normal_space = 'TANGENT'
bpy.ops.object.bake(type='NORMAL',margin=0,uv_layer='UV0')
image.filepath_raw = str(folder / 'T_WarmBundleCoat_N_GL.png')
image.file_format = 'PNG'
image.save()
