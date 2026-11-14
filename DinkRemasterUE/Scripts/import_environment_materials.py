"""Run inside UnrealEditor's Python commandlet via import_environment_materials.sh.

Photoreal pass environment materials (11 Nov 2026):
  /Game/Dink/Materials/Environment/M_Env_Terrain        master ground: four height-blended, world-aligned layers (mask RGB + remainder)
  /Game/Dink/Materials/Environment/MI_Env_Terrain_<L>   single-layer instances (dressed screens' meadow and earth)
  /Game/Dink/Materials/Environment/M_Env_Water          single-layer water (fitted ponds; needs depth behind it)
  /Game/Dink/Materials/Environment/M_Env_WaterFlat      opaque deep water for the 3 cm greybox water slabs
  /Game/Dink/Textures/Environment/T_Env_<L>_{BC,N,ORM,H,Macro}, T_Env_WaterNormal, T_Env_MaskLayerA, T_Env_MacroDefault
Layer catalogue: SourceAssets/Art/PhotorealPass/Environment/terrain_layers.json. The greybox importer
(DinkGreyboxAssets.cpp) instances M_Env_Terrain per screen; run this before Scripts/import_greybox.sh.
"""
import json
import os
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
ENV = ROOT / 'SourceAssets/Art/PhotorealPass/Environment'
TERRAIN = ROOT / 'SourceAssets/Art/PhotorealPass/Terrain'
SHARED = ROOT / 'SourceAssets/Art/SharedMaterials/Textures/1024'
MATS = '/Game/Dink/Materials/Environment'
TEX = '/Game/Dink/Textures/Environment'
ONLY_MATERIALS = os.environ.get('DINK_ENV_MATERIALS_ONLY') == '1'
LIB = unreal.EditorAssetLibrary
EDIT = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
ST = unreal.MaterialSamplerType
WRAP = unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS
CLAMP = unreal.SamplerSourceMode.SSM_CLAMP_WORLD_GROUP_SETTINGS

CATALOGUE = json.loads((ENV / 'terrain_layers.json').read_text())
terrain_manifest = json.loads((TERRAIN / 'manifest.json').read_text()) if (TERRAIN / 'manifest.json').exists() else {'sets': []}
TERRAIN_SETS = {s['name']: s for s in terrain_manifest['sets']}


def save(asset):
    if not LIB.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())


def import_texture(path, name, kind):
    """kind: BC, N, ORM, H, Macro, Mask."""
    path = Path(path)
    stamp = f'{path.stat().st_size}:{int(path.stat().st_mtime)}'
    existing = LIB.load_asset(TEX + '/' + name) if LIB.does_asset_exist(TEX + '/' + name) else None
    if existing is not None and (ONLY_MATERIALS or LIB.get_metadata_tag(existing, 'DinkEnvSource') == stamp):
        return existing
    task = unreal.AssetImportTask()
    task.filename = str(path.resolve())
    task.destination_path = TEX
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])
    tex = LIB.load_asset(TEX + '/' + name)
    if tex is None:
        raise RuntimeError('Import failed: ' + str(path))
    tex.set_editor_property('srgb', kind == 'BC')
    tex.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD)
    if kind == 'N':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel', True)  # sources are OpenGL (green up)
    elif kind == 'ORM':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
    elif kind == 'H':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_GRAYSCALE)
    elif kind in ('Macro', 'Mask', 'E'):
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
    if kind == 'Mask':
        tex.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
        tex.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
    LIB.set_metadata_tag(tex, 'DinkEnvSource', stamp)
    save(tex)
    return tex


def layer_sources(name, row):
    if row['source'] == 'terrain':
        s = TERRAIN_SETS.get(row['set'])
        if s is None:
            return None
        files = {k: TERRAIN / v for k, v in s['files'].items() if k in ('BC', 'N', 'ORM', 'H', 'Macro', 'E')}
        return files, float(s['tile_size_m']) * float(row.get('tile_scale', 1.0))
    files = {k: SHARED / f"T_Shared_{row['set']}_{k}.png" for k in ('BC', 'N', 'ORM', 'H')}
    return files, float(row['tile_m'])


def expr(mat, cls, x=0, y=0, **props):
    node = EDIT.create_material_expression(mat, cls, x, y)
    for key, value in props.items():
        node.set_editor_property(key, value)
    return node


def link(a, a_out, b, b_in):
    if not EDIT.connect_material_expressions(a, a_out, b, b_in):
        raise RuntimeError(f'cannot connect {a.get_name()}.{a_out} -> {b.get_name()}.{b_in}')


def out(node, pin, prop):
    if not EDIT.connect_material_property(node, pin, prop):
        raise RuntimeError(f'cannot connect {node.get_name()} to {prop}')


def custom(mat, x, y, code, output_type, inputs, description):
    node = expr(mat, unreal.MaterialExpressionCustom, x, y, code=code, output_type=output_type, description=description)
    pins = []
    for n in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', n)
        pins.append(pin)
    node.set_editor_property('inputs', pins)
    return node


def scalar_param(mat, name, value, x, y, group='Terrain'):
    return expr(mat, unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=float(value), group=group)


def vector_param(mat, name, rgb, x, y, group='Water'):
    return expr(mat, unreal.MaterialExpressionVectorParameter, x, y, parameter_name=name,
                default_value=unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0), group=group)


def tex_param(mat, name, texture, sampler, coords, x, y, source=WRAP):
    node = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, x, y, parameter_name=name, texture=texture,
                sampler_type=sampler, sampler_source=source, group='Layers')
    if coords is not None:
        link(coords, '', node, 'UVs')
    return node


def new_material(name):
    path = MATS + '/' + name
    mat = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if mat is None:
        mat = TOOLS.create_asset(name, MATS, unreal.Material, unreal.MaterialFactoryNew())
    # The library call skips nodes while it deletes (it mutates the list it iterates): repeat until empty,
    # otherwise stale nodes survive a rebuild (a second single-layer water output fails the compile).
    for _ in range(64):
        if EDIT.get_num_material_expressions(mat) == 0:
            break
        EDIT.delete_all_material_expressions(mat)
    return mat


F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
F2 = unreal.CustomMaterialOutputType.CMOT_FLOAT2
F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
F4 = unreal.CustomMaterialOutputType.CMOT_FLOAT4
LAYERS = 'ABCD'   # the mask's RGB weigh A, B, C; D takes what they leave

