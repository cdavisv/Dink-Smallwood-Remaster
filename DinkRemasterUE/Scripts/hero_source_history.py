"""Exact accepted Hero preimages; no latest-row or generic history exemption."""
from pathlib import Path
import hashlib
from lfs_inventory import pointer_metadata
AUTHORITY = [{'asset_path': 'SourceAssets/Art/Characters/Dink/Export/SK_Dink_LOD0.fbx',
  'old_sha256': '7f6d99353d0bfc4397cd2ebc0fe25257e84ca30c8eab2076c5348795d06dd97b',
  'new_sha256': '410774310cfe40431a4dbac48d455e2ad1764fe0287c5f54c175d1c22a8dcd8b',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/7f6d99353d0bfc4397cd2ebc0fe25257e84ca30c8eab2076c5348795d06dd97b/SK_Dink_LOD0.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/Export/SK_Dink_LOD1.fbx',
  'old_sha256': '18bc5e881c4315820b3a54a2365ec237aa8257a035d1c20cdb844e41e2ecd7a1',
  'new_sha256': 'cef5c07a515929c6a77b34972b80d899c92ec546627c2ddd4af823e3265aa935',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/18bc5e881c4315820b3a54a2365ec237aa8257a035d1c20cdb844e41e2ecd7a1/SK_Dink_LOD1.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/Export/SK_Dink_LOD2.fbx',
  'old_sha256': '946b803c0f7e2290ba0858fd10ab7cbb88515543278286a29a93178af9497ce5',
  'new_sha256': '9d24e6dcb338a51dc90d0ab662d970b7208f0e575fdc8b6106d1caf6ffd3879e',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/946b803c0f7e2290ba0858fd10ab7cbb88515543278286a29a93178af9497ce5/SK_Dink_LOD2.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/Export/SK_Dink_LOD3.fbx',
  'old_sha256': '4516f955b9c8bc6a17163edaa7227042edee3bc49877276aadb919d5ed59cd24',
  'new_sha256': '6544c0b5806bf00e6e61dc707772d6ba480eff8e64a2f3e1e19b088b443d167e',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/4516f955b9c8bc6a17163edaa7227042edee3bc49877276aadb919d5ed59cd24/SK_Dink_LOD3.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/HandBindingV2/Export/SK_Dink_Hands_LOD0.fbx',
  'old_sha256': 'a454d0ab8ab369854d7913505a09e3e0a9408b8d0cbe5ac2d173f97529e3ee73',
  'new_sha256': '97cc47a0b564ec0eb393585e94ad19a0ba75495ce3be7b8117177436581803d1',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/a454d0ab8ab369854d7913505a09e3e0a9408b8d0cbe5ac2d173f97529e3ee73/SK_Dink_Hands_LOD0.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/HandBindingV2/Export/SK_Dink_Hands_LOD1.fbx',
  'old_sha256': '2e92b77af4454d80eddc5c0d5a1b9c3aa506da4a9e67efec0328864847e9d243',
  'new_sha256': 'b6fe76766117aa35b8c56b5167982923b6aec058c64fdc8516eebf6fb55abda8',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/2e92b77af4454d80eddc5c0d5a1b9c3aa506da4a9e67efec0328864847e9d243/SK_Dink_Hands_LOD1.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/HandBindingV2/Export/SK_Dink_Hands_LOD2.fbx',
  'old_sha256': 'a0a19af2669c439bbb13e26ef95673c2296ba8c56bfa1bc07c30630222cac8e7',
  'new_sha256': '0d5e5f977e95cf9512a2da620f67f0896c6891eca7d274256b2950b43c65ce3c',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/a0a19af2669c439bbb13e26ef95673c2296ba8c56bfa1bc07c30630222cac8e7/SK_Dink_Hands_LOD2.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/HandBindingV2/Export/SK_Dink_Hands_LOD3.fbx',
  'old_sha256': '3ad2f09ccb920cfbf8f358043da9c15d1f7d594f7682fe00a9c16acfc0b0254d',
  'new_sha256': '16eeb4be737efe22077f71066f59ce021177930f0a6baa43a9d33f1f93d9c857',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/3ad2f09ccb920cfbf8f358043da9c15d1f7d594f7682fe00a9c16acfc0b0254d/SK_Dink_Hands_LOD3.fbx'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/HandBindingV2/SK_Dink_Hands.blend',
  'old_sha256': 'bd9cc7f98a087c2cfe1dbc82f196243381700d5bb1b87044a571c07577f7ea97',
  'new_sha256': '59de021c9e180531189df58bb84c7f60538cd80276c2a1c8298d2150de02efeb',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/bd9cc7f98a087c2cfe1dbc82f196243381700d5bb1b87044a571c07577f7ea97/SK_Dink_Hands.blend'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/HandBindingV2/scope_verification.json',
  'old_sha256': '4447746d05e8a70c6329d5ae8dc5d4a1dc3fc5cab3fd36e3ec444267d6125a75',
  'new_sha256': 'a78130f98b6f5d8b00fb4fba8d2293f915cdaa7f1e1e9d1a9a292f046f24535d',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/4447746d05e8a70c6329d5ae8dc5d4a1dc3fc5cab3fd36e3ec444267d6125a75/scope_verification.json'},
 {'asset_path': 'SourceAssets/Art/Characters/Dink/SK_Dink.blend',
  'old_sha256': 'da58584f5cb0e313be2c575d6a28fec7eede1100d1dca9e17d24e8bd57558006',
  'new_sha256': '935838d36428cc527af27bd833fe572ba4683fc2c53b304821502b94feb6b7d1',
  'archive_path': 'SourceAssets/Art/Characters/Dink/DefectFixes_9Nov2026/History/da58584f5cb0e313be2c575d6a28fec7eede1100d1dca9e17d24e8bd57558006/SK_Dink.blend'}]
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
