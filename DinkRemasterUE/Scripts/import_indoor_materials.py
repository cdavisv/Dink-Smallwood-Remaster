"""Run inside UnrealEditor's Python commandlet via import_indoor_materials.sh.

Builds the two presentation materials UDinkEnvironmentSubsystem's indoor set uses (environment.json `indoor`):
  M_Env_SpriteLit  the greybox sprite card lit by the scene (masked, two-sided foliage so a card lit from behind is
                   not black); texture parameter `Tex`, the same name as the importer's unlit M_DinkSprite.
  M_Env_Flame      a small procedural flame for cards at lamps and torches (unlit, additive, two-sided): teardrop
                   with a travelling wobble, white-yellow core, orange mantle, blue foot. U runs up the flame.
Re-runnable; nothing else is touched."""
import unreal

FOLDER = '/Game/Dink/Photoreal/WallKits'
LIB = unreal.EditorAssetLibrary
EDIT = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty


def fresh(name):
    path = FOLDER + '/' + name
    mat = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if mat is None:
        mat = TOOLS.create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    for _ in range(64):
        if EDIT.get_num_material_expressions(mat) == 0:
            break
        EDIT.delete_all_material_expressions(mat)
    return mat


def expr(mat, cls, x, y, **props):
    node = EDIT.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        node.set_editor_property(k, v)
    return node


def custom(mat, x, y, code, output_type, inputs):
    node = expr(mat, unreal.MaterialExpressionCustom, x, y, code=code, output_type=output_type)
    pins = []
    for n in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', n)
        pins.append(pin)
    node.set_editor_property('inputs', pins)
    return node


# --- lit sprite card
mat = fresh('M_Env_SpriteLit')
tex = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, 0, parameter_name='Tex',
           texture=unreal.load_asset('/Engine/EngineResources/DefaultTexture'), sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
half = expr(mat, unreal.MaterialExpressionMultiply, -300, 200, const_b=0.35)
EDIT.connect_material_expressions(tex, 'RGB', half, 'A')
EDIT.connect_material_property(tex, 'RGB', MP.MP_BASE_COLOR)
EDIT.connect_material_property(tex, 'A', MP.MP_OPACITY_MASK)
EDIT.connect_material_property(half, '', MP.MP_SUBSURFACE_COLOR)
EDIT.connect_material_property(expr(mat, unreal.MaterialExpressionConstant, -300, 350, r=0.9), '', MP.MP_ROUGHNESS)
EDIT.connect_material_property(expr(mat, unreal.MaterialExpressionConstant, -300, 430, r=0.08), '', MP.MP_SPECULAR)
mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
mat.set_editor_property('two_sided', True)
mat.set_editor_property('opacity_mask_clip_value', 0.5)
EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
EDIT.recompile_material(mat)
LIB.save_loaded_asset(mat, only_if_is_dirty=False)

# --- flame
mat = fresh('M_Env_Flame')
uv = expr(mat, unreal.MaterialExpressionTextureCoordinate, -900, 0)
time = expr(mat, unreal.MaterialExpressionTime, -900, 150)
pos = expr(mat, unreal.MaterialExpressionObjectPositionWS, -900, 300)
gain = expr(mat, unreal.MaterialExpressionScalarParameter, -900, 450, parameter_name='Intensity', default_value=6.0)
flame = custom(mat, -400, 0, '''
float h = saturate(UV.x);
float x = (UV.y - 0.5) * 2.0;
float t = T * 7.0 + frac(dot(Pos.xy, float2(0.0131, 0.0173))) * 6.2832;
float wob = (sin(h * 8.0 - t * 1.7) * 0.11 + sin(h * 19.0 - t * 3.1) * 0.05) * h * h;
float breathe = 1.0 + 0.08 * sin(t * 0.9) + 0.05 * sin(t * 2.3);
float w = 0.46 * pow(saturate(sin(3.14159 * pow(saturate(h / breathe), 0.6))), 1.25) * (1.0 - 0.3 * h);
float d = abs(x - wob) / max(w, 0.0005);
float body = saturate(1.0 - d);
float a = smoothstep(0.0, 0.55, body) * step(h, breathe);
float core = pow(body, 2.2) * saturate(1.4 - h * 1.1);
float3 c = lerp(float3(1.0, 0.33, 0.04), float3(1.0, 0.82, 0.42), saturate(core * 1.6));
c = lerp(c, float3(0.15, 0.3, 1.0), saturate(1.0 - h * 9.0) * 0.6);
return c * a * a * Gain;''', unreal.CustomMaterialOutputType.CMOT_FLOAT3, ['UV', 'T', 'Pos', 'Gain'])
EDIT.connect_material_expressions(uv, '', flame, 'UV')
EDIT.connect_material_expressions(time, '', flame, 'T')
EDIT.connect_material_expressions(pos, '', flame, 'Pos')
EDIT.connect_material_expressions(gain, '', flame, 'Gain')
EDIT.connect_material_property(flame, '', MP.MP_EMISSIVE_COLOR)
mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property('two_sided', True)
EDIT.recompile_material(mat)
LIB.save_loaded_asset(mat, only_if_is_dirty=False)
unreal.log('DINK INDOOR MATERIALS OK: M_Env_SpriteLit, M_Env_Flame in ' + FOLDER)
