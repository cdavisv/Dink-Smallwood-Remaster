#!/usr/bin/env python3
"""cal_script.py <outdir> <tag> [--pre 'cmd;cmd'] [--only a,b] -> capture script for the calibration pairs.
Each shot rebuilds a Blender review camera (Vegetation/src/review_*.py) in the engine: Blender (x, y, z) m ->
Unreal (y, x, z) cm from the calibration anchor, mesh yaw 90, sun 40 degrees high from the camera's right rear."""
import sys, math
out, tag = sys.argv[1], sys.argv[2]
pre = [c.strip() for c in sys.argv[sys.argv.index('--pre') + 1].split(';') if c.strip()] if '--pre' in sys.argv else []
only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
# --var name=cmd;cmd (repeatable): one capture per variant, named <tag>_<shot>_<name>; every variant must set all it needs
variants = [(a.split('=', 1)[0], [c.strip() for c in a.split('=', 1)[1].split(';') if c.strip()]) for i, a in enumerate(sys.argv) if i > 0 and sys.argv[i - 1] == '--var'] or [('', [])]
V = '/Game/Dink/Photoreal/Vegetation/'
def fov(lens): return round(2 * math.degrees(math.atan(18.0 / lens * (2.0 / 3.0) * (16.0 / 9.0))), 2)  # 16:9 frame whose central 3:2 crop is the Blender frame
def cam(loc, tgt, lens): return 'dink.CalCam %d %d %d %d %d %d %s' % (loc[1] * 100, loc[0] * 100, loc[2] * 100, tgt[1] * 100, tgt[0] * 100, tgt[2] * 100, fov(lens))
def mesh(name, x=0.0, y=0.0, yaw=90.0, s=1.0): return f'dink.CalSpawn {V}{name}.{name} {y * 100:.0f} {x * 100:.0f} 0 {yaw:.0f} {s}'
def wall(name, x): return f'dink.CalSpawn /Game/Dink/Photoreal/WallKits/{name}.{name} 0 {x * 100:.0f} 0 90 1'
def town(name, x, y, z=0.0, yaw=0.0):
    # a module of the town-house kit at a Blender position and anticlockwise yaw (TownExteriors manifest 'fit' notes)
    return f'dink.CalSpawn /Game/Dink/Photoreal/TownExteriors/{name}.{name} {y * 100:.1f} {x * 100:.1f} {z * 100:.1f} {90 - yaw:.0f} 1'
HOUSE = ([town('SM_Town_Wall_Window_L', 0, 0), town('SM_Town_Wall_Door', 2.5, 0), town('SM_Town_Wall_Window_R', 5.0, 0), town('SM_Town_Door_Studded', 2.5 + 0.73, -0.025)]
         + [town('SM_Town_Wall_Plain', x + 2.5, 5.51, 0, 180) for x in (0, 2.5, 5.0)]
         + [town('SM_Town_Roof_Slope', 0, 0), town('SM_Town_Roof_Dormer', 2.5, 0), town('SM_Town_Roof_Slope_B', 5.0, 0)]
         + [town(n, x + 2.5, 5.51, 0, 180) for n, x in (('SM_Town_Roof_Slope_B', 0), ('SM_Town_Roof_Slope', 2.5), ('SM_Town_Roof_Slope_B', 5.0))]
         + [town('SM_Town_Wall_GableEnd', 0, 5.51, 0, -90), town('SM_Town_Roof_Verge', 0, 5.51, 0, -90), town('SM_Town_Wall_GableEnd', 7.5, 0, 0, 90), town('SM_Town_Roof_Verge', 7.5, 0, 0, 90)]
         + [town('SM_Town_Roof_RidgeCap', x, 2.755, 7.35) for x in (0, 1.5, 3.0, 4.5, 6.0)]
         + [town('SM_Town_Chimney_Stack', 7.5 + 0.12, 2.755, 0, 90), town('SM_Town_Corner_Quoin', -2.5, -1.0), town('SM_Town_Wall_Narrow', -5.0, -1.0)])
def struct(name, x, y, yaw=0.0): return f'dink.CalSpawn /Game/Dink/Photoreal/Structures/{name}.{name} {y * 100:.0f} {x * 100:.0f} 0 {90 - yaw:.0f} 1'
TREE = ((1.0, -11.0, 3.6), (0, 0, 2.6), 24)
import random
rng = random.Random(3)
grid = [mesh(f'SM_Veg_GrassPatch_Dense_0{rng.randint(1, 3)}', ix * 0.8 + rng.uniform(-.1, .1), iy * 0.8 + rng.uniform(-.1, .1), rng.uniform(0, 360), round(rng.uniform(0.9, 1.15), 2))
        for ix in range(-3, 4) for iy in range(-3, 4)]
