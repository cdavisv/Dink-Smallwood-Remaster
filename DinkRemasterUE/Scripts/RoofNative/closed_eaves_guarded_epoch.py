"""Pinned optional source epoch. No editor operations or permissive fallbacks."""
import hashlib
import json
from pathlib import Path

FBX_SHA='e2560be3e346428bdebaa41fc29a58aeee6d37b8cd3620cfe43eacda7f1d892d'
NPZ_SHA='886f0bbc726191204d97d2459f8a1bab64533665b36c60a41c43256a94558994'
METADATA_SHA='2096c7f3ddfae5ee375ff3e21e9ba7154f53361b30887a253bae806c4d19d57a'
PROOF_SHA='44424ebaae5ce7159d452e9aed7e89971698f298d4205cc24f8691ea724126f5'
PROFILE='house439_uv2_weld_seam_guard_v1'


def load_guarded_epoch(project_root):
    folder=Path(project_root)/'SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1/UV2WeldSeamGuardV1'
    paths={'mesh':folder/'FBX/SM_Cottage_Stonebrook_01.fbx',
           'metadata':folder/'Reference/REFERENCE.json',
           'reference':folder/'Reference/SOURCE_GEOMETRY_WITH_UV2_GUARD.npz',
           'proof':folder/'Evidence/SERIALIZED_UV2_GUARD_READBACK_V2.json'}
    for key,expected in [('mesh',FBX_SHA),('metadata',METADATA_SHA),('reference',NPZ_SHA),('proof',PROOF_SHA)]:
        if hashlib.sha256(paths[key].read_bytes()).hexdigest()!=expected:
            raise ValueError('Guarded source epoch differs: '+key)
    metadata=json.loads(paths['metadata'].read_text());proof=json.loads(paths['proof'].read_text())
    if (metadata['fbx_sha256']!=FBX_SHA or metadata['geometry_npz_sha256']!=NPZ_SHA
            or metadata['transport_profile']!=PROFILE or metadata['expected_uv_channels']!=3
            or metadata['serialized_proof_sha256']!=PROOF_SHA
            or proof['prototype_fbx_sha256']!=FBX_SHA or proof['profile']!=PROFILE
            or proof['guard_grid_integer_exact'] is not True
            or proof['same_tuple_same_guard_and_distinct_tuple_distinct_guard'] is not True
            or proof['all_original_geometry_UV01_N_RGBA_material_smoothing_winding_and_six_UCX_arrays_exact'] is not True
            or proof['original_point05_normal_tangent_gate_unchanged'] is not True
            or proof['bitangent_sign_changes']!=0
            or any(proof['base_zero_vector_counts'].values())
            or proof['max_normal_vs_frozen_degrees']>=.05 or proof['max_tangent_vs_frozen_degrees']>=.05):
        raise ValueError('Guarded source proof or metadata association differs')
    return dict(paths,mesh_sha256=FBX_SHA,metadata_sha256=METADATA_SHA,
                proof_sha256=PROOF_SHA,transport_profile=PROFILE,expected_uv_channels=3)
