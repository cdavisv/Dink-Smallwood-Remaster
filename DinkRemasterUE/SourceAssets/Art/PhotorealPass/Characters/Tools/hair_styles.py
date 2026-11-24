"""Per-character hair styles for hair_groom.py. Lengths in metres, angles in degrees."""
import math
def short_shells(k=1.0):
    return [
        dict(n=int(430 * k), layer=1, tiles='dense', e0=0, e1=.92, width=(.026, .034), nseg=3, across=1, lift_scale=.35, lift_off=.0012, roll=.02, len_var=.2, t_range=(0.0, .8)),
        dict(n=int(420 * k), layer=2, tiles='mid', e0=0, e1=.99, width=(.018, .025), nseg=4, across=1, lift_scale=.7, lift_off=.0015, len_var=.25),
        dict(n=int(260 * k), layer=3, tiles='thin', e0=0, e1=.97, width=(.014, .021), nseg=4, across=1, lift_scale=1.0, lift_off=.002, roll=.06, len_var=.25),
        dict(n=int(120 * k), layer=5, tiles='wisp', e0=.88, e1=1.0, width=(.012, .018), nseg=2, across=1, lift_scale=1.0, lift_off=.0008, kind='wisp'),
        dict(n=int(70 * k), layer=5, tiles='fly', e0=.05, e1=.9, width=(.014, .020), nseg=3, across=1, lift_scale=1.1, lift_off=.002, kind='fly', roll=.3, nblend=.5),
    ]
CROP_TILES = ['fill'] * 3 + ['dense'] * 2 + ['mid'] * 3 + ['mid'] * 2 + ['thin'] * 3 + ['wisp'] * 2 + ['fly']
def crop_shells():
    return [
        dict(n=260, layer=1, tiles='fill', e0=0, e1=.93, width=(.030, .040), nseg=2, across=1, lift_scale=.3, lift_off=.001, roll=.02, root_ext=.014),
        dict(n=230, layer=2, tiles='fill', e0=0, e1=.96, width=(.020, .028), nseg=3, across=1, lift_scale=.65, lift_off=.0012, root_ext=.008),
        dict(n=200, layer=3, tiles='mid', e0=0, e1=.98, width=(.012, .018), nseg=3, across=1, lift_scale=.9, lift_off=.0015, roll=.05, len_var=.25),
        dict(n=140, layer=5, tiles='wisp', e0=.84, e1=1.0, width=(.008, .012), nseg=2, across=1, lift_scale=1.0, lift_off=.0006, kind='wisp'),
        dict(n=12, layer=5, tiles='fly', e0=.05, e1=.9, width=(.010, .014), nseg=3, across=1, lift_scale=1.0, lift_off=.001, kind='fly', roll=.3, nblend=.5),
    ]
def narrow_short(k=1.0, w=1.0, seg=1, ls=1.0, lv=(.15, .2), taper=.3, fly=10, wisp=150, over=0):
    """lv: how much shorter than its guide a card of the two main layers may be; taper: how much a card narrows to its
    tip; fly: stray hairs standing off the head; over: a third, sparse layer of thin locks lying over the others."""
    sh = [
        dict(n=int(470 * k), layer=2, tiles=('n_dense', 'n_mid'), e0=0, e1=1.0, width=(.007 * w, .010 * w), nseg=2 + seg, across=1, lift_scale=.8 * ls, lift_off=.0016, roll=.10, len_var=lv[0], flare=(.0, .004), taper=taper),
        dict(n=int(440 * k), layer=3, tiles=('n_mid', 'n_thin'), e0=0, e1=.99, width=(.006 * w, .009 * w), nseg=3 + seg, across=1, lift_scale=1.0 * ls, lift_off=.0022, roll=.22, len_var=lv[1], flare=(.001, .006), nblend=.75, taper=taper),
        dict(n=int(wisp * k), layer=5, tiles=('n_wisp', 'n_thin'), e0=.84, e1=1.0, width=(.005 * w, .008 * w), nseg=2, across=1, lift_scale=1.0, lift_off=.0008, kind='wisp'),
        dict(n=int(fly * k), layer=5, tiles=('n_fly',), e0=.05, e1=.9, width=(.004 * w, .006 * w), nseg=3, across=1, lift_scale=1.1, lift_off=.002, kind='fly', roll=.4, nblend=.5),
    ]
    if over:
        sh.insert(2, dict(n=int(over * k), layer=3, tiles=('n_thin', 'n_wisp'), e0=0, e1=.97, width=(.004 * w, .007 * w), nseg=3 + seg, across=1, lift_scale=1.05 * ls, lift_off=.0032, roll=.35, len_var=lv[1] + .1, flare=(.002, .008), nblend=.6, taper=min(.8, taper + .15)))
    return sh
