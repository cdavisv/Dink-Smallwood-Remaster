"""Per-character hair styles for hair_groom.py. Lengths in metres, angles in degrees."""
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
def long_shells(k=1.0, w=1.0):
    """Long loose hair: wide dense cards on the back carry the mass, narrower ones over them, loose outer locks, a fringe."""
    return [
        dict(n=int(238 * k), layer=2, tiles=('n_dense', 'n_mid'), e0=0, e1=1.0, width=(.024 * w, .034 * w), nseg=7, seg_len=.072, across=1, lift_scale=1.0, lift_off=0.0, roll=.05, len_var=.06, taper=.2, kind='under'),
        dict(n=int(212 * k), layer=3, tiles=('n_dense', 'n_mid'), e0=0, e1=1.0, width=(.016 * w, .024 * w), nseg=7, seg_len=.072, across=1, lift_scale=1.0, lift_off=0.0, roll=.14, len_var=.10, taper=.35, kind='hair'),
        dict(n=int(60 * k), layer=3, tiles=('n_mid', 'n_thin'), e0=0, e1=.97, width=(.009 * w, .014 * w), nseg=7, seg_len=.072, across=1, lift_scale=1.0, lift_off=0.0, roll=.3, len_var=.2, taper=.6, nblend=.7, kind='over'),
        dict(n=int(110 * k), layer=3, tiles=('n_mid', 'n_thin'), e0=.58, e1=1.0, azmax=1.0, width=(.008 * w, .013 * w), nseg=5, across=1, lift_scale=1.0, lift_off=.0015, roll=.12, len_var=.2, taper=.5, kind='fringe'),
        dict(n=int(120 * k), layer=5, tiles=('n_wisp', 'n_thin'), e0=.86, e1=1.0, width=(.005 * w, .008 * w), nseg=2, across=1, lift_scale=1.0, lift_off=.0008, kind='wisp'),
    ]
STYLES = {
 # The maidens (NPC/Maiden and its colour twins; 1997 pictures 221-259): long loose yellow hair with a fringe
 'Maiden': dict(dir='NPC/Maiden', kind='long', seed=33, hairline=(.46, .12, -.5), guides=1200, density=700000, interp=4, K=24, resample=30,
                L_fringe=.062, z_end=1.21, gravity=1.1, back_pull=1.7, fan=.22, tuck=.9, hug=.010, wave=.06, wave_n=6.0, wander=.012, len_lock=.07,
                torso=dict(top=1.515, z_sh=1.44, y0=0.0, a=(.200, .070), b=(.128, .088)),
                clump=.5, clump_d=.010, noise_d=.0014, frizz_d=.0008, trim_rand=.02, tip_spread=.002,
                strand=dict(melanin=.20, redness=.30, rough=.32, radial=.4, rand_col=.10),
                albedo=(.36, .25, .085), col_var=.10, cap_tip=(.10, .22), cap_h=.5, cap_hmax=.006,
                brow=dict(th=.0040, n=600, arch=.0070, inner_up=.0012), brow_rgb='128,98,58', lash_rgb='40,28,18', brow_melanin=.35, brow_dark=.5,
                card_mat=dict(transl=.9, shadow=.2, spec=.006, spec2=10.0, ao=.45),
                tile=dict(frizz=.006, wave=.02, clump=.6, stray=.012, tip_gain=.4, n_dense=750, n_mid=300, n_thin=100, n_wisp=30, n_fly=8, strand_px=2.0),
                shells=long_shells()),
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
                albedo=(.105, .042, .017), col_var=.2, cap_h=.45, brow=dict(th=.0054, n=600), brow_dark=.85, brow_px=2.3, brow_melanin=.2, card_mat=dict(spec=.005, spec2=20.0, transl=.8), brow_rgb='70,40,26', lash_rgb='46,28,20',
                tile=dict(frizz=.008, wave=.012, clump=.5, stray=.015, tip_gain=.2, n_dense=700, n_mid=280, n_thin=90, n_wisp=30, n_fly=8, strand_px=2.0), shells=narrow_short(1.35, .62, 0, .8, fly=4), edge_narrow=.3, cap_rings=17, cap_segs=38),
 'Mother': dict(kind='bun', seed=21, hairline=(.46, .12, -.5), part_split=.06, guides=1100, density=700000, interp=4, K=16, resample=24,
                bun_dir=(0, .93, -.28), bun_r=(.040, .036, .030), bun_bundles=7, lift_tip=.005, jit=.04, wander=.008, wisps=3, wisps_nape=5, card_wisps=5, card_wisps_nape=8,   # in the game a loose strand across the temple or cheek is a thin dark line on the face: few, and mostly at the nape
               
                clump=.35, clump_d=.007, noise_d=.0012, noise_s=10.0, frizz_d=.0009, trim_rand=.01, streak_scale=45.0,
                strand=dict(melanin=.42, redness=.30, rough=.34, radial=.4, rand_col=.12, grey=.16),
                albedo=(.20, .115, .046), col_var=.08, grey=.05, cap_tip=(.92, 1.0), cap_h=.15, cap_hmax=.002, bun_strips=0, bun_ribbons=False, bun_core=1.06, bun_core_res=(48, 22), bun_coil=.085,   # ribbons wound round a coil are polygons with bright edges at any affordable segment count: the bun is the modelled core alone
                grey_col=(.33, .27, .19), brow=dict(th=.0040, n=600, arch=.0078, x0=-.016, inner_up=.0020), brow_rgb='122,102,74', lash_rgb='30,21,14', brow_melanin=.5, brow_dark=.42,
                card_mat=dict(transl=.9, shadow=.2, spec=.006, spec2=10.0, ao=.45),
                tile=dict(frizz=.004, wave=.006, clump=.3, stray=.008, smooth=.5, narrow_k=1.5, nn_dense=85, nn_mid=55, nn_thin=30, n_dense=750, n_mid=300, n_thin=100, n_wisp=30, n_fly=8, strand_px=2.0),
                shells=[
                    # Over the painted cap the cards only add loose strands and a broken outline. Dense tiles here read as
                    # overlapping planks with square ends (the "straw shingles" of 13 Nov 2026): thin and wisp tiles, narrower.
                    dict(n=300, layer=2, tiles=('n_thin', 'n_wisp'), e0=0, e1=1.0, width=(.007, .010), nseg=8, seg_len=.026, across=1, lift_scale=.8, lift_off=.0014, roll=.04, taper=.35),
                    dict(n=200, layer=3, tiles=('n_wisp', 'n_thin'), e0=0, e1=.99, width=(.006, .009), nseg=8, seg_len=.026, across=1, lift_scale=1.0, lift_off=.0022, roll=.08, taper=.35),
                    dict(n=110, layer=5, tiles=('n_wisp', 'n_thin'), e0=.9, e1=1.0, width=(.005, .008), nseg=2, across=1, lift_scale=1.0, lift_off=.0008, t_range=(0.0, .2)),
                ]),
}
