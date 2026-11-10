#!/usr/bin/env python3
"""Build voice_takes_review.html: every generated voice take, grouped by voice, with
keep/redo verdicts kept in the browser (localStorage) and exportable as CSV.

    python3 tools/build_takes_review.py            # from SourceAssets/Audio/Voice
    python3 -m http.server 8765                    # then open http://localhost:8765/voice_takes_review.html

Keys while listening: Space play/pause, K keep (and advance), R redo (and advance),
N next, P previous. "Auto-advance" starts the next take when one ends.
Verdicts: localStorage key `dink_voice_verdicts` = {line id: {v: "keep"|"redo", note}}.
`tools/apply_verdicts.py verdicts.csv` writes them back to voice_lines.csv / the ledger.
"""
import csv, html, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

voices = {r["voice"]: r for r in csv.DictReader(open("voices.csv", encoding="utf-8"))}
lines = list(csv.DictReader(open("voice_lines.csv", encoding="utf-8")))

by_voice = {}
for r in lines:
    v = r["voice"]
    if not v:
        continue
    path = f"{v}/{r['id']}.mp3"
    if not os.path.exists(path):
        continue
    by_voice.setdefault(v, []).append({
        "id": r["id"], "script": r["script"], "character": r["character"],
        "kind": r["kind"], "text": r["text"], "tts": r["tts_text"], "src": path,
    })

order = sorted(by_voice, key=lambda v: (v != "dink", -len(by_voice[v]), v))
data = {v: {"desc": voices.get(v, {}).get("description", ""), "lines": by_voice[v]} for v in order}
total = sum(len(d["lines"]) for d in data.values())

page = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Voice takes review</title>
<style>
:root{--bg:#f7f5f0;--fg:#1d1b17;--mute:#6b665c;--card:#fff;--line:#e3dfd6;--keep:#2d7a3a;--redo:#b23a2a;--acc:#5a4ad1}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#15140f;--fg:#ece8df;--mute:#9b968b;--card:#1f1d17;--line:#33302a;--keep:#5ec46f;--redo:#ef6a57;--acc:#9b8cff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif;display:grid;grid-template-columns:240px 1fr;min-height:100vh}
nav{border-right:1px solid var(--line);padding:12px;position:sticky;top:0;height:100vh;overflow:auto}
nav h1{font-size:15px;margin:0 0 8px}nav button{display:block;width:100%;text-align:left;background:none;border:0;color:var(--fg);padding:4px 6px;border-radius:6px;cursor:pointer;font:inherit}
nav button.on{background:var(--card);outline:1px solid var(--line)}nav small{color:var(--mute);float:right}
main{padding:16px 24px 50vh}header{position:sticky;top:0;background:var(--bg);padding:8px 0 10px;border-bottom:1px solid var(--line);z-index:2}
header h2{margin:0 0 4px;font-size:18px}header p{margin:0;color:var(--mute);font-size:13px;max-width:70em}
.bar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:8px;font-size:13px}.bar button,.bar label{font:inherit}
.bar button{padding:4px 10px;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:6px;cursor:pointer}
.take{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin:10px 0;display:grid;grid-template-columns:1fr auto;gap:6px 14px}
.take.cur{outline:2px solid var(--acc)}.take .who{font-size:12px;color:var(--mute)}.take .txt{margin:2px 0 6px;white-space:pre-wrap}
.take audio{width:100%;height:32px}.take .v{display:flex;flex-direction:column;gap:6px;min-width:150px}
.take .v button{font:inherit;padding:5px 8px;border-radius:6px;border:1px solid var(--line);background:none;color:var(--fg);cursor:pointer}
.take.keep .v .k,.take .v .k:hover{border-color:var(--keep);color:var(--keep)}.take.redo .v .r,.take .v .r:hover{border-color:var(--redo);color:var(--redo)}
.take.keep{border-left:4px solid var(--keep)}.take.redo{border-left:4px solid var(--redo)}
.take input{font:inherit;padding:4px 6px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);width:100%}
.help{color:var(--mute);font-size:12px}
@media(max-width:800px){body{grid-template-columns:1fr}nav{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}}
</style>
<body>
<nav><h1>Voices <small id="tot"></small></h1><div id="nav"></div></nav>
<main>
<header>
<h2 id="vname"></h2><p id="vdesc"></p>
<div class="bar">
<button id="play">Play / pause (Space)</button>
<label><input type="checkbox" id="auto" checked> Auto-advance</label>
<label><input type="checkbox" id="unrev"> Only unreviewed</label>
<label>Sample <select id="samp"><option value="0">all</option><option value="10">10</option><option value="25">25</option></select></label>
<button id="exp">Export verdicts CSV</button>
<span id="stat" class="help"></span>
</div>
<div class="help">K = keep and next, R = redo and next, N / P = next / previous. Type a note in the box when a take needs a redo (what is wrong: pace, emphasis, pronunciation, wrong tone).</div>
</header>
<div id="list"></div>
</main>
<script>
const DATA = __DATA__;
const KEY = 'dink_voice_verdicts';
let V = {}; try { V = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { V = {}; }
function save() { try { localStorage.setItem(KEY, JSON.stringify(V)); } catch (e) {} stat(); }
const voices = Object.keys(DATA);
let cur = voices[0], idx = 0, shown = [];
const $ = s => document.querySelector(s);
function stat() {
  const all = voices.flatMap(v => DATA[v].lines);
  const n = all.filter(l => V[l.id] && V[l.id].v).length, r = all.filter(l => V[l.id] && V[l.id].v === 'redo').length;
  $('#stat').textContent = `${n} of ${all.length} reviewed, ${r} marked redo`;
  $('#tot').textContent = all.length;
  document.querySelectorAll('#nav button').forEach(b => {
    const v = b.dataset.v, L = DATA[v].lines, k = L.filter(l => V[l.id] && V[l.id].v).length;
    b.querySelector('small').textContent = `${k}/${L.length}`;
  });
}
function nav() {
  $('#nav').innerHTML = voices.map(v => `<button data-v="${v}" class="${v === cur ? 'on' : ''}">${v} <small></small></button>`).join('');
  document.querySelectorAll('#nav button').forEach(b => b.onclick = () => { cur = b.dataset.v; idx = 0; render(); });
}
function seeded(arr, n) { // deterministic sample so the same 10 come back next session
  let s = 2166; const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { s = (s * 9301 + 49297) % 233280; const j = Math.floor(s / 233280 * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a.slice(0, n).sort((x, y) => arr.indexOf(x) - arr.indexOf(y));
}
function render() {
  nav();
  const d = DATA[cur]; $('#vname').textContent = `${cur} (${d.lines.length} takes)`; $('#vdesc').textContent = d.desc;
  let L = d.lines; const n = +$('#samp').value; if (n) L = seeded(L, n);
  if ($('#unrev').checked) L = L.filter(l => !(V[l.id] && V[l.id].v));
  shown = L; idx = Math.min(idx, Math.max(0, L.length - 1));
  $('#list').innerHTML = L.map((l, i) => {
    const v = V[l.id] || {};
    return `<div class="take ${v.v || ''}" data-i="${i}" id="t${i}">
<div><div class="who">${esc(l.character)} · <code>${l.id}</code> · ${l.kind}</div>
<div class="txt">${esc(l.text)}</div>
<audio preload="none" controls src="${l.src}"></audio></div>
<div class="v"><button class="k">Keep (K)</button><button class="r">Redo (R)</button><input placeholder="note" value="${esc(v.note || '')}"></div></div>`;
  }).join('') || '<p class="help">Nothing to show with these filters.</p>';
  document.querySelectorAll('.take').forEach(t => {
    const i = +t.dataset.i, l = L[i], a = t.querySelector('audio');
    t.querySelector('.k').onclick = () => mark(i, 'keep');
    t.querySelector('.r').onclick = () => mark(i, 'redo');
    t.querySelector('input').onchange = e => { V[l.id] = Object.assign(V[l.id] || {}, { note: e.target.value, voice: cur }); save(); };
    a.onplay = () => { idx = i; hl(false); document.querySelectorAll('audio').forEach(o => { if (o !== a) o.pause(); }); };
    a.onended = () => { if ($('#auto').checked) go(i + 1, true); };
  });
  hl(false); stat();
}
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]); }
function hl(scroll) { document.querySelectorAll('.take').forEach(t => t.classList.toggle('cur', +t.dataset.i === idx)); const t = $('#t' + idx); if (t && scroll) t.scrollIntoView({ block: 'center', behavior: 'smooth' }); }
function mark(i, v) { const l = shown[i]; if (!l) return; V[l.id] = Object.assign(V[l.id] || {}, { v, voice: cur }); save(); const t = $('#t' + i); if (t) { t.classList.remove('keep', 'redo'); t.classList.add(v); } go(i + 1, true); }
function go(i, play) { if (i < 0 || i >= shown.length) return; idx = i; hl(true); const a = $('#t' + i + ' audio'); if (a && play) { a.currentTime = 0; a.play(); } }
function toggle() { const a = $('#t' + idx + ' audio'); if (!a) return; a.paused ? a.play() : a.pause(); }
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (e.code === 'Space') { e.preventDefault(); toggle(); }
  else if (e.key === 'k' || e.key === 'K') mark(idx, 'keep');
  else if (e.key === 'r' || e.key === 'R') mark(idx, 'redo');
  else if (e.key === 'n' || e.key === 'N') go(idx + 1, true);
  else if (e.key === 'p' || e.key === 'P') go(idx - 1, true);
});
$('#play').onclick = toggle; $('#unrev').onchange = render; $('#samp').onchange = render;
$('#exp').onclick = () => {
  const rows = [['id', 'voice', 'verdict', 'note']];
  voices.forEach(v => DATA[v].lines.forEach(l => { const x = V[l.id]; if (x && (x.v || x.note)) rows.push([l.id, v, x.v || '', x.note || '']); }));
  const csv = rows.map(r => r.map(c => '"' + String(c).replace(/"/g, '""') + '"').join(',')).join('\\n');
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); a.download = 'voice_verdicts.csv'; a.click();
};
render();
</script>
</body></html>
"""
out = page.replace("__DATA__", json.dumps(data, ensure_ascii=False))
open("voice_takes_review.html", "w", encoding="utf-8").write(out)
print(f"voice_takes_review.html: {total} takes in {len(data)} voices")
