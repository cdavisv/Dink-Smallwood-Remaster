#!/usr/bin/env python3
"""Audio coverage table: every 1997 sound id and music cue a script or the engine uses, the remaster's take for it, whether that
take is cooked into the packaged build, and whether it was HEARD in a recorded run; the same for a sample of the 2,088 voice
lines and the footstep / ambience takes; and loudness per category.

  # 1. a sweep plan for the game (dink.AudioQA.Sweep <plan>):
  python3 -I Scripts/AudioQA/audio_coverage.py plan --out Saved/AudioQA/sweep_plan.tsv [--voice-lines 200]
  # 2. after a run with SDL_AUDIO_DRIVER=disk (Scripts/AudioQA/run_recorded.sh): the table
  python3 -I Scripts/AudioQA/audio_coverage.py table --log <game.log> --recording <out.raw> [--listing <pak listing>] \
      [--gameplay-log <log> --gameplay-recording <raw>] --out Docs/Verification/AudioQA_15Nov2026

`--root` is the repository (story scripts in bin/dink/story, engine source in source/dink/dink.cpp, tools/dinkex/out for the
screens' music); `--assets` is a checkout with real (LFS-pulled) source audio for loudness.
"""
import argparse, csv, json, math, re, struct, subprocess, sys
from array import array
from collections import Counter, defaultdict, OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve()
PROJECT = HERE.parents[2]
REPO = HERE.parents[3]

# The engine's own SoundPlayEffect calls with a literal id (dink.cpp), what the remaster does for each.
ENGINE = {
    1: ('12825 duck brain (quack, 800 Hz spread)', 'DinkBrains.cpp duck cue'),
    2: ('13421-13427 pig brain (pig1-4)', 'DinkBrains.cpp pig cue'), 3: ('13421-13427 pig brain', 'DinkBrains.cpp pig cue'),
    4: ('13421-13427 pig brain', 'DinkBrains.cpp pig cue'), 5: ('13421-13427 pig brain', 'DinkBrains.cpp pig cue'),
    7: ('15343-15344 touched map.dat warp without its own sound (12000 Hz)', 'DinkAudioLife warp (OnWarped)'),
    9: ('14284/14308/14356/15551 hit with attack_hit_sound 0', 'DinkGameplay/DinkBrains hit cue (regenerated take 09_punch_e, SFX/redo_15Nov2026.json)'),
    11: ('15975/16026/16033 talk menu move; 16501-16613 item screen move', 'DinkAudioLife menu; DinkInventoryScreen'),
    13: ('5851 exp raise mark (15050), 5864 exp tick (29050)', 'DinkAudioLife status ticks'),
    14: ('5931 gold tick', 'DinkAudioLife status ticks'),
    15: ('14708 Dink hurt (25050-27050)', 'DinkAudioLife hurt grunt'), 16: ('14709 Dink hurt (25050-27050)', 'DinkAudioLife hurt grunt'),
    17: ('16158 talk menu pick; 16632 item screen close', 'DinkAudioLife menu pick; DinkInventoryScreen'),
    18: ('14962 item screen open; 16480/16554 arm (42050)', 'DinkInventoryScreen'),
    19: ('14472 mouse pointer (brain 13) clicks on nothing: only the 1997 start screen (start.c) uses the pointer', 'none: the remaster has its own title menu'),
    22: ('5899/5907/5914 strength/defense/magic tick', 'DinkAudioLife status ticks'),
}
CATEGORY_VOLUME = {'sfx': 0.8, 'music': 0.35, 'voice': 1.0}


def read_json(p):
    return json.loads(Path(p).read_text())


def key(raw):
    return raw.replace('\\', '/').split('/')[-1].lower()


# ---------------------------------------------------------------------------------------------------------------- static

