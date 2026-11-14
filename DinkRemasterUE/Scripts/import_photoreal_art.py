"""Run inside UnrealEditor's Python commandlet via import_photoreal_art.sh.

Imports the photoreal pass deliveries into /Game/Dink/Photoreal (re-runnable; re-exports from the art
agents are picked up by file size and time):
  Vegetation   SourceAssets/Art/PhotorealPass/Vegetation/manifest.json   -> /Game/Dink/Photoreal/Vegetation
  Scatter      SourceAssets/Art/PhotorealPass/Terrain/manifest.json (scatter_meshes, the names in SCATTER_ALLOW)
                                                                          -> /Game/Dink/Photoreal/Scatter
  Walls        SourceAssets/Art/PhotorealPass/WallKits/manifest.json (the names in WALL_ALLOW) -> /Game/Dink/Photoreal/WallKits
  Hero         SourceAssets/Art/PhotorealPass/Characters/Dink/manifest.json -> /Game/Dink/Photoreal/Characters/Dink
DINK_PHOTOREAL_ONLY=vegetation,scatter,hero limits the run. Report: Saved/PhotorealPass/import_photoreal.json.
"""
import json
import math
import os
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
PASS = ROOT / 'SourceAssets/Art/PhotorealPass'
BASE = '/Game/Dink/Photoreal'
ONLY = {s.strip() for s in os.environ.get('DINK_PHOTOREAL_ONLY', 'vegetation,scatter,hero,walls').split(',') if s.strip()}
WALL_ALLOW = {'SM_Wall_Dungeon_Straight_A', 'SM_Wall_Dungeon_Straight_B', 'SM_Wall_Dungeon_Half', 'SM_Wall_Dungeon_Curve', 'SM_Wall_Dungeon_Arch',
              'SM_Wall_Plaster_Straight_A', 'SM_Wall_Plaster_Straight_B', 'SM_Wall_Plaster_CornerPost_L', 'SM_Wall_Plaster_CornerPost_R',
              'SM_Wall_Plaster_End_L', 'SM_Wall_Plaster_End_R', 'SM_Wall_Plaster_DoorJamb_L', 'SM_Wall_Plaster_DoorJamb_R', 'SM_Wall_Plaster_DoorHeader'}
SCATTER_ALLOW = {'SM_BeachPebbles_A', 'SM_BeachPebbles_B', 'SM_BeachPebbles_C', 'SM_BeachPebbles_D',
                 'SM_Pebbles_A', 'SM_Pebbles_B', 'SM_Pebbles_C'}
LIB = unreal.EditorAssetLibrary
EDIT = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
ST = unreal.MaterialSamplerType
F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
MESHES = (unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem))
try:
    IMPORT_CAPS = {str(k): int(v) for k, v in json.loads((ROOT / 'Content/Dink/Data/Art/texture_import_caps.json').read_text()).get('caps', {}).items()}
except (OSError, ValueError):
    IMPORT_CAPS = {}
report = {'vegetation': [], 'scatter': [], 'walls': [], 'hero': {}, 'warnings': []}  # 'pillbug' is added by its section
FROZEN = False  # set while a source export is newer than its manifest
FORCE = os.environ.get('DINK_PHOTOREAL_FORCE') == '1'  # re-import static meshes even when the source is unchanged


def warn(text):
    report['warnings'].append(text)
    unreal.log_warning('DINK PHOTOREAL: ' + text)


def save(asset):
    if not LIB.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())


def stamp_of(path):
    path = Path(path)
    return f'{path.stat().st_size}:{int(path.stat().st_mtime)}'


def import_texture(path, folder, kind, wrap=True, max_size=0):
    """kind: BC, BCA (colour with alpha coverage), N, ORM, SSS."""
    path = Path(path)
    name = path.stem
    target = folder + '/' + name
    existing = LIB.load_asset(target) if LIB.does_asset_exist(target) else None
    if existing is not None and (FROZEN or LIB.get_metadata_tag(existing, 'DinkSource') == stamp_of(path)):
        return existing
    task = unreal.AssetImportTask()
    task.filename = str(path.resolve())
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])
    tex = LIB.load_asset(target)
    if tex is None:
        raise RuntimeError('Texture import failed: ' + str(path))
    tex.set_editor_property('srgb', kind in ('BC', 'BCA', 'SSS'))
    if kind == 'N':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel', True)  # sources are OpenGL (green up)
    elif kind == 'ORM':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
    elif kind == 'BCA':
        tex.set_editor_property('compression_no_alpha', False)
        tex.set_editor_property('do_scale_mips_for_alpha_coverage', True)
        tex.set_editor_property('alpha_coverage_thresholds', unreal.Vector4(0.0, 0.0, 0.0, 0.33))
    if max_size:
        tex.set_editor_property('max_texture_size', int(max_size))
    if not wrap:
        tex.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
        tex.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
    LIB.set_metadata_tag(tex, 'DinkSource', stamp_of(path))
    save(tex)
    return tex


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


def new_material(folder, name):
    path = folder + '/' + name
    mat = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if mat is None:
        mat = TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    for _ in range(64):  # the library call skips nodes while deleting: repeat until empty
        if EDIT.get_num_material_expressions(mat) == 0:
            break
        EDIT.delete_all_material_expressions(mat)
    return mat


def instance(folder, name, parent, textures=None, scalars=None):
    path = folder + '/' + name
    mi = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if mi is None:
        mi = TOOLS.create_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    EDIT.clear_all_material_instance_parameters(mi)
    EDIT.set_material_instance_parent(mi, parent)
    for k, v in (textures or {}).items():
        EDIT.set_material_instance_texture_parameter_value(mi, k, v)
    for k, v in (scalars or {}).items():
        EDIT.set_material_instance_scalar_parameter_value(mi, k, float(v))
    EDIT.update_material_instance(mi)
    save(mi)
    return mi


