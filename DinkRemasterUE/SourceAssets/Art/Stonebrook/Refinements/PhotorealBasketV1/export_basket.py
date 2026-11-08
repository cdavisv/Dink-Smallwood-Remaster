import sys,os
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O/'Pipeline'))
from dinkasset import export_ue,common
common.finish=lambda code:(sys.stdout.flush(),sys.stderr.flush(),os._exit(code))
sys.argv=['export_basket.py','--','--blend',str(O/'PhotorealBasketV1_Export.blend'),'--out',str(O/'Export'),'--formats','fbx,gltf','--source-root',str(O),'--report',str(O/'export_report.json')]
export_ue.main()
