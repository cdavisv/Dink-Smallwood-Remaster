"""Exact32-image house source-encoding policy; no Unreal imports or launch on load."""
from pathlib import Path
import base64,hashlib,json,math,struct
PROFILE='house439_exact_eight_srgb16_encoding_v1'
NAMESPACE='/Game/Dink/Refinements/House439ClosedEavesV1'
DATA=Path(__file__).with_name('House439SourceEncodingV1')
CLASSES_SHA='fca07cf3605fc72da9bb0683421cf9d7b96f1fa8a3ef871e2a398991f1b03697'
PINS_SHA='fc54b6345dc3c7a092b80c7ecf8eafa351da6a4c6b5dfa7df58d7855a0dd623e'

def policy():
    classes_file=DATA/'CLASSES.json';pins_file=DATA/'RAW_STORAGE_PINS.json'
    if hashlib.sha256(classes_file.read_bytes()).hexdigest()!=CLASSES_SHA or hashlib.sha256(pins_file.read_bytes()).hexdigest()!=PINS_SHA:
        raise ValueError('Exact house32 texture policy payloads required')
    classes=json.loads(classes_file.read_text());pins=json.loads(pins_file.read_text())
    if len(classes)!=32 or set(classes)!=set(pins):raise ValueError('Complete house32 inventory required')
    values={sha:2 if row==dict(png_bit_depth=16,colorspace='sRGB',image_is_float=True,reference_encoding='Linear')else 0 for sha,row in classes.items()}
    if sum(v==2 for v in values.values())!=8:raise ValueError('Exact eight-image encoding scope required')
    return classes,pins,values

def expected_override(sha,image):
    classes,pins,values=policy()
    if sha not in classes or image!={'sha256':sha,'colorspace':classes[sha]['colorspace'],'size':[pins[sha]['width'],pins[sha]['height']]}:
        raise ValueError('Exact source image identity/class/size required')
    return values[sha]

def target_for(sha):return NAMESPACE+'/Textures/T_Source_'+sha

def validate_plan(plan):
    classes,pins,values=policy()
    if plan.get('source_encoding_profile')!=PROFILE or set(plan.get('textures',{}))!=set(classes) or plan.get('mesh_target')!=NAMESPACE+'/Meshes/SM_Cottage_Stonebrook_01':
        raise ValueError('Explicit exact house profile, inventory and namespace required')
    source_root=(Path(plan['project'])/'SourceAssets/Art').resolve()
    for sha,row in plan['textures'].items():
        if row['target']!=target_for(sha):raise ValueError('Exact house texture package required')
        expected_override(sha,row['image']);path=Path(row['file'])
        if path.is_symlink()or not path.resolve().is_relative_to(source_root):raise ValueError('Owned immutable source-art path required')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sha or raw[:8]!=b'\x89PNG\r\n\x1a\n' or raw[12:16]!=b'IHDR':raise ValueError('Original PNG differs')
        width,height=struct.unpack('>II',raw[16:24]);pin=pins[sha]
        if [width,height,raw[24],raw[25]]!=[pin['width'],pin['height'],pin['png_bit_depth'],pin['png_color_type']]:raise ValueError('Pinned PNG header differs')
    return values

