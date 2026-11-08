"""Hand classification of every placed (seq, frame) (pipeline stage 2).

Produced by viewing the labelled contact sheets (scripts/sprite_sheets.py ->
out/sprites/*.png) and, where the picture alone was ambiguous, rendered screens
(scripts/render_screen.py -> out/screens/sNNN.png) and the attached DinkC
script. One entry per sequence (default for all its frames) plus per-frame
entries that override it. Lookup: label(seq, frame) -> dict.

Fields: class_id, category, name, family, treatment, view, flags, confidence, notes
"""

CATEGORIES = ['structure', 'structure_part', 'interior_wall', 'furniture', 'prop', 'flora_tree',
              'flora_bush', 'flora_grass', 'rock', 'npc', 'enemy', 'animal', 'pickup', 'container',
              'effect', 'ui', 'hazard', 'other']
TREATMENTS = ['bespoke', 'modular_kit', 'sourced', 'pcg_scatter', 'generated', 'vfx', 'not_needed']

SEQ = {}     # seq -> dict (defaults)
FRAME = {}   # (seq, frame) -> dict (overrides)


def S(seq, class_id, category, name, family='', treatment='generated', view='', flags='',
      confidence='high', notes=''):
    SEQ[seq] = dict(class_id=class_id, category=category, name=name, family=family, treatment=treatment,
                    view=view, flags=flags, confidence=confidence, notes=notes)


def F(seq, frames, class_id=None, category=None, name=None, family=None, treatment=None, view=None,
      flags=None, confidence=None, notes=None):
    if isinstance(frames, int):
        frames = [frames]
    for fr in frames:
        e = FRAME.setdefault((seq, fr), {})
        for k, v in (('class_id', class_id), ('category', category), ('name', name), ('family', family),
                     ('treatment', treatment), ('view', view), ('flags', flags),
                     ('confidence', confidence), ('notes', notes)):
            if v is not None:
                e[k] = v


# ------------------------------------------------------------------ editor / misc
S(0, 'empty_placement', 'other', 'Empty placement (seq 0)', treatment='not_needed',
  view='active placement with no graphic; screens 162 and 194', notes='editor leftover, nothing drawn')

# ------------------------------------------------------------------ animals
for s, d in ((21, 1), (23, 3), (24, 4), (26, 6), (27, 7), (29, 9)):
    S(s, 'duck', 'animal', 'Duck', family='duck', treatment='bespoke',
      view='walk facing %d; one of 8 directions of the same actor' % d,
      flags='killable (die/duckdie scripts)', notes='identity creature; brain 3 behaviour')
for s, d in ((41, 1), (43, 3), (47, 7), (49, 9)):
    S(s, 'pig', 'animal', 'Pig', family='pig', treatment='sourced',
      view='walk facing %d; one of the pig facings' % d, flags='killable',
      notes='plan: quadruped shared rig')
S(121, 'duck_head', 'other', 'Duck head (death sprite) used as set dressing', family='duck', treatment='generated',
  view='single facing', confidence='medium',
  notes='screen 145 is a black void screen with 90 duck heads arranged in a pattern (easter egg); 121.4 is a headless duck body')
F(121, 4, class_id='duck_corpse', name='Dead duck body', confidence='high', notes='corpse decal/prop')
S(127, 'duck_corpse', 'other', 'Dead duck', family='duck', treatment='generated', notes='corpse prop')
S(434, 'fish', 'animal', 'Fish (swimming)', family='fish', treatment='sourced', view='top-down swimmer',
  flags='killable (fish1 script)', notes='water screens near Joppa / south coast')
S(439, 'fish_flopping', 'animal', 'Fish flopping on land', family='fish', treatment='sourced',
  view='death/flop animation frame', notes='static decoration on beach screens')
S(441, 'fish_flopping', 'animal', 'Fish flopping on land', family='fish', treatment='sourced', view='flop frame')

# ------------------------------------------------------------------ effects
S(25, 'arrow_prop', 'prop', 'Arrow (shop display / stuck in ground)', family='arrow', treatment='generated',
  view='frame = arrow direction; 3D uses one mesh rotated',
  notes='screen 97 bow shop table display, screen 663 arrows in the ground at a target-practice camp')
S(70, 'explosion_fx', 'effect', 'Explosion', treatment='vfx', view='animation frame',
  notes='placed on screen 1 (intro house fire)')
S(161, 'fire_burst_fx', 'effect', 'Fire burst (atomic explosion frames)', treatment='vfx', view='animation frame',
  notes='screen 1 house fire scene')
S(165, 'sparkle_fx', 'effect', 'Sparkle', treatment='vfx', notes='screen 1')
S(166, 'sparkle_fx', 'effect', 'Spark', treatment='vfx', notes='screen 45')
S(427, 'fire_fx', 'effect', 'Fire (looping flames)', family='fire', treatment='vfx', view='animation frame',
  notes='burning house interior (screen 1) and burnt ruins (439)', flags='hazard look only')
S(512, 'fireball_fx', 'effect', 'Fireball (vertical)', treatment='vfx', notes='screen 366, brain 6 loop; likely a torch/brazier flame',
  confidence='medium')
