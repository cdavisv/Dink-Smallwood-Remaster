#!/usr/bin/env python3
"""Rebuild the engine-ready music WAVs (and the measurable quality report) from the delivered MP3s.

Usage (from anywhere):
    python3 SourceAssets/Audio/tools/prepare_music.py            # convert + write quality_report.csv
    python3 SourceAssets/Audio/tools/prepare_music.py --no-report
    python3 SourceAssets/Audio/tools/prepare_music.py --only 01_title
    python3 SourceAssets/Audio/tools/prepare_music.py --loops-only   # rebuild only the loop files + loop_report.csv
    python3 SourceAssets/Audio/tools/prepare_music.py --no-loops     # skip the loop files

Needs: Python 3, numpy, and ffmpeg/ffprobe on PATH.

Input : SourceAssets/Audio/Music/delivered/<nn>_<cue>.mp3   (never modified)
Output: SourceAssets/Audio/Music/<nn>_<cue>.wav
          - 44.1 kHz, 16-bit PCM, stereo
          - NOT trimmed and NOT faded (that would break a loop), peak-normalised to -3 dBFS
            with a single constant gain
        SourceAssets/Audio/Music/quality_report.csv   (measurable checks only, see below)
        SourceAssets/Audio/Music/loops/<nn>_<cue>_loop.wav + loop_report.csv   (loop cues only, derived
          from the engine-ready WAV, see "Loop files" below)

The gain is measured in Python on a float decode made by ffmpeg; the final file is rendered by
ffmpeg (volume + pcm_s16le), so the result is deterministic.

Loop check (loop cues only): compares the first and last LOOP_WINDOW_MS of the file. The seam is
reported "clean" only if (a) the head and tail RMS differ by no more than LOOP_RMS_TOL_DB, (b) both
windows are above the silence floor (a fade-in / fade-out to silence is not a clean loop) and
(c) the jump between the last sample and the first sample, on the worse channel, is no more than
LOOP_JUMP_MAX of full scale. This is a measurement of the file edges only: it cannot tell whether
the music is musically loopable (a bar-aligned seam), so a person must still audition the loop.

Loop files (loop cues only; derived from the engine-ready WAV, never from delivered/):
  1. trim leading/trailing near-silence (< TRIM_SILENCE_DB RMS over 20 ms windows) and any monotonic
     fade-in / fade-out ramp at the ends (the 200 ms-smoothed envelope rising from >= 6 dB under the
     steady level to within 3 dB of it, with no dip over RAMP_TOL_DB, at most MAX_FADE_S long);
  2. estimate tempo from the onset-strength autocorrelation (numpy STFT spectral flux), refine period
     and beat phase with a comb fit, and pick a loop start near the beginning and a loop end an integer
     number of bars later near the end (bar = 3 or 4 beats; both are tried, the one the autocorrelation prefers is favoured), snapped to
     the beat grid, nudged by a few ms to a low-jump sample and aligned to the envelope of the head.
     Candidates are ranked by log-spectral difference over the crossfade region, level step at the
     seam and envelope correlation. With no clear autocorrelation peak (TEMPO_MIN_PEAK / TEMPO_MIN_Z) it
     falls back to zero-crossing points with the smallest 100 ms spectral difference;
  3. the file is audio[start:end] whose last CROSSFADE_S seconds are an equal-power crossfade of the
     tail audio[end-cf:end] with the material that originally preceded the start, audio[start-cf:start].
     The last sample of the file is then the sample that really preceded the first one, so the
     wrap-around has no click and no level step;
  4. the same loop_check() as above is re-run on the 16-bit loop file; the best candidates are tried
     in order until one passes. Results go to loop_report.csv.
This makes the seam technically clean only; nobody has checked by ear that it is musically continuous.
"""
import argparse
import csv
import math
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

MUSIC_DIR = Path(__file__).resolve().parents[1] / "Music"
DELIVERED = MUSIC_DIR / "delivered"
REPORT = MUSIC_DIR / "quality_report.csv"
LOOP_DIR = MUSIC_DIR / "loops"
LOOP_REPORT = MUSIC_DIR / "loop_report.csv"

