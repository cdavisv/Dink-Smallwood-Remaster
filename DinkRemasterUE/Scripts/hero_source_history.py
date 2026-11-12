"""Exact accepted Hero preimages; no latest-row or generic history exemption."""
from pathlib import Path
import hashlib
from lfs_inventory import pointer_metadata
AUTHORITY = [{'asset_path': 'SourceAssets/Art/Characters/Dink/Export/SK_Dink_LOD0.fbx',
  'old_sha256': '10e73c2bb671d08900b52f30492f96d0b957c77541746a75cad08dd6b25c3b20',
  'new_sha256': '5b231d99f4a8434cbc152e13434e7620c16763ed670c339ca588e9e14251e6a8',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/10e73c2bb671d08900b52f30492f96d0b957c77541746a75cad08dd6b25c3b20/SK_Dink_LOD0.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/Export/SK_Dink_LOD1.fbx',
  'old_sha256': 'fac29964cc138e5b051de483d3f1309de3b8276483ab87ae2e4f8a7c8628660c',
  'new_sha256': 'ea2e5479d8e3b99b88e234d935b5fdf08f6036538dbc54b472abd0e7725ccf08',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/fac29964cc138e5b051de483d3f1309de3b8276483ab87ae2e4f8a7c8628660c/SK_Dink_LOD1.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/Export/SK_Dink_LOD2.fbx',
  'old_sha256': '2647b087f16487917b59eb961501965707c0540a89f12b1af212c2c7a92cf09b',
  'new_sha256': 'fc26994f1baf40bb34a7568589827b4d77c4dfec98dab19646f9f3bb8609f041',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/2647b087f16487917b59eb961501965707c0540a89f12b1af212c2c7a92cf09b/SK_Dink_LOD2.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/Export/SK_Dink_LOD3.fbx',
  'old_sha256': '8917c196e3a6a53813a4e4352e8c5c1fee72f7f5de67c7b81323addabeadb5c3',
  'new_sha256': 'c21323ad7261089f4fac48065fe6092b15083eb46056596f61bb413fa9e02528',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/8917c196e3a6a53813a4e4352e8c5c1fee72f7f5de67c7b81323addabeadb5c3/SK_Dink_LOD3.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/HandBindingV2/Export/SK_Dink_Hands_LOD0.fbx',
  'old_sha256': '88fb842a4afdfd7017e0500caffc37726de41e28d31230bb7c4edd51ca8e2d12',
  'new_sha256': 'a6c62766d7bed23237bc1478a04d55fab856113c44ad5e877e6eace1aa679a8c',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/88fb842a4afdfd7017e0500caffc37726de41e28d31230bb7c4edd51ca8e2d12/SK_Dink_Hands_LOD0.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/HandBindingV2/Export/SK_Dink_Hands_LOD1.fbx',
  'old_sha256': 'f9e5f0ffd558333673306a0510fb99cf56e4a8abf61c661cce5783610390dd1e',
  'new_sha256': 'ea3391c25945b2855121d9804b23477978d5e68031a9d11012e9a47aaed75657',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/f9e5f0ffd558333673306a0510fb99cf56e4a8abf61c661cce5783610390dd1e/SK_Dink_Hands_LOD1.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/HandBindingV2/Export/SK_Dink_Hands_LOD2.fbx',
  'old_sha256': 'efc7522483c98b4d4000d59ff9c51eb9c154d9c13c7fbdaaa01be9b1cacef8c0',
  'new_sha256': 'c0fdf14f8dfa71fb7044a05ed1c52b043561acaec9cfce4c5683acdded3b4909',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/efc7522483c98b4d4000d59ff9c51eb9c154d9c13c7fbdaaa01be9b1cacef8c0/SK_Dink_Hands_LOD2.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/HandBindingV2/Export/SK_Dink_Hands_LOD3.fbx',
  'old_sha256': '0f8c4be7a7cfe11d02648e8657fbd39f6130f2c17d15b71a36c0db231bed8011',
  'new_sha256': 'ffc085693aaebd0444216822e899d68389d1e0c6d42c7b07f041322b1608ce60',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/0f8c4be7a7cfe11d02648e8657fbd39f6130f2c17d15b71a36c0db231bed8011/SK_Dink_Hands_LOD3.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/HandBindingV2/SK_Dink_Hands.blend',
  'old_sha256': 'b18ca6c4c1d281744cca8df03b033dcddf1cd96246b4bf7c971a5c7564f51dec',
  'new_sha256': 'cf6c101539491565e4569b899389edfe6f57bd4971194f50e68f9e6fa2a358ab',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/b18ca6c4c1d281744cca8df03b033dcddf1cd96246b4bf7c971a5c7564f51dec/SK_Dink_Hands.blend'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/HandBindingV2/scope_verification.json',
  'old_sha256': '0aa7f7419244de0f3e7be0ecdde039b9ef33df39f0072a0dc686b99668b8a335',
  'new_sha256': '11afd5c987c32a9d9074d4172231cb76832834130a59279763b6afaf5cfbb5f7',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/0aa7f7419244de0f3e7be0ecdde039b9ef33df39f0072a0dc686b99668b8a335/scope_verification.json'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/SK_Dink.blend',
  'old_sha256': 'f5b51a1d5420c03fb870d837639982eef5eafc3854f056faf69300255ff21fe1',
  'new_sha256': '9568c15a15d8335ea7e473a710f298071d91b8a03eb73724b1005c18bc8eb743',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/f5b51a1d5420c03fb870d837639982eef5eafc3854f056faf69300255ff21fe1/SK_Dink.blend'}]
ACCEPTED_COMMIT = '200ea3d60ec48c4a59dd7c5ac9d36219fd95b840'

SCOPE = 'Exact prior source preimages for accepted hero fixes. Original ledger rows unchanged; current files must match explicit accepted successor hashes. No runtime/geometry changes here.'

def validate_history(root, rows, manifest, metadata_only=False, inventory=None):
    """Return exact historical ledger indices eligible for archived verification.

    Full mode requires bytes. Metadata mode permits exact staged-inventory pointers.
    Call once before the ledger loop; keep all existing inventory/row checks.
    """
    if manifest != {"schema": "dink-accepted-hero-source-history/1", "accepted_commit": ACCEPTED_COMMIT, "entries": AUTHORITY, "scope": SCOPE}:
        raise ValueError("History manifest differs from exact accepted authority")
    root = Path(root).resolve()
    def verify(relative, expected_sha):
        p = root / relative
        # Refuse aliases even if they happen to resolve inside this checkout.
        if any(x.is_symlink() for x in [p, *p.parents] if x != root.parent):
            raise ValueError("History/current symlink")
        if not p.resolve().is_relative_to(root) or not p.is_file():
            raise ValueError("Missing or escaped history/current file")
        data = p.read_bytes()
        pointer = pointer_metadata(data)
        if pointer is not None:
            if (not metadata_only or inventory is None
                    or inventory.get(relative) != pointer
                    or pointer['sha256'] != expected_sha):
                raise ValueError("Pointer lacks exact approved path/hash/size inventory")
            return True  # Pointer metadata only; no binary proof.
        if hashlib.sha256(data).hexdigest() != expected_sha:
            raise ValueError("Archive or current bytes differ")
        return False
    authorized = set()
    binary_rows = metadata_rows = 0
    for entry in AUTHORITY:
        path, old, new = entry['asset_path'], entry['old_sha256'], entry['new_sha256']
        matches = [i for i,r in enumerate(rows) if r['asset_path']==path and r['sha256']==old]
        later = [i for i,r in enumerate(rows) if r['asset_path']==path and r['sha256']==new]
        if len(matches)!=1 or len(later)!=1 or later[0]<=matches[0]:
            raise ValueError("Exact old row and later accepted revision required")
        if any(i>later[0] and r['asset_path']==path for i,r in enumerate(rows)):
            raise ValueError("Unapproved later revision")
        archive_metadata = verify(entry['archive_path'], old)
        current_metadata = verify(path, new)
        if archive_metadata or current_metadata:
            metadata_rows += 1
        else:
            binary_rows += 1
        authorized.add(matches[0])
    return {'indices': authorized, 'historical_rows_binary_verified': binary_rows,
            'historical_rows_metadata_only': metadata_rows}
