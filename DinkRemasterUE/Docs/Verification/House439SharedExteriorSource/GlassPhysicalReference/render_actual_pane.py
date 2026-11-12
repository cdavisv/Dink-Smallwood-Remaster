"""Controlled source reference using the exact cottage pane; no source/native edits."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
import sys
D=Path(sys.argv[sys.argv.index('--out')+1]).resolve() if '--out' in sys.argv else Path(__file__).resolve().parent;D.mkdir(exist_ok=True);P=Path(__file__).resolve().parents[4]/'SourceAssets/Art/Stonebrook/Refinements/House439SharedExteriorV1/House439_SharedExterior_Source.blend';assert not (D/'REFERENCE.json').exists(),'Use --out with a fresh folder; preserve frozen proof'
source_sha=hashlib.sha256(P.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(P));bpy.context.view_layer.update();pane=bpy.data.objects['InsetGlassPane.009'];matrix=pane.matrix_world.copy();mesh=pane.data
before={'vertices':[list(v.co)for v in mesh.vertices],'faces':[list(p.vertices)for p in mesh.polygons],'UV':[[list(x.uv)for x in u.data]for u in mesh.uv_layers],'matrix':[list(x)for x in matrix]};material=next(m for m in mesh.materials if m and m.name=='MI_Shared_ThinWavyGlass2m');pane.parent=None;pane.matrix_world=matrix
for o in list(bpy.data.objects):
 if o!=pane:bpy.data.objects.remove(o,do_unlink=True)
for m in list(bpy.data.materials):
 if m!=material:bpy.data.materials.remove(m,do_unlink=True)
for collection in [bpy.data.meshes,bpy.data.images]:
 for data in list(collection):
  if data.users==0:collection.remove(data)
world_positions=[pane.matrix_world@v.co for v in mesh.vertices];center=Vector([(min(v[i]for v in world_positions)+max(v[i]for v in world_positions))/2 for i in range(3)])
checker=bpy.data.materials.new('ReferenceCardEmission');checker.use_nodes=True;n=checker.node_tree.nodes;l=checker.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial');em=n.new('ShaderNodeEmission');em.inputs['Strength'].default_value=.8;uv=n.new('ShaderNodeTexCoord');grid=n.new('ShaderNodeTexChecker');grid.inputs['Scale'].default_value=8;grid.inputs['Color1'].default_value=(.015,.1,.38,1);grid.inputs['Color2'].default_value=(.82,.55,.07,1);l.new(uv.outputs['Generated'],grid.inputs['Vector']);l.new(grid.outputs['Color'],em.inputs['Color']);l.new(em.outputs[0],out.inputs['Surface'])
cardmesh=bpy.data.meshes.new('Card');cardmesh.from_pydata([(-.7,0,-.7),(.7,0,-.7),(.7,0,.7),(-.7,0,.7)],[],[(0,1,2,3)]);cardmesh.update();card=bpy.data.objects.new('PatternReferenceCard',cardmesh);bpy.context.scene.collection.objects.link(card);cardmesh.materials.append(checker)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=64;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=2;s.render.resolution_x=800;s.render.resolution_y=800;s.render.resolution_percentage=100;s.view_layers[0].material_override=None
world=bpy.data.worlds.new('ControlledReflectionEnvironment');world.use_nodes=True;world.node_tree.nodes.get('Background').inputs[0].default_value=(.11,.14,.2,1);world.node_tree.nodes.get('Background').inputs[1].default_value=.5;s.world=world
ld=bpy.data.lights.new('ReflectionSoftbox','AREA');ld.energy=35;ld.shape='RECTANGLE';ld.size=.35;ld.size_y=1.;light=bpy.data.objects.new(ld.name,ld);s.collection.objects.link(light)
cd=bpy.data.cameras.new('ReferenceCamera');camera=bpy.data.objects.new(cd.name,cd);s.collection.objects.link(camera);s.camera=camera;cd.type='ORTHO';cd.ortho_scale=.85
views=[('outside_card',Vector((0,-2,0)),.2),('inside_card',Vector((0,2,0)),-.2),('outside_grazing',Vector((1.8,-.65,.15)),.2)];receipts=[]
for name,offset,card_offset in views:
 camera.location=center+offset;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();card.location=center+Vector((0,card_offset,0));sign=-1 if offset.y<0 else 1;light.location=center+Vector((-.55,sign*.8,.3));light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
 for state in ['glass','bare']:
  pane.hide_render=state=='bare';filename=f'{name}_{state}.png';s.render.filepath=str(D/filename);bpy.ops.render.render(write_still=True);receipts.append({'file':filename,'camera':list(camera.location),'target':list(center),'card_center':list(card.location),'glass_visible':state=='glass','sha256':hashlib.sha256((D/filename).read_bytes()).hexdigest()});print('PANE_REFERENCE_DONE',filename,flush=True)
pane.hide_render=False;bpy.ops.wm.save_as_mainfile(filepath=str(D/'ActualCottagePane_OpticalReference.blend'),compress=True)
after={'vertices':[list(v.co)for v in mesh.vertices],'faces':[list(p.vertices)for p in mesh.polygons],'UV':[[list(x.uv)for x in u.data]for u in mesh.uv_layers],'matrix':[list(x)for x in pane.matrix_world]};assert before==after;assert source_sha==hashlib.sha256(P.read_bytes()).hexdigest();(D/'REFERENCE.json').write_text(json.dumps({'status':'RENDERED_ACTUAL_CLOSED_PANE_SOURCE_REFERENCE_REVIEW_PENDING','source_sha256_unchanged':source_sha,'pane':'InsetGlassPane.009','pane_geometry_UV_world_transform_exact':True,'dimensions_m':[.35,.012,.56],'source_material':material.name,'CPU_threads':2,'samples':64,'views':receipts,'qualification':'Cycles thinwall material on originalclosed12mmgeometry, not native one-sided policy parity. Bare controls remove only pane fromrender; emittercard andreflectionsoftbox fixed perpair. Finewaviness mayremain subtle. No native/cottage source edit or finalapproval.'},indent=2)+'\n')
