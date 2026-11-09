"""Publish only the reviewed starting-house floor mesh references.

The default checks and reports the change. --apply atomically updates the
house manifest after a separate saved-package verification commandlet.
"""
import argparse
import hashlib
import json
from pathlib import Path

OLD = '/Game/Dink/Kits/Stonebrook/SM_Floor_Oak_2m_01.SM_Floor_Oak_2m_01'
NEW = '/Game/Dink/Kits/Stonebrook/Refinements/FloorOakV1/SM_Floor_Oak_2m_01.SM_Floor_Oak_2m_01'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--verification', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.project.resolve()
    verify = json.loads(args.verification.read_text())
    assert verify['passed'] and verify['mode'] == 'verify'
    assert verify['project'] == str(root)
    assert verify['native_geometry_uv_nails_collision_nanite_unchanged']
    assert not verify['protected_changes']
    assert not verify['runtime_data_changes']
    output = root / 'Saved/Art/floor_surface_publication.json'
    data_pins = verify['runtime_data_sha256']
    actual_data = {str(p.relative_to(root)): sha(p) for p in (root / 'Content/Dink/Data').rglob('*') if p.is_file()}
    assert set(actual_data) == set(data_pins), 'Runtime Data file set changed since verification'
    house_key = 'Content/Dink/Data/Art/stonebrook.json'
    assert house_key in data_pins
    for relative, digest in data_pins.items():
        if actual_data[relative] == digest:
            continue
        # Only this publisher's exact prior output may differ on an idempotent run.
        assert relative == house_key and output.is_file(), 'Runtime Data drift: ' + relative
        previous = json.loads(output.read_text())
        assert previous['passed'] and previous['applied']
        assert previous['verification_sha256'] == sha(args.verification)
        assert previous['verified_baseline_sha256'] == digest
        assert previous['after_sha256'] == actual_data[relative], 'Published house changed since publication'
    source = root / 'SourceAssets/Art/Stonebrook/Refinements/FloorOakV1'
    assert sha(source / 'material_manifest.json') == verify['source_manifest_sha256']
    spec = json.loads((source / 'material_manifest.json').read_text())
    for row in list(spec['textures'].values()) + list(spec['source_files'].values()) + [spec['source_image']]:
        path = (source / row['file']).resolve()
        assert path.is_relative_to(source.resolve())
        assert sha(path) == row['sha256'], 'Source changed since verification: ' + row['file']
    assert sha(root / 'Scripts/import_floor_surface.py') == verify['importer_sha256']
    packages = verify['saved_package_sha256']
    expected = {'Content/Dink/Kits/Stonebrook/Refinements/FloorOakV1/SM_Floor_Oak_2m_01.uasset',
                'Content/Dink/Materials/Stonebrook/Refinements/MI_Stonebrook_FloorOakV1.uasset'}
    expected.update('Content/Dink/Textures/Stonebrook/Refinements/T_Stonebrook_FloorOakV1_' + channel + '.uasset'
                    for channel in ('BC', 'N', 'ORM'))
    assert set(packages) == expected
    for relative, digest in packages.items():
        path = (root / relative).resolve()
        assert path.is_relative_to(root / 'Content'), relative
        assert sha(path) == digest, 'Package changed since native verification: ' + relative
    target = root / 'Content/Dink/Data/Art/stonebrook.json'
    original = target.read_bytes()
    document = json.loads(original)
    assert document['schema'] == 'dink-art/1' and document['screen'] == 1
    elements = document['elements']
    assets = document['assets']
    old_elements = [row for row in elements if row.get('mesh') == OLD]
    new_elements = [row for row in elements if row.get('mesh') == NEW]
    old_assets = [row for row in assets if row.get('mesh') == OLD]
    new_assets = [row for row in assets if row.get('mesh') == NEW]
    before_counts = (len(old_elements), len(new_elements), len(old_assets), len(new_assets))
    assert before_counts in {(56, 0, 1, 0), (0, 56, 0, 1)}, before_counts
    for row in old_elements + old_assets:
        row['mesh'] = NEW
    # Prove the only semantic changes are precisely the 57 mesh references.
    reverted = json.loads(json.dumps(document))
    for row in reverted['elements'] + reverted['assets']:
        if row.get('mesh') == NEW:
            row['mesh'] = OLD
    baseline = json.loads(original)
    for row in baseline['elements'] + baseline['assets']:
        if row.get('mesh') == NEW:
            row['mesh'] = OLD
    assert reverted == baseline
    if args.apply and old_elements:
        temporary = target.with_suffix('.json.floor-tmp')
        assert not temporary.exists()
        temporary.write_text(json.dumps(document, indent=2) + '\n')
        temporary.replace(target)
    report = {'passed': True, 'applied': args.apply, 'already_published': not old_elements,
              'floor_elements': 56, 'asset_rows': 1, 'only_mesh_references_changed': True,
              'transforms_collision_lights_and_other_elements_unchanged': True,
              'before_sha256': hashlib.sha256(original).hexdigest(), 'after_sha256': sha(target),
              'verified_baseline_sha256': data_pins[house_key],
              'verification_sha256': sha(args.verification)}
    report_output = output if args.apply else output.with_name('floor_surface_publication_check.json')
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
