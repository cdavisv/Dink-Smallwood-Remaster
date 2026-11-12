"""Review renders of an assembled character: sun + sky, ground plane, AgX. usage: -- <blend rel to OUT> <outdir rel> <tag> [sets]
sets: body,face,hands,poses,lods (comma list)"""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *
a = args(); blend, outdir, tag = a[0], OUT / a[1], a[2]; sets = (a[3] if len(a) > 3 else 'body,face,hands,poses').split(',')
samples = int(a[4]) if len(a) > 4 else 48
bpy.ops.wm.open_mainfile(filepath=str(OUT / blend)); outdir.mkdir(parents=True, exist_ok=True)
D = bpy.data.objects; sc = bpy.context.scene; arm = D['Armature']; arm.data.pose_position = 'POSE'
lod0 = next(o for o in D if o.type == 'MESH' and o.name.endswith('_LOD0'))
for o in D:
    if o.type == 'MESH': o.hide_render = o is not lod0
setup_render(samples=samples, res=(700, 1100))
sc.world.node_tree.nodes['Background'].inputs[1].default_value = .085
idle = load_idle()
walk = json.loads((Path(__file__).parent / 'pose_cache/walk_poses.json').read_text()) if (Path(__file__).parent / 'pose_cache/walk_poses.json').exists() else {}
def pose(name):
    reset_pose(arm)
    if name == 'rest': return
    if name == 'idle': apply_world_pose(arm, idle); return
    if name.startswith('walk'): apply_world_pose(arm, walk[name]); return
    if name.startswith('fist'):
        fb = CHARS / 'Animations/Unarmed/Dink_Fist.blend'
        if 'Dink_Fist_Forward' not in bpy.data.actions:
            with bpy.data.libraries.load(str(fb)) as (s_, d_): d_.actions = ['Dink_Fist_Forward']
        act = bpy.data.actions['Dink_Fist_Forward']; arm.animation_data_create(); arm.animation_data.action = act
        try: arm.animation_data.action_slot = act.slots[0]
        except Exception: pass
        sc.frame_set(int(name.split('_')[1])); bpy.context.view_layer.update(); return
    if name == 'reach':   # arms up and forward, a deformation stress pose
        apply_world_pose(arm, idle)
        rot_bone(arm, 'upperarm_l', (0, 1, 0), -95); rot_bone(arm, 'upperarm_r', (1, 0, 0), -80); rot_bone(arm, 'lowerarm_r', (1, 0, 0), -60)
        rot_bone(arm, 'spine_03', (1, 0, 0), 12)
    if name == 'turn':     # mid-stride with the trunk and lead leg turning
        apply_world_pose(arm, walk['walk_45'])
        rot_bone(arm, 'spine_01', (0, 0, 1), 14); rot_bone(arm, 'spine_03', (0, 0, 1), 14); rot_bone(arm, 'thigh_l', (0, 0, 1), 28); rot_bone(arm, 'head', (0, 0, 1), 20)
    if name == 'crouch':
        apply_world_pose(arm, idle)
        rot_bone(arm, 'thigh_l', (1, 0, 0), -75); rot_bone(arm, 'calf_l', (1, 0, 0), 95); rot_bone(arm, 'thigh_r', (1, 0, 0), -30); rot_bone(arm, 'calf_r', (1, 0, 0), 60)
        rot_bone(arm, 'spine_02', (1, 0, 0), 25); rot_bone(arm, 'upperarm_l', (1, 0, 0), -45); rot_bone(arm, 'lowerarm_l', (1, 0, 0), -70)
def montage(files, out):
    ims = [bpy.data.images.load(str(f)) for f in files]
    w = sum(i.size[0] for i in ims); h = max(i.size[1] for i in ims)
    buf = np.zeros((h, w, 4), np.float32); x = 0
    for i in ims:
        px = np.empty(i.size[0] * i.size[1] * 4, np.float32); i.pixels.foreach_get(px); px = px.reshape(i.size[1], i.size[0], 4)
        buf[:i.size[1], x:x + i.size[0]] = px; x += i.size[0]
    o = bpy.data.images.new('montage', w, h); o.pixels.foreach_set(buf.ravel()); o.filepath_raw = str(out); o.file_format = 'PNG'; o.save()
    for f in files: os.remove(f)
def head_pos():
    bpy.context.view_layer.update(); return arm.pose.bones['head'].head.copy()
if 'body' in sets:
    pose('idle'); fs = []
    for nm, loc in (('front', (0.25, -5.2, 1.25)), ('threeq', (3.3, -4.0, 1.35)), ('back', (-0.6, 5.2, 1.3))):
        f = outdir / ('%s_body_%s.png' % (tag, nm)); shoot(f, loc, (0, 0, .93), lens=85, res=(700, 1100)); fs.append(f)
    montage(fs, outdir / ('%s_body.png' % tag))
