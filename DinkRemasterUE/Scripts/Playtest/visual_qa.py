#!/usr/bin/env python3
"""Private :189 visual QA. W routes are separate from explicitly labelled photo fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Scripts'))
import playtest_desktop as desktop
import playtest_interactions as interactions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--phase', choices=['routes', 'angles'], required=True)
    parser.add_argument('--label-prefix', default='', help='Keep successive readback/capture labels distinct')
    parser.add_argument('--readbacks', action='store_true', help='Record read-only runtime state alongside each route capture')
    args = parser.parse_args()
    assert not args.label_prefix or args.label_prefix.replace('-', '').replace('_', '').isalnum()
    args.out.mkdir(parents=True, exist_ok=True)
    receipt_path = args.out / (args.phase + '.json')
    assert not receipt_path.exists(), 'Preserve previous evidence'
    desktop.use_private_display()
    window = desktop.window()
    tools = Path(os.environ.get('DINK_QA_TOOLS', str(Path.home() / 'Work/DinkQA/Tools')))
    launch = json.loads((tools / 'game.json').read_text())
    assert window['pid'] == launch['game_pid']
    assert str(PROJECT / 'DinkRemaster.uproject') in launch['command']
    assert launch['log'] == str(args.log.resolve())
    actual_args = Path('/proc/%d/cmdline' % window['pid']).read_bytes().split(b'\0')
    assert str(PROJECT / 'DinkRemaster.uproject').encode() in actual_args
    desktop.focus(window)
    commands = []
    def command(value):
        output = interactions.command_output(value, args.log)
        commands.append({'command': value, 'output': output})
        return output
    def capture(label):
        desktop.console('dink.View 270 -18') if label == 'fresh-house' else None
        time.sleep(1)
        if args.readbacks:
            read_label = args.label_prefix + label
            assert 'QA_VISUAL_READ ' + read_label in command('py qa_v_read(%r)' % read_label)
        interactions.capture(args.out / (label + '.png'))
    command('dink.ScreenInfo 0')
    if args.readbacks:
        source = PROJECT / 'Scripts/Playtest/read_visual_qa.py'
        assert 'QA_VISUAL_READER_READY' in command('py exec(open(%r).read())' % str(source))
    if args.phase == 'routes':
        for _ in range(40):
            if not desktop.player(args.log)['move_ignored']:
                break
            desktop.run('wtype', '-k', 'space')
            time.sleep(.35)
        else:
            raise RuntimeError('Opening dialogue still owns input')
        initial = desktop.player(args.log)
        assert initial['screen'] == 1 and initial['radius'] == 28
        capture('fresh-house')
        desktop.walk_route(PROJECT / 'Scripts/Playtest/house_exit_art.json', args.log, args.out / 'actual-exit.json')
        capture('actual-outside')
        outside = desktop.player(args.log)
        assert outside['screen'] == 439
        desktop.walk_route(PROJECT / 'Scripts/Playtest/house_return_art.json', args.log, args.out / 'actual-return.json')
        capture('actual-return')
        final = desktop.player(args.log)
        assert final['screen'] == 1 and not final['move_ignored']
        result = {'initial': initial, 'outside': outside, 'final': final,
                  'method': 'Actual held W routes; no fixture teleports or property setters.'}
    else:
        source = PROJECT / 'Scripts/Playtest/read_visual_qa.py'
        assert 'QA_VISUAL_READER_READY' in command('py exec(open(%r).read())' % str(source))
        result = {'method': 'Normal camera rotation at actual returned doorway; no teleport.'}
        assert desktop.player(args.log)['screen'] == 1
        for yaw in [180, 225, 270, 315, 0, 45, 90, 135]:
            label = args.label_prefix + 'returned-%03d' % yaw
            command('dink.View %s -18' % yaw)
            time.sleep(1.5)
            assert 'QA_VISUAL_READ ' + label in command('py qa_v_read(%r)' % label)
            capture(label)
    result.update(window=window, launch=launch, commands=commands, phase=args.phase,
                  qa_driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if args.phase == 'angles' or args.readbacks:
        result['qa_reader_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(result, indent=2) + '\n')
    print('VISUAL_QA_%s_PASS' % args.phase.upper(), flush=True)


if __name__ == '__main__':
    main()
