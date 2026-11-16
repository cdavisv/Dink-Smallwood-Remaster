#!/usr/bin/env python3
"""Publish the footstep and ambience-bed sources: measure loudness, write the runtime table and the ledger rows.

  python3 -I Scripts/AudioQA/register_life_audio.py           # after synth_life.py (or after replacing a WAV by a generated take)
  Scripts/AudioQA/import_life_audio.sh                         # editor import of the WAVs into /Game/Dink/Audio/Life (Unreal turn)

Writes Content/Dink/Data/Audio/life.json (read by UDinkAudioLifeSubsystem): per surface the step takes, per bed its loop, each
with a gain that brings its integrated loudness (ffmpeg ebur128) to the category target, so a replaced take needs no code change.
Adds or refreshes one SourceAssets/asset_ledger.csv row per file (status `placeholder` for synthesised ones).
"""
import csv, hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'SourceAssets/Audio/Life'
OUT = ROOT / 'Content/Dink/Data/Audio/life.json'
LEDGER = ROOT / 'SourceAssets/asset_ledger.csv'
TARGET_LUFS = {'step': -26.0, 'bed': -30.0}


def lufs(path: Path) -> float:
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = re.findall(r'I:\s+(-?[0-9.]+) LUFS', r.stderr)
    if not m:
        raise SystemExit(f'REGISTER FAILED: no loudness for {path}')
    return float(m[-1])


def main() -> int:
    meta = json.loads((SRC / 'life_sources.json').read_text())
    steps, beds, rows = {}, {}, []
    for f in meta['files']:
        wav = SRC / (f['name'] + '.wav')
        level = lufs(wav)
        gain = round(min(4.0, 10 ** ((TARGET_LUFS[f['kind']] - level) / 20)), 3)
        entry = {'asset': f"/Game/Dink/Audio/Life/{f['name']}.{f['name']}", 'gain': gain, 'lufs': level}
        if f['kind'] == 'step':
            steps.setdefault(f['surface'], []).append(entry)
        else:
            beds[f['bed']] = entry
        rows.append((wav, f, level))
    runtime = {
        'schema': 'dink-audio-life/1',
        'note': 'Written by Scripts/AudioQA/register_life_audio.py. gain brings each take to its category loudness (steps -26 LUFS, beds -30 LUFS at the file); volumes are the category faders.',
        'volumes': {'steps': 0.55, 'beds': 0.5},
        'steps': steps,
        'beds': beds,
        'import': [{'name': f['name'], 'source': f"SourceAssets/Audio/Life/{f['name']}.wav", 'loop': f['loop'], 'duration_s': f['duration_s']} for _, f, _ in rows],
    }
    OUT.write_text(json.dumps(runtime, indent=1, sort_keys=True) + '\n')
    # Ledger: replace this script's rows, keep everything else byte for byte.
    with open(LEDGER, newline='', encoding='utf-8') as fh:
        reader = csv.reader(fh)
        header = next(reader)
        kept = [r for r in reader if not (r and r[0].startswith('SourceAssets/Audio/Life/'))]
    tool = meta.get('tool', '')
    new = []
    for wav, f, level in rows:
        digest = hashlib.sha256(wav.read_bytes()).hexdigest()
        placeholder = 'placeholder' in tool
        what = f"footstep, {f['surface']}" if f['kind'] == 'step' else f"ambience bed, {f['bed']} (seamless loop)"
        new.append([f"SourceAssets/Audio/Life/{wav.name}", f"Content/Dink/Audio/Life/{f['name']}.uasset", 'sfx',
                    'none (1997 has no footsteps or ambience beds)', 'Original project work' if placeholder else 'see notes', tool, '',
                    f"loudness {level:.1f} LUFS; loop={str(f['loop']).lower()}", '', '', '2026-11-15', '0',
                    'Project-authored source (procedural synthesis, no samples)' if placeholder else '', digest,
                    f"{f['duration_s']:.3f}", 'placeholder' if placeholder else 'candidate',
                    f"{what}; procedural placeholder until a generated take replaces it (FABLE_ART_QUEUE AU-01/AU-02); ElevenLabs was not attached to the session that made it"])
    with open(LEDGER, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(header); w.writerows(kept); w.writerows(new)
    print(f'REGISTER OK: {len(rows)} files, life.json and {len(new)} ledger rows')
    return 0


if __name__ == '__main__':
    sys.exit(main())