S(94, 'fountain_spray_fx', 'effect', 'Fountain water spray', family='fountain', treatment='vfx',
  notes='paired with fountains 66.23/66.24 (screens 260, 586)')
S(431, 'seed_scatter', 'prop', 'Scattered seed / grain on ground', treatment='generated', view='decal',
  notes='screens 407, 439 (farm)', confidence='medium')
for s in (187, 188, 189):
    S(s, 'blood_splat', 'effect', 'Blood splatter', family='blood', treatment='vfx', view='decal frame',
      notes='placed as static gore decals (fight aftermath, s7 Darklands)')
for s in (155, 156, 157):
    S(s, 'small_fire_fx', 'effect', 'Small fire on floor', family='fire', treatment='vfx',
      notes='screen 1 house fire; burning debris')
S(154, 'burn_damage_decal', 'effect', 'Burn damage / scorch with fire', family='damage', treatment='vfx',
  notes='screen 1 house fire')
S(158, 'burn_hole_decal', 'prop', 'Burnt hole / scorch mark', family='damage', treatment='generated',
  view='floor/ground decal; frames 4-5 are larger roof holes', notes='burnt house (1, 5), ruins (439, 533, 536)')
F(158, [4, 5], class_id='burnt_floor_hole', name='Burnt hole in floor/roof (large)')

# ------------------------------------------------------------------ interior wall kits
S(31, 'int_wall_plaster', 'interior_wall', 'Plaster interior wall', family='interior_plaster_kit',
  treatment='modular_kit', view='wall segment drawn for the back (north) and front (south) faces only')
F(31, 19, class_id='int_wall_plaster_end_r', name='Plaster wall, right end trim')
F(31, 20, class_id='int_wall_plaster_end_l', name='Plaster wall, left end shading')
F(31, 21, class_id='int_wall_plaster_corner_r', name='Plaster wall with right corner post')
F(31, 22, class_id='int_wall_plaster_corner_l', name='Plaster wall with left corner post')
F(31, 23, class_id='int_wall_plaster_side', name='Plaster side wall (edge-on strip)',
  view='18 px strip: east/west wall seen edge-on, stacked vertically')
F(31, [26, 27, 28, 29, 30], class_id='int_wall_plaster', name='Plaster wall segment',
  view='100x100 segment; frames 27-30 are texture variants of 26')
F(31, [35, 36], class_id='int_wall_plaster_doorjamb', name='Plaster wall door jamb / end cap',
  view='18 px end cap beside door openings (35 left, 36 right)')

S(80, 'dungeon_wall_stone', 'interior_wall', 'Dungeon stone wall', family='dungeon_stone_kit',
  treatment='modular_kit', view='wall segment drawn for one facing only')
F(80, [1, 2, 3, 4, 12, 14, 15], class_id='dungeon_wall_stone', name='Dungeon stone wall segment',
  view='100x100 straight segment; frames are texture variants')
F(80, [5, 6], class_id='dungeon_wall_stone_side', name='Dungeon wall end / side strip', view='30 px edge-on strip')
F(80, [7, 8, 9, 10], class_id='dungeon_wall_stone_curve', name='Dungeon curved wall', view='one of 4 curve orientations')
F(80, 16, class_id='dungeon_wall_stone_arch', name='Dungeon wall with archway')
F(80, [18, 19], class_id='dungeon_wall_stone_ivy', name='Dungeon wall overgrown with ivy')
F(80, 20, class_id='dungeon_wall_stone_cracked', name='Cracked / broken dungeon wall',
  notes='V-shaped breach; likely the visual for breached walls', confidence='medium')
F(80, [21, 22], class_id='hanging_vines', category='flora_grass', name='Hanging vines', treatment='generated',
  family='dungeon_stone_kit', view='overlay on wall face')
F(80, 23, class_id='rubble_pile', category='rock', name='Rubble pile', treatment='generated')
F(80, 24, class_id='idol_statue_small', category='prop', name='Small demon idol', treatment='bespoke',
  flags='pushable (s2-idol push)', notes='push puzzle object in the dungeon')
F(80, 25, class_id='dungeon_arch_freestanding', name='Freestanding stone archway')
F(80, [27, 28], class_id='dungeon_pillar', name='Stone pillar', view='single pillar, 2 variants')
S(81, 'snake_carving', 'prop', 'Small stone snake carving', family='snake_pillar', treatment='bespoke',
  confidence='low', notes='15x13, brain 6 on screen 625; possibly an animated snake head')
S(82, 'snake_pillar', 'structure_part', 'Pillar with coiled snake', family='snake_pillar', treatment='bespoke',
  notes='screens 238, 625 (Darklands / temple)', confidence='medium')

# ------------------------------------------------------------------ flora
S(32, 'tree', 'flora_tree', 'Tree', family='trees', treatment='pcg_scatter', view='single view; shadow baked into sprite')
F(32, 1, class_id='tree_pine_large', name='Pine tree', flags='burnable when scripted (s2-sec1, s2-sec3, s3-sec1: die -> tree fire seq 20); s2-sec2 is a talking tree that resists magic',
  notes='the scripted burnable trees are seq 32 frame 1 with a secret script; make them visibly dry in 3D')
