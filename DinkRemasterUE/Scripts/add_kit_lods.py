"""Run inside UnrealEditor's Python commandlet via add_kit_lods.sh (bug A200, 15 Nov 2026).

Gives the bound kit meshes that the 1997-sprite replacement draws with ONE LOD and Nanite off (the
art_wiring_audit.py `lod` rows: the seven corpse meshes of /Game/Dink/Photoreal/Corpses and three
Unclaimed machines/statues) generated LODs, in place: LOD0 stays the imported mesh untouched (same
vertices, sections, material slots, the corpse gore atlas in slot 0 and the alpha-tested blood-pool
card in slot 1), LOD1 keeps 50 % and LOD2 25 % of its triangles. Nanite stays OFF (the pool card is
alpha-tested). No re-import: the kit masters (Unclaimed/M_Struct_Baked*, Corpses/M_Struct_Baked*) are
not touched.

Screen sizes come from distance: LOD1 starts LOD1_DISTANCE_CM and LOD2 LOD2_DISTANCE_CM from the camera,
converted with Unreal's own rule (screen size = 2 * 0.5 * max(P[0][0], P[1][1]) * bounds radius /
distance; outdoor camera FOV 90 at 16:9: 1.778 * r / d). The play camera's boom is 180-650 cm (400 cm
default), so a mesh near Dink is always drawn at LOD0, and the gore is never shown on a reduced LOD at the
play camera except across the screen, where LOD1 still carries the whole pool card and the baked wounds
(the pool section and the bounds are checked per LOD below, and the run fails if a LOD loses them).

Re-runnable: a mesh carries the metadata tag DinkLods (settings + LOD0 triangle count); a mesh whose tag
matches is left alone. import_town_exteriors.py calls ensure_lods() for every single-LOD mesh it has
just re-imported with more than MIN_TRIANGLES triangles, so a kit re-import keeps generated LODs.
Report: Saved/PhotorealPass/kit_lods.json.

Bounds (23 Nov 2026): a static mesh's bounds are the union of ALL its LODs (StaticMeshBuilder.cpp: MeshBoundsBuilder +=
each LOD's SourceMeshBounds), and a reduced LOD can stand a little outside LOD0 (the corpse of the Mother, 26.8 cm tall
as imported, measured 29.5 cm once LOD1/LOD2 were generated, so Dink.Art.ImportedAssetScaleAndMaterials failed after any
corpse kit import). The section check above allows 3 % of the extent per LOD; the mesh's bounds may not move more than
BOUNDS_TOLERANCE_CM on any side. A mesh whose generated LODs would move them keeps its one LOD (tag DinkLods
'<tag>:single', left alone on later runs), except the A200 TARGETS, which keep their LODs (a warning names the move;
the corpse Maiden's is 4.2 cm, as on master since #154).
"""
import json
import unreal

LIB = unreal.EditorAssetLibrary
MESHES = (unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem))
VERSION = 'kitlods1'
MIN_TRIANGLES = 5000
LOD_PERCENTS = (1.0, 0.5, 0.25)
LOD1_DISTANCE_CM = 1000.0
LOD2_DISTANCE_CM = 2000.0
SCREEN_MULTIPLE = 0.5 * 16.0 / 9.0  # 0.5 * max(P[0][0], P[1][1]), horizontal FOV 90 at 16:9
BOUNDS_TOLERANCE_CM = 0.5  # the art test allows 1 cm on the whole size (Dink.Art.ImportedAssetScaleAndMaterials)

