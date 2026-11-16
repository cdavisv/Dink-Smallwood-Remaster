"""Animation clips for the rigged monsters that had none: slayer, dragon, stone giant, knight (the bonca has clips_bonca.py).

Each source (Unclaimed/<family>/<Name>/SK_<Name>_PR.blend) has a rig and no action. This adds <Name>_Idle, _Walk, _Attack,
_Hit and _Death (30 fps, in place: the root never moves; export_monster_ue.py writes them to Export/ for Unreal) and
SM_<Name>_Corpse_PR.fbx, the LOD0 mesh frozen in the last frame of the death clip (what lies on the ground afterwards).

Poses are built in armature space, parent first, as turns about the body's own axes through each bone's head, so nothing
depends on bone rolls. All rigs face -Y, left is +X. Conventions of the helpers:
  sw(bone, deg)    swing: + carries the far end of a hanging limb FORWARD, raises a bone that points forward
  yaw(bone, deg)   + turns to the animal's left
  roll(bone, deg)  + drops the left side

What each is meant to do, from the 1997 frames:
  slayer       641-649 prowls on four limbs, the long fore blades reaching ahead, tail whipping; 632-638 rears and slashes
               both blades down; dead (645) it lies on its side
  dragon       202-208 stands upright and treads, wings beating, tail curling (it has no attack sequence: it spits fire
               while walking, so Attack is authored but not bound); dead (212/216) it lies torn open (corpse kit asset)
  stone giant  821-829 knuckle-walks on its long arms; 812-818 swings both fists overhead and slams them down; dead
               (825) it lies as a heap of its own stones
  knight       271-299 marches with the halberd; 712-718 chops overhead; dead (275) he lies on his back (corpse kit asset)

usage: tools/bl.sh clips_monsters.py <slayer|dragon|giant|knight> build [review] [export]
"""
import bpy, sys, os, math
from mathutils import Matrix, Vector

A = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
WHO = A[0] if A else 'slayer'
HERE = os.path.dirname(os.path.abspath(__file__)); UNC = os.path.dirname(HERE)
SRC = {'slayer': ('slayer', 'Slayer'), 'dragon': ('dragon', 'Dragon'), 'giant': ('stone_giant', 'Stone_Giant'), 'knight': ('npc_knight_blue', 'Knight')}[WHO]
DIR = os.path.join(UNC, *SRC); NAME = SRC[1]; BLEND = os.path.join(DIR, 'SK_%s_PR.blend' % NAME)
FPS = 30; TAU = math.tau
ARM = None
META = {}


def _turn(bone, axis, deg):
    if abs(deg) < 1e-6 or bone not in ARM.pose.bones: return
    pb = ARM.pose.bones[bone]; h = pb.matrix.to_translation()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h) @ pb.matrix
    bpy.context.view_layer.update()


def sw(bone, deg): _turn(bone, 'X', -deg)
def yaw(bone, deg): _turn(bone, 'Z', deg)
def roll(bone, deg): _turn(bone, 'Y', deg)
def move(bone, d):
    pb = ARM.pose.bones[bone]; pb.matrix = Matrix.Translation(Vector(d)) @ pb.matrix; bpy.context.view_layer.update()
def ease(t): t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)
def bump(t, a, b): return 0.0 if t <= a or t >= b else math.sin(math.pi * (t - a) / (b - a)) ** 2
def head_z(bone): return ARM.pose.bones[bone].matrix.to_translation().z
def chain(prefix, n, fn, first=1):
    for i in range(n): fn('%s_%02d' % (prefix, i + first), i)


def hind(side, swing, lift, digit=True):
    """A digitigrade hind leg (thigh forward-down, calf back-down, foot down): swing + = foot forward, lift 0..1 folds it off the ground."""
    s = '_' + side
    sw('thigh' + s, swing + 14 * lift); sw('calf' + s, -30 * lift - .3 * swing); sw('foot' + s, 22 * lift - .5 * swing)
    if digit: sw('ball' + s, -(swing + 6 * lift) * .25)


def tail(n, sway, lift, lag, ph, k0=.4, k1=.16):
    for i in range(n):
        yaw('tail_%02d' % (i + 1), sway * (k0 + k1 * i) * math.sin(ph - lag * i)); sw('tail_%02d' % (i + 1), lift * (.5 + .12 * i) * math.sin(2 * ph - lag * i * 1.3))


# ------------------------------------------------------------------------------------------------ slayer
def sl_fore(side, swing, lift):
    s = '_' + side
    sw('upperarm' + s, swing + 10 * lift); sw('lowerarm' + s, 16 * lift - .25 * swing); sw('hand' + s, 10 * lift - .3 * swing)


