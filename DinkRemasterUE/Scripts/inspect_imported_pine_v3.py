"""Read back actual pine mesh/material/mip contracts; no asset mutations."""
import unreal,json
from pathlib import Path
assert '-game' not in unreal.SystemLibrary.get_command_line().split(), 'Editor-only readback cannot run in a game session'
ROOT=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
mesh=unreal.load_asset('/Game/Dink/Foliage/StonebrookFields/Refinements/SM_Pine_Stonebrook_V3')
assert isinstance(mesh,unreal.StaticMesh)
nanite_enabled=bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled'))
assert not nanite_enabled, 'Pine uses authored classic LODs; Nanite must be disabled'
editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem)
assert editor.get_lod_count(mesh)==3
assert editor.get_convex_collision_count(mesh)==1
assert mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')==unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX
bounds=mesh.get_bounds().box_extent
expected=[5.780095100402832*100,5.865981578826904*100,1300]
actual=[bounds.x*2,bounds.y*2,bounds.z*2];assert all(abs(a-b)<1 for a,b in zip(actual,expected)),actual
slots=mesh.get_editor_property('static_materials');assert len(slots)==2
mat=unreal.load_asset('/Game/Dink/Materials/StonebrookFields/MI_PineV3_Sprays');assert mat.get_editor_property('blend_mode')==unreal.BlendMode.BLEND_MASKED
assert mat.get_editor_property('two_sided') and abs(mat.get_editor_property('opacity_mask_clip_value')-.12)<1e-6
node=unreal.MaterialEditingLibrary.get_material_property_input_node(mat,unreal.MaterialProperty.MP_OPACITY_MASK)
assert isinstance(node,unreal.MaterialExpressionTextureSample)
tex=node.get_editor_property('texture');assert tex.get_name()=='T_PineV3_Sprays_BC'
assert tex.get_editor_property('srgb') and not tex.get_editor_property('compression_no_alpha')
assert tex.get_editor_property('do_scale_mips_for_alpha_coverage')
coverage=tex.get_editor_property('alpha_coverage_thresholds');assert abs(coverage.w-.12)<1e-6
for suffix,compression in [('N',unreal.TextureCompressionSettings.TC_NORMALMAP),('ORM',unreal.TextureCompressionSettings.TC_MASKS)]:
 t=unreal.load_asset('/Game/Dink/Textures/StonebrookFields/T_PineV3_Sprays_'+suffix)
 assert not t.get_editor_property('srgb') and t.get_editor_property('compression_settings')==compression
report={'mesh':mesh.get_path_name(),'lods':3,'nanite_enabled':nanite_enabled,'convex_colliders':1,'size_cm':actual,'materials':[s.get_editor_property('material_interface').get_path_name() for s in slots],'masked_two_sided':True,'alpha_clip':mat.get_editor_property('opacity_mask_clip_value'),'mask_input_texture':tex.get_path_name(),'compression_keeps_alpha':True,'mip_alpha_coverage_enabled':True,'mip_alpha_threshold':coverage.w,'normal_and_orm_color_space_verified':True,'mutations':0}
out=ROOT/'Saved/Art/pine_v3_import_readback.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');unreal.log('PINE V3 READBACK PASS '+json.dumps(report))
