#!/usr/bin/env python3
"""Build SourceAssets/Audio/review.html, an offline page for auditioning the generated audio.

Reads (all relative to SourceAssets/):
  asset_ledger.csv, Audio/SFX/quality_report.csv, Audio/Music/quality_report.csv,
  Audio/Music/loop_report.csv, Audio/Music/README.md (for the "weakest matches" warning).
Writes Audio/review.html: one self-contained file (inline CSS and JS, no external requests) that
links to the MP3/WAV files by relative path. Python 3 standard library only.

    python3 SourceAssets/Audio/tools/build_review_page.py
"""
import csv
import html
import re
import sys
from pathlib import Path

AUDIO = Path(__file__).resolve().parent.parent
ROOT = AUDIO.parent  # SourceAssets/
OUT = AUDIO / "review.html"


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def esc(s):
    return html.escape(s or "", quote=True)


def weakest_cues():
    """Cue numbers named in the README sentence about the weakest tail/head matches."""
    text = (AUDIO / "Music" / "README.md").read_text(encoding="utf-8")
    m = re.search(r"Cues\s+([0-9, and]+?)\s+have the weakest", text)
    if not m:
        return set()
    return set(re.findall(r"\d+", m.group(1)))


def main():
    ledger = {r["asset_path"]: r for r in read_csv(ROOT / "asset_ledger.csv")}
    sfx_q = read_csv(AUDIO / "SFX" / "quality_report.csv")
    mus_q = read_csv(AUDIO / "Music" / "quality_report.csv")
    loops = {r["cue"]: r for r in read_csv(AUDIO / "Music" / "loop_report.csv")}
    weak = weakest_cues()

    # ---- SFX rows, grouped by slot ----
    slots = {}
    for r in sfx_q:
        slots.setdefault((r["slot"], r["cue"]), {})[r["variant"]] = r
    sfx_rows = []
    for (slot, cue), takes in sorted(slots.items()):
        a_path = f"SourceAssets/Audio/SFX/delivered/{slot}_{cue}_a.mp3"
        led = ledger.get(a_path, {})
        players = []
        flags = []
        for v in ("a", "b"):
            q = takes.get(v)
            rel = f"SFX/delivered/{slot}_{cue}_{v}.mp3"
            if q is None:
                players.append(f"<div class='take'>take {v}: missing</div>")
                continue
            clip = int(q["clip_samples"] or 0)
            cls = "warn" if (clip or q["flags"]) else ""
            stats = f"peak {esc(q['peak_db'])} dB, clip {clip}, {esc(q['measured_s'])} s"
            players.append(
                f"<div class='take'><b>{v}</b> <span class='{cls}'>{stats}</span><br>"
                f"<audio controls preload='none' src='{esc(rel)}'></audio></div>")
            if q["flags"]:
                flags.append(f"{v}: {q['flags']}")
        flag_html = "".join(f"<div class='warn'>{esc(f)}</div>" for f in flags)
        key = f"SourceAssets/Audio/SFX/delivered/{slot}_{cue}"  # slot id (both takes)
        sfx_rows.append(
            f"<tr class='row' data-kind='sfx' data-id='{slot}_{cue}' data-key='{esc(key)}'>"
            f"<td class='id'>{esc(slot)}</td><td><b>{esc(cue)}</b><br>"
            f"<span class='dim'>{esc(takes.get('a', takes.get('b'))['type'])}</span></td>"
            f"<td>{esc(led.get('replaces'))}</td><td class='prompt'>{esc(led.get('prompt'))}{flag_html}</td>"
            f"<td>{players[0]}{players[1]}</td>"
            f"<td class='choice'>"
            f"<label><input type='radio' name='c_{slot}_{cue}' value='a'> a</label> "
            f"<label><input type='radio' name='c_{slot}_{cue}' value='b'> b</label> "
            f"<label><input type='radio' name='c_{slot}_{cue}' value='neither'> neither (regenerate)</label><br>"
            f"<input type='text' class='note' placeholder='note' aria-label='note for {esc(cue)}'></td></tr>")

    # ---- Music rows ----
    mus_rows = []
    for r in mus_q:
        base = r["file"][:-4]  # nn_cue
        a_path = f"SourceAssets/Audio/Music/delivered/{r['file']}"
        led = ledger.get(a_path, {})
        is_loop = r["loop"] == "loop"
        lp = loops.get(base)
        extra = ""
        if is_loop:
            rel = f"Music/loops/{base}_loop.wav"
            seam = "loop report missing"
            if lp:
                seam = (f"tempo {esc(lp['tempo_bpm'])} bpm, {esc(lp['loop_start_s'])} - {esc(lp['loop_end_s'])} s "
                        f"({esc(lp['loop_length_s'])} s), seam {esc(lp['seam_level_diff_db'])} dB / "
                        f"jump {esc(lp['seam_sample_jump'])} FS, {esc(lp['result'])}, {esc(lp['method'])}")
            warn = ""
            if r["cue"] in weak:
                warn = "<div class='warn'>Weakest tail/head match (README): listen to this loop first.</div>"
            if lp and "low-confidence" in lp["notes"]:
                warn += "<div class='warn'>Low-confidence tempo estimate.</div>"
            extra = (f"<div class='take'><b>loop file</b> <span class='dim'>{seam}</span>{warn}<br>"
                     f"<audio controls preload='none' src='{esc(rel)}' class='loopaudio'></audio> "
                     f"<label><input type='checkbox' class='loopbox'> loop</label></div>")
        mus_rows.append(
            f"<tr class='row' data-kind='music' data-id='{esc(base)}' data-key='{esc(a_path)}'>"
            f"<td class='id'>{esc(r['cue'])}</td><td><b>{esc(r['name'])}</b><br>"
            f"<span class='dim'>{'loop cue' if is_loop else 'one-shot'}</span></td>"
            f"<td>{esc(led.get('replaces'))}</td><td class='prompt'>{esc(led.get('prompt'))}</td>"
            f"<td>{esc(r['duration_s'])} s<br><span class='dim'>peak {esc(r['peak_db'])} dB</span></td>"
            f"<td><div class='take'><b>delivered mp3</b><br>"
            f"<audio controls preload='none' src='Music/delivered/{esc(r['file'])}'></audio></div>{extra}</td>"
            f"<td class='choice'>"
            f"<label><input type='radio' name='c_{esc(base)}' value='keep'> keep</label> "
            f"<label><input type='radio' name='c_{esc(base)}' value='regenerate'> regenerate</label> "
            f"<label><input type='radio' name='c_{esc(base)}' value='needs loop retune'> needs loop retune</label><br>"
            f"<input type='text' class='note' placeholder='note' aria-label='note for {esc(r['name'])}'></td></tr>")

    page = TEMPLATE.replace("@@SFX@@", "\n".join(sfx_rows)).replace("@@MUSIC@@", "\n".join(mus_rows))
    page = page.replace("@@NSFX@@", str(len(sfx_rows))).replace("@@NMUS@@", str(len(mus_rows)))
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({len(sfx_rows)} SFX slots, {len(mus_rows)} music cues)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dink remaster audio review</title>
<style>
:root{color-scheme:light dark;--bg:#fff;--fg:#1a1a1a;--dim:#666;--line:#ccc;--warn:#b00020;--sel:#e8f2ff}
@media (prefers-color-scheme:dark){:root{--bg:#161616;--fg:#e6e6e6;--dim:#999;--line:#444;--warn:#ff7a8a;--sel:#1d2b3d}}
body{margin:0;font:14px/1.4 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:8px 16px;z-index:5}
h1{font-size:18px;margin:0 0 4px}h2{margin:24px 16px 8px}
button{font:inherit;padding:3px 10px;margin-right:6px}
#status{color:var(--dim);margin-left:8px}
table{border-collapse:collapse;width:100%}
th,td{border-top:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left}
th{position:static;font-size:12px;color:var(--dim)}
td.id{font-variant-numeric:tabular-nums;white-space:nowrap}
td.prompt{max-width:34em;font-size:13px}
.dim{color:var(--dim);font-size:12px}.warn{color:var(--warn);font-size:12px}
.take{margin-bottom:6px}audio{width:260px;height:32px;vertical-align:middle}
td.choice label{white-space:nowrap;margin-right:6px}
input.note{width:95%;margin-top:4px}
tr.done{background:var(--sel)}
p.intro{margin:8px 16px;color:var(--dim)}
</style></head><body>
<header><h1>Dink remaster audio review</h1>
<button id="exp" type="button">Export choices</button>
<button id="imp" type="button">Import choices</button>
<input id="file" type="file" accept=".csv,text/csv" hidden>
<button id="clr" type="button">Clear all</button><span id="status"></span>
<label style="margin-left:12px"><input type="checkbox" id="solo" checked> one player at a time</label>
</header>
<p class="intro">Pick by ear; choices and notes are saved in this browser (localStorage) as you go. Export to <code>audio_choices.csv</code>, then apply with <code>tools/apply_choices.py --choices /path/audio_choices.csv</code>. The project retains approved decisions and notes separately from the delivered originals.</p>
<h2>Sound effects (@@NSFX@@)</h2>
<table id="sfx"><thead><tr><th>Slot</th><th>Cue</th><th>Replaces</th><th>Prompt / flags</th><th>Takes</th><th>Choice</th></tr></thead><tbody>
@@SFX@@
</tbody></table>
<h2>Music (@@NMUS@@)</h2>
<table id="music"><thead><tr><th>Nn</th><th>Cue</th><th>Replaces</th><th>Prompt</th><th>Length</th><th>Audio</th><th>Rating</th></tr></thead><tbody>
@@MUSIC@@
</tbody></table>
<script>
(function(){
var PFX='dinkaudio:', rows=[].slice.call(document.querySelectorAll('tr.row'));
function lsGet(k){try{return localStorage.getItem(k)}catch(e){return null}}
function lsSet(k,v){try{localStorage.setItem(k,v)}catch(e){}}
function lsDel(k){try{localStorage.removeItem(k)}catch(e){}}
function state(tr){
  var r=tr.querySelector('input[type=radio]:checked');
  return {choice:r?r.value:'', note:tr.querySelector('.note').value};
}
function apply(tr,s){
  [].forEach.call(tr.querySelectorAll('input[type=radio]'),function(r){r.checked=(r.value===s.choice)});
  tr.querySelector('.note').value=s.note||'';
  tr.classList.toggle('done',!!s.choice);
}
function save(tr){
  var s=state(tr);tr.classList.toggle('done',!!s.choice);
  if(!s.choice&&!s.note)lsDel(PFX+tr.dataset.key);else lsSet(PFX+tr.dataset.key,JSON.stringify(s));
  count();
}
function count(){
  var n=rows.filter(function(t){return t.classList.contains('done')}).length;
  document.getElementById('status').textContent=n+' of '+rows.length+' decided';
}
rows.forEach(function(tr){
  var v=lsGet(PFX+tr.dataset.key);
  if(v){try{apply(tr,JSON.parse(v))}catch(e){}}
  tr.addEventListener('change',function(){save(tr)});
  tr.addEventListener('input',function(){save(tr)});
  var lb=tr.querySelector('.loopbox');
  if(lb){lb.addEventListener('change',function(){tr.querySelector('.loopaudio').loop=lb.checked})}
});
count();
document.addEventListener('play',function(e){
  if(!document.getElementById('solo').checked)return;
  [].forEach.call(document.querySelectorAll('audio'),function(a){if(a!==e.target&&!a.paused)a.pause()});
},true);
function q(s){return '"'+String(s).replace(/"/g,'""')+'"'}
document.getElementById('exp').onclick=function(){
  var out=['kind,id,choice,note'];
  rows.forEach(function(tr){var s=state(tr);
    if(s.choice||s.note)out.push([tr.dataset.kind,tr.dataset.id,s.choice,s.note].map(q).join(','));});
  var blob=new Blob([out.join('\r\n')+'\r\n'],{type:'text/csv'});
  var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='audio_choices.csv';
  document.body.appendChild(a);a.click();document.body.removeChild(a);
  setTimeout(function(){URL.revokeObjectURL(a.href)},2000);
};
function parseCSV(t){
  var rows=[],row=[],f='',i=0,inq=false,c;
  for(;i<t.length;i++){c=t[i];
    if(inq){if(c=='"'){if(t[i+1]=='"'){f+='"';i++}else inq=false}else f+=c}
    else if(c=='"')inq=true;
    else if(c==','){row.push(f);f=''}
    else if(c=='\n'||c=='\r'){if(c=='\r'&&t[i+1]=='\n')i++;row.push(f);f='';rows.push(row);row=[]}
    else f+=c;}
  if(f!==''||row.length){row.push(f);rows.push(row)}
  return rows;
}
document.getElementById('imp').onclick=function(){document.getElementById('file').click()};
document.getElementById('file').onchange=function(ev){
  var file=ev.target.files[0];if(!file)return;
  var rd=new FileReader();
  rd.onload=function(){
    var data=parseCSV(String(rd.result).replace(/^﻿/,'')),n=0,miss=0;
    var idx={};rows.forEach(function(tr){idx[tr.dataset.kind+'|'+tr.dataset.id]=tr});
    data.slice(1).forEach(function(r){
      var tr=idx[r[0]+'|'+r[1]];
      if(!tr){if(r.length>1)miss++;return}
      var ok=[].some.call(tr.querySelectorAll('input[type=radio]'),function(x){return x.value===r[2]});
      apply(tr,{choice:ok?r[2]:'',note:r[3]||''});save(tr);n++;
    });
    document.getElementById('status').textContent='imported '+n+' rows'+(miss?(', '+miss+' unknown ids skipped'):'');
    ev.target.value='';
  };
  rd.readAsText(file);
};
document.getElementById('clr').onclick=function(){
  if(!confirm('Clear all choices and notes in this browser?'))return;
  rows.forEach(function(tr){apply(tr,{choice:'',note:''});lsDel(PFX+tr.dataset.key)});count();
};
})();
</script></body></html>
"""

if __name__ == "__main__":
    sys.exit(main())
