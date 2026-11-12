"""Shared constants for the Stonebrook duck (Quackers) source build.

Source units are metres, +X is the bill/actor forward direction, +Z is up, the
feet rest on Z=0 and the armature origin sits between the feet.
"""
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'Tools'
WORKING = ROOT / 'Working'
TEXTURES = ROOT / 'Textures'
EXPORT = ROOT / 'Export'
PREVIEWS = ROOT / 'Previews'

ASSET = 'SK_Duck'
LOD0 = 'SK_Duck_LOD0'
SEED = 1997
TEX_PX = 2048
FPS = 30


def pipeline_dir():
    """Locate the companion tools/blender pipeline (read-only)."""
    for parent in ROOT.parents:
        cand = parent / 'tools' / 'blender'
        if (cand / 'dinkasset' / 'validate.py').exists():
            return cand
    raise RuntimeError('tools/blender/dinkasset not found above ' + str(ROOT))


# Part identifiers stored in the integer attributes `duck_part` (point) and `duck_fpart` (face).
PART_BODY, PART_WING, PART_TAIL, PART_BILL_UP, PART_BILL_LO, PART_EYE, \
    PART_LEG, PART_TOE, PART_WEB, PART_CLAW, PART_LID, PART_NOSTRIL, \
    PART_CARD, PART_CAP_BODY, PART_CAP_HEAD, PART_BLOOD_BODY, PART_BLOOD_HEAD = range(17)
GORE_BODY = (PART_CAP_BODY, PART_BLOOD_BODY)
GORE_HEAD = (PART_CAP_HEAD, PART_BLOOD_HEAD)
GORE = GORE_BODY + GORE_HEAD

MATERIALS = ['MI_Duck_Feather', 'MI_Duck_Bill', 'MI_Duck_Feet', 'MI_Duck_Eye']
# Gore surfaces share the feather material (masked, two-sided, wet look from the ORM roughness).
PART_MATERIAL = {PART_BODY: 0, PART_WING: 0, PART_TAIL: 0, PART_LID: 0, PART_CARD: 0,
                 PART_CAP_BODY: 0, PART_CAP_HEAD: 0, PART_BLOOD_BODY: 0, PART_BLOOD_HEAD: 0,
                 PART_BILL_UP: 1, PART_BILL_LO: 1, PART_NOSTRIL: 1,
                 PART_LEG: 2, PART_TOE: 2, PART_WEB: 2, PART_CLAW: 2,
                 PART_EYE: 3}

# Feather flow curve (design space): from the bill root back along the head, neck and body
# to the tail tip.  Arc length along it parameterises the contour-feather rows.
SPINE_CURVE = [(0.215, 0, 0.428), (0.165, 0, 0.432), (0.148, 0, 0.405), (0.138, 0, 0.365),
               (0.124, 0, 0.322), (0.100, 0, 0.278), (0.050, 0, 0.240), (-0.020, 0, 0.215),
               (-0.100, 0, 0.215), (-0.170, 0, 0.235), (-0.235, 0, 0.262)]

# Contour-feather exposed row length along the flow curve (m), shared by cards and textures.
FEATHER_S = [0.00, 0.035, 0.07, 0.12, 0.20, 0.26, 0.33, 0.45, 0.56, 0.70]
FEATHER_L = [0.0030, 0.0034, 0.0042, 0.0060, 0.0085, 0.0130, 0.0200, 0.0245, 0.0250, 0.0230]

# Pekin posture: the upper body (everything but the legs) is authored in a design space and
# then rotated nose-up about the hip and lowered onto shorter, thicker legs.
POSTURE_PIVOT = (-0.030, 0.0, 0.165)
POSTURE_PITCH_DEG = 9.0
POSTURE_DROP = 0.027

# Decapitation plane (design space) across the mid neck: normal points toward the head.
CUT_POINT = (0.127, 0.0, 0.336)
CUT_NORMAL = (0.30, 0.0, 0.954)


def posture(p):
    """Design-space point -> final rest-space point (rotation about Y, then drop)."""
    import math
    a = math.radians(POSTURE_PITCH_DEG)
    x, y, z = p[0] - POSTURE_PIVOT[0], p[1], p[2] - POSTURE_PIVOT[2]
    xr = x * math.cos(a) - z * math.sin(a)
    zr = x * math.sin(a) + z * math.cos(a)
    return (xr + POSTURE_PIVOT[0], y, zr + POSTURE_PIVOT[2] - POSTURE_DROP)


HEAD_PIVOT = (0.138, 0.0, 0.368)


