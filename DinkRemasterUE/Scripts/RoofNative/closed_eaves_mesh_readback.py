"""Actual unsaved mesh callback; image/GPU/cooked physics acceptance separate."""
import hashlib
import json
from pathlib import Path
import numpy as np

from RoofNative.closed_eaves_uv_profile import reference_uvs
from RoofNative.closed_eaves_linear_color_restore import restore_imported_colors
from RoofNative.closed_eaves_built_geometry_compare import compare_built
from RoofNative.closed_eaves_convex_compare import inspect_convex,compare_convex

REFERENCE_SHA='20e969bcd0f4fae11f47d6d224e8063eb802e615263a8304ecd0c16c020d0c3d'


def make_mesh_readback(U,reference_file,metadata_file,frame,guard,texture_pixel_readback):
    if not callable(texture_pixel_readback):raise ValueError('Actual texture source pixel reader required')
    metadata=json.loads(Path(metadata_file).read_text())
    profile=metadata.get('transport_profile','legacy_2uv')
    expected_sha={'legacy_2uv':REFERENCE_SHA,'house439_uv2_weld_seam_guard_v1':'886f0bbc726191204d97d2459f8a1bab64533665b36c60a41c43256a94558994'}.get(profile)
    if expected_sha is None:raise ValueError('Unknown source transport profile')
    path=Path(reference_file)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected_sha:
        raise ValueError('Frozen source geometry reference differs')
    if metadata['geometry_npz_sha256']!=expected_sha:
        raise ValueError('Geometry reference metadata differs')
    with np.load(path,allow_pickle=False) as packed:reference={name:packed[name] for name in packed.files}
    reference_uvs(reference,profile) # Validate complete derived guard before any mutation.
    roles=metadata['material_roles']

    def inspect(mesh,materials,bindings,plan):
        if metadata['fbx_sha256']!=plan['mesh_sha256']:
            raise ValueError('Native plan does not use frozen reference FBX')
        if set(roles)!={'MI_Shared_'+role for role in plan['graphs']}:
            raise ValueError('Source reference material roles differ')
        # This performs exact geometry/UV/role/N/T/sign association before any
        # color mutation, then verifies raw preservation after native rebuild.
        repaired=restore_imported_colors(U,mesh,reference,roles,frame,guard,transport_profile=profile)
        geometry=repaired['after']
        for slot in geometry['slots']:
            role=slot['imported_name'].removeprefix('MI_Shared_')
            if slot['material_path'].split('.')[0]!=plan['materials'][role]:
                raise ValueError('Actual mesh material binding differs')
        built=compare_built(reference,roles,geometry,frame,transport_profile=profile)
        guard();actual_hulls=inspect_convex(U,mesh)
        hulls=compare_convex(reference,metadata,actual_hulls,frame)
        pixels=texture_pixel_readback(plan,bindings)
        if pixels['source_images_compared']!=len(plan['textures']):
            raise ValueError('Native source pixel coverage incomplete')
        return dict(source_reference_sha256=expected_sha,transport_profile=profile,raw=repaired['comparison'],
                    linear_colors_restored=repaired['changed'],built=built,convex=hulls,
                    actual_texture_source_pixels=pixels,
                    saved=False,activated=False,
                    texture_pixel_acceptance=False,gpu_gradient_acceptance=False,
                    cooked_physics_acceptance=False,
                    scope='Raw/built source geometry, packing and six convex inputs verified; not final art/runtime acceptance')
    return inspect
