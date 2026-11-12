"""Portable path adapter for byte-preserved, actually executed QA recipes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

PACKED='233f6041c201fc2d8a6e92fd9dad63e292f8e88ba67a4bfd83e6e965b96f28c2'
OLD_FBX='aa4e091a48f3337f7b9bda4b1f044786c46149c163df511978bebb86bc210f27'
REFERENCE='20e969bcd0f4fae11f47d6d224e8063eb802e615263a8304ecd0c16c020d0c3d'
RECIPES={'export_validate.py':'2660cf4305c453350b5100c6b96e8120137e077f1f10dd11cdd2b36b8bceb365','readback_serialized_tbn.py':'9a4bda8e6d0d0ddd01814e775d773f2298e6765a83b8cab0ead7432e9ac1111f'}


def run(kind):
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',required=True,type=Path)
    parser.add_argument('--reference',required=True,type=Path,help='Frozen geometry NPZ20e969')
    parser.add_argument('--output',required=True,type=Path,help='Disposable export/check directory')
    a=parser.parse_args(argv);project=a.project_root.resolve();output=a.output.resolve();reference=a.reference.resolve()
    bundle=Path(__file__).resolve().parents[1]
    for protected in [project,bundle,reference.parent]:
        if output==protected or output.is_relative_to(protected):
            raise ValueError('Disposable output must be outside project, bundle and reference directories')
    packet=project/'SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1/Packet'
    packed=packet/'Source/House439_ClosedEaves.blend';oldfbx=packet/'FBX/SM_Cottage_Stonebrook_01.fbx'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for path,digest in [(packed,PACKED),(oldfbx,OLD_FBX),(reference,REFERENCE)]:
        if sha(path)!=digest:raise ValueError('Pinned source/reference changed: '+str(path))
    recipe=Path(__file__).resolve().parents[1]/'Evidence/RawScripts'/kind
    if sha(recipe)!=RECIPES[kind]:raise ValueError('Archived executed recipe changed')
    if kind=='export_validate.py':
        if output.exists() and any(output.iterdir()):raise ValueError('Disposable output must be empty')
        for name in ['FBX','Evidence']:(output/name).mkdir(parents=True,exist_ok=True)
        (output/'PRESERVED_INPUT_PINS.json').write_text(json.dumps({str(path):digest for path,digest in [(packed,PACKED),(oldfbx,OLD_FBX),(reference,REFERENCE)]},indent=2)+'\n')
        text=recipe.read_text()
        before="D=Path(__file__).resolve().parents[1]";assert text.count(before)==1
        text=text.replace(before,'D=Path('+repr(str(output))+')',1)
        before="P=Path('/home/davisc/Work/DinkHouse439ClosedEavesNative/DinkRemasterUE/SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1/Packet/Source/House439_ClosedEaves.blend')";assert text.count(before)==1
        text=text.replace(before,'P=Path('+repr(str(packed))+')',1)
    else:
        if (output/'Evidence/SERIALIZED_TBN_READBACK.json').exists():raise ValueError('Refuse to overwrite diagnostic evidence')
        text=recipe.read_text()
        replacements={"P=Path('/home/davisc/Work/DinkHouse439ClosedEavesNative/DinkRemasterUE')":'P=Path('+repr(str(project))+')',"Q=Path(__file__).resolve().parents[1]":'Q=Path('+repr(str(output))+')',"ref=Path('/home/davisc/Work/DinkQA/House439ClosedEavesNativeReference/FROZEN_FBX_GEOMETRY.npz')":'ref=Path('+repr(str(reference))+')'}
        for before,after in replacements.items():
            assert text.count(before)==1; text=text.replace(before,after,1)
    # Only path bindings are adapted in memory. Archived recipe bytes remain exact.
    exec(compile(text,str(recipe),'exec'),{'__name__':'__main__','__file__':str(recipe)})
    for path,digest in [(packed,PACKED),(oldfbx,OLD_FBX),(reference,REFERENCE)]:
        if sha(path)!=digest:raise ValueError('Source/reference changed during recipe')
