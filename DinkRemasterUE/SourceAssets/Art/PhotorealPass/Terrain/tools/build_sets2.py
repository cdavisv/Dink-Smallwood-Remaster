"""More recipes (registered into build_sets.R)."""
import sys
import numpy as np
from tl import *
bs = sys.modules.get('__main__')
R, PAL, recipe = bs.R, bs.PAL, bs.recipe


def one(aid, size):
    s = load(aid, size)
    s['used'] = [(aid, s['source'], 1)]
    return s


@recipe
def CaveRock():
    a = one('rock_face_04', 2.0)
    grade(a, (96, 90, 76), hue=0.7, mean_luma=74, sat=0.75, contrast=1.05)
    return write_set('CaveRock', a, 2.0, ['cave_wall', 'rock_mass', 'cliff_face'], seed=10, rough_gain=0.9,
                     note='Poly Haven rock_face_04 (dark water-worn rock with mineral crusts), cooled and darkened; slightly lower roughness for a damp cave',
                     weaknesses='single scan; the pale mineral crust patches are repeating landmarks on long walls')


@recipe
def CaveFloor():
    T = 3.0
    a = rep(load('rock_ground', 1.5), 2)
    b = match_colour(fit(load('rock_face_04', 2.0), T, (0.2, 0.3)), a, 0.7)
    s = hblend(a, b, cover(fbm(111, 0.4, 0.04, 1.3), 0.28, 0.3) * window(), 0.8)
    drift = fbm(112, 1.0, 0.2, 1.6)
    s['bc'] = s['bc'] * (1 + 0.10 * drift[..., None])
    grade(s, PAL['cave_floor'], hue=0.5, mean_luma=70, sat=0.8)
    return write_set('CaveFloor', s, T, ['cave_floor'], seed=11,
                     note='Poly Haven rock_ground (2x2: grit, rubble and trodden dirt) with patches of bare rock from rock_face_04 showing through',
                     weaknesses='the grit layer repeats at 1.5 m; bedrock patches are few')


@recipe
def CobbleStreet():
    a = one('cobblestone_05', 2.4)
    grade(a, (118, 110, 98), hue=0.5, mean_luma=98, sat=0.85)
    return write_set('CobbleStreet', a, 2.4, ['path', 'stone_floor', 'structure_facade'], seed=12,
                     note='Poly Haven cobblestone_05 (worn setts with sandy joints and a little moss)',
                     weaknesses='single scan; setts are coursed, so the course direction must follow the street')


@recipe
def DungeonFlagstone():
    a = one('rock_tile_floor', 1.96)
    grade(a, (84, 84, 78), hue=0.8, mean_luma=74, sat=0.55, contrast=1.05)
    return write_set('DungeonFlagstone', a, 1.96, ['stone_floor'], seed=13, rough_gain=0.92,
                     note='Poly Haven rock_tile_floor (random-coursed tooled stone flags with weathered joints), darkened and desaturated to the original dungeon floor grey',
                     weaknesses='single scan; a little moss green survives in some joints (plausible in a cellar, not in a dry hall)')


@recipe
def DungeonMasonry():
    a = one('medieval_blocks_03', 2.0)
    # this scan's packed AO/roughness file is flat (like its displacement): rebuild both from the integrated height and the albedo
    cav = gblur(a['h'], 10) - a['h']
    a['ao'] = np.clip(1.0 - np.clip(cav / 0.004, 0, 1) * 0.65 - np.clip((gblur(a['h'], 2.5) - a['h']) / 0.0015, 0, 1) * 0.2, 0.15, 1)
    l = luma(a['bc']); ln = np.clip((l - np.quantile(l[::8, ::8], 0.05)) / (np.quantile(l[::8, ::8], 0.95) - np.quantile(l[::8, ::8], 0.05) + 1e-6), 0, 1)
    a['rough'] = np.clip(0.90 - 0.14 * ln + 0.06 * np.clip(cav / 0.004, 0, 1), 0, 1)
    grade(a, (92, 88, 78), hue=0.75, mean_luma=80, sat=0.7, contrast=1.05)
    return write_set('DungeonMasonry', a, 2.0, ['structure_facade', 'cave_wall'], seed=14,
                     note='Poly Haven medieval_blocks_03 (large coursed ashlar with lichen-pitted faces), greyed for dungeon walls',
                     weaknesses='single scan, five courses per tile: course heights repeat every 2 m; the scan shipped blank displacement and AO/roughness files, so H is integrated from the normal map and AO/roughness are derived here')


