#!/usr/bin/env python3
"""Footstep and ambience-bed WAVs from the generated takes (ElevenLabs), replacing the procedural placeholders of synth_life.py.

  python3 -I Scripts/AudioQA/prepare_life_takes.py            # delivered MP3s + life_takes.json -> Life/*.wav + life_sources.json
  python3 -I Scripts/AudioQA/register_life_audio.py           # loudness gains (life.json) and ledger rows
  Scripts/AudioQA/import_life_audio.sh                        # editor import (one Unreal turn)

Input : SourceAssets/Audio/Life/delivered/<Step_surface|Bed_name>_<variant>.mp3 (as returned, never modified)
        SourceAssets/Audio/Life/life_takes.json: flow, prompts, every generation, its measurements and verdict, and the picks
        (`picks`: runtime name -> delivered stem).
Output: SourceAssets/Audio/Life/<runtime name>.wav, PCM16 44.1 kHz:
          - steps: mono; one footfall: the 10 ms window with the most energy is the hit, the take starts at the first sample
            within 120 ms before it that is no more than 30 dB under it (2 ms preroll), lasts STEP_S, 30 ms fade-out,
            peak -3 dBFS (a take holding two or three steps keeps the loudest one);
          - beds: stereo, untouched in time (the generator's seamless loop), one constant gain to -3 dBFS peak.
        SourceAssets/Audio/Life/life_sources.json with each file's provenance for register_life_audio.py.
"""
import json, subprocess, sys, wave
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LIFE = ROOT / 'SourceAssets/Audio/Life'
SR = 44100
STEP_S = 0.42
PEAK_DB = -3.0


def decode(mp3: Path, channels: int) -> np.ndarray:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(mp3), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, '<f4').reshape(-1, 2).astype('f8')
    return x.mean(1) if channels == 1 else x


def one_step(x: np.ndarray) -> np.ndarray:
    w = int(0.01 * SR)
    e = np.convolve(x * x, np.ones(w), 'valid')
    hit = int(np.argmax(e))
    floor = e[hit] * 10 ** (-30 / 10)
    lo = max(0, hit - int(0.12 * SR))
    start = lo + int(np.argmax(e[lo:hit + 1] >= floor))
    start = max(0, start - int(0.002 * SR))
    y = x[start:start + int(STEP_S * SR)].copy()
    if len(y) < int(STEP_S * SR):
        y = np.pad(y, (0, int(STEP_S * SR) - len(y)))
    f = int(0.03 * SR)
    y[-f:] *= np.linspace(1, 0, f)
    return y


def write(path: Path, x: np.ndarray) -> float:
    x = x / (np.max(np.abs(x)) or 1.0) * 10 ** (PEAK_DB / 20)
    pcm = np.round(np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1 if pcm.ndim == 1 else pcm.shape[1]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return len(pcm) / SR


def main() -> int:
    spec = json.loads((LIFE / 'life_takes.json').read_text())
    gens = {g['stem']: g for g in spec['generations']}
    rows = []
    for name, stem in spec['picks'].items():
        g = gens[stem]
        mp3 = LIFE / 'delivered' / f'{stem}.mp3'
        if g['kind'] == 'step':
            dur = write(LIFE / f'{name}.wav', one_step(decode(mp3, 1)))
            row = {'name': name, 'kind': 'step', 'surface': g['surface'], 'loop': False}
        else:
            dur = write(LIFE / f'{name}.wav', decode(mp3, 2))
            row = {'name': name, 'kind': 'bed', 'bed': g['bed'], 'loop': True}
        row.update({'duration_s': round(dur, 4), 'delivered': f'SourceAssets/Audio/Life/delivered/{stem}.mp3', 'generation': g})
        rows.append(row)
    order = {'step': 0, 'bed': 1}
    rows.sort(key=lambda r: (order[r['kind']], r['name']))
    meta = {'schema': 'dink-audio-life-sources/1', 'tool': 'ElevenLabs eleven_text_to_sound_v2 (Scripts/AudioQA/prepare_life_takes.py)',
            'flow_id': spec['flow_id'], 'generated_on': spec['generated_on'], 'licence': spec['licence'], 'files': rows,
            'not_picked': [g for s, g in gens.items() if s not in set(spec['picks'].values())]}
    (LIFE / 'life_sources.json').write_text(json.dumps(meta, indent=1, ensure_ascii=False) + '\n')
    print(f'PREPARE OK: {len(rows)} files from generated takes, {len(meta["not_picked"])} takes not picked')
    return 0


if __name__ == '__main__':
    sys.exit(main())
