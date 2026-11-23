"""Run inside UnrealEditor's Python commandlet via import_town_exteriors.sh.

Imports the photoreal town-house kit (SourceAssets/Art/PhotorealPass/TownExteriors/manifest.json) into
/Game/Dink/Photoreal/TownExteriors: the MI_Town_* materials built from the manifest's `integration` contract
(one master material M_Town_Surface: macro variation, occlusion in the colour, dirt / bleaching / moss by the
'Grime' vertex colours, lead / iron / glass by vertex alpha, soot by vertex alpha) and one static mesh per module
with its three LODs. Collision hulls (UCX) are dropped: family art is visual only. Re-runnable; a module is
re-imported when its FBX changes. Refuses to run while the manifest has no `integration` block or an FBX is newer
than the manifest (an export in progress). Report: Saved/PhotorealPass/import_town.json.
"""
import json
import os
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
REPO = ROOT.parent
# DINK_KIT=Structures/Stonebrook DINK_KIT_FOLDER=Structures imports another kit that follows the same contract
# (the Stonebrook cottage, fence, gate, well and boulders) into /Game/Dink/Photoreal/<DINK_KIT_FOLDER>.
KIT = ROOT / 'SourceAssets/Art/PhotorealPass' / os.environ.get('DINK_KIT', 'TownExteriors')
FOLDER = '/Game/Dink/Photoreal/' + os.environ.get('DINK_KIT_FOLDER', 'TownExteriors')
TEX = FOLDER + '/Textures'
LIB = unreal.EditorAssetLibrary
EDIT = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
ST = unreal.MaterialSamplerType
F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('add_kit_lods', str(ROOT / 'Scripts/add_kit_lods.py'))
kit_lods = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(kit_lods)
MESHES = (unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem))
report = {'materials': [], 'modules': [], 'warnings': [], 'lod_sections_remapped': []}
REMAPPED = report['lod_sections_remapped']


def warn(text):
    report['warnings'].append(text)
    unreal.log_warning('DINK TOWN: ' + text)


def save(asset):
    if not LIB.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())


def stamp_of(path):
    path = Path(path)
    return f'{path.stat().st_size}:{int(path.stat().st_mtime)}'


def import_texture(path, kind):
    path = Path(path)
    target = TEX + '/' + path.stem
    existing = LIB.load_asset(target) if LIB.does_asset_exist(target) else None
    if existing is not None and LIB.get_metadata_tag(existing, 'DinkSource') == stamp_of(path):
        return existing
    task = unreal.AssetImportTask()
    task.filename = str(path.resolve())
    task.destination_path = TEX
    task.destination_name = path.stem
    task.automated = True
    task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])
    tex = LIB.load_asset(target)
    if tex is None:
        raise RuntimeError('Texture import failed: ' + str(path))
    tex.set_editor_property('srgb', kind == 'BC')
    if kind == 'N':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel', True)  # sources are OpenGL (green up)
    elif kind != 'BC':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
    if kind == 'H':
        tex.set_editor_property('max_texture_size', 1024)
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


def custom(mat, x, y, code, output_type, inputs, description):
    node = expr(mat, unreal.MaterialExpressionCustom, x, y, code=code, output_type=output_type, description=description)
    pins = []
    for n in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', n)
        pins.append(pin)
    node.set_editor_property('inputs', pins)
    return node


# The contract's weights, shared by the three custom nodes (colour, roughness, normal flattening).
WEIGHTS = '''
float fd = saturate(V.r * (1.15 - 0.5 * H));
float fb = saturate(V.b * saturate(0.9 * H + 0.35));
float fm = saturate(4.0 * ((V.g + 0.5 * Macro.b) - (0.55 * H + 0.62))) * (V.g > 0.02 ? 1.0 : 0.0);
float lead = (Switch > 0.5 && Lead > 0.5 && VA < 0.875) ? 1.0 : 0.0;
float iron = (Switch > 0.5 && VA < (Lead > 0.5 ? 0.625 : 0.75)) ? 1.0 : 0.0;
float glass = (Switch > 0.5 && VA < 0.25) ? 1.0 : 0.0;
float fs = Soot > 0.5 ? saturate((1.0 - VA) * (0.7 * Macro.g + 1.0)) : 0.0;
'''


