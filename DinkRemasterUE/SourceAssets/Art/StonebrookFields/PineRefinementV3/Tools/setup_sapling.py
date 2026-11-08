"""Install onlypinned Sapling into isolated/tmp; never Blenderpreferences/config."""
from pathlib import Path
import hashlib,zipfile,urllib.request,json
URL='https://github.com/meet-brad-ch/add_curve_sapling/releases/download/v0.4.0/sapling_tree_gen-0.4.0.zip'
SHA='3022b572ab0000754cf9b77740b8161b86bb85380c959b321702fa9347cadb4e'
BASE=Path('/tmp/dink-qa-tools');DEST=BASE/'sapling';BASE.mkdir(exist_ok=True);archive=BASE/'sapling_tree_gen-0.4.0.zip'
if not archive.is_file():
 request=urllib.request.Request(URL,headers={'User-Agent':'DinkRemaster-art-source/1'});archive.write_bytes(urllib.request.urlopen(request,timeout=45).read())
if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA:raise RuntimeError('Sapling releasechecksum mismatch')
with zipfile.ZipFile(archive) as package:
 for name in package.namelist():
  p=Path(name)
  if p.is_absolute() or'..'in p.parts:raise RuntimeError('Unsafe extensionarchive path')
 package.extractall(DEST)
print('Sapling0.4.0 ready:',DEST,'verifiedSHA256',SHA,'no globalinstallation')