def surface_material(folder, name, defaults, foliage=False, wind=None, skeletal=False, shading='lit', two_sided=False, masked=False, profile=None,
                     scatter=False, blend=None, blend_channel='r', ground_blend=False, timber=False, morph=False, vertex_tint=False):
    """One parent material: BC/N/ORM (+SSS) texture parameters, optional alpha mask, optional wind offset."""
    mat = new_material(folder, name)
    bc = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -700, -300, parameter_name='BC', texture=defaults['BC'], sampler_type=ST.SAMPLERTYPE_COLOR)
    nm = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -700, 0, parameter_name='N', texture=defaults['N'], sampler_type=ST.SAMPLERTYPE_NORMAL)
    orm = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -700, 300, parameter_name='ORM', texture=defaults['ORM'], sampler_type=ST.SAMPLERTYPE_MASKS)
    tint_param = expr(mat, unreal.MaterialExpressionVectorParameter, -700, -1100, parameter_name='Tint', default_value=unreal.LinearColor(1, 1, 1, 1))
    base = expr(mat, unreal.MaterialExpressionMultiply, -550, -300)
    link(bc, 'RGB', base, 'A'); link(tint_param, '', base, 'B')
    base_pin = ''
    if vertex_tint:
        # per-card tint painted into the mesh (the duck's feather cards: cream staining, belly soil, value jitter)
        vtint = expr(mat, unreal.MaterialExpressionVertexColor, -700, -1250)
        tinted = expr(mat, unreal.MaterialExpressionMultiply, -500, -450)
        link(base, '', tinted, 'A'); link(vtint, '', tinted, 'B')
        base = tinted
    bc_rgb = base
    if ground_blend:
        # UVMask (second UV channel): U = 1 at the ground, 0 from 0.9 m up. Soil and moss darken the foot of the
        # trunk so it sits in the ground; GroundBlend 0 turns it off (meshes without the channel must leave it 0).
        uv1 = expr(mat, unreal.MaterialExpressionTextureCoordinate, -1000, -1300, coordinate_index=1)
        amount = expr(mat, unreal.MaterialExpressionScalarParameter, -1000, -1220, parameter_name='GroundBlend', default_value=0.0)
        # Soil: the mean terrain colour under the tree. The family layer writes it into custom primitive data 0-2
        # (UDinkEnvironmentSubsystem::GroundColourAt); anything else gets the default, a meadow soil.
        soil = expr(mat, unreal.MaterialExpressionVectorParameter, -1000, -1140, parameter_name='GroundColour', default_value=unreal.LinearColor(0.093, 0.13, 0.045, 1.0))
        try:
            soil.set_editor_property('use_custom_primitive_data', True)
            soil.set_editor_property('primitive_data_index', 0)
        except Exception as error:
            warn(f'{name}: GroundColour cannot read custom primitive data ({error}); trunks use the default soil colour')
        grounded = custom(mat, -450, -1300, '''
// bark darkened and stained at the foot, then taken over by the soil colour itself in the last third (splash, moss, litter)
float w = saturate(UV.x) * saturate(Amount);
float3 stained = lerp(C, C * float3(0.46, 0.44, 0.30), w * w * 0.85);
float lum = dot(C, float3(0.3, 0.59, 0.11)) / max(dot(Soil, float3(0.3, 0.59, 0.11)), 0.02);
float3 earth = Soil * clamp(lerp(1.0, lum, 0.35), 0.6, 1.3) * 0.85;
return lerp(stained, earth, smoothstep(0.45, 1.0, w) * 0.8);''', F3, ['C', 'UV', 'Amount', 'Soil'], 'Ground blend')
        link(base, '', grounded, 'C'); link(uv1, '', grounded, 'UV'); link(amount, '', grounded, 'Amount'); link(soil, '', grounded, 'Soil')
        base = grounded
    if timber:
        # timber vertex colours: B limewash (pale plate, posts, rails), R dark sill and handling, G soot
        vct = expr(mat, unreal.MaterialExpressionVertexColor, -1000, -1500)
        timbered = custom(mat, -450, -1500, '''
// as the wall kit's Blender timber: limewash worn through on the grain lows, dark handling and sill, soot, occlusion in the colour
float lum = dot(C, float3(0.2126, 0.7152, 0.0722));
float3 c = lerp(C, float3(0.42, 0.41, 0.36), saturate(V.b) * saturate(lum * 2.0 + 0.55) * 0.95);
c *= lerp(float3(1.0, 1.0, 1.0), float3(0.10, 0.07, 0.05), saturate(V.r) * 0.95);
c *= lerp(float3(1.0, 1.0, 1.0), float3(0.20, 0.19, 0.18), saturate(V.g) * 0.8);
return c * lerp(1.0, AO, 0.5);''', F3, ['C', 'V', 'AO'], 'Timber grime')
        link(base, '', timbered, 'C'); link(vct, '', timbered, 'V'); link(orm, 'R', timbered, 'AO')
        base = timbered
    if blend is not None:
        # second texture set blended in by vertex colour R (damp masonry), vertex colour G darkens (soot)
        vcb = expr(mat, unreal.MaterialExpressionVertexColor, -1000, -600)
        bc2 = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -1000, -300, parameter_name='BC2', texture=blend['BC'], sampler_type=ST.SAMPLERTYPE_COLOR)
        nm2 = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -1000, 0, parameter_name='N2', texture=blend['N'], sampler_type=ST.SAMPLERTYPE_NORMAL)
        orm2 = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -1000, 300, parameter_name='ORM2', texture=blend['ORM'], sampler_type=ST.SAMPLERTYPE_MASKS)
        # As the wall kit's Blender material (WallKits/tools/wallkit_build.py blend_material): the hand-over to the
        # second set is height-aware (weight * 2.2 - 0.6 - height, so a low weight shows nothing of it and the edge
        # follows the relief; a plain lerp ghosts the broken-plaster patches over the whole wall), damp multiplies a
        # green-brown tint in, soot multiplies towards dark grey, and 45 % of the occlusion goes into the colour.
        height = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -1000, 600, parameter_name='H', texture=blend.get('H') or defaults['ORM'], sampler_type=ST.SAMPLERTYPE_MASKS)
        fac = custom(mat, -800, -600, f'return saturate(saturate(V.{blend_channel}) * 2.2 - 0.6 - H);', F1, ['V', 'H'], 'Height-aware blend weight')
        link(vcb, '', fac, 'V'); link(height, 'R', fac, 'H')
        damp = 'c *= lerp(float3(1.0, 1.0, 1.0), float3(0.30, 0.29, 0.20), saturate(V.r) * 0.95);' if blend_channel != 'r' else ''
        blended = custom(mat, -450, -300, f'''
float3 c = lerp(A, B, F);
{damp}
c *= lerp(float3(1.0, 1.0, 1.0), float3(0.20, 0.19, 0.18), saturate(V.g) * 0.8 * Soot);
return c * lerp(1.0, lerp(OA, OB, F), 0.45);''', F3, ['A', 'B', 'V', 'Soot', 'F', 'OA', 'OB'], 'Blend by vertex colour')
        link(base, '', blended, 'A'); link(bc2, 'RGB', blended, 'B'); link(vcb, '', blended, 'V'); link(fac, '', blended, 'F')
        link(orm, 'R', blended, 'OA'); link(orm2, 'R', blended, 'OB')
        soot_base = base
        base = blended
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -700, -520, parameter_name='Soot', default_value=1.0), '', base, 'Soot')
    if scatter:
        # scatter instances take the ground's field-scale colour drift (same lookup as the terrain material)
        macro_tex = LIB.load_asset('/Game/Dink/Textures/Environment/T_Env_MacroDefault')
        obj0 = expr(mat, unreal.MaterialExpressionObjectPositionWS, -1000, -900)
        big_uv = custom(mat, -850, -900, 'return P.xy / 11000.0;', unreal.CustomMaterialOutputType.CMOT_FLOAT2, ['P'], 'Field UV')
        link(obj0, '', big_uv, 'P')
        big = expr(mat, unreal.MaterialExpressionTextureSample, -700, -900, texture=macro_tex, sampler_type=ST.SAMPLERTYPE_MASKS,
                   sampler_source=unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        link(big_uv, '', big, 'UVs')
        match = expr(mat, unreal.MaterialExpressionScalarParameter, -700, -1180, parameter_name='GroundMatch', default_value=0.0)
        matched = custom(mat, -450, -900, '''
float3 c = C;
float3 g = c * (1.0 + 0.3 * (Big.r * 2.0 - 1.0));
float lum = dot(g, float3(0.3, 0.59, 0.11));
g = lerp(g, lum * float3(1.16, 1.04, 0.74), 0.3 * smoothstep(0.45, 0.8, Big.g * 0.7 + Big.b * 0.3));
// dry, straw-coloured stretches in drifts (the macro map's third channel), never evenly
float dry = saturate(Dry) * smoothstep(0.52, 0.78, Big.b * 0.6 + Big.r * 0.4);
g = lerp(g, dot(g, float3(0.3, 0.59, 0.11)) * float3(1.75, 1.42, 0.72), dry);
return lerp(c, g, saturate(Match));''', F3, ['C', 'Big', 'Match', 'Dry'], 'Ground colour match')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -700, -1260, parameter_name='DryPatches', default_value=0.0), '', matched, 'Dry')
        link(base, base_pin, matched, 'C'); link(big, 'RGB', matched, 'Big'); link(match, '', matched, 'Match')
        base, base_pin = matched, ''
    if not foliage:
        out(base, base_pin, MP.MP_BASE_COLOR)
    strength = expr(mat, unreal.MaterialExpressionScalarParameter, -700, 200, parameter_name='NormalStrength', default_value=1.0)
    normal = custom(mat, -400, 0, 'return normalize(float3(N.xy * S, N.z));', F3, ['N', 'S'], 'Normal strength')
    link(nm, 'RGB', normal, 'N'); link(strength, '', normal, 'S')
    if blend is not None:
        normal2 = custom(mat, -400, 80, 'return normalize(lerp(A, B, F));', F3, ['A', 'B', 'F'], 'Blend normal')
        link(normal, '', normal2, 'A'); link(nm2, 'RGB', normal2, 'B'); link(fac, '', normal2, 'F')
        normal = normal2
        damp_rough = 'o.g = saturate(o.g - 0.12 * saturate(V.r));' if blend_channel != 'r' else ''
        ormb = custom(mat, -400, 300, f'float3 o = lerp(A, B, F); {damp_rough} return o;', F3, ['A', 'B', 'F', 'V'], 'Blend ORM')
        link(orm, 'RGB', ormb, 'A'); link(orm2, 'RGB', ormb, 'B'); link(fac, '', ormb, 'F'); link(vcb, '', ormb, 'V')
        for channel, prop in (('r', MP.MP_AMBIENT_OCCLUSION), ('g', MP.MP_ROUGHNESS), ('b', MP.MP_METALLIC)):
            pick = expr(mat, unreal.MaterialExpressionComponentMask, -200, 300, r=channel == 'r', g=channel == 'g', b=channel == 'b', a=False)
            link(ormb, '', pick, '')
            out(pick, '', prop)
    elif shading == 'hair':
        # hair cards: default lit, anisotropic along the strand (card V), never glossier than 0.38
        rough = custom(mat, -400, 300, 'return max(R, 0.38);', F1, ['R'], 'Hair roughness')
        link(orm, 'G', rough, 'R')
        out(rough, '', MP.MP_ROUGHNESS)
        out(orm, 'R', MP.MP_AMBIENT_OCCLUSION)
        out(expr(mat, unreal.MaterialExpressionConstant, -400, 380, r=0.35), '', MP.MP_SPECULAR)
        out(expr(mat, unreal.MaterialExpressionScalarParameter, -400, 460, parameter_name='Anisotropy', default_value=0.55), '', MP.MP_ANISOTROPY)
        if 'FLOW' in defaults:
            # round 6 hair: strand direction in FLOW.rg (tangent space); the cards no longer run along V everywhere
            flow = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -700, 620, parameter_name='FLOW', texture=defaults['FLOW'], sampler_type=ST.SAMPLERTYPE_LINEAR_COLOR)
            along = custom(mat, -400, 540, 'float2 d = F.rg * 2.0 - 1.0; return normalize(float3(d, 0.0) + float3(0.0, 1e-4, 0.0));', F3, ['F'], 'Strand direction')
            link(flow, 'RGB', along, 'F')
            out(along, '', MP.MP_TANGENT)
        else:
            out(expr(mat, unreal.MaterialExpressionConstant3Vector, -400, 540, constant=unreal.LinearColor(0.0, 1.0, 0.0, 1.0)), '', MP.MP_TANGENT)
    elif shading == 'eye':
        # one shell with a modelled cornea. The clear-coat pins are hidden from the scripting API, so the wet
        # highlight comes from a glossy default-lit surface (roughness capped at 0.1, raised specular).
        out(orm, 'R', MP.MP_AMBIENT_OCCLUSION)
        eye_rough = custom(mat, -400, 300, 'return min(R, 0.1);', F1, ['R'], 'Eye roughness')
        link(orm, 'G', eye_rough, 'R')
        out(eye_rough, '', MP.MP_ROUGHNESS)
        out(expr(mat, unreal.MaterialExpressionConstant, -400, 380, r=0.7), '', MP.MP_SPECULAR)
    elif foliage:
        # Leaves and needles. Calibrated against the Cycles review renders (Saved/PhotorealPass/lighting/tools/cal.sh):
        # specular well under the 0.5 default, roughness from ORM G never glossy, and the crown interior darkened by
        # the branch-bend wind weight (vertex alpha: 0 at the trunk, 1 at the limb tips) in base colour, subsurface
        # and ambient occlusion, because neither the sky light nor the shadow maps resolve leaf-scale occlusion.
        fvc = expr(mat, unreal.MaterialExpressionVertexColor, -1000, -1700)
        # second proxy, for meshes whose cards all carry the same weight (bushes): depth inside the mesh's own bounds
        bounds = expr(mat, unreal.MaterialExpressionObjectLocalBounds, -1200, -1900)
        local = expr(mat, unreal.MaterialExpressionTransformPosition, -1200, -2050,
                     transform_source_type=unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
                     transform_type=unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
        link(expr(mat, unreal.MaterialExpressionWorldPosition, -1400, -2050), '', local, '')
        crown = custom(mat, -800, -1700, '''
float a = lerp(saturate(Shade), 1.0, pow(saturate(VA), max(Power, 0.05)));
float3 c = (Mn + Mx) * 0.5;
float3 h = max((Mx - Mn) * 0.5, 1.0);
float3 q = (L - float3(c.xy, Mn.z + h.z * 0.6)) / h;          // the dark core sits a little below the middle
float d = smoothstep(0.25, 0.95, length(q));
// the inner face of a card, seen through the gaps of the cards in front, is the unlit inside of the crown
// grass: dark at the root, lighter at the tip (height inside the patch's own bounds)
float up = saturate((L.z - Mn.z) / max(Mx.z - Mn.z, 1.0));
return a * lerp(saturate(Depth), 1.0, d) * (Side < 0.0 ? saturate(Back) : 1.0) * lerp(Root, Tip, up);''', F1, ['VA', 'Shade', 'Power', 'L', 'Mn', 'Mx', 'Depth', 'Side', 'Back', 'Root', 'Tip'], 'Crown interior shade')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -1000, -1220, parameter_name='RootShade', default_value=1.0), '', crown, 'Root')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -1000, -1140, parameter_name='TipLight', default_value=1.0), '', crown, 'Tip')
        link(expr(mat, unreal.MaterialExpressionTwoSidedSign, -1000, -1380), '', crown, 'Side')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -1000, -1300, parameter_name='BackShade', default_value=1.0), '', crown, 'Back')
        link(fvc, 'A', crown, 'VA'); link(local, '', crown, 'L'); link(bounds, 'Min', crown, 'Mn'); link(bounds, 'Max', crown, 'Mx')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -1000, -1460, parameter_name='DepthShade', default_value=1.0), '', crown, 'Depth')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -1000, -1620, parameter_name='CrownShade', default_value=1.0), '', crown, 'Shade')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -1000, -1540, parameter_name='CrownPower', default_value=1.0), '', crown, 'Power')
        shaded = expr(mat, unreal.MaterialExpressionMultiply, -300, -300)
        link(base, base_pin, shaded, 'A'); link(crown, '', shaded, 'B')
        out(shaded, '', MP.MP_BASE_COLOR)
        ao = custom(mat, -400, 380, 'return saturate(lerp(1.0, A, Strength)) * lerp(saturate(CrownAO), 1.0, C);', F1, ['A', 'C', 'Strength', 'CrownAO'], 'Foliage AO')
        link(orm, 'R', ao, 'A'); link(crown, '', ao, 'C')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -700, 420, parameter_name='AOStrength', default_value=1.0), '', ao, 'Strength')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -700, 500, parameter_name='CrownAO', default_value=1.0), '', ao, 'CrownAO')
        out(ao, '', MP.MP_AMBIENT_OCCLUSION)
        frough = custom(mat, -400, 300, 'return clamp(R * S, 0.35, 1.0);', F1, ['R', 'S'], 'Foliage roughness')
        link(orm, 'G', frough, 'R')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -700, 340, parameter_name='RoughnessScale', default_value=1.0), '', frough, 'S')
        out(frough, '', MP.MP_ROUGHNESS)
        out(expr(mat, unreal.MaterialExpressionScalarParameter, -400, 460, parameter_name='Specular', default_value=0.25), '', MP.MP_SPECULAR)
    else:
        out(orm, 'R', MP.MP_AMBIENT_OCCLUSION)
        out(orm, 'G', MP.MP_ROUGHNESS)
        out(orm, 'B', MP.MP_METALLIC)
    if shading == 'hair':
        # the same normal on both faces of a hair card: the engine flips the normal of a back face, this flips it back
        same = custom(mat, -250, 0, 'return N * S;', F3, ['N', 'S'], 'Same normal on both faces')
        link(normal, '', same, 'N'); link(expr(mat, unreal.MaterialExpressionTwoSidedSign, -400, 120), '', same, 'S')
        normal = same
    out(normal, '', MP.MP_NORMAL)
    if masked or foliage:
        mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
        clip = expr(mat, unreal.MaterialExpressionScalarParameter, -700, -420, parameter_name='AlphaClip', default_value=0.33)
        # the clip value is a parameter: remap alpha so the material's fixed 0.5 threshold lands on it
        mask = custom(mat, -400, -420, 'return saturate(A - Clip + 0.5);', F1, ['A', 'Clip'], 'Alpha clip')
        link(bc, 'A', mask, 'A'); link(clip, '', mask, 'Clip')
        out(mask, '', MP.MP_OPACITY_MASK)
        mat.set_editor_property('opacity_mask_clip_value', 0.5)
        mat.set_editor_property('dither_opacity_mask', bool(skeletal))  # not on foliage: the dither pattern survives TSR and the crown turns to stipple (tried 12 Nov 2026)
    if foliage:
        sss = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -700, 600, parameter_name='SSS', texture=defaults['SSS'], sampler_type=ST.SAMPLERTYPE_COLOR)
        amount = expr(mat, unreal.MaterialExpressionScalarParameter, -700, 820, parameter_name='Translucency', default_value=0.4)
        sub = custom(mat, -400, 600, 'return S * T * Amount * C;', F3, ['S', 'T', 'Amount', 'C'], 'Subsurface colour')
        link(sss, 'RGB', sub, 'S'); link(tint_param, '', sub, 'T'); link(amount, '', sub, 'Amount'); link(crown, '', sub, 'C')
        out(sub, '', MP.MP_SUBSURFACE_COLOR)
        mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
        mat.set_editor_property('two_sided', True)
    elif shading == 'skin':
        sss = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -700, 600, parameter_name='SSS', texture=defaults['SSS'], sampler_type=ST.SAMPLERTYPE_COLOR)
        if profile is not None:
            # subsurface profile: Opacity is the scatter strength; the map is scatter colour x thickness
            scatter = custom(mat, -400, 600, 'return saturate(dot(S, float3(0.4, 0.35, 0.25)) * Amount);', F1, ['S', 'Amount'], 'Scatter strength')
            link(sss, 'RGB', scatter, 'S')
            link(expr(mat, unreal.MaterialExpressionScalarParameter, -700, 820, parameter_name='ScatterAmount', default_value=0.9), '', scatter, 'Amount')
            out(scatter, '', MP.MP_OPACITY)
            mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_SUBSURFACE_PROFILE)
            mat.set_editor_property('subsurface_profile', profile)
        else:
            out(sss, 'RGB', MP.MP_SUBSURFACE_COLOR)
            out(expr(mat, unreal.MaterialExpressionConstant, -400, 700, r=0.6), '', MP.MP_OPACITY)
            mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_SUBSURFACE)
    if two_sided:
        mat.set_editor_property('two_sided', True)
    if wind is not None:
        # Vertex colour "Wind": R trunk sway (0 ground .. 1 top), G branch phase, B leaf flutter, A branch bend.
        vc = expr(mat, unreal.MaterialExpressionVertexColor, -700, 1000)
        time = expr(mat, unreal.MaterialExpressionTime, -700, 1200)
        obj = expr(mat, unreal.MaterialExpressionObjectPositionWS, -700, 1280)
        amount = expr(mat, unreal.MaterialExpressionCollectionParameter, -700, 1360, collection=wind, parameter_name='Wind')
        scale = expr(mat, unreal.MaterialExpressionScalarParameter, -700, 1440, parameter_name='WindScale', default_value=1.0)
        wpo = custom(mat, -350, 1100, '''
float ph = VC.g * 6.2832 + dot(Obj.xy, float2(0.0031, 0.0047));
float sway = (sin(T * 0.62 + ph * 0.3) + 0.35 * sin(T * 1.37 + ph)) * VC.r * VC.r * 5.0;
float bend = sin(T * 1.9 + ph) * VA * 4.0;
float flutter = sin(T * 7.3 + ph * 3.1) * VC.b * 0.9;
float3 dir = float3(0.8, 0.6, 0.0);
// gusts: a slow value-noise field (about 14 m and 5 m) travelling down the wind, so a field leans in passing waves
float2 gp = Obj.xy / 1400.0 - float2(0.92, 0.39) * T * 0.11;
float2 gi = floor(gp); float2 gf = gp - gi; gf = gf * gf * (3.0 - 2.0 * gf);
#define DINK_GH(c) frac(sin(dot(c, float2(127.1, 311.7))) * 43758.5453)
float g1 = lerp(lerp(DINK_GH(gi), DINK_GH(gi + float2(1.0, 0.0)), gf.x), lerp(DINK_GH(gi + float2(0.0, 1.0)), DINK_GH(gi + float2(1.0, 1.0)), gf.x), gf.y);
float2 hp = Obj.xy / 520.0 - float2(0.92, 0.39) * T * 0.23;
float2 hi = floor(hp); float2 hf = hp - hi; hf = hf * hf * (3.0 - 2.0 * hf);
float g2 = lerp(lerp(DINK_GH(hi), DINK_GH(hi + float2(1.0, 0.0)), hf.x), lerp(DINK_GH(hi + float2(0.0, 1.0)), DINK_GH(hi + float2(1.0, 1.0)), hf.x), hf.y);
#undef DINK_GH
float gust = 0.45 + 1.5 * smoothstep(0.35, 0.85, 0.65 * g1 + 0.35 * g2);
float3 offset = (dir * (sway + bend) * gust + float3(0.0, 0.0, 1.0) * (bend * 0.3 + flutter * (0.6 + 0.4 * gust))) * Wind * Scale;
// scatter thinning: beyond FadeNear an instance shrinks into its pivot once its random number exceeds the
// share still kept at that distance; none are left at FadeFar
float keep = saturate((FadeFar - distance(Cam, Obj)) / max(FadeFar - FadeNear, 1.0));
float s = lerp(1.0, saturate((keep - Rnd * 0.85) * 6.0), saturate(Fade));
return offset * s + (Obj - WP) * (1.0 - s);''', F3,
                     ['VC', 'VA', 'T', 'Obj', 'Wind', 'Scale', 'Cam', 'WP', 'Rnd', 'Fade', 'FadeNear', 'FadeFar'], 'Wind offset (cm) and scatter thinning')
        link(expr(mat, unreal.MaterialExpressionCameraPositionWS, -700, 1520), '', wpo, 'Cam')
        link(expr(mat, unreal.MaterialExpressionWorldPosition, -700, 1600), '', wpo, 'WP')
        link(expr(mat, unreal.MaterialExpressionPerInstanceRandom, -700, 1680), '', wpo, 'Rnd')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -700, 1760, parameter_name='ScatterFade', default_value=0.0), '', wpo, 'Fade')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -700, 1840, parameter_name='FadeNearCm', default_value=1200.0), '', wpo, 'FadeNear')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -700, 1920, parameter_name='FadeFarCm', default_value=3700.0), '', wpo, 'FadeFar')
        link(vc, '', wpo, 'VC'); link(vc, 'A', wpo, 'VA'); link(time, '', wpo, 'T'); link(obj, '', wpo, 'Obj'); link(amount, '', wpo, 'Wind'); link(scale, '', wpo, 'Scale')
        out(wpo, '', MP.MP_WORLD_POSITION_OFFSET)
    EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    if skeletal:
        EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
    if morph:
        # without this flag the game draws a mesh whose shape key is active in black or in the default grey material
        EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_MORPH_TARGETS, True)
    EDIT.recompile_material(mat)
    save(mat)
    return mat


