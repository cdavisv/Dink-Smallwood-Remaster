"""Beach shells at a size the play camera can read (13 Nov 2026).

The clam (7.5 cm) and the starfish (13.7 cm) of scatter_build.py are real-size single objects; from the play camera, 6.5 m back,
they are a few pixels, and the family layer has no scale of its own. This script makes, from the delivered FBX files and on the
same texture sets (no new bake):
  SM_ClamShell_Cluster_A/B/C   three or four surf clams of 10 to 14 cm, closed and open, half bedded in the sand, over 28 to 40 cm
  SM_Starfish_Large_A/B        the two starfish at 2.1 x (29 cm, a large common starfish)
and adds their rows to scatter_meshes in Terrain/manifest.json (status interim). Two LODs per file, as scatter_build.py exports.

    blender -b --factory-startup -t 4 --python Terrain/tools/scatter_clusters.py
"""
import bpy, bmesh, os, json, math
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__)); TER = os.path.dirname(HERE); OUT = os.path.join(TER, 'Scatter')


def load(name):
    """-> {0: mesh, 1: mesh} of one delivered scatter FBX (world transform applied, metres)"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(OUT, name + '.fbx'))
    out = {}
    for o in set(bpy.data.objects) - before:
        if o.type == 'MESH' and o.name[:len(name) + 5] in (name + '_LOD0', name + '_LOD1'):
            o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4); out[int(o.name[len(name) + 4])] = o
        else:
            bpy.data.objects.remove(o)
    assert set(out) == {0, 1}, (name, out)
    return out


def place(src, M, coll):
    o = src.copy(); o.data = src.data.copy(); coll.objects.link(o); o.data.transform(M); return o


def join(obs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]; bpy.ops.object.join(); o = obs[0]; o.name = name; o.data.name = name
    one_material(o); return o


def one_material(o):
    """one slot named as the texture set's material: a second FBX import names its copy MI_..._001, and the importer maps slots by name"""
    first = o.data.materials[0]
    base = bpy.data.materials.get(first.name.split('.')[0]) or first
    o.data.polygons.foreach_set('material_index', [0] * len(o.data.polygons))
    o.data.materials.clear(); o.data.materials.append(base)


def tris(o):
    o.data.calc_loop_triangles(); return len(o.data.loop_triangles)