F(32, 2, class_id='tree_oak_large', name='Broadleaf (oak) tree')
F(32, 3, class_id='tree_willow', name='Weeping (willow-like) tree')
F(32, 4, class_id='tree_willow_large', name='Large weeping tree')
F(32, 5, class_id='tree_dead_dark', name='Dead leafless tree (dark)')
F(32, 6, class_id='tree_dead_dark_tall', name='Dead leafless tree (tall)')
F(32, 7, class_id='tree_dead_frosted', name='Dead leafless tree (frosted / snow)', notes='snow region')
F(32, 8, class_id='pine_forest_edge_strip', name='Pine forest edge strip (horizontal)',
  view='strip of pines forming a forest border; replace with scattered pines along the edge')
F(32, [9, 10], class_id='pine_forest_edge_strip_vert', name='Pine forest edge strip (vertical)',
  view='tall strip forming the left/right forest border')
F(32, [11, 12, 13], class_id='tree_stump', name='Tree stump', view='3 stump variants', treatment='generated')
S(65, 'grass_tuft', 'flora_grass', 'Grass / weed tuft', family='ground_plants', treatment='pcg_scatter')
F(65, 1, class_id='grass_tall', name='Tall grass clump')
F(65, 2, class_id='weed_sprig', name='Small weed sprig')
F(65, 3, class_id='fern', name='Fern clump', category='flora_bush')
F(65, [4, 5, 6], class_id='weed_small', name='Small weed / seedling')
S(66, 'flower', 'flora_grass', 'Garden flower', family='garden', treatment='pcg_scatter')
F(66, 1, class_id='flower_bed_row', name='Planted bed / hedge row (dark)', category='flora_bush', treatment='generated',
  confidence='medium', notes='217x120 dark strip, garden bed')
F(66, [2, 3, 4, 5, 6, 7, 8], class_id='mushroom', name='Mushroom', view='variants (colour/size)')
F(66, [10, 13, 14, 15, 17, 18, 19, 21, 22], class_id='flower_small', name='Small flower', view='variants')
F(66, [23, 24], class_id='fountain_stone', category='structure', name='Stone fountain', treatment='bespoke',
  family='fountain', view='23 blue basin, 24 tan basin', notes='s3-fount / s6-fount: healing fountain (talk)')
S(179, 'bush', 'flora_bush', 'Bush', family='bushes', treatment='pcg_scatter', view='4 shape variants')
F(179, 1, class_id='bush_round_large')
F(179, 2, class_id='bush_round_medium')
F(179, 3, class_id='bush_wide')
F(179, 4, class_id='bush_small')
S(91, 'fallen_log', 'prop', 'Forest floor debris', family='forest_floor', treatment='pcg_scatter')
F(91, [1, 5], class_id='twig', name='Fallen twig')
F(91, [2, 3], class_id='fallen_log', name='Fallen log')
F(91, 4, class_id='fallen_branch_forked', name='Fallen forked branch')
S(90, 'grave_detail', 'prop', 'Graveyard / wasteland detail', family='graveyard', treatment='generated')
F(90, [1, 2, 3, 4], class_id='bones', name='Scattered bones', treatment='pcg_scatter')
F(90, [5, 6], class_id='skull', name='Skull', treatment='pcg_scatter')
F(90, [7, 8, 9, 10], class_id='thorn_bush', category='hazard', name='Thorn bramble', treatment='generated',
  flags='blocking; scripted thorn barriers (thorn.c) lock fights', notes='plan: thorn barrier for locked fights')
F(90, [11, 12, 13], class_id='thorn_branch', category='hazard', name='Thorn branch', treatment='pcg_scatter')

# ------------------------------------------------------------------ rocks
S(95, 'boulder', 'rock', 'Boulder', family='boulders', treatment='sourced', view='single view; variants')
F(95, [1, 2], class_id='boulder_grey_tall', name='Tall grey boulder',
  flags='pushable when scripted (s1-roc push)')
F(95, 3, class_id='boulder_red', name='Reddish boulder', flags='bombable/pushable when scripted (s3-rock, s4-rock)',
  notes='scripted ones need a cracked look in 3D')
F(95, [4, 5], class_id='boulder_flat', name='Flat boulder', flags='bombable when scripted (s4-sec1)')
F(95, 7, class_id='boulder_white', name='White/snowy boulder')
F(95, 8, class_id='ore_rock_blue', name='Blue crystal rock', confidence='medium', flags='scripted (s3-rock)',
  notes='screen 590; unique blue mineral rock')
F(95, 9, class_id='boulder_white_pair', name='Pair of white boulders')
F(95, 10, class_id='boulder_large', name='Large dark boulder', flags='pushable when scripted (s1-roc, s3-rock)')
S(97, 'pebbles', 'rock', 'Pebble scatter', family='pebbles', treatment='pcg_scatter', view='ground scatter variants')
F(97, [17, 18], class_id='rock_mound_small', name='Small conical rock mound', treatment='generated',
  confidence='medium', notes='one each on screen 671')
S(89, 'ground_crack', 'prop', 'Crack in the ground', family='ground_holes', treatment='generated', view='ground decal')
F(89, 9, class_id='ground_hole_dark', name='Dark hole in the ground', category='hazard',
  flags='touch: fall / secret (s1-hole, s6-hole)', notes='hole you can drop into')
