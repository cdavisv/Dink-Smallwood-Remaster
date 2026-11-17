#!/usr/bin/env python3
"""Bind the photoreal people (SourceAssets/Art/PhotorealPass/Characters/NPC) to their 1997 pictures as class rows.

Writes one row per figure into `classes` of Content/Dink/Data/Art/creatures.json (DinkCreatureClass.h): every placement
of the figure's sprite class on every screen, and every sprite a script makes or dresses with the figure's walk pictures
(create_sprite, sp_base_walk), is shown by the figure. Presentation only: a class row adds no collision, no body and no
actor tag, so talking to, hitting and touching a person keep the 1997 boxes, and the layer is off in headless runs.
(The first version of this binding wrote origin rows into characters.json: such a figure is talked to by its drawn
body, 1.5 m in front of Dink, and the story probe's talk to the gravedigger of SCR_408 from 25 px no longer reached.)

A standing figure faces as its picture does (287 = the knight facing 7); a walking one follows its sprite.
Rows of other classes are left as they are.

    python3 -I Scripts/bind_people_classes.py [--check]
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NPC = ROOT / 'SourceAssets/Art/PhotorealPass/Characters/NPC'
TARGET = ROOT / 'Content/Dink/Data/Art/creatures.json'
DINK_INI = ROOT.parent / 'bin/dink/dink.ini'
# Motion-capture locomotion of the shared mannequin skeleton (animation_natural.json): played in place, speed is the
# ground speed the clip was captured at for a figure of full height; a smaller figure takes shorter steps.
IDLE = '/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle.MM_Idle'
GAITS = (('/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd.MF_Unarmed_Walk_Fwd', 273.0, 2),
         ('/Game/Characters/Mannequins/Anims/Unarmed/Jog/MF_Unarmed_Jog_Fwd.MF_Unarmed_Jog_Fwd', 600.0, 3))
# class id (tools/data/sprite_classes.csv where the class is placed on the map; a free name where only scripts make it),
# figure, 1997 walk base, what the picture is
PEOPLE = (
    ('npc_maiden_red', 'MaidenRed', 220, 'people/maiden/red: the young woman in the red dress'),
    ('npc_old_man', 'OldMan', 230, 'people/oldman: the stooped figure in the brown robe (Ethel of SCR_002 is drawn with it)'),
    ('npc_maiden_brown', 'MaidenBrown', 240, 'people/maiden/brown'),
    ('npc_maiden_blue', 'MaidenBlue', 250, 'people/maiden/blue'),
    ('npc_knight_red', 'KnightRed', 270, 'people/knight/red: dark red harness'),
    ('npc_knight_blue', 'Knight', 280, 'people/knight/blue: the guards of the castle'),
    ('npc_knight_silver', 'KnightSilver', 290, 'people/knight/silver (the gravedigger of SCR_408 is drawn with it)'),
    ('npc_knight_gold', 'KnightGold', 300, 'people/knight/gold: the Cast; made by scripts only'),
    ('npc_girl', 'Girl', 330, 'people/girl'),
    ('npc_merchant_red', 'MerchantRed', 340, 'people/merchant: Jack and the men of Terris; made by scripts only'),
    ('npc_matron_green', 'MatronGreen', 360, 'people/mom/brown: the stout woman in green; made by scripts only'),
    ('npc_merchant_blue', 'Merchant', 370, 'people/merchant/blue'),
    ('npc_merchant_green', 'MerchantGreen', 380, 'people/merchant/green'),
    ('npc_merchant_purple', 'MerchantPurple', 390, 'people/merchant/purple: the barkeep; made by scripts only'),
    ('npc_soldier', 'Soldier', 400, 'people/soldier'),
    ('npc_peasant', 'Peasant', 410, 'people/peasant2: straw hat and pole'),
    ('npc_gnome_purple', 'Gnome', 560, 'people/gnome: the wizard Martridge'),
    # dink.ini loads the green gnome at 581-589, but nothing shows it: Milder's script s7-mil loads Seth's own pictures over
    # them (effects/magic/seth1w, 3w, 7w, 9w and `pose` as 580) before s7-boss gives him walk base 580.
    ('seth', 'Seth', 580, 'effects/magic/seth1w-9w and pose (loaded over 580-589 by s7-mil): Seth, the last enemy (s7-boss, made in Milder\'s scene on SCR_086)'),
)
# Milder's scene makes Seth with picture 580 frame 1 (s7-mil.c:97, create_sprite(320, 150, 0, 580, 1): his standing picture
# `pose`) and gives him his script and walk base only after his speech; with 580 in the row he stands there from the moment the
# explosion leaves him.
EXTRA_PICTURES = {'seth': [580]}
# A standing picture with a pose of its own: (role name, picture, idle clip). Seth stands with his arms crossed (580, the
# picture `pose`) from the moment Milder's scene makes him until s7-boss sends him walking (581-589).
POSE_ROLES = {'seth': ('pose', 580, '/Game/Dink/Hero/Animations/Pass1/AN_Seth_Pose.AN_Seth_Pose')}
# Pictures outside a walk set. (class id, figure, sequences, yaw added to the picture's facing, note)
STILL = (
    # the red knight frozen in his swing (two placements, SCR_241/242): the figure stands; there is no swing clip
    ('npc_knight_red_attacking', 'KnightRed', [712, 714, 716, 718], 0.0, 'people/knight/red/attack 712-718: shown standing, no swing clip'),
    # King Daniel is picture 421 frame 31. Sequence 421 is the sheet of the food pictures too, and scripts make food
    # sprites with it; a role on 421 would turn a dropped ham into a king. The row therefore names a sequence number no
    # picture has (dink.ini ends at 843): it binds by class id only, and a class figure whose picture has no role stands in
    # the row's first role. 421 reads as "facing 1" (south-west); he faces the hall (south), 45 degrees less.
    ('king_on_throne', 'King', [9421], -45.0, 'misc 421 frame 31: the King seated, one piece with his throne; bound by class id (9421 is no picture)'),
)


def figures():
    """figure name -> (animation set, placement scale)"""
    out = {}
    for mf in sorted(NPC.glob('*/manifest.json')):
        m = json.loads(mf.read_text())
        out[mf.parent.name] = (m['animation_set'], m['placement_scale'])
    for name, row in json.loads((NPC / 'variants.json').read_text())['variants'].items():
        scale = row.get('placement_scale')
        if scale is None:   # a twin of a ported figure stands as tall as its base
            scale = json.loads((NPC / row['base'].split('/')[-1] / 'manifest.json').read_text())['placement_scale']
        out[name] = (row['animation_set'], scale)
    return out


def loaded_sequences():
    seqs = set()
    for line in DINK_INI.read_text(errors='replace').splitlines():
        m = re.match(r'\s*load_sequence(?:_now)?\s+\S+\s+(\d+)', line, re.I)
        if m:
            seqs.add(int(m.group(1)))
    return seqs


# Figures that carry a polearm stood on the root bone (npc_port.py): their idle closes the right fist on the shaft
# (AnimationPassV1 clips_people.py Guard_Stand; the shaft stands where the clip's POLE says). Twins of the knight too.
GUARD_IDLE = '/Game/Dink/Hero/Animations/Pass1/AN_Guard_Stand.AN_Guard_Stand'
GUARDS = {'Knight', 'KnightRed', 'KnightSilver', 'KnightGold'}


def row(class_id, name, sequences, scale, yaw, note):
    path = f'/Game/Dink/Photoreal/Characters/NPC/{name}/SK_{name}_Photoreal.SK_{name}_Photoreal'
    return {'class': class_id, 'mesh': path,
            'locomotion': {'idle': GUARD_IDLE if name in GUARDS else IDLE, 'gaits': [{'clip': clip, 'speed_cm_s': round(speed * scale, 1), 'cycles': cycles} for clip, speed, cycles in GAITS]},
            # the figures face +Y (as the characters.json rows: yaw -90)
            'rotation_deg': [0, -90 + yaw, 0], 'scale': scale,
            'roles': {'walk': {'sequences': sequences, 'locomotion': True}}, 'note': note}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='exit 1 if creatures.json would change')
    a = ap.parse_args()
    known, loaded = figures(), loaded_sequences()
    rows = []
    for class_id, name, base, what in PEOPLE:
        seqs = [base + d for d in (1, 2, 3, 4, 6, 7, 8, 9) if base + d in loaded]   # base + 5 is the death picture
        seqs = sorted(seqs + EXTRA_PICTURES.get(class_id, [])) if seqs else seqs
        if name not in known or not seqs:
            print(f'{class_id}: no figure {name} or no walk pictures at {base}; row not written')
            continue
        made = row(class_id, name, seqs, known[name][1], 0.0,
                        f'{what}. Walk pictures {seqs[0]}-{seqs[-1]}: every placement of the class and every sprite a script makes or dresses '
                        f'with them (sp_base_walk {base}). The figure on the mannequin skeleton with its walk and jog; it stands as its picture faces. '
                        'No hit or death clip: 1997 has none, a kill leaves the death picture.')
        if class_id in POSE_ROLES:      # the walk role stays first: a class figure whose picture has no role stands in the row's first role
            role, picture, clip = POSE_ROLES[class_id]
            walk = made['roles']['walk']; walk['sequences'] = [q for q in walk['sequences'] if q != picture]
            made['roles'] = {'walk': walk, role: {'sequences': [picture], 'locomotion': dict(made['locomotion'], idle=clip)}}
            made['note'] += f' Picture {picture} is the role `{role}`: the same walk set with the idle {clip.rsplit(".", 1)[1]}.'
        rows.append(made)
    for class_id, name, seqs, yaw, note in STILL:
        if name in known:
            rows.append(row(class_id, name, seqs, known[name][1], yaw, note))
    text = TARGET.read_text()
    data = json.loads(text)
    before = json.dumps(data, sort_keys=True)
    mine = {r['class'] for r in rows}
    people = '/Game/Dink/Photoreal/Characters/NPC/'      # every row of a figure of this folder is this script's
    data['classes'] = [r for r in data.get('classes', []) if r.get('class') not in mine and not str(r.get('mesh', '')).startswith(people)] + rows
    print('people class rows:', len(rows), ' '.join(r['class'] for r in rows))
    if a.check:
        sys.exit(0 if before == json.dumps(data, sort_keys=True) else 1)
    TARGET.write_text(json.dumps(data, indent=2) + ('\n' if text.endswith('\n') else ''))
    print('wrote', TARGET.relative_to(ROOT))


if __name__ == '__main__':
    main()
