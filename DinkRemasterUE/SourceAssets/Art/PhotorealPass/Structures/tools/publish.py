"""Write the integration blocks, the kit manifests, Structures/manifest.json and the contact sheets.
python3 -I publish.py   (after the build scripts and review renders; render folders are named in each kit's tools/notes.json 'render_dir')"""
import json, os, subprocess, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); S = os.path.dirname(HERE); PP = os.path.dirname(S)
REL = 'DinkRemasterUE/SourceAssets/Art/PhotorealPass'
KITS = [os.path.join(PP, 'TownExteriors'), os.path.join(S, 'Stonebrook'), os.path.join(S, 'Castle')] + [os.path.join(S, k) for k in ('Misc',) if os.path.isdir(os.path.join(S, k))]
CONTRACT = {
 'uv': 'UV0 already carries the tiling: one UV unit is one repeat of the set (tile_size_m is the nominal size the UVs were laid out for; small blocks use up to 2x denser UVs). Sample BC, N, ORM and H at UV0; sample Macro at UV0 / 7. Do not rescale.',
 'textures': 'BC sRGB; N linear OpenGL (flip green on import); ORM linear (R ambient occlusion, G roughness, B metallic = 0); H linear 16-bit height, used 0..1; Macro linear 512 px (R large, G medium, B small variation).',
 'vertex_colour': "FBX vertex colour set 'Grime', linear RGBA float, exported with every LOD. R = dirt and damp, G = moss / algae, B = bleaching (silvered oak, lichen, dressed stone, fresh straw), A = material switch (see below; 1 everywhere else).",
 'graph': [
  'base = BC * tint * (1 - macro + 2 * macro * Macro.R)',
  'base = lerp(base, base * ORM.R, 0.5)',
  'fd = saturate(R * (1.15 - 0.5 * H))',
  "dirt_mode multiply: c = lerp(base, base * dirt, fd * dirt_amount);   dirt_mode mix: c = lerp(base, dirt * (3 * luminance(base) + 0.35), fd * dirt_amount)",
  'fb = saturate(B * saturate(0.9 * H + 0.35));   c = lerp(c, pale * (2.2 * luminance(c) + 0.55), fb * pale_amount)',
  'fm = saturate(4 * ((G + 0.5 * Macro.B) - (0.55 * H + 0.62))) * (G > 0.02);   c = lerp(c, moss * (0.9 * Macro.G + 0.55), fm)',
  'roughness = lerp(ORM.G, moss_roughness, fm) - 0.10 * fd;   normal = N;   metallic = 0',
  'alpha_switch materials only: A < 0.875 lead (only where alpha_lead is true): colour (0.15, 0.16, 0.17) * (0.7 * Macro.G + 0.65), roughness 0.42, flat normal;  A < 0.625 (A < 0.75 where alpha_lead is false) black iron, charred wood, burnt straw or unlit void: colour (0.016, 0.015, 0.014), roughness 0.5 + 0.42 * R (iron has R = 0, char has R = 1), normal kept;  A < 0.25 window glass: colour glass_tint, roughness 0.06, flat normal, opaque (the pane mesh is faceted so each quarry reflects differently; a dark closed box stands behind it). Values written: 1, 0.75, 0.5, 0.',
  'alpha_soot materials only: fs = saturate((1 - A) * (0.7 * Macro.G + 1.0));  c = lerp(c, (0.012, 0.011, 0.010), fs);  roughness = lerp(roughness, 0.97, fs)'],
 'colours': 'all colours are linear RGB',
 'fbx': 'One FBX per asset beside the manifest: mesh objects <asset>_LOD0, _LOD1, _LOD2 (import as one static mesh with three LODs) and UCX_<asset>_LOD0_NN convex hulls; metres with UnitScaleFactor 100; Z up, front -Y; smoothing by edge (import normals); material slots in the order of each module\'s "materials" list. Family meshes are visual only (ART_STANDARD section 5).'}


