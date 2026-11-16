#!/usr/bin/env python3
"""Procedural PLACEHOLDER sounds for footsteps and ambience beds (numpy only, deterministic seeds).

No generated or recorded take existed for these (1997 has no footsteps or ambience beds; the reviewed set's bird take 49 was
rejected) and the ElevenLabs connector was not attached to the session that made them (15 Nov 2026). They are synthesised
from filtered noise and damped partials so the systems that play them can be built and proven; replace them with generated
takes (doc/remaster/FABLE_ART_QUEUE.md rows AU-*), same file names, and re-run Scripts/AudioQA/import_life_audio.sh.

  python3 -I Scripts/AudioQA/synth_life.py [--out SourceAssets/Audio/Life]

Writes PCM16 44.1 kHz WAVs: Step_<surface>_<n>.wav (mono, 7 surfaces x 4) and Bed_<name>.wav (stereo, 24 s seamless loops).
"""
import argparse, json, sys, wave
from pathlib import Path
import numpy as np

SR = 44100
SURFACES = ['grass', 'dirt', 'sand', 'wood', 'stone', 'snow', 'water']
BEDS = ['sea', 'wind', 'cave', 'meadow']


def band(x, lo, hi, soft=0.25):
    """Band-pass by FFT with raised-cosine edges (soft = fraction of the edge frequency)."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    m = np.ones_like(f)
    if lo > 0:
        e = lo * soft
        m *= np.clip((f - (lo - e)) / (2 * e), 0, 1)
    if hi < SR / 2:
        e = hi * soft
        m *= np.clip(((hi + e) - f) / (2 * e), 0, 1)
    m = 0.5 - 0.5 * np.cos(np.pi * m)
    return np.fft.irfft(np.fft.rfft(x) * m, n)


def pink(n, rng):
    f = np.fft.rfftfreq(n, 1 / SR)
    spec = (rng.standard_normal(len(f)) + 1j * rng.standard_normal(len(f))) / np.sqrt(np.maximum(f, 20))
    return np.fft.irfft(spec, n)


def env(n, attack_s, decay_s):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack_s, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(t - attack_s, 0) / max(decay_s, 1e-4))


def norm(x, peak_db):
    p = np.max(np.abs(x)) or 1.0
    return x / p * 10 ** (peak_db / 20)


def grains(n, rng, rate_hz, lo, hi, dur_s, grain_ms=(1.5, 5)):
    """A crunch: many tiny noise grains (snow, sand, grit)."""
    out = np.zeros(n)
    count = int(rate_hz * dur_s)
    for _ in range(count):
        g = int(SR * rng.uniform(*grain_ms) / 1000)
        at = int(rng.uniform(0, dur_s) ** 1.3 / dur_s ** 0.3 * SR)
        if at + g >= n:
            continue
        out[at:at + g] += rng.standard_normal(g) * np.hanning(g) * rng.uniform(0.3, 1.0)
    return band(out, lo, hi)


def partials(n, freqs, decays, amps):
    t = np.arange(n) / SR
    return sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, d, a in zip(freqs, decays, amps))


def step(surface, rng):
    n = int(SR * 0.42)
    t = np.arange(n) / SR
    thump = partials(n, [rng.uniform(55, 80), rng.uniform(95, 130)], [0.035, 0.025], [1.0, 0.5])
    if surface == 'grass':
        x = 0.35 * thump + band(rng.standard_normal(n), 1800, 9000) * env(n, 0.01, 0.07) * 1.2
        x += 0.6 * grains(n, rng, 260, 2500, 10000, 0.16)
    elif surface == 'dirt':
        x = 0.9 * thump + band(rng.standard_normal(n), 250, 2500) * env(n, 0.003, 0.03) * 0.8
        x += 0.35 * grains(n, rng, 120, 1200, 6000, 0.08)
    elif surface == 'sand':
        x = 0.4 * thump + 0.9 * grains(n, rng, 700, 1200, 7000, 0.17) + band(rng.standard_normal(n), 400, 3000) * env(n, 0.02, 0.06) * 0.3
    elif surface == 'wood':
        heel = partials(n, [rng.uniform(170, 200), rng.uniform(390, 440), rng.uniform(880, 990), 2150], [0.07, 0.045, 0.03, 0.012], [1.0, 0.6, 0.35, 0.15])
        knock = band(rng.standard_normal(n), 600, 5000) * env(n, 0.0008, 0.006) * 0.7
        toe = np.roll(heel * 0.45 + knock * 0.6, int(SR * rng.uniform(0.045, 0.065)))
        x = 0.6 * thump + heel + knock + toe
    elif surface == 'stone':
        click = band(rng.standard_normal(n), 2000, 12000) * env(n, 0.0005, 0.004)
        ring = partials(n, [rng.uniform(1100, 1400), rng.uniform(2600, 3100)], [0.02, 0.01], [0.25, 0.12])
        scuff = band(rng.standard_normal(n), 1500, 8000) * env(n, 0.03, 0.05) * 0.12
        x = 0.55 * thump + click * 1.3 + ring + np.roll(click * 0.5, int(SR * 0.05)) + scuff
    elif surface == 'snow':
        x = 0.3 * thump + 1.0 * grains(n, rng, 900, 400, 4500, 0.2, (2, 7)) + band(rng.standard_normal(n), 200, 1200) * env(n, 0.03, 0.08) * 0.25
    elif surface == 'water':
        splash = band(rng.standard_normal(n), 350, 6000) * env(n, 0.015, 0.11)
        bub = np.zeros(n)
        for _ in range(6):
            at = int(SR * rng.uniform(0.02, 0.2)); d = int(SR * rng.uniform(0.012, 0.03))
            if at + d < n:
                tt = np.arange(d) / SR
                f0 = rng.uniform(500, 1300)
                bub[at:at + d] += np.sin(2 * np.pi * (f0 * tt + 4000 * tt * tt)) * np.exp(-tt / 0.01) * 0.4
        x = 0.4 * thump + splash + bub
    else:
        raise ValueError(surface)
    fade = np.ones(n); k = int(SR * 0.02); fade[-k:] = np.linspace(1, 0, k)
    return norm(x * fade, -6.0 + rng.uniform(-1.5, 0))


def loop_seam(x, seconds=1.5):
    """Make a seamless loop: crossfade the tail into the head (equal power)."""
    k = int(SR * seconds)
    head, tail = x[:k].copy(), x[-k:]
    w = np.linspace(0, np.pi / 2, k)
    if x.ndim == 2:
        w = w[:, None]
    out = x[:-k].copy()
    out[:k] = head * np.sin(w) + tail * np.cos(w)
    return out


def bed(name, rng, seconds=24.0):
    n = int(SR * (seconds + 1.5))
    t = np.arange(n) / SR
    ch = []
    for c in range(2):
        r = np.random.default_rng(rng.integers(1 << 31) + c)
        if name == 'sea':
            swell = np.zeros(n)
            at = r.uniform(0, 2)
            while at < seconds + 1.5:
                period = r.uniform(6.5, 9.5)
                swell += np.exp(-0.5 * ((t - at - period * 0.35) / (period * 0.22)) ** 2) * r.uniform(0.6, 1.0)
                at += period
            body = band(pink(n, r), 80, 900) * (0.25 + swell)
            wash = band(r.standard_normal(n), 1500, 9000) * (np.roll(swell, int(SR * 0.6)) ** 2) * 0.12
            x = body + wash
        elif name == 'wind':
            gust = 0.55 + 0.45 * np.sin(2 * np.pi * t / r.uniform(5, 8) + r.uniform(0, 6)) * np.sin(2 * np.pi * t / r.uniform(11, 17))
            lo = band(pink(n, r), 150, 700) * gust
            hi = band(pink(n, r), 900, 2600) * gust ** 3 * 0.35
            x = lo + hi
        elif name == 'meadow':
            breeze = 0.5 + 0.5 * np.sin(2 * np.pi * t / r.uniform(7, 11) + r.uniform(0, 6)) ** 2
            x = band(pink(n, r), 400, 3000) * breeze * 0.5
            leaves = np.zeros(n)
            for _ in range(int(seconds * 1.2)):
                at = int(SR * r.uniform(0, seconds + 1)); d = int(SR * r.uniform(0.3, 0.9))
                if at + d < n:
                    leaves[at:at + d] += r.standard_normal(d) * np.hanning(d) * r.uniform(0.1, 0.3)
            x += band(leaves, 2500, 9000)
        elif name == 'cave':
            x = band(pink(n, r), 30, 240) * 0.08
            drips = np.zeros(n)
            for _ in range(int(seconds * 0.55)):
                at = int(SR * r.uniform(0.2, seconds)); d = int(SR * 0.06)
                tt = np.arange(d) / SR
                f0 = r.uniform(1400, 3200)
                drip = np.sin(2 * np.pi * (f0 * tt - 9000 * tt * tt)) * np.exp(-tt / 0.012) * r.uniform(0.3, 1.0)
                if at + d < n:
                    drips[at:at + d] += drip
            for delay, gain in [(0.113, 0.45), (0.187, 0.32), (0.271, 0.22), (0.39, 0.14)]:
                drips[int(SR * delay):] += drips[:-int(SR * delay)] * gain * 0.6
            x += drips * 0.5
        else:
            raise ValueError(name)
        ch.append(x)
    x = np.stack(ch, 1)
    x = loop_seam(x)
    return norm(x, -9.0)


def write(path, x):
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1 if pcm.ndim == 1 else pcm.shape[1]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return len(pcm) / SR


def main(argv=None) -> int:
    here = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out', default=str(here / 'SourceAssets/Audio/Life'))
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for si, s in enumerate(SURFACES):
        for i in range(4):
            rng = np.random.default_rng(1000 + si * 10 + i)
            name = f'Step_{s}_{i + 1}'
            rows.append({'name': name, 'kind': 'step', 'surface': s, 'duration_s': round(write(out / f'{name}.wav', step(s, rng)), 4), 'loop': False})
    for bi, b in enumerate(BEDS):
        rng = np.random.default_rng(2000 + bi)
        name = f'Bed_{b}'
        rows.append({'name': name, 'kind': 'bed', 'bed': b, 'duration_s': round(write(out / f'{name}.wav', bed(b, rng)), 4), 'loop': True})
    (out / 'life_sources.json').write_text(json.dumps({'schema': 'dink-audio-life-sources/1', 'tool': 'Scripts/AudioQA/synth_life.py (procedural placeholder)', 'files': rows}, indent=1) + '\n')
    print(f'SYNTH OK: {len(rows)} files in {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
