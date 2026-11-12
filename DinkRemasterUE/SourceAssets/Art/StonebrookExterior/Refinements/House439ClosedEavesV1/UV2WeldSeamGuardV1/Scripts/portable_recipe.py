"""Portable path-only adapter for preserved executed UV2 recipes.

Export is opt-in; checks never start Blender. Export output must be disposable.
"""
import argparse,hashlib,json,sys
from pathlib import Path

RECIPES={'export_uv2_guard_prototype.py': 'a16d17a1b4d750256a2253c4e123c007b0e9f8737587a7afcc76232202ae26e7', 'readback_uv2_guard.py': 'f994c83a7de24b4b623dadef7de0f5cdb3af36cb66ab9f3d48badc0e9279f301'}
PACKED='f01cdbd2f679c9e4a11bf4424fe064ca5fa8229796702c67bdef883b2d7ca385'
PREDECESSOR='4d8c8f1eda4e37beed0dc1586bc3a72e1937660d990330d4473f8ec389c854e3'
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
          "P=Path('<HOME>/Work/DinkHouse439ClosedEavesNative/DinkRemasterUE/SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1/Packet/Source/House439_ClosedEaves.blend')":'P=Path('+repr(str(packed))+')',
          "reference_path=Path('<HOME>/Work/DinkQA/House439ExplicitTangentsNativeReference/FROZEN_FBX_GEOMETRY.npz')":'reference_path=Path('+repr(str(ref))+')'}
    else:
        if (output/'Evidence/SERIALIZED_UV2_GUARD_READBACK_V2.json').exists():raise ValueError('Refuse to overwrite readback evidence')
        if sha(output/'FBX/SM_Cottage_Stonebrook_01.fbx')!='e2560be3e346428bdebaa41fc29a58aeee6d37b8cd3620cfe43eacda7f1d892d':
            raise ValueError('Readback requires retained candidate FBX')
        replacements={"P=Path('<HOME>/Work/DinkHouse439ClosedEavesNative/DinkRemasterUE')":'P=Path('+repr(str(project))+')',
          "Q=Path(__file__).resolve().parents[1]":'Q=Path('+repr(str(output))+')',
          "old=Path('<HOME>/Work/DinkQA/House439ExplicitTangentsV1/FBX/SM_Cottage_Stonebrook_01.fbx')":'old=Path('+repr(str(old))+')',
          "ref=Path('<HOME>/Work/DinkQA/House439ExplicitTangentsNativeReference/FROZEN_FBX_GEOMETRY.npz')":'ref=Path('+repr(str(ref))+')'}
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