# ---------------------------------------------------------------------------------------------- textures
support = {
    'WaterNormal': import_texture(ENV / 'Textures/T_Env_WaterNormal.png', 'T_Env_WaterNormal', 'N'),
    'MaskLayerA': import_texture(ENV / 'Textures/T_Env_MaskLayerA.png', 'T_Env_MaskLayerA', 'Mask'),
    'MacroDefault': import_texture(ENV / 'Textures/T_Env_MacroDefault.png', 'T_Env_MacroDefault', 'Macro'),
    'Black': import_texture(ENV / 'Textures/T_Env_Black.png', 'T_Env_Black', 'E'),
}
layers = {}
for name, row in CATALOGUE['layers'].items():
    src = layer_sources(name, row)
    if src is None or not all(p.exists() for p in src[0].values()):
        unreal.log_warning(f'DINK ENV: layer {name} skipped (source set missing)')
        continue
    files, tile_m = src
    textures = {k: import_texture(p, f'T_Env_{name}_{k}', k) for k, p in files.items()}
    textures.setdefault('Macro', support['MacroDefault'])
    layers[name] = {'textures': textures, 'tile_cm': tile_m * 100.0, 'normal_strength': float(row.get('normal_strength', 1.0)),
                    'backlight': float(row.get('backlight', 0.0)), 'emissive': float(row.get('emissive', 0.0)),
                    'structured': 1.0 if row.get('structured') else 0.0,
                    'drift': 0.0 if row.get('structured') or row.get('drift') is False else 1.0}
if 'MeadowTurf' not in layers:
    raise RuntimeError('MeadowTurf layer is required as the default of M_Env_Terrain')

# ---------------------------------------------------------------------------------------------- terrain
BLACK = support['Black']
mat = new_material('M_Env_Terrain')
default = layers['MeadowTurf']
wp = expr(mat, unreal.MaterialExpressionWorldPosition, -2600, 0)
xy = expr(mat, unreal.MaterialExpressionComponentMask, -2450, 0, r=True, g=True, b=False, a=False)
link(wp, '', xy, '')
depth = expr(mat, unreal.MaterialExpressionPixelDepth, -2600, -300)
far_start = scalar_param(mat, 'FarStartCm', 900, -2600, -220)
far_range = scalar_param(mat, 'FarRangeCm', 2600, -2600, -140)
far_max = scalar_param(mat, 'FarBlendMax', 0.72, -2600, -60)
far = custom(mat, -2300, -220, 'return saturate((Depth - Start) / max(Range, 1.0)) * MaxBlend;', F1,
             ['Depth', 'Start', 'Range', 'MaxBlend'], 'Far blend')
for n, pin in ((depth, 'Depth'), (far_start, 'Start'), (far_range, 'Range'), (far_max, 'MaxBlend')):
    link(n, '', far, pin)
far_scale = scalar_param(mat, 'FarTileScale', 0.173, -2600, 120)
macro_scale = scalar_param(mat, 'MacroTileScale', 0.118, -2600, 200)
# Meso breakup: a slow world-space warp of the near UVs so tile rows never line up over a field.
warp_uv = expr(mat, unreal.MaterialExpressionMultiply, -2450, 320, const_b=1.0 / 2300.0)
link(xy, '', warp_uv, 'A')
warp_tex = expr(mat, unreal.MaterialExpressionTextureSample, -2300, 320, texture=support['MacroDefault'],
                sampler_type=ST.SAMPLERTYPE_MASKS, sampler_source=WRAP)
link(warp_uv, '', warp_tex, 'UVs')
warp_amount = scalar_param(mat, 'UVWarpCm', 55, -2300, 520)
warp = custom(mat, -2100, 320, 'return XY + (Noise.rg - 0.5) * 2.0 * Amount;', F2, ['XY', 'Noise', 'Amount'], 'Warped world XY')
link(xy, '', warp, 'XY'); link(warp_tex, 'RGB', warp, 'Noise'); link(warp_amount, '', warp, 'Amount')

S = {}
for i, L in enumerate(LAYERS):
    y = 700 + i * 1100
    tile = scalar_param(mat, f'Tile{L}Cm', default['tile_cm'], -2100, y, group='Layers')
    # Structured layers (boards, flagstones, cobbles, masonry, plaster): a laid pattern must stay straight and at one
    # scale, so the meso warp, the quarter-turned variant lookup and the far (5.8 x larger) lookup are off for them.
    structured = scalar_param(mat, f'Structured{L}', 0.0, -2100, y - 320, group='Layers')
    # Drift 0: the field-scale value drift and the dry, yellowed patches leave this layer alone (floors, snow, ice).
    drift = scalar_param(mat, f'Drift{L}', 1.0, -2100, y - 400, group='Layers')
    uv_src = custom(mat, -2050, y - 80, 'return lerp(W, XY, saturate(S));', F2, ['W', 'XY', 'S'], 'Warped or straight XY')
    link(warp, '', uv_src, 'W'); link(xy, '', uv_src, 'XY'); link(structured, '', uv_src, 'S')
    uv = expr(mat, unreal.MaterialExpressionDivide, -1950, y)
    link(uv_src, '', uv, 'A'); link(tile, '', uv, 'B')
    uv_plain = expr(mat, unreal.MaterialExpressionDivide, -1950, y + 80)
    link(xy, '', uv_plain, 'A'); link(tile, '', uv_plain, 'B')
    uv_far = expr(mat, unreal.MaterialExpressionMultiply, -1800, y + 80)
    link(uv_plain, '', uv_far, 'A'); link(far_scale, '', uv_far, 'B')
    # second, quarter-turned and rescaled lookup of the same tile: blended in by noise so no row of tiles lines up
    uv_var = custom(mat, -1800, y + 240, 'return UV.yx * 0.87 + float2(0.37, 0.61);', F2, ['UV'], 'Variant UV')
    link(uv_plain, '', uv_var, 'UV')
    uv_macro = expr(mat, unreal.MaterialExpressionMultiply, -1800, y + 160)
    link(uv_plain, '', uv_macro, 'A'); link(macro_scale, '', uv_macro, 'B')
    t = default['textures']
    S[L] = {
        'BC': tex_param(mat, f'BC{L}', t['BC'], ST.SAMPLERTYPE_COLOR, uv, -1600, y),
        'Far': tex_param(mat, f'BC{L}', t['BC'], ST.SAMPLERTYPE_COLOR, uv_far, -1600, y + 180),
        'Var': tex_param(mat, f'BC{L}', t['BC'], ST.SAMPLERTYPE_COLOR, uv_var, -1600, y + 270),
        'UV': uv_plain,
        'E': tex_param(mat, f'E{L}', BLACK, ST.SAMPLERTYPE_MASKS, uv, -1600, y + 990),
        'ES': scalar_param(mat, f'EmissiveStrength{L}', 0.0, -1600, y - 240, group='Layers'),
        'BL': scalar_param(mat, f'Backlight{L}', default['backlight'] if L == 'A' else 0.0, -1600, y - 160, group='Layers'),
        'N': tex_param(mat, f'N{L}', t['N'], ST.SAMPLERTYPE_NORMAL, uv, -1600, y + 360),
        'ORM': tex_param(mat, f'ORM{L}', t['ORM'], ST.SAMPLERTYPE_MASKS, uv, -1600, y + 540),
        'H': tex_param(mat, f'H{L}', t['H'], ST.SAMPLERTYPE_LINEAR_GRAYSCALE, uv, -1600, y + 720),
        'Macro': tex_param(mat, f'Macro{L}', t['Macro'], ST.SAMPLERTYPE_MASKS, uv_macro, -1600, y + 900),
        'NS': scalar_param(mat, f'NormalStrength{L}', default['normal_strength'], -1600, y - 80, group='Layers'),
        'St': structured, 'Dr': drift,
    }