def town_master(defaults):
    path = FOLDER + '/M_Town_Surface'
    mat = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if mat is None:
        mat = TOOLS.create_asset('M_Town_Surface', FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    for _ in range(64):
        if EDIT.get_num_material_expressions(mat) == 0:
            break
        EDIT.delete_all_material_expressions(mat)
    def tex(name, y, sampler):
        return expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -1100, y, parameter_name=name, texture=defaults[name], sampler_type=sampler)
    bc, nm, orm, h = tex('BC', -600, ST.SAMPLERTYPE_COLOR), tex('N', -350, ST.SAMPLERTYPE_NORMAL), tex('ORM', -100, ST.SAMPLERTYPE_MASKS), tex('H', 150, ST.SAMPLERTYPE_MASKS)
    macro = tex('Macro', 400, ST.SAMPLERTYPE_MASKS)
    uv = expr(mat, unreal.MaterialExpressionTextureCoordinate, -1500, 400, coordinate_index=0, u_tiling=1.0 / 7.0, v_tiling=1.0 / 7.0)  # Macro at UV0 / 7
    link(uv, '', macro, 'UVs')
    vc = expr(mat, unreal.MaterialExpressionVertexColor, -1100, 650)
    def vec(name, y, default):
        return expr(mat, unreal.MaterialExpressionVectorParameter, -1100, y, parameter_name=name, default_value=unreal.LinearColor(default[0], default[1], default[2], 1.0))
    def sca(name, y, default):
        return expr(mat, unreal.MaterialExpressionScalarParameter, -1100, y, parameter_name=name, default_value=default)
    tint, dirt, moss, pale, glass = vec('Tint', 900, (1, 1, 1)), vec('Dirt', 1100, (0.3, 0.25, 0.2)), vec('Moss', 1300, (0.045, 0.058, 0.02)), vec('Pale', 1500, (0.5, 0.47, 0.4)), vec('GlassTint', 1700, (0.035, 0.05, 0.065))
    scalars = {n: sca(n, 1900 + i * 80, d) for i, (n, d) in enumerate((('DirtAmount', 0.85), ('DirtMix', 0.0), ('MossRoughness', 0.95), ('PaleAmount', 0.55),
                                                                        ('MacroAmount', 0.22), ('AlphaSwitch', 0.0), ('AlphaSoot', 0.0), ('AlphaLead', 1.0)))}
    common = ['V', 'VA', 'H', 'Macro', 'Switch', 'Soot', 'Lead']
    def wire(node):
        link(vc, '', node, 'V'); link(vc, 'A', node, 'VA'); link(h, 'R', node, 'H'); link(macro, 'RGB', node, 'Macro')
        link(scalars['AlphaSwitch'], '', node, 'Switch'); link(scalars['AlphaSoot'], '', node, 'Soot'); link(scalars['AlphaLead'], '', node, 'Lead')
    colour = custom(mat, -400, -600, WEIGHTS + '''
float3 base = BC * Tint * (1.0 - MacroAmount + 2.0 * MacroAmount * Macro.r);
base = lerp(base, base * AO, 0.5);
float lb = dot(base, float3(0.2126, 0.7152, 0.0722));
float3 c = DirtMix > 0.5 ? lerp(base, Dirt * (3.0 * lb + 0.35), fd * DirtAmount) : lerp(base, base * Dirt, fd * DirtAmount);
c = lerp(c, Pale * (2.2 * dot(c, float3(0.2126, 0.7152, 0.0722)) + 0.55), fb * PaleAmount);
c = lerp(c, Moss * (0.9 * Macro.g + 0.55), fm);
c = lerp(c, float3(0.15, 0.16, 0.17) * (0.7 * Macro.g + 0.65), lead);
c = lerp(c, float3(0.016, 0.015, 0.014), iron);
c = lerp(c, GlassTint, glass);
return lerp(c, float3(0.012, 0.011, 0.010), fs);''', F3, common + ['BC', 'AO', 'Tint', 'Dirt', 'Moss', 'Pale', 'GlassTint', 'DirtAmount', 'DirtMix', 'PaleAmount', 'MacroAmount'], 'Town surface colour (integration contract)')
    wire(colour)
    link(bc, 'RGB', colour, 'BC'); link(orm, 'R', colour, 'AO'); link(tint, '', colour, 'Tint'); link(dirt, '', colour, 'Dirt'); link(moss, '', colour, 'Moss')
    link(pale, '', colour, 'Pale'); link(glass, '', colour, 'GlassTint')
    for n in ('DirtAmount', 'DirtMix', 'PaleAmount', 'MacroAmount'):
        link(scalars[n], '', colour, n)
    rough = custom(mat, -400, -100, WEIGHTS + '''
float r = lerp(R, MossRoughness, fm) - 0.10 * fd;
r = lerp(r, 0.42, lead);
r = lerp(r, 0.5 + 0.42 * V.r, iron);
r = lerp(r, 0.06, glass);
return saturate(lerp(r, 0.97, fs));''', F1, common + ['R', 'MossRoughness'], 'Town surface roughness')
    wire(rough)
    link(orm, 'G', rough, 'R'); link(scalars['MossRoughness'], '', rough, 'MossRoughness')
    normal = custom(mat, -400, -350, WEIGHTS + '''
float flat_n = max(lead * (1.0 - iron), glass);   // lead and glass are flat; iron and char keep the relief
// hand-blown quarries: each 7 cm diamond of a pane leans a degree or two its own way and bellies slightly
float2 q = (WP.xy + WP.yx * float2(0.37, -0.37) + WP.zz * float2(1.0, 0.61)) / 7.0;
float2 cell = floor(q); float2 in_cell = frac(q) - 0.5;
float2 tilt = (frac(sin(float2(dot(cell, float2(127.1, 311.7)), dot(cell, float2(269.5, 183.3)))) * 43758.5453) - 0.5) * 0.09 + in_cell * 0.05;
float3 pane = normalize(float3(tilt, 1.0));
return normalize(lerp(lerp(N, float3(0.0, 0.0, 1.0), flat_n), pane, glass));''', F3, common + ['N', 'WP'], 'Town surface normal')
    wire(normal)
    link(nm, 'RGB', normal, 'N')
    link(expr(mat, unreal.MaterialExpressionWorldPosition, -1100, 2700), '', normal, 'WP')
    spec = custom(mat, -400, 150, WEIGHTS + '''
return lerp(0.3, 1.0, glass);''', F1, common, 'Town surface specular (glass is a full dielectric; rough masonry, plaster and thatch show less sky sheen in shade)')
    wire(spec)
    EDIT.connect_material_property(spec, '', MP.MP_SPECULAR)
    for node, prop in ((colour, MP.MP_BASE_COLOR), (rough, MP.MP_ROUGHNESS), (normal, MP.MP_NORMAL)):
        if not EDIT.connect_material_property(node, '', prop):
            raise RuntimeError('cannot connect ' + str(prop))
    EDIT.connect_material_property(orm, 'R', MP.MP_AMBIENT_OCCLUSION)
    EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    EDIT.recompile_material(mat)
    save(mat)
    return mat


PIT_CODE = '''
float3 Vt = mul(Parameters.TangentToWorld, Parameters.CameraVector);
float2 dir = -Vt.xy / max(abs(Vt.z), 0.22);
float4 c0 = Texture2DSample(BCt, BCtSampler, UV);
float3 m0 = Texture2DSample(ORMt, ORMtSampler, UV).rgb;
float3 col = c0.rgb;
float spec = 0.12 * m0.r;
if (m0.b > 0.5)
{
    float t = 1.0;
    float found = 0.0;
    for (int i = 1; i <= 12; i++)
    {
        float s = i / 12.0;
        float h = Texture2DSampleLevel(ORMt, ORMtSampler, UV + dir * (WallUV * s), 0).b;
        if (found < 0.5 && h < 0.5) { t = s; found = 1.0; }
    }
    if (found > 0.5)
    {
        float3 face = lerp(float3(0.075, 0.066, 0.058), float3(0.030, 0.019, 0.012), smoothstep(0.0, 0.3, t));
        col = face * pow(1.0 - 0.9 * t, 1.6);
    }
    else
    {
        float2 qb = UV + dir * FloorUV;
        col = Texture2DSampleLevel(BCt, BCtSampler, qb, 0).rgb * Texture2DSampleLevel(ORMt, ORMtSampler, qb, 0).b;
    }
    spec = 0.0;
}
return float4(col, spec);'''
PIT_DITHER = '''
float n = frac(52.9829189 * frac(dot(Parameters.SvPosition.xy + 5.588238 * float(View.StateFrameIndexMod8), float2(0.06711056, 0.00583715))));
return A - n + 0.5;'''


