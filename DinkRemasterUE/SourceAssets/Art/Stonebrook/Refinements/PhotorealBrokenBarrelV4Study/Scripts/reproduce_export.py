"""Blender CPU exporter wrapper; frozen script remains byte-exact archived evidence."""
import sys,hashlib
from pathlib import Path
Q=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:]
assert len(args)==2 and args[0]=='--output'
out=Path(args[1]).resolve();repo=Q.parents[5]
assert not out.exists() and out.is_absolute() and out!=repo and repo not in out.parents
source=Q/'portable.source.blend';script=Q/'Scripts/Historical/export_lod0.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='d91d35d37225aeec36a5795197dcc5ec1b425b7bb2cfb7c6c2e1fe00650bee8c'
assert hashlib.sha256(script.read_bytes()).hexdigest()=='bebb4563b1bbd86ad240a186d25b26704270c936b698dd1d18e6208167112ba9'
text=script.read_text();old="SRC=Path('/home/davisc/Work/DinkQA/PhotorealBrokenBarrelAsymmetricV4Variant/PhotorealBrokenBarrelV4_AsymmetricComposition.blend')"
assert text.count(old)==1 and text.count('Q=Path(__file__).resolve().parent')==1
text=text.replace(old,'SRC=Path('+repr(str(source))+')').replace('Q=Path(__file__).resolve().parent','Q=Path('+repr(str(out))+')')
out.mkdir(parents=True,exist_ok=False)
exec(compile(text,str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