# the A200 rows (PR #154, art_wiring.csv `lod`)
TARGETS = [
    '/Game/Dink/Photoreal/Corpses/SM_Corpse_Maiden_PR',
    '/Game/Dink/Photoreal/Corpses/SM_Corpse_Girl_PR',
    '/Game/Dink/Photoreal/Corpses/SM_Corpse_Merchant_PR',
    '/Game/Dink/Photoreal/Corpses/SM_Corpse_Merchant_Green_PR',
    '/Game/Dink/Photoreal/Corpses/SM_Corpse_Peasant_PR',
    '/Game/Dink/Photoreal/Corpses/SM_Corpse_Knight_PR',
    '/Game/Dink/Photoreal/Corpses/SM_Dragon_Corpse_PR',
    '/Game/Dink/Photoreal/Unclaimed/SM_Dragon_Statue_PR',
    '/Game/Dink/Photoreal/Unclaimed/SM_Save_Machine_PR',
    '/Game/Dink/Photoreal/Unclaimed/SM_Teleport_Machine_PR',
]


def _struct(*names):
    for n in names:
        if hasattr(unreal, n):
            return getattr(unreal, n)
    raise RuntimeError('no reduction struct among ' + ', '.join(names))


def screen_sizes(mesh):
    r = mesh.get_bounds().sphere_radius
    s1 = min(0.9, 2.0 * SCREEN_MULTIPLE * r / LOD1_DISTANCE_CM)
    s2 = min(s1 * 0.5, 2.0 * SCREEN_MULTIPLE * r / LOD2_DISTANCE_CM)
    return [1.0, round(s1, 4), round(s2, 4)]


def tag_for(mesh, lod0_tris):
    return f'{VERSION}:{lod0_tris}:' + ','.join(str(p) for p in LOD_PERCENTS) + f':{int(LOD1_DISTANCE_CM)},{int(LOD2_DISTANCE_CM)}'


