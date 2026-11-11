#!/usr/bin/env python3
"""Generate versioned fixed-foundation authority to an EXPLICIT output directory.

Reads ImportData screens/collision and already projected Gameplay inputs. Does
not generate native assets, alter a world, or implicitly write project Data.
"""
import argparse
from sync_gameplay_data import validate_editor_hard_flags
import csv
import hashlib
import json
import math
from pathlib import Path


def build(bundle: Path, gameplay: Path, *, selected_screens=None, layers_root=None):
    screens = json.loads((bundle / 'screens.json').read_text())['screens']
    collision = json.loads((bundle / 'collision.json').read_text())['screens']
    common = {}
    for name, required in [('frames.csv', {'seq','frame'}), ('placements.csv', {'origin','que'})]:
        raw = (gameplay/name).read_bytes()
        header = next(csv.reader(raw.decode().splitlines()))
        if not required.issubset(header):
            raise ValueError(f'{name}: missing migration columns')
        common[name] = hashlib.sha1(raw).hexdigest()
    if selected_screens is not None:
        screens = [screen for screen in screens if screen['screen'] in selected_screens]
        if {screen['screen'] for screen in screens} != set(selected_screens):
            raise ValueError('selected foundation screen missing from bundle')
    layers_root = gameplay if layers_root is None else layers_root
    output = {}
    for screen in screens:
        number = screen['screen']
        if type(number) is not int or not 1 <= number <= 768 or screen['id'] != f'SCR_{number:03d}':
            raise ValueError('invalid screen identity')
        corners = screen['corners']
        for key in ['nw','ne','sw','se']:
            if (not isinstance(corners[key], list) or len(corners[key]) != 2
                    or any(type(v) not in (int,float) or not math.isfinite(v) for v in corners[key])):
                raise ValueError('invalid screen corners')
        classes = collision[screen['id']]
        for role in ['fill_solid','fill_water']:
            for rect in classes.get(role, []):
                if (len(rect) != 4 or any(type(v) is not int for v in rect)
                        or not 0 <= rect[0] < rect[2] <= 600 or not 0 <= rect[1] < rect[3] <= 400):
                    raise ValueError('invalid fixed fill rectangle')
        layer = f'Hardness/SCR_{number:03d}_layers.json'
        raw = (layers_root/layer).read_bytes()
        packet = json.loads(raw)
        if (not isinstance(packet,dict) or packet.get('schema') != 'dinkex.runtime-hardness/2'
                or type(packet.get('width')) is not int or packet['width'] != 600
                or type(packet.get('height')) is not int or packet['height'] != 400
                or type(packet.get('vision')) is not int or packet['vision'] != 0
                or packet.get('skipped_tile_indices') != []):
            raise ValueError('base tile authority missing or unsupported')
        validate_editor_hard_flags(packet)
        prefix = f'/Game/Dink/RuntimeHardnessV1/SCR_{number:03d}/SM_SCR_{number:03d}_'
        def object_path(suffix):
            package = prefix + suffix
            return package + '.' + package.rsplit('/',1)[1]
        descriptor = dict(schema='dink-runtime-hardness-foundation/1', screen=number,
            corners=corners, height_cm=300, collision_source_hash=screen['collision_hash'],
            solid_mesh=object_path('FixedSolidV1'),
            low_mesh=object_path('FixedLowV1') if classes.get('fill_water') else None,
            fill_solid=classes.get('fill_solid',[]), fill_water=classes.get('fill_water',[]),
            gameplay_files_sha1={**common,layer:hashlib.sha1(raw).hexdigest()})
        output[f'SCR_{number:03d}.json']=(json.dumps(descriptor,sort_keys=True,indent=2)+'\n').encode()
    return output


def activation_plan(files, art_documents):
    """Required staging selection, NOT authorization to tag existing worlds.

    Include every art manifest used by that world. Native staging must also
    validate the applied authored registry before publishing any marker.
    """
    authored=set()
    for document in art_documents:
        if not isinstance(document,dict) or document.get('schema') != 'dink-art/1':
            raise ValueError('explicit dink-art/1 manifests required')
        values=document.get('authored_collision_screens',[])
        if not isinstance(values,list) or any(type(n) is not int or not 1<=n<=768 for n in values):
            raise ValueError('invalid authored collision screen list')
        authored.update(values)
    rows=[]
    for name,raw in sorted(files.items()):
        screen=json.loads(raw)['screen']; excluded=screen in authored
        rows.append(dict(screen=screen, descriptor=name,
            descriptor_sha256=hashlib.sha256(raw).hexdigest(),
            activation='excluded_authored_legacy' if excluded else 'requires_native_staging_verification',
            publish_marker=False))
    return dict(schema='dink-runtime-hardness-staging-plan/1',
        world_changed=False, native_verified=False, screens=rows)


def write_missing(destination: Path, files):
    for name, raw in files.items():
        target = destination/name
        if target.is_symlink() or (target.exists() and target.read_bytes() != raw):
            raise ValueError(f'refusing changed/external existing descriptor: {target}')
    destination.mkdir(parents=True,exist_ok=True)
    for name,raw in files.items():
        target=destination/name
        if not target.exists():target.write_bytes(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',required=True,type=Path)
    parser.add_argument('--gameplay',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args(); files=build(args.bundle,args.gameplay)
    if args.check:
        return 0 if all((args.out/n).is_file() and not (args.out/n).is_symlink() and (args.out/n).read_bytes()==b for n,b in files.items()) else 1
    write_missing(args.out,files)
    print(f'FOUNDATION DESCRIPTORS {len(files)}; native assets/world unchanged')
    return 0

if __name__=='__main__':raise SystemExit(main())
