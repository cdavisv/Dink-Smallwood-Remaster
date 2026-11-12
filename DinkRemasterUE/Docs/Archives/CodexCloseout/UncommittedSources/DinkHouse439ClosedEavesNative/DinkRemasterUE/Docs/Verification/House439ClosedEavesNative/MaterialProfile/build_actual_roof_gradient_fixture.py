"""New diagnostic mesh from actual source data; frozen artwork remains unchanged."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
D=Path('<HOME>/Work/DinkQA/House439ActualRoofGradientV1');D.mkdir(parents=True,exist_ok=True)
P=Path('<HOME>/Work/DinkQA/House439ClosedEavesNativeReference/FROZEN_FBX_GEOMETRY.npz')
sha=hashlib.sha256(P.read_bytes()).hexdigest();assert sha=='20e969bcd0f4fae11f47d6d224e8063eb802e615263a8304ecd0c16c020d0c3d'
a=np.load(P,allow_pickle=False);tri=a['triangles'];values=a['color_linear_rgba'][tri];ids=np.flatnonzero(np.ptp(values[:,:,0],axis=1)>1e-6)
assert ids.tolist()==[127971,127972,128499,134703,134704,134705,134706,134707,134736,134862]
bpy.ops.wm.read_factory_settings(use_empty=True);positions=[];faces=[];tiles=[]
for ordinal,source_id in enumerate(ids):
 x=(ordinal%4)*1.25;y=(ordinal//4)*1.25;offset=len(positions);positions.extend([(x,y,0),(x+1,y,0),(x,y+1,0)]);faces.append((offset,offset+1,offset+2))
 tiles.append(dict(tile=ordinal,source_triangle=int(source_id),origin_xy=[x,y],source_RGBA=values[source_id].tolist()))
m=bpy.data.meshes.new('ActualRoofGradient');m.from_pydata(positions,[],faces);m.update();uv0=m.uv_layers.new(name='UV0');uv1=m.uv_layers.new(name='UV1_SharedData');color=m.color_attributes.new(name='SharedSurfaceData',type='FLOAT_COLOR',domain='CORNER')
for ordinal,source_id in enumerate(ids):
 for j,source_corner in enumerate(tri[source_id]):
  li=ordinal*3+j;uv0.data[li].uv=a['uv0'][source_corner];uv1.data[li].uv=a['uv1'][source_corner];color.data[li].color=a['color_linear_rgba'][source_corner]
m.color_attributes.active_color=color
obj=bpy.data.objects.new('SM_ActualRoofGradient',m);bpy.context.scene.collection.objects.link(obj)
mat=bpy.data.materials.new('M_SourceLinearVertexDiagnostic');mat.use_nodes=True;n=mat.node_tree.nodes;n.clear();links=mat.node_tree.links
out=n.new('ShaderNodeOutputMaterial');em=n.new('ShaderNodeEmission');attribute=n.new('ShaderNodeVertexColor');attribute.layer_name='SharedSurfaceData';links.new(attribute.outputs['Color'],em.inputs['Color']);links.new(em.outputs[0],out.inputs['Surface']);m.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1;scene.cycles.use_denoising=False;scene.render.resolution_x=768;scene.render.resolution_y=576;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='OPEN_EXR';scene.render.image_settings.color_depth='32'
cam=bpy.data.objects.new('GradientCamera',bpy.data.cameras.new('GradientCamera'));scene.collection.objects.link(cam);cam.location=(2.375,1.75,10);cam.data.type='ORTHO';cam.data.ortho_scale=5.4;scene.camera=cam
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
fbx=D/'SM_ActualRoofGradient.fbx';bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},mesh_smooth_type='EDGE',use_triangles=True,use_tspace=False,colors_type='LINEAR',prioritize_active_color=True,apply_unit_scale=True,global_scale=1,apply_scale_options='FBX_SCALE_ALL',axis_forward='Y',axis_up='Z',bake_anim=False,path_mode='RELATIVE')
bpy.ops.wm.save_as_mainfile(filepath=str(D/'SourceGradient.blend'),compress=True)
W,H=768,576;deps=bpy.context.evaluated_depsgraph_get();projection=cam.calc_matrix_camera(deps,x=W,y=H);inverse=(projection@cam.matrix_world.inverted()).inverted();samples=[]
for mode in ('RGB','Alpha'):
 for link in list(em.inputs['Color'].links):links.remove(link)
 links.new(attribute.outputs['Color'if mode=='RGB'else'Alpha'],em.inputs['Color']);scene.render.filepath=str(D/('Source_'+mode+'.exr'));bpy.ops.render.render(write_still=True)
 image=bpy.data.images.load(scene.render.filepath,check_existing=False);pixels=np.array(image.pixels[:],dtype=np.float64).reshape(H,W,4);bpy.data.images.remove(image)
 for tile in tiles:
  origin=np.array(tile['origin_xy']);rgba=np.array(tile['source_RGBA'])
  for weights in ((1/3,1/3,1/3),(.45,.45,.1),(.1,.45,.45)):
   target=origin+np.array([weights[1],weights[2]]);view=world_to_camera_view(scene,cam,Vector((target[0],target[1],0)));px=int(view.x*W);py=int(view.y*H)
   world=inverse@Vector((2*(px+.5)/W-1,2*(py+.5)/H-1,-1,1));world/=world.w;local=np.array([world.x,world.y])-origin;actual_weights=np.array([1-local.sum(),local[0],local[1]])
   assert np.min(actual_weights)>.05
   expected=actual_weights@rgba;wanted=expected[:3]if mode=='RGB'else np.repeat(expected[3],3);actual=pixels[py,px,:3];error=float(np.max(np.abs(actual-wanted)))
   # One-sample pixel jitter moves the actual sample within this pixel.
   # Record the measured deviation, do not declare a future native tolerance.
   samples.append(dict(mode=mode,tile=tile['tile'],source_triangle=tile['source_triangle'],pixel_bottom_xy=[px,py],
    expected_pixel_center_barycentric=actual_weights.tolist(),expected_linear_RGB=wanted.tolist(),actual_Cycles_RGB=actual.tolist(),max_pixel_center_error=error))
assert hashlib.sha256(P.read_bytes()).hexdigest()==sha
report=dict(scope='Actual10roofdata gradients on flat diagnostic triangles; CPU source renders, not native/GPU acceptance',source_reference_sha256=sha,tiles=tiles,samples=samples,
 render_size=[W,H],camera_world=[2.375,1.75,10],orthographic_width=5.4,fbx_sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),
 max_observed_CPU_pixel_center_deviation=max(v['max_pixel_center_error']for v in samples),native_tolerance_defined=False,source_art_modified=False)
(D/'FIXTURE.json').write_text(json.dumps(report,indent=2)+'\n');print('GRADIENT_FIXTURE_COMPLETE',len(tiles),len(samples),report['max_observed_CPU_pixel_center_deviation'],flush=True)