def scripts_scan(root: Path):
    story = root / 'bin/dink/story'
    load = {}
    uses, sp_uses, midis = defaultdict(list), defaultdict(list), defaultdict(list)
    for f in sorted(story.glob('*.c')):
        text = f.read_text(errors='replace')
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
        text = re.sub(r'//[^\n]*', '', text)  # commented-out calls never run
        for m in re.finditer(r'load_sound\s*\(\s*"([^"]+)"\s*,\s*(\d+)', text, re.I):
            load[int(m.group(2))] = m.group(1)
        for m in re.finditer(r'playsound\s*\(\s*(\d+)', text, re.I):
            uses[int(m.group(1))].append(f.stem)
        for m in re.finditer(r'sp_sound\s*\([^,]+,\s*(\d+)', text, re.I):
            sp_uses[int(m.group(1))].append(f.stem)
        for m in re.finditer(r'playmidi\s*\(\s*"([^"]*)"', text, re.I):
            if m.group(1):
                midis[key(m.group(1))].append(f.stem)
    return load, uses, sp_uses, midis


def screen_music(root: Path):
    """Screens whose music.dat entry plays a cue: (raw, file key) -> screens (as UDinkAudioSubsystem::EnterScreen resolves it)."""
    out = defaultdict(list)
    for f in sorted((root / 'tools/dinkex/out/screens').glob('SCR_*.json')):
        s = json.loads(f.read_text())
        m = s.get('music') or {}
        if isinstance(m, dict) and m.get('action') == 'play' and int(m.get('raw') or 0) > 0:
            out[(int(m['raw']), key(m.get('file') or m.get('name') or ''))].append(s['screen'])
    return out


def story_order(trace_dir: Path):
    order = []
    names = ['stonebrook_probe_trace.txt'] + [f'probe_ch{i}_trace.txt' for i in range(2, 21)]
    seen = set()
    for n in names:
        p = trace_dir / n
        if not p.is_file():
            continue
        for line in p.read_text(errors='replace').splitlines():
            m = re.search(r' say .* id=(\S+)', line)
            if m and m.group(1) not in seen:
                seen.add(m.group(1)); order.append(m.group(1))
    return order


# ---------------------------------------------------------------------------------------------------------------- plan

def make_plan(a):
    data = PROJECT / 'Content/Dink/Data/Audio'
    approved, voice, life = read_json(data / 'approved.json'), read_json(data / 'voice.json'), read_json(data / 'life.json')
    rows = []
    vol = approved.get('volumes', {})
    mix = read_json(data / 'mix.json') if (data / 'mix.json').is_file() else {'sfx': {}, 'music': {}}
    for k, v in sorted(approved['sounds'].items(), key=lambda kv: int(kv[0])):
        rows.append(('sfx', k, v['asset'], round(vol.get('sfx', .8) * mix['sfx'].get(k, 1.0), 4), 5.0))
    seen = set()
    for k, v in approved['music'].items():
        if v['asset'] not in seen:
            seen.add(v['asset']); rows.append(('music', k, v['asset'], round(vol.get('music', .35) * mix['music'].get(v['asset'], 1.0), 4), a.music_seconds))
    lines = voice['lines']
    order = [i for i in story_order(Path(a.traces)) if i in lines][: a.voice_lines] if a.traces else []
    if len(order) < a.voice_lines:  # no traces: csv order
        order += [i for i in lines if i not in order][: a.voice_lines - len(order)]
    voices_done = {lines[i].get('voice') for i in order}
    for i, v in lines.items():
        if v.get('voice') not in voices_done:
            voices_done.add(v.get('voice')); order.append(i)
    for i in order:
        rows.append(('voice', i, lines[i]['asset'], voice.get('volume', 1.0), 12.0))
    for s, takes in life['steps'].items():
        for t in takes:
            rows.append(('step', s, t['asset'], round(t['gain'] * life['volumes']['steps'], 4), 2.0))
    for b, t in life['beds'].items():
        rows.append(('bed', b, t['asset'], round(t['gain'] * life['volumes']['beds'], 4), 6.0))
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w') as f:
        f.write('# kind\tkey\tasset\tvolume\tseconds (Scripts/AudioQA/audio_coverage.py plan)\n')
        for r in rows:
            f.write('\t'.join(str(x) for x in r) + '\n')
    c = Counter(r[0] for r in rows)
    print(f'PLAN OK: {len(rows)} items {dict(c)} -> {out}')
    return 0


