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


def baked_master(defaults, name='M_Struct_Baked', emissive=False, kind='opaque'):
    """A unique bake (the contract's `baked` materials): BC / N / ORM on UV0, no vertex colour. Round 2 of the props:
    ORM.B is real metallic; `emissive` adds the E map x EmissiveNits x EmissiveScale; kind 'subsurface' (wax) and
    'translucent' (horn panes) change the shading only."""
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
    EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
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
    """One FBX with objects <name>_LOD0.._LOD2 and UCX hulls -> one static mesh with three LODs, no collision."""
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
    tex = {role: import_texture(REPO / rel, role) for role, rel in row['files'].items() if role in ('BC', 'N', 'ORM', 'H', 'Macro')}
    if row.get('baked'):
        kind = row.get('kind') or 'opaque'
        if 'E' in row['files']:
            tex['E'] = import_texture(REPO / row['files']['E'], 'BC')
        key = (kind, 'E' in tex)
        if key not in baked_parents:
            baked_parents[key] = baked_master(tex, 'M_Struct_Baked' + {'opaque': '', 'subsurface': '_Wax', 'translucent': '_Pane'}.get(kind, '') + ('_Glow' if 'E' in tex else ''), 'E' in tex, kind)
        materials[mat_name] = instance(mat_name, baked_parents[key], {k: tex[k] for k in ('BC', 'N', 'ORM', 'E') if k in tex},
                                       {'EmissiveNits': row.get('emissive_nits') or 0.0} if 'E' in tex else {}, {})
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
        if wanted not in materials:
            raise RuntimeError(f"{row['name']}: slot {index} ({slot_name}) has no contract material")
        slot.set_editor_property('material_interface', materials[wanted])
    mesh.set_editor_property('static_materials', slots)
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

dest = ROOT / ('Saved/PhotorealPass/import_' + os.environ.get('DINK_KIT_FOLDER', 'town').lower().replace('townexteriors', 'town') + '.json')
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(report, indent=2))
unreal.log(f"DINK TOWN IMPORT OK: {len(report['materials'])} materials, {len(report['modules'])} modules, {len(REMAPPED)} LOD sections remapped by slot name, {len(report['warnings'])} warnings; report {dest}")
