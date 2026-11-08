#!/usr/bin/env python3
"""Capture approved playback from an existing private audio-enabled Dink QA game.

Routes only the verified QA PID to its requested private sink; never changes the
default sink or other applications. Real F input drives the SFX checks.
"""
import sys,time,json,subprocess,signal,wave,array,math,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import playtest_desktop as d
import playtest_interactions as q
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',type=Path,default=Path('Saved/Playtest/evidence/audio-private-final'))
args=parser.parse_args()
root=Path(__file__).resolve().parent.parent;out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
d.use_private_display(':189','/tmp/dink-qa-tools/xauthority');d.focus(d.window())
game=json.loads(Path('/tmp/dink-qa-tools/game.json').read_text());assert game['audio_enabled'] and game['pulse_sink']=='dink_qa_private'
sinks=json.loads(subprocess.check_output(['pactl','-f','json','list','sinks'],text=True));sink=next(x for x in sinks if x['name']=='dink_qa_private')
inputs=json.loads(subprocess.check_output(['pactl','-f','json','list','sink-inputs'],text=True));ours=[x for x in inputs if x['properties'].get('application.process.id')==str(game['game_pid'])]
assert ours,'No audio stream belongs to the verified QA game PID'
adjusted=[]
for stream in ours:
 if stream['sink']!=sink['index']:
  subprocess.run(['pactl','move-sink-input',str(stream['index']),'dink_qa_private'],check=True);adjusted.append(stream['index'])
inputs=json.loads(subprocess.check_output(['pactl','-f','json','list','sink-inputs'],text=True));ours=[x for x in inputs if x['properties'].get('application.process.id')==str(game['game_pid'])]
assert ours and all(x['sink']==sink['index'] for x in ours),'QA game is not exclusively routed to the private sink'
(out/'sink-inputs.json').write_text(json.dumps({'game':game,'sink':sink,'game_inputs':ours,'routing_adjusted_streams':adjusted},indent=2)+'\n')
log=Path('/tmp/dink-qa-private.log');before=q.story(log)
audio_before=q.command_output('dink.Audio',log)
components=q.command_output('getall AudioComponent Sound',log);(out/'audio-components.log').write_text(components)
path=out/'home-music-and-real-fists.wav'
action_offset=log.stat().st_size
record=subprocess.Popen(['parecord','--latency-msec=50','--process-time-msec=10','--device=dink_qa_private.monitor','--file-format=wav','--format=s16le','--rate=48000','--channels=2',str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
try:
 time.sleep(2);d.run('wtype','-k','f');time.sleep(2);d.run('wtype','-k','f');time.sleep(2)
finally:
 record.send_signal(signal.SIGINT);record.wait(timeout=5)
after=q.story(log)
audio_after=q.command_output('dink.Audio',log)
with log.open() as handle:
 handle.seek(action_offset);action_log=handle.read()
(out/'actual-playback.log').write_text(audio_before+audio_after+action_log)
with wave.open(str(path)) as wav:
 params={'channels':wav.getnchannels(),'sample_rate':wav.getframerate(),'sample_width':wav.getsampwidth(),'frames':wav.getnframes()};samples=array.array('h',wav.readframes(wav.getnframes()))
baseline=samples[:int(params['sample_rate']*params['channels']*1.5)];baseline_rms=math.sqrt(sum(v*v for v in baseline)/max(len(baseline),1));music_component_present='/MUS_' in components
peak=max(abs(v) for v in samples);rms=math.sqrt(sum(v*v for v in samples)/len(samples));seconds=params['frames']/params['sample_rate'];verified=q.advanced(before,after,'item-fst','use')
receipt={'result':'PASS' if peak>100 and rms>10 and baseline_rms>10 and music_component_present and seconds>5 and verified else 'FAIL','params':params,'seconds':seconds,'peak':peak,'rms':rms,'music_baseline_rms':baseline_rms,'approved_music_component_present':music_component_present,'rms_dbfs':20*math.log10(max(rms,1)/32768),'f_input_verified':verified,'private_sink_pid_verified':True,'audio_before':audio_before,'audio_after':audio_after,'playback_log':str(out/'actual-playback.log'),'before':before,'after':after,'wav':str(path)}
(out/'capture.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ['before','after']},indent=2),flush=True)
if receipt['result']!='PASS':raise SystemExit(1)
