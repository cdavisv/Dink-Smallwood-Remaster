"""Publish the props: copy each FBX from Props/_build into Props/<Name>/, write per-asset manifests and Props/manifest.json
(inventory + assets + the integration block, same contract as Structures/manifest.json) and Props/contact_sheet.png.
python3 -I props_publish.py   (after props_build.py, the review renders named in tools/notes.json and inventory.py)"""
import json, os, shutil, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); PROPS = os.path.dirname(HERE); PP = os.path.dirname(PROPS)
REL = 'DinkRemasterUE/SourceAssets/Art/PhotorealPass'
_s = open(os.path.join(PP, 'Structures', 'tools', 'publish.py')).read()
_g = {}
exec(_s[_s.index('CONTRACT = {'):_s.index('def set_block')], _g)
CONTRACT = dict(_g['CONTRACT'])
CONTRACT['props_note'] = ("Props use the structure contract unchanged. Slot materials on the WroughtIron set (MI_Prop_Iron) use dirt_mode mix: R is rust, B is bright wear. "
                          "alpha_switch materials on props: A 0.5 marks forged nail heads, lock plates and unlit voids (crate interiors, eye sockets, wick), A 0 on MI_Prop_PotionGlass_* is the tinted opaque glass.")
CONTRACT['round2_material_upgrades'] = {
    'metal_tiling': "Tiling props (not baked): every material whose entry has \"metal\": true (MI_Prop_Iron) is METALLIC. metallic = 1 - saturate(fd * dirt_amount) (rust, vertex colour R, is dielectric); "
                    "base colour of the clean iron = BC * (0.55, 0.56, 0.6); where fb (vertex colour B, worn bright) > 0: base colour -> (0.5, 0.49, 0.47), roughness -> 0.3, metallic 1. "
                    "On alpha_switch materials the A < 0.625 'black iron' region (nail heads, lock plates, straps) is metallic = 1 - R with base colour (0.075, 0.075, 0.085), roughness 0.45 + 0.45 * R. "
                    "The Blender preview materials in Props.blend still show these dielectric; the baked props below carry true metal in ORM.B.",
    'baked': "Baked props (asset entry has \"baked\"): NO vertex colour, NO tiling sets. Every slot of the asset samples the SAME unique texture set at UV0 (non-overlapping): "
             "T_<Asset>_BC (sRGB), T_<Asset>_N (linear, OpenGL +Y: flip green on import), T_<Asset>_ORM (linear; R ambient occlusion, G roughness, B metallic: real values, iron and steel are 1 with rust 0), "
             "and, when listed, T_<Asset>_E (sRGB emissive colour 0..1; emissive = E * emissive_nits * flicker; set the multiplier to 0 for an unlit state). Slots differ only in shading model, given by slot kind.",
    'slot_kinds': {'opaque': 'Default Lit, opaque',
                   'subsurface': 'wax / tallow: Subsurface (or Subsurface Profile) shading model, subsurface colour = BC * 0.9, mean free path about 8 mm (params.sss_radius = RGB radii in metres), opaque',
                   'translucent': 'glass / horn panes: thin translucent, two-sided, no refraction needed. Horn: Translucent or Two Sided Foliage style with opacity 0.75 and transmission colour = BC; glass: Translucent, opacity 0.35 + fresnel, tint = BC. '
                                  'Emissive from E as for the other slots (the horn panes of a lit lantern glow through E). The mesh carries dink_translucent (Nanite off).'},
    'glass_and_embers_not_baked': "Props still on tiling sets (asset entry has no \"baked\"): SM_Potion_Flask_PR: the alpha 0 region of MI_Prop_PotionGlass_* is the glass; give that material a translucent variant (opacity 0.35 + fresnel, tint = glass_tint, roughness 0.06, two-sided) and the flask reads as glass with the dark liquid box behind it. SM_Shelf_Bottles_PR bottles are glazed earthenware, opaque by design. SM_Fireplace_Fieldstone_PR has NO ember mask yet (not reached in round 2): light the hearth with an engine fire effect.",
    'decals': "Props/Decals (decals.json): T_Decal_BloodSplat_* and T_Decal_BurnHole_*, 2 x 2 atlases, BC alpha = opacity; see the 'decals' block of this manifest.",
    'texture_caps': 'Baked props ship 2048 px (prop) or 1024 px (prop_small and the lantern). Props that dress a family as scatter are capped at 1024 by ART_STANDARD section 4: list T_<Asset>_ in Content/Dink/Data/Art/texture_import_caps.json to cap on import if wanted; the source stays 2048.'}