F(89, 10, class_id='cave_hole_warp', category='structure_part', name='Hole into a cave (warp)',
  treatment='bespoke', flags='warp door (prop=1 on most placements); also revealed by burnt tree',
  notes='s2-sec1 turns a burnt tree into this frame')
S(92, 'beach_debris', 'prop', 'Beach debris', family='beach', treatment='pcg_scatter')
F(92, 1, class_id='starfish', name='Starfish', flags='one placement is bombable (s5-sec1 secret)')
F(92, [2, 3], class_id='seashell_clam', name='Clam shell')
F(92, 4, class_id='seashell_conch', name='Conch shell')
F(92, [5, 6, 7, 8, 9, 10, 11], class_id='beach_pebbles', name='Shell and pebble scatter', category='rock')

# ------------------------------------------------------------------ fences / bridges / landmarks
S(93, 'fence_rail', 'structure_part', 'Wooden rail fence', family='fence_rail', treatment='modular_kit',
  view='one of 4 fence angles')
F(93, 1, class_id='fence_rail_ew', name='Rail fence (east-west, long)')
F(93, [2, 5], class_id='fence_rail_diag_ne', name='Rail fence diagonal')
F(93, [3, 6], class_id='fence_rail_diag_nw', name='Rail fence diagonal (other)')
F(93, 4, class_id='fence_rail_ns', name='Rail fence (north-south)')
S(58, 'bridge_wood', 'structure_part', 'Wooden rope bridge piece', family='bridge_wood', treatment='modular_kit',
  view='deck and rail pieces; one facing per frame')
F(58, [1, 2, 3], class_id='bridge_wood_deck', name='Wooden bridge deck', view='deck sections (N-S)')
F(58, [6, 8, 10], class_id='bridge_wood_rail_plank', name='Bridge side rail with planking')
F(58, [7, 9, 11], class_id='bridge_wood_rail_rope', name='Bridge rope rail')
S(186, 'landmark', 'structure', 'Landmark', family='landmarks', treatment='bespoke')
F(186, [1, 2], class_id='well_stone', name='Stone well with roof', flags='talk/hit (s2-well1)', view='2 colour variants')
F(186, [4, 5], class_id='bridge_stone', name='Stone arch bridge', view='4 is long, 5 short; same family',
  family='bridge_stone')
F(186, [7, 8, 9, 10], class_id='sign_post', category='prop', name='Signpost', treatment='generated',
  family='signs', flags='talk (sign text scripts)', view='7 one board, 8-10 multi-board variants')
S(159, 'monument', 'structure', 'Monument / statue', family='monuments', treatment='bespoke')
F(159, 4, class_id='dink_monument_rock', name='"Dink Smallwood" carved rock', flags='talk (s4-stat)')
F(159, [5, 6], class_id='dragon_statue', name='Dragon statue on orb', view='2 mirrored facings')
F(159, 7, class_id='teleport_shrine', name='Shrine with stained glass (teleporter)', flags='warp (s7-warp/s6-warp talk)')
F(159, 8, class_id='golden_duck_statue', name='Golden duck statue', notes='screen 536')
S(84, 'teleport_machine', 'structure', 'Teleport machine (armillary sphere)', family='monuments',
  treatment='bespoke', flags='warp (s7-warp)', notes='screens 154, 253')
S(449, 'save_machine', 'structure', 'Save machine', family='save_machine', treatment='bespoke',
  flags='save point (savebot)', notes='10 placements = the 10 original save spots; plan section 3 fast travel')

# ------------------------------------------------------------------ buildings
S(33, 'town_house_kit', 'structure_part', 'Town house kit piece', family='town_house_kit', treatment='modular_kit',
  view='stone ground-floor wall sections and shingle roof parts; upper timber storey is painted in tiles ts34/35',
  notes='used in the big towns (screens 418, 466, 498, 506, 538); town names not verified')
F(33, [1, 2, 11, 14, 15, 16, 17, 18, 19, 35, 36, 37, 40, 41, 42, 43, 44, 45, 46],
  class_id='town_wall_stone_window', name='Stone ground-floor wall (windows / plain)',
  view='wall segment drawn for one facing only; 64 px frames are corner/edge pieces')
F(33, [3, 5, 6, 21, 23, 33, 34, 38, 39], class_id='town_wall_stone_door', name='Stone ground-floor wall with door')
F(33, [7, 10, 24], class_id='town_wall_gable_end', name='Timbered gable end / tower corner', view='92x200 end piece')
F(33, [8, 25], class_id='town_roof_ridge_cap', name='Roof ridge / corner cap', view='roof piece')
F(33, [9, 26, 27], class_id='town_roof_slope', name='Shingle roof slope', view='roof piece')
F(33, [12, 29, 30], class_id='town_roof_flat', name='Shingle roof section', view='roof piece')
F(33, [13, 31, 32], class_id='town_roof_dormer', name='Roof section with dormer window', view='roof piece')
S(59, 'log_cabin', 'structure', 'Log cabin', family='log_cabin', treatment='bespoke', view='whole building, one angle')
F(59, 2, class_id='log_cabin_door', category='structure_part', name='Log cabin door', flags='door (scripted warp on some)')
F(59, 3, class_id='log_cabin_window', category='structure_part', name='Log cabin window')
S(60, 'church', 'structure', 'Stone church', family='church', treatment='bespoke', view='whole building, one angle',
  notes='screens 187-188 (Stonebrook church)')
