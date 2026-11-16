"""Camera fade variants of the vegetation materials (15 Nov 2026).

Trees carry no collision, so the play camera can stand in a pine crown. UDinkInteriorCameraComponent fades a crown that
stands between the camera and Dink through a variant of its base material, listed in Content/Dink/Data/Art/
camera_materials.json under "foliage_variants". A variant is a duplicate of the base material with one change to its
opacity mask, the same recipe as the house variants of import_camera_materials.py:
- M_Veg_Foliage (masked, not dithered): the mask is cut at 0.5 first (exactly what the original's clip does), then
  multiplied by DinkCameraOpacity; the variant dithers that product, so at opacity 1 it draws exactly the original
  coverage and in between it thins out evenly. The shadow pass keeps the whole crown (ShadowPassSwitch).
- M_Veg_Bark (opaque): masked and dithered, mask = DinkCameraOpacity, shadow pass 1.
DINK_CAMERA_CHECK=1 only checks. Existing variants are validated, never overwritten (a new DINK_CAMERA_REVISION makes new ones).
"""
import json, os, re
from pathlib import Path
import unreal

assert '-game' not in unreal.SystemLibrary.get_command_line().split(), 'Material authoring needs an editor commandlet'
ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
LIB = unreal.EditorAssetLibrary
EDIT = unreal.MaterialEditingLibrary
CHECK = os.environ.get('DINK_CAMERA_CHECK') == '1'
REVISION = os.environ.get('DINK_CAMERA_REVISION', 'v1')
assert re.fullmatch(r'[A-Za-z0-9_]+', REVISION), 'Invalid revision'
REPORT = ROOT / 'Saved/Art/camera_foliage_materials_report.json'
CONFIG = ROOT / 'Content/Dink/Data/Art/camera_materials.json'
FOLDER = '/Game/Dink/Camera/Vegetation'
SOURCES = {
    'Foliage': '/Game/Dink/Photoreal/Vegetation/M_Veg_Foliage',
    'Bark': '/Game/Dink/Photoreal/Vegetation/M_Veg_Bark',
}
report = {'passed': False, 'check_only': CHECK, 'revision': REVISION, 'materials': []}


def require(c, msg):
    if not c:
        raise RuntimeError(msg)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    tmp.replace(path)


def custom(mat, x, y, code, inputs, description):
    node = EDIT.create_material_expression(mat, unreal.MaterialExpressionCustom, x, y)
    node.set_editor_property('code', code)
    node.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    node.set_editor_property('description', description)
    pins = []
    for n in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', n)
        pins.append(pin)
    node.set_editor_property('inputs', pins)
    return node


def opacity_param(mat, x, y):
    p = EDIT.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, x, y)
    p.set_editor_property('parameter_name', 'DinkCameraOpacity')
    p.set_editor_property('default_value', 1.0)
    return p


def check(mat, kind):
    require(mat.get_editor_property('blend_mode') == unreal.BlendMode.BLEND_MASKED, kind + ': variant must be masked')
    require(mat.get_editor_property('dither_opacity_mask'), kind + ': variant needs temporal opacity dithering')
    require(abs(mat.get_editor_property('opacity_mask_clip_value') - .5) < 1e-6, kind + ': clip must be 0.5')
    node = EDIT.get_material_property_input_node(mat, unreal.MaterialProperty.MP_OPACITY_MASK)
    require(isinstance(node, unreal.MaterialExpressionShadowReplace), kind + ': ShadowPassSwitch on the mask is required')
    names = [str(p.get_editor_property('parameter_name')) for p in EDIT.get_material_expressions(mat) if isinstance(p, unreal.MaterialExpressionScalarParameter)] \
        if hasattr(EDIT, 'get_material_expressions') else None
    if names is not None:
        require('DinkCameraOpacity' in names, kind + ': DinkCameraOpacity missing')