HAIR_MODEL = os.environ.get('DINK_HAIR_MODEL', 'hair')   # 'lit' builds the previous default-lit anisotropic card material (comparison)
# Per-character trim of the hair material instance: 'tint' multiplies the atlas colour, 'scalars' are instance values
# of the parameters hair_material() declares.
# Calibrated in the running game on 14 Nov 2026 (Docs/Verification/CharacterHair_14Nov2026): with the first values
# (root 0.55, depth 0.6) the hero's hair was near black outdoors and Milder's crop was full of dark dashes; the
# Mother's fair hair blew out to straw-white in window light, and any root-to-tip shading drew every painted strand of
# her pulled-back hair as a separate shingle, so she has none.
HAIR_LOOK = {
    'Dink': {'tint': (2.4, 1.5, 1.1), 'scalars': {'Scatter': 0.8}},
    'Mother': {'tint': (0.8, 0.76, 0.7), 'scalars': {'RootShade': 1.0, 'TipLight': 1.0, 'Scatter': 0.5, 'StrandVariation': 0.12, 'DepthShade': 0.45, 'Specular': 0.25, 'RoughnessScale': 1.3, 'CapShade': 1.0, 'CardShadow': 1.0}},
    'Milder': {'tint': (0.85, 0.8, 0.75), 'scalars': {'RootShade': 0.95, 'DepthShade': 0.9, 'Scatter': 0.45, 'Specular': 0.3, 'StrandVariation': 0.12}},
}


# Skin tint per character (multiplies the base colour). The Mother's fair skin was chalk in the window light of her house.
SKIN_LOOK = {'Mother': (0.78, 0.72, 0.69)}


def hair_material(folder, name, defaults, morph=False):
    """Hair cards with the engine's Hair shading model (two highlight lobes and light through the hair), masked,
    two-sided, dithered. Inputs of that model, as the engine names its pins: Base Color, Scatter (the metallic pin),
    Specular, Roughness, Tangent (the normal pin: the strand direction in tangent space) and Backlit (the first custom
    data pin, reached through UDinkCharacterArtLibrary because Python's enum hides it).
    The atlas maps (Characters/Tools/hairlib.py compose_atlas) drive it: BC rgb + alpha; FLOW rg the strand direction
    in the atlas plane, b 0 on the opaque cap and 1 on the cards; MSK r nearness within the lock, g a number per
    strand, b root (0) to tip (1); ORM r occlusion, g roughness."""
    mat = new_material(folder, name)
    bc = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -1100, -300, parameter_name='BC', texture=defaults['BC'], sampler_type=ST.SAMPLERTYPE_COLOR)
    orm = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -1100, 300, parameter_name='ORM', texture=defaults['ORM'], sampler_type=ST.SAMPLERTYPE_MASKS)
    flow = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -1100, 600, parameter_name='FLOW', texture=defaults['FLOW'], sampler_type=ST.SAMPLERTYPE_LINEAR_COLOR)
    msk = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -1100, 900, parameter_name='MSK', texture=defaults['MSK'], sampler_type=ST.SAMPLERTYPE_LINEAR_COLOR)
    # the normal map is not read by the Hair model (its normal pin is the tangent); the parameter stays so that the
    # instance can carry the texture of the manifest
    expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -1100, 0, parameter_name='N', texture=defaults['N'], sampler_type=ST.SAMPLERTYPE_NORMAL)
    tint = expr(mat, unreal.MaterialExpressionVectorParameter, -1100, -700, parameter_name='Tint', default_value=unreal.LinearColor(1, 1, 1, 1))
    row = [0]
    def param(pname, value):
        row[0] += 80
        return expr(mat, unreal.MaterialExpressionScalarParameter, -1500, -900 + row[0], parameter_name=pname, default_value=value)
    colour = custom(mat, -600, -500, '''
// off the strands the mask is empty: take middle values there so that the texels the alpha edge blends in stay neutral
float on = step(0.004, M.r + M.g + M.b);
float t = lerp(0.5, saturate(M.b), on);
float strand = lerp(0.5, M.g, on);
float depth = lerp(0.7, saturate(M.r), on);
float3 c = C * T;
c *= lerp(RootShade, 1.0, smoothstep(0.0, 0.5, t));              // darker at the root, where hair lies on hair
c *= lerp(1.0, TipLight, smoothstep(0.45, 1.0, t));              // lighter, sun-bleached tips
c *= 1.0 + Variation * (strand * 2.0 - 1.0);                     // strand to strand
c *= lerp(DepthShade, 1.0, depth);                               // strands deep in the lock are in its shade
c *= lerp(CapShade, 1.0, saturate(Card));                        // the opaque cap under the cards is the hair's dark depth
return c;''', F3, ['C', 'T', 'M', 'RootShade', 'TipLight', 'Variation', 'DepthShade', 'CapShade', 'Card'], 'Hair colour: root to tip, strand to strand, depth')
    link(bc, 'RGB', colour, 'C'); link(tint, '', colour, 'T'); link(msk, 'RGB', colour, 'M')
    # CapShade: under a crop the cap was lit paler than the cards standing on it and showed between them as scalp
    # (Milder, 14 Nov 2026); where the cap IS the visible hair (the Mother's drawn-back hair) the instance sets 1
    link(param('CapShade', 0.6), '', colour, 'CapShade'); link(flow, 'B', colour, 'Card')
    link(param('RootShade', 0.85), '', colour, 'RootShade'); link(param('TipLight', 1.1), '', colour, 'TipLight')
    link(param('StrandVariation', 0.18), '', colour, 'Variation'); link(param('DepthShade', 0.8), '', colour, 'DepthShade')
    out(colour, '', MP.MP_BASE_COLOR)
    out(param('Scatter', 0.7), '', MP.MP_METALLIC)
    out(param('Specular', 0.5), '', MP.MP_SPECULAR)
    rough = custom(mat, -600, 300, 'return clamp(R * S, 0.3, 1.0);', F1, ['R', 'S'], 'Hair roughness')
    link(orm, 'G', rough, 'R'); link(param('RoughnessScale', 1.0), '', rough, 'S')
    out(rough, '', MP.MP_ROUGHNESS)
    ao = custom(mat, -600, 420, 'return lerp(1.0, A, saturate(S));', F1, ['A', 'S'], 'Hair occlusion')
    link(orm, 'R', ao, 'A'); link(param('AOStrength', 1.0), '', ao, 'S')
    out(ao, '', MP.MP_AMBIENT_OCCLUSION)
    # strand direction: FLOW.rg is in the atlas plane with v up (a Blender image); the engine's tangent space has
    # its second axis down the texture, so the second component changes sign (FlowFlip -1 restores the old reading)
    along = custom(mat, -600, 600, 'float2 d = F.rg * 2.0 - 1.0; d.y *= -Flip; return normalize(float3(d, 0.0) + float3(0.0, 1e-4, 0.0));', F3, ['F', 'Flip'], 'Strand direction')
    link(flow, 'RGB', along, 'F'); link(param('FlowFlip', 1.0), '', along, 'Flip')
    out(along, '', MP.MP_NORMAL)
    back = custom(mat, -600, 760, 'return saturate(B * Amount);', F1, ['B', 'Amount'], 'Light through the hair')
    link(flow, 'B', back, 'B'); link(param('Backlit', 1.0), '', back, 'Amount')
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_HAIR)
    if not unreal.DinkCharacterArtLibrary.connect_material_custom_data(mat, back, '', 0):
        raise RuntimeError(f'{name}: cannot connect the Backlit pin of the Hair shading model')
    # coverage: the strand alpha itself, thinned towards the tips; dithered, so the anti-aliasing resolves it to soft hair
    mask = custom(mat, -600, -150, '''
float on = step(0.004, M.r + M.g + M.b);
float t = lerp(0.5, saturate(M.b), on);
// Coverage below Cut is no hair at all. A card of sparse strands averages to a few per cent of coverage in the
// smaller mips, and the dithered mask drew that haze as a ghost sheet over the head and a stipple halo round it.
float c = A * Gain * lerp(1.0, TipFade, smoothstep(0.7, 1.0, t)) + Bias;
return saturate((c - Cut) / max(1.0 - Cut, 0.01));''', F1, ['A', 'M', 'Gain', 'TipFade', 'Bias', 'Cut'], 'Hair coverage')
    link(bc, 'A', mask, 'A'); link(msk, 'RGB', mask, 'M'); link(param('AlphaCut', 0.3), '', mask, 'Cut')
    link(param('AlphaGain', 1.5), '', mask, 'Gain'); link(param('TipFade', 0.7), '', mask, 'TipFade'); link(param('AlphaBias', 0.0), '', mask, 'Bias')
    # Shadows: only the opaque cap casts one (FLOW.b is 0 on the cap, 1 on the cards). A card lifted a few millimetres
    # off the head shadowed its own visible side and the cap under it, and a short crop in full sun was dark dashes on
    # a pale cap (Milder, 14 Nov 2026). CardShadow 1 lets the cards cast again.
    shadow_mask = custom(mat, -350, -150, 'return A * lerp(1.0 - saturate(B), 1.0, saturate(K));', F1, ['A', 'B', 'K'], 'Hair coverage in the shadow pass')
    link(mask, '', shadow_mask, 'A'); link(flow, 'B', shadow_mask, 'B'); link(param('CardShadow', 0.0), '', shadow_mask, 'K')
    in_pass = expr(mat, unreal.MaterialExpressionShadowReplace, -150, -150)
    link(mask, '', in_pass, 'Default'); link(shadow_mask, '', in_pass, 'Shadow')
    out(in_pass, '', MP.MP_OPACITY_MASK)
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property('opacity_mask_clip_value', 0.5)
    mat.set_editor_property('dither_opacity_mask', True)
    mat.set_editor_property('two_sided', True)
    EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
    if morph:
        EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_MORPH_TARGETS, True)
    EDIT.recompile_material(mat)
    save(mat)
    return mat


