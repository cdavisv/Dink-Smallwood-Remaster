"""Portable source/config preflight only; never imports Unreal or performs native actions."""
from pathlib import Path
import json,hashlib
ROOT_REL=Path('SourceAssets/Art/Stonebrook/Refinements/RoofChimneyV12d')
NAMESPACE='/Game/Dink/Refinements/RoofChimneyV12d'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(root,mode='import',expected_hashes=None):
 root=Path(root).resolve();tools=root/'Scripts/RoofNative';source=root/ROOT_REL
 pins=json.loads((source/'SHA256SUMS.json').read_text());assert len(pins)==100
 for name,h in pins.items():
  f=(source/name).resolve();assert f.is_relative_to(source)and sha(f)==h,'Frozen source100 differs'
 binding=json.loads((tools/'binding.json').read_text());binding['project']=str(root)
 for key in ['source_packet','source_reference','source_inventory']:
  rel=binding.pop('project_relative_'+key);p=(root/rel).resolve();assert p.is_relative_to(root);binding[key]=str(p)
 proposal=json.loads((tools/'native_asset_only_proposal_v12.json').read_text());recipe=json.loads((tools/'native_material_recipe_v12.json').read_text())
 assert mode in ['import','readback'];assert len(proposal['packages'])==50
 paths={'Content/'+a['package'].removeprefix('/Game/')+'.uasset'for a in proposal['packages']}
 if mode=='readback':assert expected_hashes and set(expected_hashes)==paths,'Exact50 import receipt hashes required'
 for a in proposal['packages']:
  assert a['package'].startswith(NAMESPACE+'/')and'.'not in a['package'];relative='Content/'+a['package'].removeprefix('/Game/')+'.uasset';f=root/relative
  if mode=='import':assert not f.exists(),'Existing canonical destination; no automatic resume'
  else:assert f.is_file()and not f.is_symlink()and sha(f)==expected_hashes[relative],'Missing/changed saved canonical package'
 return proposal,recipe,binding

def main():raise RuntimeError('REVIEW ONLY: no automatic native import or build')
if __name__=='__main__':main()