try:
    variants = {}
    for kind, source in SOURCES.items():
        name = source.rsplit('/', 1)[1]
        target = f'{FOLDER}/M_CameraFade_Veg{kind}_{REVISION}'
        existing = LIB.does_asset_exist(target)
        require(existing or not CHECK, 'Missing camera variant ' + target)
        if existing:
            mat = unreal.load_asset(target)
        else:
            original = unreal.load_asset(source)
            require(isinstance(original, unreal.Material), 'No source material ' + source)
            old_mask = EDIT.get_material_property_input_node(original, unreal.MaterialProperty.MP_OPACITY_MASK)
            if kind == 'Foliage':
                require(original.get_editor_property('blend_mode') == unreal.BlendMode.BLEND_MASKED, 'M_Veg_Foliage is expected masked')
                require(old_mask is not None, 'M_Veg_Foliage has no opacity mask')
            else:
                require(original.get_editor_property('blend_mode') == unreal.BlendMode.BLEND_OPAQUE, 'M_Veg_Bark is expected opaque')
            mat = LIB.duplicate_asset(source, target)
            require(isinstance(mat, unreal.Material), 'Could not duplicate ' + source)
            mask = EDIT.get_material_property_input_node(mat, unreal.MaterialProperty.MP_OPACITY_MASK)
            mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
            mat.set_editor_property('dither_opacity_mask', True)
            mat.set_editor_property('opacity_mask_clip_value', .5)
            alpha = opacity_param(mat, -150, -900)
            switch = EDIT.create_material_expression(mat, unreal.MaterialExpressionShadowReplace, 250, -700)
            if kind == 'Foliage':
                # coverage cut first (what the original's clip at 0.5 does), so dithering only ever thins whole texels
                faded = custom(mat, 50, -800, 'return step(0.5, M) * saturate(O);', ['M', 'O'], 'Camera fade of the cut coverage')
                whole = custom(mat, 50, -650, 'return step(0.5, M);', ['M'], 'Whole coverage in the shadow pass')
                require(EDIT.connect_material_expressions(mask, '', faded, 'M'), 'Cannot connect the coverage')
                require(EDIT.connect_material_expressions(alpha, '', faded, 'O'), 'Cannot connect the fade')
                require(EDIT.connect_material_expressions(mask, '', whole, 'M'), 'Cannot connect the shadow coverage')
                require(EDIT.connect_material_expressions(faded, '', switch, 'Default'), 'Cannot connect the faded mask')
                require(EDIT.connect_material_expressions(whole, '', switch, 'Shadow'), 'Cannot keep the shadow')
            else:
                opaque = EDIT.create_material_expression(mat, unreal.MaterialExpressionConstant, 50, -650)
                opaque.set_editor_property('r', 1.0)
                require(EDIT.connect_material_expressions(alpha, '', switch, 'Default'), 'Cannot connect the fade')
                require(EDIT.connect_material_expressions(opaque, '', switch, 'Shadow'), 'Cannot keep the shadow')
            require(EDIT.connect_material_property(switch, '', unreal.MaterialProperty.MP_OPACITY_MASK), 'Cannot connect the mask')
            EDIT.recompile_material(mat)
            require(LIB.save_loaded_asset(mat, only_if_is_dirty=False), 'Cannot save ' + target)
        check(mat, kind)
        variants[source + '.' + name] = mat.get_path_name()
        report['materials'].append({'original': source, 'variant': mat.get_path_name(), 'existing_kept': existing})
    config = json.loads(CONFIG.read_text())
    require(config.get('schema') == 'dink-camera/1', 'Unsupported camera schema')
    if CHECK:
        require(config.get('foliage_variants') == variants, 'foliage_variants differs from the variants')
    elif config.get('foliage_variants') != variants:
        config['foliage_variants'] = variants
        save_json(CONFIG, config)
    report['passed'] = True
    report['foliage_variants'] = variants
    save_json(REPORT, report)
    unreal.log('DINK CAMERA FOLIAGE MATERIALS ' + ('CHECK PASS' if CHECK else 'READY'))
except Exception as error:
    report['error'] = str(error)
    save_json(REPORT, report)
    raise
