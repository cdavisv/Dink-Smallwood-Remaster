"""Pure, owner-bound starting-house lighting authoring; no Unreal import or asset save.

The held Blender kit/layout remains geometry authority. LightingV1 replaces only
its historical lights list, preserving the accepted fireplace and all scene data.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import struct

PROFILE = 'SourceAssets/Art/Stonebrook/LightingV1/lighting.json'
WINDOW_NAMES = {'NorthWall_1', 'NorthWall_6', 'WestWall_2', 'WestWall_4', 'EastWall_2', 'EastWall_4'}
WINDOW_MESH = '/Game/Dink/Kits/Stonebrook/SM_Window_Limewash_2m_01.SM_Window_Limewash_2m_01'
SOURCE_FILES = {'SourceAssets/Art/tools/build_stonebrook.py',
                'SourceAssets/Art/Stonebrook/Export/Game/Dink/Kits/Stonebrook/SM_Window_Limewash_2m_01.fbx'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _number(value, positive=True):
    if type(value) not in (int, float):
        raise ValueError('Expected numeric runtime float scalar')
    try:
        number = float(value)
        # Match core LightNumber's finite double/range gate BEFORE conversion.
        if not math.isfinite(number) or abs(number) > float.fromhex('0x1.fffffep+127'):
            raise ValueError('Scalar is outside finite runtime float range')
        converted = struct.unpack('=f', struct.pack('=f', number))[0]
    except (OverflowError, struct.error) as error:
        raise ValueError('Scalar is outside finite runtime float range') from error
    invalid = (number <= 0 or converted <= 0) if positive else (number < 0 or converted < 0)
    if invalid:
        raise ValueError('Expected positive runtime float scalar' if positive else 'Expected nonnegative runtime float scalar')
    return converted


def _vector(value):
    if type(value) is not list or len(value) != 3:
        raise ValueError('Expected three-component vector')
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
        raise ValueError('Expected finite numeric vector')
    return value


def validate_profile(profile):
    if (profile.get('schema') != 'dink-house-lighting/1' or type(profile.get('screen')) is not int or
            profile['screen'] != 1 or profile.get('owner_manifest') != 'stonebrook.json'):
        raise ValueError('Lighting profile has wrong schema/owner')
    pins = profile['source_files_sha256']
    if set(pins) != SOURCE_FILES or any(type(h) is not str or len(h) != 64 or any(c not in '0123456789abcdef' for c in h) for h in pins.values()):
        raise ValueError('Require the exact original window source authorities')
    windows = profile['windows']
    if len(windows) != 6 or {x['expected_runtime']['name'] for x in windows} != WINDOW_NAMES:
        raise ValueError('Require six unique original window bindings')
    for binding in windows:
        row = binding['expected_runtime']
        source = binding['expected_source']
        if row['mesh'] != WINDOW_MESH or source['name'] != row['name'] or source['mesh'] != 'SM_Window_Limewash_2m_01':
            raise ValueError('Window source/mesh identity differs')
        _vector(row['world_cm']); _vector(row['rotation_deg']); _vector(row['scale'])
    daylight = profile['daylight']
    for key in ['kelvin', 'radius_cm', 'source_width_cm', 'source_height_cm', 'outside_wall_cm']:
        _number(daylight[key])
    _number(daylight['lumens_per_window'], positive=False)
    if daylight['outside_wall_cm'] != 30:
        raise ValueError('V1 source plane is reviewed at30cm outside the wall')
    aperture = profile['source_aperture']
    if aperture != dict(clear_width_unscaled_cm=88, clear_height_cm=136, center_local_cm=[100, 0, 185], frame_max_depth_cm=23):
        raise ValueError('Original aperture authority differs')
    if daylight['source_height_cm'] >= aperture['clear_height_cm'] or daylight['outside_wall_cm'] <= aperture['frame_max_depth_cm']:
        raise ValueError('Source does not clear the original frame')
    if len(profile['practical_points']) != 2 or len(profile['legacy_lights']) != 5 or profile['practical_points'] != profile['legacy_lights'][:2]:
        raise ValueError('Accepted practical lights are not retained')
    for row in profile['practical_points']:
        _vector(row['world_cm'])
        for key in ['kelvin', 'radius_cm']: _number(row[key])
        _number(row['lumens'], positive=False)
    # Complete derivation belongs in the early preflight, not just metadata output
    # after a native importer has already changed materials/packages.
    _derive_rows(profile)
    return profile


def load_profile(project):
    project = Path(project)
    profile = validate_profile(json.loads((project / PROFILE).read_text()))
    for relative, expected in profile['source_files_sha256'].items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Source authority must be project-relative')
        if hashlib.sha256((project / path).read_bytes()).hexdigest() != expected:
            raise ValueError('Window source authority changed: ' + relative)
    return profile


def validate_source_layout(profile, layout):
    validate_profile(profile)
    if layout.get('schema') != 'dink-art/1' or layout.get('screen') != 1:
        raise ValueError('Wrong source layout owner')
    expected = {b['expected_source']['name']: b['expected_source'] for b in profile['windows']}
    actual = [x for x in layout['elements'] if x.get('mesh') == 'SM_Window_Limewash_2m_01']
    if len(actual) != 6 or {x['name'] for x in actual} != set(expected):
        raise ValueError('Source window membership changed')
    if any(canonical(x) != canonical(expected[x['name']]) for x in actual):
        raise ValueError('Source window placement changed')


def preflight_source(profile, layout):
    """Validate source identity AND every derived runtime light before native work."""
    validate_source_layout(profile, layout)
    return _derive_rows(profile)


def _derive_rows(profile):
    result = copy.deepcopy(profile['practical_points'])
    d = profile['daylight']; aperture = profile['source_aperture']
    width = _number(d['source_width_cm']); height = _number(d['source_height_cm'])
    for binding in profile['windows']:
        w = binding['expected_runtime']; name = w['name']
        if width >= aperture['clear_width_unscaled_cm'] * w['scale'][0] or height >= aperture['clear_height_cm']:
            raise ValueError('Source rectangle exceeds scaled clear aperture')
        angle = math.radians(w['rotation_deg'][1])
        local = aperture['center_local_cm']
        center = [w['world_cm'][0] + local[0] * w['scale'][0] * math.cos(angle),
                  w['world_cm'][1] + local[0] * w['scale'][0] * math.sin(angle), local[2]]
        if name.startswith('North'): inward, yaw = [0, 1, 0], 90
        elif name.startswith('West'): inward, yaw = [1, 0, 0], 0
        else: inward, yaw = [-1, 0, 0], 180
        result.append(dict(name='Daylight_' + name, kind='rect',
                           world_cm=[center[i] - d['outside_wall_cm'] * inward[i] for i in range(3)],
                           rotation_deg=[0, yaw, 0], lumens=d['lumens_per_window'], kelvin=d['kelvin'],
                           radius_cm=d['radius_cm'], source_width_cm=d['source_width_cm'],
                           source_height_cm=d['source_height_cm']))
    for row in result:
        kind = row.get('kind', 'point')
        if kind not in ('point', 'rect'):
            raise ValueError('Unsupported generated runtime light kind')
        _vector(row['world_cm'])
        _number(row['lumens'], positive=False)
        for key in ['kelvin', 'radius_cm']: _number(row[key])
        if kind == 'rect':
            _vector(row['rotation_deg'])
            for key in ['source_width_cm', 'source_height_cm']: _number(row[key])
        elif 'source_width_cm' in row or 'source_height_cm' in row:
            raise ValueError('Point light cannot have rectangle dimensions')
    return result


def light_rows(profile, manifest):
    validate_profile(profile)
    if (manifest.get('schema') != 'dink-art/1' or type(manifest.get('screen')) is not int or
            manifest['screen'] != 1 or 'context' in manifest):
        raise ValueError('Wrong physical starting-house manifest')
    expected = {b['expected_runtime']['name']: b['expected_runtime'] for b in profile['windows']}
    actual = [x for x in manifest['elements'] if x.get('mesh') == WINDOW_MESH]
    if len(actual) != 6 or {x['name'] for x in actual} != set(expected):
        raise ValueError('Runtime window membership changed')
    if any(canonical(x) != canonical(expected[x['name']]) for x in actual):
        raise ValueError('Runtime window placement changed')
    return _derive_rows(profile)


def apply_lighting(profile, manifest, *, generated_from_legacy_layout=False):
    rows = light_rows(profile, manifest)
    current = manifest.get('lights')
    if not generated_from_legacy_layout:
        legacy = canonical(current) == canonical(profile['legacy_lights'])
        owned = (type(current) is list and len(current) == 8 and
                 canonical(current[:2]) == canonical(profile['practical_points']) and
                 all(type(x) is dict and x.get('kind') == 'rect' for x in current[2:]) and
                 {x.get('name') for x in current[2:]} == {x['name'] for x in rows[2:]})
        if not legacy and not owned:
            raise ValueError('Refuse to overwrite an unrelated lighting inventory')
    result = copy.deepcopy(manifest)
    result['lights'] = rows
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Write ONLY the owner manifest lighting rows after validation')
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    profile = load_profile(project)
    preflight_source(profile, json.loads((project / 'SourceAssets/Art/Stonebrook/room_layout.json').read_text()))
    path = project / 'Content/Dink/Data/Art' / profile['owner_manifest']
    old = json.loads(path.read_text()); new = apply_lighting(profile, old)
    if args.apply:
        path.write_text(json.dumps(new, indent=2) + '\n')
    elif canonical(old) != canonical(new):
        raise SystemExit('House lighting metadata differs; review profile, then --apply')
    print('HOUSE_LIGHTING_METADATA_PASS (native rendering/shadow/optics/performance unverified)')


if __name__ == '__main__':
    main()