def sections(mesh, lod):
    """[(slot, triangles, (min x, min y, min z, max x, max y, max z) of the section's vertices)] of one LOD."""
    out = []
    for s in range(mesh.get_num_sections(lod)):
        slot = MESHES.get_lod_material_slot(mesh, lod, s)
        verts, tris = [], []
        try:
            got = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, lod, s)
            verts, tris = list(got[0]), list(got[1])
        except Exception as error:  # noqa: BLE001 (report and go on with counts only)
            unreal.log_warning(f'DINK KIT LODS: section read {mesh.get_name()} LOD{lod} s{s}: {error}')
        box = None
        if verts:
            xs, ys, zs = [v.x for v in verts], [v.y for v in verts], [v.z for v in verts]
            box = [round(min(xs), 1), round(min(ys), 1), round(min(zs), 1), round(max(xs), 1), round(max(ys), 1), round(max(zs), 1)]
        out.append({'slot': slot, 'triangles': len(tris) // 3, 'box': box})
    return out


def describe(mesh):
    lods = MESHES.get_lod_count(mesh)
    nanite = mesh.get_editor_property('nanite_settings').get_editor_property('enabled')
    return {'mesh': mesh.get_path_name().split('.')[0], 'lods': lods, 'nanite': bool(nanite),
            'radius_cm': round(mesh.get_bounds().sphere_radius, 1),
            'screen_sizes': [round(x, 4) for x in MESHES.get_lod_screen_sizes(mesh)],
            'triangles': [mesh.get_num_triangles(l) for l in range(lods)],
            'sections': [sections(mesh, l) for l in range(lods)]}


def check(info):
    """Every reduced LOD keeps every section (the corpse pool card in slot 1) with the LOD0 extent."""
    problems = []
    base = info['sections'][0]
    for lod in range(1, info['lods']):
        got = info['sections'][lod]
        if sorted(s['slot'] for s in got) != sorted(s['slot'] for s in base):
            problems.append(f"LOD{lod} sections {[s['slot'] for s in got]} != LOD0 {[s['slot'] for s in base]}")
            continue
        for b in base:
            g = next(s for s in got if s['slot'] == b['slot'])
            if g['triangles'] <= 0:
                problems.append(f"LOD{lod} slot {b['slot']} lost all triangles")
            if b['box'] and g['box']:
                ext = [b['box'][i + 3] - b['box'][i] for i in range(3)]
                tol = max(2.0, 0.03 * max(ext))
                if max(abs(g['box'][i] - b['box'][i]) for i in range(6)) > tol:
                    problems.append(f"LOD{lod} slot {b['slot']} extent {g['box']} differs from LOD0 {b['box']}")
    return problems


def bounds_box(mesh):
    """(min x, min y, min z, max x, max y, max z) of the mesh's bounds, cm (the union of its LODs)."""
    b = mesh.get_bounds()
    o, e = b.origin, b.box_extent
    return [o.x - e.x, o.y - e.y, o.z - e.z, o.x + e.x, o.y + e.y, o.z + e.z]


def bounds_moved(before, after):
    """Largest move of any side of the bounds box, cm."""
    return max(abs(a - b) for a, b in zip(after, before))


def ensure_lods(mesh, force=False, strict=False):
    """Generated LOD1/LOD2 on a single-object kit mesh. Returns (changed, info). Nanite stays as it is (off).
    strict: no mesh may change its bounds, the A200 TARGETS included (the corpse LOD restore of A9, 25 Nov 2026)."""
    lods = MESHES.get_lod_count(mesh)
    lod0 = mesh.get_num_triangles(0)
    tag = tag_for(mesh, lod0)
    if not force and LIB.get_metadata_tag(mesh, 'DinkLods') == tag and lods == len(LOD_PERCENTS):
        return False, None
    if not force and LIB.get_metadata_tag(mesh, 'DinkLods') == tag + ':single' and lods == 1:
        return False, None
    if lods > 1 and not LIB.get_metadata_tag(mesh, 'DinkLods'):
        # LODs from the FBX (TownExteriors _LOD1/_LOD2 objects): those are art, leave them
        return False, None
    if lods > 1:
        MESHES.remove_lods(mesh)
    before = bounds_box(mesh)
    options_cls = _struct('StaticMeshReductionOptions', 'EditorScriptingMeshReductionOptions')
    settings_cls = _struct('StaticMeshReductionSettings', 'EditorScriptingMeshReductionSettings')
    sizes = screen_sizes(mesh)
    rows = []
    for pct, size in zip(LOD_PERCENTS, sizes):
        row = settings_cls()
        row.set_editor_property('percent_triangles', pct)
        row.set_editor_property('screen_size', size)
        rows.append(row)
    options = options_cls()
    options.set_editor_property('auto_compute_lod_screen_size', False)
    options.set_editor_property('reduction_settings', rows)
    # the baked atlases (wounds, rust, carving) live in UV0: weigh UV seams and the silhouette above triangle count
    got = MESHES.set_lods(mesh, options)
    if got != len(LOD_PERCENTS):
        raise RuntimeError(f'{mesh.get_name()}: set_lods made {got} LODs')
    for lod in range(1, len(LOD_PERCENTS)):
        red = MESHES.get_lod_reduction_settings(mesh, lod)
        for key in ('silhouette_importance', 'texture_importance'):
            try:
                red.set_editor_property(key, unreal.MeshFeatureImportance.HIGH)
            except Exception as error:  # noqa: BLE001
                unreal.log_warning(f'DINK KIT LODS: {key}: {error}')
        MESHES.set_lod_reduction_settings(mesh, lod, red)
    MESHES.set_lod_screen_sizes(mesh, sizes)
    nanite = mesh.get_editor_property('nanite_settings')
    if nanite.get_editor_property('enabled'):
        raise RuntimeError(f'{mesh.get_name()}: Nanite is on (alpha-tested sections): not touched')
    moved = bounds_moved(before, bounds_box(mesh))
    path = mesh.get_path_name().split('.')[0]
    if moved > BOUNDS_TOLERANCE_CM:
        if path in TARGETS and not strict:
            # the A200 rows keep their LODs (decided for the frame rate); their bounds carry the reduced LODs' reach
            unreal.log_warning(f'DINK KIT LODS: {path}: generated LODs moved its bounds by {moved:.1f} cm (A200 target: LODs kept)')
            moved = 0.0
    if moved > BOUNDS_TOLERANCE_CM:
        # the imported size is the art's: one LOD rather than a mesh that measures bigger than its FBX
        MESHES.remove_lods(mesh)
        LIB.set_metadata_tag(mesh, 'DinkLods', tag + ':single')
        unreal.log_warning(f'DINK KIT LODS: {path}: generated LODs moved its bounds by {moved:.1f} cm '
                           f'({before} -> union of the LODs); kept as one LOD')
        return True, describe(mesh)
    LIB.set_metadata_tag(mesh, 'DinkLods', tag)
    info = describe(mesh)
    problems = check(info)
    if problems:
        raise RuntimeError(f'{mesh.get_name()}: ' + '; '.join(problems))
    return True, info


def folder_meshes(folder):
    """The single-LOD, non-Nanite static meshes of a content folder with more than MIN_TRIANGLES triangles."""
    out = []
    for path in sorted(LIB.list_assets(folder, recursive=False, include_folder=False)):
        path = str(path).split('.')[0]
        mesh = LIB.load_asset(path)
        if not isinstance(mesh, unreal.StaticMesh):
            continue
        if MESHES.get_lod_count(mesh) == 1 and mesh.get_num_triangles(0) > MIN_TRIANGLES \
                and not mesh.get_editor_property('nanite_settings').get_editor_property('enabled'):
            out.append(path)
    return out


def main():
    import os
    root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
    report = {'version': VERSION, 'percents': LOD_PERCENTS, 'lod1_cm': LOD1_DISTANCE_CM, 'lod2_cm': LOD2_DISTANCE_CM, 'before': [], 'after': []}
    # A9 (25 Nov 2026): DINK_KIT_LODS_FOLDER=/Game/Dink/Photoreal/Corpses also takes every single-LOD mesh of that folder
    # over MIN_TRIANGLES (the corpse LODs lost at the 16 Nov kit import); DINK_KIT_LODS_STRICT=1 lets no mesh change its
    # bounds, the A200 TARGETS included (such a mesh keeps its one LOD, tag '<tag>:single').
    strict = os.environ.get('DINK_KIT_LODS_STRICT') == '1'
    targets = list(TARGETS)
    if os.environ.get('DINK_KIT_LODS_FOLDER'):
        targets += [p for p in folder_meshes(os.environ['DINK_KIT_LODS_FOLDER']) if p not in targets]
    report['strict'] = strict
    report['bounds'] = []
    changed = 0
    for path in targets:
        mesh = LIB.load_asset(path)
        if mesh is None:
            raise RuntimeError('missing ' + path)
        report['before'].append(describe(mesh))
        box_before = bounds_box(mesh)
        did, _ = ensure_lods(mesh, strict=strict)
        report['bounds'].append({'mesh': path, 'before': [round(v, 2) for v in box_before],
                                 'after': [round(v, 2) for v in bounds_box(mesh)], 'moved_cm': round(bounds_moved(box_before, bounds_box(mesh)), 2)})
        if did:
            if not LIB.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError('Cannot save ' + path)
            changed += 1
        info = describe(mesh)
        report['after'].append(info)
        unreal.log(f"DINK KIT LODS: {path} lods {info['lods']} tris {info['triangles']} screen {info['screen_sizes']} nanite {info['nanite']} "
                   f"pool/slot tris {[[(s['slot'], s['triangles']) for s in l] for l in info['sections']]}")
    out = root + 'Saved/PhotorealPass/kit_lods.json'
    unreal.Paths.make_platform_filename(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w') as f:
        json.dump(report, f, indent=1)
    unreal.log(f'DINK KIT LODS OK: {len(targets)} meshes, {changed} changed (strict {strict}); report {out}')


if __name__ == '__main__':
    main()
