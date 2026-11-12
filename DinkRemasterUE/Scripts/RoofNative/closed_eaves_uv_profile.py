"""Explicit optional seam-transport profile; never changes original UVs or tolerances."""
import numpy as np

LEGACY='legacy_2uv'
GUARDED='house439_uv2_weld_seam_guard_v1'


def canonical_guard(reference):
    uv=np.concatenate((reference['uv0'],reference['uv1']),axis=1).astype('<f4')
    if uv.ndim!=2 or uv.shape[1]!=4 or not np.isfinite(uv).all():
        raise ValueError('Finite original two-UV reference required')
    _,ids=np.unique(uv.view('<u4'),axis=0,return_inverse=True)
    return np.column_stack((ids%1024,ids//1024)).astype(np.float32),ids


def reference_uvs(reference,profile=LEGACY):
    if profile not in (LEGACY,GUARDED):raise ValueError('Unknown source transport profile')
    old=np.concatenate((reference['uv0'],reference['uv1']),axis=1)
    if profile==LEGACY:return old
    guard,_=canonical_guard(reference)
    actual=np.asarray(reference.get('uv2_weld_seam_guard'))
    if actual.dtype!=np.float32 or actual.shape!=guard.shape or not np.array_equal(actual,guard):
        raise ValueError('Source UV2 guard must exactly derive from original UV0/UV1 bits')
    return np.concatenate((old,actual),axis=1)


def validate_native_guard(uv,reference,profile,frame):
    if profile==LEGACY:return
    if profile!=GUARDED:raise ValueError('Unknown source transport profile')
    reference_uvs(reference,profile)
    guard,ids=canonical_guard(reference)
    actual=np.asarray(uv[:,4:6],float).copy()
    if frame.get('uv_v_flip') is not True:raise ValueError('Explicit guard V flip required')
    actual[:,1]=1-actual[:,1]
    if not np.isfinite(actual).all() or not np.array_equal(actual,np.rint(actual)):
        raise ValueError('Actual UV2 guard must contain exact integers')
    if np.any(actual[:,0]<0) or np.any(actual[:,0]>=1024) or np.any(actual[:,1]<0) or np.any(actual[:,1]>(len(np.unique(ids))-1)//1024):
        raise ValueError('Actual UV2 guard grid outside declared range')
    decoded=actual[:,0].astype(np.int64)+1024*actual[:,1].astype(np.int64)
    if np.any(decoded>=len(np.unique(ids))) or not np.array_equal(np.sort(decoded),np.sort(ids)):
        raise ValueError('Actual UV2 guard inventory differs from source tuple IDs')