def sl_idle(t):
    ph = TAU * t; br = math.sin(2 * ph)
    move('pelvis', (0, 0, -.01 + .01 * math.sin(ph))); sw('spine_01', 1.5 * br); sw('spine_02', -1.0 * br)
    yaw('neck_01', 6 * math.sin(ph)); yaw('head', 8 * math.sin(ph - .7)); sw('head', 3 * math.sin(2 * ph + 1))
    sl_fore('l', 2 * math.sin(ph), 0); sl_fore('r', -2 * math.sin(ph), 0)
    tail(7, 9, 2.5, .5, ph)


def sl_walk(t, k=1.0):
    ph = TAU * t
    move('pelvis', (0, 0, -.02 + .02 * math.cos(2 * ph))); yaw('pelvis', 5 * math.sin(ph)); roll('pelvis', 3 * math.sin(ph + .5))
    yaw('spine_01', -4 * math.sin(ph)); yaw('spine_02', -5 * math.sin(ph)); yaw('neck_01', 3 * math.sin(ph)); sw('head', 2 * math.sin(2 * ph))
    for side, o in (('l', 0.0), ('r', math.pi)):
        hind(side, 22 * k * math.sin(ph + o), max(0.0, math.cos(ph + o)) ** 1.4)
        f = ph + o + math.pi                                 # the fore limb moves with the opposite hind leg
        sl_fore(side, 15 * k * math.sin(f), max(0.0, math.cos(f)) ** 1.4)
    tail(7, 12, 3, .55, ph + math.pi)


def sl_attack(t):
    up = bump(t, 0.0, .55); cut = ease((t - .38) / .2) * (1 - ease((t - .78) / .22))
    move('pelvis', (0, .06 * up - .14 * cut, .05 * up - .06 * cut))
    sw('pelvis', 14 * up - 10 * cut); sw('spine_01', 10 * up - 12 * cut); sw('spine_02', 8 * up - 12 * cut); sw('neck_01', -10 * up + 6 * cut); sw('head', -8 * up + 10 * cut)
    for s in ('l', 'r'):
        sw('upperarm_' + s, 55 * up - 40 * cut); sw('lowerarm_' + s, 30 * up - 22 * cut); sw('hand_' + s, 25 * up - 16 * cut)
        hind(s, -8 * up + 6 * cut, 0)
    yaw('upperarm_l', 8 * up); yaw('upperarm_r', -8 * up)
    chain('tail', 7, lambda b, i: (sw(b, (-4 * up + 7 * cut) * (.5 + .15 * i)), yaw(b, 8 * cut * math.sin(TAU * t * 2 - i * .7))))


def sl_hit(t):
    k = bump(t, 0.0, 1.0) * (1.25 - .5 * t)
    move('pelvis', (0, .06 * k, -.03 * k)); sw('pelvis', 5 * k); roll('pelvis', 5 * k); sw('spine_02', 6 * k); yaw('spine_02', 10 * k); yaw('neck_01', 12 * k); sw('head', 12 * k)
    sl_fore('l', -8 * k, .3 * k); sl_fore('r', 6 * k, 0); hind('l', -5 * k, 0); hind('r', 5 * k, .2 * k)
    chain('tail', 7, lambda b, i: yaw(b, -7 * k * (.5 + .2 * i)))


def sl_death(t):
    st = bump(t, 0.0, .35); fall = ease((t - .2) / .45); rest = ease((t - .6) / .4)
    hip = head_z('pelvis')
    move('pelvis', (-.25 * fall, .05 * st, -(hip - .30) * fall + .04 * st)); sw('pelvis', 8 * st); roll('pelvis', 6 * st + 82 * fall)
    sw('spine_01', 6 * st - 6 * rest); sw('spine_02', 6 * st - 8 * rest); yaw('spine_02', -6 * fall); sw('neck_01', 14 * st - 16 * rest); sw('head', 16 * st - 12 * rest); yaw('head', 10 * st)
    sl_fore('l', 30 * fall, .6 * fall); sl_fore('r', -22 * fall + 10 * st, .2 * fall); yaw('upperarm_l', 20 * fall); yaw('upperarm_r', 14 * fall)
    hind('l', 26 * fall, .8 * fall); hind('r', -14 * fall + 10 * st, .4 * fall)
    chain('tail', 7, lambda b, i: (yaw(b, 9 * st * math.sin(TAU * t * 2 - i) * (1 - rest) + 30 * rest), sw(b, 5 * st - (4 + 3.2 * i) * rest * .6)))


# ------------------------------------------------------------------------------------------------ dragon
def dr_wings(beat, fold=0.0):
    """beat -1..1: the wings' stroke (+ = up). The arm leads, the fingers follow and spread on the way down."""
    for s, k in (('l', 1), ('r', -1)):
        roll('wing_01_' + s, -k * (16 * beat - 30 * fold)); roll('wing_02_' + s, -k * (12 * beat - 34 * fold)); yaw('wing_01_' + s, k * 22 * fold)
        for f, w in (('f1', .6), ('f2', 1.0), ('f3', 1.4)): roll('wing_%s_%s' % (f, s), -k * (7 * beat * w - 20 * fold * w))


