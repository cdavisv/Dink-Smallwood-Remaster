"""Move every PulseAudio stream of processes whose command line contains MARK to SINK, as soon as it appears.
usage: move_game_stream.py <sink> <mark> <seconds>"""
import json, subprocess, sys, time
sink, mark, until = sys.argv[1], sys.argv[2], time.time() + float(sys.argv[3])
moved = set()
def cmdline(pid):
    try: return open('/proc/%s/cmdline' % pid, 'rb').read().replace(b'\0', b' ').decode(errors='replace')
    except OSError: return ''
while time.time() < until:
    try: inputs = json.loads(subprocess.run(['pactl', '-f', 'json', 'list', 'sink-inputs'], capture_output=True, text=True).stdout or '[]')
    except ValueError: inputs = []
    for s in inputs:
        pid = s.get('properties', {}).get('application.process.id')
        if s['index'] not in moved and pid and mark in cmdline(pid):
            r = subprocess.run(['pactl', 'move-sink-input', str(s['index']), sink])
            print('moved stream %s (pid %s, %s) -> %s rc=%d' % (s['index'], pid, s['properties'].get('application.name'), sink, r.returncode), flush=True)
            if r.returncode:  # could not move: mute it so nothing reaches the speakers
                subprocess.run(['pactl', 'set-sink-input-mute', str(s['index']), '1'])
                print('move failed, stream muted', flush=True)
            moved.add(s['index'])
    time.sleep(0.02)
