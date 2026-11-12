"""Diffuse-color reference ONLY; preserve geometry and all other material inputs."""
import bpy,json,hashlib,sys,os,traceback
from pathlib import Path
O=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
try:
 source=O/'Inputs/V3_Source.blend';pin=sha(source);assert pin=='eb43ac65cce5d84b8880adf5dbef0e69b46f51005748f8e7e4dbe9adae38e8bb';imagepath=O/'Textures/GeneratedShortcrust_Albedo_V1.png';assert sha(imagepath)=='4b211bc541e2bdced47dc483c3378d03f4f64411823a2052d41537c0c3fe233b'
 bpy.ops.wm.open_mainfile(filepath=str(source));mat=bpy.data.materials['MI_Pie_PastryFruit_PhotoSource'];N=mat.node_tree.nodes;L=mat.node_tree.links;bs=next(n for n in N if n.type=='BSDF_PRINCIPLED');color=bs.inputs['Base Color'].links[0].from_node;assert color.type=='MIX_RGB'
 coord=N.new('ShaderNodeTexCoord');coord.name='GeneratedReference_ObjectCoordinates';scale=N.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs['Scale'].default_value=12.5;L.new(coord.outputs['Object'],scale.inputs[0]);tex=N.new('ShaderNodeTexImage');tex.name='GeneratedShortcrust_DIFFUSE_ONLY';tex.label='Original AI-generated reference, COLOR ONLY; no derived normal/height';im=bpy.data.images.load(str(imagepath),check_existing=False);im.colorspace_settings.name='sRGB';im.pack();im.filepath='//Textures/'+imagepath.name;tex.image=im;tex.projection='BOX';tex.projection_blend=.18;tex.interpolation='Linear'
 extensions=[i.identifier for i in tex.bl_rna.properties['extension'].enum_items]
 if 'MIRROR'in extensions:
  tex.extension='MIRROR';L.new(scale.outputs[0],tex.inputs['Vector']);mapping='MIRROR extension with metre-scaled Object box projection'
 else:
  split=N.new('ShaderNodeSeparateXYZ');join=N.new('ShaderNodeCombineXYZ');L.new(scale.outputs[0],split.inputs[0])
  for axis in range(3):
   ping=N.new('ShaderNodeMath');ping.operation='PINGPONG';ping.inputs[1].default_value=1;L.new(split.outputs[axis],ping.inputs[0]);L.new(ping.outputs[0],join.inputs[axis])
  tex.extension='EXTEND';L.new(join.outputs[0],tex.inputs['Vector']);mapping='Continuous ping-pong Object coordinates with box projection; raw reference tileability not asserted'
 exposure=N.new('ShaderNodeMixRGB');exposure.blend_type='MULTIPLY';exposure.inputs[0].default_value=1;exposure.inputs[2].default_value=(.28,.20,.12,1);L.new(tex.outputs['Color'],exposure.inputs[1]);brown=next(n for n in N if n.type=='ATTRIBUTE'and n.attribute_name=='Browning');shade=N.new('ShaderNodeMapRange');shade.inputs['To Min'].default_value=1;shade.inputs['To Max'].default_value=.6;L.new(brown.outputs['Fac'],shade.inputs[0]);tint=N.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;L.new(exposure.outputs[0],tint.inputs[1]);L.new(shade.outputs[0],tint.inputs[2]);L.new(tint.outputs[0],color.inputs[1])
 mat['dink_generated_albedo_sha256']=sha(imagepath);mat['dink_generated_albedo_role']='Pastry Base Color ONLY; no BC-derived roughness/normal/height';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealPieV1_Source.blend'));assert sha(source)==pin
 (O/'reference_application.json').write_text(json.dumps({'passed':True,'input_source_sha256':pin,'output_source_sha256':sha(O/'PhotorealPieV1_Source.blend'),'reference_sha256':sha(imagepath),'reference_nominal_field_m':.08,'mapping':mapping,'synthetic_reference_RGB_multiplier':[.28,.20,.12],'independent_roughness_normal_grain':'Preserved; separately verified','generated_bitmap_role':'Pastry Base Color only; original fruit mask/dark fruit color preserved','native_imported':False},indent=2)+'\n')
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
