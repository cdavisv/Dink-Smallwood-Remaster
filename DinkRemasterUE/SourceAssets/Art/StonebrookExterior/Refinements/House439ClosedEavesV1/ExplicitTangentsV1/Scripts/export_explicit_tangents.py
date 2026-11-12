from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from portable_recipe import run
if __name__=='__main__':run('export_validate.py')