def import_static(fbx_lods, folder, name, import_normals, lods_in_file=False):
    target = folder + '/' + name
    key = '|'.join(stamp_of(f) for f in fbx_lods)
    existing = LIB.load_asset(target) if LIB.does_asset_exist(target) else None
    if existing is not None and (FROZEN or (LIB.get_metadata_tag(existing, 'DinkSource') == key and not FORCE)):
        return existing, False
    options = unreal.FbxImportUI()
    for k, v in {'automated_import_should_detect_type': False, 'mesh_type_to_import': unreal.FBXImportType.FBXIT_STATIC_MESH,
                 'import_mesh': True, 'import_materials': False, 'import_textures': False, 'import_animations': False}.items():
        options.set_editor_property(k, v)
    opts = options.static_mesh_import_data
    settings = {'combine_meshes': not lods_in_file, 'import_mesh_lods': lods_in_file, 'remove_degenerates': True,
                'auto_generate_collision': False, 'generate_lightmap_u_vs': False, 'convert_scene': True,
                'convert_scene_unit': True, 'import_uniform_scale': 1.0,
                'vertex_color_import_option': unreal.VertexColorImportOption.REPLACE,
                'normal_import_method': unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS if import_normals
                else unreal.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS}
    for k, v in settings.items():
        opts.set_editor_property(k, v)
    if existing is not None:
        # A re-import of an existing mesh reads the asset's stored import data, not this task's options, and came
        # in at 1/100 scale. Family art and the scatter refer to meshes by path, so replace the asset instead.
        LIB.delete_asset(target)
        existing = None
    task = unreal.AssetImportTask()
    task.filename = str(Path(fbx_lods[0]).resolve())
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.options = options
    task.factory = unreal.FbxFactory()
    TOOLS.import_asset_tasks([task])
    mesh = LIB.load_asset(target)
    if mesh is None:
        raise RuntimeError('Mesh import failed: ' + str(fbx_lods[0]))
    for index, f in enumerate(fbx_lods[1:], 1):
        if MESHES.import_lod(mesh, index, str(Path(f).resolve())) != index:
            raise RuntimeError(f'{name}: LOD{index} import failed')
    for index in range(MESHES.get_lod_count(mesh)):
        build = MESHES.get_lod_build_settings(mesh, index)
        build.set_editor_property('recompute_normals', not import_normals)
        build.set_editor_property('recompute_tangents', True)
        build.set_editor_property('remove_degenerates', True)
        MESHES.set_lod_build_settings(mesh, index, build)
    LIB.set_metadata_tag(mesh, 'DinkSource', key)
    return mesh, True


def import_scatter(fbx, folder, name):
    """The scatter FBX holds two plain objects, <name>_LOD0 and <name>_LOD1 (no LOD group): import them as two
    temporary meshes, keep LOD0 under the asset's name and attach LOD1's geometry as its second LOD."""
    target = folder + '/' + name
    key = stamp_of(fbx) + ':vc2'  # vertex colours; 2 = LOD sections mapped by slot name
    existing = LIB.load_asset(target) if LIB.does_asset_exist(target) else None
    if existing is not None and LIB.get_metadata_tag(existing, 'DinkSource') == key:
        return existing, False
    temp = folder + '/_Import'
    options = unreal.FbxImportUI()
    for k, v in {'automated_import_should_detect_type': False, 'mesh_type_to_import': unreal.FBXImportType.FBXIT_STATIC_MESH,
                 'import_mesh': True, 'import_materials': False, 'import_textures': False, 'import_animations': False}.items():
        options.set_editor_property(k, v)
    opts = options.static_mesh_import_data
    for k, v in {'combine_meshes': False, 'import_mesh_lods': False, 'remove_degenerates': True, 'auto_generate_collision': False,
                 'generate_lightmap_u_vs': False, 'convert_scene': True, 'convert_scene_unit': True, 'import_uniform_scale': 1.0,
                 # the grime weights of the wall kits live in the vertex colours: without REPLACE every vertex is white
                 # (all weights 1: plaster fully broken, damp and sooted; found 12 Nov 2026)
                 'vertex_color_import_option': unreal.VertexColorImportOption.REPLACE,
                 'normal_import_method': unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS}.items():
        opts.set_editor_property(k, v)
    task = unreal.AssetImportTask()
    task.filename = str(Path(fbx).resolve())
    task.destination_path = temp
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.options = options
    task.factory = unreal.FbxFactory()
    TOOLS.import_asset_tasks([task])
    parts = {}
    for path in task.get_editor_property('imported_object_paths'):
        asset = unreal.load_object(None, str(path)) if '.' in str(path) else LIB.load_asset(str(path))
        if asset is not None:
            label = asset.get_name()
            if 'UCX' in label:
                continue
            parts['LOD1' if label.endswith('LOD1') else 'LOD0'] = asset
    if 'LOD0' not in parts:
        raise RuntimeError(f'{name}: no LOD0 object in {fbx}')
    if existing is not None:
        LIB.delete_asset(target)
    mesh = LIB.duplicate_loaded_asset(parts['LOD0'], target)
    if mesh is None:
        raise RuntimeError(f'{name}: cannot create {target}')
    if 'LOD1' in parts:
        MESHES.set_lod_from_static_mesh(mesh, 1, parts['LOD1'], 0, True)
        # sections follow slot NAMES: the LOD object lists its materials in its own order (see import_town_exteriors.py)
        def slot_names(m):
            return [str(x.get_editor_property('material_slot_name')).split('.')[0] for x in m.get_editor_property('static_materials')]
        main_names, part_names = slot_names(mesh), slot_names(parts['LOD1'])
        for section in range(parts['LOD1'].get_num_sections(0)):
            source = MESHES.get_lod_material_slot(parts['LOD1'], 0, section)
            wanted = part_names[source] if 0 <= source < len(part_names) else None
            if wanted in main_names:
                MESHES.set_lod_material_slot(mesh, main_names.index(wanted), 1, section)
            else:
                warn(f'{name}: LOD1 section {section} uses {wanted}, which LOD0 has no slot for')
    LIB.set_metadata_tag(mesh, 'DinkSource', key)
    LIB.delete_directory(temp)
    return mesh, True


def decal_material(folder, name, texture, roughness=0.12):
    """A deferred decal that lays the texture's colour on whatever is under it (ground and grass), alpha as opacity."""
    mat = new_material(folder, name)
    mat.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    bc = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -500, 0, parameter_name='BC', texture=texture, sampler_type=ST.SAMPLERTYPE_COLOR)
    rough = expr(mat, unreal.MaterialExpressionConstant, -300, 220, r=roughness)
    out(bc, 'RGB', MP.MP_BASE_COLOR)
    out(bc, 'A', MP.MP_OPACITY)
    out(rough, '', MP.MP_ROUGHNESS)
    EDIT.recompile_material(mat)
    save(mat)
    return mat


def assign_slots(mesh, materials, name):
    slots = list(mesh.get_editor_property('static_materials'))
    for slot in slots:
        key = str(slot.get_editor_property('material_slot_name')).split('.')[0]
        if key not in materials:
            key = str(slot.get_editor_property('imported_material_slot_name')).split('.')[0]
        if key not in materials:
            raise RuntimeError(f'{name}: unmapped material slot {key}')
        slot.set_editor_property('material_interface', materials[key])
    mesh.set_editor_property('static_materials', slots)


def check_size(mesh, dimensions_m, name):
    size = mesh.get_bounding_box().max - mesh.get_bounding_box().min
    got = [size.x / 100.0, size.y / 100.0, size.z / 100.0]
    worst = max(abs(a - b) for a, b in zip(sorted(got[:2]) + [got[2]], sorted(dimensions_m[:2]) + [dimensions_m[2]]))
    if worst > max(0.02, 0.03 * max(dimensions_m)):
        warn(f'{name}: imported size {[round(v, 3) for v in got]} m differs from the manifest {dimensions_m}')
    return [round(v, 3) for v in got]


# ------------------------------------------------------------------------------------------- vegetation
VEG = PASS / 'Vegetation'
if 'vegetation' in ONLY and os.environ.get('DINK_PHOTOREAL_ALLOW_MIXED') != '1':
    # an export still being written has files newer than its manifest: do not import a mixed state
    manifest_time = (VEG / 'manifest.json').stat().st_mtime
    newer = [p.name for p in (VEG / 'Export').rglob('*') if p.is_file() and p.stat().st_mtime > manifest_time + 1.0]
    if os.environ.get('DINK_PHOTOREAL_FROZEN') == '1' and not newer:
        newer = ['(DINK_PHOTOREAL_FROZEN=1: only assets that are not imported yet)']
    if newer:
        # keep what is already imported exactly as it is (only assets that do not exist yet are imported, and
        # the materials are rebuilt from the imported textures)
        FROZEN = True
        warn(f'vegetation frozen: {len(newer)} export files are newer than manifest.json ({newer[0]} ...); existing assets were not re-imported, re-run when the export is finished')