def crest_shells(k=1.0, w=1.0):
    """Seth's crest: long standing locks need more segments than a short cut; a dense inner layer carries the mass over
    the cap, a thinner outer layer and the wisps break the outline."""
    return [
        dict(n=int(520 * k), layer=2, tiles=('n_dense', 'n_mid'), e0=0, e1=1.0, width=(.009 * w, .013 * w), nseg=7, seg_len=.014, across=1, lift_scale=.85, lift_off=.0016, roll=.10, len_var=.18, flare=(.0, .004), taper=.45),
        dict(n=int(480 * k), layer=3, tiles=('n_mid', 'n_thin'), e0=0, e1=.99, width=(.007 * w, .011 * w), nseg=7, seg_len=.014, across=1, lift_scale=1.0, lift_off=.0024, roll=.24, len_var=.24, flare=(.001, .006), nblend=.75, taper=.55),
        dict(n=int(190 * k), layer=3, tiles=('n_thin', 'n_wisp'), e0=0, e1=.97, width=(.005 * w, .008 * w), nseg=7, seg_len=.014, across=1, lift_scale=1.05, lift_off=.0034, roll=.35, len_var=.3, flare=(.002, .008), nblend=.6, taper=.7),
        dict(n=int(170 * k), layer=5, tiles=('n_wisp', 'n_thin'), e0=.84, e1=1.0, width=(.005 * w, .008 * w), nseg=2, across=1, lift_scale=1.0, lift_off=.0008, kind='wisp'),
    ]
def long_shells(k=1.0, w=1.0, over=60):
    """Long loose hair: wide dense cards on the back carry the mass, narrower ones over them, loose outer locks, a fringe."""
    return [
        dict(n=int(238 * k), layer=2, tiles=('n_dense', 'n_mid'), e0=0, e1=1.0, width=(.024 * w, .034 * w), nseg=7, seg_len=.072, across=1, lift_scale=1.0, lift_off=0.0, roll=.05, len_var=.06, taper=.2, kind='under'),
        dict(n=int(212 * k), layer=3, tiles=('n_dense', 'n_mid'), e0=0, e1=1.0, width=(.016 * w, .024 * w), nseg=7, seg_len=.072, across=1, lift_scale=1.0, lift_off=0.0, roll=.14, len_var=.10, taper=.35, kind='hair'),
        dict(n=int(over * k), layer=3, tiles=('n_mid', 'n_thin'), e0=0, e1=.97, width=(.009 * w, .014 * w), nseg=7, seg_len=.072, across=1, lift_scale=1.0, lift_off=0.0, roll=.3, len_var=.2, taper=.6, nblend=.7, kind='over'),
        dict(n=int(110 * k), layer=3, tiles=('n_mid', 'n_thin'), e0=.58, e1=1.0, azmax=1.0, width=(.008 * w, .013 * w), nseg=5, across=1, lift_scale=1.0, lift_off=.0015, roll=.12, len_var=.2, taper=.5, kind='fringe'),
        dict(n=int(120 * k), layer=5, tiles=('n_wisp', 'n_thin'), e0=.86, e1=1.0, width=(.005 * w, .008 * w), nseg=2, across=1, lift_scale=1.0, lift_off=.0008, kind='wisp'),
    ]
