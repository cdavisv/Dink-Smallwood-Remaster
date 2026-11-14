"""Write Corpses/manifest.json, the kit manifest Scripts/import_town_exteriors.py reads, from the per-asset manifests.

    python3 -I tools/make_kit_manifest.py            # rewrite manifest.json
    python3 -I tools/make_kit_manifest.py --check    # fail when manifest.json is stale
    python3 -I tools/make_kit_manifest.py --all      # every built asset, bound or not (for a look in the game before binding)

Import (from DinkRemasterUE/, headless, re-runnable):

    DINK_KIT=Corpses DINK_KIT_FOLDER=Corpses Scripts/import_town_exteriors.sh

The kit has its own content folder, /Game/Dink/Photoreal/Corpses, with its own master materials (M_Struct_Baked for the
opaque atlases, M_Struct_Baked_Cut for the cut-out ones), so importing it never rewrites another kit's packages.
Without --all the kit lists only the meshes a row of Content/Dink/Data/Art/families.json uses.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(KIT, '..', '..', '..', '..', '..'))
ROOT = 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/Corpses'
GAME = '/Game/Dink/Photoreal/Corpses/'


def bound_meshes():
    rows = json.load(open(os.path.join(REPO, 'DinkRemasterUE', 'Content', 'Dink', 'Data', 'Art', 'families.json')))['families']
    paths = [r.get('mesh', '') for r in rows] + [v for r in rows for v in r.get('variants', [])]
    return {p.rsplit('.', 1)[1] for p in paths if p.startswith(GAME)}


def build(everything=False):
    assets, materials, skipped = [], {}, []
    bound = bound_meshes()
    for path in sorted(glob.glob(os.path.join(KIT, '*', 'manifest.json'))):
        m = json.load(open(path))
        if not everything and m['name'] not in bound:
            skipped.append({'name': m['name'], 'why': 'no families.json row uses it: ' + (m.get('not_bound') or 'not bound')})
            continue
        for k in m['kit_materials']:
            for f in list(k['files'].values()) + [m['fbx']]:
                if not os.path.isfile(os.path.join(REPO, f)):
                    raise SystemExit('%s: missing %s' % (m['name'], f))
            if k['name'] in materials:
                raise SystemExit('material name used twice: ' + k['name'])
            materials[k['name']] = {'baked': True, 'kind': k['kind'], 'files': k['files']}
        assets.append({'name': m['name'], 'class': m['class'], 'fbx': m['fbx'], 'materials': m['materials'],
                       'dimensions_m': [round(float(v), 3) for v in m['dimensions_m']], 'collision_hulls': 0,
                       'families': m['families'], 'folder': os.path.relpath(os.path.dirname(path), REPO).replace(os.sep, '/')})
    return {
        'schema': 'dink-props/1',
        'root': ROOT,
        'generated_by': 'Corpses/tools/make_kit_manifest.py (do not edit by hand)',
        'summary': '%d static meshes of remains, thrown blood and burn holes. Each FBX holds one object named after the asset (LOD0 only, no collision): '
                   'a body atlas (opaque, or cut-out where it carries hair) and, on a second slot, the alpha-tested ground card with the pool.' % len(assets),
        'assets': assets,
        'not_imported': skipped,
        'integration': {
            'contract': {'textures': 'BC sRGB (alpha = cut-out mask on masked materials); N linear OpenGL (flip green on import); ORM linear (R occlusion, G roughness, B metallic)',
                         'uv': 'UV0, unique bake, no tiling', 'collision': 'none imported; placements keep their hardbox'},
            'materials': materials,
        },
    }


def main():
    text = json.dumps(build('--all' in sys.argv), indent=1) + '\n'
    dest = os.path.join(KIT, 'manifest.json')
    if '--check' in sys.argv:
        if not os.path.isfile(dest) or open(dest).read() != text:
            raise SystemExit('Corpses/manifest.json is stale: run tools/make_kit_manifest.py')
        print('manifest.json is current')
        return
    open(dest, 'w').write(text)
    kit = json.loads(text)
    print('wrote manifest.json: %d assets, %d materials, %d not imported' % (len(kit['assets']), len(kit['integration']['materials']), len(kit['not_imported'])))


if __name__ == '__main__':
    main()
