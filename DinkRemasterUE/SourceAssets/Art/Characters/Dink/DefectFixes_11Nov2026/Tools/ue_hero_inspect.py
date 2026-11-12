"""Read-only inspection of the hero's materials, atlas textures and skeletal mesh build settings.

UnrealEditor-Cmd <DinkRemaster.uproject> -run=pythonscript -script="<this file> inspect <report.json>" -nullrhi -unattended -nosplash -nopause
Writes only the report: for each MI_Dink_* its base material's domain, blend mode, two-sided flag, clip
value and shading model; every T_Dink_Atlas_* setting; and LOD build/import settings of SK_Dink and
SK_Dink_Hands. Used on 11 Nov 2026 to rule the materials out as the cause of the backlit head lines.
"""
import json, sys
from pathlib import Path
import unreal
args = [a for a in sys.argv[1:]]
MODE, REPORT = args[0], Path(args[1])
TEX = '/Game/Dink/Textures/Characters/'
MATS = ['MI_Dink_Skin', 'MI_Dink_Eyes', 'MI_Dink_Hair', 'MI_Dink_BrowLash', 'MI_Dink_Wardrobe']
PROPS = ['srgb', 'compression_settings', 'flip_green_channel', 'lod_group', 'mip_gen_settings', 'filter',
         'address_x', 'address_y', 'never_stream', 'compression_no_alpha', 'lod_bias', 'max_texture_size',
         'adjust_brightness', 'adjust_saturation', 'adjust_vibrance', 'adjust_rgb_curve', 'compression_quality']
def tex_props(t):
    out = {}
    for p in PROPS:
        try: out[p] = str(t.get_editor_property(p))
        except Exception as e: out[p] = 'n/a'
    try: out['source_file'] = str(t.get_editor_property('asset_import_data').get_first_filename())
    except Exception: out['source_file'] = 'n/a'
    out['size'] = [t.blueprint_get_size_x(), t.blueprint_get_size_y()]
    return out
report = {'mode': MODE}
if MODE == 'inspect':
    mats = {}
    for name in MATS:
        m = unreal.load_asset('/Game/Dink/Materials/Characters/' + name)
        base = m.get_base_material()
        row = {'class': m.get_class().get_name(), 'base': base.get_path_name()}
        for p in ['material_domain', 'blend_mode', 'two_sided', 'opacity_mask_clip_value', 'shading_model', 'subsurface_profile', 'dithered_lod_transition', 'tangent_space_normal']:
            try: row[p] = str(base.get_editor_property(p))
            except Exception: row[p] = 'n/a'
        row['textures'] = sorted(t.get_path_name() for t in unreal.MaterialEditingLibrary.get_used_textures(m))
        mats[name] = row
    report['materials'] = mats
    report['textures'] = {n: tex_props(unreal.load_asset(TEX + n)) for n in ['T_Dink_Atlas_BC', 'T_Dink_Atlas_N', 'T_Dink_Atlas_ORM']}
    meshes = {}
    for path in ['/Game/Dink/Hero/Refinements/SK_Dink_Hands', '/Game/Dink/Hero/SK_Dink']:
        mesh = unreal.load_asset(path); row = {'lods': []}
        sub = unreal.SkeletalMeshEditorSubsystem
        for lod in range(sub.get_lod_count(mesh)):
            entry = {}
            try:
                bs = sub.get_lod_build_settings(mesh, lod)
                for p in ['recompute_normals', 'recompute_tangents', 'use_mikk_t_space', 'compute_weighted_normals', 'remove_degenerates',
                          'use_high_precision_tangent_basis', 'use_full_precision_u_vs', 'threshold_position', 'threshold_tangent_normal', 'threshold_uv']:
                    try: entry[p] = str(bs.get_editor_property(p))
                    except Exception: entry[p] = 'n/a'
            except Exception as e: entry['build_settings'] = 'n/a: ' + str(e)
            row['lods'].append(entry)
        try: row['lod_screen_sizes'] = [str(i.get_editor_property('screen_size')) for i in mesh.get_editor_property('lod_info')]
        except Exception as e: row['lod_screen_sizes'] = 'n/a: ' + str(e)
        try:
            imp = mesh.get_editor_property('asset_import_data')
            row['import'] = {p: str(imp.get_editor_property(p)) for p in ['normal_import_method', 'normal_generation_method', 'compute_weighted_normals', 'threshold_position', 'threshold_tangent_normal', 'threshold_uv']}
            row['import']['source'] = str(imp.get_first_filename())
        except Exception as e: row['import'] = 'n/a: ' + str(e)
        meshes[path] = row
    report['meshes'] = meshes
REPORT.write_text(json.dumps(report, indent=2) + '\n')
unreal.log('DINK HERO ATLAS ' + MODE.upper() + ' DONE ' + str(REPORT))
