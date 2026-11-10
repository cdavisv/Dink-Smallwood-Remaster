#!/usr/bin/env python3
"""Known UE5.8.4 ShaderPrint workaround; no Engine host edits. See DXC issue8417."""
from pathlib import Path
import argparse,hashlib,json,os,stat,subprocess,tempfile
ORIGINAL_SHA='69e3599c3bd8277a114f565a77f4e99f84bfa48c6d036b79d330cb17a4a390f2'
FIXED_SHA='c832c56f04778bab2a8f73adbb3b905d84619693113cfd36da1de3ea8dcabd64'
ORIGINAL_CONDITION=b'#if ES3_1_PROFILE || (COMPILER_HLSL && !COMPILER_DXC)'
FIXED_CONDITION=ORIGINAL_CONDITION+b' || COMPILER_VULKAN'
BWRAP=Path('/usr/bin/bwrap')
def _need(ok,message):
    if not ok:raise ValueError(message)
def _snapshot(path):
    path=Path(path);_need(path.resolve()==path and not path.is_symlink(),'Shader source must be a physical ordinary file')
    s=path.stat();_need(stat.S_ISREG(s.st_mode),'Shader source is not a regular file')
    return dict(device=s.st_dev,inode=s.st_ino,size=s.st_size,mode=stat.S_IMODE(s.st_mode),mtime_ns=s.st_mtime_ns,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def _classify(data):
    digest=hashlib.sha256(data).hexdigest()
    if digest==FIXED_SHA:return 'already_fixed',None
    _need(digest==ORIGINAL_SHA,'Unreviewed ShaderPrint source revision; no automatic Engine modification')
    _need(data.count(ORIGINAL_CONDITION)==1,'Expected unique ShaderPrint condition absent')
    patched=data.replace(ORIGINAL_CONDITION,FIXED_CONDITION,1)
    _need(hashlib.sha256(patched).hexdigest()==FIXED_SHA,'Unexpected ShaderPrint patch bytes')
    return 'private_overlay',patched
def _namespace_command(engine,private,command,cwd):
    return [str(BWRAP),'--die-with-parent','--cap-drop','ALL','--bind','/','/',
            '--ro-bind',str(private),str(engine/'Shaders/Private/ShaderPrint.ush'),
            '--chdir',str(cwd),'--',*command]
def execute(engine,command):
    engine=Path(engine).expanduser().resolve();command=list(command)
    _need(command and Path(command[0]).resolve()==engine/'Build/BatchFiles/RunUAT.sh','Only the selected Engine RunUAT script may be wrapped')
    target=engine/'Shaders/Private/ShaderPrint.ush';before=_snapshot(target);mode,patched=_classify(target.read_bytes())
    if mode=='private_overlay':
        version=json.loads((engine/'Build/Build.version').read_text())
        _need([version.get(n)for n in ['MajorVersion','MinorVersion','PatchVersion']]==[5,8,4],'Workaround source is reviewed only for UE5.8.4')
        _need(BWRAP.is_file(),'The Linux ShaderPrint workaround requires bubblewrap')
    print('ShaderPrint workaround '+json.dumps(dict(mode=mode,host=before),sort_keys=True),flush=True)
    try:
        if mode=='already_fixed':result=subprocess.run(command,check=False)
        else:
            with tempfile.TemporaryDirectory(prefix='dink-shaderprint-')as directory:
                private=Path(directory)/'ShaderPrint.ush';private.write_bytes(patched);private.chmod(0o400)
                result=subprocess.run(_namespace_command(engine,private,command,Path.cwd()),check=False)
    finally:
        _need(_snapshot(target)==before,'Host ShaderPrint identity/content changed during packaging; outputs are not accepted')
    print('ShaderPrint host source unchanged',flush=True)
    return result.returncode if result.returncode>=0 else 128-result.returncode

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',required=True,type=Path);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();command=a.command[1:]if a.command[:1]==['--']else a.command
    try:return execute(a.engine,command)
    except ValueError as error:p.exit(2,'ShaderPrint workaround refused: '+str(error)+'\n')
if __name__=='__main__':raise SystemExit(main())