structured4 = custom(mat, -1300, -1500, 'return saturate(float4(A, B, C, D));', F4, ['A', 'B', 'C', 'D'], 'Structured layers')
drift4 = custom(mat, -1300, -1600, 'return saturate(float4(A, B, C, D));', F4, ['A', 'B', 'C', 'D'], 'Drifting layers')
for L in LAYERS:
    link(S[L]['St'], '', structured4, L); link(S[L]['Dr'], '', drift4, L)
fine_uv = expr(mat, unreal.MaterialExpressionMultiply, -2450, -1000, const_b=1.0 / 700.0)
link(xy, '', fine_uv, 'A')
fine_tex = expr(mat, unreal.MaterialExpressionTextureSample, -2300, -1000, texture=support['MacroDefault'],
                sampler_type=ST.SAMPLERTYPE_MASKS, sampler_source=WRAP)
link(fine_uv, '', fine_tex, 'UVs')
wz = expr(mat, unreal.MaterialExpressionComponentMask, -2450, 80, r=False, g=False, b=True, a=False)
link(wp, '', wz, '')
tc = expr(mat, unreal.MaterialExpressionTextureCoordinate, -2100, -500)
mask_warp = scalar_param(mat, 'MaskWarp', 0.012, -2100, -420)
mask_uv = custom(mat, -1900, -500, 'return UV + (Noise.gb - 0.5) * 2.0 * Amount + (Fine.rg - 0.5) * 2.0 * FineAmount;', F2,
                 ['UV', 'Noise', 'Amount', 'Fine', 'FineAmount'], 'Warped mask UV')
link(fine_tex, 'RGB', mask_uv, 'Fine'); link(scalar_param(mat, 'MaskWarpFine', 0.007, -2100, -340), '', mask_uv, 'FineAmount')
link(tc, '', mask_uv, 'UV'); link(warp_tex, 'RGB', mask_uv, 'Noise'); link(mask_warp, '', mask_uv, 'Amount')
mask = tex_param(mat, 'LayerMask', support['MaskLayerA'], ST.SAMPLERTYPE_MASKS, mask_uv, -1600, -500, source=CLAMP)
blend_k = scalar_param(mat, 'HeightBlend', 0.55, -1300, -420)
blend_depth = scalar_param(mat, 'HeightBlendDepth', 0.12, -1300, -340)
weights = custom(mat, -1100, -500, '''
float4 w = float4(max(Mask, 0.0), 0.0);
// the fourth layer takes what the three mask channels leave (0 on a mask of up to three layers; the small
// rounding remainder of an 8-bit mask falls under the height blend's depth and never shows)
w.w = saturate(1.0 - (w.x + w.y + w.z));
if (Patch > 0.0)
{
    // procedural worn-ground mask (authored earth meshes): layer B grows in patches on level ground
    float n = Fine.g * 0.6 + Fine.b * 0.4;
    float p = saturate((n - (1.0 - Patch)) * 5.0) * saturate((Z + 14.0) / 10.0);
    // layer C (pond mud) takes over below the rim, with a noisy upper edge
    float mud = saturate((-Z - 6.0 - n * 14.0) / 12.0);
    w = float4((1.0 - p) * (1.0 - mud), p * (1.0 - mud), mud, 0.0);
}
w /= max(w.x + w.y + w.z + w.w, 1e-3);
float4 h = float4(HA, HB, HC, HD);
float4 v = saturate(w * 3.0) * (w + h * K);
float m = max(max(v.x, v.y), max(v.z, v.w)) - Depth;
float4 r = max(v - m, 0.0);
return r / max(r.x + r.y + r.z + r.w, 1e-4);''', F4, ['Mask', 'HA', 'HB', 'HC', 'HD', 'K', 'Depth', 'Patch', 'Fine', 'Z'], 'Height-blended layer weights')
link(scalar_param(mat, 'ProcPatch', 0.0, -1300, -580), '', weights, 'Patch'); link(fine_tex, 'RGB', weights, 'Fine'); link(wz, '', weights, 'Z')
link(mask, 'RGB', weights, 'Mask')
for L in LAYERS:
    link(S[L]['H'], 'R', weights, 'H' + L)
link(blend_k, '', weights, 'K'); link(blend_depth, '', weights, 'Depth')

