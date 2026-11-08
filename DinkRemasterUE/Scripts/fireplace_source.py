"""Portable raw-source/provenance and recovery guards shared by fireplace commands.
Inputs may be materialized from any verified storage; Unreal requires actual local bytes.
"""
import csv,hashlib,json,math
from pathlib import Path

def validate_source_inputs(root):
    root=Path(root).resolve();source=root/'SourceAssets/Art/Stonebrook/Refinements/FireplaceV2'
    rows={}
    with (root/'SourceAssets/asset_ledger.csv').open(newline='',encoding='utf-8-sig') as stream:
        for row in csv.DictReader(stream):rows.setdefault(row['asset_path'],[]).append(row['sha256'])
    def checked(path):
        path=Path(path).resolve()
        if not path.is_relative_to(root):raise ValueError(f'Source path escapes project: {path}')
        rel=path.relative_to(root).as_posix();expected=rows.get(rel,[])
        if len(expected)!=1:raise ValueError(f'Expected one trusted source-ledger record: {rel}')
        if not path.is_file():raise ValueError(f'Missing source bytes: {rel}; materialize the approved raw bytes (for example git lfs pull)')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected[0]:raise ValueError(f'Source SHA256 mismatch: {rel}; materialize the approved raw bytes')
        return path
    plan=json.loads(checked(source/'placement_plan.json').read_text())
    if plan['schema']!='dink-fireplace-refinement/1':raise ValueError('Unknown fireplace source plan')
    blend=checked(root/plan['source_blend'])
    if hashlib.sha256(blend.read_bytes()).hexdigest()!=plan['source_blend_sha256']:raise ValueError('Source blend differs from reviewed plan')
    export=json.loads((root/plan['source_export']).read_text())['assets'][0]
    if export['source']['sha256']!=plan['source_blend_sha256'] or export['name']!=plan['mesh']:raise ValueError('Export metadata differs from reviewed source plan')
    spec=json.loads((source/'candidate_manifest.json').read_text())
    if spec['name']!=plan['mesh'] or spec['textures']!={k:f'Textures/T_FireplaceV2_Atlas_{k}.png' for k in ['BC','N','ORM','E']}:raise ValueError('Candidate inputs differ from source plan')
    paths=[checked(source/path) for path in spec['textures'].values()]
    paths += [checked(source/'Export/SingleLODs'/f'{plan["mesh"]}_LOD{i}.fbx') for i in range(3)]
    return plan,spec,{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [blend,*paths]}

def validate_render_policy(percent,relative_error,policy):
    for label,actual in [('fallback_percent_triangles',percent),('fallback_relative_error',relative_error)]:
        value=float(actual);expected=float(policy[label])
        if not math.isfinite(value) or abs(value-expected)>1e-6:raise ValueError(f'{label} differs from reviewed plan: {value} != {expected}')

def import_action(mode,destination_exists,runtime_published):
    if mode not in ['import','check','publish','resume']:raise ValueError('Unknown fireplace mode')
    if mode=='resume':
        if runtime_published:raise ValueError('Refusing to overwrite a published candidate; preserve it and review a new revision')
        return 'resume' if destination_exists else 'create'
    if destination_exists:return 'check'
    if mode!='import':raise ValueError('Import the candidate packages before checking or publishing')
    return 'create'
