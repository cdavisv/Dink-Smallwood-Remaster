#!/usr/bin/env python3
"""Rendered authored-prop interaction regression checks in an existing Dink game.

Fixture teleports establish exact locations. F/E/W inputs trigger the real game
rules; expected procedures are never invoked directly. Pickup cases require a
fresh, nonsaved session with the house pie and feed sack still present.
"""
import argparse
import json
import math
from pathlib import Path
import re
import time

import playtest_desktop as desktop


CASES = [
    ('table_far', [370, 231], 180, 'f', 's1-h1-4', 'hit', False),
    ('table_near', [350, 231], 180, 'f', 's1-h1-4', 'hit', True),
    ('table_away', [350, 231], 0, 'f', 's1-h1-4', 'hit', False),
    ('bed_far_hit', [280, 287], 180, 'f', 's1-h1-1', 'hit', False),
    ('bed_far_talk', [280, 287], 180, 'e', 's1-h1-1', 'talk', False),
    ('bed_near_hit', [245, 287], 180, 'f', 's1-h1-1', 'hit', True),
    ('bed_near_talk', [245, 287], 180, 'e', 's1-h1-1', 'talk', True),
]


def command_output(command, log):
    offset = log.stat().st_size
    desktop.console(command)
    with log.open() as handle:
        handle.seek(offset)
        return handle.read()


def story(log):
    text = command_output('dink.Story', log)
    entries = {}
    pattern = r'#(\d+) ([\w-]+)\.(\w+) sprite (\d+) screen (\d+) state (\d+) block (\d+) lines (\d+)'
    for match in re.finditer(pattern, text):
        entries[match[2]] = {'id': int(match[1]), 'procedure': match[3], 'sprite': int(match[4]),
                             'screen': int(match[5]), 'state': int(match[6]),
                             'block': int(match[7]), 'lines': int(match[8])}
    return {'instances': entries, 'log': text}


def advanced(before, after, script, procedure):
    old = before['instances'].get(script, {})
    new = after['instances'].get(script, {})
    return new.get('procedure') == procedure and (
        old.get('id') != new.get('id') or new.get('lines', 0) > old.get('lines', 0))


def setup(point, yaw, log):
    # A clear northern aisle is used only to align the actual pawn with W. A
    # camera change alone does not turn a third-person pawn's body.
    desktop.console('dink.Goto 1 370 170')
    desktop.console(f'dink.View {yaw} -18')
    desktop.run('wtype', '-P', 'w', '-s', '400', '-p', 'w')
    time.sleep(.3)
    desktop.console(f'dink.Goto 1 {point[0]} {point[1]}')
    state = desktop.player(log)
    if state['screen'] != 1 or math.dist(state['map'], point) > 3:
        raise RuntimeError(f'Could not establish fixture at {point}: {state}')
    if state['move_ignored']:
        raise RuntimeError(f'Player is frozen at fixture: {state}')
    return state


def capture(path):
    w = desktop.window()
    x, y = w['at']; width, height = w['size']
    desktop.run('grim', '-g', f'{x},{y} {width}x{height}', str(path.resolve()))