if 'vegetation' in ONLY:
    manifest = json.loads((VEG / 'manifest.json').read_text())
    folder = BASE + '/Vegetation'
    tex_folder = folder + '/Textures'
    mpc_path = folder + '/MPC_Dink_Environment'
    mpc = LIB.load_asset(mpc_path) if LIB.does_asset_exist(mpc_path) else None
    if mpc is None:
        mpc = TOOLS.create_asset('MPC_Dink_Environment', folder, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
        wind_param = unreal.CollectionScalarParameter()
        wind_param.set_editor_property('parameter_name', 'Wind')
        wind_param.set_editor_property('default_value', 1.0)
        mpc.set_editor_property('scalar_parameters', [wind_param])
        save(mpc)
    sets = {}
    derived = {}
    for mat_name, row in manifest['materials'].items():
        masked = 'masked' in row['blend_mode']
        if not row.get('maps') or (row.get('texture_set') and mat_name != 'MI_Veg_' + row['texture_set'][len('T_Veg_'):]):
            derived[mat_name] = row  # a tinted instance of another set, built after the parents
            continue
        tex = {}
        for role in row['maps']:
            path = VEG / 'Export/Textures' / f"{row['texture_set']}_{role}.png"
            tex[role] = import_texture(path, tex_folder, 'BCA' if (role == 'BC' and masked) else role,
                                       max_size=next((cap for key, cap in IMPORT_CAPS.items() if key in path.name), 0))  # family-scatter cap
        sets[mat_name] = (masked, tex)
    # Texture sets on disk that the manifest does not list yet (an export newer than its manifest): import them
    # too, so a mesh slot naming them still resolves. A set with an _SSS map is foliage.
    for bc in sorted((VEG / 'Export/Textures').glob('T_Veg_*_BC.png')):
        set_name = bc.stem[:-3]
        mat_name = 'MI_Veg_' + set_name[len('T_Veg_'):]
        if mat_name in sets:
            continue
        masked = (bc.parent / f'{set_name}_SSS.png').exists()
        tex = {}
        for role in ('BC', 'N', 'ORM', 'SSS'):
            path = bc.parent / f'{set_name}_{role}.png'
            if path.exists():
                tex[role] = import_texture(path, tex_folder, 'BCA' if (role == 'BC' and masked) else role)
        if {'BC', 'N', 'ORM'} <= set(tex):
            sets[mat_name] = (masked, tex)
            warn(f'{mat_name}: texture set found on disk but not in the vegetation manifest; imported from the files')
    bark_default = next(t for m, t in sets.values() if not m)
    leaf_default = next(t for m, t in sets.values() if m)
    parents = {False: surface_material(folder, 'M_Veg_Bark', bark_default, wind=mpc, ground_blend=True),
               True: surface_material(folder, 'M_Veg_Foliage', leaf_default, foliage=True, wind=mpc, scatter=True)}
    materials = {}
    # Calibrated 12 Nov 2026 against the Cycles review renders with Saved/PhotorealPass/lighting/tools/cal.sh and
    # cal_compare.py (same framing and sun, foliage mean / percentile RGB): tint, specular, crown shade, crown AO, light through.
    # round 6 (cal v6 against the 12 Nov re-export): pine median luminance 27 against 56 in Cycles -> tint x1.3; oak 95th percentile 143 against 81 -> specular halved
    FOLIAGE_LOOK = {'PineNeedles': ((0.78, 0.80, 0.52), 0.25, 0.35, 0.20, 0.10), 'OakLeaves': ((0.45, 0.50, 0.26), 0.06, 0.22, 0.08, 0.10),
                    'WillowLeaves': ((0.60, 0.62, 0.42), 0.20, 0.35, 0.20, 0.10), 'Understory': ((0.42, 0.48, 0.26), 0.10, 1.0, 0.5, 0.10),
                    'GroundCover': ((0.60, 0.62, 0.36), 0.10, 1.0, 1.0, 0.10), 'Shrub': ((0.38, 0.46, 0.22), 0.10, 1.0, 0.5, 0.10)}
    foliage_tints = {}
    for mat_name, (masked, tex) in sets.items():
        scalars = {}
        if masked:
            scalars['AlphaClip'] = 0.25 if 'Needles' in mat_name else 0.33
            look = next((v for k, v in FOLIAGE_LOOK.items() if k in mat_name), FOLIAGE_LOOK['Understory'])
            foliage_tints[mat_name] = look[0]
            scalars.update({'Specular': look[1], 'CrownShade': look[2], 'CrownAO': look[3], 'Translucency': look[4]})
            if 'Understory' in mat_name or 'Shrub' in mat_name:   # MI_Veg_Shrub: the four bushes since the 12 Nov re-export
                scalars['BackShade'] = 0.35
                scalars['DepthShade'] = 0.3  # bushes and ferns: every card carries the same branch weight, so shade by depth in the bounds
            if 'Leaves' in mat_name or 'Needles' in mat_name:
                scalars['BackShade'] = 0.6
        if 'Deadwood' in mat_name:
            scalars['WindScale'] = 0.0
        if not masked and 'Bark' in mat_name:
            scalars['GroundBlend'] = 1.0  # tree trunks carry the UVMask channel
        materials[mat_name] = instance(folder, mat_name, parents[masked], tex, scalars)
    def tinted(mi, colour):
        EDIT.set_material_instance_vector_parameter_value(mi, 'Tint', unreal.LinearColor(colour[0], colour[1], colour[2], 1.0))
        EDIT.update_material_instance(mi)
        save(mi)
        return mi
    for mat_name, colour in foliage_tints.items():
        tinted(materials[mat_name], colour)
    if 'MI_Veg_Understory_Frost' in derived and 'MI_Veg_Understory' in sets:
        # hoar frost on bare twigs: the understory set multiplied up, no light through the leaves
        materials['MI_Veg_Understory_Frost'] = tinted(instance(folder, 'MI_Veg_Understory_Frost', parents[True], sets['MI_Veg_Understory'][1],
                                                                 {'AlphaClip': 0.33, 'Translucency': 0.0}), (2.6, 2.8, 3.2))
    if 'MI_Terrain_TransitionDirt_Tilled' in derived:
        dirt = {role: import_texture(PASS / 'Terrain/TransitionDirt' / f'T_Terrain_TransitionDirt_{role}.png', tex_folder, role) for role in ('BC', 'N', 'ORM')}
        materials['MI_Terrain_TransitionDirt_Tilled'] = tinted(instance(folder, 'MI_Terrain_TransitionDirt_Tilled', parents[False], dirt, {'WindScale': 0.0}), (0.5, 0.44, 0.4))
    for name in derived:
        if name not in materials:
            warn(f'{name}: derived material of the vegetation manifest is not handled by the importer')
    # the grass carpet: a "_Scatter" twin of each ground-cover material, colour-matched to the ground under it and
    # thinned out with distance by the material (UDinkEnvironmentSubsystem picks the twin by name)
    # olive-yellow like the MeadowTurf scan under it (sRGB 85, 99, 58), so far grass and terrain run together
    for source, colour in (('MI_Veg_GroundCover', (0.60, 0.58, 0.34)), ('MI_Veg_Understory', (0.60, 0.50, 0.27)), ('MI_Veg_MeadowGrass', (0.58, 0.58, 0.385))):   # round 6: slightly less saturated field
        if source in sets and source == 'MI_Veg_MeadowGrass':
            # the Tall / Short / Dry field patches (round 5): the Dry mesh carries the straw, so no painted dry patches here
            tinted(instance(folder, source + '_Scatter', parents[True], sets[source][1],
                            {'AlphaClip': 0.33, 'ScatterFade': 1.0, 'FadeNearCm': 1200.0, 'FadeFarCm': 3700.0, 'GroundMatch': 1.0, 'Translucency': 0.10,
                             'Specular': 0.10, 'CrownShade': 1.0, 'CrownAO': 1.0, 'RootShade': 0.55, 'TipLight': 1.25, 'DryPatches': 0.25}), colour)
        elif source in sets:
            tinted(instance(folder, source + '_Scatter', parents[True], sets[source][1],
                            {'AlphaClip': 0.33, 'ScatterFade': 1.0, 'FadeNearCm': 1200.0, 'FadeFarCm': 3700.0, 'GroundMatch': 1.0, 'Translucency': 0.10,
                             'Specular': 0.10, 'CrownShade': 1.0, 'CrownAO': 1.0, 'RootShade': 0.55, 'TipLight': 1.25, 'DryPatches': 0.7}), colour)
    for asset in manifest['assets']:
        fbx = [VEG / lod['fbx'] for lod in sorted(asset['lods'], key=lambda l: l['lod'])]
        mesh, changed = import_static(fbx, folder, asset['name'], import_normals=True)
        assign_slots(mesh, materials, asset['name'])
        # visual only: no collision; cards must not build distance fields that black out Lumen under the crown
        nanite = mesh.get_editor_property('nanite_settings')
        nanite.set_editor_property('enabled', False)
        mesh.set_editor_property('nanite_settings', nanite)
        size = check_size(mesh, asset['dimensions_m'], asset['name'])
        save(mesh)
        report['vegetation'].append({'mesh': folder + '/' + asset['name'], 'lods': MESHES.get_lod_count(mesh), 'size_m': size,
                                     'families': asset['families'], 'reimported': changed})

FROZEN = False

# ------------------------------------------------------------------------------------------- scatter
if 'scatter' in ONLY:
    TER = PASS / 'Terrain'
    manifest = json.loads((TER / 'manifest.json').read_text())
    folder = BASE + '/Scatter'
    tex_folder = folder + '/Textures'
    rows = [r for r in manifest.get('scatter_meshes', []) if r['name'] in SCATTER_ALLOW]
    materials = {}
    parent = None
    for row in rows:
        if row['material'] in materials:
            continue
        tex = {role: import_texture(TER / path, tex_folder, role) for role, path in row['textures'].items() if role in ('BC', 'N', 'ORM')}
        if parent is None:
            parent = surface_material(folder, 'M_Scatter_Stone', tex)
        materials[row['material']] = instance(folder, row['material'], parent, tex)
    for row in rows:
        mesh, changed = import_scatter(TER / row['fbx'], folder, row['name'])
        assign_slots(mesh, materials, row['name'])
        size = check_size(mesh, row['dimensions_m'], row['name'])
        save(mesh)
        report['scatter'].append({'mesh': folder + '/' + row['name'], 'lods': MESHES.get_lod_count(mesh), 'size_m': size,
                                  'families': row['families'], 'reimported': changed})

# ------------------------------------------------------------------------------------------- wall kits
if 'walls' in ONLY:
    WALLS = PASS / 'WallKits'
    TER = PASS / 'Terrain'
    manifest = json.loads((WALLS / 'manifest.json').read_text())
    folder = BASE + '/WallKits'
    tex_folder = folder + '/Textures'
    sets = {}
    for set_name in ('DungeonMasonry', 'DungeonMasonryDamp'):
        sets[set_name] = {role: import_texture(TER / set_name / f'T_Terrain_{set_name}_{role}.png', tex_folder, role) for role in ('BC', 'N', 'ORM')}
    for set_name in ('PlasterWall', 'PlasterWallBroken', 'TimberBeam'):
        sets[set_name] = {role: import_texture(TER / set_name / f'T_Terrain_{set_name}_{role}.png', tex_folder, role) for role in ('BC', 'N', 'ORM')}
    for set_name in ('PlasterWall', 'DungeonMasonry'):  # height of the first set drives the hand-over to the second
        sets[set_name]['H'] = import_texture(TER / set_name / f'T_Terrain_{set_name}_H.png', tex_folder, 'ORM', max_size=1024)
    def second(name):
        return {'BC2': sets[name]['BC'], 'N2': sets[name]['N'], 'ORM2': sets[name]['ORM']}
    masonry = surface_material(folder, 'M_Wall_Masonry', sets['DungeonMasonry'], blend=dict(sets['DungeonMasonryDamp'], H=sets['DungeonMasonry']['H']))
    plaster = surface_material(folder, 'M_Wall_Plaster', sets['PlasterWall'], blend=dict(sets['PlasterWallBroken'], H=sets['PlasterWall']['H']), blend_channel='b')
    timber = surface_material(folder, 'M_Wall_Timber', sets['TimberBeam'], timber=True)
    # the indoor set's backdrop (UDinkEnvironmentSubsystem): unlit black, one-sided
    black = new_material(folder, 'M_Env_IndoorBlack')
    black.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    out(expr(black, unreal.MaterialExpressionConstant3Vector, -300, 0, constant=unreal.LinearColor(0.0, 0.0, 0.0, 1.0)), '', MP.MP_EMISSIVE_COLOR)
    EDIT.recompile_material(black)
    save(black)
    wall_materials = {
        'MI_Wall_DungeonMasonry': instance(folder, 'MI_Wall_DungeonMasonry', masonry, dict(sets['DungeonMasonry'], **second('DungeonMasonryDamp'))),
        'MI_Wall_Plaster': instance(folder, 'MI_Wall_Plaster', plaster, dict(sets['PlasterWall'], **second('PlasterWallBroken'))),
        'MI_Wall_Timber': instance(folder, 'MI_Wall_Timber', timber, sets['TimberBeam'])}
    for row in manifest['modules']:
        if row['name'] not in WALL_ALLOW:
            continue
        # same two-object layout as the scatter files; UCX collision hulls are dropped (family art is visual only)
        mesh, changed = import_scatter(WALLS / row['fbx'], folder, row['name'])
        assign_slots(mesh, wall_materials, row['name'])
        size = check_size(mesh, row['dimensions_m'], row['name'])
        save(mesh)
        report['walls'].append({'mesh': folder + '/' + row['name'], 'lods': MESHES.get_lod_count(mesh), 'size_m': size,
                                'families': row['families'], 'reimported': changed})

# ------------------------------------------------------------------------------------------- hero
# round 6: Mother and Milder go the same way (DINK_PHOTOREAL_ONLY=mother,milder), each into /Game/Dink/Photoreal/Characters/<Name>
for CHAR in [c for c, k in (('Dink', 'hero'), ('Mother', 'mother'), ('Milder', 'milder')) if k in ONLY]:
    HERO = PASS / 'Characters' / CHAR
    report['hero'] = {}
    report.setdefault('characters', {})[CHAR] = report['hero']
    manifest = json.loads((HERO / 'manifest.json').read_text())
    folder = BASE + '/Characters/' + CHAR
    tex_folder = folder + '/Textures'
    name = manifest['asset']
    target = folder + '/' + name
    reference_mesh = LIB.load_asset('/Game/Dink/Hero/Refinements/SK_Dink_Hands')
    if reference_mesh is None:
        raise RuntimeError('reference hero mesh missing')
    skeleton = reference_mesh.get_editor_property('skeleton')
    profile_path = folder + '/SP_Dink_PR_Skin'
    profile = LIB.load_asset(profile_path) if LIB.does_asset_exist(profile_path) else None
    if profile is None:
        try:
            profile = TOOLS.create_asset('SP_Dink_PR_Skin', folder, unreal.SubsurfaceProfile, None)
            if profile is not None:
                save(profile)
        except Exception as error:  # fall back to plain subsurface shading
            warn(f'subsurface profile could not be created ({error}); skin uses the Subsurface shading model')
            profile = None
    if profile is not None:
        try:
            settings = profile.get_editor_property('settings')
            # fair skin: red travels furthest; a short mean free path keeps pores and creases readable
            for key, value in {'surface_albedo': unreal.LinearColor(0.80, 0.56, 0.45, 1.0), 'mean_free_path_color': unreal.LinearColor(1.0, 0.32, 0.18, 1.0),
                               'mean_free_path_distance': 0.5, 'world_unit_scale': 0.1, 'tint': unreal.LinearColor(1.0, 1.0, 1.0, 1.0),
                               'boundary_color_bleed': unreal.LinearColor(0.9, 0.45, 0.35, 1.0)}.items():
                settings.set_editor_property(key, value)
            profile.set_editor_property('settings', settings)
            save(profile)
        except Exception as error:
            warn(f'subsurface profile settings not applied ({error})')
    materials = {}
    has_shapes = any(lod.get('shape_keys') for lod in manifest.get('lods', []))
    for mat_name, row in manifest['materials'].items():
        masked = 'masked' in row['shading'].lower()
        tex = {}
        for role, rel in row['textures'].items():
            tex[role] = import_texture(HERO / rel, tex_folder, 'BCA' if (role == 'BC' and masked) else role)
        kind = 'skin' if 'SSS' in tex else 'hair' if 'Hair' in mat_name else 'eye' if 'Eyes' in mat_name else 'lit'
        if kind == 'hair' and HAIR_MODEL == 'hair' and 'FLOW' in tex and 'MSK' in tex:
            parent = hair_material(folder, 'M_' + mat_name[3:], tex, morph=has_shapes)
        else:
            parent = surface_material(folder, 'M_' + mat_name[3:], tex, skeletal=True, shading=kind, masked=masked, two_sided=masked,
                                      profile=profile if kind == 'skin' else None, morph=has_shapes)
        # NormalStrength 0.6 on skin (14 Nov 2026): at full strength the pore and crease relief, right in the Blender
        # renders, read as orange peel and goose flesh under the game's sun and window light
        materials[mat_name] = instance(folder, mat_name, parent, tex, {'ScatterAmount': 0.35, 'NormalStrength': 0.6} if kind == 'skin' else None)
        # Calibrated 12 Nov 2026 against Characters/contact_sheet.png (face close-up in sun, dink.CalCam): at the full
        # scatter strength the face blew out pale and flat (freckles, lids and nose shading gone); the hair read brown.
        look = {'skin': SKIN_LOOK.get(CHAR, (0.86, 0.82, 0.80)), 'hair': (1.4, 1.2, 1.05)}.get(kind)
        if kind == 'hair' and HAIR_MODEL == 'hair':
            # The Hair model scatters light through the strands, so the atlas colour needs no brightening; the tint
            # only trims the hue per character (calibrated in the running game, see HAIR_LOOK). DINK_HAIR_TINT_<Name>
            # ("r,g,b") and DINK_HAIR_PARAMS ("Scatter=0.6,Backlit=0.8") override it for a calibration run.
            look = HAIR_LOOK.get(CHAR, {}).get('tint', (1.0, 1.0, 1.0))
            env = os.environ.get('DINK_HAIR_TINT_' + CHAR)
            if env:
                look = tuple(float(x) for x in env.split(','))
            scal = dict(HAIR_LOOK.get(CHAR, {}).get('scalars', {}))
            for item in filter(None, os.environ.get('DINK_HAIR_PARAMS', '').split(',')):
                scal[item.split('=')[0]] = float(item.split('=')[1])
            for k, v in scal.items():
                EDIT.set_material_instance_scalar_parameter_value(materials[mat_name], k, float(v))
        if look:
            EDIT.set_material_instance_vector_parameter_value(materials[mat_name], 'Tint', unreal.LinearColor(look[0], look[1], look[2], 1.0))
            EDIT.update_material_instance(materials[mat_name])
            save(materials[mat_name])
    fbx = [HERO / f for f in manifest['fbx']]
    key = '|'.join(stamp_of(f) for f in fbx)
    mesh = LIB.load_asset(target) if LIB.does_asset_exist(target) else None
    if mesh is None or LIB.get_metadata_tag(mesh, 'DinkSource') != key:
        options = unreal.FbxImportUI()
        for k, v in {'automated_import_should_detect_type': False, 'mesh_type_to_import': unreal.FBXImportType.FBXIT_SKELETAL_MESH,
                     'import_as_skeletal': True, 'import_mesh': True, 'import_materials': False, 'import_textures': False,
                     'import_animations': False, 'create_physics_asset': True}.items():
            options.set_editor_property(k, v)
        # a first import gets its own skeleton and is then gated onto the shared one; a re-import keeps the shared one
        options.set_editor_property('skeleton', skeleton if mesh is not None else None)
        data = options.skeletal_mesh_import_data
        settings = {'convert_scene': True, 'convert_scene_unit': True, 'import_uniform_scale': 1.0,
                    'update_skeleton_reference_pose': False, 'use_t0_as_ref_pose': False, 'import_mesh_lods': False,
                    'import_meshes_in_bone_hierarchy': True,
                    # build shapes (Physique_*, see Characters/Tools/physique.py) arrive as FBX blend shapes
                    'import_morph_targets': True,
                    'normal_import_method': unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS}
        for k, v in settings.items():
            data.set_editor_property(k, v)
        if mesh is not None:
            # A re-import reads its options from the mesh's stored FBX import data, not from the task. import_lod goes
            # through Interchange and leaves Interchange import data on the mesh; the FBX re-import then falls back to
            # engine defaults, which drop morph targets. So the mesh gets FBX import data with these settings first.
            old = mesh.get_editor_property('asset_import_data')
            if not isinstance(old, unreal.FbxSkeletalMeshImportData):
                old = unreal.new_object(unreal.FbxSkeletalMeshImportData, outer=mesh)
                mesh.set_editor_property('asset_import_data', old)
            for k, v in settings.items():
                old.set_editor_property(k, v)
            old.scripted_add_filename(str(fbx[0].resolve()), 0, '')
        task = unreal.AssetImportTask()
        task.filename = str(fbx[0].resolve())
        task.destination_path = folder
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        task.options = options
        task.factory = unreal.FbxFactory()
        TOOLS.import_asset_tasks([task])
        mesh = LIB.load_asset(target)
        if mesh is None:
            raise RuntimeError('hero import failed')
        rig = json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(mesh))
        reference = json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(reference_mesh))
        if {b['name'] for b in rig['bones']} != {b['name'] for b in reference['bones']}:
            raise RuntimeError('hero bones differ from the shared rig')
        if not unreal.DinkCharacterArtLibrary.assign_matching_skeleton(mesh, reference_mesh):
            raise RuntimeError('hero bind pose does not match the shared animation rig (native gate refused it)')
        for index, f in enumerate(fbx[1:], 1):
            if unreal.SkeletalMeshEditorSubsystem.import_lod(mesh, index, str(f.resolve())) != index:
                raise RuntimeError(f'hero LOD{index} import failed')
        # every shape key the source declares must have arrived, with data on every LOD
        wanted = sorted({k for lod in manifest.get('lods', []) for k in lod.get('shape_keys', [])})
        if wanted:
            got = {m['name']: m['lod_moved_vertices'] for m in json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(mesh)).get('morph_targets', [])}
            for shape in wanted:
                if shape not in got or len(got[shape]) != len(fbx) or min(got[shape]) <= 0:
                    raise RuntimeError(f'hero shape key {shape} did not import on every LOD: {got.get(shape)}')
            report['hero']['shape_keys'] = {shape: got[shape] for shape in wanted}
        LIB.set_metadata_tag(mesh, 'DinkSource', key)
        report['hero']['bounds_size_cm'] = rig['bounds_size_cm']
    slots = list(mesh.get_editor_property('materials'))
    for slot in slots:
        slot_key = str(slot.get_editor_property('material_slot_name')).split('.')[0]
        if slot_key not in materials:
            raise RuntimeError(f'hero: unknown material slot {slot_key}')
        slot.set_editor_property('material_interface', materials[slot_key])
    mesh.set_editor_property('materials', slots)
    physics = mesh.get_editor_property('physics_asset')
    if physics is None:
        physics = unreal.SkeletalMeshEditorSubsystem.create_physics_asset(mesh, True, 0)
    if physics is not None:
        save(physics)
    save(mesh)
    report['hero'].update({'mesh': target, 'lods': unreal.SkeletalMeshEditorSubsystem.get_lod_count(mesh),
                           'skeleton': mesh.get_editor_property('skeleton').get_path_name(),
                           'slots': [str(s.get_editor_property('material_slot_name')) for s in slots],
                           'skin_shading': 'subsurface profile' if profile is not None else 'subsurface'})

