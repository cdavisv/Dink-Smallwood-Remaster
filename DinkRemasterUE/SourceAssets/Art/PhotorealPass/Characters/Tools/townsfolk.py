"""The townsfolk that are characters of their own in the character pipeline (second pass, queue rows SP-04 / SP-09).

The first pass ported the people of PhotorealPass/Unclaimed onto the mannequin rig by their skin weights (npc_port.py):
plain base faces, modelled cap hair, mitten hands. A figure listed here no longer comes from that port. It is built the
way Seth is (seth_build.py): the hero's body, hands and clothes with a head stage, a skin set and a strand groom of its
own, the clothes turned to the colours of its 1997 pictures (townsfolk_outfit.py), the hero's pack and straps left
off, and the things the pictures give it (a hat, a staff) made and painted by townsfolk_pack.py.

    run_townsfolk.sh <Name>         every stage in order (the list is in that file)

A figure in a robe keeps the clothes of its Unclaimed source (`body='port'`, townsfolk_port_pack.py): only the head, the
hands, the hair and the beard are new. `src`: its folder and texture stem under Unclaimed/. `drop` / `gear`: boxes
(x0, x1, y0, y1, z0, z1, metres on the mannequin rig); a piece of the ported outfit that lies inside a drop box goes (a
modelled beard), one inside a gear box moves to the Gear slot (shoes, a cane). `undersleeve`: a narrow tube of the robe's
cloth from the hand up the forearm (townsfolk_port_pack.py), so no hand hangs in a wide sleeve.

`junk`: parts of Dink/Work/dink_packed.blend the figure does not wear (the bracers stay on every figure: the hero's
sleeves end above the wrist and his skin has no forearm under them). `outfit` may give a part the gain None: it then takes the
brightness of the jerkin, so shirt sleeves and jerkin read as ONE sleeved coat; `mottle` wears the cloth unevenly. `gear_red`: colour and gain for the hero's red
bracer leather. `outfit`: (jerkin, shirt, trousers) target colours
and gains for the hero's outfit map. `props`: what townsfolk_pack.py adds, each in a rectangle of the gear atlas that the
junked parts leave free (checked against the UVs of the parts that stay)."""
NO_PACK = ['Pack', 'PackFlap', 'PackStrap_l', 'PackStrap_r', 'PackBuckle_l', 'PackBuckle_r', 'ShoulderStrap_l', 'ShoulderStrap_r']
TOWNSFOLK = {
    # people/peasant2, pictures 411-419: a countryman in a brown belted coat over olive trousers and dark boots, a wide
    # flat straw hat with a dark knob, a pale cloth round his neck, a long pole in his right hand
    'Peasant': dict(
        families=['npc_peasant'], animation_set='NpcM', placement_scale=0.95, iris='96,74,48', eye_seed=11,
        junk=NO_PACK + ['BracerLace_l', 'BracerLace_r'], gear_red=((0.34, 0.185, 0.10), 2.9),
        # one coat: the hero's jerkin and the sleeves of his shirt in the same weathered brown (the sleeves take the jerkin's brightness), the leather cuffs with them
        outfit=dict(jerkin=((0.40, 0.215, 0.115), 3.1), shirt=((0.40, 0.215, 0.115), None), trousers=((0.17, 0.18, 0.085), 3.0), mottle=0.30),
        props=dict(hat=dict(rect=(0.070, 0.143, 0.395, 0.622), radius=0.255, crown_r=0.098, crown_h=0.062, drop=0.050, sink=0.052, tilt=-7.0, seed=411),
                   staff=dict(rect=(0.472, 0.640, 0.793, 0.881), xy=(-0.30, -0.10), grip_z=1.17, length=2.02, radius=0.0155, seed=413),      # xy and grip_z = POLE of AnimationPassV1 clips_people.py (Guard_Stand closes the right fist there)
                   # the pale cloth of the pictures: wound once round the neck over the coat's collar, knotted in front, two ends on the chest
                   scarf=dict(rect=(0.480, 0.705, 0.770, 0.985), ring=(0.076, 0.072), tube=0.028, z=(1.487, 1.523, 1.517), tails=(0.135, 0.105), col=(0.60, 0.585, 0.545), seed=415)),
        what='the countryman of pictures 411-419 (people/peasant2): straw hat, neck cloth and pole',
        weak=['The body, the hands and the cut of the clothes are the hero\'s: his jerkin and the sleeves of his shirt in one brown read as a sleeved coat with turned leather cuffs, but the armhole of the jerkin is still there as a shoulder seam and the coat ends at the belt line of the hero\'s jerkin.',
              'The neck cloth is a swept shape with painted folds and weave (townsfolk_pack.py), skinned by the nearest body weights: no cloth simulation, its ends do not swing.',
              'The pole stands upright on the root bone where the idle clip Guard_Stand closes his right fist (bind_people_classes.py GUARDS): a walking man lets go of it and it glides beside him.',
              'The hat and the pole are painted by townsfolk_pack.py (plaited straw, peeled wood), not baked from modelled straw.',
              'The face is sculpted with the kit\'s face operations (cfg/head.json): a weathered man of no particular likeness.']),
    # people/oldman, pictures 231-239 (Ethel of SCR_002 is drawn with it): a stooped figure in a brown hooded habit, long grey hair
    # and beard, a cane
    'OldMan': dict(
        body='port', src=('npc_old_man/Old_Man', 'Old_Man_PR'), families=['npc_old_man'], animation_set='NpcM', placement_scale=0.87, iris='118,126,132', eye_seed=23,
        drop=[(-0.11, 0.11, -0.21, 0.0, 1.38, 1.63)], gear=[(-0.25, 0.25, -0.25, 0.10, -0.01, 0.20), (-0.40, -0.28, -0.12, -0.02, -0.01, 1.35)],
        undersleeve=dict(over=0.012, length=0.085, r0=0.033, r1=0.039),      # a forearm's worth of under-sleeve inside each wide sleeve (the hero's skin ends at the wrist)
        what='the old man of pictures 231-239 (people/oldman): brown habit, grey hair and beard, a cane',
        weak=['The habit, the hood, the shoes and the cane are those of the Unclaimed source, carried onto the rig by its own skin weights: swept shapes with a painted weave, no cloth simulation.',
              'He stands upright; the 1997 figure is bent double over his cane (a pose for a clip, not built).',
              'The cane stands on the root bone beside him: his hand does not hold it.',
              'Hair and beard are cards rigid on the head bone: the beard does not swing and a deep nod carries it into the chest.',
              'The face is sculpted with the kit\'s face operations (cfg/head.json): an old man of no particular likeness.']),
}
