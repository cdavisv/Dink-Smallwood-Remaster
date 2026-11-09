"""Strict raw-relative + resolved filename checks, independently of source pixels/geometry."""
from pathlib import Path
import json

def need(ok,msg):
 if not ok:raise ValueError(msg)
def expected_files(files,packet):
 packet=Path(packet).resolve();out=[]
 for f in files:
  p=Path(f);need(p.is_absolute()and p.resolve()==p and p.is_relative_to(packet)and p.is_file(),'Metadata source escaped/missing')
  out.append(str(p))
 need(bool(out)and len(out)==len(set(out)),'Empty/duplicate source metadata');return out

def validate_snapshot(data,asset_path,files,is_mesh):
 need(data.get('schema')=='dink-roof-source-filenames/1'and data.get('valid')is True and data.get('asset')==asset_path,'Invalid raw filename snapshot')
 rows=data['files'];need(len(rows)==1,'Ambiguous AssetImportData source count')
 def check(row,expected):
  raw=row['stored'];need(type(raw)is str and raw and not Path(raw).is_absolute()and row['relative']is True,'Saved raw filename is not relative')
  need(Path(row['resolved']).is_absolute()and str(Path(row['resolved']).resolve())==expected,'Saved resolved source differs')
 check(rows[0],files[0]);lods=data['LODs'];need(len(lods)==(len(files)if is_mesh else 0),'Saved LOD filename coverage differs')
 for i,row in enumerate(lods):need(row['LOD']==i,'Saved LOD order differs');check(row,files[i])
 return data

def inspect_relative_sources(U,asset,files,packet):
 expected=expected_files(files,packet);bridge=getattr(getattr(U,'DinkRoofSourceMetadataLibrary',None),'inspect_roof_source_filenames',None);need(callable(bridge),'Raw filename inspector missing');data=json.loads(bridge(asset));return validate_snapshot(data,asset.get_path_name(),expected,isinstance(asset,U.StaticMesh))
def configure_relative_sources(U,asset,files,packet,guard):
 expected=expected_files(files,packet);setter=getattr(getattr(U,'DinkRoofSourceMetadataLibrary',None),'set_roof_source_filenames_relative',None);need(callable(setter),'Reviewed filename-only setter missing');guard();need(setter(asset,expected)is True,'Metadata-only setter rejected source contract');return inspect_relative_sources(U,asset,files,packet)
