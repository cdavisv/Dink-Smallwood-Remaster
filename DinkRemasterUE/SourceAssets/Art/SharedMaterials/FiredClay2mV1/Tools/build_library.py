"""Extract/replay the two generic packed fired-clay materials without changing graphs.
Default reads the registered library. --source can initially extract from a packed
reviewed scene; no author-workspace paths or external image dependencies required.
Run through Blender: blender -b --python Tools/build_library.py -- --out output.blend
"""
import bpy,argparse,sys,json,hashlib,os
from pathlib import Path
D=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=D/'SharedFiredClayLibrary_Source.blend');p.add_argument('--out',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[])
if a.source.resolve()==a.out.resolve():raise SystemExit('Use a distinct output; registered source stays read-only')
bpy.ops.wm.read_factory_settings(use_empty=True)
names=['MI_Shared_FiredClay2m','MI_Shared_FiredClayMasonry2m']
with bpy.data.libraries.load(str(a.source),link=False)as(src,dst):
 assert set(names)<=set(src.materials);dst.materials=list(names)
for m in dst.materials:
 for node in m.node_tree.nodes:
  if node.type=='TEX_IMAGE':assert node.image and node.image.packed_file
bpy.data.libraries.write(str(a.out),set(dst.materials),fake_user=True,compress=True)
print(json.dumps(dict(output=str(a.out),materials=names,sha256=hashlib.sha256(a.out.read_bytes()).hexdigest())))

sys.stdout.flush();os._exit(0)