@recipe
def PlasterWall():
    T = 2.0
    a = one('painted_plaster_wall', 2.0)
    b = match_colour(rep(load('white_plaster_rough_01', 1.0), 2, (0.13, 0.29)), a, 0.94)
    s = hblend(a, b, cover(fbm(151, 0.5, 0.03, 1.2), 0.22, 0.9), 0.5, 0.8)
    # limewash brush/trowel drift: faint directional value streaks
    st = fbm(152, 0.5, 0.02, 1.0, aniso=(1.0, 0.18))
    s['bc'] = s['bc'] * (1 + 0.035 * st[..., None])
    s['rough'] = s['rough'] + 0.04 * st
    grade(s, (222, 210, 186), hue=0.8, mean_luma=198, sat=0.9, contrast=1.0)
    info = write_set('PlasterWall', s, T, ['structure_facade', 'wood_floor'], seed=15, status='interim',
                     note='Poly Haven painted_plaster_wall (trowelled plaster with hairline cracks and scuffs) with stained, rougher patches from white_plaster_rough_01 and faint limewash brush streaks; warm off-white',
                     weaknesses='reads as plain trowelled plaster: trowel marks and cracks are only the faint ones of the scan; damp staining at the base and soot at the top do not tile, so they are a separate mask (WallGrime) the wall material applies by wall height, and that mask was not render-reviewed')
    # non-tiling wall-height mask: U tiles, V = 0 floor .. 1 ceiling. R damp rising from the base, G soot settling under the ceiling, B drip streaks
    n = 512
    v = (1 - (np.arange(n) + 0.5) / n)[:, None]
    wick = fbm(153, 0.5, 0.03, 1.2, n)[0:1, :] * 0.06 + fbm(154, 0.2, 0.02, 1.0, n) * 0.035
    damp = smooth(0.34, 0.02, v + wick) * (0.75 + 0.25 * np.clip(fbm(155, 0.3, 0.03, 1.2, n) * 0.5 + 0.5, 0, 1))
    soot = smooth(0.62, 1.0, v + fbm(156, 0.4, 0.05, 1.3, n) * 0.07) ** 1.5
    drip = np.clip(fbm(157, 0.6, 0.01, 0.8, n, aniso=(1.0, 0.04)) * 0.5, 0, 1) * smooth(0.2, 0.9, v)
    g = np.stack([damp, soot, drip], -1)
    Image.fromarray(np.clip(g * 255 + 0.5, 0, 255).astype(np.uint8), 'RGB').save(os.path.join(TERRAIN, 'PlasterWall', 'T_Terrain_PlasterWall_WallGrime.png'))
    info['files']['WallGrime'] = 'PlasterWall/T_Terrain_PlasterWall_WallGrime.png'
    info['wall_grime_mask'] = 'non-tiling in V (0 floor, 1 ceiling), tiles in U; R damp at the base (darken x0.7, tint green-brown, roughness -0.15), G soot under the ceiling (multiply toward 0.25 grey), B drip streaks'
    json.dump(info, open(os.path.join(TERRAIN, 'PlasterWall', 'set.json'), 'w'), indent=1)
    return info


@recipe
def PlankFloor():
    a = one('old_wood_floor', 3.0)
    grade(a, PAL['wood_floor'], hue=0.6, mean_luma=84, sat=0.9, contrast=1.05)
    return write_set('PlankFloor', a, 3.0, ['wood_floor'], seed=16, rough_gain=0.9,
                     note='Poly Haven old_wood_floor (worn, gapped softwood boards with nail heads and traffic wear), warmed to the original floor brown',
                     weaknesses='boards are narrow (about 12 cm) and run across the full tile width: butt joints are rare; single scan')