# Wetness: below a waterline height (authored pond banks) and near the shore of the mask's alpha.
wet = custom(mat, -1100, -760, '''
float wz = saturate((WetZ - Z) / max(Range, 1.0));
float ws = Shore * smoothstep(0.74, 0.5, A);
return saturate(max(wz, ws));''', F1, ['Z', 'WetZ', 'Range', 'Shore', 'A'], 'Wetness')
link(wz, '', wet, 'Z'); link(scalar_param(mat, 'WetZ', -1000000.0, -1300, -840), '', wet, 'WetZ')
link(scalar_param(mat, 'WetRangeCm', 25.0, -1300, -760), '', wet, 'Range')
link(scalar_param(mat, 'ShoreWet', 1.0, -1300, -680), '', wet, 'Shore'); link(mask, 'A', wet, 'A')
# Foliage transmission: looking towards the sun, grass lights up instead of turning into a dark matte sheet.
cam = expr(mat, unreal.MaterialExpressionCameraVectorWS, -1300, -1000)
sun = expr(mat, unreal.MaterialExpressionSkyAtmosphereLightDirection, -1300, -920)
backlight = custom(mat, -1100, -960, 'return pow(saturate(dot(-normalize(Cam), normalize(Sun))), 3.0) * dot(float4(BA, BB, BC, BD), W);', F1,
                   ['Cam', 'Sun', 'BA', 'BB', 'BC', 'BD', 'W'], 'Backlight')
link(cam, '', backlight, 'Cam'); link(sun, '', backlight, 'Sun'); link(weights, '', backlight, 'W')
for L in LAYERS:
    link(S[L]['BL'], '', backlight, 'B' + L)
macro_strength = scalar_param(mat, 'MacroStrength', 0.4, -1300, -200)
# Field-scale variation (one repeat per 110 m): value drift and patches of drier, yellower ground.
big_uv = expr(mat, unreal.MaterialExpressionMultiply, -2450, -700, const_b=1.0 / 11000.0)
link(xy, '', big_uv, 'A')
big_tex = expr(mat, unreal.MaterialExpressionTextureSample, -2300, -700, texture=support['MacroDefault'],
               sampler_type=ST.SAMPLERTYPE_MASKS, sampler_source=WRAP)
link(big_uv, '', big_tex, 'UVs')
big_strength = scalar_param(mat, 'FieldVariation', 0.3, -2300, -900)
dry_amount = scalar_param(mat, 'FieldDryness', 0.3, -2300, -820)
color = custom(mat, -900, 0, '''
float vmix = smoothstep(0.35, 0.65, Fine.r);
float4 fr = 1.0 - St;   // 0 for a structured layer: one lookup, straight and at one scale
float3 ca = lerp(lerp(BCA, VA, vmix * fr.x), FA, Far * fr.x), cb = lerp(lerp(BCB, VB, vmix * fr.y), FB, Far * fr.y), cc = lerp(lerp(BCC, VC, vmix * fr.z), FC, Far * fr.z);
float3 cd = lerp(lerp(BCD, VD, vmix * fr.w), FD, Far * fr.w);
float loose = dot(W, Dr);   // field-scale drift and dry patches belong to open ground, not to a floor or to snow
float3 k = float3(0.5, 0.32, 0.18);
float4 m = float4(dot(MA, k), dot(MB, k), dot(MC, k), dot(MD, k)) * 2.0 - 1.0;
// value drift plus a slight warm/cool drift, strongest in the largest octave
float3 warm = float3(1.0, 0.9, 0.72);
ca *= 1.0 + Strength * m.x * warm; cb *= 1.0 + Strength * m.y * warm; cc *= 1.0 + Strength * m.z * warm; cd *= 1.0 + Strength * m.w * warm;
float3 c = max(ca * W.x + cb * W.y + cc * W.z + cd * W.w, 0.0);
c *= 1.0 + BigStrength * loose * (Big.r * 2.0 - 1.0);
float lum = dot(c, float3(0.3, 0.59, 0.11));
float dry = Dry * loose * smoothstep(0.45, 0.8, Big.g * 0.7 + Big.b * 0.3);
c = lerp(c, lum * float3(1.16, 1.04, 0.74), dry);
c *= 1.0 + BL * float3(0.85, 1.0, 0.4);
c *= lerp(1.0, 0.68, Wet);
c *= Tint;
if (HRange > 0.0) c = lerp(c, c * HTint, saturate(Z / HRange));
return c;''', F3,
               ['BCA', 'BCB', 'BCC', 'BCD', 'FA', 'FB', 'FC', 'FD', 'MA', 'MB', 'MC', 'MD', 'W', 'Far', 'Strength', 'Big', 'BigStrength', 'Dry',
                'VA', 'VB', 'VC', 'VD', 'Fine', 'BL', 'Wet', 'Tint', 'HTint', 'HRange', 'Z', 'St', 'Dr'], 'Layer colour')
link(structured4, '', color, 'St'); link(drift4, '', color, 'Dr')
link(fine_tex, 'RGB', color, 'Fine'); link(backlight, '', color, 'BL'); link(wet, '', color, 'Wet'); link(wz, '', color, 'Z')
link(vector_param(mat, 'Tint', (1.0, 1.0, 1.0), -1300, -1160, group='Terrain'), '', color, 'Tint')
link(vector_param(mat, 'HeightTint', (1.0, 1.0, 1.0), -1300, -1320, group='Terrain'), '', color, 'HTint')
link(scalar_param(mat, 'HeightTintRangeCm', 0.0, -1300, -1080), '', color, 'HRange')
for L in LAYERS:
    link(S[L]['Var'], 'RGB', color, 'V' + L)
link(big_tex, 'RGB', color, 'Big'); link(big_strength, '', color, 'BigStrength'); link(dry_amount, '', color, 'Dry')
for L in LAYERS:
    link(S[L]['BC'], 'RGB', color, 'BC' + L); link(S[L]['Far'], 'RGB', color, 'F' + L); link(S[L]['Macro'], 'RGB', color, 'M' + L)
link(weights, '', color, 'W'); link(far, '', color, 'Far'); link(macro_strength, '', color, 'Strength')
out(color, '', MP.MP_BASE_COLOR)

vnormal = expr(mat, unreal.MaterialExpressionVertexNormalWS, -1300, 400)
wp_rel = expr(mat, unreal.MaterialExpressionWorldPosition, -1300, 480,
              world_position_shader_offset=unreal.WorldPositionIncludedOffsets.WPT_CAMERA_RELATIVE)
