"""Guarded underfloor context publication. Default is check-only; --apply creates one new JSON."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

SOURCE_REL = 'SourceAssets/Art/Stonebrook/Refinements/UnderfloorV1'
HANDOFF_SHA = 'e697e206247435c13cb5082c9c22357e52dd630c7b72d8ea9f58056ad705b2c8'
DEST = '/Game/Dink/Kits/Stonebrook/Refinements/UnderfloorV1/SM_Underfloor_Stonebrook_V1'
MAT = '/Game/Dink/Materials/Stonebrook/Refinements/M_Stonebrook_Underfloor_DarkOak_V1'
PACKAGES = {p.replace('/Game/', 'Content/', 1) + '.uasset' for p in (DEST, MAT)}
CONTEXT = 'Content/Dink/Data/Art/stonebrook_underfloor_v1.json'


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
    spec = json.loads((source / 'asset_manifest.json').read_text())
    plan = json.loads((source / 'underfloor_plan.json').read_text())
    context = json.loads((source / 'stonebrook_underfloor_v1.context.draft.json').read_text())
    assert spec['schema'] == 'dink-underfloor-asset/1'
    assert spec['proposed_native_package'] == DEST
    assert spec['source_geometry']['triangles'] == 44
    assert spec['source_geometry']['source_UCX_count'] == 0
    assert context['schema'] == 'dink-art/1' and context['screen'] == 1
    assert context['context'] == {'visibility': 'owner_screen_only', 'render_only': True}
    assert len(context['assets']) == len(context['elements']) == 1
    assert context['elements'][0] == spec['proposed_runtime_element']
    assert context['elements'][0]['collision'] is False and context['elements'][0]['camera_occluder'] is False
    assert context['assets'][0]['mesh'] == DEST + '.' + DEST.rsplit('/', 1)[1]
    assert context['assets'][0]['expected_lods'] == 1 and context['assets'][0]['bounds_tolerance_cm'] == 1
    assert all(abs(a - b * 100) < 1e-6 for a, b in zip(context['assets'][0]['expected_size_cm'], plan['dimensions_m']))
    return spec, plan, context


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
    verify = json.loads(verification.read_text())
    assert verify['passed'] is True and verify['mode'] == 'verify'
    assert verify['project'] == str(root)
    assert not verify['protected_changes'] and not verify['runtime_data_changes']
    source = root / SOURCE_REL
    _, plan, context = source_guard(source)
    assert sha(source / 'source_handoff.json') == verify['source_handoff_sha256']
    assert sha(root / 'Scripts/import_underfloor_surface.py') == verify['importer_sha256']
    assert sha(root / 'Scripts/publish_underfloor_surface.py') == verify['publisher_sha256']
    binding_guard(root, plan)
    assert set(verify['saved_package_sha256']) == PACKAGES
    current_assets = asset_pins(root)
    assert current_assets == verify['all_asset_sha256'], 'Asset set/content drift after saved verification'
    assert all(current_assets[p] == digest for p, digest in verify['saved_package_sha256'].items())
    baseline = verify['runtime_data_sha256']
    current = data_pins(root)
    expected = (json.dumps(context, indent=2) + '\n').encode()
    already = CONTEXT in current
    receipt = root / 'Saved/Art/underfloor_surface_publication.json'
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
        temporary = root / 'Saved/Art/underfloor_context.tmp'
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
    output = root / ('Saved/Art/underfloor_surface_publication.json' if args.apply
                     else 'Saved/Art/underfloor_surface_publication_check.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
