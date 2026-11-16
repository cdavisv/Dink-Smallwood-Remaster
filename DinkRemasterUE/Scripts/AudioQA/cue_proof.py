#!/usr/bin/env python3
"""Proof that given effects SOUNDED at the moment the game cued them, in a run recorded by run_recorded.sh.

For every "Playing approved sound <asset> ... pitch=<p>" line and every "AUDIOQA sweep" line of the chosen assets, the source
take (from the selection manifest, resampled to the cue's pitch) is searched in the recording around the predicted moment by
cross-correlation. The report gives the found onset, the normalised match (1 = identical waveform), the RMS of the recording
over the take's length from that onset, and the RMS of the second before it (the floor: music, ambience). An event counts as
heard when its window is louder than its floor by at least 3 dB AND the match is at least 0.3 (positional effects are mixed
with music and ambience, so the match is below the sweep's ~0.99).

  python3 -I Scripts/AudioQA/cue_proof.py --log <run>/game.log --recording <run>/audio.raw --channels 6 \
      --asset SFX_09_punch --asset SFX_44_bow1 --asset SFX_49_bird1 --out <dir>/cue_proof.md
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audio_coverage as ac  # noqa: E402

PLAY = re.compile(r'Playing approved sound (\S+) sprite=(-?\d+) pitch=([0-9.]+)')
STEP = re.compile(r'Step [a-z] on SCR_\d+ at [^:]+: (\S+)')
BED = re.compile(r'Ambience bed \S+: (\S+) volume=')
SWEEP = re.compile(r'AUDIOQA sweep \d+/\d+ (\S+) (\S+) (\S+) volume=([0-9.]+) play=([0-9.]+)')
DRIFT = 0.011   # the SDL disk driver writes about 1.1 % more audio than wall-clock time (see README)


def source(path: Path, pitch: float, rate: int, seconds: float):
    import numpy as np
    af = f'asetrate=44100*{pitch:.4f},aresample={rate}' if abs(pitch - 1.0) > 1e-3 else f'aresample={rate}'
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-t', f'{seconds / max(pitch, 0.1):.3f}', '-af', af, '-ac', '1',
                        '-f', 'f32le', '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype='<f4')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--log', required=True); ap.add_argument('--recording', required=True)
    ap.add_argument('--rate', type=int, default=48000); ap.add_argument('--channels', type=int, default=6)
    ap.add_argument('--assets', default=str(ac.PROJECT), help='checkout with SourceAssets/Audio (LFS-pulled)')
    ap.add_argument('--asset', action='append', required=True, help='SoundWave name, e.g. SFX_09_punch, or a prefix ending in * (Step_*); repeatable')
    ap.add_argument('--out')
    a = ap.parse_args()
    root = Path(a.assets)
    man = json.loads((root / 'SourceAssets/Audio/selection_manifest.json').read_text())
    src_of = {x['name']: root / x['source'] for x in man['assets']}
    life = root / 'SourceAssets/Audio/Life'
    src_of.update({w.stem: w for w in life.glob('*.wav')} if life.is_dir() else {})
    want = lambda n: any(n == a or (a.endswith('*') and n.startswith(a[:-1])) for a in a_assets)
    a_assets = a.asset
    rec = ac.Recording(a.recording, a.rate, a.channels)
    t_open = ac.device_open_seconds(Path(a.log))
    if t_open is None:
        sys.exit('no SDL "Writing to file" line in the log: not a disk-driver recording')
    events = []
    for line in Path(a.log).read_text(errors='replace').splitlines():
        t = ac.log_seconds(line)
        if t is None:
            continue
        m = PLAY.search(line) or STEP.search(line) or BED.search(line)
        if m:
            name = m.group(1).rsplit('.', 1)[-1]
            pitch = float(m.group(3)) if m.re is PLAY else 1.0
            if want(name):
                events.append(dict(kind='game', name=name, t=t, sprite=int(m.group(2)) if m.re is PLAY else 0, pitch=pitch))
            continue
        m = SWEEP.search(line)
        if m:
            name = m.group(3).rsplit('.', 1)[-1]
            if want(name):
                events.append(dict(kind='sweep', name=name, t=t, sprite=None, pitch=1.0))
    rows = []
    for e in events:
        wall = e['t'] - t_open
        pred = wall * (1 + DRIFT)
        take = source(src_of[e['name']], e['pitch'], rec.rate, 3.0)
        dur = len(take) / rec.rate
        lo, hi = pred - 2.0 - 0.004 * wall, pred + 2.0 + 0.004 * wall + dur
        found, match = ac.xcorr_onset(rec, take, lo, hi)
        if found is None:
            rows.append(dict(e, wall=wall, onset=None, match=0.0, rms=None, floor=None, peak=None, heard=False)); continue
        rms = rec.rms_db(found, found + max(0.1, dur))
        floor = rec.rms_db(found - 1.05, found - 0.05)
        peak = rec.peak_db(found, found + max(0.1, dur))
        heard = rms is not None and floor is not None and rms >= floor + 3.0 and match >= 0.3
        rows.append(dict(e, wall=wall, onset=found, match=match, rms=rms, floor=floor, peak=peak, heard=heard))
    f = lambda v, p=1: '-' if v is None else f'{v:.{p}f}'
    out = ['| asset | cue | log time (s after device open) | onset in recording (s) | match | RMS dBFS | floor (1 s before) dBFS | peak dBFS | heard |',
           '|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        cue = 'sweep' if r['kind'] == 'sweep' else f"game, sprite {r['sprite']}, pitch {r['pitch']:.3f}"
        out.append(f"| {r['name']} | {cue} | {f(r['wall'])} | {f(r['onset'], 2)} | {f(r['match'], 3)} | {f(r['rms'])} | {f(r['floor'])} | "
                   f"{f(r['peak'])} | {'yes' if r['heard'] else 'NO'} |")
    text = '\n'.join(out) + '\n'
    print(text)
    for n in sorted({r['name'] for r in rows}):
        got = [r for r in rows if r['name'] == n]
        print(f"{n}: {len(got)} cue(s), heard {sum(r['heard'] for r in got)} ({sum(r['kind'] == 'game' for r in got)} in gameplay)")
    if a.out:
        Path(a.out).write_text(text)


if __name__ == '__main__':
    main()