# ---------------------------------------------------------------------------------------------------------------- recording

LOGTIME = re.compile(r'^\[(\d{4})\.(\d\d)\.(\d\d)-(\d\d)\.(\d\d)\.(\d\d):(\d{3})\]')


def log_seconds(line):
    m = LOGTIME.match(line)
    if not m:
        return None
    y, mo, d, h, mi, s, ms = map(int, m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s + ms / 1000.0


class Recording:
    """Raw interleaved float32 (SDL disk driver), memory-mapped."""

    def __init__(self, path, rate, channels, fmt='f32'):
        import numpy as np
        self.np = np
        self.rate, self.ch = rate, channels
        x = np.memmap(path, dtype='<f4' if fmt == 'f32' else '<i2', mode='r')
        n = len(x) // channels * channels
        self.x = x[:n].reshape(-1, channels)
        self.frames = len(self.x)

    def seg(self, t0, t1):
        a, b = max(0, int(t0 * self.rate)), min(self.frames, int(t1 * self.rate))
        return self.x[a:b] if b > a else None

    def rms_db(self, t0, t1):
        s = self.seg(t0, t1)
        if s is None:
            return None
        acc = float(self.np.mean(self.np.square(s.astype('f8')).sum(axis=1)))  # power summed over the speakers
        return 10 * self.np.log10(acc) if acc > 0 else -120.0

    def peak_db(self, t0, t1):
        s = self.seg(t0, t1)
        p = float(self.np.abs(s).max()) if s is not None and len(s) else 0.0
        return 20 * self.np.log10(p) if p > 0 else -120.0

    def first_onset(self, after=0.0, thresh_db=-50.0, win=0.01):
        t = after
        while t < self.frames / self.rate:
            r = self.rms_db(t, t + win)
            if r is not None and r > thresh_db:
                return t
            t += win
        return None

    def lufs(self, t0, t1, scratch: Path):
        s = self.seg(t0, t1)
        if s is None or len(s) < self.rate * 0.4:
            return None
        p = scratch / 'seg.f32'
        self.np.ascontiguousarray(s, dtype='<f4').tofile(p)
        # 5.1 as the device wrote it (FL FR FC LFE SL SR): ebur128 weights the surrounds like a listener would
        r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-f', 'f32le', '-ar', str(self.rate), '-ac', str(self.ch), '-i', str(p),
                            '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True)
        m = re.findall(r'I:\s+(-?[0-9.]+) LUFS', r.stderr)
        return float(m[-1]) if m else None


def sweep_windows(log_path: Path):
    """AUDIOQA sweep lines: (kind, key, asset, log seconds, play seconds, status)."""
    out = []
    pat = re.compile(r'AUDIOQA sweep (\d+)/(\d+) (\S+) (\S+) (\S+) volume=([0-9.]+) play=([0-9.]+) load_ms=([0-9.]+) (\S+)')
    for line in log_path.read_text(errors='replace').splitlines():
        m = pat.search(line)
        t = log_seconds(line)
        if m and t is not None:
            out.append({'kind': m.group(3), 'key': m.group(4), 'asset': m.group(5), 't': t, 'play': float(m.group(7)),
                        'load_ms': float(m.group(8)), 'status': m.group(9)})
    return out


def device_open_seconds(log_path: Path):
    """Log time at which SDL opened the device: sample 0 of the recording (the disk driver writes from that moment, in real time)."""
    for line in log_path.read_text(errors='replace').splitlines():
        if 'Writing to file' in line and 'LogSDL3' in line:
            return log_seconds(line)
    return None


def snap_onset(rec, t, before=0.4, after=0.6, step=0.005):
    """The first energy jump (>= 15 dB over the 150 ms before it, above -70 dB) near t, else t."""
    k = t - before
    while k < t + after:
        a, b = rec.rms_db(k, k + 0.01), rec.rms_db(k - 0.16, k - 0.01)
        if a is not None and b is not None and a > -70 and a > b + 15:
            return k
        k += step
    return t


def source_resolver(assets_root: Path):
    """Asset path -> source audio file (approved takes from the selection manifest, voice lines, life takes)."""
    man = json.loads((assets_root / 'SourceAssets/Audio/selection_manifest.json').read_text())
    out = {f"{x['folder']}/{x['name']}.{x['name']}": assets_root / x['source'] for x in man['assets']}
    voice = read_json(PROJECT / 'Content/Dink/Data/Audio/voice.json')['lines']
    for k, v in voice.items():
        out[v['asset']] = assets_root / 'SourceAssets/Audio/Voice' / v.get('voice', '') / f'{k}.mp3'
    for d in (assets_root, PROJECT):
        life = d / 'SourceAssets/Audio/Life'
        for f in life.glob('*.wav') if life.is_dir() else []:
            if f.stat().st_size > 1000:
                out.setdefault(f'/Game/Dink/Audio/Life/{f.stem}.{f.stem}', f)
    return out


def source_pcm(path: Path, seconds: float, rate: int):
    import numpy as np
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-t', f'{seconds:.3f}', '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-'], capture_output=True)
    return np.frombuffer(r.stdout, dtype='<f4')


def xcorr_onset(rec, src, t0, t1):
    """Where src starts in the recording between t0 and t1 (seconds), and the normalised match (1 = the same waveform)."""
    np = rec.np
    seg = rec.seg(max(0.0, t0), t1)
    if seg is None or len(src) < 200 or len(seg) < len(src):
        return None, 0.0
    m = seg.astype('f8').sum(axis=1)
    n = 1 << int(np.ceil(np.log2(len(m) + len(src))))
    c = np.fft.irfft(np.fft.rfft(m, n) * np.conj(np.fft.rfft(src, n)), n)[: len(m) - len(src) + 1]
    lag = int(np.argmax(np.abs(c)))
    e = np.linalg.norm(m[lag:lag + len(src)]) * np.linalg.norm(src)
    return max(0.0, t0) + lag / rec.rate, float(abs(c[lag]) / e) if e > 0 else 0.0


def sweep_heard(windows, rec: Recording, scratch: Path, base=None, sources=None):
    """Each sweep window found in the recording by cross-correlating it with its own source take (proof that THIS asset sounded),
    the clock offset tracked as it goes (the SDL disk driver runs about 1 % fast against the log's wall clock); level, loudness
    and peak then measured from the found start. heard = match >= 0.5 and RMS above -70 dBFS."""
    if not windows:
        return {}
    if base is None:
        onset = rec.first_onset()
        base = windows[0]['t'] - (onset or 0.0)
    sources = sources or {}
    drift, last_t, offset = 0.0, None, 0.0
    res = {}
    for w in windows:
        pred = (w['t'] - base) + offset + (drift * (w['t'] - last_t) if last_t is not None else 0.0)
        src_path = sources.get(w['asset'])
        found, match = None, 0.0
        if src_path is not None and src_path.is_file():
            src = source_pcm(src_path, min(w['play'], 3.0), rec.rate)
            found, match = xcorr_onset(rec, src, pred - 1.5, pred + 1.5 + min(w['play'], 3.0))
        if found is not None and match >= 0.5:
            new_offset = found - (w['t'] - base)
            if last_t is not None and w['t'] > last_t + 1:
                drift = 0.7 * drift + 0.3 * ((new_offset - offset) / (w['t'] - last_t))
            offset, last_t = new_offset, w['t']
            t0 = found
        else:
            t0 = snap_onset(rec, pred)
        dur = max(0.15, min(w['play'], 4.0))
        sig = rec.rms_db(t0, t0 + dur)
        heard = sig is not None and sig > -70 and match >= 0.5
        res[(w['kind'], w['asset'])] = {'rms_db': sig, 'floor_db': None, 'peak_db': rec.peak_db(t0, t0 + max(0.15, w['play'])),
                                       'lufs': rec.lufs(t0, t0 + min(w['play'], 8.0), scratch),
                                       'heard': heard, 'match': round(match, 3), 'load_ms': w['load_ms'], 'onset_s': round(t0, 3)}
    return res


def gameplay_events(log_path: Path):
    """Playing approved sound/music/voice lines with log times."""
    ev = []
    pats = [('sfx', re.compile(r'Playing approved sound (\S+)')), ('music', re.compile(r'Playing approved music (\S+)')),
            ('voice', re.compile(r'Playing voice (\S+) speaker=')), ('bed', re.compile(r'Ambience bed \S+: (\S+)')),
            ('warp', re.compile(r'Warp sound (\d+) at'))]
    for line in log_path.read_text(errors='replace').splitlines():
        t = log_seconds(line)
        for kind, p in pats:
            m = p.search(line)
            if m and t is not None:
                ev.append((kind, m.group(1), t))
    return ev


# ---------------------------------------------------------------------------------------------------------------- loudness

def file_lufs(path: Path, cache: dict):
    k = str(path)
    if k in cache:
        return cache[k]
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True)
    i = re.findall(r'I:\s+(-?[0-9.]+) LUFS', r.stderr)
    p = re.findall(r'Peak:\s+(-?[0-9.]+) dBFS', r.stderr)
    cache[k] = (float(i[-1]) if i else None, float(p[-1]) if p else None)
    return cache[k]


