"""Bounded caller template; Root supplies its existing reviewed clearance/mount/module guard.
No environment auto-discovery, launcher, new approval protocol or module-load Unreal calls.
Native wrappers/CDO closures live only in _native_scope, following reviewed VistaV7 cleanup.
"""
from pathlib import Path
import gc
import json
import traceback

PHASES = ('trial_import', 'trial_readback', 'production_bindings', 'production_readback')


def _native_scope(root, phase, contract, guard, record_saved, emit_receipt,
                  diagnostic_root=None, tolerances=None, imported=None,
                  trial_readback=None, activation=None):
    import unreal as U
    from shared_roof_contract import require, package_file, sha
    from shared_roof_native import (import_trial, verify_trial_readback,
                                    apply_production_bindings, verify_production_readback)
    from shared_roof_verify import make_mesh_verifier, make_pixel_verifier
    root = Path(root)
    require(phase in PHASES and all(callable(f) for f in (guard, record_saved, emit_receipt)),
            'Exact phase and Root guard/save-registration/receipt callbacks required')
    # Reject Unreal objects in receipts/state before a native wrapper can escape this scope.
    json.dumps(contract)
    for receipt in (imported, trial_readback, activation):
        if receipt is not None:
            json.dumps(receipt)
    guard()
    require(str(Path(U.Paths.convert_relative_path_to_full(U.Paths.project_dir())).resolve()) == str(root),
            'Wrong actual project for this Root clearance')
    require('-game' not in U.SystemLibrary.get_command_line().lower().split(), 'Editor commandlet only')
    writable = set(contract['trial_packages']) if phase == 'trial_import' else {
        r['existing_package'] for r in contract['production'].values()} if phase == 'production_bindings' else set()

    def save(asset, overwrite=False):
        package = asset.get_path_name().split('.')[0]
        file = package_file(root, package)
        require(package in writable and overwrite is (phase == 'production_bindings'),
                'Save outside exact phase whitelist or wrong replacement mode')
        require(file.resolve().is_relative_to(root) and not file.is_symlink() and file.exists() is overwrite,
                'Unexpected/aliased phase save destination')
        if overwrite:
            name = package.rsplit('/', 1)[-1]
            require(file.stat().st_nlink == 1 and sha(file) ==
                    contract['production'][name]['expected_existing_package_sha256'],
                    'Production save preimage changed')
        guard()
        require(U.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False) is True,
                'Root-whitelisted native save failed')
        require(file.is_file() and not file.is_symlink() and file.stat().st_nlink == 1,
                'Saved native package missing/aliased')
        # Bind this to Root's existing checked mutable-output guard.saved/package tracker.
        # Production uses Root's explicitly reviewed overwrite/preimage tracking variant.
        record_saved(phase, package, sha(file))
        guard()
        return True

    if phase == 'production_bindings':
        require(trial_readback is not None, 'Saved23 trial acceptance required')
        return apply_production_bindings(U, root, contract, trial_readback, guard, save, emit_receipt)
    require(diagnostic_root is not None, 'Approved fresh empty pixel diagnostic directory required')
    pixels = make_pixel_verifier(U, Path(diagnostic_root), guard)
    if phase == 'production_readback':
        require(activation is not None and trial_readback is not None, 'Actual activation/trial receipts required')
        return verify_production_readback(U, root, contract, activation, trial_readback, guard, pixels, emit_receipt)
    require(tolerances is not None, 'Root-approved geometry/UV/normal tolerances required')
    mesh_verifier = make_mesh_verifier(U, root, contract, tolerances)
    if phase == 'trial_import':
        return import_trial(U, root, contract, guard, save, pixels, mesh_verifier, emit_receipt)
    require(imported is not None, 'Actual23 import receipt required')
    return verify_trial_readback(U, root, contract, imported, guard, pixels, mesh_verifier, emit_receipt)


def run_phase(*args, **kwargs):
    """Let the native scope unwind, clear failure-frame aliases, then collect before UE teardown.
    Pattern reused from reviewed SharedVistaImportDevelopmentV7/import_shared_vista.py.
    Root callbacks/state must themselves be plain JSON/file/module-guard objects, not UObject holders.
    """
    result = None
    try:
        result = _native_scope(*args, **kwargs)
        json.dumps(result)
        return result
    except BaseException as error:
        pending, seen = [error], set()
        while pending:
            item = pending.pop()
            if id(item) in seen:
                continue
            seen.add(id(item))
            traceback.clear_frames(item.__traceback__)
            pending.extend(e for e in (item.__cause__, item.__context__) if e is not None)
        raise
    finally:
        result = None  # A malformed non-JSON native result must not survive failure cleanup.
        gc.collect()


if __name__ == '__main__':
    raise RuntimeError('Root must bind its reviewed current guards/clearance/save tracker; no automatic native launch')