notes = json.load(open(os.path.join(HERE, 'notes.json')))
mods = json.load(open(os.path.join(PROPS, '_build', 'modules.json')))
mats = json.load(open(os.path.join(PROPS, '_build', 'materials.json')))
inv = json.load(open(os.path.join(PROPS, 'inventory.json')))


def set_block(name):
    for root, rel in ((os.path.join(PROPS, 'Sets'), REL + '/Props/Sets'), (os.path.join(PP, 'Structures', 'Sets'), REL + '/Structures/Sets'), (os.path.join(PP, 'Terrain'), REL + '/Terrain')):
        p = os.path.join(root, name, 'set.json')
        if os.path.exists(p):
            info = json.load(open(p))
            return {'tile_size_m': info['tile_size_m'], 'files': {k: rel + '/' + v for k, v in info['files'].items() if k in ('BC', 'N', 'ORM', 'H', 'Macro')},
                    'third_party': [u['asset_id'] for u in info.get('third_party', [])]}
    raise SystemExit('no set ' + name)


imat = {}
for r in mods:
    bk = r.get('baked')
    if bk:
        for sl in bk['slots']:
            imat[sl['material']] = {'baked': True, 'kind': sl['kind'], 'files': {k: REL + '/Props/' + bk['texture_folder'] + '/' + v for k, v in bk['textures'].items()}, 'resolution_px': bk['px'],
                                    'emissive_nits': bk.get('emissive_nits'), 'params': bk.get('params'), 'third_party': bk.get('third_party', []), 'texture_set': None}
for name, m in mats.items():
    if name in imat:
        continue
    b = dict(m); b.update(set_block(m['set'])); b['texture_set'] = b.pop('set')
    if name == 'MI_Prop_Iron':
        b['metal'] = True
    if not b.get('alpha_switch'):
        b.pop('glass_tint', None)
    imat[name] = b
assets = []; iassets = {}
for r in mods:
    short = r['name'][3:-3] if r['name'].endswith('_PR') else r['name'][3:]
    d = os.path.join(PROPS, short); os.makedirs(d, exist_ok=True)
    shutil.copy2(os.path.join(PROPS, '_build', r['fbx']), os.path.join(d, r['fbx']))
    rec = dict(r); rec['folder'] = REL + '/Props/' + short; rec['fbx'] = REL + '/Props/' + short + '/' + r['fbx']; rec['source_blend'] = REL + '/Props/_build/Props.blend'
    rec['build'] = 'DINK_PP=<PhotorealPass> blender -b -t 4 --python Props/tools/props_build.py'
    rec.update(notes.get('all_assets', {})); rec.update(notes['assets'].get(r['name'], {}))
    rec.setdefault('status', 'interim')
    rec['third_party'] = sorted({t for s in r['materials'] for t in imat[s]['third_party']})
    rec['texture_sets'] = sorted({imat[s]['texture_set'] for s in r['materials'] if imat[s]['texture_set']})
    rec['textures_px'] = r['baked']['px'] if r.get('baked') else 2048
    if r.get('baked'):
        rec.update(notes.get('baked_assets', {})); rec.update(notes['assets'].get(r['name'], {}))
        rec['source_blend'] = REL + '/Props/' + r['baked']['source_blend']; rec['build'] = 'DINK_PP=<PhotorealPass> blender -b -t 4 --python Props/tools/props_bake.py -- <asset>; then blender -b Props/_build/Props.blend --python Props/tools/props_merge.py'
        rec['textures'] = {k: REL + '/Props/' + r['baked']['texture_folder'] + '/' + v for k, v in r['baked']['textures'].items()}
    for k in [k for k in rec if k.endswith('+')]:         # "emissive+": {...} in notes merges into the dict from modules.json
        rec[k[:-1]] = dict(rec.get(k[:-1], {}), **rec.pop(k))
    json.dump(rec, open(os.path.join(d, 'manifest.json'), 'w'), indent=1)
    assets.append(rec)
    iassets[r['name']] = {'fbx': rec['fbx'], 'class': r['class'], 'material_slots': r['materials'], 'lod_triangles': [r['lod0_triangles'], r['lod1_triangles'], r['lod2_triangles']],
                          'bounds_min_m': r['bounds_min_m'], 'bounds_max_m': r['bounds_max_m'], 'collision_hulls': r['collision_hulls']}
    if 'emissive' in rec:
        iassets[r['name']]['emissive'] = rec['emissive']
    if r.get('baked') and r['baked'].get('extra'):
        iassets[r['name']].update(r['baked']['extra'])
    if r.get('baked'):
        iassets[r['name']]['baked'] = {'slots': r['baked']['slots'], 'textures': rec['textures'], 'resolution_px': r['baked']['px'], 'emissive_nits': r['baked'].get('emissive_nits'), 'params': r['baked'].get('params')}