@recipe
def Snow():
    a = one('snow_02', 2.0)
    l = luma(a['bc'])
    lb = gblur(l, 40)
    lift = smooth(0.0, 0.10, lb * 0.97 - l)          # the scan's dark dirt squiggles are repeating landmarks: fill them
    a['bc'] = a['bc'] * (1 - lift[..., None]) + gblur(a['bc'], 40) * lift[..., None]
    # the scan's animal tracks and drag marks are repeating landmarks too: soft-clip the mid-scale relief and rebuild the normal
    hl = gblur(a['h'], 160)
    det = a['h'] - hl
    fine = det - gblur(det, 6)                  # crust grain, kept whole
    mid = det - fine                            # track-scale relief, soft-clipped hard
    sg = float(mid.std()) * 0.45
    a['h'] = hl * 0.5 + sg * np.tanh(mid / sg) + fine
    a['n'] = normal_from_height(a['h'], 2.0 / N)
    a['ao'] = np.clip(a['ao'] + lift * 0.3, 0, 1) ** 0.6
    drift = fbm(171, 1.0, 0.2, 1.6)
    a['bc'] = a['bc'] * (1 + 0.025 * drift[..., None])
    grade(a, PAL['snow'], hue=0.8, mean_luma=226, sat=0.8, contrast=0.8)
    return write_set('Snow', a, 2.0, ['snow', 'ice'], seed=17, status='interim',
                     note='Poly Haven snow_02 (settled snow with wind crust); dirt marks filled, track-scale relief soft-clipped and the normal rebuilt from the height; cool white',
                     weaknesses='the scan carries animal tracks that repeat as landmarks at 4x4; they are soft-clipped here but not gone; albedo is capped at 240 so sparkle and subsurface must come from the Unreal material')


@recipe
def SnowTrampled():
    a = one('snow_01', 2.0)
    grade(a, PAL['snow'], hue=0.8, mean_luma=212, sat=0.8, contrast=0.9)
    return write_set('SnowTrampled', a, 2.0, ['snow', 'path'], seed=18,
                     note='Poly Haven snow_01 (boot-trodden snow with clear tread prints)',
                     weaknesses='footprints have a direction (along V) and modern boot treads visible under 1 m; prints repeat every 2 m')


@recipe
def ScorchedSoil():
    T = 2.0
    a = one('mud_cracked_dry_riverbed_002', 2.0)
    b = match_colour(rep(load('burned_ground_01', 1.0), 2, (0.21, 0.37)), a, 0.72)
    s = hblend(a, b, cover(fbm(191, 0.3, 0.03, 1.1), 0.36, 0.5), 0.9, 0.45)
    grade(s, (78, 74, 70), hue=0.85, mean_luma=64, sat=0.55, contrast=1.1)
    ash = cover(fbm(192, 0.4, 0.02, 1.2), 0.3, 0.6) * smooth(0.0, 1.0, (s['h'] - s['h'].mean()) / (s['h'].std() + 1e-9) * -1 + 0.3)
    grey = np.float32(0.16)
    s['bc'] = s['bc'] * (1 - 0.5 * ash[..., None]) + grey * 0.5 * ash[..., None]
    s['rough'] = s['rough'] + 0.05 * ash
    return write_set('ScorchedSoil', s, T, ['wasteland'], seed=19,
                     note='Poly Haven mud_cracked_dry_riverbed_002 (cracked crust) height-blended with burned_ground_01 (2x2: charred turf, dead straw), desaturated to char with pale ash settled in the hollows',
                     weaknesses='the burnt-straw layer is at its 1 m period; the original wasteland tiles are grey-green rock, this is the darker scorched reading the brief asks for')


