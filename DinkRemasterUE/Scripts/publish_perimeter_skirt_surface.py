"""Guarded perimeter_skirt context publication. Default is check-only; --apply creates one new JSON."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

SOURCE_REL = 'SourceAssets/Art/Stonebrook/Refinements/PerimeterSkirtV1'
HANDOFF_SHA = '36c3dd6d2a7f66669eb666ad1724e234b4250a5e3f61c7f2dc7360cf3eafac0d'
DEST = '/Game/Dink/Kits/Stonebrook/Refinements/PerimeterSkirtV1/SM_Stonebrook_PerimeterSkirt_V1'
MAT = '/Game/Dink/Materials/Stonebrook/Refinements/M_Stonebrook_Underfloor_DarkOak_V1'
PACKAGES = {p.replace('/Game/', 'Content/', 1) + '.uasset' for p in (DEST,)}
CONTEXT = 'Content/Dink/Data/Art/stonebrook_perimeter_skirt_v1.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained(root, relative):
    path = (root / relative).resolve()
    assert path.is_relative_to(root.resolve()), 'Path escapes bundle: ' + relative
    assert path.is_file(), 'Missing file: ' + relative
    return path


def data_pins(root):
    return {str(p.relative_to(root)): sha(p) for p in (root / 'Content/Dink/Data').rglob('*') if p.is_file()}


def asset_pins(root):
    return {str(p.relative_to(root)): sha(p) for p in (root / 'Content').rglob('*')
            if p.is_file() and p.suffix.lower() in {'.uasset', '.uexp', '.ubulk'}}


def source_guard(source):
    assert sha(source / 'source_handoff.json') == HANDOFF_SHA, 'Unreviewed source handoff'
    handoff = json.loads((source / 'source_handoff.json').read_text())
    for name, digest in handoff['files'].items():
        assert sha(contained(source, name)) == digest, 'Source drift: ' + name
    raw = json.loads((source / 'asset_manifest.json').read_text())
    original_plan = json.loads((source / 'underfloor_plan.json').read_text())
    context = json.loads((source / 'stonebrook_perimeter_skirt_v1.context.draft.json').read_text())
    assert raw['schema'] == 'dink-perimeter-skirt/1'
    assert raw['proposed_package'] == DEST
    assert raw['vertices'] == 48 and raw['triangles'] == 96 and raw['source_UCX_count'] == 0
    assert raw['world_top_cm'] == -.2 and raw['world_base_cm'] == -18
    assert raw['inside_original_floor_contour'] is True
    assert raw['material'] == original_plan['material']
    assert raw['material']['base_color_linear'] == [.009, .005, .0025]
    assert context['schema'] == 'dink-art/1' and context['screen'] == 1
    assert context['context'] == {'visibility': 'owner_screen_only', 'render_only': True}
    assert set(context) == {'schema', 'screen', 'context', 'source', 'assets', 'elements'}
    assert context['source'] == SOURCE_REL + '/asset_manifest.json'
    assert len(context['assets']) == len(context['elements']) == 1
    path = DEST + '.' + DEST.rsplit('/', 1)[1]
    element = context['elements'][0]
    assert element == {'name': 'StartingHousePerimeterSkirtV1', 'mesh': path,
        'world_cm': raw['placement_world_cm'], 'rotation_deg': [0,0,0], 'scale': [1,1,1],
        'collision': False, 'camera_occluder': False}
    assert raw['placement_world_cm'] == original_plan['placement_world_cm']
    assert context['assets'][0] == {'mesh': path, 'expected_size_cm': [x*100 for x in raw['dimensions_m']],
        'expected_lods': 1, 'bounds_tolerance_cm': 1}
    verified = json.loads((source / 'export_verification.json').read_text())
    assert verified['passed'] and verified['actual_native_gap_rays_replayed'] == 7
    assert all(r['nearest_front_facing_normal_dot_ray'] < 0 for r in verified['ray_results'])
    spec = dict(raw)
    spec['source_geometry'] = {'vertices': 48, 'triangles': 96, 'dimensions_m': raw['dimensions_m']}
    spec['files'] = {'fbx': {'file': next(n for n in raw['files'] if n.endswith('.fbx'))}}
    plan = dict(original_plan, dimensions_m=raw['dimensions_m'])
    return spec, plan, context


def owned_content(root):
    content = root / 'Content'
    assert content.is_dir() and not content.is_symlink()
    assert not any(p.is_symlink() for p in content.rglob('*')), 'Shared/symlinked Content forbidden'


def tool_pins(root):
    return {name: sha(root / 'Scripts' / name) for name in
        ('import_perimeter_skirt_surface.py', 'publish_perimeter_skirt_surface.py', 'perimeter_fbxparse.py')}


def module_pins(root):
    paths = list((root / 'Binaries/Linux').glob('*.so')) + list((root / 'Plugins').glob('*/Binaries/Linux/*.so'))
    assert paths, 'Project modules missing'
    assert all(not p.is_symlink() and p.resolve().is_relative_to(root.resolve()) for p in paths), 'Shared project modules forbidden'
    return {str(p.relative_to(root)): sha(p) for p in paths}


def report_guard(root, report):
    assert not (root / 'Saved').is_symlink(), 'Shared Saved tree forbidden'
    saved = (root / 'Saved').resolve()
    assert saved.is_relative_to(root.resolve()), 'Shared Saved tree forbidden'
    assert report.resolve().is_relative_to(saved), 'Report must stay in owned Saved tree'


def source_geometry(source, spec):
    import perimeter_fbxparse as fbx
    filename = contained(source, spec['files']['fbx']['file'])
    summary = fbx.inspect(filename)
    assert summary['unit_scale_factor'] == 100
    assert summary['up_axis'] == [2,1] and summary['front_axis'] == [1,-1]
    assert summary['coord_axis'] == [0,1]
    models = summary['models']
    assert set(models) == {spec['name']}
    model = models[spec['name']]
    assert model['type'] == 'Mesh' and model['parent'] is None
    assert all(abs(v) < 1e-7 for v in model['translation'] + model['rotation'])
    assert model['scaling'] == [1,1,1]
    _, top = fbx.parse(filename)
    objects = next(n for n in top if n.name == 'Objects')
    geometries = [n for n in objects.children if n.name == 'Geometry']
    assert len(geometries) == 1
    geom = geometries[0]
    raw = geom.first('Vertices').props[0]
    points = [(raw[i]*100, -raw[i+1]*100, raw[i+2]*100) for i in range(0,len(raw),3)]
    faces = []; current = []
    for index in geom.first('PolygonVertexIndex').props[0]:
        current.append(-index-1 if index < 0 else index)
        if index < 0:
            assert len(current) == 3
            faces.append(tuple(current)); current = []
    assert not current and len(points) == 48 and len(faces) == 96
    return points, faces


def match_geometry(expected, faces, actual, actual_faces):
    from collections import Counter
    assert len(actual) == len(expected) and len(actual_faces) == len(faces)
    mapping = {}
    maximum = 0.
    for i,point in enumerate(actual):
        assert all(math.isfinite(x) for x in point)
        distance,index = min((math.dist(point,target),j) for j,target in enumerate(expected))
        assert distance < .05, 'Source vertex differs'
        mapping[i] = index
        maximum = max(maximum,distance)
    assert len(set(mapping.values())) == len(expected), 'Source matching not bijective'
    cyclic = lambda t: min(tuple(t),tuple(t[1:])+tuple(t[:1]),tuple(t[2:])+tuple(t[:2]))
    assert all(len(t)==3 and all(i in mapping for i in t) for t in actual_faces)
    assert Counter(cyclic(tuple(mapping[i] for i in t)) for t in actual_faces) == Counter(cyclic(t) for t in faces), 'Source triangles/winding differ'
    return maximum



def binding_guard(root, plan):
    doc = json.loads((root / 'Content/Dink/Data/Art/stonebrook.json').read_text())
    rows = [{k: row[k] for k in ('name', 'world_cm', 'rotation_deg', 'scale')}
            for row in doc['elements'] if row.get('mesh', '').split('.')[-1] == 'SM_Floor_Oak_2m_01']
    rows.sort(key=lambda row: row['name'])
    assert len(rows) == 56
    assert all(math.isfinite(v) for row in rows for key in ('world_cm', 'rotation_deg', 'scale') for v in row[key])
    signature = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert signature == plan['floor_transform_signature_sha256'], 'Floor placement drift'
    return signature


def check_publication(root, verification):
    owned_content(root)
    report_guard(root,root/'Saved/Art/perimeter_skirt_surface_publication.json')
    verify = json.loads(verification.read_text())
    assert verify['tool_sha256'] == tool_pins(root), 'Tool drift after verification'
    assert verify['module_sha256'] == module_pins(root), 'Module drift after verification'
    assert verify['passed'] is True and verify['mode'] == 'verify'
    assert verify['project'] == str(root)
    assert not verify['protected_changes'] and not verify['runtime_data_changes']
    source = root / SOURCE_REL
    _, plan, context = source_guard(source)
    assert sha(source / 'source_handoff.json') == verify['source_handoff_sha256']
    assert sha(root / 'Scripts/import_perimeter_skirt_surface.py') == verify['importer_sha256']
    assert sha(root / 'Scripts/publish_perimeter_skirt_surface.py') == verify['publisher_sha256']
    binding_guard(root, plan)
    assert set(verify['saved_package_sha256']) == PACKAGES
    current_assets = asset_pins(root)
    assert current_assets == verify['all_asset_sha256'], 'Asset set/content drift after saved verification'
    assert all(current_assets[p] == digest for p, digest in verify['saved_package_sha256'].items())
    baseline = verify['runtime_data_sha256']
    current = data_pins(root)
    expected = (json.dumps(context, indent=2) + '\n').encode()
    already = CONTEXT in current
    receipt = root / 'Saved/Art/perimeter_skirt_surface_publication.json'
    if CONTEXT in baseline:
        # A fresh saved-native verification pins an already delivered context.
        # This supports normal clones without trusting a machine-local receipt.
        assert baseline[CONTEXT] == hashlib.sha256(expected).hexdigest()
        assert current == baseline, 'Runtime Data drift after fresh published verification'
        assert already
        return verify, expected, True
    if already:
        assert receipt.is_file(), 'Refusing preexisting foreign context'
        prior = json.loads(receipt.read_text())
        assert prior['passed'] is True and prior['applied'] is True
        assert prior['verification_sha256'] == sha(verification)
        assert prior['baseline_data_sha256'] == baseline
        assert prior['context_sha256'] == current[CONTEXT] == hashlib.sha256(expected).hexdigest()
        current = {p: digest for p, digest in current.items() if p != CONTEXT}
    assert current == baseline, 'Runtime Data set/content drift after saved verification'
    return verify, expected, already


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--verification', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.project.resolve()
    verify, payload, already = check_publication(root, args.verification)
    if args.apply and not already:
        target = root / CONTEXT
        temporary = root / 'Saved/Art/perimeter_skirt_context.tmp'
        temporary.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive temporary creation; atomic link refuses any concurrent target creation.
        with temporary.open('xb') as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        try:
            check_publication(root, args.verification)  # Recheck immediately before publication.
            os.link(temporary, target)
        finally:
            temporary.unlink()
    expected_data = dict(verify['runtime_data_sha256'])
    if args.apply or already:
        expected_data[CONTEXT] = hashlib.sha256(payload).hexdigest()
    assert data_pins(root) == expected_data, 'Unexpected concurrent Data mutation'
    report = {'passed': True, 'applied': args.apply, 'already_published': already,
              'verification_sha256': sha(args.verification),
              'baseline_data_sha256': verify['runtime_data_sha256'],
              'context_sha256': hashlib.sha256(payload).hexdigest(),
              'only_new_context_created': True, 'original_floor_and_vista_unchanged': True}
    output = root / ('Saved/Art/perimeter_skirt_surface_publication.json' if args.apply
                     else 'Saved/Art/perimeter_skirt_surface_publication_check.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