F(60, [2, 9], class_id='church_window_small', category='structure_part', name='Church small window')
F(60, [4, 5, 6], class_id='church_stained_glass', category='structure_part', name='Stained-glass window',
  view='4 large, 5/6 narrow')
F(60, 7, class_id='church_door', category='structure_part', name='Church door')
S(61, 'door_wood_single', 'structure_part', 'Wooden door', family='doors', treatment='modular_kit',
  flags='door (talk/touch scripts, warp on many)', view='door drawn for one facing')
S(62, 'door_wood_wide', 'structure_part', 'Wide wooden door', family='doors', treatment='modular_kit',
  flags='door (touch scripts)', view='door drawn for one facing')
S(63, 'cottage_thatched', 'structure', 'Thatched stone cottage', family='cottage_thatched', treatment='bespoke',
  view='whole building; each frame is a different footprint, single view')
F(63, 1, class_id='cottage_thatched_long')
F(63, [2, 3], class_id='cottage_door', category='structure_part', name='Cottage door', treatment='modular_kit',
  view='2 = door on left-facing wall, 3 = right-facing wall', flags='door / warp')
F(63, [4, 5], class_id='cottage_thatched_two_storey', name='Two-storey thatched cottage', view='4/5 mirrored')
F(63, 6, class_id='cottage_thatched_large')
F(63, [7, 8], class_id='cottage_thatched_small', view='7/8 near-mirror variants')
F(63, 10, class_id='cottage_thatched_l_shape', name='L-shaped thatched cottage')
F(63, [11, 12, 13], class_id='chimney_stone', category='structure_part', name='Stone chimney', view='short/medium/tall')
S(67, 'castle_wall', 'structure_part', 'Castle curtain wall / tower', family='castle_kit', treatment='modular_kit',
  view='wall drawn for one facing; towers round', notes='Goodheart castle and snow castle')
F(67, [1, 2, 3, 4], class_id='castle_tower_round', name='Round castle tower', view='tower with wall stubs at different angles')
F(67, 5, class_id='castle_gatehouse', name='Castle gatehouse block')
F(67, [6, 7, 9], class_id='castle_wall_diag', name='Castle curtain wall (diagonal run)')
F(67, 8, class_id='castle_wall_corner', name='Castle wall corner')
F(67, 12, class_id='castle_wall_end', name='Castle wall end (edge-on)')
S(68, 'castle_door', 'structure_part', 'Castle door', family='castle_kit', treatment='modular_kit')
F(68, 6, class_id='castle_drawbridge', name='Drawbridge with chains')
S(96, 'snow_house', 'structure', 'Snow-region timbered house', family='snow_house', treatment='bespoke',
  view='assembled from 4 pieces on screen 149', notes='screen 149 (north, snow)')
F(96, 1, class_id='snow_house_lower', category='structure_part', name='House lower walls')
F(96, 2, class_id='snow_house_timber', category='structure_part', name='House timbered upper walls')
F(96, 3, class_id='snow_house_roof', category='structure_part', name='House pyramid roof', view='roof piece')
F(96, 10, class_id='snow_house_door', category='structure_part', name='House door')
S(424, 'island_hut', 'structure', 'Koka Isle round hut', family='island_village', treatment='bespoke',
  view='whole hut; frames are footprint/door variants')
F(424, [1, 2, 3], class_id='island_hut_round', view='door facing variants')
F(424, [4, 6], class_id='island_hut_two_storey', name='Two-tier round hut')
F(424, [7, 8], class_id='island_fence_lattice', category='structure_part', name='Lashed pole fence',
  treatment='modular_kit', view='7 east-west, 8 north-south')
F(424, [13, 16, 17], class_id='island_spear_pole', category='prop', name='Spear pole', treatment='generated')
F(424, 18, class_id='island_totem_pole', category='prop', name='Pole with skull/feather totem', treatment='generated')
S(425, 'island_torch', 'prop', 'Bamboo torch / pole', family='island_village', treatment='generated',
  view='1 straight, 6 bent', confidence='medium')
S(428, 'stairs_wood', 'structure_part', 'Wooden stairs', family='stairs', treatment='modular_kit',
  view='1/3 stairs up (two facings), 2/4 stairwell down', flags='warp on scripted ones (s4-not, s1-h3-5 touch)')
F(428, 5, class_id='cellar_hatch', name='Cellar hatch / ladder')
S(429, 'siege_engine', 'structure', 'Siege engine', family='siege', treatment='bespoke')
F(429, 1, class_id='catapult', name='Catapult')
F(429, 4, class_id='ballista', name='Ballista')