if 'face' in sets:
    pose('idle'); h = head_pos()
    shoot(outdir / ('%s_face.png' % tag), (h.x + .12, h.y - .95, h.z + .09), (h.x, h.y - .02, h.z + .075), lens=85, res=(1000, 1000))
    fs = []
    for nm, loc in (('side', (h.x + 1.0, h.y - .25, h.z + .1)), ('backhead', (h.x - .5, h.y + .95, h.z + .2))):
        f = outdir / ('%s_head_%s.png' % (tag, nm)); shoot(f, loc, (h.x, h.y, h.z + .07), lens=85, res=(700, 700)); fs.append(f)
    montage(fs, outdir / ('%s_head.png' % tag))
if 'close' in sets:     # portrait distance: 0.6 m, sun and sky, then the same camera under an overcast sky
    pose('idle'); h = head_pos(); sky = next(n for n in sc.world.node_tree.nodes if n.type == 'TEX_SKY'); fs = []
    cam = (h.x + .10, h.y - .60, h.z + .085); tgt = (h.x, h.y - .02, h.z + .07)
    f = outdir / ('%s_close_sun.png' % tag); shoot(f, cam, tgt, lens=52, res=(900, 900)); fs.append(f)
    try: sky.sun_intensity = 0.0
    except Exception: pass
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = .22
    f = outdir / ('%s_close_ovc.png' % tag); shoot(f, (h.x - .22, h.y - .56, h.z + .085), tgt, lens=52, res=(900, 900)); fs.append(f)
    try: sky.sun_intensity = 1.0
    except Exception: pass
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = .085
    montage(fs, outdir / ('%s_close.png' % tag))
if 'hands' in sets:
    pose('idle'); bpy.context.view_layer.update(); hp = arm.pose.bones['hand_l'].head.copy(); fs = []
    f = outdir / ('%s_h1.png' % tag); shoot(f, (hp.x + .25, hp.y - .75, hp.z + .12), (hp.x - .02, hp.y, hp.z + .04), lens=80, res=(800, 800)); fs.append(f)
    f = outdir / ('%s_h2.png' % tag); shoot(f, (.45, -1.3, 1.25), (0, 0, 1.12), lens=70, res=(800, 800)); fs.append(f)
    f = outdir / ('%s_h3.png' % tag); shoot(f, (.7, -1.0, .35), (.02, 0, .2), lens=60, res=(800, 800)); fs.append(f)
    montage(fs, outdir / ('%s_details.png' % tag))
if 'poses' in sets:
    fs = []
    plist = [p for p in ('walk_20', 'walk_70', 'fist_3', 'fist_8', 'reach', 'crouch') if not p.startswith('walk') or p in walk]
    for i, p in enumerate(plist):
        pose(p); f = outdir / ('%s_pose_%s.png' % (tag, p))
        loc = (2.6, -4.2, 1.4) if i % 2 == 0 else (-2.9, 3.9, 1.5)
        if p in ('reach', 'crouch'): loc = (1.2, -5.0, 1.3)
        shoot(f, loc, (0, 0, .95), lens=85, res=(560, 900)); fs.append(f)
        if arm.animation_data: arm.animation_data.action = None
    montage(fs, outdir / ('%s_poses.png' % tag))
if 'game' in sets:      # gameplay distance, about 3 m, slightly raised camera
    pose('idle'); shoot(outdir / ('%s_game.png' % tag), (1.7, -2.6, 2.1), (0, 0, .95), lens=38, res=(900, 1000))
if 'overcast' in sets:
    pose('idle'); h = head_pos(); sky = sc.world.node_tree.nodes['Sky Texture'] if 'Sky Texture' in sc.world.node_tree.nodes else next(n for n in sc.world.node_tree.nodes if n.type == 'TEX_SKY')
    try: sky.sun_intensity = 0.0
    except Exception: sky.sun_disc = False
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = .22
    shoot(outdir / ('%s_overcast.png' % tag), (h.x + .12, h.y - .95, h.z + .09), (h.x, h.y - .02, h.z + .075), lens=85, res=(900, 900))
    try: sky.sun_intensity = 1.0
    except Exception: sky.sun_disc = True
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = .085
if 'lods' in sets:
    pose('idle'); fs = []
    for i in range(4):
        for o in D:
            if o.type == 'MESH' and '_LOD' in o.name: o.hide_render = not o.name.endswith('_LOD%d' % i)
        f = outdir / ('%s_lod%d.png' % (tag, i)); shoot(f, (0.25, -5.2, 1.25), (0, 0, .93), lens=85, res=(500, 800)); fs.append(f)
    montage(fs, outdir / ('%s_lods.png' % tag))
if 'skirt' in sets:     # skirt / tabard deformation: walk pose pair from two sides and a turn
    fs = []
    for i, (p, loc) in enumerate((('walk_20', (2.0, -4.6, 1.2)), ('walk_70', (2.0, -4.6, 1.2)), ('walk_20', (5.0, .3, 1.1)), ('walk_70', (-5.0, .3, 1.1)), ('turn', (1.6, -4.8, 1.2)), ('turn', (-3.2, 3.8, 1.3)))):
        pose(p); f = outdir / ('%s_skirt_%d.png' % (tag, i)); shoot(f, loc, (0, 0, .9), lens=85, res=(560, 900)); fs.append(f)
    montage(fs, outdir / ('%s_skirt.png' % tag))