RATE = 44100
TARGET_PEAK_DB = -3.0
LOOP_WINDOW_MS = 50.0
LOOP_RMS_TOL_DB = 6.0
LOOP_JUMP_MAX = 0.10
SILENCE_FLOOR_DB = -50.0
CLIP_LEVEL = 0.999
SILENT_PEAK_DB = -40.0
DURATION_TOLERANCE = 0.25
CLIP_SAMPLES = 3

# loop-file construction
TRIM_SILENCE_DB = -45.0      # RMS over TRIM_WIN_MS windows below this is "silence"
TRIM_WIN_MS = 20.0
SMOOTH_WIN = 10              # envelope smoothing for fade detection, in TRIM_WIN_MS windows (200 ms)
RAMP_TOL_DB = 2.0            # largest dip allowed below the running maximum inside a fade ramp
RAMP_START_DB = 6.0          # a fade must start at least this far under the steady level
RAMP_END_DB = 3.0            # ... and is over once within this of the steady level
MAX_FADE_S = 15.0            # a ramp longer than this is a musical build, not a fade
CROSSFADE_S = 1.0
SHORT_USABLE_S = 30.0        # below this much usable audio the crossfade shrinks proportionally
MIN_BPM, MAX_BPM, PRIOR_BPM, PRIOR_OCT = 50.0, 220.0, 110.0, 1.0
TEMPO_MIN_PEAK = 0.25        # normalised autocorrelation peak needed for a "clear" tempo
TEMPO_MIN_Z = 2.5            # ... and its z-score against the other lags
HEAD_SEARCH_S, TAIL_SEARCH_S = 10.0, 12.0
FINE_SHIFT_MS = 30           # end-point alignment search against the head envelope
JUMP_SEARCH = 350            # samples either side of a start point searched for a low-jump sample
TOP_K = 8                    # candidates actually built and checked per path

# cue number -> (requested duration in seconds, loop?)   (cue list of the 7 Nov 2026 music batch)
CUES = {
    "01": (90, False), "02": (60, True), "03": (60, True), "04": (60, True), "05": (60, True),
    "06": (60, True), "07": (60, True), "08": (60, True), "09": (60, True), "10": (60, True),
    "11": (90, False), "12": (60, True), "13": (60, True), "14": (60, True), "15": (60, True),
    "16": (60, True), "17": (60, True), "18": (60, True), "19": (60, True), "20": (60, True),
    "21": (90, True), "22": (60, False), "23": (12, False), "24": (15, False), "25": (15, False),
    "26": (20, False), "27": (15, False), "28": (60, False),
}


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True)


def decode_stereo(path):
    """Decode to float32 stereo (frames, 2) at 44.1 kHz with ffmpeg."""
    out = run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le",
               "-ac", "2", "-ar", str(RATE), "-"]).stdout
    return np.frombuffer(out, dtype="<f4").reshape(-1, 2)


def db(x):
    return 20 * math.log10(x) if x > 0 else float("-inf")


def split_name(path):
    m = re.fullmatch(r"(\d\d)_(.+)", path.stem)
    if not m:
        raise ValueError(f"unexpected file name {path.name}")
    return m.groups()


def gain_for(samples):
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if peak <= 0:
        raise RuntimeError("digital silence, cannot normalise")
    return 10 ** (TARGET_PEAK_DB / 20) / peak


def convert(mp3):
    gain = gain_for(decode_stereo(mp3))
    wav = MUSIC_DIR / (mp3.stem + ".wav")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-af", f"volume={gain:.8f}",
         "-ar", str(RATE), "-ac", "2", "-c:a", "pcm_s16le", "-map_metadata", "-1", str(wav)])
    return wav


def loop_check(x, loop):
    """x: float stereo frames as they will sit in the WAV. Returns (clean_text, head_db, tail_db, jump)."""
    n = int(round(LOOP_WINDOW_MS / 1000 * RATE))
    if len(x) < 2 * n:
        return "n/a (too short)", float("nan"), float("nan"), float("nan")
    rms = lambda a: float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
    head, tail = db(rms(x[:n])), db(rms(x[-n:]))
    jump = float(np.max(np.abs(x[0] - x[-1])))
    if not loop:
        return "n/a (one-shot)", head, tail, jump
    reasons = []
    if min(head, tail) < SILENCE_FLOOR_DB:
        reasons.append("edge near silence (fade)")
    elif abs(head - tail) > LOOP_RMS_TOL_DB:
        reasons.append(f"head/tail RMS differ {abs(head - tail):.1f} dB")
    if jump > LOOP_JUMP_MAX:
        reasons.append(f"sample jump {jump:.2f} FS")
    return ("yes" if not reasons else "NO: " + "; ".join(reasons)), head, tail, jump