# ------------------------------------------------------------------ interiors / furniture
S(64, 'interior_detail', 'furniture', 'Interior furniture', family='house_interior', treatment='generated')
F(64, 1, class_id='shelf_bottles', name='Shelf of bottles (shop wall)')
F(64, 2, class_id='counter_wood', name='Wooden shop/bar counter', flags='talk (shopkeepers behind it)')
F(64, 3, class_id='bed', name='Bed', flags='talk/hit (bed scripts; sleeping)')
F(64, 4, class_id='bookcase', name='Bookcase')
F(64, 5, class_id='fireplace_brick', name='Brick fireplace', category='structure_part')
S(86, 'hearth_fire', 'effect', 'Fireplace fire', family='house_interior', treatment='vfx')
S(87, 'table', 'furniture', 'Table / bench', family='house_interior', treatment='generated')
F(87, [1, 7], class_id='cabinet_wood', name='Wooden cabinet / dresser')
F(87, 2, class_id='bench_long', name='Long bench')
F(87, [3, 5], class_id='table_long', name='Long table')
F(87, [4, 6], class_id='bench_short', name='Bench')
F(87, 8, class_id='cabinet_narrow', name='Narrow cabinet (side view)', confidence='medium')
F(87, 9, class_id='table_round', name='Round table')
F(87, 10, class_id='support_post_timber', category='structure_part', name='Timber support post on stone footing',
  family='interior_plaster_kit', treatment='modular_kit', confidence='medium',
  notes='T-shaped post in bars and shops (screens 34, 97); not a cross')
S(458, 'shop_sign', 'prop', 'Hanging shop sign', family='signs', treatment='generated',
  view='bracket sign on wall; frame = shop emblem')
F(458, 2, name='Hanging sign (pig / meat)', confidence='medium')
F(458, 4, name='Hanging sign (red cross: healer)')
F(458, 6, name='Hanging sign (fish/gold)', confidence='medium')
F(458, 7, name='Hanging sign (animal)', confidence='medium')
F(458, 10, name='Hanging sign (blue fish)', confidence='medium')
S(459, 'shelf_empty', 'furniture', 'Wooden shelving', family='house_interior', treatment='generated',
  view='1/4 back-wall facing, 2/3 side-wall facings')
S(461, 'chair', 'furniture', 'Chair / stool', family='house_interior', treatment='generated',
  view='frame = chair facing')
F(461, [11, 12, 13, 14], class_id='stool', name='Stool')
S(462, 'poster', 'prop', 'Wall poster', family='signs', treatment='generated', flags='talk (poster, s2-want)')
F(462, 2, class_id='poster_wanted', name='"Wanted" poster')
F(462, 3, class_id='poster_hark', name='"Hark!" notice')

# ------------------------------------------------------------------ props / containers / pickups
S(173, 'barrel', 'container', 'Barrel', family='barrels', treatment='generated',
  flags='breakable; bar-* scripts drop loot on hit')
F(173, 6, class_id='barrel_broken', name='Smashed barrel', category='prop')
S(175, 'chest_small', 'container', 'Treasure chest (small)', family='chests', treatment='generated',
  flags='hit to open; ch1-* loot scripts')
S(176, 'chest_medium', 'container', 'Treasure chest', family='chests', treatment='generated', flags='hit to open (ch2-*)')
S(177, 'chest_large', 'container', 'Treasure chest (large)', family='chests', treatment='generated', flags='hit to open (ch3-*)')
S(443, 'crate', 'container', 'Wooden crate', family='crates', treatment='generated', flags='breakable (box1-e)')
S(444, 'crate_small', 'container', 'Small wooden crate', family='crates', treatment='generated', flags='breakable (box2-e)')
S(445, 'crate_stack', 'prop', 'Stack of crates', family='crates', treatment='generated', view='stack size variants')
S(446, 'gravestone', 'prop', 'Engraved gravestone', family='graveyard', treatment='generated',
  view='3 tilt variants', confidence='medium', notes='source folder items/tomb')
S(447, 'farm_tool', 'prop', 'Farm / smithy tool', family='tools', treatment='generated')
F(447, [1, 11], class_id='pitchfork', name='Pitchfork (leaning)')
F(447, [3, 13], class_id='rake', name='Rake (leaning)')
F(447, 4, class_id='spinning_wheel', name='Spinning wheel', category='furniture')
F(447, [5, 6, 7, 8, 10, 14, 15, 16], class_id='hand_tool_small', name='Small hand tool (hammer, axe, tongs)',
  confidence='medium')
F(447, 12, class_id='scythe', name='Scythe / hook', confidence='medium')
S(448, 'pottery', 'prop', 'Pot / jar / cup', family='pottery', treatment='generated', view='variants')
F(448, [1, 2, 3], class_id='bowl', name='Bowl')
F(448, [4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18], class_id='jar_vase', name='Jar / vase / bottle')
S(463, 'grain_sack', 'prop', 'Grain sack', family='sacks', treatment='generated', view='colour/slump variants')
S(422, 'paper_item', 'prop', 'Paper / basket', family='', treatment='generated')
F(422, 1, class_id='scroll_note', name='Note / paper on floor', flags='talk/touch scripted (s1-mh-f)')
F(422, 12, class_id='basket_wicker', name='Wicker basket', flags='scripted (s1-sack)', confidence='medium')
S(421, 'food', 'pickup', 'Food item', family='food', treatment='generated', view='single item',
  notes='mostly set dressing; sfood script makes some edible pickups')