def dr_neck(pitch, turn=0.0, jaw=0.0):
    for b, k in (('neck_01', .8), ('neck_02', 1.0), ('neck_03', 1.2)): sw(b, pitch * k); yaw(b, turn * k)
    sw('head', -pitch * 1.6); yaw('head', turn * .8); sw('jaw', -jaw)


def dr_idle(t):
    ph = TAU * t; br = math.sin(2 * ph)
    move('pelvis', (0, 0, -.012 + .012 * math.sin(ph))); sw('spine_01', 1.2 * br); sw('spine_02', -1.6 * br)
    dr_wings(.35 * math.sin(ph), fold=.25); dr_neck(2.5 * math.sin(ph + .4), 7 * math.sin(ph), 3 + 3 * br)
    sw('upperarm_l', 4 * br); sw('upperarm_r', -4 * br); tail(7, 10, 3, .5, ph)


def dr_walk(t, k=1.0):
    ph = TAU * t
    move('pelvis', (0, 0, -.03 + .03 * math.cos(2 * ph))); yaw('pelvis', 5 * math.sin(ph)); roll('pelvis', 3.5 * math.sin(ph + .5)); sw('pelvis', -3)
    yaw('spine_01', -3 * math.sin(ph)); yaw('spine_02', -3 * math.sin(ph))
    for side, o in (('l', 0.0), ('r', math.pi)): hind(side, 20 * k * math.sin(ph + o), max(0.0, math.cos(ph + o)) ** 1.4)
    dr_wings(math.sin(2 * ph), fold=0.0); dr_neck(2 * math.sin(2 * ph + .5), 4 * math.sin(ph)); sw('upperarm_l', 8 * math.sin(ph + math.pi)); sw('upperarm_r', 8 * math.sin(ph))
    tail(7, 13, 4, .5, ph + math.pi)


def dr_attack(t):
    back = bump(t, 0.0, .5); out = ease((t - .35) / .15) * (1 - ease((t - .75) / .25))
    move('pelvis', (0, .05 * back - .12 * out, -.03 * out)); sw('pelvis', 5 * back - 8 * out); sw('spine_02', 6 * back - 8 * out)
    dr_neck(14 * back - 16 * out, 0, 34 * out + 6 * back); dr_wings(.9 * back - .8 * out, fold=0.0)
    for s in ('l', 'r'): sw('upperarm_' + s, 20 * out); hind(s, -5 * back + 4 * out, 0)
    chain('tail', 7, lambda b, i: sw(b, (-5 * back + 6 * out) * (.5 + .15 * i)))


def dr_hit(t):
    k = bump(t, 0.0, 1.0) * (1.25 - .5 * t)
    move('pelvis', (0, .07 * k, -.03 * k)); sw('pelvis', 6 * k); roll('pelvis', 4 * k); dr_neck(10 * k, 14 * k, 16 * k); dr_wings(-.8 * k, fold=.3 * k)
    hind('l', -6 * k, 0); hind('r', 5 * k, .2 * k); chain('tail', 7, lambda b, i: yaw(b, -6 * k * (.5 + .2 * i)))


def dr_death(t):
    st = bump(t, 0.0, .35); fall = ease((t - .2) / .45); rest = ease((t - .6) / .4)
    hip = head_z('pelvis')
    move('pelvis', (-.35 * fall, .08 * st, -(hip - .55) * fall + .05 * st)); sw('pelvis', 8 * st - 30 * fall); roll('pelvis', 5 * st + 70 * fall)
    sw('spine_01', -12 * rest); sw('spine_02', -14 * rest); dr_neck(12 * st - 22 * rest, 12 * st - 8 * rest, 20 * st + 12 * rest)
    dr_wings(-.9 * st * (1 - fall) - 1.2 * fall, fold=.75 * fall)
    hind('l', 24 * fall, .8 * fall); hind('r', -12 * fall + 8 * st, .4 * fall); sw('upperarm_l', 20 * fall); sw('upperarm_r', -10 * fall)
    chain('tail', 7, lambda b, i: (yaw(b, 8 * st * math.sin(TAU * t * 2 - i) * (1 - rest) + 6 * rest), sw(b, 4 * st + (2 + 1.2 * i) * rest)))


# ------------------------------------------------------------------------------------------------ stone giant
def gi_leg(side, swing, lift):
    s = '_' + side
    sw('thigh' + s, swing + 12 * lift); sw('calf' + s, -24 * lift - .3 * swing); sw('foot' + s, 12 * lift - .5 * swing)