def snapshot(value,U):
    if value is None or type(value)in(bool,int,str):return value
    if type(value)is float:
        if not math.isfinite(value):raise ValueError('Nonfinite native source color setting')
        return value
    if isinstance(value,U.EnumBase):
        if type(value.value)is not int or type(value.name)is not str:raise ValueError('Invalid reflected enum value')
        return dict(enum=type(value).__name__,name=value.name,value=value.value)
    if isinstance(value,dict):return {k:snapshot(v,U)for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [snapshot(v,U)for v in value]
    if callable(getattr(value,'to_dict',None)):return snapshot(value.to_dict(),U)
    raise ValueError('Unsupported native setting snapshot type')

def verify_storage(actual,sha,image,target,override):
    _,pins,_=policy();pin=pins[sha];expected=expected_override(sha,image)
    if override not in(0,expected)or target!=target_for(sha):raise ValueError('Wrong house encoding/storage request')
    if(actual.get('schema')!='dink-texture-source-pixels/1'or actual.get('valid')is not True or actual.get('texture','').split('.')[0]!=target
       or actual.get('format')!=pin['native_expected_format']or[actual.get('width'),actual.get('height')]!=[pin['width'],pin['height']]
       or actual.get('source_encoding_override_none')is not(override==0)or actual.get('source_color_space_none')is not True
       or actual.get('texture_srgb')is not(image['colorspace']=='sRGB')or actual.get('gpu_pixels_read')is not False
       or actual.get('row_origin')!='top_left'or actual.get('byte_order')!='little'or actual.get('source_gamma')not in('Linear','sRGB','Pow22')):
        raise ValueError('Native original-source storage provenance differs')
    raw=base64.b64decode(actual['base64'],validate=True)
    if len(raw)!=pin['expected_native_storage_bytes']or actual['byte_count']!=len(raw)or hashlib.sha256(raw).hexdigest()!=pin['expected_native_storage_sha256']:
        raise ValueError('Native source code-value bytes differ from original PNG')
    return dict(source_storage_exact=True,source_storage_sha256=pin['expected_native_storage_sha256'],source_byte_count=len(raw),native_source_format=actual['format'],native_source_gamma=actual['source_gamma'],encoding_override_expected=override,scope='Raw original code-value storage only; no transfer applied or GPU equivalence claim')

def read_encoding(U,texture,sha,image,guard):
    guard();settings=texture.get_editor_property('source_color_settings')
    override=settings.get_editor_property('encoding_override');space=settings.get_editor_property('color_space');expected=expected_override(sha,image)
    if not isinstance(override,U.TextureSourceEncoding)or override.value!=expected or not isinstance(space,U.TextureColorSpace)or space.value!=0:raise ValueError('Actual reflected source encoding/color space differs')
    return dict(override_value=override.value,override_name=override.name,color_space_value=space.value,profile=PROFILE)

def configure_texture(U,texture,sha,row,guard):
    target=row['target'];image=row['image'];expected=expected_override(sha,image)
    if target!=target_for(sha)or not callable(guard):raise ValueError('Exact house target and guard required')
    guard()
    if texture.get_path_name().split('.')[0]!=target:raise ValueError('Actual house texture identity differs')
    guard();before=json.loads(U.DinkMaterialArtLibrary.inspect_texture_source_pixels(texture));prior=verify_storage(before,sha,image,target,0)
    guard();settings=texture.get_editor_property('source_color_settings');initial=snapshot(settings,U)
    old=settings.get_editor_property('encoding_override');space=settings.get_editor_property('color_space')
    if not isinstance(old,U.TextureSourceEncoding)or old.value!=0 or not isinstance(space,U.TextureColorSpace)or space.value!=0:raise ValueError('Untouched source color defaults required')
    if expected==2:
        guard();copy=settings.copy();copy.set_editor_property('encoding_override',U.TextureSourceEncoding.cast(2));wanted=snapshot(copy,U)
        old_fields=dict(initial);new_fields=dict(wanted);old_fields.pop('encoding_override');new_fields.pop('encoding_override')
        if old_fields!=new_fields:raise ValueError('Unrelated source color setting changed')
        text=copy.export_text();guard();texture.set_editor_property('source_color_settings',copy)
        guard();actual_settings=texture.get_editor_property('source_color_settings')
        if snapshot(actual_settings,U)!=wanted or actual_settings.export_text()!=text:raise RuntimeError('Actual complete encoding setting readback differs')
    if expected==0:
        guard()
        if snapshot(texture.get_editor_property('source_color_settings'),U)!=initial:raise RuntimeError('Default source color settings changed')
    reflected=read_encoding(U,texture,sha,image,guard)
    guard();after=json.loads(U.DinkMaterialArtLibrary.inspect_texture_source_pixels(texture));final=verify_storage(after,sha,image,target,expected)
    if prior['source_storage_sha256']!=final['source_storage_sha256']or prior['native_source_gamma']!=final['native_source_gamma']:raise RuntimeError('Stored bytes or intrinsic source gamma changed')
    return dict(profile=PROFILE,changed=expected==2,reflected_encoding=reflected,raw_source_storage=final,other_source_color_settings_preserved=True,saved=False,activated=False,gpu_pixel_equivalence_accepted=False)