def stat(xs):
    xs = sorted(x for x in xs if x is not None and x > -70)
    if not xs:
        return ('', '', '', 0)
    return (round(xs[0], 1), round(xs[len(xs) // 2], 1), round(xs[-1], 1), len(xs))


# ---------------------------------------------------------------------------------------------------------------- table

def make_table(a):
    root, assets_root = Path(a.root), Path(a.assets)
    data = PROJECT / 'Content/Dink/Data/Audio'
    approved, voice, life = read_json(data / 'approved.json'), read_json(data / 'voice.json'), read_json(data / 'life.json')
    manifest = read_json(assets_root / 'SourceAssets/Audio/selection_manifest.json')
    source_of = {f"{x['folder']}/{x['name']}.{x['name']}": assets_root / x['source'] for x in manifest['assets']}
    load, uses, sp_uses, midis = scripts_scan(root)
    smusic = screen_music(root)
    listing = Path(a.listing).read_text(errors='replace').lower() if a.listing else None
    cooked = lambda asset: '' if listing is None else ('yes' if asset.split('.')[0].lower().replace('/game/', '/content/') + '.uasset' in listing else 'NO')
    import tempfile
    scratch = Path(tempfile.mkdtemp(prefix='dink_audio_cov_'))
    cache_p = PROJECT / 'Saved/AudioQA/loudness_cache.json'
    cache_p.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(cache_p.read_text()) if cache_p.is_file() else {}
    heard = {}
    rec = None
    if a.log and a.recording:
        rec = Recording(a.recording, a.rate, a.channels)
        heard = sweep_heard(sweep_windows(Path(a.log)), rec, scratch, device_open_seconds(Path(a.log)), source_resolver(assets_root))
    game = gameplay_events(Path(a.gameplay_log)) if a.gameplay_log else []
    game_count = Counter((k, v) for k, v, _ in game)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    loud = defaultdict(list)

    def heard_cols(kind, asset):
        h = heard.get((kind, asset))
        if not h:
            return ['', '', '', '']
        return ['yes' if h['heard'] else 'NO', '' if h['rms_db'] is None else round(h['rms_db'], 1),
                '' if h['lufs'] is None else round(h['lufs'], 1), round(h['peak_db'], 1)]

    # ---- SFX
    rows = []
    for sid in range(1, 50):
        entry = approved['sounds'].get(str(sid))
        rejected_ids = {int(str(r.get('id', '0')).split('_')[0]) for r in approved.get('rejected', []) if isinstance(r, dict) and str(r.get('id', '')).split('_')[0].isdigit()}
        status = 'approved' if entry else ('REJECTED' if sid in rejected_ids else 'none')
        asset = entry['asset'] if entry else ''
        src = source_of.get(asset)
        lufs, peak = file_lufs(src, cache) if src and src.is_file() else (None, None)
        eff = None if lufs is None else round(lufs + 20 * math.log10(approved['volumes']['sfx']), 1)
        if eff is not None:
            loud['sfx'].append(eff)
        eng = ENGINE.get(sid, ('', ''))
        u = uses.get(sid, [])
        rows.append([sid, load.get(sid, ''), len(u), ' '.join(sorted(set(u))[:6]), len(sp_uses.get(sid, [])), eng[0], eng[1] or ('DinkDirector playsound' if u else ''),
                     status, asset.split('.')[-1] if asset else '', cooked(asset) if asset else '', *heard_cols('sfx', asset),
                     game_count.get(('sfx', asset), 0) if asset else '', '' if lufs is None else round(lufs, 1), eff if eff is not None else '', '' if peak is None else peak])
    sfx_header = ['id', '1997 file', 'script playsound calls', 'scripts', 'sp_sound uses', 'engine call (dink.cpp)', 'remaster emitter', 'take', 'asset',
                  'cooked', 'heard (sweep)', 'sweep RMS dBFS', 'sweep LUFS', 'sweep peak dBFS', 'played in gameplay run', 'source LUFS', 'in-game LUFS (x0.8)', 'source peak dBFS']
    write_csv(out / 'coverage_sfx.csv', sfx_header, rows)

    # ---- music
    mrows = []
    cues = OrderedDict()
    for k_, files in sorted(midis.items()):
        cues[('playmidi', k_)] = (len(files), ' '.join(sorted(set(files))[:6]))
    for (raw, name), screens in sorted(smusic.items()):
        cues[('screen', f'{raw} {name}')] = (len(screens), ' '.join(str(s) for s in screens[:8]) + (' ...' if len(screens) > 8 else ''))
    for (src_kind, k_), (n, where) in cues.items():
        if src_kind == 'screen':
            raw_, file_ = k_.split(' ', 1)
            e = approved['music'].get(file_) or approved['music'].get(raw_)  # EnterScreen: the file first, then the raw number
        else:
            e = approved['music'].get(k_)
        asset = e['asset'] if e else ''
        src = source_of.get(asset)
        lufs, peak = file_lufs(src, cache) if src and src.is_file() else (None, None)
        eff = None if lufs is None else round(lufs + 20 * math.log10(approved['volumes']['music']), 1)
        mrows.append([src_kind, k_, n, where, asset.split('.')[-1] if asset else 'UNRESOLVED (silent)', 'loop' if e and e.get('loop') else ('one-shot' if e else ''),
                      cooked(asset) if asset else '', *heard_cols('music', asset), game_count.get(('music', asset), 0) if asset else '',
                      '' if lufs is None else round(lufs, 1), '' if eff is None else eff])
    for asset in {v['asset'] for v in approved['music'].values()}:
        src = source_of.get(asset)
        l, _ = file_lufs(src, cache) if src and src.is_file() else (None, None)
        if l is not None:
            loud['music'].append(l + 20 * math.log10(approved['volumes']['music']))
    for sc, e in sorted(approved.get('screen_music', {}).items(), key=lambda kv: int(kv[0])):
        mrows.append(['screen override', sc, 1, sc, e['asset'].split('.')[-1], 'loop' if e.get('loop') else 'one-shot', cooked(e['asset']), *heard_cols('music', e['asset']),
                      game_count.get(('music', e['asset']), 0), '', ''])
    write_csv(out / 'coverage_music.csv', ['source', 'cue', 'uses', 'scripts / screens', 'take', 'kind', 'cooked', 'heard (sweep)', 'sweep RMS dBFS', 'sweep LUFS',
                                           'sweep peak dBFS', 'played in gameplay run', 'source LUFS', 'in-game LUFS (x0.35)'], mrows)

    # ---- voice
    lines = voice['lines']
    vrows = []
    vcsv = {r['id']: r for r in csv.DictReader(open(assets_root / 'SourceAssets/Audio/Voice/voice_lines.csv', encoding='utf-8'))}
    swept = [k for (kind, asset), v in heard.items() if kind == 'voice' for k in [asset]]
    asset_to_id = {v['asset']: i for i, v in lines.items()}
    all_cooked = Counter(cooked(v['asset']) for v in lines.values()) if listing else Counter()
    for i, v in lines.items():
        src = assets_root / 'SourceAssets/Audio/Voice' / v.get('voice', '') / f'{i}.mp3'
        if a.voice_loudness_all or (v['asset'] in swept):
            l, p = file_lufs(src, cache) if src.is_file() else (None, None)
            if l is not None:
                loud['voice'].append(l)
        else:
            l, p = (None, None)
        if v['asset'] in swept:
            vrows.append([i, v.get('voice', ''), vcsv.get(i, {}).get('character', ''), v['asset'].split('.')[-1], v.get('duration_s', ''), cooked(v['asset']),
                          *heard_cols('voice', v['asset']), game_count.get(('voice', i), 0), '' if l is None else round(l, 1)])
    write_csv(out / 'coverage_voice_sample.csv', ['line', 'voice', 'character', 'asset', 'duration s', 'cooked', 'heard (sweep)', 'sweep RMS dBFS', 'sweep LUFS',
                                                  'sweep peak dBFS', 'played in gameplay run', 'source LUFS'], vrows)
    game_voice = {k for (kind, k) in game_count if kind == 'voice'}

    # ---- life
    lrows = []
    for s, takes in life['steps'].items():
        for t in takes:
            lrows.append(['step', s, t['asset'].split('.')[-1], t['gain'], round(t['lufs'] + 20 * math.log10(t['gain'] * life['volumes']['steps']), 1), cooked(t['asset']), *heard_cols('step', t['asset'])])
            loud['steps'].append(t['lufs'] + 20 * math.log10(t['gain'] * life['volumes']['steps']))
    for b, t in life['beds'].items():
        lrows.append(['bed', b, t['asset'].split('.')[-1], t['gain'], round(t['lufs'] + 20 * math.log10(t['gain'] * life['volumes']['beds']), 1), cooked(t['asset']), *heard_cols('bed', t['asset'])])
        loud['beds'].append(t['lufs'] + 20 * math.log10(t['gain'] * life['volumes']['beds']))
    write_csv(out / 'coverage_life.csv', ['kind', 'surface/bed', 'asset', 'gain', 'in-game LUFS (file)', 'cooked', 'heard (sweep)', 'sweep RMS dBFS', 'sweep LUFS', 'sweep peak dBFS'], lrows)

    # ---- measured loudness per category from the sweep recording
    measured = defaultdict(list)
    peaks = defaultdict(list)
    for (kind, asset), h in heard.items():
        if h['lufs'] is not None:
            measured[kind].append(h['lufs'])
        peaks[kind].append(h['peak_db'])
    cache_p.write_text(json.dumps(cache))

    # ---- summary
    s = []
    s.append('# Audio coverage (generated by Scripts/AudioQA/audio_coverage.py)\n')
    nsfx = [r for r in rows if r[7] == 'approved']
    used = [r for r in rows if r[2] or r[4] or r[5]]
    s.append(f'- 1997 sound ids used by a script or the engine: {len(used)}; with an approved take: {sum(1 for r in used if r[7] == "approved")}; '
             f'rejected (silent by the owner\'s review): {[r[0] for r in used if r[7] == "REJECTED"]}; none: {[r[0] for r in used if r[7] == "none"]}.')
    if heard:
        s.append(f'- SFX heard in the sweep: {sum(1 for r in nsfx if r[10] == "yes")}/{len(nsfx)}; not heard: {[r[0] for r in nsfx if r[10] == "NO"]}.')
        takes = {v['asset'] for v in approved['music'].values()}
        heard_m = {a for (k, a), h in heard.items() if k == 'music' and h['heard']}
        cued = {r[4] for r in mrows if r[0] != 'screen override'}
        unused = sorted(t.split('.')[-1] for t in takes if t.split('.')[-1] not in cued)
        s.append(f'- Music takes heard: {len(heard_m & takes)} of {len(takes)}; cues that resolve to no take (silent): {[r[1] for r in mrows if str(r[4]).startswith("UNRESOLVED")]}; '
                 f'takes no active 1997 cue reaches (their playmidi calls are commented out in the 1997 scripts): {unused}.')
        s.append(f'- Voice lines in the sweep: {len(vrows)}, heard {sum(1 for r in vrows if r[6] == "yes")}; voices covered: {len({r[1] for r in vrows})}.')
        s.append(f'- Life takes heard: {sum(1 for r in lrows if r[6] == "yes")}/{len(lrows)}.')
    if listing:
        s.append(f'- Cooked into the package: SFX {sum(1 for r in nsfx if r[9] == "yes")}/{len(nsfx)}, voice {all_cooked.get("yes", 0)}/{len(lines)}, '
                 f'life {sum(1 for r in lrows if r[5] == "yes")}/{len(lrows)}.')
    if game:
        s.append(f'- Gameplay run: {len(game)} playback events; distinct SFX {len({k for (kd, k) in game_count if kd == "sfx"})}, music {len({k for (kd, k) in game_count if kd == "music"})}, '
                 f'voice lines {len(game_voice)}, warp sounds {sum(1 for e in game if e[0] == "warp")}, bed changes {sum(1 for e in game if e[0] == "bed")}.')
    s.append('\n## Loudness per category (integrated LUFS)\n')
    s.append('| category | takes as delivered x category volume (before mix.json): min / median / max (n) | measured in the sweep recording, with mix.json gains: min / median / max (n) | sweep peak max dBFS |')
    s.append('|---|---|---|---|')
    for cat, mk in [('sfx', 'sfx'), ('music', 'music'), ('voice', 'voice'), ('steps', 'step'), ('beds', 'bed')]:
        a1, a2 = stat(loud[cat]), stat(measured[mk])
        pk = max(peaks[mk]) if peaks[mk] else ''
        s.append(f'| {cat} | {a1[0]} / {a1[1]} / {a1[2]} ({a1[3]}) | {a2[0]} / {a2[1]} / {a2[2]} ({a2[3]}) | {pk if pk == "" else round(pk, 1)} |')
    (out / 'COVERAGE.md').write_text('\n'.join(s) + '\n')
    print('\n'.join(s))
    return 0


def write_csv(path, header, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(header); w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--out', required=True)
    p.add_argument('--voice-lines', type=int, default=200)
    p.add_argument('--music-seconds', type=float, default=8.0)
    p.add_argument('--traces', default='', help='folder with the probe traces (stonebrook_probe_trace.txt, probe_chN_trace.txt): story order of the lines')
    t = sub.add_parser('table')
    t.add_argument('--root', default=str(REPO))
    t.add_argument('--assets', default=str(PROJECT), help='a checkout whose SourceAssets/Audio holds real (LFS-pulled) files')
    t.add_argument('--log'); t.add_argument('--recording'); t.add_argument('--rate', type=int, default=48000); t.add_argument('--channels', type=int, default=2)
    t.add_argument('--gameplay-log'); t.add_argument('--listing')
    t.add_argument('--voice-loudness-all', action='store_true', help='measure all 2,088 voice sources (slow), not only the swept ones')
    t.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'plan':
        return make_plan(a)
    a.assets = str(Path(a.assets).resolve())
    return make_table(a)


if __name__ == '__main__':
    sys.exit(main())