def baked_master(defaults, name='M_Struct_Baked', emissive=False, kind='opaque'):
    """A unique bake (the contract's `baked` materials): BC / N / ORM on UV0, no vertex colour. Round 2 of the props:
    ORM.B is real metallic; `emissive` adds the E map x EmissiveNits x EmissiveScale; kind 'subsurface' (wax) and
    'translucent' (horn panes) change the shading only; 'masked' cuts the surface out by the alpha of BC; 'pit' is a
    burnt-through hole (see below)."""
    path = FOLDER + '/' + name
    mat = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if mat is None:
        mat = TOOLS.create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    for _ in range(64):
        if EDIT.get_num_material_expressions(mat) == 0:
            break
        EDIT.delete_all_material_expressions(mat)
    bc = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, -300, parameter_name='BC', texture=defaults['BC'], sampler_type=ST.SAMPLERTYPE_COLOR)
    nm = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, 0, parameter_name='N', texture=defaults['N'], sampler_type=ST.SAMPLERTYPE_NORMAL)
    orm = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, 300, parameter_name='ORM', texture=defaults['ORM'], sampler_type=ST.SAMPLERTYPE_MASKS)
    for node, pin, prop in ((bc, 'RGB', MP.MP_BASE_COLOR), (nm, 'RGB', MP.MP_NORMAL), (orm, 'R', MP.MP_AMBIENT_OCCLUSION), (orm, 'G', MP.MP_ROUGHNESS), (orm, 'B', MP.MP_METALLIC)):
        EDIT.connect_material_property(node, pin, prop)
    if emissive:
        # the contract gives nits; the project's light scale is far below physical (sun 10), so EmissiveScale brings them into it
        em = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, 600, parameter_name='E', texture=defaults['E'], sampler_type=ST.SAMPLERTYPE_COLOR)
        nits = expr(mat, unreal.MaterialExpressionScalarParameter, -600, 800, parameter_name='EmissiveNits', default_value=0.0)
        scale = expr(mat, unreal.MaterialExpressionScalarParameter, -600, 880, parameter_name='EmissiveScale', default_value=0.1)
        glow = custom(mat, -300, 600, 'return E * Nits * Scale;', F3, ['E', 'Nits', 'Scale'], 'Emissive')
        link(em, 'RGB', glow, 'E'); link(nits, '', glow, 'Nits'); link(scale, '', glow, 'Scale')
        EDIT.connect_material_property(glow, '', MP.MP_EMISSIVE_COLOR)
    if kind == 'subsurface':
        mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_SUBSURFACE)
        sss = custom(mat, -300, -500, 'return C * 0.9;', F3, ['C'], 'Subsurface colour')
        link(bc, 'RGB', sss, 'C')
        EDIT.connect_material_property(sss, '', MP.MP_SUBSURFACE_COLOR)
        EDIT.connect_material_property(expr(mat, unreal.MaterialExpressionScalarParameter, -300, -420, parameter_name='Scatter', default_value=0.6), '', MP.MP_OPACITY)
    elif kind == 'translucent':
        mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('two_sided', True)
        mat.set_editor_property('translucency_lighting_mode', unreal.TranslucencyLightingMode.TLM_SURFACE)
        EDIT.connect_material_property(expr(mat, unreal.MaterialExpressionScalarParameter, -300, -420, parameter_name='Opacity', default_value=0.75), '', MP.MP_OPACITY)
    elif kind == 'masked':
        # cut-out: the alpha of the BC map is the opacity mask (hair cards, the blood and scorch ground cards of the corpse kit)
        mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
        mat.set_editor_property('two_sided', True)
        mat.set_editor_property('opacity_mask_clip_value', 0.4)
        EDIT.connect_material_property(bc, 'A', MP.MP_OPACITY_MASK)
    elif kind == 'pit':
        # A hole burnt through planks or a wall (corpse kit, picture 158; Corpses/tools/gore_sheets.py pit_sheet). The sheet is flat;
        # ORM.b is not metallic here but the void mask. Inside the void the shader walks the view ray down through the thickness of
        # the planks (PitWallUV, in UV units): where it leaves the void it shows the charred cut face of the far side, else what
        # lies below (the BC of the void, read PitFloorUV deeper). The void has no specular at all: a lit black sheet is grey.
        # The cover (BC alpha) is dithered against a per-frame noise, so the scorch fades into the floor instead of ending in a cut.
        mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
        mat.set_editor_property('two_sided', True)
        mat.set_editor_property('opacity_mask_clip_value', 0.5)
        uv = expr(mat, unreal.MaterialExpressionTextureCoordinate, -1500, -900)
        bct = expr(mat, unreal.MaterialExpressionTextureObjectParameter, -1500, -800, parameter_name='PitBC', texture=defaults['BC'], sampler_type=ST.SAMPLERTYPE_COLOR)
        ormt = expr(mat, unreal.MaterialExpressionTextureObjectParameter, -1500, -700, parameter_name='PitORM', texture=defaults['ORM'], sampler_type=ST.SAMPLERTYPE_MASKS)
        wall = expr(mat, unreal.MaterialExpressionScalarParameter, -1500, -600, parameter_name='PitWallUV', default_value=0.03)
        floor_ = expr(mat, unreal.MaterialExpressionScalarParameter, -1500, -520, parameter_name='PitFloorUV', default_value=0.10)
        pit = custom(mat, -1100, -800, PIT_CODE, unreal.CustomMaterialOutputType.CMOT_FLOAT4, ['UV', 'BCt', 'ORMt', 'WallUV', 'FloorUV'], 'Burnt-through hole: far wall by parallax, void without specular')
        for node, pin in ((uv, 'UV'), (bct, 'BCt'), (ormt, 'ORMt'), (wall, 'WallUV'), (floor_, 'FloorUV')):
            link(node, '', pit, pin)
        rgb = expr(mat, unreal.MaterialExpressionComponentMask, -800, -850, r=True, g=True, b=True, a=False)
        spec = expr(mat, unreal.MaterialExpressionComponentMask, -800, -750, r=False, g=False, b=False, a=True)
        link(pit, '', rgb, ''); link(pit, '', spec, '')
        EDIT.connect_material_property(rgb, '', MP.MP_BASE_COLOR)
        EDIT.connect_material_property(spec, '', MP.MP_SPECULAR)
        EDIT.connect_material_property(expr(mat, unreal.MaterialExpressionConstant, -300, 420, r=0.0), '', MP.MP_METALLIC)
        dith = custom(mat, -300, -560, PIT_DITHER, F1, ['A'], 'Cover dithered per frame (the scorch fades out)')
        link(bc, 'A', dith, 'A')
        EDIT.connect_material_property(dith, '', MP.MP_OPACITY_MASK)
    EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    EDIT.recompile_material(mat)
    save(mat)
    return mat


