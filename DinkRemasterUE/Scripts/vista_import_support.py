"""Source, material and recovery guards for the private VistaV3 import.
No Unreal import, asset writes, publication or storage-provider assumptions.
"""
import hashlib,json,math
from pathlib import Path

BUNDLE_SHA256='6c952a483ac6a0f0e1e23aa36ae688fefccea1c8db9e6bc9a54d6529c6b69e2f'
DEST='/Game/Dink/Kits/Stonebrook/InteriorVista'
DEST_ROOTS=(DEST,'/Game/Dink/Props/Stonebrook/InteriorVista')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate_bundle(source,expected_sha=BUNDLE_SHA256):
    source=Path(source).resolve();manifest=source/'bundle_manifest.json'
    if sha(manifest)!=expected_sha:raise ValueError('Unreviewed Vista source bundle')
    bundle=json.loads(manifest.read_text(encoding='utf-8'))
    if len(bundle['files'])!=139:raise ValueError('Vista source requires all139 pinned files')
    for rel,digest in bundle['files'].items():
        path=(source/rel).resolve()
        if not path.is_relative_to(source) or Path(rel).is_absolute() or '..' in Path(rel).parts:raise ValueError('Source path escapes bundle')
        if not path.is_file() or sha(path)!=digest:raise ValueError('Vista source SHA256 mismatch: '+rel)
    spec=json.loads((source/'Export/manifest.json').read_text(encoding='utf-8'))
    proposal=json.loads((source/'placement_proposal.json').read_text(encoding='utf-8'))
    assets=spec['assets'];names=[a['name'] for a in assets]
    if len(assets)!=55 or len(set(names))!=55 or sum(a['tris']['LOD0'] for a in assets)!=17604:raise ValueError('Unexpected Vista geometry inventory')
    for a in assets:
        if a['lod_count']!=1 or a['nanite'] is not True or a['content_path'] not in [prefix+'/'+a['name'] for prefix in DEST_ROOTS]:raise ValueError('Unexpected Vista source policy')
        fbx='Export/'+a['files']['fbx']
        if fbx not in bundle['files']:raise ValueError('Unpinned consumed FBX: '+fbx)
    if len(proposal['instances'])!=316 or len(proposal['new_meshes'])!=55:raise ValueError('Unexpected Vista placement inventory')
    return spec,proposal,expected_sha

def resolve_base_material(material,material_type):
    chain=[];seen=set()
    while material is not None:
        path=material.get_path_name();key=path.lower()
        if key in seen:raise ValueError('Material parent cycle: '+path)
        seen.add(key);chain.append(path)
        if isinstance(material,material_type):return material,chain
        try:material=material.get_editor_property('parent')
        except Exception as error:raise ValueError('Unsupported material parent: '+path) from error
    raise ValueError('Missing material parent: '+str(chain))

def validate_material_usage(material,material_type,has_usage,usage):
    base,chain=resolve_base_material(material,material_type)
    if not has_usage(base,usage):raise ValueError('Shared base material lacks required Nanite usage: '+chain[-1])
    return base,chain

def render_policy(settings,target,expected_triangles,actual_nanite_triangles):
    if not settings.get_editor_property('enabled') or settings.get_editor_property('fallback_target')!=target:raise ValueError('Vista requires source-approved Nanite/PercentTriangles')
    for key,expected in [('fallback_percent_triangles',1.),('fallback_relative_error',0.)]:
        value=float(settings.get_editor_property(key))
        if not math.isfinite(value) or abs(value-expected)>1e-6:raise ValueError('Vista Nanite policy mismatch: '+key)
    if actual_nanite_triangles!=expected_triangles:raise ValueError('Actual Nanite triangles differ from source')

def package_file(root,asset):
    return Path(root)/'Content'/(asset['content_path'].removeprefix('/Game/')+'.uasset')

def is_published(art_dir,dest=None):
    needles=[(prefix+'/').lower() for prefix in (DEST_ROOTS if dest is None else (dest,))]
    return any(any(needle in p.read_text(encoding='utf-8').lower() for needle in needles) for p in Path(art_dir).glob('*.json'))

def action(mode,destination_exists,published):
    if mode not in ['import','check','resume']:raise ValueError('Unknown Vista mode')
    if mode=='resume':
        if published:raise ValueError('Refusing to resume published Vista; preserve it and review a new revision')
        return 'resume' if destination_exists else 'create'
    if mode=='import':
        if destination_exists:raise ValueError('Vista destination exists: use check, or explicit resume if unpublished')
        return 'create'
    if not destination_exists:raise ValueError('Vista packages missing: import approved source first')
    return 'check'


def material_reference(proposed):
    # The original exterior importer uses its shared Stonebrook material folder.
    # Preserve the pinned proposal; record this known reference correction separately.
    return {'/Game/Dink/Materials/StonebrookExterior/MI_Stonebrook_Meadow.MI_Stonebrook_Meadow':
            '/Game/Dink/Materials/Stonebrook/MI_Stonebrook_Meadow.MI_Stonebrook_Meadow'}.get(proposed,proposed)

def asset_file(root,object_path):
    package=object_path.split('.',1)[0]
    if not package.startswith('/Game/Dink/') or '..' in package.split('/'):
        raise ValueError('Unexpected shared object path: '+object_path)
    return Path(root)/'Content'/(package.removeprefix('/Game/')+'.uasset')