# colour variants (notes.json "slot_variants"): the same FBX under a further asset name with other slot materials, so that a sprite
# family can bind it (families.json binds a mesh, not a mesh and a material): the potion flask in its three glass tints
for base, variants in (notes.get('slot_variants') or {}).items():
    src = next(a for a in assets if a['name'] == base)
    for vname, v in variants.items():
        rec = dict(src, name=vname, materials=[v['slots'].get(m, m) for m in src['materials']], families=v['families'], slot_override=v['slots'], variant_of=base,
                   supersedes=v.get('supersedes', src.get('supersedes')))
        assets.append(rec)
        iassets[vname] = dict(iassets[base], material_slots=rec['materials'], slot_override=v['slots'], variant_of=base)
built = {}
for a in assets:
    for f in a['families']:
        built.setdefault(f, []).append(a['name'])
man = {'schema': 'dink-props/1', 'root': REL + '/Props', 'date': notes.get('date'), 'contact_sheet': 'contact_sheet.png',
       'summary': notes.get('summary'), 'review': notes.get('review'), 'validator': notes.get('validator'), 'not_done': notes.get('not_done'),
       'inventory': dict(inv, built_this_pass=notes.get('built_classes'), remaining_note=notes.get('remaining_note')),
       'texture_sets': [dict(json.load(open(os.path.join(PROPS, 'Sets', s, 'set.json'))), folder=REL + '/Props/Sets/' + s) for s in sorted(os.listdir(os.path.join(PROPS, 'Sets')))],
       'decals': json.load(open(os.path.join(PROPS, 'Decals', 'decals.json'))) if os.path.exists(os.path.join(PROPS, 'Decals', 'decals.json')) else None,
       'assets': assets, 'integration': {'contract': CONTRACT, 'materials': imat, 'assets': iassets}}
# contact sheet: the final review renders named in notes['sheet'], two per row
RD = os.path.join(PROPS, 'review', notes['render_dir'])
try:
    font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', 20)
except Exception:
    font = ImageFont.load_default()
strips = []                                             # baked props first: one strip each (gameplay camera, 1 m, interior light) from the newest review round
import glob, re
rdirs = sorted(os.listdir(os.path.join(PROPS, 'review')), key=lambda d_: int(re.sub(r'\D', '', d_) or 0), reverse=True)
for r in mods:
    if not r.get('baked') or r['name'] in notes.get('sheet_skip', []):
        continue
    short = r['name'][3:-3] if r['name'].endswith('_PR') else r['name'][3:]
    for d_ in rdirs:
        fs = [os.path.join(PROPS, 'review', d_, '%s_%s.png' % (short, v)) for v in ('game', 'close', 'int', 'open')]
        fs = [f for f in fs if os.path.exists(f)]
        if fs:
            strips.append((fs, '%s  (baked, %s)' % (r['name'], d_))); break
shots = []
for e in notes['sheet']:                               # [render, caption] or [render, caption, review dir]
    d_ = os.path.join(PROPS, 'review', e[2]) if len(e) > 2 else RD
    if os.path.exists(os.path.join(d_, e[0] + '.png')):
        shots.append((os.path.join(d_, e[0] + '.png'), e[1]))
tw, th = 1100, 760; cols = 2
sh = 540; y0 = len(strips) * (sh + 34)
s = Image.new('RGB', (cols * tw, y0 + ((len(shots) + cols - 1) // cols) * (th + 34)), (18, 18, 18)); d = ImageDraw.Draw(s)
for i, (fs, cap) in enumerate(strips):
    x = 0; d.text((8, i * (sh + 34) + 4), cap, fill=(235, 235, 235), font=font)
    for f in fs[:3]:
        im = Image.open(f).convert('RGB'); im = im.resize((int(im.width * sh / im.height), sh), Image.LANCZOS); s.paste(im, (x, i * (sh + 34) + 30)); x += im.width + 6
for i, (n, cap) in enumerate(shots):
    x, y = (i % cols) * tw, y0 + (i // cols) * (th + 34)
    s.paste(Image.open(n).convert('RGB').resize((tw, th), Image.LANCZOS), (x, y + 30)); d.text((x + 8, y + 4), cap, fill=(235, 235, 235), font=font)
s = s.convert('RGB').resize((1400, int(s.height * 1400 / s.width)), Image.LANCZOS)          # keep the sheet small enough to open
s.save(os.path.join(PROPS, 'contact_sheet.png'), optimize=True)
json.dump(man, open(os.path.join(PROPS, 'manifest.json'), 'w'), indent=1)
print('published', len(assets), 'props; sheet', s.size)