STAIRWELL_CODE = (
    # UV: 0..1 over the opening, U along the flight (down towards U = 1). V: camera vector in tangent space (towards the
    # camera). Size = (length m, width m, rise m, going m). A stepped box under the quad is marched from the quad down.
    'float3 d = -normalize(V); d.z = min(d.z, -0.08); '
    'float3 p = float3(UV.x * Size.x, UV.y * Size.y, 0.0); float3 q = p; float3 prev = p; float hit = 0.0; '
    'for (int i = 0; i < 64; i++) { prev = q; q = p + d * (0.05 * (i + 1)); '
    'if (q.x < 0.0 || q.x > Size.x || q.y < 0.0 || q.y > Size.y) { hit = 2.0; break; } '
    'if (q.z < -(floor(q.x / Size.w) + 1.0) * Size.z) { hit = 1.0; break; } } '
    'float depth = max(-q.z, 0.0); float fade = exp(-depth * 1.15); float3 col = float3(0.0, 0.0, 0.0); '
    'if (hit > 0.5 && hit < 1.5) { '
    'bool riser = floor(prev.x / Size.w) != floor(q.x / Size.w) && prev.z >= -(floor(prev.x / Size.w) + 1.0) * Size.z; '
    'float nosing = 1.0 - smoothstep(0.0, 0.10, frac(q.x / Size.w)); '
    'float grain = 0.85 + 0.15 * sin(q.y * 37.0 + floor(q.x / Size.w) * 5.0); '
    'col = Wood * (riser ? 0.45 : 0.8 + 0.5 * nosing) * grain * fade; } '
    'else if (hit > 1.5) { col = Wood * 0.55 * (0.8 + 0.2 * step(0.5, frac(depth / 0.22))) * fade; } '
    'return col;')