def gi_arm(side, swing, lift):
    s = '_' + side
    sw('upperarm' + s, swing + 8 * lift); sw('lowerarm' + s, 14 * lift - .35 * swing); sw('hand' + s, 8 * lift - .4 * swing)


def gi_idle(t):
    ph = TAU * t; br = math.sin(2 * ph)
    move('pelvis', (0, 0, -.008 + .008 * math.sin(ph))); roll('pelvis', 1.0 * math.sin(ph)); sw('spine_01', 1.0 * br); sw('spine_02', -1.4 * br)
    yaw('neck_01', 5 * math.sin(ph)); yaw('head', 6 * math.sin(ph - .6)); gi_arm('l', 1.5 * br, 0); gi_arm('r', -1.5 * br, 0)


def gi_walk(t, k=1.0):
    ph = TAU * t
    move('pelvis', (0, 0, -.025 + .025 * math.cos(2 * ph))); yaw('pelvis', 7 * math.sin(ph)); roll('pelvis', 5 * math.sin(ph + .5))   # a heavy body thrown from side to side
    yaw('spine_01', -5 * math.sin(ph)); yaw('spine_02', -6 * math.sin(ph)); roll('spine_02', -3 * math.sin(ph + .5)); yaw('head', 4 * math.sin(ph)); sw('head', 2 * math.sin(2 * ph))
    for side, o in (('l', 0.0), ('r', math.pi)):
        gi_leg(side, 18 * k * math.sin(ph + o), max(0.0, math.cos(ph + o)) ** 1.4)
        f = ph + o + math.pi; gi_arm(side, 12 * k * math.sin(f), 0)
    stand()
    for side, o in (('l', 0.0), ('r', math.pi)):            # the knuckles stand on the ground and are lifted only to be carried forward
        f = ph + o + math.pi; plant('lowerarm_' + side, 'hand_' + side, ARM.data.bones['hand_' + side].tail_local.z + .16 * max(0.0, math.cos(f)) ** 1.4, -28, 28)


def gi_attack(t):
    up = ease(t / .4) * (1 - ease((t - .45) / .12)); slam = ease((t - .45) / .12) * (1 - ease((t - .8) / .2))
    hip = head_z('pelvis')
    move('pelvis', (0, .10 * up - .10 * slam, .12 * up - .06 * slam)); sw('pelvis', 24 * up - 6 * slam); sw('spine_01', 14 * up - 8 * slam); sw('spine_02', 12 * up - 10 * slam); sw('head', -10 * up + 10 * slam)
    for s, k in (('l', 1), ('r', -1)):
        sw('upperarm_' + s, 118 * up - 16 * slam); sw('lowerarm_' + s, 26 * up - 20 * slam); sw('hand_' + s, 18 * up - 14 * slam); yaw('upperarm_' + s, -k * 14 * (up + slam))   # the fists meet overhead and come down together
        gi_leg(s, -6 * up + 4 * slam, 0)


def gi_hit(t):
    k = bump(t, 0.0, 1.0) * (1.25 - .5 * t)
    move('pelvis', (0, .05 * k, -.02 * k)); sw('pelvis', 5 * k); roll('pelvis', 4 * k); sw('spine_02', 6 * k); yaw('spine_02', 10 * k); yaw('head', 12 * k)
    gi_arm('l', -8 * k, .3 * k); gi_arm('r', 5 * k, 0); gi_leg('l', -4 * k, 0); gi_leg('r', 4 * k, .15 * k)


def gi_death(t):
    st = bump(t, 0.0, .3); fall = ease((t - .15) / .5); rest = ease((t - .55) / .45)
    hip = head_z('pelvis')
    # sprite 825: it pitches forward and lies sprawled, a heap of its own stones, arms thrown out ahead, legs trailing
    move('pelvis', (0, -.45 * fall + .04 * st, -(hip - .42) * fall)); sw('pelvis', 6 * st - 53 * fall); roll('pelvis', 8 * rest)
    sw('spine_01', -4 * fall); sw('spine_02', -4 * fall); sw('neck_01', 8 * rest); sw('head', 12 * rest); yaw('head', 24 * rest)
    for s, k in (('l', 1), ('r', -1)):
        # angles from straight down, summed along the chain: the arm ends level ahead of it, the leg level behind, the foot turned back
        sw('upperarm_' + s, (119 + 8 * k) * fall); yaw('upperarm_' + s, k * (26 + 8 * k) * fall); sw('lowerarm_' + s, (6 - 6 * k) * fall); sw('hand_' + s, 4 * fall)
        sw('thigh_' + s, -(73 + 4 * k) * fall); yaw('thigh_' + s, k * 22 * fall); sw('calf_' + s, (64 + 6 * k) * fall); sw('foot_' + s, -108 * fall)


