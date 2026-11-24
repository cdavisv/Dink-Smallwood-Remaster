"""LODs authored in a corpse's FBX, with the thrown chunks kept whole.

    Unclaimed/tools/bl.sh ../../Corpses/tools/fbx_lods.py Dragon_Corpse

Why: remains with thrown chunks (the dragon of picture 216) are many small islands round one large body. The engine's
reduction (Scripts/add_kit_lods.py, 50 % and 25 %) shrinks every small island alike, so the far chunks pull in from the
edge and the kit import refuses the mesh ("LOD2 slot 0 extent ... differs from LOD0"). Here only the LARGE islands are
reduced (never below BIG_FLOOR of their own triangles); every island under BIG_VERTS vertices (chunks, entrails,
the pool card) is copied as it is, so a LOD holds more than its nominal share when the chunks are a large part. The importer takes
objects <asset>_LOD0/_LOD1/_LOD2 from one FBX and then leaves the mesh alone (import_town_exteriors.import_module,
add_kit_lods.ensure_lods returns for LODs that came from the file).

The source .blend is opened, its one game object <asset> becomes <asset>_LOD0 (untouched), LOD1/LOD2 are built, the FBX
is exported again and the .blend saved. UVs are kept (collapse decimation), so no rebake. The manifest gets `lods`.
The run fails if a LOD stands outside LOD0's box by more than 0.4 cm on any side, or if a material slot loses its extent.
"""
import json
import os
import sys

import bmesh
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'Unclaimed', 'tools'))
import pplib as L  # noqa: E402

CORP = os.path.normpath(os.path.join(HERE, '..'))
RATIOS = (0.5, 0.25)        # of the LOD0 triangle count, as add_kit_lods.LOD_PERCENTS
BIG_VERTS = 300             # islands with fewer vertices are kept whole in every LOD
BIG_FLOOR = (0.35, 0.18)    # the big islands are never reduced below this share of their own triangles (thin tails and wing tips pull in below it)
OUTSIDE_CM = 0.4            # add_kit_lods.BOUNDS_TOLERANCE_CM is 0.5


def islands(ob):
    """[[vertex index, ...], ...] of the connected parts of a mesh object."""
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table(); seen = set(); out = []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]; seen.add(v.index); part = []
        while stack:
            a = stack.pop(); part.append(a.index)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index); stack.append(b)
        out.append(part)
    bm.free(); return out


def box(ob, slot=None):
    me = ob.data
    if slot is None:
        idx = range(len(me.vertices))
    else:
        idx = sorted({v for p in me.polygons if p.material_index == slot for v in p.vertices})
    pts = [ob.matrix_world @ me.vertices[i].co for i in idx]
    return [min(p[k] for p in pts) * 100 for k in range(3)] + [max(p[k] for p in pts) * 100 for k in range(3)]


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def reduced(lod0, ratio, name, floor):
    """copy of lod0 whose big islands are collapsed so the whole mesh has about ratio x its triangles"""
    o = L.dup(lod0, name); parts = islands(o); big = {i for part in parts if len(part) >= BIG_VERTS for i in part}
    me = o.data; total = tris(o); big_tris = sum(len(p.vertices) - 2 for p in me.polygons if all(v in big for v in p.vertices))
    keep = total - big_tris; want = max(floor, (total * ratio - keep) / max(1, big_tris))
    g = o.vertex_groups.new(name='lod_big'); g.add(sorted(big), 1.0, 'REPLACE')
    # split: the big islands in one object, the rest untouched in another
    L.activate(o); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.object.mode_set(mode='OBJECT')
    for v in me.vertices:
        v.select = v.index in big
    for p in me.polygons:
        p.select = all(v in big for v in p.vertices)
    for e in me.edges:
        e.select = all(v in big for v in e.vertices)
    before = set(bpy.data.objects)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.separate(type='SELECTED'); bpy.ops.object.mode_set(mode='OBJECT')
    body = next(x for x in bpy.data.objects if x not in before)
    L.mod(body, 'DECIMATE', ratio=want, use_collapse_triangulate=True); L.apply_mods(body)
    lo0 = box(lod0)                                  # a collapse may push a vertex a few millimetres out of LOD0's box (under the ground, as a rule): back inside
    for v in body.data.vertices:
        for k in range(3):
            v.co[k] = min(max(v.co[k], lo0[k] / 100.0), lo0[k + 3] / 100.0)
    # same material slot order as LOD0 on both halves, then join (the rest first so slots keep their indices)
    out = L.join([o, body], name); out.name = name; out.data.name = name
    for vg in list(out.vertex_groups):
        out.vertex_groups.remove(vg)
    return out, dict(ratio=ratio, big_islands=sum(1 for part in parts if len(part) >= BIG_VERTS), kept_whole=sum(1 for part in parts if len(part) < BIG_VERTS),
                     big_ratio=round(want, 4))