def stairwell_material(name, row):
    """A stair opening in a floor that cannot be cut (materials row "procedural": "stairwell"; FableF/tools/build_stair_pit.py):
    the quad that closes the opening shows the flight going down under it: a stepped box marched along the view ray in
    tangent space, treads lighter at their nosing, risers and the well's walls darker, everything sinking into the dark."""
    path = FOLDER + '/' + name
    mat = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if mat is None:
        mat = TOOLS.create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    for _ in range(64):
        if EDIT.get_num_material_expressions(mat) == 0:
            break
        EDIT.delete_all_material_expressions(mat)
    cam = expr(mat, unreal.MaterialExpressionCameraVectorWS, -1100, 0)
    ts = expr(mat, unreal.MaterialExpressionTransform, -900, 0, transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
              transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    link(cam, '', ts, '')
    size = row.get('size_m', [2.9, 1.2])
    wood = row.get('wood', [0.165, 0.092, 0.04])
    pit = custom(mat, -500, 0, STAIRWELL_CODE, F3, ['UV', 'V', 'Size', 'Wood'], 'Stair flight under the floor')
    link(expr(mat, unreal.MaterialExpressionTextureCoordinate, -900, -200), '', pit, 'UV')
    link(ts, '', pit, 'V')
    link(expr(mat, unreal.MaterialExpressionVectorParameter, -900, 200, parameter_name='Size',
              default_value=unreal.LinearColor(float(size[0]), float(size[1]), float(row.get('rise_m', 0.1944)), float(row.get('going_m', 0.235)))), '', pit, 'Size')
    link(expr(mat, unreal.MaterialExpressionVectorParameter, -900, 400, parameter_name='Wood', default_value=unreal.LinearColor(float(wood[0]), float(wood[1]), float(wood[2]), 1.0)), '', pit, 'Wood')
    EDIT.connect_material_property(pit, '', MP.MP_BASE_COLOR)
    EDIT.connect_material_property(expr(mat, unreal.MaterialExpressionConstant, -300, 200, r=0.9), '', MP.MP_ROUGHNESS)
    EDIT.connect_material_property(expr(mat, unreal.MaterialExpressionConstant, -300, 280, r=0.1), '', MP.MP_SPECULAR)
    EDIT.recompile_material(mat)
    save(mat)
    return mat


def instance(name, parent, textures, scalars, vectors):
    path = FOLDER + '/' + name
    mi = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if mi is None:
        mi = TOOLS.create_asset(name, FOLDER, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    EDIT.clear_all_material_instance_parameters(mi)
    EDIT.set_material_instance_parent(mi, parent)
    for k, v in textures.items():
        EDIT.set_material_instance_texture_parameter_value(mi, k, v)
    for k, v in scalars.items():
        EDIT.set_material_instance_scalar_parameter_value(mi, k, float(v))
    for k, v in vectors.items():
        EDIT.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
    EDIT.update_material_instance(mi)
    save(mi)
    return mi


def import_module(fbx, name):
    """One FBX with objects <name>_LOD0.._LOD2 (or a single object <name>) and UCX hulls -> one static mesh
    with the LODs the file holds, no collision."""
    target = FOLDER + '/' + name
    key = stamp_of(fbx) + ':town2'
    existing = LIB.load_asset(target) if LIB.does_asset_exist(target) else None
    if existing is not None and LIB.get_metadata_tag(existing, 'DinkSource') == key:
        return existing, False
    temp = FOLDER + '/_Import'
    options = unreal.FbxImportUI()
    for k, v in {'automated_import_should_detect_type': False, 'mesh_type_to_import': unreal.FBXImportType.FBXIT_STATIC_MESH,
                 'import_mesh': True, 'import_materials': False, 'import_textures': False, 'import_animations': False}.items():
        options.set_editor_property(k, v)
    opts = options.static_mesh_import_data
    for k, v in {'combine_meshes': False, 'import_mesh_lods': False, 'remove_degenerates': True, 'auto_generate_collision': False,
                 'generate_lightmap_u_vs': False, 'convert_scene': True, 'convert_scene_unit': True, 'import_uniform_scale': 1.0,
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
        if asset is None or 'UCX' in asset.get_name():
            continue
        for lod in (0, 1, 2):
            if asset.get_name().endswith(f'LOD{lod}'):
                parts[lod] = asset
        # A kit whose FBX holds one object named after the asset, with no LOD suffix (Unclaimed): that object is LOD0.
        if asset.get_name() == name and 0 not in parts:
            parts[0] = asset
    if 0 not in parts:
        raise RuntimeError(f'{name}: no LOD0 object in {fbx}')
    if existing is not None:
        LIB.delete_asset(target)
    mesh = LIB.duplicate_loaded_asset(parts[0], target)
    if mesh is None:
        raise RuntimeError(f'{name}: cannot create {target}')
    def slot_names(m):
        return [str(s.get_editor_property('material_slot_name')).split('.')[0] for s in m.get_editor_property('static_materials')]
    main_names = slot_names(mesh)
    for lod in (1, 2):
        if lod in parts:
            MESHES.set_lod_from_static_mesh(mesh, lod, parts[lod], 0, True)
            # Each LOD object lists its materials in its own order (order of first use after decimation): a section
            # copied by slot index showed another material at a distance (plaster as oak, oak as rope). Map by name.
            part_names = slot_names(parts[lod])
            for section in range(parts[lod].get_num_sections(0)):
                source = MESHES.get_lod_material_slot(parts[lod], 0, section)
                wanted = part_names[source] if 0 <= source < len(part_names) else None
                if wanted not in main_names:
                    raise RuntimeError(f'{name}: LOD{lod} section {section} uses {wanted}, which LOD0 has no slot for')
                if main_names.index(wanted) != source:
                    REMAPPED.append(f'{name} LOD{lod} section {section}: {source} -> {main_names.index(wanted)} ({wanted})')
                MESHES.set_lod_material_slot(mesh, main_names.index(wanted), lod, section)
    MESHES.remove_collisions(mesh)
    LIB.set_metadata_tag(mesh, 'DinkSource', key)
    LIB.delete_directory(temp)
    return mesh, True


manifest = json.loads((KIT / 'manifest.json').read_text())
integration = manifest.get('integration')
if not integration:
    raise RuntimeError(f'{KIT.name}/manifest.json has no integration block: nothing imported')
manifest_time = (KIT / 'manifest.json').stat().st_mtime
newer = [p.name for p in KIT.glob('**/*.fbx') if '_build' not in p.parts and p.stat().st_mtime > manifest_time + 1.0]
if newer:
    raise RuntimeError(f'{len(newer)} FBX files are newer than the manifest ({newer[0]} ...): export in progress, nothing imported')

materials = {}
parent = None
baked_parents = {}
for mat_name, row in integration['materials'].items():
    if row.get('procedural') == 'stairwell':
        try:
            materials[mat_name] = stairwell_material(mat_name, row)
            report['materials'].append(mat_name)
        except Exception as error:      # never lose the whole kit to one drawn hole: the slot takes a baked material and the report says so
            warn(f'{mat_name}: stairwell material not built ({error})')
            if materials:
                materials[mat_name] = next(iter(materials.values()))
        continue
    # a file is a source path, or the /Game/ path of a map another kit has imported (states of a prop that keep its normal and ORM maps)
    tex = {role: (LIB.load_asset(rel) if str(rel).startswith('/Game/') else import_texture(REPO / rel, role)) for role, rel in row['files'].items() if role in ('BC', 'N', 'ORM', 'H', 'Macro')}
    if any(t is None for t in tex.values()):
        raise RuntimeError(f"{mat_name}: a /Game/ texture of its contract does not exist (import its kit first)")
    if row.get('baked'):
        kind = row.get('kind') or 'opaque'
        if 'E' in row['files']:
            tex['E'] = import_texture(REPO / row['files']['E'], 'BC')
        key = (kind, 'E' in tex)
        if key not in baked_parents:
            baked_parents[key] = baked_master(tex, 'M_Struct_Baked' + {'opaque': '', 'subsurface': '_Wax', 'translucent': '_Pane', 'masked': '_Cut', 'pit': '_Pit'}.get(kind, '') + ('_Glow' if 'E' in tex else ''), 'E' in tex, kind)
        textures = {k: tex[k] for k in ('BC', 'N', 'ORM', 'E') if k in tex}
        scalars = {'EmissiveNits': row.get('emissive_nits') or 0.0} if 'E' in tex else {}
        if kind == 'pit':                             # the pit shader reads the same two maps as texture objects, and the depths of this hole
            textures.update({'PitBC': tex['BC'], 'PitORM': tex['ORM']})
            scalars.update({'PitWallUV': (row.get('pit') or {}).get('wall_uv', 0.03), 'PitFloorUV': (row.get('pit') or {}).get('floor_uv', 0.10)})
        materials[mat_name] = instance(mat_name, baked_parents[key], textures, scalars, {})
        report['materials'].append(mat_name)
        continue
    missing = {'BC', 'N', 'ORM', 'H', 'Macro'} - set(tex)
    if missing:
        raise RuntimeError(f'{mat_name}: texture roles missing in the contract: {sorted(missing)}')
    if parent is None:
        parent = town_master(tex)
    scalars = {'DirtAmount': row.get('dirt_amount', 0.0), 'DirtMix': 1.0 if row.get('dirt_mode') == 'mix' else 0.0, 'MossRoughness': row.get('moss_roughness', 0.95),
               'PaleAmount': row.get('pale_amount', 0.0), 'MacroAmount': row.get('macro', 0.0), 'AlphaSwitch': 1.0 if row.get('alpha_switch') else 0.0,
               'AlphaSoot': 1.0 if row.get('alpha_soot') else 0.0, 'AlphaLead': 1.0 if row.get('alpha_lead', True) else 0.0}
    vectors = {'Tint': row.get('tint', [1, 1, 1]), 'Dirt': row.get('dirt', [1, 1, 1]), 'Moss': row.get('moss', [0.045, 0.058, 0.02]), 'Pale': row.get('pale', [1, 1, 1])}
    if row.get('glass_tint'):
        vectors['GlassTint'] = row['glass_tint']
    materials[mat_name] = instance(mat_name, parent, tex, scalars, vectors)
    report['materials'].append(mat_name)

# a kit lists its meshes as `modules` (fbx beside the manifest) or as `assets` (fbx path from the repository root: Props)
for row in (manifest.get('modules') or manifest['assets']):
    fbx_path = REPO / row['fbx'] if str(row['fbx']).startswith('DinkRemasterUE/') else KIT / row['fbx']
    mesh, changed = import_module(fbx_path, row['name'])
    slots = list(mesh.get_editor_property('static_materials'))
    # the contract: material slots in the order of the module's "materials" list; a slot named after a contract material wins
    for index, slot in enumerate(slots):
        slot_name = str(slot.get_editor_property('material_slot_name')).split('.')[0]
        listed = row.get('materials') or (integration.get('assets', {}).get(row['name'], {}).get('material_slots') or [])
        wanted = slot_name if slot_name in materials else (listed[index] if index < len(listed) else None)
        # a colour variant: the same FBX under another asset name, with some slot materials exchanged (the potion flask's three glass tints)
        wanted = (row.get('slot_override') or {}).get(wanted, wanted)
        if wanted not in materials:
            raise RuntimeError(f"{row['name']}: slot {index} ({slot_name}) has no contract material")
        slot.set_editor_property('material_interface', materials[wanted])
    mesh.set_editor_property('static_materials', slots)
    # A200: a re-imported single-LOD, non-Nanite mesh of more than 5,000 triangles gets engine-reduced LODs
    # (Scripts/add_kit_lods.py: LOD0 untouched, LOD1/LOD2 from 10/20 m, every section kept)
    if changed and MESHES.get_lod_count(mesh) == 1 and mesh.get_num_triangles(0) > kit_lods.MIN_TRIANGLES \
            and not mesh.get_editor_property('nanite_settings').get_editor_property('enabled'):
        kit_lods.ensure_lods(mesh)
    size = mesh.get_bounding_box().max - mesh.get_bounding_box().min
    got = [round(size.x / 100.0, 3), round(size.y / 100.0, 3), round(size.z / 100.0, 3)]
    want = row.get('dimensions_m') or got
    if max(abs(a - b) for a, b in zip(got, want)) > max(0.03, 0.03 * max(want)):
        warn(f"{row['name']}: imported size {got} m differs from the manifest {want}")
    save(mesh)
    report['modules'].append({'mesh': FOLDER + '/' + row['name'], 'lods': MESHES.get_lod_count(mesh), 'size_m': got,
                              'slots': [str(s.get_editor_property('material_slot_name')) for s in slots], 'reimported': changed})

# Decal sheets of a kit (Props/Decals, manifest `decals`): 2 x 2 atlases as deferred decals, one instance per cell
# (MI_Decal_<Set>_0..3). UDinkEnvironmentSubsystem binds them to sprite classes through environment.json `decals`.
if isinstance(manifest.get('decals'), dict) and manifest['decals'].get('sets'):
    decal_dir = REPO / manifest['decals']['folder']
    decal_parent = None
    report['decals'] = []
    for row in manifest['decals']['sets']:
        tex = {role: import_texture(decal_dir / rel, role) for role, rel in row['files'].items() if role in ('BC', 'N', 'ORM')}
        if decal_parent is None:
            path = FOLDER + '/M_Decal_Sheet'
            mat = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
            if mat is None:
                mat = TOOLS.create_asset('M_Decal_Sheet', FOLDER, unreal.Material, unreal.MaterialFactoryNew())
            for _ in range(64):
                if EDIT.get_num_material_expressions(mat) == 0:
                    break
                EDIT.delete_all_material_expressions(mat)
            mat.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
            mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
            uv = custom(mat, -900, 0, 'return UV * 0.5 + Cell.xy;', unreal.CustomMaterialOutputType.CMOT_FLOAT2, ['UV', 'Cell'], 'Atlas cell')
            link(expr(mat, unreal.MaterialExpressionTextureCoordinate, -1100, 0), '', uv, 'UV')
            link(expr(mat, unreal.MaterialExpressionVectorParameter, -1100, 100, parameter_name='Cell', default_value=unreal.LinearColor(0, 0, 0, 0)), '', uv, 'Cell')
            bc = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, -300, parameter_name='BC', texture=tex['BC'], sampler_type=ST.SAMPLERTYPE_COLOR)
            nm = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, 0, parameter_name='N', texture=tex['N'], sampler_type=ST.SAMPLERTYPE_NORMAL)
            orm = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, 300, parameter_name='ORM', texture=tex['ORM'], sampler_type=ST.SAMPLERTYPE_MASKS)
            for node in (bc, nm, orm):
                link(uv, '', node, 'UVs')
            for node, pin, prop in ((bc, 'RGB', MP.MP_BASE_COLOR), (bc, 'A', MP.MP_OPACITY), (nm, 'RGB', MP.MP_NORMAL), (orm, 'G', MP.MP_ROUGHNESS)):
                EDIT.connect_material_property(node, pin, prop)
            EDIT.recompile_material(mat)
            save(mat)
            decal_parent = mat
        for cell in range(4):
            mi = instance(f"MI_Decal_{row['name']}_{cell}", decal_parent, tex, {}, {})
            EDIT.set_material_instance_vector_parameter_value(mi, 'Cell', unreal.LinearColor(0.5 * (cell % 2), 0.5 * (cell // 2), 0.0, 0.0))
            EDIT.update_material_instance(mi)
            save(mi)
        report['decals'].append(row['name'])

# Effect flipbooks of a kit (manifest `flipbooks`): an atlas of frames played by the material itself, unlit; additive for
# pictures that are light rather than things (the twinkle on gold), translucent (row "blend": "translucent") for the ones
# with dark parts (fire with smoke, embers on charred wood, blood), lit translucent (row "blend": "lit") for water, which
# has no light of its own. Masters M_FX_Flipbook, M_FX_Flipbook_Blend and M_FX_Flipbook_Lit, one
# MI_FX_<name> per row; a row's "hot": [lo, hi, base] sets where the glow of a translucent flipbook starts.
# UDinkArtFamilySubsystem draws it on a camera-facing card for families.json rows with `effect`.
if isinstance(manifest.get('flipbooks'), list) and manifest['flipbooks']:
    report['flipbooks'] = []
    fx_parents = {}

    def flipbook_master(blend, tex):
        """M_FX_Flipbook (additive: light only, the twinkle) or M_FX_Flipbook_Blend (translucent: a flipbook with dark
        parts: fire with smoke, charred wood under its embers, blood, water; the frame's alpha is the opacity, pixels
        brighter than Hot.x glow by the Grid glow factor, the rest keep their colour times Hot.z).
        Scalars: StartTime (world seconds, set per card by UDinkArtFamilySubsystem), OneShot (1 = play once and hold the
        last frame, 0 = loop), CameraOffset (cm the card is drawn towards the camera, so the ground does not cut it),
        Roll (turns the picture inside its square card, in whole turns: 0.25 puts the picture's bottom on the right,
        0.5 on top, 0.75 on the left; a kit row's "roll": the fireball's four directions share one texture)."""
        name = {'translucent': 'M_FX_Flipbook_Blend', 'lit': 'M_FX_Flipbook_Lit', 'decal': 'M_FX_Flipbook_Decal'}.get(blend, 'M_FX_Flipbook')
        path = FOLDER + '/' + name
        mat = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
        if mat is None:
            mat = TOOLS.create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
        for _ in range(64):
            if EDIT.get_num_material_expressions(mat) == 0:
                break
            EDIT.delete_all_material_expressions(mat)
        mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT if blend == 'lit' else unreal.MaterialShadingModel.MSM_UNLIT)
        mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE if blend == 'additive' else unreal.BlendMode.BLEND_TRANSLUCENT)
        if blend == 'lit':
            # water spray: lit by the scene from every side (the translucency lighting volume: sun, sky and lamps), so it
            # is bright in daylight and dim in a dungeon; no normal, no highlight of its own
            mat.set_editor_property('translucency_lighting_mode', unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
        mat.set_editor_property('two_sided', True)
        if blend == 'decal':
            # a burn on a wall or a roof (UDinkArtFamilySubsystem "effect_decal"): the frames are projected onto the surface
            mat.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
            mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
            mat.set_editor_property('two_sided', False)
        # Grid = (columns, rows, frames per second, glow); frames run row by row from the top left
        uv = custom(mat, -900, 0, 'float n = Grid.x * Grid.y; float t = max(T - Start, 0.0) * Grid.z; '
                    'float f = Once > 0.5 ? min(floor(t), n - 1.0) : floor(frac(t / n) * n); '
                    'float2 p = UV - 0.5; float sn, cs; sincos(Roll * 6.2831853, sn, cs); '
                    'float2 q = saturate(float2(cs * p.x - sn * p.y, sn * p.x + cs * p.y) + 0.5); '
                    'return (q + float2(fmod(f, Grid.x), floor(f / Grid.x))) / Grid.xy;',
                    unreal.CustomMaterialOutputType.CMOT_FLOAT2, ['UV', 'T', 'Grid', 'Start', 'Once', 'Roll'], 'Flipbook frame')
        link(expr(mat, unreal.MaterialExpressionTextureCoordinate, -1100, -100), '', uv, 'UV')
        link(expr(mat, unreal.MaterialExpressionTime, -1100, 0), '', uv, 'T')
        grid = expr(mat, unreal.MaterialExpressionVectorParameter, -1100, 100, parameter_name='Grid', default_value=unreal.LinearColor(8, 8, 24, 3))
        link(grid, '', uv, 'Grid')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -1100, 500, parameter_name='StartTime', default_value=0.0), '', uv, 'Start')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -1100, 600, parameter_name='OneShot', default_value=0.0), '', uv, 'Once')
        link(expr(mat, unreal.MaterialExpressionScalarParameter, -1100, 700, parameter_name='Roll', default_value=0.0), '', uv, 'Roll')
        frames = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, 0, parameter_name='Flipbook', texture=tex, sampler_type=ST.SAMPLERTYPE_COLOR)
        link(uv, '', frames, 'UVs')
        if blend == 'lit':
            # Grid.w ("glow") scales the water's own colour (1 = as painted); roughness 1, no specular: a card has no shape to shine on
            tint = expr(mat, unreal.MaterialExpressionMultiply, -300, 0)
            link(frames, 'RGB', tint, 'A')
            link(grid, 'A', tint, 'B')
            EDIT.connect_material_property(tint, '', MP.MP_BASE_COLOR)
            EDIT.connect_material_property(frames, 'A', MP.MP_OPACITY)
            EDIT.connect_material_property(expr(mat, unreal.MaterialExpressionConstant, -300, 150, r=1.0), '', MP.MP_ROUGHNESS)
            EDIT.connect_material_property(expr(mat, unreal.MaterialExpressionConstant, -300, 220, r=0.0), '', MP.MP_SPECULAR)
        elif blend == 'decal':
            # char keeps its own colour and takes the scene's light; what is brighter than Hot.x is fire and glows
            hot = expr(mat, unreal.MaterialExpressionVectorParameter, -1100, 300, parameter_name='Hot', default_value=unreal.LinearColor(0.16, 0.5, 1.0, 0.0))
            glow = custom(mat, -300, 0, 'float m = max(C.r, max(C.g, C.b)); float h = smoothstep(Hot.x, Hot.y, m); return C * Glow * Scale * h;',
                          unreal.CustomMaterialOutputType.CMOT_FLOAT3, ['C', 'Hot', 'Glow', 'Scale'], 'Fire glow')
            link(frames, 'RGB', glow, 'C')
            link(hot, '', glow, 'Hot')
            link(grid, 'A', glow, 'Glow')
            link(expr(mat, unreal.MaterialExpressionScalarParameter, -600, 250, parameter_name='GlowScale', default_value=1.0), '', glow, 'Scale')
            EDIT.connect_material_property(frames, 'RGB', MP.MP_BASE_COLOR)
            EDIT.connect_material_property(glow, '', MP.MP_EMISSIVE_COLOR)
            EDIT.connect_material_property(frames, 'A', MP.MP_OPACITY)
            EDIT.connect_material_property(expr(mat, unreal.MaterialExpressionConstant, -300, 150, r=0.92), '', MP.MP_ROUGHNESS)
        elif blend == 'translucent':
            hot = expr(mat, unreal.MaterialExpressionVectorParameter, -1100, 300, parameter_name='Hot', default_value=unreal.LinearColor(0.25, 0.6, 1.0, 0.0))
            # GlowScale (review: `dink.MatParam MI_FX_<name> GlowScale 2`) multiplies the row's glow at run time
            glow = custom(mat, -300, 0, 'float m = max(C.r, max(C.g, C.b)); float h = smoothstep(Hot.x, Hot.y, m); return C * lerp(Hot.z, Glow * Scale, h);',
                          unreal.CustomMaterialOutputType.CMOT_FLOAT3, ['C', 'Hot', 'Glow', 'Scale'], 'Ember glow')
            link(frames, 'RGB', glow, 'C')
            link(hot, '', glow, 'Hot')
            link(grid, 'A', glow, 'Glow')
            link(expr(mat, unreal.MaterialExpressionScalarParameter, -600, 250, parameter_name='GlowScale', default_value=1.0), '', glow, 'Scale')
            EDIT.connect_material_property(glow, '', MP.MP_EMISSIVE_COLOR)
            EDIT.connect_material_property(frames, 'A', MP.MP_OPACITY)
        else:
            lit = expr(mat, unreal.MaterialExpressionMultiply, -300, 0)
            link(frames, 'RGB', lit, 'A')
            link(frames, 'A', lit, 'B')
            glow = expr(mat, unreal.MaterialExpressionMultiply, -100, 0)
            link(lit, '', glow, 'A')
            link(grid, 'A', glow, 'B')
            EDIT.connect_material_property(glow, '', MP.MP_EMISSIVE_COLOR)
        if blend != 'decal':
            # towards the camera, worked out per vertex (the camera vector node exists only in the pixel shader)
            pull = custom(mat, -300, 500, 'return normalize(Cam - Pos) * Off;', unreal.CustomMaterialOutputType.CMOT_FLOAT3, ['Cam', 'Pos', 'Off'], 'Towards the camera')
            link(expr(mat, unreal.MaterialExpressionCameraPositionWS, -600, 420), '', pull, 'Cam')
            link(expr(mat, unreal.MaterialExpressionWorldPosition, -600, 520), '', pull, 'Pos')
            link(expr(mat, unreal.MaterialExpressionScalarParameter, -600, 620, parameter_name='CameraOffset', default_value=0.0), '', pull, 'Off')
            EDIT.connect_material_property(pull, '', MP.MP_WORLD_POSITION_OFFSET)
        EDIT.recompile_material(mat)
        save(mat)
        return mat

    for row in manifest['flipbooks']:
        tex = import_texture(REPO / row['file'], 'BC')
        blend = 'translucent' if row.get('blend') in ('translucent', 'alpha') else row['blend'] if row.get('blend') in ('lit', 'decal') else 'additive'
        if blend == 'decal' and not tex.get_editor_property('never_stream'):
            # texture streaming does not see a decal's size on screen: the sheet stayed at a coarse mip (blocks) on a far roof
            tex.set_editor_property('never_stream', True)
            save(tex)
        if blend not in fx_parents:
            fx_parents[blend] = flipbook_master(blend, tex)
        mi = instance('MI_FX_' + row['name'], fx_parents[blend], {'Flipbook': tex},
                      {'OneShot': 0.0 if row.get('loop', True) else 1.0, 'CameraOffset': float(row.get('camera_offset_cm', 0.0)),
                       'Roll': float(row.get('roll', 0.0))}, {})
        if blend in ('translucent', 'decal') and isinstance(row.get('hot'), list) and len(row['hot']) == 3:
            EDIT.set_material_instance_vector_parameter_value(mi, 'Hot', unreal.LinearColor(float(row['hot'][0]), float(row['hot'][1]), float(row['hot'][2]), 0.0))
        g = row.get('grid', [8, 8])
        EDIT.set_material_instance_vector_parameter_value(mi, 'Grid', unreal.LinearColor(float(g[0]), float(g[1]), float(row.get('fps', 24)), float(row.get('glow', 3))))
        EDIT.update_material_instance(mi)
        save(mi)
        report['flipbooks'].append(row['name'])

dest = ROOT / ('Saved/PhotorealPass/import_' + os.environ.get('DINK_KIT_FOLDER', 'town').lower().replace('townexteriors', 'town') + '.json')
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(report, indent=2))
unreal.log(f"DINK TOWN IMPORT OK: {len(report['materials'])} materials, {len(report['modules'])} modules, {len(REMAPPED)} LOD sections remapped by slot name, {len(report['warnings'])} warnings; report {dest}")