# ------------------------------------------------------------------------------------------------ knight
SPN = ('spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05')


def kn_leg(side, swing, lift):
    s = '_' + side
    sw('thigh' + s, swing + 22 * lift); sw('calf' + s, -44 * lift - max(0.0, -swing) * .35); sw('foot' + s, 12 * lift - .25 * swing)


def kn_carry(k=1.0, tilt=0.0):
    """The halberd (fused to hand_r, its shaft along the hanging forearm) is carried upright: the forearm lifts and the hand
    turns back by as much, so the shaft stays vertical. tilt + leans its head back, - forward."""
    sw('upperarm_r', 8 * k); sw('lowerarm_r', 40 * k); yaw('upperarm_r', 5 * k); sw('hand_r', -48 * k + tilt)


def kn_idle(t):
    ph = TAU * t; br = math.sin(2 * ph)
    move('pelvis', (.006 * math.sin(ph), 0, -.004 + .004 * br)); roll('pelvis', .8 * math.sin(ph))
    for b in SPN[2:]: sw(b, -.5 * br)
    yaw('neck_01', 6 * math.sin(ph)); yaw('head', 8 * math.sin(ph - .5)); kn_carry(); sw('upperarm_l', 2 * br); sw('lowerarm_l', 8 + 2 * br)


def kn_walk(t, k=1.0):
    ph = TAU * t
    move('pelvis', (0, 0, -.018 + .018 * math.cos(2 * ph))); yaw('pelvis', 5 * math.sin(ph)); roll('pelvis', 2.5 * math.sin(ph + .5)); sw('pelvis', -3)
    for b in SPN: yaw(b, -1.6 * math.sin(ph))
    sw('spine_03', -2); yaw('head', 2 * math.sin(ph))
    for side, o in (('l', 0.0), ('r', math.pi)): kn_leg(side, 24 * k * math.sin(ph + o), max(0.0, math.cos(ph + o)) ** 1.3 * min(1.6, k))
    kn_carry(); sw('upperarm_r', 3 * math.sin(ph)); sw('upperarm_l', 20 * math.sin(ph + math.pi)); sw('lowerarm_l', 14 + 8 * math.sin(ph + math.pi))


def kn_attack(t):
    """712-718: the axe goes up and back over the head, then comes down in front of him as he bends. The right hand works the
    shaft as a lever (forward and up to raise the head back, pulled down to the hip to throw it forward), the left hand guides."""
    up = ease(t / .4) * (1 - ease((t - .45) / .13)); chop = ease((t - .45) / .13) * (1 - ease((t - .8) / .2)); carry = 1 - max(up, chop)
    move('pelvis', (0, .03 * up - .08 * chop, -.05 * chop)); sw('pelvis', 4 * up - 10 * chop); yaw('pelvis', -8 * up + 6 * chop)
    for b in SPN: sw(b, 2.0 * up - 5 * chop); yaw(b, -2 * up + 2 * chop)
    kn_carry(carry)
    sw('upperarm_r', 38 * up - 42 * chop); sw('lowerarm_r', 30 * up + 16 * chop); sw('hand_r', -34 * up - 44 * chop)
    sw('upperarm_l', 58 * up + 50 * chop); yaw('upperarm_l', -26 * (up + chop)); sw('lowerarm_l', 50 * up + 30 * chop)
    kn_leg('l', 16 * chop - 4 * up, 0); kn_leg('r', -14 * chop, 0); sw('head', 6 * up - 8 * chop)


def kn_hit(t):
    k = bump(t, 0.0, 1.0) * (1.25 - .5 * t)
    move('pelvis', (0, .05 * k, -.03 * k)); sw('pelvis', 5 * k)
    for b in SPN: sw(b, 2.2 * k); yaw(b, 2.5 * k)
    yaw('head', 14 * k); sw('head', 8 * k); kn_carry(1 - .4 * k); sw('upperarm_l', -24 * k); roll('upperarm_l', -16 * k); kn_leg('l', -10 * k, 0); kn_leg('r', 6 * k, .2 * k)


def kn_death(t):
    st = bump(t, 0.0, .35); fall = ease((t - .2) / .45); rest = ease((t - .6) / .4)
    hip = head_z('pelvis')
    # sprite 275: on his back, arms thrown out
    move('pelvis', (0, .55 * fall + .05 * st, -(hip - .16) * fall)); sw('pelvis', 10 * st + 80 * fall)
    for b in SPN: sw(b, 2 * st + 1.5 * fall)
    sw('head', 14 * st - 6 * rest); yaw('head', 20 * rest)
    kn_carry(1 - fall, tilt=-80 * fall); sw('upperarm_r', -20 * fall); roll('upperarm_r', 55 * fall); roll('upperarm_l', -70 * fall); sw('lowerarm_l', 20 * fall)
    kn_leg('l', 16 * rest, .25 * bump(t, .2, .7) + .2 * rest); kn_leg('r', -4 * fall, 0); yaw('thigh_l', 14 * fall); yaw('thigh_r', -8 * fall)