def mane_shells(k=1.0, w=1.0, over=14, tp=0.0):
    """Long loose hair to the waist with style key `drape` (the maidens). Three jobs, three sets of cards: (1) the MANE, wide
    cards rooted on the lower half of the head that carry the mass on the back, and full-length locks from the whole scalp over
    them, cut into segments where the path bends (adapt); (2) SHINGLES on the skull: narrow cards a hand long that run with the
    flow of the hair, narrow to a point and overlap like roof tiles, so no long plank spans the curve of the head; (3) a
    fringe and wisps at the hair line. tp is added to every taper."""
    A = dict(adapt=.0014, seg_max=.12, across=1, lift_scale=1.0, lift_off=0.0)
    return [
        dict(n=int(130 * k), layer=2, tiles=('n_dense', 'n_mid'), e0=.42, e1=1.0, azmin=.9, width=(.026 * w, .036 * w), nseg=7, roll=.05, len_var=.06, taper=min(.9, .35 + tp), root_w=.45, kind='under', **A),
        dict(n=int(150 * k), layer=3, tiles=('n_dense', 'n_mid'), e0=0, e1=1.0, width=(.015 * w, .021 * w), nseg=10, roll=.12, len_var=.10, taper=min(.92, .6 + tp), root_w=.5, kind='hair', **A),
        dict(n=int(over * k), layer=3, tiles=('n_mid', 'n_thin'), e0=0, e1=.97, width=(.009 * w, .013 * w), nseg=10, roll=.3, len_var=.2, taper=min(.95, .75 + tp), nblend=.7, kind='over', **A),
        dict(n=int(120 * k), layer=2, tiles=('n_dense', 'n_mid'), e0=0, e1=.8, width=(.016 * w, .022 * w), nseg=6, roll=.06, len_var=.15, taper=min(.92, .55 + tp), t_range=(0.0, .26), kind='under', adapt=.0009, seg_max=.05, across=1, lift_scale=1.0, lift_off=0.0),
        dict(n=int(170 * k), layer=3, tiles=('n_mid', 'n_thin'), e0=0, e1=.9, width=(.010 * w, .014 * w), nseg=6, roll=.16, len_var=.30, taper=min(.95, .75 + tp), t_range=(0.0, .30), kind='hair', adapt=.0009, seg_max=.05, across=1, lift_scale=1.0, lift_off=.0012),
        dict(n=int(40 * k), layer=3, tiles=('n_mid', 'n_thin'), e0=0, e1=.62, wfun=lambda az, e: math.exp(-((math.sin(az) * max(e, .05)) / .06) ** 2), width=(.010 * w, .014 * w), nseg=4, roll=.10, len_var=.1, taper=min(.92, .6 + tp), t_range=(0.0, .16), kind='cross', adapt=.0009, seg_max=.05, across=1, lift_scale=1.0, lift_off=.0014),      # locks rooted beside the parting and combed over it
        dict(n=int(90 * k), layer=3, tiles=('n_mid', 'n_thin'), e0=.58, e1=1.0, azmax=1.0, width=(.008 * w, .013 * w), nseg=4, across=1, lift_scale=1.0, lift_off=.0015, roll=.12, len_var=.2, taper=min(.9, .5 + tp), kind='fringe'),
        dict(n=int(80 * k), layer=5, tiles=('n_wisp', 'n_thin'), e0=.86, e1=1.0, width=(.005 * w, .008 * w), nseg=2, across=1, lift_scale=1.0, lift_off=.0008, kind='wisp'),
    ]
