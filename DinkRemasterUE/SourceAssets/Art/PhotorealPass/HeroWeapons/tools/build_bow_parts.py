"""The bow that bends (art row AN-05): the one-piece bows of this kit cut into rigid parts that the game turns and stretches
while the bow is drawn (UDinkHeroBowSubsystem, Content/Dink/Data/Art/hero_weapons.json `bows`).

1997 draws the bow bending and its string coming back to Dink's face in six pictures a direction (graphics/dink/bow/hit).
The remaster's bow was one static mesh, strung and at rest. A static mesh cannot bend, so the stave is cut across into
a middle part (the grip, which stays in the hand) and six segments a limb, each with its origin on the stave's
centre line where it joins the part before it; the game turns each a few degrees further than the one before, which reads
as one bending limb (neighbours overlap by OVERLAP so no crack opens on the back of the bend). The string is cut at the
arrow's height into an upper and a lower half, each with its origin at its limb tip and +X along the string: the game
aims and stretches the two halves from the tips to the string hand.

No bake: the parts keep the UVs of the one-piece mesh and use its material and textures (kit manifest: a slot named
after a contract material takes that material).

    blender -b --factory-startup -t 4 --python HeroWeapons/tools/build_bow_parts.py -- Bow_Wood Bow_Blue
    python3 -I HeroWeapons/tools/build_weapons.py --manifest

Run it again whenever a bow is rebuilt (build_weapons.py <bow> final rewrites the bow's manifest.json). It writes
<bow>/Parts/SM_Hero_<bow>_<part>_PR.fbx, adds `parts` and `draw` to <bow>/manifest.json and prints the `draw` numbers
that hero_weapons.json carries (game units: centimetres, the game's Y is Blender's -Y).
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(KIT, '..', '..', '..', '..'))          # the Unreal project folder, as in build_weapons.py
sys.path.insert(0, os.path.join(os.path.dirname(KIT), 'Unclaimed', 'tools'))

HALF = 0.65                                    # build_weapons._bow: half the stave
GRIP = 0.110                                   # the middle part ends here (the binding ends at 0.068; the hand covers 0.05)
JOINTS = (0.110, 0.190, 0.270, 0.350, 0.430, 0.510)   # where the six segments of a limb begin (m from the grip centre)
WEIGHTS = (0.14, 0.18, 0.19, 0.19, 0.17, 0.13)       # share of the bend at each joint: least beside the grip and at the tip. Four segments turned
                                                     # up to 9.8 degrees at a joint at full draw and showed as a kink above the grip in a close render; six stay under 6.3
OVERLAP = 0.005
NOCK_UP = 0.035                                # the arrow's height on the stave: the string is cut and pulled here
MAX_DRAW = 0.56                                # the string hand's furthest travel behind the braced string
STRING_END = 0.972 * HALF                      # where the string is tied (build_weapons._bow)


def yc(x):
    """the stave's centre line at rest (build_weapons._bow)"""
    s = x / HALF; t = min(1.0, max(0.0, (abs(s) - 0.80) / 0.20)); sm = t * t * (3 - 2 * t)
    return -0.150 * s * s - 0.030 * s ** 4 + 0.022 * sm


def islands(bm):
    seen, out = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        seen.add(v.index)
        while stack:
            a = stack.pop(); isl.append(a)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index); stack.append(b)
        out.append(isl)
    return out


def piece(src, name, keep, x0=None, x1=None, origin=(0, 0, 0), turn=False):
    """A copy of the source mesh with only the islands `keep` accepts, cut to x0..x1, moved so `origin` is its origin
    (turn: also turned half round Z, so that its +X runs back towards the grip)."""
    me = src.data.copy(); bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.verts.index_update()
    drop = [v for isl in islands(bm) if not keep(isl) for v in isl]
    bmesh.ops.delete(bm, geom=drop, context='VERTS')
    for x, normal in ((x0, (-1, 0, 0)), (x1, (1, 0, 0))):
        if x is not None:
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(x, 0, 0), plane_no=normal, clear_outer=True, clear_inner=False)
    M = Matrix.Translation(-Vector(origin))
    if turn:
        M = Matrix.Rotation(math.pi, 4, 'Z') @ M
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free(); me.name = name
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    # the shading of the uncut mesh: the cut rings would otherwise get normals from one side only and show as a line
    mod = ob.modifiers.new('n', 'DATA_TRANSFER'); mod.object = src; mod.use_loop_data = True; mod.data_types_loops = {'CUSTOM_NORMAL'}; mod.loop_mapping = 'POLYINTERP_NEAREST'
    return ob


