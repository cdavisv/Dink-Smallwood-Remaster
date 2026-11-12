#!/usr/bin/env python3
"""make_script.py <outdir> [--pre 'cmd;cmd'] -> prints a capture script with the fixed review cameras."""
import sys
out=sys.argv[1]; pre=[]
if '--pre' in sys.argv: pre=[c.strip() for c in sys.argv[sys.argv.index('--pre')+1].split(';') if c.strip()]
only=None
if '--only' in sys.argv: only=sys.argv[sys.argv.index('--only')+1].split(',')
CAMS=[  # name, screen, mapx, mapy, yaw, pitch
 ('01_interior_1',1,314,161,180,-4),
 ('02_interior_1_fire',1,330,250,-60,-6),
 ('03_yard_439_cottage',439,300,385,-90,-2),
 ('04_yard_439_fields',439,300,385,25,-8),
 ('05_yard_439_south',439,300,385,100,-10),
 ('06_pond_471',471,215,125,10,-14),
 ('07_pond_438',438,300,290,5,-16),
 ('08_pigpen_407',407,300,330,-90,-8),
 ('09_forest_238',238,300,300,-80,-6),
 ('10_beach_383',383,150,215,-70,-10),
 ('11_darklands_28',28,300,200,-45,-8),
 ('12_snow_47',47,300,200,-45,-8),
]
EXTRA=[  # ingame review cameras: name, screen, mapx, mapy, yaw, pitch, boom cm
 ('13_hero_front_2m',439,300,385,0,-4,200),
 ('14_hero_back_gameplay',439,300,385,180,-10,400),
 ('15_pines_183',183,300,330,-90,-3,400),
 ('16_willow_574',574,330,240,-150,-3,400),
 ('17_beach_pebbles_761',761,190,395,-90,-24,250),
 ('18_meadow_low_604',604,300,340,-110,-2,180),
 ('19_stumps_184',184,455,270,-90,-14,300),
 ('20_dungeon_579',579,300,240,-90,-6,400),
 ('21_dungeon_260',260,300,220,-45,-6,400),
 ('22_lava_85',85,300,200,-90,-10,400),
 ('23_interior_2',2,300,220,-90,-8,400),
 ('24_interior_34',34,300,220,180,-8,400),
 ('25_oaks_664',664,300,280,-80,-3,400),
 ('26_deadtrees_darklands',160,280,330,-80,-3,400),
 ('27_frosted_trees',123,300,300,-100,-3,400),
 ('28_bushes',178,300,390,-90,-6,400),
 ('30_yard_439_cottage_west',439,120,330,-60,-4,400),
 ('31_yard_439_cottage_door',439,430,300,-90,-6,400),
 ('32_yard_439_cottage_east',439,520,360,-125,-4,400),
]
if '--extra' in sys.argv: CAMS=[c+(400,) for c in CAMS]+EXTRA
else: CAMS=[c+(400,) for c in CAMS]
warm=sys.argv[sys.argv.index('--warm')+1] if '--warm' in sys.argv else '2'
L=['wait 22','dink.Goto 471 215 125','dink.View 10 5',f'wait {warm}','dink.Skip','wait 1','dink.Skip','wait 1','dink.Skip','wait 1','t.MaxFPS 0','r.VSync 0']+pre
for name,s,x,y,yaw,pitch,boom in CAMS:
    if only and not any(o in name for o in only): continue
    L+=[f'dink.Goto {s} {x} {y}',f'dink.CameraDistance {boom}',f'FOV {0 if boom>=400 else (40 if boom>=250 else 30)}','wait 1',f'dink.View {yaw} {pitch}','wait 7','dink.Player','wait 2',f'fps {name}',f'shot {out}/{name}.png','wait 1']
L+=['quit']
print('\n'.join(L))
