"""Convert verified original native reference facts to typed settings, no mutations."""
def typed_nanite(U,result):
    if result.get('status')!='PASS_REFERENCE_READBACK_ONLY' or result.get('imports')!=0 or result.get('saves')!=0:
        raise ValueError('Successful original read-only evidence required')
    expected={'enabled':True,'fallback_percent_triangles':1.0,'fallback_relative_error':0.0,'fallback_target':'<NaniteFallbackTarget.PERCENT_TRIANGLES: 1>'}
    if result.get('nanite_raw')!=expected or result.get('collision_raw')!='<CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX: 2>':
        raise ValueError('Original saved policy differs; new review required')
    member=U.NaniteFallbackTarget.PERCENT_TRIANGLES
    if member.value!=1 or str(member)!=expected['fallback_target']:
        raise ValueError('Actual native Nanite enum differs from observed original')
    return dict(enabled=True,fallback_percent_triangles=1.0,fallback_relative_error=0.0,fallback_target=member)