def bob_shells(k=1.0, w=1.0, wv=1.0, tp=0.0, rl=1.0):
    """A full bob to the jaw and nape (the Mother): short cards in many segments so the bell curves, a fringe, wisps at the hair line.
    wv: width of the cards one SEES (the under layers keep w); tp: added to every taper (a card narrows to a point instead of ending
    square); rl: gain on the roll of the seen cards about their own length (locks that do not lie in parallel bands)."""
    return [
        dict(n=int(270 * k), layer=2, tiles=('n_dense', 'n_mid'), e0=0, e1=1.0, width=(.025 * w, .033 * w), nseg=6, seg_len=.040, across=1, lift_scale=1.0, lift_off=0.0, roll=.05, len_var=.05, taper=min(.9, .2 + tp), kind='under'),
        dict(n=int(262 * k), layer=3, tiles=('n_dense', 'n_mid'), e0=0, e1=1.0, width=(.015 * w * wv, .022 * w * wv), nseg=6, seg_len=.040, across=1, lift_scale=1.0, lift_off=0.0, roll=.10 * rl, len_var=.08 + .1 * (rl - 1), taper=min(.9, .4 + tp), kind='hair'),
        dict(n=int(56 * k), layer=3, tiles=('n_mid', 'n_thin'), e0=0, e1=.97, width=(.008 * w * wv, .012 * w * wv), nseg=6, seg_len=.040, across=1, lift_scale=1.0, lift_off=0.0, roll=.2 * rl, len_var=.15, taper=min(.9, .7 + tp), nblend=.7, kind='over'),
        dict(n=int(150 * k), layer=2, tiles=('n_dense',), e0=.2, e1=1.0, azmin=2.0, width=(.022 * w, .030 * w), nseg=6, seg_len=.040, across=1, lift_scale=1.0, lift_off=0.0, roll=.04, len_var=.04, taper=min(.9, .15 + tp), kind='under'),      # the back of the head and the nape closed: between the two sides of the parting the cap's rim showed as dark specks
        dict(n=int(130 * k), layer=3, tiles=('n_mid', 'n_thin'), e0=.55, e1=1.0, azmax=1.0, width=(.008 * w * wv, .013 * w * wv), nseg=4, across=1, lift_scale=1.0, lift_off=.0015, roll=.12 * rl, len_var=.2, taper=min(.9, .5 + tp), kind='fringe'),
        dict(n=int(70 * k), layer=3, tiles=('n_mid', 'n_thin'), e0=0, e1=.62, wfun=lambda az, e: math.exp(-((math.sin(az) * max(e, .05)) / .06) ** 2), width=(.011 * w * wv, .015 * w * wv), nseg=6, seg_len=.040, across=1, lift_scale=1.0, lift_off=.0012, roll=.10 * rl, len_var=.1, taper=min(.9, .4 + tp), t_range=(0.0, .6), kind='cross'),      # locks rooted beside the parting and combed over it, so the scalp does not show as a dark jagged line
        dict(n=int(140 * k), layer=5, tiles=('n_wisp', 'n_thin'), e0=.86, e1=1.0, width=(.005 * w, .008 * w), nseg=2, across=1, lift_scale=1.0, lift_off=.0008, kind='wisp'),
    ]
