import sys,os
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O/'Pipeline'))
from dinkasset import make_lods,common
common.finish=lambda code:(sys.stdout.flush(),sys.stderr.flush(),os._exit(code))
sys.argv=['make_lods.py','--','--blend',str(O/'PhotorealCandleV1_Source.blend'),'--collection','SM_Candle_Iron_01','--lods','--output',str(O/'PhotorealCandleV1_LODs.blend'),'--report',str(O/'lod_generation.json')]
make_lods.main()