def creature_skeletal_options(skeleton):
    options = unreal.FbxImportUI()
    for k, v in {'automated_import_should_detect_type': False, 'mesh_type_to_import': unreal.FBXImportType.FBXIT_SKELETAL_MESH,
                 'import_as_skeletal': True, 'import_mesh': True, 'import_materials': False, 'import_textures': False,
                 'import_animations': False, 'create_physics_asset': False}.items():
        options.set_editor_property(k, v)
    options.set_editor_property('skeleton', skeleton)
    data = options.skeletal_mesh_import_data
    for k, v in {'convert_scene': True, 'convert_scene_unit': True, 'import_uniform_scale': 1.0, 'update_skeleton_reference_pose': False,
                 'use_t0_as_ref_pose': False, 'import_mesh_lods': False, 'import_meshes_in_bone_hierarchy': True,
                 'vertex_color_import_option': unreal.VertexColorImportOption.REPLACE,
                 'normal_import_method': unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS}.items():
        data.set_editor_property(k, v)
    return options


def creature_mesh(source_dir, source, folder, name, skeleton, materials):
    """A photoreal creature's skeletal mesh from Export/<source>_LOD0..2.fbx -> (mesh, rig, slot names).
    `skeleton` None: the mesh brings its own; else the import targets it."""
    target = folder + '/' + name
    fbx = [source_dir / f'Export/{source}_LOD{i}.fbx' for i in range(3)]
    key = '|'.join(stamp_of(f) for f in fbx)
    mesh = LIB.load_asset(target) if LIB.does_asset_exist(target) else None
    if mesh is None or LIB.get_metadata_tag(mesh, 'DinkSource') != key:
        if mesh is not None and skeleton is not None:
            LIB.delete_asset(target)
        task = unreal.AssetImportTask()
        task.filename = str(fbx[0].resolve())
        task.destination_path = folder
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        task.options = creature_skeletal_options(skeleton if skeleton is not None else (mesh.get_editor_property('skeleton') if mesh is not None else None))
        task.factory = unreal.FbxFactory()
        TOOLS.import_asset_tasks([task])
        mesh = LIB.load_asset(target)
        if mesh is None:
            raise RuntimeError(f'{name}: import failed')
        for index, f in enumerate(fbx[1:], 1):
            if unreal.SkeletalMeshEditorSubsystem.import_lod(mesh, index, str(f.resolve())) != index:
                raise RuntimeError(f'{name}: LOD{index} import failed')
        LIB.set_metadata_tag(mesh, 'DinkSource', key)
    slots = list(mesh.get_editor_property('materials'))
    for slot in slots:
        slot_key = str(slot.get_editor_property('material_slot_name')).split('.')[0]
        if slot_key not in materials:
            raise RuntimeError(f'{name}: unknown material slot {slot_key}')
        slot.set_editor_property('material_interface', materials[slot_key])
    mesh.set_editor_property('materials', slots)
    rig = json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(mesh))
    if any(math.dist(b['scale'], [1, 1, 1]) > 0.001 for b in rig['bones']):
        raise RuntimeError(f'{name}: non-unit reference bone scale')
    return mesh, rig, [str(s.get_editor_property('material_slot_name')) for s in slots]