STYLES = {
 # The maidens (NPC/Maiden and its colour twins; 1997 pictures 221-259): long loose yellow hair with a fringe
 'Maiden': dict(dir='NPC/Maiden', kind='long', seed=33, hairline=(.46, .12, -.5), guides=1200, density=700000, interp=4, K=40, resample=30,
                # the mass of pictures 221-259: a full head standing off the skull, as wide as the shoulders on the back and down to the waist (it was a flat cap with a narrow tail)
                L_fringe=.058, z_end=1.10, gravity=1.1, wave=.06, wave_n=6.0, len_lock=.07, over_lift=.006,
                part_back=.95, drape=dict(rel=.03, back=.30, comb=.16, width=.160, smooth=6),
                torso=dict(top=1.515, z_sh=1.44, y0=0.0, a=(.200, .070), b=(.128, .088)),
                clump=.5, clump_d=.010, noise_d=.0014, frizz_d=.0008, trim_rand=.02, tip_spread=.002,
                strand=dict(melanin=.20, redness=.30, rough=.32, radial=.4, rand_col=.10),
                albedo=(.36, .25, .085), col_var=.10, cap_tip=(.10, .22), cap_h=.5, cap_hmax=.006,
                brow=dict(th=.0040, n=600, arch=.0070, inner_up=.0012), brow_rgb='128,98,58', lash_rgb='40,28,18', brow_melanin=.35, brow_dark=.5,
                card_mat=dict(transl=.9, shadow=.2, spec=.006, spec2=10.0, ao=.45),
                # in the game (23 Nov 2026) her head was a lattice of crossed planks: key `drape` (hair_groom.py guide_drape) and mane_shells; rag_k feathers the ends of the cards
                tile=dict(frizz=.006, wave=.02, clump=.6, stray=.012, tip_gain=.4, n_dense=750, n_mid=300, n_thin=100, n_wisp=30, n_fly=8, strand_px=2.0, rag_k=2.0),
                shells=mane_shells(1.0, 1.0, over=14)),
 # Seth (NPC/Seth, the last enemy): dark brown hair standing in a tall crest from a high forehead (1997 pictures pose and seth1w-9w)
 'Seth': dict(dir='NPC/Seth', kind='crest', seed=13, hairline=(.62, .20, -.50), guides=1300, density=800000, interp=4, K=12, resample=18,
              L_side=.048, L_nape=.030, el_side=9, el_jit=4, tousle=.35, jit=.10, gravity=.25, lift_tip=.006, wander=.03,
              crest_e=(.72, .42), crest_h=.115, crest_back=-.012, crest_sweep=.040, crest_peak=.05, crest_w=.26, crest_l=.62, crest_out=.44, crest_arc=.62, lock_var=.5, crest_x=.012, crest_len=(.82, 1.0),
              clump=.75, clump_d=.012, noise_d=.0014, frizz_d=.0007, trim_rand=.014, tip_spread=.001,
              strand=dict(melanin=.84, redness=.75, rough=.30, radial=.4, rand_col=.12),
              albedo=(.030, .016, .009), col_var=.22, brow_melanin=.10, brow=dict(th=.0056, n=760, inner_up=-.0016, z0=.0180, arch=.0042), brow_dark=.9, card_mat=dict(spec=.006, transl=.7, spec2=20.0), brow_rgb='48,28,18', lash_rgb='34,22,16',
              cap_tip=(.45, .85), cap_h=.74, cap_hmax=.11, cap_rings=26, cap_segs=52,
              tile=dict(frizz=.010, wave=.035, clump=1.0, stray=.03, tip_gain=.5, n_dense=700, n_mid=280, n_thin=90, n_wisp=30, n_fly=8, strand_px=2.0, rag_k=1.7),
              shells=crest_shells()),
 # The countryman (NPC/Peasant, pictures 411-419): dark hair going grey, grown over the ears and the collar, flat on top under his straw hat
 'Peasant': dict(dir='NPC/Peasant', kind='short', seed=41, hairline=(.52, .16, -.5), guides=1100, density=750000, interp=4,
                 L_top=.032, L_side=.052, L_nape=.058, L_fringe=.040, el_top=6, el_side=8, el_jit=5, sweep=.5, tousle=.7, jit=.14, gravity=1.3, lift_tip=.002, wander=.05,
                 clump=.75, clump_d=.011, noise_d=.0013, frizz_d=.0008, trim_rand=.016, tip_spread=.001,
                 strand=dict(melanin=.80, redness=.55, rough=.36, radial=.4, rand_col=.16, grey=.16),
                 albedo=(.040, .024, .015), col_var=.25, grey=.10, grey_col=(.34, .32, .29), brow_melanin=.12, brow=dict(th=.0052, n=700, inner_up=.0004, z0=.0195), brow_dark=.85, card_mat=dict(spec=.005, transl=.7, spec2=20.0), brow_rgb='58,40,28', lash_rgb='40,26,18',
                 fringe_var=.5, fringe_scale=30, cap_tip=(.3, .72),
                 tile=dict(frizz=.014, wave=.035, clump=1.0, stray=.03, tip_gain=.5, n_dense=700, n_mid=280, n_thin=90, n_wisp=30, n_fly=8, strand_px=2.0, rag_k=1.7),
                 shells=narrow_short(.74, 1.12, lv=(.34, .42), taper=.55, fly=10, wisp=140, over=100)),      # fewer, a little wider cards: the hat hides his crown and he stands with others on a screen
 # The old man (NPC/OldMan, pictures 231-239): thin grey-white hair from a high forehead, grown over the ears, and a full grey beard to the chest
 'OldMan': dict(dir='NPC/OldMan', kind='short', seed=71, hairline=(.62, .20, -.5), guides=1000, density=600000, interp=4,
                L_top=.050, L_side=.075, L_nape=.050, L_fringe=.030, el_top=10, el_side=8, el_jit=6, sweep=.4, tousle=.8, jit=.16, gravity=1.4, lift_tip=.003, wander=.06,
                clump=.75, clump_d=.011, noise_d=.0015, frizz_d=.0010, trim_rand=.02, tip_spread=.001,
                strand=dict(melanin=.10, redness=.25, rough=.40, radial=.4, rand_col=.10),
                albedo=(.27, .265, .255), col_var=.16, brow_melanin=.10, brow=dict(th=.0056, n=620, inner_up=-.0006, z0=.0190), brow_dark=.75, card_mat=dict(spec=.006, transl=.8, spec2=14.0), brow_rgb='150,146,140', lash_rgb='70,62,56',
                fringe_var=.5, fringe_scale=30, cap_tip=(.3, .72),
                tile=dict(frizz=.016, wave=.04, clump=1.0, stray=.035, tip_gain=.5, n_dense=700, n_mid=280, n_thin=90, n_wisp=30, n_fly=8, strand_px=2.0, rag_k=1.7),
                shells=narrow_short(.72, 1.12, seg=1, lv=(.34, .42), taper=.55, fly=14, wisp=130, over=100),      # thin hair, and a budget: he stands with others on a screen (LOD0 under 35,000 triangles)
                beard=dict(n=(190, 210, 70), core=130, L=.17, L_side=.055, L_lip=.050, tip_lift=.018, gravity=1.0, wave=.10, wave_n=9.0, wander=.025, point=.5, seg_len=.036, over='NPC/OldMan/Work/oldman_packed.blend:Robe')),
 'Dink': dict(kind='short', seed=5, hairline=(.50, .14, -.52), guides=1100, density=750000, interp=4,
              L_top=.075, L_side=.05, L_nape=.036, L_fringe=.066, el_top=18, el_side=6, el_jit=6, sweep=.95, tousle=.6, jit=.12, gravity=1.2, lift_tip=.003, wander=.05,
              clump=.7, clump_d=.010, noise_d=.0012, frizz_d=.0006, trim_rand=.012, tip_spread=.001,
              strand=dict(melanin=.70, redness=.92, rough=.32, radial=.4, rand_col=.14),
              albedo=(.064, .029, .016), col_var=.25, brow_melanin=.12, brow=dict(th=.0046, n=640, inner_up=.0022, z0=.0200), brow_dark=.8, card_mat=dict(spec=.005, transl=.8, spec2=20.0), brow_rgb='86,44,24', lash_rgb='46,26,18',
              fringe_var=.5, fringe_scale=30, cap_tip=(.3, .72),   # the opaque cap stops well short of the tips: the fringe and the outline are free strands on cards
              tile=dict(frizz=.012, wave=.03, clump=1.0, stray=.03, tip_gain=.5, n_dense=700, n_mid=280, n_thin=90, n_wisp=30, n_fly=8, strand_px=2.0, rag_k=1.7),
              shells=narrow_short(1.0, 1.0, lv=(.34, .42), taper=.55, fly=44, wisp=190, over=170)),
 # Milder's cards: many, fine, close to the head (the wide lifted ones read as dark dashes on a pale scalp in the game)
 'Milder': dict(kind='short', seed=9, hairline=(.47, .16, -.5), fade=.78, edge_short=.6, guides=900, density=700000, interp=4,
                L_top=.042, L_side=.020, L_nape=.014, L_fringe=.022, el_top=30, el_side=14, sweep=-.5, tousle=.3, jit=.08, gravity=.3, lift_tip=.002, wander=.03,
                clump=.35, clump_d=.006, noise_d=.0015, frizz_d=.0008, trim_rand=.006,
                strand=dict(melanin=.58, redness=.8, rough=.3, radial=.4, rand_col=.10),
                albedo=(.105, .042, .017), col_var=.2, cap_h=.45, brow=dict(th=.0044, n=560, arch=.0064, x0=-.018, inner_up=.0010), brow_dark=.85, brow_px=2.3, brow_melanin=.2, card_mat=dict(spec=.005, spec2=20.0, transl=.8), brow_rgb='70,40,26', lash_rgb='46,28,20',   # g5 (15 Nov 2026): a thinner, arched brow, lifted a little at the nose
                tile=dict(frizz=.008, wave=.012, clump=.5, stray=.015, tip_gain=.2, n_dense=700, n_mid=280, n_thin=90, n_wisp=30, n_fly=8, strand_px=2.0), shells=narrow_short(1.35, .62, 0, .8, fly=4), edge_narrow=.3, cap_rings=17, cap_segs=38),
 # The Mother (pictures 351-359: a full golden head of hair to the jaw, a fringe, the ears covered). Until 16 Nov 2026 she wore a tight bun
 # over a painted cap, which read as a helmet with a ruled hair line in every close-up (queue row SP-07): kind 'long' cut to a bob.
 'Mother': dict(kind='long', seed=21, hairline=(.46, .12, -.5), guides=1200, density=700000, interp=4, K=22, resample=26,
                L_fringe=.048, z_end=1.545, z_back=-.02, gravity=1.0, back_pull=.3, fan=0.0, hug=.020, puff=.016, curl=.25, wave=.05, wave_n=5.0, wander=.011, len_lock=.035, lock_scale=26, part_back=.93, guide_smooth=4, over_lift=.007,
                torso=dict(top=1.515, z_sh=1.44, y0=0.0, a=(.200, .070), b=(.128, .088)),
                clump=.5, clump_d=.010, noise_d=.0016, frizz_d=.0010, trim_rand=.02, tip_spread=.002,
                strand=dict(melanin=.30, redness=.32, rough=.34, radial=.4, rand_col=.20, grey=.14),
                albedo=(.215, .132, .042), col_var=.22, grey=.05, grey_col=(.36, .30, .21), cap_tip=(.10, .22), cap_h=.5, cap_hmax=.008,
                brow=dict(th=.0042, n=360, arch=.0066, x0=-.019, inner_up=.0006, len=(.0100, .0065)), brow_px=2.2, brow_rgb='122,102,74', lash_rgb='30,21,14', brow_melanin=.42, brow_dark=.45,   # sparse single hairs, light brown: darker than her hair, with skin showing between them
                card_mat=dict(transl=.9, shadow=.2, spec=.006, spec2=10.0, ao=.45),
                # in the game (23 Nov 2026) the bob read as straw thatch: wide flat strips with square ends in parallel bands. Feathered tips (rag_k), cards that
                # narrow to a point (tp), narrower seen cards (wv), locks rolled out of the common plane (rl), more colour from strand to strand, a darker gold.
                tile=dict(frizz=.010, wave=.026, clump=.6, stray=.020, tip_gain=.4, n_dense=750, n_mid=300, n_thin=100, n_wisp=30, n_fly=8, strand_px=2.0, rag_k=2.4),
                shells=bob_shells(1.0, 1.0, wv=.80, tp=.30, rl=2.2)),
}
