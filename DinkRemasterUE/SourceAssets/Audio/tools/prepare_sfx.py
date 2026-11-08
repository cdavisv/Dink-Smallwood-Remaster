#!/usr/bin/env python3
"""Rebuild the engine-ready SFX WAVs (and the measurable quality report) from the delivered MP3s.

Usage (from anywhere):
    python3 SourceAssets/Audio/tools/prepare_sfx.py            # convert + write quality_report.csv
    python3 SourceAssets/Audio/tools/prepare_sfx.py --no-report
    python3 SourceAssets/Audio/tools/prepare_sfx.py --only 01_quack_a 23_fire_b

Needs: Python 3 standard library and ffmpeg/ffprobe on PATH.

Input : SourceAssets/Audio/SFX/delivered/<slot>_<cue>_<a|b>.mp3   (never modified)
Output: SourceAssets/Audio/SFX/<slot>_<cue>_<a|b>.wav
          - 44.1 kHz, 16-bit PCM
          - one-shots: mono, leading silence trimmed, peak-normalised to -3 dBFS
          - loops (slots 23 and 34): stereo kept, NOT trimmed, NOT faded (that would break the
            seamless loop), peak-normalised to -3 dBFS with a single constant gain
        SourceAssets/Audio/SFX/quality_report.csv   (measurable checks only, see below)

Leading silence is defined as the time before the first sample whose absolute value reaches
-50 dBFS. One-shots keep PREROLL_MS of that lead-in so the first transient is not clipped hard.

The trim point and the gain are measured in Python on a float decode made by ffmpeg; the final
file is then rendered by ffmpeg (atrim + volume + pcm_s16le), so the result is deterministic.
"""
import argparse
import array
import csv
import math
import re
import subprocess
import sys
from pathlib import Path

SFX_DIR = Path(__file__).resolve().parents[1] / "SFX"
DELIVERED = SFX_DIR / "delivered"
LEDGER = Path(__file__).resolve().parents[2] / "asset_ledger.csv"
REPORT = SFX_DIR / "quality_report.csv"

RATE = 44100
LOOP_SLOTS = {"23", "34"}          # fire, save: seamless loops, stereo, untouched in time
TARGET_PEAK_DB = -3.0
SILENCE_DB = -50.0
PREROLL_MS = 2.0
SNAPPY_SLOTS = {                    # hits, clicks, swings: must start promptly
    "08", "09", "10", "11", "13", "20", "21", "36", "37", "41", "44", "45", "48",
}
# Flag thresholds (measurable only)
SILENT_PEAK_DB = -40.0
DURATION_TOLERANCE = 0.25
SNAPPY_MAX_LEAD_MS = 150.0
CLIP_SAMPLES = 3


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


MONO_PAN = "pan=mono|c0=0.5*c0+0.5*c1"     # explicit, identical in analysis and in the render


def decode_stereo(mp3):
    """Decode to interleaved float32 stereo at 44.1 kHz with ffmpeg (the MP3s are all stereo)."""
    out = run(["ffmpeg", "-v", "error", "-i", str(mp3), "-f", "f32le",
               "-ac", "2", "-ar", str(RATE), "-"]).stdout
    a = array.array("f")
    a.frombytes(out)
    return a


def to_mono(stereo):
    """Same maths as MONO_PAN: (L + R) / 2."""
    return array.array("f", ((l + r) * 0.5 for l, r in zip(stereo[0::2], stereo[1::2])))


def first_loud_frame(samples, channels):
    thr = 10 ** (SILENCE_DB / 20)
    for i, s in enumerate(samples):
        if abs(s) >= thr:
            return i // channels
    return len(samples) // channels


def volumedetect(path):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
                        "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    mean = re.search(r"mean_volume:\s*(-?[\d.]+|-inf) dB", p.stderr)
    peak = re.search(r"max_volume:\s*(-?[\d.]+|-inf) dB", p.stderr)
    f = lambda m: float(m.group(1)) if m else float("nan")
    return f(mean), f(peak)


def split_name(path):
    m = re.fullmatch(r"(\d\d)_(.+)_([ab])", path.stem)
    if not m:
        raise ValueError(f"unexpected file name {path.name}")
    return m.groups()