normal = custom(mat, -900, 400, '''
float3 n = NA * float3(SA, SA, 1.0) * W.x + NB * float3(SB, SB, 1.0) * W.y + NC * float3(SC, SC, 1.0) * W.z + N4 * float3(S4, S4, 1.0) * W.w;
n.xy += ND.xy * DS * (1.0 - saturate(Depth / 450.0)) * (1.0 - dot(W, St));
n.xy *= (1.0 - Far * 0.55) * (1.0 - 0.5 * Wet);
n = normalize(n);
// Geometric normal from the surface itself: the authored pond banks carry unusable shading
// normals (they rendered black under any sun that was not behind them). Ground always faces up.
float3 g = cross(ddx(WP), ddy(WP));
float3 nv = dot(g, g) > 1e-12 ? normalize(g) : float3(0.0, 0.0, 1.0);
nv = nv.z < 0.0 ? -nv : nv;
float3 vn = dot(VN, VN) > 1e-4 ? normalize(VN) : nv;
nv = vn.z > 0.35 && dot(vn, nv) > 0.8 ? vn : nv;  // keep smooth vertex normals where they agree
float3 t = float3(1.0, 0.0, 0.0) - nv * nv.x;
t = dot(t, t) > 1e-4 ? normalize(t) : float3(0.0, 1.0, 0.0);
float3 b = cross(nv, t);
// world-aligned UVs: U = +X, V = +Y; green of the (DirectX-convention) sample points towards -V
return normalize(t * n.x - b * n.y + nv * n.z);''', F3, ['NA', 'NB', 'NC', 'N4', 'SA', 'SB', 'SC', 'S4', 'W', 'Far', 'VN', 'WP', 'ND', 'DS', 'Depth', 'Wet', 'St'], 'World normal')
link(structured4, '', normal, 'St')
# close-range detail normal: layer A's own normal map at 6.4x, faded out by 4.5 m
uv_detail = expr(mat, unreal.MaterialExpressionMultiply, -1800, 560, const_b=6.37)
link(S['A']['UV'], '', uv_detail, 'A')
detail = tex_param(mat, 'NA', default['textures']['N'], ST.SAMPLERTYPE_NORMAL, uv_detail, -1600, 560)
link(detail, 'RGB', normal, 'ND'); link(scalar_param(mat, 'DetailNormal', 0.55, -1300, 560), '', normal, 'DS')
link(depth, '', normal, 'Depth'); link(wet, '', normal, 'Wet')
link(wp_rel, '', normal, 'WP')
for L in LAYERS:
    pin = '4' if L == 'D' else L
    link(S[L]['N'], 'RGB', normal, 'N' + pin); link(S[L]['NS'], '', normal, 'S' + pin)
link(weights, '', normal, 'W'); link(far, '', normal, 'Far'); link(vnormal, '', normal, 'VN')
out(normal, '', MP.MP_NORMAL)

orm = custom(mat, -900, 800, '''
float3 o = OA * W.x + OB * W.y + OC * W.z + OD * W.w;
float m = dot(MA * W.x + MB * W.y + MC * W.z + MD * W.w, float3(0.2, 0.4, 0.4)) * 2.0 - 1.0;
// A flat plane has no blade-scale self shadowing: keep a floor on roughness so low-sun glare
// does not sheet across a field, and let it rise with distance (lost normal detail).
o.g = saturate(max(o.g, RoughMin) + m * RoughVar + Far * 0.08 - BL * 0.14);
o.g = lerp(o.g, 0.42, Wet * 0.85);
return o;''', F3, ['OA', 'OB', 'OC', 'OD', 'MA', 'MB', 'MC', 'MD', 'W', 'Far', 'RoughVar', 'RoughMin', 'BL', 'Wet'], 'AO / roughness')
link(backlight, '', orm, 'BL'); link(wet, '', orm, 'Wet')
link(scalar_param(mat, 'RoughnessFloor', 0.7, -1300, 980), '', orm, 'RoughMin')
rough_var = scalar_param(mat, 'MacroRoughness', 0.12, -1300, 900)
for L in LAYERS:
    link(S[L]['ORM'], 'RGB', orm, 'O' + L); link(S[L]['Macro'], 'RGB', orm, 'M' + L)
link(weights, '', orm, 'W'); link(far, '', orm, 'Far'); link(rough_var, '', orm, 'RoughVar')
ao = expr(mat, unreal.MaterialExpressionComponentMask, -650, 760, r=True, g=False, b=False, a=False)
rough = expr(mat, unreal.MaterialExpressionComponentMask, -650, 860, r=False, g=True, b=False, a=False)
link(orm, '', ao, ''); link(orm, '', rough, '')
out(ao, '', MP.MP_AMBIENT_OCCLUSION)
out(rough, '', MP.MP_ROUGHNESS)
spec = custom(mat, -650, 960, 'return lerp(0.2 * lerp(0.5, 1.0, AO), 0.3, Wet);', F1, ['AO', 'Wet'], 'Cavity specular')
link(ao, '', spec, 'AO'); link(wet, '', spec, 'Wet')
out(spec, '', MP.MP_SPECULAR)
# Emissive layers (lava crust): the set's E mask glows in the catalogue's lava colour.
lava = CATALOGUE.get('lava_colour', [1.0, 0.33, 0.07])
emissive = custom(mat, -900, 1200, f'return (EA.r * SA * W.x + EB.r * SB * W.y + EC.r * SC * W.z + ED.r * SD * W.w) * float3({lava[0]}, {lava[1]}, {lava[2]});', F3,
                  ['EA', 'EB', 'EC', 'ED', 'SA', 'SB', 'SC', 'SD', 'W'], 'Emissive')
for L in LAYERS:
    link(S[L]['E'], 'RGB', emissive, 'E' + L); link(S[L]['ES'], '', emissive, 'S' + L)
link(weights, '', emissive, 'W')
out(emissive, '', MP.MP_EMISSIVE_COLOR)
mat.set_editor_property('tangent_space_normal', False)
mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)
EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_NANITE, True)
EDIT.recompile_material(mat)
save(mat)
terrain = mat

