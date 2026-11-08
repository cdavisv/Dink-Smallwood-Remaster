#!/usr/bin/env python3
"""Stage/start/inspect/stop the private Dink Xvfb session without desktop input.

Tools live in persistent ~/Work/DinkQA/Tools (DINK_QA_TOOLS overrides it).
A verified /tmp/dink-qa-tools alias keeps existing input helpers compatible.
The only accepted display is :189;
TCP is disabled and a per-session authority cookie protects its Unix socket.
No system package or desktop configuration is changed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import time

from qa_private_x11 import PrivateX11

TOOLS = Path(os.environ.get('DINK_QA_TOOLS', str(Path.home()/'Work/DinkQA/Tools'))).resolve()
AUTH = TOOLS / 'xauthority'
DISPLAY = ':189'
PACKAGE_URL = 'https://archlinux.org/packages/extra/x86_64/xorg-server-xvfb/download/'
PROJECT = Path(__file__).resolve().parent.parent


def proc_args(pid):
    path = Path(f'/proc/{pid}/cmdline')
    return path.read_bytes().rstrip(b'\0').split(b'\0') if path.exists() else []


def stage():
    TOOLS.mkdir(parents=True,exist_ok=True)
    legacy=Path('/tmp/dink-qa-tools')
    if not legacy.exists() and not legacy.is_symlink():legacy.symlink_to(TOOLS,target_is_directory=True)
    if legacy.resolve()!=TOOLS:raise SystemExit('Private QA tool alias is occupied by another directory; refusing to overwrite it.')
    binary = TOOLS / 'usr/bin/Xvfb'
    if not binary.exists():
        archive = TOOLS / 'xvfb.pkg.tar.zst'
        subprocess.run(['curl','-fL','--proto','=https',PACKAGE_URL,'-o',str(archive)],check=True)
        subprocess.run(['bsdtar','-xf',str(archive),'-C',str(TOOLS),'usr/bin/Xvfb',
                        'usr/share/licenses/xorg-server-xvfb/COPYING','usr/share/man/man1/Xvfb.1.gz'],check=True)
        (TOOLS/'tool_receipt.json').write_text(json.dumps({'source':PACKAGE_URL,
            'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()},indent=2)+'\n')
    return binary


def ensure_display():
    binary = stage()
    lock = Path('/tmp/.X189-lock')
    if lock.exists():
        pid = int(lock.read_text().strip())
        args = proc_args(pid)
        if str(binary).encode() not in args or DISPLAY.encode() not in args or not AUTH.exists():
            raise SystemExit('Display189 is occupied by a different or unverified server; refusing to reuse it.')
        return pid
    if Path('/tmp/.X11-unix/X189').exists():
        raise SystemExit('Unowned display189 socket exists; refusing to overwrite it.')
    fields = [b'',b'189',b'MIT-MAGIC-COOKIE-1',os.urandom(16)]
    AUTH.write_bytes(struct.pack('>H',65535)+b''.join(struct.pack('>H',len(v))+v for v in fields))
    AUTH.chmod(0o600)
    with (TOOLS/'xvfb.log').open('w') as output:
        process = subprocess.Popen([str(binary),DISPLAY,'-screen','0','1280x720x24',
            '-nolisten','tcp','-auth',str(AUTH),'-noreset'],stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
    for _ in range(50):
        if Path('/tmp/.X11-unix/X189').exists():return process.pid
        if process.poll() is not None:raise SystemExit('Private Xvfb failed; inspect /tmp/dink-qa-tools/xvfb.log')
        time.sleep(.1)
    raise SystemExit('Private display did not become ready in5 seconds.')


def find_game():
    try:
        backend = PrivateX11(DISPLAY,str(AUTH))
        return backend,backend.window()
    except SystemExit as error:
        if 'found 0' in str(error):return None,None
        raise


def stop_game():
    backend,window = find_game()
    if not window:
        print('No private Dink game is running.');return
    pid = window.get('pid')
    args = proc_args(pid) if pid else []
    receipt_path=TOOLS/'game.json'
    receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    if (b'-sdlvideodriver=x11' not in args or str(PROJECT/'DinkRemaster.uproject').encode() not in args or
        receipt.get('game_pid')!=pid or ('-abslog='+receipt.get('log','')).encode() not in args):
        raise SystemExit('Private window PID/project/log could not be verified against this QA session receipt; refusing to stop it.')
    backend.focus(window)
    backend.command('wtype','-k','grave','-s','350','-d','20','quit','-k','Return')
    for _ in range(100):
        if not proc_args(pid):
            print(f'Private Dink game {pid} exited.');return
        time.sleep(.1)
    # The PID and private log/X11 arguments were checked above. No broad kill.
    os.kill(pid,signal.SIGTERM)
    print(f'Sent SIGTERM only to verified private Dink game {pid} after the console-exit timeout.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','inspect','stop-game','stop-display'])
    parser.add_argument('--log',type=Path,default=PROJECT/'Saved/Playtest/private-session.log')
    parser.add_argument('--audio',action='store_true',help='Enable actual audio output for a new private session; default is silent.')
    parser.add_argument('--serial-rhi',action='store_true',help='Diagnostic only: disable RHI threading and force immediate command submission; may reduce performance.')
    parser.add_argument('--serial-vulkan-submit',action='store_true',help='Diagnostic: disable dedicated Vulkan submission/interrupt threads at startup; end-of-pipe TaskGraph work remains.')
    parser.add_argument('--pulse-sink',help='Route only this audio-enabled game to an existing private PulseAudio sink.')
    args=parser.parse_args()
    if args.pulse_sink and not args.audio:parser.error('--pulse-sink requires --audio')
    if args.action=='start':
        args.log=args.log.expanduser().resolve()
        args.log.parent.mkdir(parents=True,exist_ok=True)
        server_pid=ensure_display()
        backend,window=find_game()
        if window:
            print(json.dumps({'status':'already running','server_pid':server_pid,'game':window},indent=2));return
        env=os.environ.copy();env.pop('WAYLAND_DISPLAY',None)
        env.update({'DISPLAY':DISPLAY,'XAUTHORITY':str(AUTH),'SDL_VIDEODRIVER':'x11','MESA_VK_WSI_DEBUG':'sw'})
        if args.pulse_sink:
            env.update({'PULSE_SINK':args.pulse_sink,'SDL_AUDIODRIVER':'pulseaudio','SDL_AUDIO_DRIVER':'pulseaudio'})
        engine=Path(os.environ.get('UE_ROOT',str(Path.home()/'UnrealEngine/UE_5.8.4')))
        command=[str(engine/'Engine/Binaries/Linux/UnrealEditor'),str(PROJECT/'DinkRemaster.uproject'),
            '/Game/Dink/_Generated/Maps/L_Greybox_World','-game','-sdlvideodriver=x11','-windowed',
            '-ResX=1280','-ResY=720','-nosplash','-unattended',f'-abslog={args.log}']
        if args.serial_rhi:command.extend(['-norhithread','-forcerhibypass'])
        if args.serial_vulkan_submit:command.append('-ForceDPCVars=r.Vulkan.Submission.UseInterruptThread=0,r.Vulkan.Submission.UseSubmissionThread=0')
        if not args.audio:command.append('-nosound')
        with (TOOLS/'game.stdout.log').open('w') as output:
            process=subprocess.Popen(command,env=env,cwd=PROJECT,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        receipt={'display':DISPLAY,'server_pid':server_pid,'game_pid':process.pid,'log':str(args.log),'audio_enabled':args.audio,'pulse_sink':args.pulse_sink,'serial_rhi_diagnostic':args.serial_rhi,'serial_vulkan_submission_diagnostic':args.serial_vulkan_submit,
                 'command':command,'renderer_transport':'RADV with MESA_VK_WSI_DEBUG=sw; normal X11 swapchain, not nullrhi'}
        (TOOLS/'game.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(receipt,indent=2))
    elif args.action=='inspect':
        backend,window=find_game();print(json.dumps(window or {'status':'no private game'},indent=2))
    elif args.action=='stop-game':stop_game()
    else:
        backend,window=find_game()
        if window:raise SystemExit('Stop the private game before stopping its display.')
        lock=Path('/tmp/.X189-lock')
        if not lock.exists():print('Private display is already stopped.');return
        pid=int(lock.read_text().strip());arguments=proc_args(pid)
        if str(TOOLS/'usr/bin/Xvfb').encode() not in arguments or DISPLAY.encode() not in arguments:
            raise SystemExit('Display PID is not owned by this QA setup; refusing to stop it.')
        os.kill(pid,signal.SIGTERM);print(f'Stopped only private Xvfb server{pid}.')


if __name__=='__main__':main()