def export(ob, path):
    import pplib                                   # the kit's own FBX settings (and its scratch export: an FBX stores the path it was written to)
    pplib.export_fbx(path, [ob])


def build(bow):
    folder = os.path.join(KIT, bow); asset = 'SM_Hero_%s_PR' % bow
    bpy.ops.wm.open_mainfile(filepath=os.path.join(folder, asset + '.blend'))
    src = bpy.data.objects[asset]
    bm = bmesh.new(); bm.from_mesh(src.data)
    def is_string(isl):
        xs = [v.co.x for v in isl]; ys = [v.co.y for v in isl]
        return max(xs) - min(xs) > 1.0 and max(ys) - min(ys) < 0.01
    string = [isl for isl in islands(bm) if is_string(isl)]
    if len(string) != 1:
        raise RuntimeError('%s: %d string islands' % (bow, len(string)))
    ys = sum(v.co.y for v in string[0]) / len(string[0]); xe = max(v.co.x for v in string[0]); bm.free()
    stave = lambda isl: not is_string(isl)
    out = os.path.join(folder, 'Parts'); os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith('.fbx'):
            os.remove(os.path.join(out, f))
    made = []

    def emit(tag, ob, origin_ue):
        name = 'SM_Hero_%s_%s_PR' % (bow, tag); ob.name = name; ob.data.name = name
        path = os.path.join(out, name + '.fbx'); export(ob, path)
        dg = bpy.context.evaluated_depsgraph_get(); me = ob.evaluated_get(dg).to_mesh()
        lo = [min(v.co[i] for v in me.vertices) for i in range(3)]; hi = [max(v.co[i] for v in me.vertices) for i in range(3)]
        made.append({'name': name, 'part': tag, 'fbx': 'DinkRemasterUE/' + os.path.relpath(path, REPO).replace(os.sep, '/'), 'triangles': len(me.polygons),
                     'dimensions_m': [round(hi[i] - lo[i], 4) for i in range(3)], 'origin_cm': [round(v, 2) for v in origin_ue]})
    ends = list(JOINTS[1:]) + [None]
    emit('Grip', piece(src, 'grip', stave, -GRIP - OVERLAP, GRIP + OVERLAP), (0, 0, 0))
    for side, sgn in (('U', 1.0), ('L', -1.0)):
        for k, (a, b) in enumerate(zip(JOINTS, ends)):
            lo_ = a - OVERLAP; hi_ = None if b is None else b + OVERLAP
            x0, x1 = (lo_, hi_) if sgn > 0 else (None if hi_ is None else -hi_, -lo_)
            emit('Limb%s%d' % (side, k + 1), piece(src, 'limb', stave, x0, x1, origin=(sgn * a, yc(a), 0)), (sgn * a * 100, -yc(a) * 100, 0))
    # the string: cut where the arrow sits; each half starts at its own end and runs towards the cut
    emit('StringU', piece(src, 'string', is_string, NOCK_UP, None, origin=(xe, ys, 0), turn=True), (xe * 100, -ys * 100, 0))
    emit('StringL', piece(src, 'string', is_string, None, NOCK_UP, origin=(-xe, ys, 0)), (-xe * 100, -ys * 100, 0))
    draw = {'units': 'cm, the game mesh axes (X up the upper limb, +Y from the grip to the string, Z across)',
            'joints_cm': [[round(a * 100, 2), round(-yc(a) * 100, 2)] for a in JOINTS], 'weights': list(WEIGHTS),
            'string_end_cm': [round(xe * 100, 2), round(-ys * 100, 2)], 'nock_up_cm': NOCK_UP * 100, 'max_draw_cm': MAX_DRAW * 100,
            'string_half_cm': [round((xe - NOCK_UP) * 100, 2), round((xe + NOCK_UP) * 100, 2)]}
    mpath = os.path.join(folder, 'manifest.json'); m = json.load(open(mpath))
    m['parts'] = made; m['draw'] = draw
    m['parts_note'] = 'the same mesh cut into rigid parts for the bending bow (tools/build_bow_parts.py): same UVs, same material and textures'
    open(mpath, 'w').write(json.dumps(m, indent=1) + '\n')
    print('BOWPARTS %s: %d parts, %d triangles' % (bow, len(made), sum(p['triangles'] for p in made)))
    print('BOWDRAW %s %s' % (bow, json.dumps(draw)))


if __name__ == '__main__':
    for b in sys.argv[sys.argv.index('--') + 1:]:
        build(b)