def headfix(p):
    """Counter-tilt the head (design space) so the bill stays level after the posture pitch.
    Blended over the upper neck (design z 0.372 -> 0.402) so the neck bends smoothly."""
    import math
    t = max(0.0, min(1.0, (p[2] - 0.372) / 0.030))
    w = t * t * (3 - 2 * t)
    a = -math.radians(POSTURE_PITCH_DEG) * w
    x, z = p[0] - HEAD_PIVOT[0], p[2] - HEAD_PIVOT[2]
    xr = x * math.cos(a) - z * math.sin(a)
    zr = x * math.sin(a) + z * math.cos(a)
    return (xr + HEAD_PIVOT[0], p[1], zr + HEAD_PIVOT[2])


def final(p):
    return posture(headfix(p))


def posture_matrix():
    from mathutils import Matrix, Vector
    import math
    piv = Vector(POSTURE_PIVOT)
    R = Matrix.Rotation(-math.radians(POSTURE_PITCH_DEG), 4, 'Y')
    return Matrix.Translation((0, 0, -POSTURE_DROP)) @ Matrix.Translation(piv) @ R @ Matrix.Translation(-piv)


LEG_Y = 0.050
KNEE = (0.004, 0.092)     # (x, z) final space: inside the feathered thigh
ANKLE = (-0.017, 0.049)   # intertarsal joint
FOOT = (-0.002, 0.013)    # base of the toes
_UPPER = [
    ('root', (0, 0, 0), (0, 0.1, 0), None),
    ('pelvis', (-0.070, 0, 0.205), (0.000, 0, 0.212), 'root'),
    ('spine_01', (0.000, 0, 0.212), (0.060, 0, 0.232), 'pelvis'),
    ('spine_02', (0.060, 0, 0.232), (0.100, 0, 0.272), 'spine_01'),
    ('neck_01', (0.100, 0, 0.272), (0.124, 0, 0.322), 'spine_02'),
    ('neck_02', (0.124, 0, 0.322), (0.138, 0, 0.368), 'neck_01'),
    ('neck_03', (0.138, 0, 0.368), (0.150, 0, 0.412), 'neck_02'),
    ('head', (0.150, 0, 0.412), (0.272, 0, 0.410), 'neck_03'),
    ('jaw', (0.192, 0, 0.412), (0.268, 0, 0.404), 'head'),
    ('tail_01', (-0.070, 0, 0.205), (-0.160, 0, 0.228), 'pelvis'),
    ('tail_02', (-0.160, 0, 0.228), (-0.255, 0, 0.268), 'tail_01'),
]
for _side, _s in (('l', 1), ('r', -1)):
    _UPPER += [
        ('wing_' + _side, (0.070, _s * 0.075, 0.262), (-0.060, _s * 0.090, 0.245), 'spine_01'),
        ('wingtip_' + _side, (-0.060, _s * 0.090, 0.245), (-0.215, _s * 0.060, 0.252), 'wing_' + _side),
    ]
BONES = [(n, (h if n == 'root' else final(h)), (t if n == 'root' else final(t)), p) for n, h, t, p in _UPPER]
for _side, _s in (('l', 1), ('r', -1)):
    _y = _s * LEG_Y
    BONES += [
        ('thigh_' + _side, final((-0.030, _s * 0.040, 0.165)), (KNEE[0], _y, KNEE[1]), 'pelvis'),
        ('calf_' + _side, (KNEE[0], _y, KNEE[1]), (ANKLE[0], _y, ANKLE[1]), 'thigh_' + _side),
        ('foot_' + _side, (ANKLE[0], _y, ANKLE[1]), (FOOT[0], _y, FOOT[1]), 'calf_' + _side),
        ('toes_' + _side, (FOOT[0], _y, FOOT[1]), (FOOT[0] + 0.058, _s * (LEG_Y + 0.006), 0.006), 'foot_' + _side),
    ]

ACTIONS = {
    # name: frames (inclusive, 30 fps), loop.  Locomotion speeds are derived from the gait.
    'Duck_Idle': dict(frames=61, loop=True),
    'Duck_Walk': dict(frames=13, loop=True),
    'Duck_Run': dict(frames=9, loop=True),
    'Duck_Peck': dict(frames=37, loop=False),
    'Duck_Quack': dict(frames=19, loop=False),
    'Duck_Hit': dict(frames=13, loop=False),
    'Duck_Death': dict(frames=46, loop=False),
    # Faithful original (brain 3): first hit -> head off, headless body keeps running
    # (bloody walk seq 111-119 loops 4 x 75 ms = 0.3 s); second hit -> gone.
    'Duck_HeadlessRun': dict(frames=10, loop=True),
    'Duck_HeadlessDeath': dict(frames=49, loop=False),
}


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)
