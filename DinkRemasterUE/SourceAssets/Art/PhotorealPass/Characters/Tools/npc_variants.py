"""Colour variants of imported characters: writes the recoloured base colour maps and Characters/NPC/variants.json,
which Scripts/import_photoreal_art.py (DINK_PHOTOREAL_ONLY=npcs) turns into copies of the base mesh with instances of
the base's materials. A variant is the base's twin in another dress: same body, face, hair shape and skin weights.

    python3 -I npc_variants.py        (after the Mother or Milder textures change: their outfit maps are the input)"""
import json
import numpy as np
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
CHARS = Path(__file__).resolve().parent.parent; NPC = CHARS / 'NPC'; UNC = '../../Unclaimed'
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def recolour(src, dst, target, pick, keep=0.12, gain=2.4, size=2048):
    """tint the pixels chosen by pick(rgb) -> 0..1 towards target, keeping their light and dark (as Unclaimed/tools/build_npcs.py)"""
    a = np.asarray(Image.open(src).convert('RGB').resize((size, size), Image.LANCZOS), np.float32) / 255.0
    m = np.clip(pick(a), 0, 1)[..., None]; lum = (a @ LUMA)[..., None]
    out = a * (1 - m) + m * (a * keep + (1 - keep) * np.clip(lum * gain, 0, 1.2) * np.array(target, np.float32))
    dst.parent.mkdir(parents=True, exist_ok=True); Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(dst, optimize=True)


def is_red(a): return (a[..., 0] - np.maximum(a[..., 1], a[..., 2]) - 0.06) * 8.0
def is_blue(a): return (a[..., 2] - np.maximum(a[..., 0], a[..., 1]) - 0.03) * 8.0


# 1997 walk bases (dink.ini sequences base+1..base+9) each figure stands for: scripts dress their people with
# sp_base_walk, so Scripts/bind_npc_characters.py writes characters.json `walk_base_profiles` and `script_profiles` from these.
WALK_BASE = {'MaidenRed': [220], 'MaidenBrown': [240], 'MaidenBlue': [250], 'Soldier': [400], 'KnightRed': [270], 'KnightSilver': [290], 'KnightGold': [300],
             'MerchantGreen': [380], 'MerchantRed': [340], 'MerchantPurple': [390], 'MatronGreen': [360]}


DRESS = {   # name: (base, slot stem, colour, pick, gain, hair tint, animation set, family, what it is)
    # hair as the 1997 pictures have it (221 and 251: yellow blonde; 241: orange auburn). The atlas is dark: a blonde needs a tint above 1
    # (the hero's is 2.4, 1.5, 1.1); at 0.86 the blue maiden's hair was dark brown in the game.
    'MaidenBlue': ('Mother', (0.15, 0.21, 0.45), is_red, 3.4, (1.45, 1.15, 0.62), 'NpcF', 'npc_maiden_blue', 'woman in a long blue dress, blonde hair'),
    'MaidenBrown': ('Mother', (0.34, 0.23, 0.13), is_red, 3.6, (1.00, 0.52, 0.24), 'NpcF', 'npc_maiden_brown', 'woman in a long brown dress, auburn hair'),
    'MaidenRed': ('Mother', (0.50, 0.03, 0.10), is_red, 3.4, (1.45, 1.15, 0.62), 'NpcF', 'npc_maiden_red', 'woman in a long crimson dress, blonde hair'),
    # the stout woman in the green dress (pictures 361-369: Nadine of Terris, the mother of Joppa): the Mother herself, her own aged skin
    'MatronGreen': ('Mother', (0.17, 0.24, 0.08), is_red, 3.4, (0.40, 0.36, 0.30), 'NpcF', None, 'older woman in a long green dress, greying brown hair'),
    'Soldier': ('Milder', (0.22, 0.13, 0.07), is_blue, 2.4, (0.40, 0.34, 0.28), 'NpcM', 'npc_soldier', 'soldier: Milder\'s harness with a brown gambeson, dark hair'),
}
variants = {}
for name, (base, colour, pick, gain, hair, aset, fam, what) in DRESS.items():
    out = NPC / name / 'Textures' / f'T_{name}_PR_Outfit_BC.png'
    recolour(CHARS / base / 'Textures' / f'T_{base}_PR_Outfit_BC.png', out, colour, pick, gain=gain)
    variants[name] = {'base': base, 'base_asset': f'SK_{base}_Photoreal', 'animation_set': aset, 'families': [fam] if fam else [], 'what': what, 'placement_scale': 0.9 if base == 'Mother' else 1.0,
                      'materials': {f'MI_{base}_PR_Outfit': {'textures': {'BC': f'{name}/Textures/{out.name}'}}, f'MI_{base}_PR_Hair': {'tint': list(hair)}}}
    if base == 'Mother' and name.startswith('Maiden'):
        # a younger skin for the three women (one set for all): NPC/Maiden/cfg/skin.json is the Mother's with the age
        # lines, broken capillaries and sun damage taken down; bake it with
        #   blender -b -t 4 --python dink_05b_skin.py -- <abs path>/NPC/Maiden/cfg/skin.json
        variants[name]['materials']['MI_Mother_PR_Skin'] = {'textures': {r: f'Maiden/Textures/T_Maiden_PR_Skin_{r}.png' for r in ('BC', 'N', 'ORM', 'SSS')}, 'tint': [0.80, 0.75, 0.72]}
    print('recoloured', out.name)
