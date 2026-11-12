import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
D=Path(__file__).resolve().parents[1];C=D/'Review';P=D/'House439_SharedExterior_Source.blend';before=hashlib.sha256(P.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(P));objects=[bpy.data.objects['SM_Cottage_Stonebrook_01']]+list(bpy.data.collections['House439_ProductionMineralCandidateV1'].objects)
for a in bpy.context.scene.objects:a.hide_render=a not in objects
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=900;s.render.resolution_y=600;s.render.resolution_percentage=100
clay=bpy.data.materials.new('V13_MACRO_CLAY_REVIEW_ONLY');clay.use_nodes=True;bs=clay.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.42,.40,.36,1);bs.inputs['Roughness'].default_value=.8;s.view_layers[0].material_override=None
w=bpy.data.worlds.new('V13ClayWorld');w.use_nodes=True;w.node_tree.nodes.get('Background').inputs[0].default_value=(.35,.38,.42,1);w.node_tree.nodes.get('Background').inputs[1].default_value=.6;s.world=w
ld=bpy.data.lights.new('MacroReviewKey','AREA');ld.energy=3500;ld.size=12;a=bpy.data.objects.new('MacroReviewKey',ld);s.collection.objects.link(a);a.location=(2,-12,17);a.rotation_euler=(Vector((0,0,2))-a.location).to_track_quat('-Z','Y').to_euler();a.hide_render=False
cd=bpy.data.cameras.new('V13ClayCamera');cam=bpy.data.objects.new('V13ClayCamera',cd);s.collection.objects.link(cam);s.camera=cam;cd.type='ORTHO';cam.hide_render=False
views=[('color_broad_front.png',(21,-26,16),(0,0,3.4),26),('color_broad_guide_direction.png',(-26,-21,16),(0,0,3.4),26),('color_wood_window_closeup.png',(-4.1,-8.2,3.2),(-3.,-4.5,2.3),2.2),('color_hip_eave_closeup.png',(-12,-9,6),(-8,-3.8,3.7),4.4)]
views.append(('color_eave_cutfield_closeup.png',(0,-7.6,4.05),(0,-5.19,3.4),1.65))
views.append(('color_chimney_flashing_closeup.png',(-9,-2,10),(-5.435,1.9,6.8),4.0))
views=[v for v in views if v[0] in ['color_broad_front.png','color_wood_window_closeup.png','color_hip_eave_closeup.png']]
for name,pos,target,scale in views:
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=scale;s.render.filepath=str(C/name);bpy.ops.render.render(write_still=True);print('CLAY_VIEW_DONE',name,flush=True)
assert hashlib.sha256(P.read_bytes()).hexdigest()==before
(C/'COLOR_RENDER_RECEIPT.json').write_text(json.dumps({'status':'Actual CPU registered shared cottage material views; review pending','blend_sha256_unchanged':before,'views':[{'file':v[0],'camera':v[1],'target':v[2],'ortho_scale':v[3],'sha256':hashlib.sha256((C/v[0]).read_bytes()).hexdigest()}for v in views],'CPU_threads':2,'material_override':'None; seven registered shared roles, thin-glass derivative; sourcefile not saved','guide_camera':'Approximate matchingdirection; notsourcecameracalibration/identicalpixel-silhouetteclaim','scope':'Registered source derivative; fixed views match prior V6 review cameras/settings, not native or final appearance approval'},indent=2)+'\n');print('V14_COLOR_COMPLETE',flush=True)