def set_block(name):
    for root, rel in ((os.path.join(S, 'Sets'), REL + '/Structures/Sets'), (os.path.join(PP, 'Terrain'), REL + '/Terrain')):
        p = os.path.join(root, name, 'set.json')
        if os.path.exists(p):
            info = json.load(open(p))
            return {'tile_size_m': info['tile_size_m'], 'files': {k: rel + '/' + v for k, v in info['files'].items() if k in ('BC', 'N', 'ORM', 'H', 'Macro')},
                    'third_party': [u['asset_id'] for u in info.get('third_party', [])]}
    raise SystemExit('no set ' + name)


def integration(kit, notes):
    mats = json.load(open(os.path.join(kit, 'materials.json')))
    mods = []
    for f in notes.get('module_files', ['modules.json']):
        mods += json.load(open(os.path.join(kit, f)))
    out = {'contract': CONTRACT, 'materials': {}, 'assets': {}}
    for name, m in mats.items():
        b = dict(m); b.update(set_block(m['set'])); b['texture_set'] = b.pop('set')
        if not b.get('alpha_switch'):
            b.pop('glass_tint', None)
        out['materials'][name] = b
    for r in mods:
        if 'textures' in r:                      # a private bake: its own BC / N / ORM on unique UVs, no vertex-colour layer
            out['materials'][r['materials'][0]] = {'baked': True, 'texture_px': r['texture_px'], 'files': {k: REL + '/' + os.path.relpath(os.path.join(kit, v), PP).replace(os.sep, '/') for k, v in r['textures'].items()},
                                                   'graph': 'base colour = BC, normal = N (OpenGL, flip green), occlusion = ORM.R, roughness = ORM.G, metallic 0; UV0 is a unique unwrap in 0-1; no vertex colour'}
        out['assets'][r['name']] = {'fbx': REL + '/' + os.path.relpath(os.path.join(kit, r['fbx']), PP).replace(os.sep, '/'), 'class': r['class'], 'material_slots': r['materials'],
                                    'lod_triangles': [r['lod0_triangles'], r['lod1_triangles'], r['lod2_triangles']], 'bounds_min_m': r['bounds_min_m'], 'bounds_max_m': r['bounds_max_m'], 'collision_hulls': r['collision_hulls']}
    return out


allint = {}
for kit in KITS:
    np_ = os.path.join(kit, 'tools', 'notes.json'); notes = json.load(open(np_))
    notes['integration'] = integration(kit, notes); json.dump(notes, open(np_, 'w'), indent=1)
    rd = notes.get('render_dir')
    subprocess.check_call([sys.executable, '-I', os.path.join(HERE, 'finish.py'), kit, os.path.join(S, 'review', rd)])
    if kit.startswith(S):
        allint[os.path.basename(kit)] = notes['integration']
mp = os.path.join(S, 'manifest.json'); man = json.load(open(mp))
man['kits'] = {os.path.basename(k): json.load(open(os.path.join(k, 'manifest.json'))) for k in KITS if k.startswith(S)}
mats = {}; assets = {}
for v in allint.values():
    mats.update(v['materials']); assets.update(v['assets'])
man['integration'] = {'contract': CONTRACT, 'materials': mats, 'assets': assets}
json.dump(man, open(mp, 'w'), indent=1)
ims = [Image.open(os.path.join(k, 'contact_sheet.png')) for k in KITS if k.startswith(S)]
w = 1600; ims = [i.resize((w, int(i.height * w / i.width)), Image.LANCZOS) for i in ims]
s = Image.new('RGB', (w, sum(i.height + 8 for i in ims)), (18, 18, 18)); y = 0
for i in ims:
    s.paste(i, (0, y)); y += i.height + 8
s.save(os.path.join(S, 'contact_sheet.png')); print('published', [os.path.basename(k) for k in KITS], s.size)