@recipe
def LavaCrust():
    T = 2.0
    a = one('mud_cracked_dry_riverbed_002', 2.0)
    b = match_colour(fit(load('rock_face_04', 2.0), 1.0, (0.1, 0.6)), a, 1.0)   # 2x enlarged detail is fine for ropy crust
    b['size_m'] = 2.0
    hn = (a['h'] - a['h'].mean()) / (a['h'].std() + 1e-9)
    crack = smooth(-0.9, -2.2, gblur(hn, 0.8))
    l = np.clip(luma(a['bc']), 1e-4, None); l = l / l.mean()
    lb = np.clip(luma(b['bc']), 1e-4, None); lb = lb / lb.mean()
    tone = (l ** 0.8) * (lb ** 0.9)
    var = fbm(201, 0.6, 0.05, 1.4)
    base = np.array([0.036, 0.033, 0.034], np.float32) * (1 + 0.25 * var[..., None]) * tone[..., None]
    region = cover(fbm(202, 0.7, 0.08, 1.5), 0.42, 0.9)
    glow = np.clip(crack * region, 0, 1) ** 1.3
    halo = gblur(glow, 5.0)
    base = base * (1 + halo[..., None] * np.array([2.2, 0.5, 0.1], np.float32))     # heat-reddened rims
    base = base * (1 - 0.6 * glow[..., None])
    s = dict(a)
    s['bc'] = base
    s['h'] = a['h'] * 1.6 + b['h'] * 0.35 - crack * 0.012
    s['n'] = normal_from_height(gblur(s['h'], 0.6), T / N) * 0.6 + (a['n'] + b['n'] * 0.6) * 0.4
    s['rough'] = np.clip(0.62 + 0.12 * var - 0.25 * smooth(0.5, 2.0, hn) + 0.2 * crack, 0.2, 1)
    s['ao'] = a['ao'] * (1 - 0.5 * crack)
    s['emis'] = glow
    s['used'] = [('mud_cracked_dry_riverbed_002', 'polyhaven', 1), ('rock_face_04', 'polyhaven', 0.5)]
    return write_set('LavaCrust', s, T, ['lava', 'wasteland'], seed=20,
                     note='built here from scan structure: the crack network and plates of mud_cracked_dry_riverbed_002 recoloured as cooled basalt crust with rock_face_04 surface detail; the E mask is the crack depth gated by a low-frequency region mask so only part of the network glows. ambientCG Lava001/002 were fetched and rejected (stylised swirls)',
                     weaknesses='plates are mud-crack polygons, flatter and more regular than real pahoehoe or aa crust; interim', status='interim',
                     extra={'emissive': 'E mask 0..1; suggested colour ramp (1.0,0.12,0.0) to (1.0,0.75,0.25), strength 20-60 nits scaled by E'})


@recipe
def PondMud():
    T = 2.6
    a = rep(load('brown_mud_03', 1.3), 2)
    b = match_colour(rep(load('brown_mud_02', 1.3), 2, (0.23, 0.41)), a, 0.8)
    s = hblend(a, b, cover(fbm(211, 0.6, 0.05, 1.4), 0.45, 0.5), 0.7)
    hn = (s['h'] - s['h'].mean()) / (s['h'].std() + 1e-9)
    wet = smooth(0.2, -1.2, hn)
    s['rough'] = s['rough'] * (1 - 0.55 * wet)
    s['bc'] = s['bc'] * (1 - 0.15 * wet[..., None])
    grade(s, (92, 76, 56), hue=0.6, mean_luma=66, sat=0.85)
    return write_set('PondMud', s, T, ['dirt', 'water', 'grass'], seed=21, rough_gain=0.85,
                     note='Poly Haven brown_mud_03 and brown_mud_02 (2x2 each, shifted) height-blended; hollows are wetter (lower roughness, darker)',
                     weaknesses='no standing-water film or reeds; the 1.3 m period of both scans can be found at 4x4')


@recipe
def RockyGrass():
    T = 2.8
    a = rep(load('Grass004', 1.4), 2, (0.5, 0.25))
    a['h'] = a['h'] * 2.5
    grade(a, PAL['grass_rocky'], hue=0.55, mean_luma=90, sat=0.9)
    a['rough'] = np.clip(a['rough'] + 0.2, 0, 1)
    b = fit(load('rocky_trail', 2.0), T, (0.4, 0.1))
    grade(b, (120, 114, 104), hue=0.6, mean_luma=104, sat=0.8)
    c = fit(load('leafy_grass', 2.0), T, (0.6, 0.7)); match_colour(c, a, 0.6)
    s = hblend(a, c, cover(fbm(221, 0.3, 0.02, 1.0), 0.28, 0.5) * window(), 1.2, 0.4)
    s = hblend(s, b, cover(fbm(222, 0.3, 0.02, 1.0), 0.26, 0.4) * window(), 1.6, 0.35)
    return write_set('RockyGrass', s, T, ['grass_rocky'], seed=22,
                     note='MeadowTurf grass (Grass004) with thin worn turf (leafy_grass) and stony ground (rocky_trail) breaking through in patches',
                     weaknesses='stones are gravel-sized; the larger rocks of the original tiles must be meshes')
