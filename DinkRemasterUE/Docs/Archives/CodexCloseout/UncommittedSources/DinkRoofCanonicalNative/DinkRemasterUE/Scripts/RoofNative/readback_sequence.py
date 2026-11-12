"""Persist every available raw LOD before strict matching. No launch/import/save path."""
import json,gzip
from pathlib import Path
from native_buffer_capture_v11d import capture_all,capture_failures
from native_asset_readback_v12 import verify_assets
import vista_geometry
TOLERANCES={'position_cm':.002,'UV0':.01/2048,'normal_component':.005}
def readback(U,root,proposal,recipe,binding,expected_hashes,approved_FP_nanite,guard,pixel_check,emit_receipt,write_raw,read_raw):
 subsystem=U.get_default_object(U.StaticMeshEditorSubsystem)
 summary=capture_all(U,binding['meshes'],subsystem,guard,write_raw)
 failures=capture_failures(summary)
 assert summary['all_expected_meshes_visited']and len(summary['meshes'])==10 and summary['actual_LOD_count']==12,'Incomplete raw capture; retain all available files'
 actual={row['package']:[read_raw(lod['raw_file'])for lod in row['LODs']]for row in summary['meshes']}
 source=json.loads(gzip.decompress(Path(binding['source_reference']).read_bytes()))
 return verify_assets(U,root,proposal,recipe,binding,source,expected_hashes,approved_FP_nanite,TOLERANCES,vista_geometry,guard,pixel_check,emit_receipt,actual,summary,failures)
