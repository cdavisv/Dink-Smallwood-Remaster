"""World life (stream world-alive, 15 Nov 2026): the assets UDinkWorldLifeSubsystem reads, built in the editor.

    Scripts/import_world_life.sh            (runs this file in UnrealEditor-Cmd -run=pythonscript)

Builds /Game/Dink/WorldLife:
  MPC_Dink_World      shared wind and walk-through pushers (Scripts/world_life_wind.py lists the parameters)
  M_WorldLife_Lit     lit translucent particle plane (dust, smoke, debris chips, ripples): colour, opacity, shape and
                      seed from the six per-instance custom floats UDinkWorldLifeSubsystem writes (r, g, b, opacity,
                      shape 0 puff / 1 ring / 2 chip, seed), soft against the ground (depth fade)
  M_WorldLife_Glow    additive unlit plane (embers, sparks, fireball glow, pollen): same six floats, shape 0 dot / 1 streak
Then, unless DINK_WORLD_LIFE_SKIP_VEG=1, rebuilds the vegetation parents M_Veg_Foliage / M_Veg_Bark with the shared wind
node by running Scripts/import_photoreal_art.py with DINK_PHOTOREAL_ONLY=vegetation and DINK_PHOTOREAL_FROZEN=1 (meshes
and textures are kept exactly as imported; only the materials are rebuilt).
Prints `DINK WORLD LIFE IMPORT OK: ...` at the end.
"""
import os
import runpy
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world_life_wind  # noqa: E402

LIB = unreal.EditorAssetLibrary
EDIT = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
FOLDER = '/Game/Dink/WorldLife'


def save(asset):
    LIB.save_loaded_asset(asset, only_if_is_dirty=False)


def expr(mat, cls, x=0, y=0, **props):
    node = EDIT.create_material_expression(mat, cls, x, y)
    for key, value in props.items():
        node.set_editor_property(key, value)
    return node


def link(a, a_out, b, b_in):
    if not EDIT.connect_material_expressions(a, a_out, b, b_in):
        raise RuntimeError(f'cannot connect {a.get_name()}.{a_out} -> {b.get_name()}.{b_in}')


def link_any(a, a_out, b, names):
    for n in names:
        if EDIT.connect_material_expressions(a, a_out, b, n):
            return
    raise RuntimeError(f'cannot connect {a.get_name()}.{a_out} -> {b.get_name()} {names}')


def out(node, pin, prop):
    if not EDIT.connect_material_property(node, pin, prop):
        raise RuntimeError(f'cannot connect {node.get_name()}.{pin} -> {prop}')


def custom(mat, x, y, code, output_type, inputs, description):
    node = expr(mat, unreal.MaterialExpressionCustom, x, y, code=code, output_type=output_type, description=description)
    pins = []
    for n in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', n)
        pins.append(pin)
    node.set_editor_property('inputs', pins)
    return node


def new_material(name):
    path = FOLDER + '/' + name
    mat = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if mat is None:
        mat = TOOLS.create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    for _ in range(64):
        if EDIT.get_num_material_expressions(mat) == 0:
            break
        EDIT.delete_all_material_expressions(mat)
    return mat


def instance_floats(mat):
    nodes = []
    for i in range(6):
        nodes.append(expr(mat, unreal.MaterialExpressionPerInstanceCustomData, -900, 100 * i, data_index=i, const_default_value=0.0))
    return nodes


F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1

LIT_SHAPE = '''
float2 c = UV * 2.0 - 1.0;
float r = length(c);
float a = 0.0;
if (Shape < 0.5)
{
    // soft puff with a lumpy rim (a different rim per particle)
    float ang = atan2(c.y, c.x);
    float n = 0.12 * sin(ang * 3.0 + Seed * 20.0) + 0.07 * sin(ang * 7.0 + Seed * 41.0) + 0.04 * sin(ang * 13.0 + Seed * 7.0);
    a = 1.0 - smoothstep(0.25 + n, 0.95 + n * 0.5, r);
    a *= a;
}
else if (Shape < 1.5)
{
    // a thin ring (ripples), soft both sides
    a = exp(-pow((r - 0.72) / 0.085, 2.0)) * saturate((1.0 - r) * 6.0);
}
else
{
    // a chip / splinter: an irregular quad, hard edged
    float2 q = abs(c);
    float e = max(q.x, q.y * 0.9) + 0.12 * sin(Seed * 50.0 + c.x * 9.0 + c.y * 5.0);
    a = e < 0.8 ? 1.0 : 0.0;
}
return saturate(a) * saturate(Alpha);'''