# ---------------------------------------------------------------- loop files

def window_db(x, w):
    n = len(x) // w
    p = (x[:n * w].astype(np.float64) ** 2).reshape(n, w, x.shape[1]).mean(axis=(1, 2))
    return 10 * np.log10(np.maximum(p, 1e-12))


def _ramp_len(sm_db, steady):
    """Windows to drop from the start of sm_db if it begins with a monotonic ramp, else 0."""
    reach = np.nonzero(sm_db >= steady - RAMP_END_DB)[0]
    j = int(reach[0]) if reach.size else 0
    if j == 0 or j * TRIM_WIN_MS / 1000 > MAX_FADE_S or sm_db[0] > steady - RAMP_START_DB:
        return 0
    seg = sm_db[:j + 1]
    if (np.maximum.accumulate(seg) - seg).max() > RAMP_TOL_DB:
        return 0
    return j


def trim_ends(x):
    """Return (u0, u1, info): usable sample range after silence and fade trimming."""
    w = int(round(TRIM_WIN_MS / 1000 * RATE))
    e = window_db(x, w)
    loud = np.nonzero(e >= TRIM_SILENCE_DB)[0]
    if loud.size == 0:
        raise RuntimeError("nothing above the silence threshold")
    i0, i1 = int(loud[0]), int(loud[-1])
    power = 10 ** (e[i0:i1 + 1] / 10)
    pp = np.pad(power, (SMOOTH_WIN // 2 - 1, SMOOTH_WIN // 2), mode="edge")
    sm = 10 * np.log10(np.maximum(np.convolve(pp, np.ones(SMOOTH_WIN) / SMOOTH_WIN, mode="valid"), 1e-12))
    n = len(sm)
    steady = float(np.median(sm[n // 4: 3 * n // 4]))
    jh, jt = _ramp_len(sm, steady), _ramp_len(sm[::-1], steady)
    u0, u1 = (i0 + jh) * w, (i1 + 1 - jt) * w
    ms = lambda k: k * w / RATE * 1000
    return u0, u1, {"head_ms": ms(i0 + jh), "tail_ms": (len(x) - u1) / RATE * 1000,
                    "head_silence_ms": ms(i0), "head_fade_ms": ms(jh),
                    "tail_silence_ms": (len(x) - (i1 + 1) * w) / RATE * 1000, "tail_fade_ms": ms(jt),
                    "steady_db": steady}


ONSET_FFT, ONSET_HOP = 1024, 512


def onset_env(mono):
    win = np.hanning(ONSET_FFT)
    nfr = 1 + (len(mono) - ONSET_FFT) // ONSET_HOP
    idx = np.arange(ONSET_FFT)[None, :] + ONSET_HOP * np.arange(nfr)[:, None]
    mag = np.abs(np.fft.rfft(mono[idx] * win, axis=1))[:, 1:190]       # up to about 8 kHz
    s = np.log1p(10 * mag)
    flux = np.concatenate([[0.0], np.maximum(s[1:] - s[:-1], 0).sum(axis=1)])
    k = 43                                                              # about 0.5 s local mean
    local = np.convolve(np.pad(flux, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid")
    return np.maximum(flux - local, 0.0)


def estimate_tempo(env):
    """Onset-strength autocorrelation. Returns (lag_frames or None, peak, z, ac)."""
    fps = RATE / ONSET_HOP
    e = env - env.mean()
    n = len(e)
    f = np.fft.rfft(e, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n]
    if ac[0] <= 0:
        return None, 0.0, 0.0, ac
    ac = ac / ac[0] * n / (n - np.arange(n))
    lo, hi = int(fps * 60 / MAX_BPM), int(np.ceil(fps * 60 / MIN_BPM))
    lags = np.arange(lo, hi + 1)
    seg = ac[lo:hi + 1]
    bpm = 60 * fps / lags
    wgt = np.exp(-0.5 * (np.log2(bpm / PRIOR_BPM) / PRIOR_OCT) ** 2)
    peaks = np.nonzero((seg[1:-1] >= seg[:-2]) & (seg[1:-1] >= seg[2:]))[0] + 1
    if peaks.size == 0:
        return None, 0.0, 0.0, ac
    b = int(peaks[np.argmax(seg[peaks] * wgt[peaks])])
    peak = float(seg[b])
    z = (peak - float(seg.mean())) / (float(seg.std()) + 1e-12)
    l0, y0, y1, y2 = lags[b], seg[b - 1], seg[b], seg[b + 1]
    den = y0 - 2 * y1 + y2
    lag = l0 + (0.5 * (y0 - y2) / den if den != 0 else 0.0)
    ok = peak >= TEMPO_MIN_PEAK and z >= TEMPO_MIN_Z
    return (float(lag) if ok else None), peak, z, ac


def refine_beats(env, lag0):
    """Comb fit of period (frames, +-3 percent) and phase. Returns (period_frames, phase_frames)."""
    t = np.arange(len(env), dtype=np.float64)
    best = (-1.0, lag0, 0.0)
    for P in lag0 * np.linspace(0.97, 1.03, 121):
        for ph in np.arange(0.0, P, 0.25):
            pos = np.arange(ph, len(env) - 1, P)
            sc = float(np.interp(pos, t, env).mean())
            if sc > best[0]:
                best = (sc, P, ph)
    return best[1], best[2]


def band_matrix(mono, ends, nwin):
    """Log band spectrum (dB, 48 log-spaced bands 60 Hz - 16 kHz) of the nwin samples ending at each position."""
    win = np.hanning(nwin)
    edges = np.unique(np.round(np.geomspace(60, 16000, 49) / RATE * nwin).astype(int))
    out = np.empty((len(ends), len(edges) - 1))
    for i, p in enumerate(ends):
        sp = np.abs(np.fft.rfft(mono[p - nwin:p] * win)) ** 2
        out[i] = 10 * np.log10(np.add.reduceat(sp, edges[:-1])[:len(edges) - 1] + 1e-9)
    return out


def rms_db_of(a):
    return db(float(np.sqrt(np.mean(a.astype(np.float64) ** 2))))


def seam_pair(x, s):
    """(level diff dB, jump) across the wrap-around, given that the file will end with x[s-1]."""
    n = int(round(LOOP_WINDOW_MS / 1000 * RATE))
    return abs(rms_db_of(x[s:s + n]) - rms_db_of(x[s - n:s])), float(np.max(np.abs(x[s] - x[s - 1])))


def fine_env(mono):
    hop, win = 44, 176                                                  # 1 ms hop, 4 ms RMS
    c = np.concatenate([[0.0], np.cumsum(mono.astype(np.float64) ** 2)])
    i = np.arange((len(mono) - win) // hop + 1) * hop
    return np.sqrt((c[i + win] - c[i]) / win)


def low_jump_start(x, s):
    lo, hi = max(1, s - JUMP_SEARCH), s + JUMP_SEARCH + 1
    j = np.max(np.abs(np.diff(x[lo - 1:hi], axis=0)), axis=1)         # j[k] = jump into sample lo+k
    return int(lo + np.argmin(j))


def build_loop(x, s, e, cfn):
    """x[s:e] with its last cfn samples crossfaded (equal power) with the audio that preceded s."""
    out = x[s:e].astype(np.float64).copy()
    t = (np.arange(cfn) + 0.5) / cfn
    fo, fi = np.cos(np.pi / 2 * t)[:, None], np.sin(np.pi / 2 * t)[:, None]
    out[-cfn:] = x[e - cfn:e] * fo + x[s - cfn:s] * fi
    peak = float(np.max(np.abs(out)))
    out *= 10 ** (TARGET_PEAK_DB / 20) / peak
    return np.clip(np.round(out * 32767), -32768, 32767).astype(np.int16)


def tempo_candidates(x, mono, u0, u1, cfn, ctx):
    """Beat-grid candidates [(cost, s, e, info)] or ([], reason)."""
    env = onset_env(mono[u0:u1])
    lag, peak, z, ac = estimate_tempo(env)
    ctx["tempo_peak"], ctx["tempo_z"] = peak, z
    if lag is None:
        return [], f"no clear tempo peak (autocorr {peak:.2f}, z {z:.1f})"
    P, ph = refine_beats(env, lag)
    ctx["bpm"] = 60 * (RATE / ONSET_HOP) / P
    Ps = P * ONSET_HOP
    acat = lambda k: float(np.interp(k * P, np.arange(len(ac)), ac))
    meter = 3 if acat(3) > 1.1 * acat(4) else 4
    ctx["meter"] = meter
    beats = u0 + (ph + np.arange(0, len(env) / P + 1) * P) * ONSET_HOP + ONSET_FFT // 2
    fe = fine_env(mono)
    ncf = cfn // 44
    usable = u1 - u0
    head_s, tail_s = min(HEAD_SEARCH_S * RATE, 0.2 * usable), min(TAIL_SEARCH_S * RATE, 0.25 * usable)
    nwin = int(0.1 * RATE)
    ntile = max(1, cfn // nwin)
    cands = []
    for b in beats[(beats >= u0 + cfn) & (beats <= u0 + cfn + head_s)]:
        s = low_jump_start(x, int(round(b)))
        if s - cfn < u0:
            continue
        level, jump = seam_pair(x, s)
        a_env = fe[(s - cfn) // 44:(s - cfn) // 44 + ncf]
        a_spec = band_matrix(mono, s - cfn + nwin * (1 + np.arange(ntile)), nwin)
        N = 2
        while True:
            N += 1
            if N % 3 and N % 4:                 # whole bars of 3 or 4 beats only
                continue
            e0 = s + int(round(N * Ps))
            if e0 > u1 + FINE_SHIFT_MS * 44:
                break
            if e0 < u1 - tail_s:
                continue
            best = (-2.0, 0)
            for dk in range(-FINE_SHIFT_MS, FINE_SHIFT_MS + 1):
                kb = (e0 - cfn) // 44 + dk
                if kb < 0 or kb + ncf > len(fe) or (e0 + dk * 44) > u1:
                    continue
                b_env = fe[kb:kb + ncf]
                c = float(np.corrcoef(a_env, b_env)[0, 1]) if b_env.std() > 0 and a_env.std() > 0 else -1.0
                if c > best[0]:
                    best = (c, dk)
            if best[0] < -1.5:
                continue
            e = e0 + best[1] * 44
            b_spec = band_matrix(mono, e - cfn + nwin * (1 + np.arange(ntile)), nwin)
            lsd = float(np.mean(np.sqrt(np.mean((a_spec - b_spec) ** 2, axis=1))))
            cost = lsd + level + (0.0 if N % meter == 0 else 1.5) + 20 * max(0.0, jump - 0.05) - 4 * best[0] + 0.05 * ((s - u0) + (u1 - e)) / RATE
            cands.append((cost, s, e, f"{(e - s) / Ps:.2f} beats, lsd {lsd:.1f} dB, env corr {best[0]:.2f}"))
    return sorted(cands)[:TOP_K], ""


def fallback_candidates(x, mono, u0, u1, cfn):
    """Zero-crossing points with the smallest 100 ms spectral difference."""
    usable = u1 - u0
    head_s, tail_s = min(HEAD_SEARCH_S * RATE, 0.2 * usable), min(TAIL_SEARCH_S * RATE, 0.25 * usable)
    nwin = int(0.1 * RATE)
    zc = np.nonzero((mono[:-1] < 0) & (mono[1:] >= 0))[0] + 1
    snap = lambda g: np.unique([int(zc[min(np.searchsorted(zc, v), len(zc) - 1)]) for v in g])
    step = int(0.02 * RATE)
    S = snap(np.arange(u0 + cfn, u0 + cfn + head_s, step))
    E = snap(np.arange(u1 - tail_s, u1, step))
    S, E = S[S - cfn >= u0], E[E <= u1]
    A, B = band_matrix(mono, S, nwin), band_matrix(mono, E, nwin)
    d2 = (A ** 2).sum(1)[:, None] + (B ** 2).sum(1)[None, :] - 2 * A @ B.T
    lsd = np.sqrt(np.maximum(d2, 0) / A.shape[1])
    pen = np.array([(lambda lv, jp: lv + 20 * max(0.0, jp - 0.05))(*seam_pair(x, int(s))) for s in S])
    cost = lsd + pen[:, None] + 0.05 * ((S - u0)[:, None] + (u1 - E)[None, :]) / RATE
    cost[(E[None, :] - S[:, None]) < 20 * cfn] = np.inf
    order = np.argsort(cost, axis=None)[:TOP_K]
    out = []
    for o in order:
        i, j = np.unravel_index(o, cost.shape)
        if np.isfinite(cost[i, j]):
            out.append((float(cost[i, j]), int(S[i]), int(E[j]), f"zero-crossing pair, lsd {lsd[i, j]:.1f} dB"))
    return out


def make_loop(wav):
    """Build and check the loop file for one engine-ready WAV. Returns a loop_report row dict."""
    nn, cue = split_name(wav)
    x = decode_stereo(wav)
    mono = x.mean(axis=1).astype(np.float64)
    u0, u1, tr = trim_ends(x)
    usable_s = (u1 - u0) / RATE
    cf_s = CROSSFADE_S if usable_s >= SHORT_USABLE_S else CROSSFADE_S * max(0.25, usable_s / SHORT_USABLE_S)
    cfn = int(round(cf_s * RATE)) // 44 * 44
    row = {"cue": f"{nn}_{cue}", "trimmed_head_ms": f"{tr['head_ms']:.0f}", "trimmed_tail_ms": f"{tr['tail_ms']:.0f}",
           "tempo_bpm": "none", "loop_start_s": "", "loop_end_s": "", "crossfade_ms": f"{cfn / RATE * 1000:.0f}",
           "seam_level_diff_db": "", "seam_sample_jump": "", "result": "fail", "loop_length_s": "", "method": "",
           "notes": ""}
    notes = [f"trim head {tr['head_silence_ms']:.0f} silence + {tr['head_fade_ms']:.0f} fade, "
             f"tail {tr['tail_silence_ms']:.0f} silence + {tr['tail_fade_ms']:.0f} fade"]
    if usable_s < 3 * CROSSFADE_S + 2:
        row["notes"] = "; ".join(notes + [f"only {usable_s:.1f} s usable"])
        return row
    ctx = {}
    paths = []
    cands, why = tempo_candidates(x, mono, u0, u1, cfn, ctx)
    if cands:
        paths.append(("tempo", cands))
        row["tempo_bpm"] = f"{ctx['bpm']:.1f}"
    else:
        notes.append(why)
    chosen = None
    for pi in range(2):
        if pi == 1:
            if chosen is not None:
                break
            cands = fallback_candidates(x, mono, u0, u1, cfn)
            if paths:
                notes.append("no tempo candidate passed the seam check, fell back to zero-crossing search")
            paths.append(("zero-crossing", cands))
        elif not cands:
            continue
        method, cands = paths[-1]
        for cost, s, e, desc in cands:
            loop = build_loop(x, s, e, cfn)
            text, head_db, tail_db, jump = loop_check(loop.astype(np.float64) / 32768, True)
            attempt = (cost, s, e, desc, loop, text, head_db, tail_db, jump, method)
            if chosen is None or (text.startswith("yes")):
                chosen = attempt
            if text.startswith("yes"):
                break
        if chosen is not None and chosen[5].startswith("yes"):
            break
        if chosen is not None and pi == 0:
            first_fail = chosen
            chosen = None
    if chosen is None and 'first_fail' in locals():
        chosen = first_fail
    if chosen is None:
        row["notes"] = "; ".join(notes + ["no loop candidates"])
        return row
    cost, s, e, desc, loop, text, head_db, tail_db, jump, method = chosen
    if text.startswith("yes"):
        LOOP_DIR.mkdir(exist_ok=True)
        with wave.open(str(LOOP_DIR / f"{nn}_{cue}_loop.wav"), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(loop.astype("<i2").tobytes())
    else:
        notes.append("seam check failed: " + text)
    if method == "tempo":
        weak = ctx["tempo_peak"] < 0.5 or ctx["tempo_z"] < 3.5
        notes.append(f"{ctx['meter']} beats/bar favoured, autocorr {ctx['tempo_peak']:.2f} z {ctx['tempo_z']:.1f}"
                     + (" (low-confidence tempo)" if weak else ""))
    row.update({"loop_start_s": f"{s / RATE:.3f}", "loop_end_s": f"{e / RATE:.3f}",
                "loop_length_s": f"{(e - s) / RATE:.3f}",
                "seam_level_diff_db": f"{abs(head_db - tail_db):.2f}", "seam_sample_jump": f"{jump:.4f}",
                "result": "pass" if text.startswith("yes") else "fail", "method": method,
                "notes": "; ".join(notes + [desc])})
    return row


def analyse(mp3):
    nn, cue = split_name(mp3)
    req, loop = CUES.get(nn, (None, False))
    x = decode_stereo(mp3)
    gain = gain_for(x)
    y = x * gain                                             # what the WAV contains (before 16-bit rounding)
    dur = len(x) / RATE
    peak = float(np.max(np.abs(x)))
    rms_db = db(float(np.sqrt(np.mean(x.astype(np.float64) ** 2))))
    clip = int(np.sum(np.abs(x) >= CLIP_LEVEL))
    loop_text, head_db, tail_db, jump = loop_check(y, loop)
    wav = MUSIC_DIR / (mp3.stem + ".wav")
    wav_peak = wav_rms = wav_dur = float("nan")
    if wav.exists():
        w = decode_stereo(wav)
        wav_dur = len(w) / RATE
        wav_peak = db(float(np.max(np.abs(w))))
        wav_rms = db(float(np.sqrt(np.mean(w.astype(np.float64) ** 2))))
    dev = (dur - req) / req if req else float("nan")
    flags = []
    if db(peak) < SILENT_PEAK_DB:
        flags.append("effectively silent (peak < -40 dB)")
    if req and abs(dev) > DURATION_TOLERANCE:
        flags.append(f"duration off by {dev * 100:+.0f}%")
    if clip >= CLIP_SAMPLES or peak > 1.0:
        flags.append(f"clipping ({clip} samples at/near full scale)")
    if loop and not loop_text.startswith("yes"):
        flags.append("loop seam not clean by measurement")
    return {
        "file": mp3.name, "cue": nn, "name": cue, "loop": "loop" if loop else "one-shot",
        "requested_s": f"{req:.1f}" if req else "", "duration_s": f"{dur:.3f}",
        "duration_dev_pct": f"{dev * 100:+.1f}" if req else "",
        "peak_db": f"{db(peak):.2f}", "rms_db": f"{rms_db:.2f}", "clip_samples": clip,
        "loop_head_rms_db": f"{head_db:.1f}", "loop_tail_rms_db": f"{tail_db:.1f}",
        "loop_seam_jump_fs": f"{jump:.3f}", "loop_clean": loop_text,
        "wav_duration_s": f"{wav_dur:.3f}", "wav_peak_db": f"{wav_peak:.2f}", "wav_rms_db": f"{wav_rms:.2f}",
        "flags": "; ".join(flags),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-report", action="store_true", help="convert only")
    ap.add_argument("--only", nargs="*", help="stems to process, e.g. 01_title")
    ap.add_argument("--no-loops", action="store_true", help="do not build the loop files")
    ap.add_argument("--loops-only", action="store_true",
                    help="only build the loop files from the existing engine-ready WAVs")
    args = ap.parse_args()

    files = sorted(DELIVERED.glob("*.mp3"))
    allfiles = files
    if args.only:
        files = [f for f in files if f.stem in set(args.only)]
    if not files:
        sys.exit(f"no mp3 files in {DELIVERED}")
    if not args.loops_only:
        for f in files:
            wav = convert(f)
            print(f"{f.name} -> {wav.name}")
        if not args.no_report and not args.only:
            rows = [analyse(f) for f in allfiles]
            with open(REPORT, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            print(f"wrote {REPORT} ({len(rows)} rows, {sum(1 for r in rows if r['flags'])} flagged)")
    if not args.no_loops:
        rows = []
        for f in files:
            nn, _ = split_name(f)
            if not CUES.get(nn, (None, False))[1]:
                continue
            r = make_loop(MUSIC_DIR / (f.stem + ".wav"))
            rows.append(r)
            print(f"loop {r['cue']}: {r['result']} bpm={r['tempo_bpm']} len={r['loop_length_s']}s "
                  f"seam {r['seam_level_diff_db']} dB / {r['seam_sample_jump']} FS  [{r['method']}]")
        if rows and not args.only:
            with open(LOOP_REPORT, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            print(f"wrote {LOOP_REPORT} ({len(rows)} rows, {sum(1 for r in rows if r['result'] != 'pass')} failed)")


if __name__ == "__main__":
    main()