def close_unrelated_menu(snapshot):
    choices = re.findall(r'  menu (\d+)\.', snapshot['log'])
    if choices:
        desktop.console(f'dink.Choose {choices[-1]}')
        time.sleep(.3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, default=Path('/tmp/dink-remaster-playtest.log'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--private-display', choices=[':189'])
    parser.add_argument('--private-authority', default='/tmp/dink-qa-tools/xauthority')
    parser.add_argument('--only', help='Comma-separated case IDs; use props for all F/E cases or pickups for the pickup cases.')
    parser.add_argument('--phase', default='after', help='Label for the recorded evidence; expectations remain the corrected behavior.')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.private_display:
        desktop.use_private_display(args.private_display, args.private_authority)
        if args.log == Path('/tmp/dink-remaster-playtest.log'):
            args.log = Path('/tmp/dink-qa-private.log')
    desktop.focus(desktop.window())
    selected = set(args.only.split(',')) if args.only else None
    run_props = selected is None or 'props' in selected
    run_pickups = selected is None or 'pickups' in selected
    receipt = {'input_backend': 'private Xvfb:189/XTest' if args.private_display else 'selected Wayland game/wtype', 'log_path': str(args.log), 'phase': args.phase, 'fixture_setup': 'Teleport to exact positions; real F/E/W actions; no expected script called directly.', 'cases': []}

    def save():
        receipt['result'] = 'PASS' if receipt['cases'] and all(c['result'] == 'PASS' for c in receipt['cases']) else 'FAIL'
        (args.out / 'results.json').write_text(json.dumps(receipt, indent=2) + '\n')

    try:
        if run_pickups:
            inventory = command_output('dink.Inventory', args.log)
            pie = command_output('dink.Origin S001_P51', args.log)
            if 'item-pig' in inventory or 'hidden=1' in pie:
                raise RuntimeError('Pickup cases require a fresh game with uncollected feed and pie; use --only props for a used session.')

        for case_id, point, yaw, key, target, procedure, expected in CASES:
            if not run_props and case_id not in (selected or set()):
                continue
            state = setup(point, yaw, args.log)
            before = story(args.log)
            action_offset = args.log.stat().st_size
            desktop.run('wtype', '-k', key)
            time.sleep(.3)
            after = story(args.log)
            with args.log.open() as handle:
                handle.seek(action_offset)
                action_log = handle.read()
            observed = advanced(before, after, target, procedure)
            input_verified = advanced(before, after, 'item-fst', 'use') if key == 'f' else 'talk:' in action_log
            image_path = args.out / f'{case_id}.png'
            capture(image_path)
            record = {'id': case_id, 'player': state, 'key': key, 'target_script': target,
                      'procedure': procedure, 'expected_target_called': expected,
                      'observed_target_called': observed, 'input_verified': input_verified,
                      'attack_input_verified': input_verified if key == 'f' else None, 'action_log': action_log,
                      'before': before, 'after': after, 'screenshot': str(image_path),
                      'result': 'PASS' if observed == expected and input_verified else 'FAIL'}
            receipt['cases'].append(record)
            print(f'{case_id}: {record["result"]}', flush=True)
            close_unrelated_menu(after)
            save()

        if run_pickups:
            far = setup([423, 130], 0, args.log)
            inventory = command_output('dink.Inventory', args.log)
            receipt['cases'].append({'id': 'sack_far', 'player': far, 'expected_collected': False,
                'observed_collected': 'item-pig' in inventory, 'inventory_log': inventory,
                'result': 'PASS' if 'item-pig' not in inventory else 'FAIL'})
            capture(args.out / 'sack_far.png')
            desktop.run('wtype', '-P', 'w', '-s', '200', '-p', 'w')
            time.sleep(.4)
            near = desktop.player(args.log)
            inventory = command_output('dink.Inventory', args.log)
            receipt['cases'].append({'id': 'sack_near', 'player': near, 'expected_collected': True,
                'observed_collected': 'item-pig' in inventory, 'inventory_log': inventory,
                'result': 'PASS' if 'item-pig' in inventory else 'FAIL'})
            capture(args.out / 'sack_near.png')
            desktop.run('wtype', '-P', 'w', '-s', '350', '-p', 'w')
            time.sleep(.4)
            passed = desktop.player(args.log)
            inventory = command_output('dink.Inventory', args.log)
            once = inventory.count(': item-pig') == 1
            receipt['cases'].append({'id': 'collected_sack_space_walk', 'player': passed,
                'expected': 'walk past the removed sack without an invisible collider; one feed item',
                'inventory_log': inventory, 'result': 'PASS' if passed['map'][0] > 449 and once else 'FAIL'})
            capture(args.out / 'collected_sack_space_walk.png')
            save()

            setup([302, 170], 90, args.log)
            desktop.console('dink.Fact life 5')
            desktop.run('wtype', '-P', 'w', '-s', '150', '-p', 'w')
            time.sleep(.3)
            desktop.run('wtype', '-P', 'w', '-s', '90', '-p', 'w')
            time.sleep(.3)
            far = desktop.player(args.log)
            inventory = command_output('dink.Inventory', args.log)
            health = int(re.search(r'life (\d+)/', inventory)[1])
            receipt['cases'].append({'id': 'pie_far', 'player': far, 'expected_health': 5,
                'observed_health': health, 'inventory_log': inventory,
                'result': 'PASS' if health == 5 else 'FAIL'})
            capture(args.out / 'pie_far.png')
            desktop.run('wtype', '-P', 'w', '-s', '400', '-p', 'w')
            time.sleep(.4)
            near = desktop.player(args.log)
            inventory = command_output('dink.Inventory', args.log)
            health = int(re.search(r'life (\d+)/', inventory)[1])
            receipt['cases'].append({'id': 'pie_near', 'player': near, 'expected_health': 8,
                'observed_health': health, 'inventory_log': inventory,
                'result': 'PASS' if health == 8 else 'FAIL'})
            capture(args.out / 'pie_near.png')
            desktop.console('dink.Fact life 10')
            save()
    except (RuntimeError, SystemExit) as error:
        receipt['cases'].append({'id': 'fixture_error', 'result': 'FAIL', 'error': str(error)})
        save()
        raise
    save()
    print(f'INTERACTIONS {receipt["result"]}: {len(receipt["cases"])} cases; {args.out / "results.json"}')
    if receipt['result'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
