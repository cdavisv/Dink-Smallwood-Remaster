"""Write Unclaimed/manifest.json, the kit manifest Scripts/import_town_exteriors.py reads, from the per-asset manifests.

    python3 -I tools/make_kit_manifest.py            # rewrite manifest.json
    python3 -I tools/make_kit_manifest.py --check    # fail when manifest.json is stale

Import (from DinkRemasterUE/, headless, re-runnable):

    DINK_KIT=Unclaimed DINK_KIT_FOLDER=Unclaimed Scripts/import_town_exteriors.sh

The kit holds the static meshes that a row of Content/Dink/Data/Art/families.json uses (its `mesh` or `variants`
under /Game/Dink/Photoreal/Unclaimed), so the imported content and the bindings always agree: bind a family first,
then run this, then import. `--all` lists every importable mesh instead (for a look in game before binding).
Importable: classes prop, prop_small, prop_large, building and door with one opaque baked set. Left out, each with
its reason in the manifest's `not_imported` list: meshes no row uses (the reason is the family's `binding` note in
tools/status_notes.json), rigged creatures and characters (they need skeletal import and clips), decal sets and
effect flipbooks (no mesh), and the posed human corpses and the king on his throne (their hair is an alpha-tested
atlas and their skin and eyes reuse character maps; the kit importer builds opaque, subsurface and translucent
baked materials only).
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UNC = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(UNC, '..', '..', '..', '..', '..'))
ROOT = 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/Unclaimed'
STATIC = {'prop', 'prop_small', 'prop_large', 'building', 'door'}
# Single-material assets whose normal and ORM maps are those of the rigged asset they were posed from.
SHARED = {
    'SM_Corpse_Knight_PR': ('npc_knight_blue/Knight/T_Knight_PR_N.png', 'npc_knight_blue/Knight/T_Knight_PR_ORM.png'),
    'SM_Dragon_Corpse_PR': ('dragon/Dragon/T_Dragon_PR_N.png', 'dragon/Dragon/T_Dragon_PR_ORM.png'),
}


def rel(path):
    return os.path.relpath(path, REPO).replace(os.sep, '/')


def bound_meshes():
    rows = json.load(open(os.path.join(REPO, 'DinkRemasterUE', 'Content', 'Dink', 'Data', 'Art', 'families.json')))['families']
    paths = [r.get('mesh', '') for r in rows] + [v for r in rows for v in r.get('variants', [])]
    return {p.rsplit('.', 1)[1] for p in paths if p.startswith('/Game/Dink/Photoreal/Unclaimed/')}


def build(everything=False):
    assets, materials, skipped = [], {}, []
    bound = bound_meshes()
    notes = json.load(open(os.path.join(HERE, 'status_notes.json')))
    for path in sorted(glob.glob(os.path.join(UNC, '*', '*', 'manifest.json'))):
        m = json.load(open(path))
        folder = os.path.dirname(path)
        if m['class'] not in STATIC:
            skipped.append({'name': m['name'], 'class': m['class'].split(' (')[0], 'why': 'not a static mesh'})
            continue
        mats = m.get('materials') or []
        roles = {}
        for t in m['textures']:
            stem = os.path.splitext(os.path.basename(t['file']))[0]
            roles.setdefault(stem.rsplit('_', 1)[1], []).append(t['file'])
        if m['name'] in SHARED:
            roles['N'] = [ROOT + '/' + SHARED[m['name']][0]]
            roles['ORM'] = [ROOT + '/' + SHARED[m['name']][1]]
        if len(mats) != 1 or any(len(roles.get(r, [])) != 1 for r in ('BC', 'N', 'ORM')):
            skipped.append({'name': m['name'], 'class': m['class'], 'why': '%d material slots (hair, eyes, skin): needs '
                            'masked and character materials the kit importer does not build' % len(mats)})
            continue
        if not everything and m['name'] not in bound:
            why = [notes.get(f, {}).get('binding') for f in m['families'] if notes.get(f, {}).get('binding')]
            skipped.append({'name': m['name'], 'class': m['class'], 'why': 'no families.json row uses it: ' + (why[0] if why else 'not bound')})
            continue
        files = {r: roles[r][0] for r in ('BC', 'N', 'ORM')}
        if len(roles.get('E', [])) == 1:
            files['E'] = roles['E'][0]
        for f in list(files.values()) + [m['fbx']]:
            if not os.path.isfile(os.path.join(REPO, f)):
                raise SystemExit('%s: missing %s' % (m['name'], f))
        if mats[0] in materials:
            raise SystemExit('material name used twice: ' + mats[0])
        materials[mats[0]] = {'baked': True, 'kind': 'opaque', 'files': files}
        assets.append({'name': m['name'], 'class': m['class'], 'fbx': m['fbx'], 'materials': mats,
                       'dimensions_m': [round(float(v), 3) for v in m['dimensions_m']],
                       'collision_hulls': m.get('collision_hulls', 0),
                       'families': m['families'], 'folder': rel(folder)})
    return {
        'schema': 'dink-props/1',
        'root': ROOT,
        'generated_by': 'Unclaimed/tools/make_kit_manifest.py (do not edit by hand)',
        'summary': '%d static meshes of the unclaimed gate 2 families that families.json binds, each with one baked opaque set (BC / N OpenGL / ORM). '
                   'Every FBX holds one object named after the asset (LOD0 only) and, where collision_hulls is 1, a UCX hull '
                   'that the importer drops: the family layer is visual only.' % len(assets),
        'assets': assets,
        'not_imported': skipped,
        'integration': {
            'contract': {'textures': 'BC sRGB; N linear OpenGL (flip green on import); ORM linear (R occlusion, G roughness, B metallic)',
                         'uv': 'UV0, unique bake, no tiling', 'collision': 'none imported; placements keep their hardbox'},
            'materials': materials,
        },
    }


def main():
    text = json.dumps(build('--all' in sys.argv), indent=1) + '\n'
    dest = os.path.join(UNC, 'manifest.json')
    if '--check' in sys.argv:
        if not os.path.isfile(dest) or open(dest).read() != text:
            raise SystemExit('Unclaimed/manifest.json is stale: run tools/make_kit_manifest.py')
        print('manifest.json is current')
        return
    open(dest, 'w').write(text)
    kit = json.loads(text)
    print('wrote manifest.json: %d assets, %d materials, %d not imported' % (len(kit['assets']), len(kit['integration']['materials']), len(kit['not_imported'])))


if __name__ == '__main__':
    main()