def main(name):
    asset = 'SM_%s_PR' % name; outdir = os.path.join(CORP, name); blend = os.path.join(outdir, asset + '.blend')
    bpy.ops.wm.open_mainfile(filepath=blend)
    lod0 = bpy.data.objects.get(asset) or bpy.data.objects.get(asset + '_LOD0')
    if lod0 is None:
        raise SystemExit('no object %s in %s' % (asset, blend))
    for old in [o for o in bpy.data.objects if o.name.startswith(asset + '_LOD') and o is not lod0]:
        bpy.data.objects.remove(old)
    lod0.name = asset + '_LOD0'; lod0.data.name = asset + '_LOD0'
    slots = [m.name for m in lod0.data.materials]; b0 = box(lod0); t0 = tris(lod0); obs = [lod0]; rows = [dict(lod=0, triangles=t0)]
    for i, r in enumerate(RATIOS):
        o, info = reduced(lod0, r, '%s_LOD%d' % (asset, i + 1), BIG_FLOOR[i])
        if [m.name for m in o.data.materials] != slots:
            raise SystemExit('LOD%d material slots %s != %s' % (i + 1, [m.name for m in o.data.materials], slots))
        b = box(o); out = max(max(b0[k] - b[k] for k in range(3)), max(b[k + 3] - b0[k + 3] for k in range(3)))
        if out > OUTSIDE_CM:
            raise SystemExit('LOD%d stands %.2f cm outside LOD0' % (i + 1, out))
        for s in range(len(slots)):
            a, c = box(lod0, s), box(o, s); ext = max(a[k + 3] - a[k] for k in range(3)); tol = max(2.0, 0.03 * ext) * 0.5
            d = max(abs(a[k] - c[k]) for k in range(6))
            if d > tol:
                raise SystemExit('LOD%d slot %d (%s) extent moved %.2f cm (allowed %.2f)' % (i + 1, s, slots[s], d, tol))
            info['slot%d_moved_cm' % s] = round(d, 2)
        info.update(lod=i + 1, triangles=tris(o), outside_lod0_cm=round(max(out, 0.0), 2)); rows.append(info); obs.append(o)
        col = lod0.users_collection[0]
        for c in list(o.users_collection):
            if c is not col:
                c.objects.unlink(o)
        if o.name not in col.objects:
            col.objects.link(o)
        o.hide_render = True
    fbx = os.path.join(outdir, asset + '.fbx'); L.export_fbx(fbx, obs)
    L.save_blend(blend)
    if os.path.exists(blend + '1'):
        os.remove(blend + '1')
    mpath = os.path.join(outdir, 'manifest.json'); man = json.load(open(mpath))
    man['lods'] = rows
    man['lod_build'] = 'Unclaimed/tools/bl.sh ../../Corpses/tools/fbx_lods.py %s (after the build; no rebake)' % name
    json.dump(man, open(mpath, 'w'), indent=1)
    print('FBX_LODS', name, json.dumps(rows))


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1])