def export(name, lods):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in lods:
        o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active = lods[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, name + '.fbx'), use_selection=True, apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='Y', axis_up='Z', bake_space_transform=False, use_triangles=True, mesh_smooth_type='FACE',
                             use_tspace=False, add_leaf_bones=False, bake_anim=False, path_mode='STRIP', object_types={'MESH', 'EMPTY'})


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0
    src = {n: load(n) for n in ('SM_ClamShell_Closed', 'SM_ClamShell_Open', 'SM_Starfish_A', 'SM_Starfish_B')}
    for d in src.values():
        for o in d.values():
            o.hide_set(True)
    man_path = os.path.join(TER, 'manifest.json'); man = json.load(open(man_path)); rows = {r['name']: r for r in man['scatter_meshes']}
    recs = []
    # (name, [(source, x, y, yaw degrees, scale, tilt degrees, sink as a share of the shell's height)])
    C, O = 'SM_ClamShell_Closed', 'SM_ClamShell_Open'
    clusters = [
        ('SM_ClamShell_Cluster_A', [(C, -0.09, 0.03, 25, 1.75, 6, 0.22), (O, 0.07, 0.06, 140, 1.45, -4, 0.12), (C, 0.03, -0.10, 250, 1.35, 9, 0.30), (C, 0.16, -0.05, 80, 1.1, -7, 0.25)]),
        ('SM_ClamShell_Cluster_B', [(O, -0.05, -0.04, 310, 1.7, 3, 0.10), (C, 0.10, 0.02, 190, 1.55, -8, 0.28), (C, -0.14, 0.09, 60, 1.2, 10, 0.2), (O, 0.02, 0.14, 15, 1.2, 5, 0.15)]),
        ('SM_ClamShell_Cluster_C', [(C, -0.05, 0.0, 100, 1.9, 5, 0.25), (C, 0.09, 0.05, 330, 1.45, -6, 0.2), (O, 0.04, -0.10, 215, 1.35, 4, 0.1)]),
    ]
    for name, parts in clusters:
        lods = []
        coll = bpy.data.collections.new(name); sc.collection.children.link(coll)
        for lod in (0, 1):
            obs = []
            for (s, x, y, yaw, k, tilt, sink) in parts:
                h = src[s][lod].dimensions.z * k
                M = Matrix.Translation((x, y, -sink * h)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(tilt), 4, 'X') @ Matrix.Scale(k, 4)
                obs.append(place(src[s][lod], M, coll))
            lods.append(join(obs, '%s_LOD%d' % (name, lod)))
        # bedded shells: cut what lies below the sand, then pivot at the base centre
        for o in lods:
            bm = bmesh.new(); bm.from_mesh(o.data)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(0, 0, -1), clear_inner=False, clear_outer=True)
            bm.to_mesh(o.data); bm.free()
        V = np.array([v.co[:] for v in lods[0].data.vertices]); c = (V.min(0) + V.max(0)) / 2
        for o in lods:
            o.data.transform(Matrix.Translation((-c[0], -c[1], 0.0)))
        export(name, lods)
        d = lods[0].dimensions
        recs.append(dict(rows[C], name=name, fbx='Scatter/%s.fbx' % name, dimensions_m=[round(x, 4) for x in d], lod0_triangles=tris(lods[0]), lod1_triangles=tris(lods[1]),
                         source_blend='Scatter/Scatter_Clusters.blend', status='interim', checks={'note': 'open at the sand line (bedded shells are cut at z = 0); UVs are those of the single shells'},
                         derived_from=sorted({p[0] for p in parts}),
                         review='not rendered in Cycles: judged in the game, Docs/Verification of the PR that binds it',
                         known_weaknesses='Three or four copies of the two delivered shells at 1.1 to 1.9 x (10 to 14 cm), set by hand and cut at the sand line: no sand piled against them, '
                                          'and the same two shells repeat. A cluster replaces what the 1997 sprite draws as one clam, so that the play camera can read it.'))
    for s in ('SM_Starfish_A', 'SM_Starfish_B'):
        name = s.replace('SM_Starfish_', 'SM_Starfish_Large_'); lods = []
        coll = bpy.data.collections.new(name); sc.collection.children.link(coll)
        for lod in (0, 1):
            o = place(src[s][lod], Matrix.Scale(2.1, 4), coll); o.name = '%s_LOD%d' % (name, lod); o.data.name = o.name; one_material(o); lods.append(o)
        export(name, lods)
        recs.append(dict(rows[s], name=name, fbx='Scatter/%s.fbx' % name, dimensions_m=[round(x, 4) for x in lods[0].dimensions], lod0_triangles=tris(lods[0]), lod1_triangles=tris(lods[1]),
                         source_blend='Scatter/Scatter_Clusters.blend', status='interim', derived_from=[s],
                         review='not rendered in Cycles: judged in the game, Docs/Verification of the PR that binds it',
                         known_weaknesses=rows[s].get('known_weaknesses', '') + ' This is the same mesh at 2.1 x (29 cm, a large common starfish) so that the play camera can read it; the knob rows scale with it.'))
    man['scatter_meshes'] = [r for r in man['scatter_meshes'] if r['name'] not in {x['name'] for x in recs}] + recs
    json.dump(man, open(man_path, 'w'), indent=1)
    bpy.ops.file.make_paths_relative() if bpy.data.filepath else None
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Scatter_Clusters.blend'), compress=True)
    for r in recs:
        print('CLUSTER', r['name'], r['dimensions_m'], r['lod0_triangles'], r['lod1_triangles'])


main()