report = {'layers': {}, 'materials': [MATS + '/M_Env_Terrain']}
for name, data in layers.items():
    mi_name = 'MI_Env_Terrain_' + name
    path = MATS + '/' + mi_name
    mi = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if mi is None:
        mi = TOOLS.create_asset(mi_name, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    EDIT.clear_all_material_instance_parameters(mi)
    EDIT.set_material_instance_parent(mi, terrain)
    for k in ('BC', 'N', 'ORM', 'H', 'Macro'):
        EDIT.set_material_instance_texture_parameter_value(mi, k + 'A', data['textures'][k])
    EDIT.set_material_instance_scalar_parameter_value(mi, 'TileACm', data['tile_cm'])
    EDIT.set_material_instance_scalar_parameter_value(mi, 'NormalStrengthA', data['normal_strength'])
    EDIT.set_material_instance_scalar_parameter_value(mi, 'BacklightA', data['backlight'])
    EDIT.set_material_instance_scalar_parameter_value(mi, 'StructuredA', data['structured'])
    EDIT.set_material_instance_scalar_parameter_value(mi, 'DriftA', data['drift'])
    if 'E' in data['textures']:
        EDIT.set_material_instance_texture_parameter_value(mi, 'EA', data['textures']['E'])
        EDIT.set_material_instance_scalar_parameter_value(mi, 'EmissiveStrengthA', data['emissive'])
    EDIT.update_material_instance(mi)
    save(mi)
    report['layers'][name] = {'tile_cm': data['tile_cm'], 'normal_strength': data['normal_strength'],
                              'macro': data['textures']['Macro'].get_name(), 'instance': path}

def terrain_instance(mi_name, layer_names, scalars=None, vectors=None):
    path = MATS + '/' + mi_name
    mi = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if mi is None:
        mi = TOOLS.create_asset(mi_name, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    EDIT.clear_all_material_instance_parameters(mi)
    EDIT.set_material_instance_parent(mi, terrain)
    for L, name in zip(LAYERS, layer_names):
        data = layers[name]
        for k in ('BC', 'N', 'ORM', 'H', 'Macro'):
            EDIT.set_material_instance_texture_parameter_value(mi, k + L, data['textures'][k])
        EDIT.set_material_instance_scalar_parameter_value(mi, f'Tile{L}Cm', data['tile_cm'])
        EDIT.set_material_instance_scalar_parameter_value(mi, 'NormalStrength' + L, data['normal_strength'])
        EDIT.set_material_instance_scalar_parameter_value(mi, 'Backlight' + L, data['backlight'])
        EDIT.set_material_instance_scalar_parameter_value(mi, 'Structured' + L, data['structured'])
        EDIT.set_material_instance_scalar_parameter_value(mi, 'Drift' + L, data['drift'])
    for k, v in (scalars or {}).items():
        EDIT.set_material_instance_scalar_parameter_value(mi, k, float(v))
    for k, v in (vectors or {}).items():
        EDIT.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
    EDIT.update_material_instance(mi)
    save(mi)
    report['materials'].append(path)

# Authored earth meshes (yard paths, pond rims and banks): worn earth with grass creeping in on level
# ground, so their polygon outlines break up, and a wet band towards the pond waterline (about z -62 cm).
if 'EarthPath' in layers:
    terrain_instance('MI_Env_Terrain_EarthWorn', ['EarthPath', 'MeadowTurf'] + (['PondMud'] if 'PondMud' in layers else []),
                     {'ProcPatch': 0.5, 'WetZ': -56.0, 'WetRangeCm': 12.0, 'HeightBlend': 0.7})
# Far skirt and hill ring: meadow that darkens to a wooded tone with height.
terrain_instance('MI_Env_Terrain_Backdrop', ['MeadowTurf'],
                 {'HeightTintRangeCm': 4500.0, 'FarBlendMax': 1.0, 'FieldVariation': 0.4, 'DetailNormal': 0.0},
                 {'HeightTint': (0.42, 0.56, 0.40)})

# Firelight flicker (light function): three incommensurate sines, never below 62 percent.
mat = new_material('M_Env_FireFlicker')
flicker = custom(mat, -400, 0, 'return 0.82 + 0.10 * sin(T * 11.3) + 0.05 * sin(T * 23.7 + 1.3) + 0.03 * sin(T * 5.1 + 0.4);', F1, ['T'], 'Flicker')
link(expr(mat, unreal.MaterialExpressionTime, -600, 0), '', flicker, 'T')
mat.set_editor_property('material_domain', unreal.MaterialDomain.MD_LIGHT_FUNCTION)
out(flicker, '', MP.MP_EMISSIVE_COLOR)
EDIT.recompile_material(mat)
save(mat)
report['materials'].append(MATS + '/M_Env_FireFlicker')

# Grass scatter placeholder: the scatter draws instanced meshes, which needs the instancing usage flag on the
# material. The authored tuft material is left untouched; a copy with the flag lives beside the environment set.
env_config = json.loads((ROOT / 'Content/Dink/Data/Environment/environment.json').read_text())
grass_mesh = LIB.load_asset(env_config['grass']['mesh'].split('.')[0]) if env_config.get('grass', {}).get('mesh') else None
if grass_mesh is not None and grass_mesh.static_materials:
    source = grass_mesh.static_materials[0].material_interface.get_base_material()
    copy_path = MATS + '/M_Env_GrassScatter'
    if LIB.does_asset_exist(copy_path):
        LIB.delete_asset(copy_path)
    copy = LIB.duplicate_asset(source.get_path_name().split('.')[0], copy_path)
    EDIT.set_base_material_usage(copy, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    EDIT.recompile_material(copy)
    save(copy)
    report['materials'].append(copy_path)

# ---------------------------------------------------------------------------------------------- water
def water_normal(mat):
    wp = expr(mat, unreal.MaterialExpressionWorldPosition, -1800, 0)
    xy = expr(mat, unreal.MaterialExpressionComponentMask, -1650, 0, r=True, g=True, b=False, a=False)
    link(wp, '', xy, '')
    speed = scalar_param(mat, 'WaveSpeed', 1.0, -1800, 200, group='Water')
    time = expr(mat, unreal.MaterialExpressionTime, -1800, 280)
    samples = []
    # (wavelength of one texture repeat in cm, drift cm/s x, y)
    for i, (scale, sx, sy) in enumerate(((430.0, 9.0, 4.0), (190.0, -5.0, 7.5), (1010.0, 3.5, -2.5))):
        uv = custom(mat, -1450, i * 220, f'return (XY + float2({sx}, {sy}) * T * Speed) / {scale};', F2, ['XY', 'T', 'Speed'], f'Ripple UV {i}')
        link(xy, '', uv, 'XY'); link(time, '', uv, 'T'); link(speed, '', uv, 'Speed')
        s = expr(mat, unreal.MaterialExpressionTextureSample, -1200, i * 220, texture=support['WaterNormal'],
                 sampler_type=ST.SAMPLERTYPE_NORMAL, sampler_source=WRAP)
        link(uv, '', s, 'UVs')
        samples.append(s)
    strength = scalar_param(mat, 'WaveStrength', 0.09, -1200, 700, group='Water')
    n = custom(mat, -900, 200, '''
float2 d = (N0.xy + N1.xy * 0.75 + N2.xy * 0.6) * Strength;
return normalize(float3(d.x, -d.y, 1.0));''', F3, ['N0', 'N1', 'N2', 'Strength'], 'World ripple normal')
    for i, s in enumerate(samples):
        link(s, 'RGB', n, f'N{i}')
    link(strength, '', n, 'Strength')
    return n

mat = new_material('M_Env_Water')
n = water_normal(mat)
out(n, '', MP.MP_NORMAL)
# Shore line: where the water column behind the surface is a few centimetres, a broken band of foam/scum.
behind = expr(mat, unreal.MaterialExpressionSceneDepthWithoutWater, -900, -500)
pixel = expr(mat, unreal.MaterialExpressionPixelDepth, -900, -420)
wxy = expr(mat, unreal.MaterialExpressionComponentMask, -900, -340, r=True, g=True, b=False, a=False)
link(expr(mat, unreal.MaterialExpressionWorldPosition, -1050, -340), '', wxy, '')
foam_uv = expr(mat, unreal.MaterialExpressionMultiply, -750, -340, const_b=1.0 / 260.0)
link(wxy, '', foam_uv, 'A')
foam_noise = expr(mat, unreal.MaterialExpressionTextureSample, -600, -340, texture=support['MacroDefault'],
                  sampler_type=ST.SAMPLERTYPE_MASKS, sampler_source=WRAP)
link(foam_uv, '', foam_noise, 'UVs')
foam = custom(mat, -400, -460, '''
float thick = max(Behind - Pixel, 0.0);
float band = 1.0 - saturate(thick / max(Width, 0.1));
float foam = saturate(band * band * smoothstep(0.3, 0.75, Noise.b * 0.6 + Noise.g * 0.4) * Amount);
// floating leaves and scum: drifting patches where the water is shallow, i.e. along the banks
float scum = (1.0 - saturate(thick / 55.0)) * smoothstep(0.52, 0.7, Scum.g * 0.65 + Scum.r * 0.35) * smoothstep(0.25, 0.6, Noise.b) * ScumAmount;
return min(saturate(max(foam, scum)), 0.99) + 2.0 * step(foam + 1e-4, scum);''', F1,
              ['Behind', 'Pixel', 'Width', 'Noise', 'Amount', 'Scum', 'ScumAmount'], 'Shore foam and scum (+2 = scum dominant)')
scum_uv = expr(mat, unreal.MaterialExpressionMultiply, -750, -240, const_b=1.0 / 1300.0)
link(wxy, '', scum_uv, 'A')
scum_noise = expr(mat, unreal.MaterialExpressionTextureSample, -600, -240, texture=support['MacroDefault'],
                  sampler_type=ST.SAMPLERTYPE_MASKS, sampler_source=WRAP)
link(scum_uv, '', scum_noise, 'UVs')
link(scum_noise, 'RGB', foam, 'Scum'); link(scalar_param(mat, 'ScumAmount', 0.8, -600, -720, group='Water'), '', foam, 'ScumAmount')
foam_packed = foam
foam = custom(mat, -300, -560, 'return frac(P);', F1, ['P'], 'Top layer coverage')
link(foam_packed, '', foam, 'P')
link(behind, '', foam_packed, 'Behind'); link(pixel, '', foam_packed, 'Pixel'); link(foam_noise, 'RGB', foam_packed, 'Noise')
link(scalar_param(mat, 'FoamWidthCm', 14.0, -600, -560, group='Water'), '', foam_packed, 'Width')
link(scalar_param(mat, 'FoamAmount', 0.3, -600, -640, group='Water'), '', foam_packed, 'Amount')
top_color = custom(mat, -200, -300, 'return P >= 2.0 ? float3(0.085, 0.11, 0.04) : float3(0.55, 0.57, 0.50);', F3, ['P'], 'Foam or scum colour')
link(foam_packed, '', top_color, 'P')
out(top_color, '', MP.MP_BASE_COLOR)
out(expr(mat, unreal.MaterialExpressionConstant, -400, -200, r=0.0), '', MP.MP_METALLIC)
out(expr(mat, unreal.MaterialExpressionConstant, -400, -120, r=0.255), '', MP.MP_SPECULAR)  # F0 0.02
water_rough = custom(mat, -200, -40, 'return lerp(Base, 0.6, Foam);', F1, ['Base', 'Foam'], 'Roughness')
link(scalar_param(mat, 'Roughness', 0.045, -400, -40, group='Water'), '', water_rough, 'Base'); link(foam, '', water_rough, 'Foam')
out(water_rough, '', MP.MP_ROUGHNESS)
# Opacity of single-layer water is the coverage of the top surface layer (here: foam) over the water
# volume; 1 would paint the whole pond with the base colour and hide the water body.
out(foam, '', MP.MP_OPACITY)
out(expr(mat, unreal.MaterialExpressionConstant, -400, 120, r=1.33), '', MP.MP_REFRACTION)
slw = expr(mat, unreal.MaterialExpressionSingleLayerWaterMaterialOutput, -100, 400)
# Coefficients are per centimetre of water path. A silty field pond: red dies first, green-brown scatter.
link(vector_param(mat, 'Scattering', (0.0100, 0.0110, 0.0050), -500, 400), '', slw, 'ScatteringCoefficients')
link(vector_param(mat, 'Absorption', (0.0450, 0.0300, 0.0500), -500, 560), '', slw, 'AbsorptionCoefficients')
link(expr(mat, unreal.MaterialExpressionConstant, -500, 720, r=0.2), '', slw, 'PhaseG')
link(expr(mat, unreal.MaterialExpressionConstant, -500, 800, r=1.0), '', slw, 'ColorScaleBehindWater')
mat.set_editor_property('tangent_space_normal', False)
mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)
mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
mat.set_editor_property('two_sided', False)
EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_NANITE, True)
EDIT.recompile_material(mat)
save(mat)
report['materials'].append(MATS + '/M_Env_Water')

# Greybox water with a terrain mask: single-layer water over the 3 cm slab. The mask's alpha (signed
# distance to the waterline) scales the extinction, so the slab is clear at the shore and deep-coloured
# two metres in; a ragged foam line sits on the waterline.
mat = new_material('M_Env_WaterShore')
n = water_normal(mat)
out(n, '', MP.MP_NORMAL)
wxy = expr(mat, unreal.MaterialExpressionComponentMask, -900, -340, r=True, g=True, b=False, a=False)
link(expr(mat, unreal.MaterialExpressionWorldPosition, -1050, -340), '', wxy, '')
shore_uv_noise = expr(mat, unreal.MaterialExpressionMultiply, -750, -340, const_b=1.0 / 330.0)
link(wxy, '', shore_uv_noise, 'A')
shore_noise = expr(mat, unreal.MaterialExpressionTextureSample, -600, -340, texture=support['MacroDefault'],
                   sampler_type=ST.SAMPLERTYPE_MASKS, sampler_source=WRAP)
link(shore_uv_noise, '', shore_noise, 'UVs')
shore_mask = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, -700, parameter_name='ShoreMask',
                  texture=support['MaskLayerA'], sampler_type=ST.SAMPLERTYPE_MASKS, sampler_source=CLAMP, group='Water')