F(421, [1, 2], class_id='food_drumstick', name='Meat drumstick')
F(421, 3, class_id='food_ham', name='Ham / steak')
F(421, 7, class_id='food_bread', name='Bread loaf')
F(421, 9, class_id='food_cheese', name='Cheese', confidence='medium')
F(421, 11, class_id='food_pie', name='Pie', confidence='medium')
F(421, 14, class_id='food_grapes', name='Grapes')
F(421, [18, 19, 20, 21, 22, 25], class_id='food_fruit', name='Fruit (apple / pear / etc.)', confidence='medium')
F(421, 23, class_id='tree_fruit', category='prop', name='Fruit hanging in a tree',
  notes='34 placed in the canopy of one tree on screens 442/474 (fruit tree)')
F(421, [27, 28], class_id='cabbage', category='flora_grass', name='Cabbage (garden crop)')
F(421, 31, class_id='king_on_throne', category='npc', name='King Daniel on throne (seated)',
  family='npc_king', treatment='bespoke', notes='script king; drawn in the food sequence')
S(420, 'bomb_item', 'pickup', 'Bomb', family='items', treatment='generated', notes='placed bombs (shop/ground)')
S(85, 'axe_item', 'pickup', 'Throwing axe (on ground)', family='items', treatment='generated', confidence='medium',
  notes='weapon sprite placed as background on screen 170')
S(52, 'heart_pickup', 'pickup', 'Heart (health)', family='hearts', treatment='generated', flags='pickup (heart)')
S(53, 'golden_heart', 'pickup', 'Golden heart (max life up)', family='hearts', treatment='generated', flags='pickup (gheart)')
S(54, 'small_heart', 'pickup', 'Small heart', family='hearts', treatment='generated', flags='pickup (sheart)')
S(55, 'potion_blue', 'pickup', 'Blue potion (strength/defense)', family='potions', treatment='generated', flags='pickup')
S(56, 'potion_red', 'pickup', 'Red potion (magic)', family='potions', treatment='generated', flags='pickup (rpotion)',
  view='frames 3/5/8 are shape variants')
S(57, 'potion_purple', 'pickup', 'Purple potion', family='potions', treatment='generated', flags='pickup (ppotion)')
S(75, 'potion_blue', 'pickup', 'Blue potion (alt sequence)', family='potions', treatment='generated', flags='pickup (apotion)')
S(178, 'gold', 'pickup', 'Gold', family='gold', treatment='generated', flags='pickup')
F(178, 1, class_id='gold_coin', name='Single coin')
F(178, 2, class_id='gold_coins_small', name='Few coins')
F(178, 4, class_id='gold_pile', name='Gold pile (lgold)')
S(450, 'wall_stripe_red', 'prop', 'Red wall stripe / banner (built from the health-bar UI art)', family='signs',
  treatment='generated', view='3-piece strip: frame 1 left cap, 2 middle (x5), 3 right cap', confidence='low',
  notes='type 0 background, que 116, along the top of the back wall in the bow shop (screen 97); the attached '
  's3-fount talk script cannot run on a background sprite. Reads as a red banner or trim; check in the HD engine')

# ------------------------------------------------------------------ NPCs
def npc(seq, cls, name, family, notes='', treatment='sourced', facing=''):
    S(seq, cls, 'npc', name, family=family, treatment=treatment,
      view=('walk frame, facing %s; placement only sets the start pose' % facing) if facing else
      'walk frame; placement only sets the start pose', notes=notes)


npc(221, 'npc_maiden_red', 'Woman (red dress)', 'npc_maiden', 's7-mom (Dink\'s mother look-alike)', facing='1')
npc(231, 'npc_old_man', 'Old man', 'npc_oldman', 's1-h2-o', facing='1')
npc(241, 'npc_maiden_brown', 'Woman (brown dress)', 'npc_maiden', 's1-ntree', facing='1')
npc(251, 'npc_maiden_blue', 'Woman (blue dress)', 'npc_maiden', 's1-h3-l', facing='1')
npc(273, 'npc_knight_red', 'Knight (red)', 'npc_knight', 's1-rob2 (robber)', facing='3')
npc(277, 'npc_knight_red', 'Knight (red)', 'npc_knight', facing='7')
npc(279, 'npc_knight_red', 'Knight (red)', 'npc_knight', facing='9')
npc(281, 'npc_knight_blue', 'Knight (blue)', 'npc_knight', 's6-g2 guard', facing='1')
npc(283, 'npc_knight_blue', 'Knight (blue)', 'npc_knight', 's6-g1 guard', facing='3')
npc(287, 'npc_knight_blue', 'Knight (blue)', 'npc_knight', 'unscripted guards', facing='7')
npc(289, 'npc_knight_blue', 'Knight (blue)', 'npc_knight', 'unscripted guards', facing='9')
npc(291, 'npc_knight_silver', 'Knight (silver)', 'npc_knight', 's2-ca-g castle guard', facing='1')
npc(293, 'npc_knight_silver', 'Knight (silver)', 'npc_knight', facing='3')
npc(299, 'npc_knight_silver', 'Knight (silver)', 'npc_knight', facing='9')
npc(331, 'npc_girl', 'Girl (child)', 'npc_girl', 's7-girl / s7-dgirl', facing='1')
npc(339, 'npc_girl', 'Girl (child)', 'npc_girl', facing='9')
npc(351, 'npc_mom', 'Dink\'s mother', 'npc_mom', 's1-h1-m', facing='1', treatment='bespoke')
npc(371, 'npc_merchant_blue', 'Merchant (blue)', 'npc_merchant', 's1-vic, s8-guy', facing='1')
npc(381, 'npc_merchant_green', 'Merchant (green)', 'npc_merchant', 's6-vend, s3-bowl', facing='1')
npc(403, 'npc_soldier', 'Soldier', 'npc_soldier', 's1-blove', facing='3')
npc(411, 'npc_peasant', 'Peasant', 'npc_peasant', 's1-h3-of, s2-mh-m', facing='1')
npc(561, 'npc_gnome_purple', 'Gnome / wizard (purple)', 'npc_gnome', 's1-mh-m', facing='1')
npc(712, 'npc_knight_red_attacking', 'Knight (red) attack pose', 'npc_knight', 'two placements, unscripted', facing='2')
S(436, 'dink_dead', 'npc', 'Dink lying dead (cutscene pose)', family='dink', treatment='bespoke',
  view='death frame', notes='s7-dink; ending / Darklands scene')
