"""Generate a pine-only source variant without modifying the reviewed field source files."""
from pathlib import Path
import copy,json
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'SourceAssets/Art/StonebrookFields'
BASE=json.loads((SOURCE/'art_manifest.json').read_text())
PINE=json.loads((SOURCE/'PineRefinementV3/art_manifest.json').read_text())
assert BASE['schema']=='dink-stonebrook-art/1' and PINE['schema']=='dink-art/1'
assert len(PINE['assets'])==1
old=[n for n,a in BASE['assets'].items() if a['class']=='foliage' and n.startswith('SM_Pine_')]
assert len(old)==1
old=old[0];new=next(iter(PINE['assets']))
variant=copy.deepcopy(BASE);variant['assets'].pop(old)
row=copy.deepcopy(PINE['assets'][new])
for field in ['fbx','source_blend']:
 if field in row:row[field]='PineRefinementV3/'+row[field]
row['lod_fbx']=['PineRefinementV3/'+p for p in row['lod_fbx']]
variant['assets'][new]=row
for name,material in PINE['materials'].items():
 material=copy.deepcopy(material)
 material['textures']={k:'PineRefinementV3/'+v for k,v in material['textures'].items()}
 variant['materials'][name]=material
OUT=SOURCE/'RuntimeVariants';OUT.mkdir(exist_ok=True)
(OUT/'pine_v3_art_manifest.json').write_text(json.dumps(variant,indent=2)+'\n')
changed={}
for screen in [471,438]:
 layout=json.loads((SOURCE/f'fields_{screen}_layout.json').read_text());count=0
 for field in ['replacements','elements']:
  for item in layout.get(field,[]):
   if item.get('mesh')==old:item['mesh']=new;count+=1
 (OUT/f'fields_{screen}_pine_v3_layout.json').write_text(json.dumps(layout,indent=2)+'\n');changed[str(screen)]=count
print('PINE VARIANT PREPARED:',old,'->',new,'; original layout/source untouched; changed mesh references',changed)
