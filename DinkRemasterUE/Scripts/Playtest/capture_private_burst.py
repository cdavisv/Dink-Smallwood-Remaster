#!/usr/bin/env python3
"""Read only private Xvfb frames before/around a real input; never sends keys."""
import argparse,ctypes as C,json,sys,time
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qa_private_x11 import PrivateX11
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--frames',type=int,default=28);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
b=PrivateX11();rows=[];start=time.monotonic()
for i in range(a.frames):
 t=time.monotonic();w=b.window();width,height=w['size'];raw=b.x.XGetImage(b.d,w['id'],0,0,width,height,C.c_ulong(-1).value,2)
 if not raw:raise SystemExit('Private readback failed')
 info=raw.contents;pixels=C.string_at(info.data,info.bytes_per_line*height);frame=Image.frombuffer('RGB',(width,height),pixels,'raw','BGRX',info.bytes_per_line,1);path=a.out/f'frame-{i:03}.png';frame.save(path,compress_level=1);b.x.XDestroyImage(raw)
 rows.append({'frame':i,'monotonic':t,'seconds':t-start,'path':str(path)})
 if i==0:(a.out/'ready.json').write_text(json.dumps({'monotonic':t,'backend':'private Xvfb:189 readback only'})+'\n')
 time.sleep(max(0,.06-(time.monotonic()-t)))
(a.out/'frames.json').write_text(json.dumps({'backend':'private Xvfb:189 readback only','frames':rows},indent=2)+'\n')