SHOTS = {  # name: (meshes, camera, grass density multiplier)
 'oak': ([mesh('SM_Veg_Oak_Large_01')], TREE, 0),
 'pine': ([mesh('SM_Veg_Pine_Large_01')], TREE, 0),
 'willow': ([mesh('SM_Veg_Willow_01')], TREE, 0),
 'bush': ([mesh('SM_Veg_Bush_Small_01', -4.0, 3.2), mesh('SM_Veg_Bush_Round_Medium_01', -2.0, 3.2), mesh('SM_Veg_Bush_Round_Large_01', 0.4, 3.4), mesh('SM_Veg_Bush_Wide_01', 3.6, 3.4)],
          ((-0.5, 0.0, 1.2), (0.6, 3.4, 0.5), 30), 0),
 'grassgrid': (grid, ((0.3, -3.6, 0.6), (0, 0, 0.12), 32), 0),
 'carpet': ([], ((0.3, -3.6, 0.6), (0, 0, 0.12), 32), 1),
 'plaster': ([wall('SM_Wall_Plaster_Straight_A', -3.9), wall('SM_Wall_Plaster_Straight_B', -1.25), wall('SM_Wall_Plaster_DoorJamb_L', 1.6), wall('SM_Wall_Plaster_CornerPost_L', 2.5)],
             ((0.8, -7.0, 1.8), (0.6, 0, 1.5), 35), 0),
 'dungeon': ([wall('SM_Wall_Dungeon_Straight_A', -4.2), wall('SM_Wall_Dungeon_Straight_B', -1.5), wall('SM_Wall_Dungeon_Curve', 1.4), wall('SM_Wall_Dungeon_Arch', 4.8)],
             ((0.8, -8.0, 1.8), (1.2, 0, 1.5), 35), 0),
 'town': (HOUSE, ((11.0, -11.0, 4.2), (3.5, 2.5, 3.2), 28), 0),
 'townclose': (HOUSE, ((4.2, -5.5, 1.7), (3.6, 0, 1.9), 28), 0),
 'townback': (HOUSE, ((-6.5, 14.0, 5.0), (3.5, 2.5, 3.2), 28), 0),
 'cottage': ([struct('SM_Cottage_Stonebrook_PR', 0, 6.0), struct('SM_Cottage_Door_PR', 14.0, 0.0), struct('SM_Well_Stone_PR', -13.0, 1.0), struct('SM_Fence_Gate_PR', -13.0, -3.0), struct('SM_Fence_GatePost_PR', -13.4, -3.0),
              struct('SM_Fence_SplitRail_4m_PR', -8.0, -4.0), struct('SM_Fence_SplitRail_4m_Broken_PR', -3.4, -4.0), struct('SM_Boulder_Field_A_PR', 3.0, -4.0), struct('SM_Boulder_Field_B_PR', 5.5, -4.0), struct('SM_Boulder_Field_C_PR', 7.5, -4.0)],
             ((6.0, -19.0, 5.0), (0, 3.0, 2.8), 24), 0),
 'structs': ([struct('SM_Well_Stone_PR', -3.5, 1.0), struct('SM_Fence_SplitRail_4m_PR', 0.5, 0.0), struct('SM_Fence_SplitRail_4m_Broken_PR', 5.0, 0.0), struct('SM_Fence_Gate_PR', -1.9, 3.0), struct('SM_Boulder_Field_A_PR', 1.5, 3.0),
              struct('SM_Boulder_Field_B_PR', 4.0, 3.0), struct('SM_Boulder_Field_C_PR', 6.0, 3.0)], ((1.5, -7.5, 2.4), (1.2, 1.0, 0.9), 28), 0),
 'carpetgame': ([], ((0, -6.0, 2.9), (0, 0.3, 0.2), 28), 1),
}
L = ['wait 22', 'dink.Goto 471 215 125', 'dink.View 10 5', 'wait 40', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 't.MaxFPS 0', 'r.VSync 0', 'dink.Goto 299 300 200', 'wait 3', 'dink.Player',
     'dink.EnvPost sunyaw -45', 'dink.EnvPost sunpitch -40', 'dink.Wind 0']
for name, (meshes, c, grass) in SHOTS.items():
    if only and name not in only: continue
    L += [f'dink.GrassDensity {grass}', 'dink.CalAnchor 0 0'] + meshes + [cam(*c), 'wait 2'] + pre
    for vname, cmds in variants:
        L += cmds + ['wait 6', f"shot {out}/{tag}_{name}{'_' + vname if vname else ''}.png", 'wait 1']
L += ['quit']
print('\n'.join(L))
