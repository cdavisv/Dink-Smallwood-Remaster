"""The people ported from PhotorealPass/Unclaimed onto the mannequin rig (npc_port.py), and the colour variants the
importer makes of them and of the Mother and Milder (Characters/NPC/variants.json).
The countryman (NPC/Peasant) is no longer ported: he is a character of his own since 23 Nov 2026 (townsfolk.py);
of the old man only the clothes still come from the port."""
NPCS = {
    'Knight': dict(src='npc_knight_blue/Knight', asset='SK_Knight_PR', set='NpcM', families=['npc_knight_blue'], pole_xy=(.30, -.10), body=dict(uv=(.193, .369), half=.027, inside=.90),
                   weak=['Plate harness of clean swept plates, rigid on one bone each, no straps or rivets, mitten gauntlets; the body under it is tubes and a lofted trunk in the harness\'s mail (npc_port.py add_body), enough to close the joints, not an anatomy.',
                         'The halberd stands upright beside him on the root bone; the idle clip Guard_Stand closes his right fist on it, a walking knight lets go of it.']),
    'Merchant': dict(src='npc_merchant_blue/Merchant', asset='SK_Merchant_PR', set='NpcM', families=['npc_merchant_blue']),
    # townsfolk: since 23 Nov 2026 only his habit, shoes and cane come from this port (townsfolk.py body='port'); npc_port.py never exports him
    'OldMan': dict(src='npc_old_man/Old_Man', asset='SK_Old_Man_PR', set='NpcM', families=['npc_old_man'], townsfolk=True,
                   weak=['The staff stands upright beside him on the root bone: his hand does not hold it.']),
    'Girl': dict(src='npc_girl/Girl', asset='SK_Girl_PR', set='NpcF', families=['npc_girl'],
                 weak=['A child carried onto the adult rig and scaled down by the placement: adult limb proportions, an adult face made small.']),
    'King': dict(src='king_on_throne/King_On_Throne', asset='SM_King_On_Throne_PR', set='NpcM', families=['king_on_throne'], static=True,
                 tex_slots={k: ('king_on_throne/King', 'King_PR') for k in ('Skin', 'Eyes', 'Hair', 'Outfit')},
                 weak=['King Daniel seated on his throne is one frozen piece on the root bone (throne, footstool and king): he does not move, breathe or turn his head.',
                       'The cloak is modelled, not draped; plain throne carving.']),
    'Gnome': dict(src='npc_gnome_purple/Gnome_Wizard', asset='SK_Gnome_Wizard_PR', set='NpcM', families=['npc_gnome_purple'],
                  weak=['A small man carried onto the adult rig and scaled down by the placement.']),
}