variants['KnightSilver'] = {'base': 'NPC/Knight', 'base_asset': 'SK_Knight_Photoreal', 'animation_set': 'NpcM', 'families': ['npc_knight_silver'], 'what': 'the knight in bright harness',
                            'materials': {'MI_Knight_PR_Outfit': {'textures': {'BC': f'{UNC}/npc_knight_blue/Knight/T_Knight_PR_Silver_BC.png'}, 'tint': [2.5, 2.3, 1.8]}}}   # the silver map is nearly as dark and blue as the blue one, and polished metal shows the blue of the sky light: in a hall both read blue
variants['MerchantGreen'] = {'base': 'NPC/Merchant', 'base_asset': 'SK_Merchant_Photoreal', 'animation_set': 'NpcM', 'families': ['npc_merchant_green'], 'what': 'the merchant in green',
                             'materials': {'MI_Merchant_PR_Outfit': {'textures': {'BC': f'{UNC}/npc_merchant_blue/Merchant/T_Merchant_PR_Outfit_Green_BC.png'}}}}
# the townsmen in red and purple (pictures 341-349 Jack and the men of Terris, 391-399 the barkeep) and the gold knights (301-309, the Cast):
# the merchant's and the knight's own maps, blue turned to the 1997 colour
for name, src, colour, gain, base, slot, what in (
        ('MerchantRed', f'{UNC}/npc_merchant_blue/Merchant/T_Merchant_PR_Outfit_BC.png', (0.50, 0.07, 0.06), 3.0, 'Merchant', 'Outfit', 'the townsman in red'),
        ('MerchantPurple', f'{UNC}/npc_merchant_blue/Merchant/T_Merchant_PR_Outfit_BC.png', (0.30, 0.12, 0.42), 3.0, 'Merchant', 'Outfit', 'the townsman in purple'),
        ('KnightGold', f'{UNC}/npc_knight_blue/Knight/T_Knight_PR_BC.png', (0.62, 0.43, 0.12), 3.2, 'Knight', 'Outfit', 'the knight in gilded harness'),
        # the red knights (271-279, 711-719) are a dark maroon in 1997; the kit's own red map was magenta pink in daylight
        ('KnightRed', f'{UNC}/npc_knight_blue/Knight/T_Knight_PR_BC.png', (0.30, 0.085, 0.09), 3.0, 'Knight', 'Outfit', 'the knight in dark red harness')):
    out = NPC / name / 'Textures' / f'T_{name}_PR_Outfit_BC.png'
    recolour((NPC / src).resolve(), out, colour, is_blue, gain=gain)
    variants[name] = {'base': f'NPC/{base}', 'base_asset': f'SK_{base}_Photoreal', 'animation_set': 'NpcM', 'what': what,
                      'families': ['npc_knight_red', 'npc_knight_red_attacking'] if name == 'KnightRed' else [],
                      'materials': {f'MI_{base}_PR_{slot}': {'textures': {'BC': f'{name}/Textures/{out.name}'}}}}
    print('recoloured', out.name)


def recolour_parts(src, dst, parts, keep=0.12, size=2048):
    """recolour() for several parts of one map in one pass: parts = [(pick, target, gain)], picked on the source colours"""
    a = np.asarray(Image.open(src).convert('RGB').resize((size, size), Image.LANCZOS), np.float32) / 255.0
    lum = (a @ LUMA)[..., None]; out = a.copy()
    for pick, target, gain in parts:
        m = np.clip(pick(a), 0, 1)[..., None]
        out = out * (1 - m) + m * (a * keep + (1 - keep) * np.clip(lum * gain, 0, 1.2) * np.array(target, np.float32))
    dst.parent.mkdir(parents=True, exist_ok=True); Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(dst, optimize=True)


def is_leather(a): return (a[..., 0] - a[..., 2] - 0.06) * 10.0 * (a[..., 0] > a[..., 1] + 0.015)       # the hero's brown vest
def is_olive(a): return (np.minimum(a[..., 0], a[..., 1]) - a[..., 2] - 0.05) * 10.0 * (a[..., 1] > a[..., 0] - 0.05)   # his trousers (red and green above blue, green not far below red)
def is_shirt(a): return (a[..., 2] - a[..., 0] - 0.04) * 10.0                                          # his blue shirt


# Seth, the last enemy (s7-boss). Not a twin made by the importer: he has a mesh of his own (Tools/seth_build.py grows the
# hero's head), so only his outfit map is made here. His 1997 pictures (graphics/effects/magic/seth1w..9w and pose, which
# Milder's script s7-mil loads over 580-589) show the hero's body in a dark red tunic over slate-blue sleeves and trousers.
out = NPC / 'Seth' / 'Textures' / 'T_Seth_PR_Outfit_BC.png'
recolour_parts(CHARS / 'Dink/Textures/T_Dink_PR_Outfit_BC.png', out,
               [(is_leather, (0.46, 0.055, 0.07), 3.3), (is_olive, (0.17, 0.26, 0.40), 3.8), (is_shirt, (0.30, 0.37, 0.46), 1.25)], size=4096)
print('recoloured', out.name)
for name, bases in WALK_BASE.items():
    variants[name]['walk_bases'] = bases
(NPC / 'variants.json').write_text(json.dumps({'schema': 'dink-photoreal-npc-variants/1', 'variants': variants}, indent=1) + '\n')
print('variants', len(variants))
