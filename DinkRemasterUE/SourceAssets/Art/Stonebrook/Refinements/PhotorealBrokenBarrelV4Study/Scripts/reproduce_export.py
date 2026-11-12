"""Blender CPU exporter wrapper; frozen script remains byte-exact archived evidence."""
import sys,hashlib
from pathlib import Path
Q=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:]
assert len(args)==2 and args[0]=='--output'
out=Path(args[1]).resolve();repo=Q.parents[5]
assert not out.exists() and out.is_absolute() and out!=repo and repo not in out.parents
source=Q/'portable.source.blend';script=Q/'Scripts/Historical/export_lod0.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='de68432d3a74d3dd0193b535d9821558d173882f506153822d2d77af66e954f4'
assert hashlib.sha256(script.read_bytes()).hexdigest()=='3e92a3fa585726d7cd9be49595d7c7dd95d4c309827cbdbe7f84ac48c8a7e114'
text=script.read_text();old="SRC=Path('/home/artist/Work/DinkQA/PhotorealBrokenBarrelAsymmetricV4Variant/PhotorealBrokenBarrelV4_AsymmetricComposition.blend')"
assert text.count(old)==1 and text.count('Q=Path(__file__).resolve().parent')==1
text=text.replace(old,'SRC=Path('+repr(str(source))+')').replace('Q=Path(__file__).resolve().parent','Q=Path('+repr(str(out))+')')
out.mkdir(parents=True,exist_ok=False)
exec(compile(text,str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
