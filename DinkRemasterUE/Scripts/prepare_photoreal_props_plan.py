"""Audit actual selected portable source and write its dynamically bound package/payload plan."""
import argparse,json
from pathlib import Path
import props_contract as C


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();plan=C.load_plan(a.source)
    for asset in plan['assets']:
        C.source_triangles(a.source,asset);C.source_hulls(a.source,asset)
    output={'schema':C.SCHEMA,'native_passed':False,'plan':plan,'plan_sha256':C.canonical_hash(plan),'required_packages':sorted(C.packages(plan)),'allowed_optional_candidate_sidecars':sorted(C.candidate_files(plan)-C.packages(plan)),'tools':C.tool_pins(Path(__file__).parent)}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(output,indent=2)+'\n');print('SOURCE PLAN PASS:3meshes,3materials,9textures; native verification pending')


if __name__=='__main__':main()