def creature_clips(source_dir, source_prefix, folder, asset_prefix, skeleton, actions):
    """In-place clips Export/<source_prefix>_<Action>.fbx -> <folder>/Animations/<asset_prefix>_<Action>. actions: (name, loops)."""
    clips = {}
    for action, loop in actions:
        fbx = source_dir / f'Export/{source_prefix}_{action}.fbx'
        if not fbx.exists():
            continue
        name = f'{asset_prefix}_{action}'
        target = folder + '/Animations/' + name
        anim = LIB.load_asset(target) if LIB.does_asset_exist(target) else None
        if anim is None or LIB.get_metadata_tag(anim, 'DinkSource') != stamp_of(fbx):
            if anim is not None:
                LIB.delete_asset(target)
            options = unreal.FbxImportUI()
            for k, v in {'automated_import_should_detect_type': False, 'mesh_type_to_import': unreal.FBXImportType.FBXIT_ANIMATION,
                         'import_as_skeletal': True, 'import_mesh': False, 'import_materials': False, 'import_textures': False,
                         'import_animations': True, 'create_physics_asset': False, 'skeleton': skeleton}.items():
                options.set_editor_property(k, v)
            for k, v in {'convert_scene': True, 'convert_scene_unit': True, 'import_uniform_scale': 1.0, 'import_bone_tracks': True,
                         'use_default_sample_rate': False, 'custom_sample_rate': 30,
                         'animation_length': unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME}.items():
                options.anim_sequence_import_data.set_editor_property(k, v)
            task = unreal.AssetImportTask()
            task.filename = str(fbx.resolve())
            task.destination_path = folder + '/Animations'
            task.destination_name = name
            task.automated = True
            task.replace_existing = True
            task.save = False
            task.options = options
            task.factory = unreal.FbxFactory()
            TOOLS.import_asset_tasks([task])
            anim = LIB.load_asset(target)
            if anim is None:
                raise RuntimeError(f'{name}: import failed')
            LIB.set_metadata_tag(anim, 'DinkSource', stamp_of(fbx))
        inspection = json.loads(unreal.DinkCharacterArtLibrary.inspect_creature_animation(anim))
        if inspection.get('skeleton') != skeleton.get_path_name() or inspection.get('duration_s', 0) <= 0 or not inspection.get('finite_poses'):
            raise RuntimeError(f'{name}: invalid imported animation')
        if inspection['root_motion_cm'] > 0.1 or inspection['max_scale_error'] > 0.001:
            raise RuntimeError(f'{name}: root motion or bone scaling in an in-place clip')
        if loop and (inspection['loop_seam_rotation_rad'] > 0.05 or inspection['loop_seam_translation_cm'] > 0.2):
            raise RuntimeError(f'{name}: loop seam does not close')
        save(anim)
        clips[action] = {'clip': target, 'duration_s': round(inspection['duration_s'], 4), 'loop': loop}
    return clips


# ------------------------------------------------------------------------------------------- pillbug (round 6)
# DINK_PHOTOREAL_ONLY=pillbug: Creatures/Pillbug -> /Game/Dink/Photoreal/Creatures/Pillbug (SK_Pillbug_Photoreal on the
# existing 43-bone pillbug skeleton, behind dink.PhotorealPillbug; SM_Pillbug_Corpse_PR, the burst carcass). A rig that
# differs from /Game/Dink/Creatures/Pillbug/SK_Pillbug is reported, never forced.
if 'pillbug' in ONLY:
    PB = PASS / 'Creatures/Pillbug'
    folder = BASE + '/Creatures/Pillbug'
    tex_folder = folder + '/Textures'
    report['pillbug'] = {}
    try:
        reference_mesh = LIB.load_asset('/Game/Dink/Creatures/Pillbug/SK_Pillbug')
        if reference_mesh is None:
            raise RuntimeError('reference pillbug mesh missing')
        skeleton = reference_mesh.get_editor_property('skeleton')
        atlas = {role: import_texture(PB / f'Textures/T_Pillbug_Atlas_{role}.png', tex_folder, role) for role in ('BC', 'N', 'ORM')}
        gore = {role: import_texture(PB / f'Textures/T_Pillbug_Gore_{role}.png', tex_folder, role) for role in ('BC', 'N', 'ORM')}
        parent = surface_material(folder, 'M_Pillbug_PR', atlas, skeletal=True)
        materials = {n: instance(folder, n + '_PR', parent, atlas) for n in ('MI_Pillbug_Carapace', 'MI_Pillbug_Ochre', 'MI_Pillbug_Joints', 'MI_Pillbug_Eyes')}
        materials['MI_Pillbug_Gore'] = instance(folder, 'MI_Pillbug_Gore_PR', parent, gore)
        materials['MI_Pillbug_Gore_Procedural'] = materials['MI_Pillbug_Gore']   # the corpse FBX names its gore slot so; the manifest says MI_Pillbug_Gore
        # the carcass body: the same atlas with blood across the plates (sprites 141/143), and the pool as a ground decal
        bloody = dict(atlas, BC=import_texture(PB / 'Textures/T_Pillbug_Corpse_BC.png', tex_folder, 'BC'), ORM=import_texture(PB / 'Textures/T_Pillbug_Corpse_ORM.png', tex_folder, 'ORM'))
        for n in ('MI_Pillbug_Carapace', 'MI_Pillbug_Ochre', 'MI_Pillbug_Joints', 'MI_Pillbug_Eyes'):
            materials[n + '_Bloody'] = instance(folder, n + '_Bloody_PR', parent, bloody)
        pool = decal_material(folder, 'M_Pillbug_BloodPool_Decal', import_texture(PB / 'Textures/T_Pillbug_BloodPool_BC.png', tex_folder, 'BCA', wrap=False))
        name = 'SK_Pillbug_Photoreal'
        target = folder + '/' + name
        fbx = [PB / f'Export/SK_Pillbug_LOD{i}.fbx' for i in range(3)]
        key = '|'.join(stamp_of(f) for f in fbx)
        mesh = LIB.load_asset(target) if LIB.does_asset_exist(target) else None
        if mesh is None or LIB.get_metadata_tag(mesh, 'DinkSource') != key:
            if mesh is not None:
                LIB.delete_asset(target)
                mesh = None
            options = unreal.FbxImportUI()
            for k, v in {'automated_import_should_detect_type': False, 'mesh_type_to_import': unreal.FBXImportType.FBXIT_SKELETAL_MESH,
                         'import_as_skeletal': True, 'import_mesh': True, 'import_materials': False, 'import_textures': False,
                         'import_animations': False, 'create_physics_asset': False}.items():
                options.set_editor_property(k, v)
            options.set_editor_property('skeleton', None)   # its own skeleton first; the native gate then decides
            data = options.skeletal_mesh_import_data
            for k, v in {'convert_scene': True, 'convert_scene_unit': True, 'import_uniform_scale': 1.0, 'update_skeleton_reference_pose': False,
                         'use_t0_as_ref_pose': False, 'import_mesh_lods': False, 'import_meshes_in_bone_hierarchy': True,
                         'normal_import_method': unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS}.items():
                data.set_editor_property(k, v)
            task = unreal.AssetImportTask()
            task.filename = str(fbx[0].resolve())
            task.destination_path = folder
            task.destination_name = name
            task.automated = True
            task.replace_existing = True
            task.save = False
            task.options = options
            task.factory = unreal.FbxFactory()
            TOOLS.import_asset_tasks([task])
            mesh = LIB.load_asset(target)
            if mesh is None:
                raise RuntimeError('pillbug import failed')
            rig = json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(mesh))
            reference = json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(reference_mesh))
            mine, theirs = {b['name'] for b in rig['bones']}, {b['name'] for b in reference['bones']}
            report['pillbug'].update({'bones': len(mine), 'reference_bones': len(theirs), 'bounds_size_cm': rig.get('bounds_size_cm'),
                                      'reference_bounds_size_cm': reference.get('bounds_size_cm')})
            if mine != theirs:
                report['pillbug']['bone_difference'] = {'only_new': sorted(mine - theirs), 'only_reference': sorted(theirs - mine)}
                raise RuntimeError('pillbug bones differ from the existing rig: ' + json.dumps(report['pillbug']['bone_difference']))
            if not unreal.DinkCharacterArtLibrary.assign_matching_skeleton(mesh, reference_mesh):
                raise RuntimeError('pillbug bind pose does not match the existing skeleton (native gate refused it)')
            for index, f in enumerate(fbx[1:], 1):
                if unreal.SkeletalMeshEditorSubsystem.import_lod(mesh, index, str(f.resolve())) != index:
                    raise RuntimeError(f'pillbug LOD{index} import failed')
            LIB.set_metadata_tag(mesh, 'DinkSource', key)
        slots = list(mesh.get_editor_property('materials'))
        for slot in slots:
            slot_key = str(slot.get_editor_property('material_slot_name')).split('.')[0]
            if slot_key not in materials:
                raise RuntimeError(f'pillbug: unknown material slot {slot_key}')
            slot.set_editor_property('material_interface', materials[slot_key])
        mesh.set_editor_property('materials', slots)
        save(mesh)
        report['pillbug'].update({'mesh': target, 'lods': unreal.SkeletalMeshEditorSubsystem.get_lod_count(mesh),
                                  'skeleton': mesh.get_editor_property('skeleton').get_path_name(),
                                  'slots': [str(s.get_editor_property('material_slot_name')) for s in slots]})
        corpse, changed = import_static([PB / f'Export/SM_Pillbug_Corpse_LOD{i}.fbx' for i in range(3)], folder, 'SM_Pillbug_Corpse_PR', True)
        assign_slots(corpse, materials, 'SM_Pillbug_Corpse_PR')
        save(corpse)
        box = corpse.get_bounding_box()
        report['pillbug']['corpse'] = {'mesh': folder + '/SM_Pillbug_Corpse_PR', 'lods': MESHES.get_lod_count(corpse), 'reimported': changed, 'pool_decal': pool.get_path_name(),
                                       'size_cm': [round(box.max.x - box.min.x, 1), round(box.max.y - box.min.y, 1), round(box.max.z - box.min.z, 1)]}
    except Exception as error:
        report['pillbug']['error'] = str(error)
        warn(f'pillbug not imported: {error}')

# ------------------------------------------------------------------------------------------- pig (gate 2 creatures)
# DINK_PHOTOREAL_ONLY=pig: Creatures/Pig -> /Game/Dink/Photoreal/Creatures/Pig/SK_Pig_Photoreal on the existing 26-bone pig
# skeleton (the clips of /Game/Dink/Creatures/Pig apply as they are). A rig that differs is reported, never forced.
if 'pig' in ONLY:
    PG = PASS / 'Creatures/Pig'
    folder = BASE + '/Creatures/Pig'
    tex_folder = folder + '/Textures'
    report['pig'] = {}
    try:
        reference_mesh = LIB.load_asset('/Game/Dink/Creatures/Pig/SK_Pig')
        if reference_mesh is None:
            raise RuntimeError('reference pig mesh missing')
        skeleton = reference_mesh.get_editor_property('skeleton')
        atlas = {r: import_texture(PG / f'Textures/T_Pig_Atlas_{r}.png', tex_folder, r) for r in ('BC', 'N', 'ORM')}
        cards = {r: import_texture(PG / f'Textures/T_Pig_BristleCards_{r}.png', tex_folder, 'BCA' if r == 'BC' else r) for r in ('BC', 'N', 'ORM')}
        parent = surface_material(folder, 'M_Pig_PR', atlas, skeletal=True)
        card_parent = surface_material(folder, 'M_Pig_BristleCards_PR', cards, skeletal=True, masked=True, two_sided=True)
        materials = {n: instance(folder, n + '_PR', parent, atlas) for n in ('MI_Pig_Skin', 'MI_Pig_Muzzle', 'MI_Pig_Eye')}
        materials['MI_Pig_HornBristle'] = instance(folder, 'MI_Pig_HornBristle_PR', card_parent, cards)
        mesh, rig, slots = creature_mesh(PG, 'SK_Pig', folder, 'SK_Pig_Photoreal', skeleton, materials)
        reference = json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(reference_mesh))
        mine, theirs = {b['name'] for b in rig['bones']}, {b['name'] for b in reference['bones']}
        if mine != theirs:
            raise RuntimeError('pig bones differ from the existing rig: ' + json.dumps({'only_new': sorted(mine - theirs), 'only_reference': sorted(theirs - mine)}))
        if mesh.get_editor_property('skeleton') != skeleton and not unreal.DinkCharacterArtLibrary.assign_matching_skeleton(mesh, reference_mesh):
            raise RuntimeError('pig bind pose does not match the existing skeleton (native gate refused it)')
        save(mesh)
        report['pig'].update({'mesh': folder + '/SK_Pig_Photoreal', 'skeleton': mesh.get_editor_property('skeleton').get_path_name(), 'bones': len(mine),
                              'bounds_size_cm': rig.get('bounds_size_cm'), 'reference_bounds_size_cm': reference.get('bounds_size_cm'),
                              'lods': unreal.SkeletalMeshEditorSubsystem.get_lod_count(mesh), 'slots': slots})
    except Exception as error:
        report['pig']['error'] = str(error)
        warn(f'pig not imported: {error}')