shore = custom(mat, -350, -600, '''
// x: depth proxy 0 (waterline) .. 1 (2 m or more from land), y: foam, z: specular
float a = A + (Noise.g - 0.5) * 0.05;
float d = saturate((0.5 - a) * 2.0);
float k = d * d * (3.0 - 2.0 * d);
float foam = saturate((a - 0.465) / 0.03) * step(a, 0.502) * smoothstep(0.35, 0.8, Noise.g) * 0.22;
float scum = step(a, 0.5) * (1.0 - saturate(d / 0.4)) * smoothstep(0.55, 0.72, Noise.r * 0.5 + Noise.g * 0.5) * smoothstep(0.3, 0.6, Noise.b) * ScumAmount;
foam = max(foam, scum);
return float3(k, foam, lerp(0.04, 0.255, saturate((0.53 - a) * 20.0)));''', F3, ['A', 'Noise', 'ScumAmount'], 'Shore terms')
link(scalar_param(mat, 'ScumAmount', 0.8, -600, -860, group='Water'), '', shore, 'ScumAmount')
link(shore_mask, 'A', shore, 'A'); link(shore_noise, 'RGB', shore, 'Noise')
shore_top = custom(mat, -100, -700, 'return lerp(float3(0.55, 0.57, 0.50), float3(0.085, 0.11, 0.04), saturate(ScumAmount));', F3, ['ScumAmount'], 'Top colour')
link(scalar_param(mat, 'ScumAmount', 0.8, -300, -780, group='Water'), '', shore_top, 'ScumAmount')
out(shore_top, '', MP.MP_BASE_COLOR)
out(expr(mat, unreal.MaterialExpressionConstant, -400, -200, r=0.0), '', MP.MP_METALLIC)
shore_spec = expr(mat, unreal.MaterialExpressionComponentMask, -100, -520, r=False, g=False, b=True, a=False)
link(shore, '', shore_spec, '')
out(shore_spec, '', MP.MP_SPECULAR)
shore_rough = custom(mat, -100, -420, 'return lerp(Base, 0.6, S.y);', F1, ['Base', 'S'], 'Roughness')
link(scalar_param(mat, 'Roughness', 0.05, -400, -40, group='Water'), '', shore_rough, 'Base'); link(shore, '', shore_rough, 'S')
out(shore_rough, '', MP.MP_ROUGHNESS)
shore_foam = expr(mat, unreal.MaterialExpressionComponentMask, -100, -340, r=False, g=True, b=False, a=False)
link(shore, '', shore_foam, '')
out(shore_foam, '', MP.MP_OPACITY)
slw = expr(mat, unreal.MaterialExpressionSingleLayerWaterMaterialOutput, -100, 400)
# per centimetre through a 3 cm slab: the full value is opaque deep water, scaled down to nothing at the shore
shore_scatter = custom(mat, -300, 400, 'return C.rgb * S.x;', F3, ['C', 'S'], 'Scattering')
shore_absorb = custom(mat, -300, 560, 'return C.rgb * S.x;', F3, ['C', 'S'], 'Absorption')
link(vector_param(mat, 'Scattering', (0.110, 0.120, 0.055), -500, 400), '', shore_scatter, 'C'); link(shore, '', shore_scatter, 'S')
link(vector_param(mat, 'Absorption', (0.50, 0.33, 0.55), -500, 560), '', shore_absorb, 'C'); link(shore, '', shore_absorb, 'S')
link(shore_scatter, '', slw, 'ScatteringCoefficients')
link(shore_absorb, '', slw, 'AbsorptionCoefficients')
link(expr(mat, unreal.MaterialExpressionConstant, -500, 720, r=0.2), '', slw, 'PhaseG')
link(expr(mat, unreal.MaterialExpressionConstant, -500, 800, r=1.0), '', slw, 'ColorScaleBehindWater')
mat.set_editor_property('tangent_space_normal', False)
mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)
mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
EDIT.recompile_material(mat)
save(mat)
report['materials'].append(MATS + '/M_Env_WaterShore')

mat = new_material('M_Env_WaterFlat')
n = water_normal(mat)
out(n, '', MP.MP_NORMAL)
# No geometry lies under the greybox slabs, so depth cannot be measured: shade as deep water
# (dark body colour; the picture is the Fresnel sky reflection from Lumen).
out(vector_param(mat, 'DeepColor', (0.010, 0.030, 0.036), -400, -300), '', MP.MP_BASE_COLOR)
out(expr(mat, unreal.MaterialExpressionConstant, -400, -200, r=0.0), '', MP.MP_METALLIC)
out(expr(mat, unreal.MaterialExpressionConstant, -400, -120, r=0.255), '', MP.MP_SPECULAR)
out(scalar_param(mat, 'Roughness', 0.05, -400, -40, group='Water'), '', MP.MP_ROUGHNESS)
mat.set_editor_property('tangent_space_normal', False)
mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)
EDIT.recompile_material(mat)
save(mat)
report['materials'].append(MATS + '/M_Env_WaterFlat')

dest = ROOT / 'Saved/PhotorealPass/lighting/environment_materials.json'
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(report, indent=2))
unreal.log(f"DINK ENV IMPORT OK: {len(layers)} terrain layers, {len(report['materials'])} materials; report {dest}")
