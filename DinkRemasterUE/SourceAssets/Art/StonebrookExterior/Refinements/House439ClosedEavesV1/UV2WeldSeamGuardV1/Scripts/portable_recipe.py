"""Portable path-only adapter for preserved executed UV2 recipes.

Export is opt-in; checks never start Blender. Export output must be disposable.
"""
import argparse,hashlib,json,sys
from pathlib import Path

RECIPES={'export_uv2_guard_prototype.py': 'efa0ec3fe03c8266db826f3d79c307d6c538f3639685eadad621cfd4f6f76cc1', 'readback_uv2_guard.py': 'b9ffc5018eeb67bb7cc7c2b126f363ab1c53a3c049162b14e73fe529c1382783'}
PACKED='233f6041c201fc2d8a6e92fd9dad63e292f8e88ba67a4bfd83e6e965b96f28c2'
PREDECESSOR='22a2f8017cd8aaa3cc36c9102c4f778f4730e6ccc8bb7b3acdc5918491b37a3d'
REFERENCE='20e969bcd0f4fae11f47d6d224e8063eb802e615263a8304ecd0c16c020d0c3d'


def run(kind):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,required=True)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    args=parser.parse_args(argv)
    project=args.project_root.resolve();ref=args.reference.resolve();output=args.output.resolve()
    bundle=Path(__file__).resolve().parents[1]
    # Disallow both descendants and ancestors to protect inputs and evidence.
    for protected in [project,bundle,ref.parent]:
        if output==protected or output.is_relative_to(protected) or protected.is_relative_to(output):
            raise ValueError('Output must be separate from protected inputs')
    root=project/'SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1'
    packed=root/'Packet/Source/House439_ClosedEaves.blend'
    old=root/'ExplicitTangentsV1/FBX/SM_Cottage_Stonebrook_01.fbx'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    pins={str(packed):PACKED,str(old):PREDECESSOR,str(ref):REFERENCE}
    for path,digest in pins.items():
        if sha(Path(path))!=digest:raise ValueError('Pinned input changed: '+path)
    recipe=bundle/'Evidence/RawScripts'/kind
    if kind not in RECIPES or sha(recipe)!=RECIPES[kind]:raise ValueError('Archived recipe changed')
    text=recipe.read_text()
    replacements={}
    if kind=='export_uv2_guard_prototype.py':
        if output.exists() and any(output.iterdir()):raise ValueError('Export output must be empty')
        replacements={"D=Path(__file__).resolve().parents[1]":'D=Path('+repr(str(output))+')',
          "P=Path('/home/artist/Work/DinkHouse439ClosedEavesNative/DinkRemasterUE/SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1/Packet/Source/House439_ClosedEaves.blend')":'P=Path('+repr(str(packed))+')',
          "reference_path=Path('/home/artist/Work/DinkQA/House439ExplicitTangentsNativeReference/FROZEN_FBX_GEOMETRY.npz')":'reference_path=Path('+repr(str(ref))+')'}
    else:
        if (output/'Evidence/SERIALIZED_UV2_GUARD_READBACK_V2.json').exists():raise ValueError('Refuse to overwrite readback evidence')
        if sha(output/'FBX/SM_Cottage_Stonebrook_01.fbx')!='d3cdb0dc1ded99283873481c3ee310ec8486358a75cf66cc589d24e420da5a6c':
            raise ValueError('Readback requires retained candidate FBX')
        replacements={"P=Path('/home/artist/Work/DinkHouse439ClosedEavesNative/DinkRemasterUE')":'P=Path('+repr(str(project))+')',
          "Q=Path(__file__).resolve().parents[1]":'Q=Path('+repr(str(output))+')',
          "old=Path('/home/artist/Work/DinkQA/House439ExplicitTangentsV1/FBX/SM_Cottage_Stonebrook_01.fbx')":'old=Path('+repr(str(old))+')',
          "ref=Path('/home/artist/Work/DinkQA/House439ExplicitTangentsNativeReference/FROZEN_FBX_GEOMETRY.npz')":'ref=Path('+repr(str(ref))+')'}
    for before,after in replacements.items():
        if text.count(before)!=1:raise ValueError('Unexpected archived recipe path binding')
        text=text.replace(before,after,1)
    for name in ['FBX','Evidence']:(output/name).mkdir(parents=True,exist_ok=True)
    pinfile=output/'PRESERVED_INPUT_PINS.json'
    if pinfile.exists():
        if json.loads(pinfile.read_text())!=pins:raise ValueError('Output input pins differ')
    else:pinfile.write_text(json.dumps(pins,indent=2)+'\n')
    exec(compile(text,str(recipe),'exec'),{'__name__':'__main__','__file__':str(recipe)})
    for path,digest in pins.items():
        if sha(Path(path))!=digest:raise ValueError('Input changed during recipe')
