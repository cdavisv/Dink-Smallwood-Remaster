from pathlib import Path
import hashlib,json,os,subprocess,time
r=Path(__file__).resolve().parents[2];o=r/'Saved/BasketReviewed/Full151'
def snap():
 paths=set()
 for directory in ['Content','ImportData','Source','Config','Scripts','SourceAssets']:
  paths.update(p for p in (r/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
 for directory in ['Plugins','Binaries']:
  paths.update(p for p in (r/directory).rglob('*') if p.is_file() and not {'Intermediate','__pycache__'}.intersection(p.parts) and (directory=='Binaries' or 'Source' in p.parts or 'Config' in p.parts or p.suffix in {'.so','.modules','.uplugin'}))
 paths.update([r/'AGENTS.md',r/'DinkRemaster.uproject'])
 return {str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
before=snap();(o/'before.json').write_text(json.dumps(before,indent=2)+'\n')
saves={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (r/'Saved').rglob('*.sav') if not p.is_relative_to(o)}
(o/'old_saves_before.json').write_text(json.dumps(saves,indent=2)+'\n')
env=dict(os.environ,UE_ROOT=str(o/'EngineWrapper'),DINK_TEST_RUN='basket_native151',XDG_CONFIG_HOME=str(o/'Config'));start=time.time()
with (o/'stdout.log').open('w') as log:process=subprocess.run(['Scripts/test.sh','Dink'],cwd=r,env=env,stdout=log,stderr=subprocess.STDOUT)
after=snap();(o/'after.json').write_text(json.dumps(after,indent=2)+'\n');changed=[p for p in before.keys()|after.keys() if before.get(p)!=after.get(p)]
savediff=[p for p,h in saves.items() if not Path(p).is_file() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
report=json.loads((r/'Saved/Automation/basket_native151/index.json').read_text(encoding='utf-8-sig'))
v={'passed':process.returncode==0 and report['failed']==0 and not changed and not savediff,'returncode':process.returncode,'seconds':time.time()-start,'tests':len(report['tests']),'failed':report['failed'],'warning_tests':report['succeededWithWarnings'],'frozen_inputs':len(before),'changed_inputs':changed,'old_save_changes':savediff,'new_saves':[str(p.relative_to(o)) for p in (o/'User').rglob('*.sav')],'scope':'Merged PR16 camera and PR15/17 source plus reviewed PhotorealBasketV1 native assets/two mesh references; full NullRHI native suite. Native source/tools/art/ledger/content/import fixtures/modules/config unchanged throughout. Docs excluded.'}
(o/'verification.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v,indent=2),flush=True);raise SystemExit(0 if v['passed'] else 1)