# ------------------------------------------------------------------------------------------- slime (gate 2 creatures)
# DINK_PHOTOREAL_ONLY=slime: Creatures/Slime -> /Game/Dink/Photoreal/Creatures/Slime. SK_Slime_PR (its own 10-bone rig), four
# clips, one material set per colour (blue, green, red) and, per colour, what a killed slime leaves: SM_Slime_Splat_<Colour>
# and its ground decal (sequences 661/663, 681/683, 701/703). The gel is opaque here: the see-through material of the
# source notes is not built.
if 'slime' in ONLY:
    SL = PASS / 'Creatures/Slime'
    folder = BASE + '/Creatures/Slime'
    tex_folder = folder + '/Textures'
    report['slime'] = {}
    try:
        shared = {r: import_texture(SL / f'Textures/T_Slime_Blue_{r}.png', tex_folder, r) for r in ('N', 'ORM')}
        core_shared = {r: import_texture(SL / f'Textures/T_Slime_Core_Blue_{r}.png', tex_folder, r) for r in ('N', 'ORM')}
        wet = {r: import_texture(SL / f'Textures/T_Slime_Wet_{r}.png', tex_folder, r) for r in ('BC', 'N', 'ORM')}
        sets = {}
        for colour in ('Blue', 'Green', 'Red'):
            sets[colour] = (dict(shared, BC=import_texture(SL / f'Textures/T_Slime_{colour}_BC.png', tex_folder, 'BC')),
                            dict(core_shared, BC=import_texture(SL / f'Textures/T_Slime_Core_{colour}_BC.png', tex_folder, 'BC')))
        parent = surface_material(folder, 'M_Slime_PR', sets['Blue'][0], skeletal=True)
        materials = {'MI_Slime': instance(folder, 'MI_Slime_Blue_PR', parent, sets['Blue'][0]),
                     'MI_Slime_Core': instance(folder, 'MI_Slime_Core_Blue_PR', parent, sets['Blue'][1]),
                     'MI_Slime_Wet': instance(folder, 'MI_Slime_Wet_PR', parent, wet)}
        variants = {'Blue': {'MI_Slime': materials['MI_Slime'].get_path_name(), 'MI_Slime_Core': materials['MI_Slime_Core'].get_path_name()}}
        for colour in ('Green', 'Red'):
            shell = instance(folder, f'MI_Slime_{colour}_PR', parent, sets[colour][0])
            core = instance(folder, f'MI_Slime_Core_{colour}_PR', parent, sets[colour][1])
            variants[colour] = {'MI_Slime': shell.get_path_name(), 'MI_Slime_Core': core.get_path_name()}
        slime, rig, slots = creature_mesh(SL, 'SK_Slime', folder, 'SK_Slime_PR', None, materials)
        skeleton = slime.get_editor_property('skeleton')
        save(skeleton); save(slime)
        report['slime'].update({'mesh': folder + '/SK_Slime_PR', 'skeleton': skeleton.get_path_name(), 'bones': len(rig['bones']),
                                'bounds_size_cm': rig.get('bounds_size_cm'), 'lods': unreal.SkeletalMeshEditorSubsystem.get_lod_count(slime),
                                'slots': slots, 'variants': variants})
        report['slime']['clips'] = creature_clips(SL, 'A_Slime', folder, 'AN_Slime', skeleton, (('Idle', True), ('Walk', True), ('Attack', False), ('Death', False)))
        splats = {}
        for colour in ('Blue', 'Green', 'Red'):
            mesh, changed = import_static([SL / 'Export/SM_Slime_Splat.fbx'], folder, f'SM_Slime_Splat_{colour}', True)
            # thrown gel: one wet colour (the atlas of the living slime does not map onto these blobs)
            gel = new_material(folder, f'M_SlimeGel_{colour}')
            tint = {'Blue': (0.10, 0.17, 0.50), 'Green': (0.36, 0.35, 0.06), 'Red': (0.42, 0.13, 0.09)}[colour]
            out(expr(gel, unreal.MaterialExpressionConstant3Vector, -400, 0, constant=unreal.LinearColor(tint[0], tint[1], tint[2], 1.0)), '', MP.MP_BASE_COLOR)
            out(expr(gel, unreal.MaterialExpressionConstant, -400, 200, r=0.12), '', MP.MP_ROUGHNESS)
            out(expr(gel, unreal.MaterialExpressionConstant, -400, 300, r=0.6), '', MP.MP_SPECULAR)
            EDIT.recompile_material(gel)
            save(gel)
            assign_slots(mesh, {'MI_Slime': gel}, f'SM_Slime_Splat_{colour}')
            save(mesh)
            decal = decal_material(folder, f'M_SlimeSplat_{colour}_Decal', import_texture(SL / f'Textures/T_SlimeSplat_{colour}_BC.png', tex_folder, 'BCA', wrap=False), roughness=0.5)
            splats[colour] = {'mesh': folder + f'/SM_Slime_Splat_{colour}', 'decal': decal.get_path_name()}
        report['slime']['splats'] = splats
    except Exception as error:
        report['slime']['error'] = str(error)
        warn(f'slime not imported: {error}')

# ------------------------------------------------------------------------------------------- duck (gate 2 creatures)
# DINK_PHOTOREAL_ONLY=duck: Creatures/Duck -> /Game/Dink/Photoreal/Creatures/Duck. A first import: SK_Duck_PR brings its own
# 23-bone skeleton, SK_Duck_Headless_PR (the body that runs on after the first hit, dink.cpp duck_brain 12745-12775) is
# gated onto it, the nine clips are imported against it, SM_Duck_Head_PR is the severed head with its pool.
if 'duck' in ONLY:
    DK = PASS / 'Creatures/Duck'
    folder = BASE + '/Creatures/Duck'
    tex_folder = folder + '/Textures'
    report['duck'] = {}
    try:
        def dtex(stem, roles=('BC', 'N', 'ORM'), alpha=False):
            return {r: import_texture(DK / f'Textures/T_Duck_{stem}_{r}.png', tex_folder, 'BCA' if (alpha and r == 'BC') else r) for r in roles}
        atlas = dtex('Atlas')
        atlas_bloody = dict(atlas, **dtex('Atlas_Bloody', ('BC', 'ORM')))
        cards = dtex('FeatherCards', alpha=True)
        cards_bloody = dtex('FeatherCards_Bloody', alpha=True)
        gore = dtex('Gore')
        body_parent = surface_material(folder, 'M_Duck_PR', atlas, skeletal=True)
        card_parent = surface_material(folder, 'M_Duck_FeatherCards_PR', cards, skeletal=True, masked=True, two_sided=True, vertex_tint=True)
        gore_parent = surface_material(folder, 'M_Duck_Gore_PR', gore, skeletal=True, two_sided=True)
        materials = {n: instance(folder, n + '_PR', body_parent, atlas) for n in ('MI_Duck_Feather', 'MI_Duck_Bill', 'MI_Duck_Feet', 'MI_Duck_Eye')}
        materials['MI_Duck_Feather_Bloody'] = instance(folder, 'MI_Duck_Feather_Bloody_PR', body_parent, atlas_bloody)
        materials['MI_Duck_FeatherCards'] = instance(folder, 'MI_Duck_FeatherCards_PR', card_parent, cards)
        materials['MI_Duck_FeatherCards_Bloody'] = instance(folder, 'MI_Duck_FeatherCards_Bloody_PR', card_parent, cards_bloody)
        materials['MI_Duck_Gore'] = instance(folder, 'MI_Duck_Gore_PR', gore_parent, gore)

        duck, rig, slots = creature_mesh(DK, 'SK_Duck', folder, 'SK_Duck_PR', None, materials)
        skeleton = duck.get_editor_property('skeleton')
        bones = [b['name'] for b in rig['bones']]
        expected = ['root', 'pelvis', 'spine_01', 'spine_02', 'neck_01', 'neck_02', 'neck_03', 'head', 'jaw', 'wing_l', 'wingtip_l', 'wing_r', 'wingtip_r',
                    'tail_01', 'tail_02', 'thigh_l', 'calf_l', 'foot_l', 'toes_l', 'thigh_r', 'calf_r', 'foot_r', 'toes_r']
        if sorted(bones) != sorted(expected):
            raise RuntimeError('duck bones differ from the source rig: ' + json.dumps(sorted(set(bones) ^ set(expected))))
        size = rig.get('bounds_size_cm') or [0, 0, 0]
        save(skeleton); save(duck)
        report['duck'].update({'mesh': folder + '/SK_Duck_PR', 'skeleton': skeleton.get_path_name(), 'bones': len(bones), 'bounds_size_cm': size,
                               'lods': unreal.SkeletalMeshEditorSubsystem.get_lod_count(duck), 'slots': slots})
        headless, hrig, hslots = creature_mesh(DK, 'SK_Duck_Headless', folder, 'SK_Duck_Headless_PR', skeleton, materials)
        if headless.get_editor_property('skeleton') != skeleton:
            if not unreal.DinkCharacterArtLibrary.assign_matching_skeleton(headless, duck):
                raise RuntimeError('headless duck bind pose does not match the duck skeleton (native gate refused it)')
        save(headless)
        report['duck']['headless'] = {'mesh': folder + '/SK_Duck_Headless_PR', 'skeleton': headless.get_editor_property('skeleton').get_path_name(),
                                      'lods': unreal.SkeletalMeshEditorSubsystem.get_lod_count(headless), 'slots': hslots}
        clips = creature_clips(DK, 'A_Duck', folder, 'AN_Duck', skeleton, (('Idle', True), ('Walk', True), ('Run', True), ('Peck', False), ('Quack', False), ('Hit', False),
                               ('Death', False), ('HeadlessRun', True), ('HeadlessDeath', False), ('Scurry', True), ('HeadlessScurry', True)))
        report['duck']['clips'] = clips
        head, changed = import_static([DK / f'Export/SM_Duck_Head_LOD{i}.fbx' for i in range(3)], folder, 'SM_Duck_Head_PR', True)
        assign_slots(head, materials, 'SM_Duck_Head_PR')
        save(head)
        box = head.get_bounding_box()
        report['duck']['head'] = {'mesh': folder + '/SM_Duck_Head_PR', 'lods': MESHES.get_lod_count(head), 'reimported': changed,
                                  'size_cm': [round(box.max.x - box.min.x, 1), round(box.max.y - box.min.y, 1), round(box.max.z - box.min.z, 1)],
                                  'min_cm': [round(box.min.x, 1), round(box.min.y, 1), round(box.min.z, 1)]}
        # the head in flight: the same head without the pool it comes to lie in (sequences 121-129)
        flying, changed = import_static([DK / 'Export/SM_Duck_HeadFlying.fbx'], folder, 'SM_Duck_HeadFlying_PR', True)
        assign_slots(flying, materials, 'SM_Duck_HeadFlying_PR')
        save(flying)
        report['duck']['head_flying'] = {'mesh': folder + '/SM_Duck_HeadFlying_PR', 'reimported': changed}
        # shared gore: one drop of blood (instanced in flight) and two stains seen from above (deferred decals)
        GR = PASS / 'Creatures/Gore'
        gore_folder = BASE + '/Creatures/Gore'
        drop_mat = new_material(gore_folder, 'M_BloodDrop')
        drop_mat.set_editor_property('used_with_instanced_static_meshes', True)
        colour = expr(drop_mat, unreal.MaterialExpressionConstant3Vector, -400, 0, constant=unreal.LinearColor(0.11, 0.002, 0.002, 1.0))
        rough = expr(drop_mat, unreal.MaterialExpressionConstant, -400, 200, r=0.07)
        spec = expr(drop_mat, unreal.MaterialExpressionConstant, -400, 300, r=0.6)
        out(colour, '', MP.MP_BASE_COLOR); out(rough, '', MP.MP_ROUGHNESS); out(spec, '', MP.MP_SPECULAR)
        EDIT.recompile_material(drop_mat)
        save(drop_mat)
        drop, changed = import_static([GR / 'Export/SM_BloodDrop.fbx'], gore_folder, 'SM_BloodDrop', True)
        assign_slots(drop, {'MI_BloodDrop': drop_mat}, 'SM_BloodDrop')
        save(drop)
        # roughness 0.5: a glossier stain mirrors the sky on grass blades and reads grey instead of red
        decals = {n: decal_material(gore_folder, f'M_{n}_Decal', import_texture(GR / f'Textures/T_{n}_BC.png', gore_folder + '/Textures', 'BCA', wrap=False), roughness=0.5)
                  for n in ('BloodBurst', 'BloodPuddle')}
        report['duck']['gore'] = {'drop': gore_folder + '/SM_BloodDrop', 'decals': sorted(d.get_path_name() for d in decals.values())}
    except Exception as error:
        report['duck']['error'] = str(error)
        warn(f'duck not imported: {error}')

dest = ROOT / 'Saved/PhotorealPass/import_photoreal.json'
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(report, indent=2))
unreal.log(f"DINK PHOTOREAL IMPORT OK: {len(report['vegetation'])} vegetation meshes, {len(report['scatter'])} scatter meshes, {len(report['walls'])} wall modules, "
           f"hero {'yes' if report['hero'] else 'no'}, {len(report['warnings'])} warnings; report {dest}")