for s, fam, nm in ((245, 'npc_maiden', 'Dead woman'), (275, 'npc_knight', 'Dead knight'),
                   (335, 'npc_girl', 'Dead girl'), (345, 'npc_merchant', 'Dead merchant'),
                   (355, 'npc_mom', 'Dead mother (burnt house)'), (385, 'npc_merchant', 'Dead merchant (green)'),
                   (405, 'npc_soldier', 'Dead soldier'), (415, 'npc_peasant', 'Dead peasant')):
    S(s, 'corpse_' + fam.replace('npc_', ''), 'npc', nm, family=fam, treatment='sourced',
      view='death sprite (body in blood)', notes='static corpse prop; reuse NPC mesh in a death pose')

# ------------------------------------------------------------------ enemies
def foe(seq, cls, name, family, view, treatment='bespoke', notes=''):
    S(seq, cls, 'enemy', name, family=family, treatment=treatment, view=view, flags='killable',
      notes=notes or 'behaviour comes from the en-* script')


for s in (131, 133):
    foe(s, 'pillbug', 'Pillbug', 'pillbug', 'walk frame (facing %d); frames are animation steps' % (s - 130))
for s in (141, 143):
    S(s, 'pillbug_corpse', 'effect', 'Pillbug death splat', family='pillbug', treatment='vfx', view='death frame')
for s in (202, 204, 206, 208):
    foe(s, 'dragon', 'Dragon', 'dragon', 'walk frame facing %d' % (s - 200), notes='s7-drag / sc-drag')
for s in (212, 216):
    S(s, 'dragon_corpse', 'enemy', 'Dead dragon', family='dragon', treatment='bespoke', view='death frame',
      notes='static corpse')
for s in (531, 533, 537, 539, 542, 544):
    foe(s, 'bonca_brown', 'Bonca (brown)', 'bonca', 'walk/attack frame; one of 8 facings', treatment='bespoke')
for s in (592, 594, 601, 603, 607, 609):
    foe(s, 'bonca_gray', 'Bonca (grey)', 'bonca', 'walk/attack frame; one of 8 facings',
        notes='recolour of bonca; sc-lock = locked fight')
for s in (611, 613, 619, 626, 628):
    foe(s, 'bonca_purple', 'Bonca (purple)', 'bonca', 'walk/attack frame; one of 8 facings', notes='recolour (en-pbon)')
for s in (632, 634, 636, 641, 643, 647, 649):
    foe(s, 'slayer', 'Slayer', 'slayer', 'walk/attack frame; one of 8 facings', notes='en-slay; also s2-stat statue pose')
foe(651, 'slime_blue', 'Slime (blue)', 'slime', 'single blob frame', treatment='generated', notes='plan: slimes by shader')
foe(671, 'slime_green', 'Slime (green)', 'slime', 'blob frames', treatment='generated',
    notes='6 is a flattened frame; plan: slimes by shader')
foe(691, 'slime_red', 'Slime (red)', 'slime', 'blob frame', treatment='generated')
foe(693, 'slime_red', 'Slime (red)', 'slime', 'blob frame (facing 3)', treatment='generated')
for s in (761, 763, 769):
    foe(s, 'goblin_hammer', 'Goblin (hammer)', 'goblin', 'walk frame; one of 8 facings', treatment='sourced',
        notes='humanoid rig per plan')
for s in (801, 803, 809):
    foe(s, 'goblin_soldier', 'Goblin soldier', 'goblin', 'walk frame; one of 8 facings', treatment='sourced')
for s in (816, 821, 823, 827, 829):
    foe(s, 'stone_giant', 'Stone giant', 'stone_giant', 'walk/attack frame; one of 8 facings', treatment='sourced')

# ------------------------------------------------------------------ build


DEFAULT = dict(class_id='', category='', name='', family='', treatment='', view='', flags='',
               confidence='high', notes='')


def label(seq, frame):
    if seq not in SEQ and (seq, frame) not in FRAME:
        return None
    e = dict(DEFAULT)
    e.update(SEQ.get(seq, {}))
    e.update(FRAME.get((seq, frame), {}))
    if not e['name']:
        e['name'] = e['class_id'].replace('_', ' ').capitalize()
    return e
