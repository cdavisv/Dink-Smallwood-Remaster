"""Blender CPU exporter wrapper; frozen script remains byte-exact archived evidence."""
import sys,hashlib
from pathlib import Path
Q=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:]
assert len(args)==2 and args[0]=='--output'
out=Path(args[1]).resolve();repo=Q.parents[5]
assert not out.exists() and out.is_absolute() and out!=repo and repo not in out.parents
source=Q/'portable.source.blend';script=Q/'Scripts/Historical/export_lod0.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='ee159f2d54a0431e6d8fa67541df5b3a370b85ccf4e42e3ea80bdacfe4c0faa5'
assert hashlib.sha256(script.read_bytes()).hexdigest()=='c8c0c835c005dedfe151b48f9fa8c7f0935091473727e7139338d1216658649e'
text=script.read_text();old="SRC=Path('<HOME>/Work/DinkQA/PhotorealBrokenBarrelAsymmetricV4Variant/PhotorealBrokenBarrelV4_AsymmetricComposition.blend')"
assert text.count(old)==1 and text.count('Q=Path(__file__).resolve().parent')==1
text=text.replace(old,'SRC=Path('+repr(str(source))+')').replace('Q=Path(__file__).resolve().parent','Q=Path('+repr(str(out))+')')
out.mkdir(parents=True,exist_ok=False)
exec(compile(text,str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