CLIPS = {
    'slayer': (('Idle', sl_idle, 60, True), ('Walk', sl_walk, 24, True), ('Run', lambda t: sl_walk(t, 1.7), 12, True), ('Attack', sl_attack, 20, False), ('Hit', sl_hit, 10, False), ('Death', sl_death, 36, False)),
    'dragon': (('Idle', dr_idle, 60, True), ('Walk', dr_walk, 30, True), ('Run', lambda t: dr_walk(t, 1.7), 16, True), ('Attack', dr_attack, 24, False), ('Hit', dr_hit, 12, False), ('Death', dr_death, 42, False)),
    'giant': (('Idle', gi_idle, 60, True), ('Walk', gi_walk, 32, True), ('Run', lambda t: gi_walk(t, 1.9), 16, True), ('Attack', gi_attack, 26, False), ('Hit', gi_hit, 12, False), ('Death', gi_death, 40, False)),
    'knight': (('Idle', kn_idle, 60, True), ('Walk', kn_walk, 28, True), ('Run', lambda t: kn_walk(t, 1.45), 16, True), ('Attack', kn_attack, 22, False), ('Hit', kn_hit, 10, False), ('Death', kn_death, 36, False)),
}[WHO]


def stand():
    """Walk clips: the body is set down so that the lower foot stands at its rest height (no sinking, no floating)."""
    feet = [b for b in ('ball_l', 'ball_r') if b in ARM.pose.bones] or ['foot_l', 'foot_r']
    dz = min(ARM.pose.bones[b].tail.z - ARM.data.bones[b].tail_local.z for b in feet)
    move('pelvis', (0, 0, -dz))


THICK = {'slayer': .07, 'dragon': .14, 'giant': .2, 'knight': .08}[WHO]


def lie():
    """Death clips: nothing goes through the ground. The body is raised until its lowest bone end clears it by a limb's half thickness."""
    low = min(min(pb.head.z, pb.tail.z) for pb in ARM.pose.bones if pb.name != 'root')
    if low < THICK: move('pelvis', (0, 0, THICK - low))


def plant(joint, end, target_z, lo=-70.0, hi=70.0):
    """Turn `joint` (swing) until the far end of `end` is at target_z: a hand set on the ground without an IK rig."""
    base = ARM.pose.bones[joint].matrix.copy(); best = (1e9, 0.0)
    for i in range(29):
        a = lo + (hi - lo) * i / 28
        ARM.pose.bones[joint].matrix = base; bpy.context.view_layer.update(); sw(joint, a)
        e = abs(ARM.pose.bones[end].tail.z - target_z)
        if e < best[0]: best = (e, a)
    ARM.pose.bones[joint].matrix = base; bpy.context.view_layer.update(); sw(joint, best[1])


def build():
    sc = bpy.context.scene; sc.render.fps = FPS
    ARM.animation_data_create(); ARM.data.pose_position = 'POSE'
    order = [b.name for b in ARM.data.bones]
    for clip, fn, n, loop in CLIPS:
        name = '%s_%s' % (NAME, clip)
        if name in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[name])
        act = bpy.data.actions.new(name); act.use_fake_user = True; ARM.animation_data.action = act
        for f in range(n + 1):
            sc.frame_set(f + 1)
            for pb in ARM.pose.bones: pb.rotation_mode = 'QUATERNION'; pb.matrix_basis = Matrix.Identity(4)
            bpy.context.view_layer.update()
            fn((f % n) / n if loop else f / n)
            if clip in ('Walk', 'Run'): stand()
            if clip == 'Death' and WHO in ('slayer', 'giant'): lie()
            for b in order:
                if b == 'root': continue
                pb = ARM.pose.bones[b]; pb.keyframe_insert('rotation_quaternion', frame=f + 1)
                if b == 'pelvis': pb.keyframe_insert('location', frame=f + 1)
        for layer in act.layers:
            for strip in layer.strips:
                for slot in act.slots:
                    bag = strip.channelbag(slot)
                    if bag:
                        for cu in bag.fcurves:
                            for k in cu.keyframe_points: k.interpolation = 'LINEAR'
        info = {'frames': n + 1, 'loop': loop, 'duration_s': round(n / FPS, 4)}
        if clip in ('Walk', 'Run'):
            foot = 'ball_l' if 'ball_l' in ARM.pose.bones else 'foot_l'; ys = []
            for f in range(n):
                sc.frame_set(f + 1); bpy.context.view_layer.update(); ys.append(ARM.pose.bones[foot].tail.y)
            info['stride_m'] = round(max(ys) - min(ys), 3); info['speed_cm_s'] = round(200 * info['stride_m'] / (n / FPS), 1)   # two steps a cycle
        META[clip] = info
        print('[CLIPS] made', name, info)
    import json
    with open(os.path.join(DIR, 'clips.json'), 'w') as fh: json.dump(META, fh, indent=1)
    ARM.animation_data.action = None
    for pb in ARM.pose.bones: pb.matrix_basis = Matrix.Identity(4)


