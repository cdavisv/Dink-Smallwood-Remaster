from pathlib import Path
import subprocess,os,json,time
root=Path(__file__).resolve().parents[2];out=root/'Saved/BasketReviewed/Native';out.mkdir(parents=True,exist_ok=True)
engine=Path('/home/artist/UnrealEngine/UE_5.8.4/Engine/Binaries/Linux/UnrealEditor-Cmd')
results=[]
for mode in ['preflight','import','verify']:
 report=out/(mode+'.json');assert not report.exists(),report
 env=dict(os.environ,DINK_BASKET_MODE=mode,DINK_BASKET_SOURCE=str(root/'SourceAssets/Art/Stonebrook/Refinements/PhotorealBasketV1'),DINK_BASKET_REPORT=str(report),DINK_BASKET_IMPORT_RECEIPT=str(out/'import.json'))
 env.pop('DISPLAY',None);env.pop('WAYLAND_DISPLAY',None)
 cmd=[str(engine),str(root/'DinkRemaster.uproject'),'-ExecutePythonScript='+str(root/'Scripts/import_photoreal_basket.py'),'-nullrhi','-unattended','-nosplash','-nopause','-nosound','-notraceserver','-ddc=InstalledNoZenLocalFallback','-LocalDataCachePath='+str(root/'Saved/NativeProps/DDC'),'-UserDir='+str(out/(mode+'User')),'-stdout','-FullStdOutLogOutput']
 start=time.time()
 with (out/(mode+'.log')).open('w') as log:r=subprocess.run(cmd,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
 data=json.loads(report.read_text()) if report.exists() else {}
 row={'mode':mode,'returncode':r.returncode,'seconds':time.time()-start,'passed':r.returncode==0 and data.get('passed')is True};results.append(row)
 (out/'runner.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(row),flush=True)
 if not row['passed']:raise SystemExit(1)