GLOW_SHAPE = '''
float2 c = UV * 2.0 - 1.0;
float a = Shape < 0.5 ? exp(-dot(c, c) * 4.5) : exp(-c.y * c.y * 10.0) * saturate(1.0 - abs(c.x)) * saturate(1.0 - abs(c.x));
return a * max(Alpha, 0.0);'''


def build_lit():
    mat = new_material('M_WorldLife_Lit')
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('translucency_lighting_mode', unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
    f = instance_floats(mat)
    colour = expr(mat, unreal.MaterialExpressionAppendVector, -600, 0)
    rg = expr(mat, unreal.MaterialExpressionAppendVector, -750, 0)
    link(f[0], '', rg, 'A'); link(f[1], '', rg, 'B')
    link(rg, '', colour, 'A'); link(f[2], '', colour, 'B')
    out(colour, '', MP.MP_BASE_COLOR)
    out(expr(mat, unreal.MaterialExpressionConstant, -400, 120, r=0.9), '', MP.MP_ROUGHNESS)
    shape = custom(mat, -500, 300, LIT_SHAPE, F1, ['UV', 'Alpha', 'Shape', 'Seed'], 'World life particle opacity by shape')
    link(expr(mat, unreal.MaterialExpressionTextureCoordinate, -800, 650), '', shape, 'UV')
    link(f[3], '', shape, 'Alpha'); link(f[4], '', shape, 'Shape'); link(f[5], '', shape, 'Seed')
    fade = expr(mat, unreal.MaterialExpressionDepthFade, -250, 300, fade_distance_default=30.0)
    link_any(shape, '', fade, ['Opacity', 'InOpacity'])
    out(fade, '', MP.MP_OPACITY)
    EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    EDIT.recompile_material(mat)
    save(mat)
    return mat


def build_glow():
    mat = new_material('M_WorldLife_Glow')
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    f = instance_floats(mat)
    rg = expr(mat, unreal.MaterialExpressionAppendVector, -750, 0)
    colour = expr(mat, unreal.MaterialExpressionAppendVector, -600, 0)
    link(f[0], '', rg, 'A'); link(f[1], '', rg, 'B')
    link(rg, '', colour, 'A'); link(f[2], '', colour, 'B')
    shape = custom(mat, -500, 300, GLOW_SHAPE, F1, ['UV', 'Alpha', 'Shape'], 'World life glow by shape')
    link(expr(mat, unreal.MaterialExpressionTextureCoordinate, -800, 650), '', shape, 'UV')
    link(f[3], '', shape, 'Alpha'); link(f[4], '', shape, 'Shape')
    fade = expr(mat, unreal.MaterialExpressionDepthFade, -350, 450, fade_distance_default=15.0)
    link_any(shape, '', fade, ['Opacity', 'InOpacity'])
    mul = expr(mat, unreal.MaterialExpressionMultiply, -200, 100)
    link(colour, '', mul, 'A'); link(fade, '', mul, 'B')
    out(mul, '', MP.MP_EMISSIVE_COLOR)
    EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    EDIT.recompile_material(mat)
    save(mat)
    return mat


mpc = world_life_wind.ensure_world_mpc(unreal, save)
lit = build_lit()
glow = build_glow()
done = [mpc.get_path_name(), lit.get_path_name(), glow.get_path_name()]
if os.environ.get('DINK_WORLD_LIFE_SKIP_VEG') != '1':
    os.environ['DINK_PHOTOREAL_ONLY'] = 'vegetation'
    os.environ['DINK_PHOTOREAL_FROZEN'] = '1'
    runpy.run_path(os.path.join(HERE, 'import_photoreal_art.py'), run_name='__main__')
    done += ['/Game/Dink/Photoreal/Vegetation/M_Veg_Foliage', '/Game/Dink/Photoreal/Vegetation/M_Veg_Bark']
unreal.log('DINK WORLD LIFE IMPORT OK: ' + ', '.join(done))