def set_clip(name, frame):
    a = bpy.data.actions[name]; ARM.animation_data_create(); ARM.animation_data.action = a
    try:
        if ARM.animation_data.action_slot is None and a.slots: ARM.animation_data.action_slot = a.slots[0]
    except Exception: pass
    ARM.data.pose_position = 'POSE'; bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()


def lod0():
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.endswith('_LOD0'): return o
    return max((o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers)), key=lambda o: len(o.data.vertices))


def review():
    from PIL import Image
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = 480; sc.render.resolution_y = 360; sc.render.film_transparent = False
    keep = lod0()
    for o in bpy.data.objects:
        if o.type == 'MESH': o.hide_render = o is not keep
    world = sc.world or bpy.data.worlds.new('W'); sc.world = world; world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.55, .62, .7, 1); world.node_tree.nodes['Background'].inputs[1].default_value = .6
    sun = bpy.data.objects.new('ReviewSun', bpy.data.lights.new('ReviewSun', 'SUN')); sun.data.energy = 3.0; sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = 0.0; sc.view_settings.look = 'None'; sun.rotation_euler = (math.radians(52), 0, math.radians(115)); sc.collection.objects.link(sun)
    bpy.ops.mesh.primitive_plane_add(size=40); ground = bpy.context.active_object
    gm = bpy.data.materials.new('ReviewGround'); gm.diffuse_color = (.32, .36, .22, 1); ground.data.materials.append(gm)
    cam = bpy.data.objects.new('ReviewCam', bpy.data.cameras.new('ReviewCam')); cam.data.lens = 45; sc.collection.objects.link(cam); sc.camera = cam
    size = max(keep.dimensions); hgt = keep.dimensions.z; cam.location = (size * 1.5 + 1.2, -size * .5, hgt * .8); look = Vector((0, 0, hgt * .5)); cam.rotation_euler = (look - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for clip, fn, n, loop in CLIPS:
        name = '%s_%s' % (NAME, clip); tiles = []
        for f in [1 + round(i * n / 8) for i in range(8)] if n >= 16 else [1 + round(i * n / 4) for i in range(4)]:
            set_clip(name, min(f, n + 1)); p = os.path.join(DIR, '_clip.png'); sc.render.filepath = p; bpy.ops.render.render(write_still=True); tiles.append(Image.open(p).convert('RGB'))
        cols = 4; rows = (len(tiles) + cols - 1) // cols; sheet = Image.new('RGB', (480 * cols, 360 * rows))
        for i, im in enumerate(tiles): sheet.paste(im, (480 * (i % cols), 360 * (i // cols)))
        sheet.save(os.path.join(DIR, 'clip_%s.jpg' % clip.lower()), quality=88); os.remove(os.path.join(DIR, '_clip.png'))
        print('[CLIPS] sheet', name)


PIECES = {'pelvis': 0, 'spine_01': 0, 'spine_02': 0, 'neck_01': 1, 'head': 1, 'upperarm_l': 2, 'lowerarm_l': 3, 'hand_l': 3, 'upperarm_r': 4, 'lowerarm_r': 5, 'hand_r': 5,
          'thigh_l': 6, 'calf_l': 7, 'foot_l': 7, 'thigh_r': 8, 'calf_r': 9, 'foot_r': 9}


def shatter(ob, src):
    """Sprite 825: the dead stone giant is a heap of its own stones, not a sleeping ape. Break the posed body at the joints
    into ten blocks (trunk, head, and two per limb), close each break with a face, and let every block settle a little
    apart from its neighbours, turned, lying on the ground. No blood: the picture has none."""
    import bmesh, random
    rnd = random.Random(825); names = {g.index: g.name for g in src.vertex_groups}; me = ob.data
    piece_v = []
    for v in me.vertices:
        acc = {}
        for g in v.groups:
            k = PIECES.get(names.get(g.group, ''), 0); acc[k] = acc.get(k, 0.0) + g.weight
        piece_v.append(max(acc, key=acc.get) if acc else 0)
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); uv = bm.loops.layers.uv.active; tag = bm.faces.layers.int.new('piece')
    for f in bm.faces:
        cnt = {}
        for v in f.verts: cnt[piece_v[v.index]] = cnt.get(piece_v[v.index], 0) + 1
        f[tag] = max(cnt, key=cnt.get)
    cut = [e for e in bm.edges if len(e.link_faces) == 2 and e.link_faces[0][tag] != e.link_faces[1][tag]]
    bmesh.ops.split_edges(bm, edges=cut)
    old = set(bm.faces); bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    for f in bm.faces:                                         # the break faces: stone colour from the rim they close
        if f in old: continue
        nb = next((lf for e in f.edges for lf in e.link_faces if lf in old), None)
        if nb is None: continue
        f[tag] = nb[tag]; f.smooth = False
        for l in f.loops:
            src_l = next((ol for ol in l.vert.link_loops if ol.face in old), None)
            if src_l is not None and uv: l[uv].uv = src_l[uv].uv
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if f not in old and len(f.verts) > 4])
    centre = sum((v.co for v in bm.verts), Vector()) / max(1, len(bm.verts))
    for k in range(10):
        vs = list({v for f in bm.faces if f[tag] == k for v in f.verts})
        if not vs: continue
        c = sum((v.co for v in vs), Vector()) / len(vs); out = Vector((c.x - centre.x, c.y - centre.y, 0)); out = out.normalized() if out.length > 1e-3 else Vector((0, 0, 0))
        R = Matrix.Rotation(math.radians(rnd.uniform(-38, 38)), 4, 'Z') @ Matrix.Rotation(math.radians(rnd.uniform(-20, 20)), 4, 'X') @ Matrix.Rotation(math.radians(rnd.uniform(-20, 20)), 4, 'Y')
        # a heap, not a sprawl: the limb blocks tumble in towards the trunk (the picture is about 2.6 m across)
        d = Vector(((centre.x - c.x) * 0.40, (centre.y - c.y) * 0.40, 0)) if k else Vector((0, 0, 0))
        for v in vs: v.co = c + (R @ (v.co - c)) + d
        z0 = min(v.co.z for v in vs)                           # every block comes to rest on the ground or on the trunk's flank, never hanging
        drop = z0 - 0.004 if (k and z0 < 0.45) or not k else z0 - rnd.uniform(0.18, 0.30)
        for v in vs: v.co.z -= max(0.0, drop)
    bm.normal_update(); bm.to_mesh(me); bm.free(); me.update()


def export():
    sc = bpy.context.scene
    for o in bpy.context.view_layer.objects: o.select_set(False)
    ARM.hide_set(False); ARM.select_set(True); bpy.context.view_layer.objects.active = ARM
    # the clips and the skeletal mesh go to Unreal through export_monster_ue.py (the creature importer's convention)
    # the body as it lies after the death clip: a static mesh for the corpse the kill leaves
    if WHO not in ('slayer', 'giant'): return                # the dragon and the knight leave their corpse kit assets (PhotorealPass/Corpses)
    n = next(c[2] for c in CLIPS if c[0] == 'Death'); set_clip('%s_Death' % NAME, n + 1)
    src = lod0(); dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(src.evaluated_get(dg), depsgraph=dg)
    ob = bpy.data.objects.new('SM_%s_Corpse_PR' % NAME, me); sc.collection.objects.link(ob); ob.matrix_world = src.matrix_world.copy()
    zmin = min((ob.matrix_world @ v.co).z for v in me.vertices)
    for v in me.vertices: v.co.z -= zmin - .004
    if WHO == 'giant': shatter(ob, src)
    cx = (max(v.co.x for v in me.vertices) + min(v.co.x for v in me.vertices)) / 2; cy = (max(v.co.y for v in me.vertices) + min(v.co.y for v in me.vertices)) / 2
    for v in me.vertices: v.co.x -= cx; v.co.y -= cy                      # the body lies in the middle of its pool (the ground decal is centred on the kill)
    for o in bpy.context.view_layer.objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    p = os.path.join(DIR, 'SM_%s_Corpse_PR.fbx' % NAME)
    bpy.ops.export_scene.fbx(filepath=p, use_selection=True, object_types={'MESH'}, apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='Y', axis_up='Z', bake_space_transform=False, mesh_smooth_type='FACE', use_mesh_modifiers=False, bake_anim=False, path_mode='STRIP')
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    print('[CLIPS] exported', os.path.basename(p), 'size', round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2), round(max(zs) - min(zs), 2))
    bpy.data.objects.remove(ob)


bpy.ops.wm.open_mainfile(filepath=BLEND)
ARM = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
if 'build' in A:
    build(); ARM.data.pose_position = 'REST'; bpy.ops.wm.save_mainfile(); ARM.data.pose_position = 'POSE'
if 'review' in A: review()
if 'export' in A:
    bpy.ops.wm.open_mainfile(filepath=BLEND); ARM = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); export()