def convert(mp3):
    slot, cue, var = split_name(mp3)
    loop = slot in LOOP_SLOTS
    ch = 2 if loop else 1
    stereo = decode_stereo(mp3)
    samples = stereo if loop else to_mono(stereo)
    peak = max((abs(s) for s in samples), default=0.0)
    if peak <= 0:
        raise RuntimeError(f"{mp3.name}: digital silence, cannot normalise")
    gain = 10 ** (TARGET_PEAK_DB / 20) / peak          # constant linear gain, peak -> -3 dBFS
    start = 0
    if not loop:
        first = first_loud_frame(samples, ch)
        start = max(0, first - int(round(PREROLL_MS / 1000 * RATE)))
    wav = SFX_DIR / (mp3.stem + ".wav")
    af = [] if loop else [MONO_PAN]
    if start:
        af.append(f"atrim=start_sample={start}")
        af.append("asetpts=PTS-STARTPTS")
    af.append(f"volume={gain:.8f}")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-af", ",".join(af),
         "-ar", str(RATE), "-ac", str(ch), "-c:a", "pcm_s16le", "-map_metadata", "-1", str(wav)])
    return wav, start / RATE


def load_requested():
    """slot/cue -> requested duration (s) from the ledger's `parameters` column."""
    req = {}
    if not LEDGER.exists():
        return req
    with open(LEDGER, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = Path(row["asset_path"]).stem
            m = re.search(r"duration_s=([\d.]+)", row["parameters"])
            if m:
                req[name] = float(m.group(1))
    return req


def analyse(mp3, requested):
    slot, cue, var = split_name(mp3)
    loop = slot in LOOP_SLOTS
    ch = 2 if loop else 1
    stereo = decode_stereo(mp3)
    samples = stereo if loop else to_mono(stereo)       # what the WAV will contain
    measured = (len(stereo) // 2) / RATE
    mean_db, peak_db = volumedetect(mp3)                 # on the delivered MP3 as-is
    lead_ms = first_loud_frame(samples, ch) / RATE * 1000
    clip = sum(1 for s in stereo if abs(s) >= 0.999)     # on the MP3's own channels
    wav = SFX_DIR / (mp3.stem + ".wav")
    wav_peak = wav_dur = float("nan")
    if wav.exists():
        _, wav_peak = volumedetect(wav)
        wav_dur = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-of", "csv=p=0", str(wav)]).stdout.decode().strip())
    req = requested.get(mp3.stem)
    dev = (measured - req) / req if req else float("nan")
    flags = []
    if peak_db < SILENT_PEAK_DB:
        flags.append("effectively silent (peak < -40 dB)")
    if req and abs(dev) > DURATION_TOLERANCE:
        flags.append(f"duration off by {dev * 100:+.0f}%")
    if slot in SNAPPY_SLOTS and lead_ms > SNAPPY_MAX_LEAD_MS:
        flags.append(f"leading silence {lead_ms:.0f} ms on a snappy sound")
    if clip >= CLIP_SAMPLES or any(abs(s) > 1.0 for s in stereo):
        flags.append(f"clipping ({clip} samples at/near full scale)")
    return {
        "file": mp3.name, "slot": slot, "cue": cue, "variant": var,
        "type": "loop" if loop else ("oneshot_snappy" if slot in SNAPPY_SLOTS else "oneshot"),
        "requested_s": f"{req:.2f}" if req else "",
        "measured_s": f"{measured:.3f}",
        "duration_dev_pct": f"{dev * 100:+.1f}" if req else "",
        "peak_db": f"{peak_db:.1f}", "mean_db": f"{mean_db:.1f}",
        "leading_silence_ms": f"{lead_ms:.1f}",
        "clip_samples": clip,
        "wav_duration_s": f"{wav_dur:.3f}", "wav_peak_db": f"{wav_peak:.1f}",
        "flags": "; ".join(flags),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-report", action="store_true", help="convert only")
    ap.add_argument("--only", nargs="*", help="stems to process, e.g. 01_quack_a")
    args = ap.parse_args()

    files = sorted(DELIVERED.glob("*.mp3"))
    if args.only:
        files = [f for f in files if f.stem in set(args.only)]
    if not files:
        sys.exit(f"no mp3 files in {DELIVERED}")
    for f in files:
        wav, trimmed = convert(f)
        print(f"{f.name} -> {wav.name} (trimmed {trimmed * 1000:.0f} ms)")
    if not args.no_report and not args.only:
        requested = load_requested()
        rows = [analyse(f, requested) for f in files]
        with open(REPORT, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        flagged = [r for r in rows if r["flags"]]
        print(f"wrote {REPORT} ({len(rows)} rows, {len(flagged)} flagged)")


if __name__ == "__main__":
    main()
