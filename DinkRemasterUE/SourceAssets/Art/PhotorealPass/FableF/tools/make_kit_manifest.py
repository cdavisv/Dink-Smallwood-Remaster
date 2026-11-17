"""Kit manifest of Fable stream F's sources for Scripts/import_town_exteriors.py.

    python3 -I SourceAssets/Art/PhotorealPass/FableF/tools/make_kit_manifest.py [--check]
    DINK_KIT=FableF DINK_KIT_FOLDER=FableF Scripts/import_town_exteriors.sh

Reads every <family>/<Asset>/manifest.json of this folder: effect flipbooks become `flipbooks` rows (additive
M_FX_Flipbook, or the translucent M_FX_Flipbook_Blend when the flipbook says "blend": "translucent"), static meshes
with one baked BC / N / ORM set become `assets` rows. Everything lands in /Game/Dink/Photoreal/FableF.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
ROOT = 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/FableF'


def build():
    assets, materials, flipbooks = [], {}, []
    for path in sorted(glob.glob(os.path.join(KIT, '*', '*', 'manifest.json'))):
        m = json.load(open(path))
        rel = ROOT + '/' + os.path.relpath(os.path.dirname(path), KIT).replace(os.sep, '/')
        if m.get('flipbook'):
            fb = m['flipbook']
            row = {'name': m['name'][len('FX_'):], 'file': m['textures'][0]['file'], 'grid': fb['grid'], 'fps': fb['fps'],
                   'glow': fb.get('glow', 6), 'families': m['families']}
            if fb.get('blend') == 'translucent':
                row['blend'] = 'translucent'
            if fb.get('hot'):
                row['hot'] = fb['hot']
            flipbooks.append(row)
            continue
        mat = 'MI_' + m['name'][len('SM_'):]
        files = {}
        for t in m['textures']:
            files[os.path.splitext(os.path.basename(t['file']))[0].rsplit('_', 1)[1]] = t['file']
        materials[mat] = {'baked': True, 'kind': m.get('material_kind', 'opaque'), 'files': files}
        assets.append({'name': m['name'], 'class': m['class'], 'fbx': rel + '/' + m['name'] + '.fbx', 'materials': [mat],
                       'dimensions_m': m['dimensions_m'], 'collision_hulls': m.get('collision_hulls', 0), 'families': m['families'], 'folder': rel})
    return {
        'schema': 'dink-props/1',
        'root': ROOT,
        'generated_by': 'FableF/tools/make_kit_manifest.py (do not edit by hand)',
        'summary': 'Gate 2 families outside every work packet (Fable stream F, 15 Nov 2026): %d effect flipbooks, %d static meshes.' % (len(flipbooks), len(assets)),
        'assets': assets,
        'flipbooks': flipbooks,
        'integration': {
            'contract': {'textures': 'BC sRGB; N linear OpenGL (flip green on import); ORM linear (R occlusion, G roughness, B metallic)',
                         'uv': 'UV0, unique bake, no tiling', 'collision': 'none imported; placements keep their hardbox'},
            'materials': materials,
        },
    }


def main():
    text = json.dumps(build(), indent=1) + '\n'
    dest = os.path.join(KIT, 'manifest.json')
    if '--check' in sys.argv:
        if not os.path.isfile(dest) or open(dest).read() != text:
            raise SystemExit('FableF/manifest.json is stale: run tools/make_kit_manifest.py')
        print('manifest.json is current')
        return
    open(dest, 'w').write(text)
    print('wrote manifest.json: %d flipbooks, %d meshes' % (text.count('"grid"'), text.count('"fbx"')))


if __name__ == '__main__':
    main()
