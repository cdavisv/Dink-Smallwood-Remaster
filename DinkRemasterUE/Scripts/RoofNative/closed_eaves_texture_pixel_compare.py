"""Actual native SOURCE-mip comparisons. Never substitutes for GPU pixels."""
import base64
import hashlib
import json
from pathlib import Path
import numpy as np
from RoofNative.closed_eaves_house_texture_encoding import validate_plan,read_encoding,verify_storage,expected_override


def compare_source_pixels(snapshot,expected,image,target,reference_encoding,encoding_override=0):
    if encoding_override not in(0,2)or(encoding_override==2 and expected_override(image.get('sha256'),image)!=2):
        raise ValueError('Exact house encoding profile required')
    if reference_encoding not in ('Linear','sRGB'):
        raise ValueError('Explicit calibrated reference encoding required')
    if (snapshot.get('schema')!='dink-texture-source-pixels/1' or snapshot.get('valid') is not True
            or snapshot.get('texture','').split('.')[0]!=target
            or snapshot.get('gpu_pixels_read') is not False
            or snapshot.get('row_origin')!='top_left' or snapshot.get('byte_order')!='little'
            or snapshot.get('texture_srgb')!=(image['colorspace']=='sRGB')
            or snapshot.get('source_encoding_override_none') is not(encoding_override==0)
            or snapshot.get('source_color_space_none') is not True
            or snapshot.get('source_gamma') not in ('Linear','sRGB','Pow22')):
        raise ValueError('Actual native source pixel provenance/decode differs')
    width,height=image['size']
    if [snapshot['width'],snapshot['height']]!=[width,height] or expected.shape!=(height,width,4):
        raise ValueError('Native/reference pixel dimensions differ')
    formats={'BGRA8':('<u1',255),'RGBA16':('<u2',65535),
             'RGBA16F':('<f2',None),'RGBA32F':('<f4',None)}
    if snapshot['format'] not in formats:raise ValueError('Unsupported native source pixel format')
    dtype,scale=formats[snapshot['format']]
    data=base64.b64decode(snapshot['base64'],validate=True)
    if len(data)!=snapshot['byte_count'] or len(data)!=width*height*4*np.dtype(dtype).itemsize:
        raise ValueError('Native pixel payload size differs')
    pixels=np.frombuffer(data,dtype=dtype).reshape(height,width,4).astype(np.float32)
    if scale is not None:pixels/=scale
    if snapshot['format']=='BGRA8':pixels=pixels[:,:,[2,1,0,3]]
    pixels=np.flipud(pixels).copy() # Fixed top-left native -> bottom-left Blender.
    if snapshot['source_gamma']=='sRGB':
        c=pixels[:,:,:3];pixels[:,:,:3]=np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
    elif snapshot['source_gamma']=='Pow22':pixels[:,:,:3]=pixels[:,:,:3]**2.2
    # Encoding is calibrated per actual source buffer class by Cycles emission.
    expected=expected.astype(np.float32).copy()
    if reference_encoding=='sRGB':
        c=expected[:,:,:3];expected[:,:,:3]=np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
    if not np.isfinite(pixels).all() or not np.isfinite(expected).all():
        raise ValueError('Nonfinite native/reference pixels')
    delta=np.abs(pixels.astype(np.float64)-expected)
    return dict(actual_source_pixels_compared=True,width=width,height=height,
                native_source_format=snapshot['format'],native_source_gamma=snapshot['source_gamma'],
                reference_encoding=reference_encoding,
                max_RGBA_error=delta.max(axis=(0,1)).tolist(),
                rms_RGBA_error=np.sqrt((delta*delta).mean(axis=(0,1))).tolist(),
                gpu_pixels_read=False,pixel_equivalence_accepted=False,
                encoding_override_value=encoding_override,encoding_override_applied_to_source_values=False,scope='Intrinsic-source-gamma reference diagnostic only; explicit build override does not rewrite source storage; GPU/appearance separate')


def make_texture_pixel_readback(U,reference_folder,guard):
    folder=Path(reference_folder)
    record=json.loads((folder/'REFERENCE.json').read_text())
    if record['material_source_sha256']!='95ac660d0d21c932d6187a9a569902e6c79862cb3f006500abe6aaaa2bb30577':
        raise ValueError('Frozen material-source pixel reference differs')
    if record.get('reference_basis')!='cycles_calibrated_per_image_rgba':
        raise ValueError('Per-image Cycles-calibrated reference required')
    calibration=folder/'CALIBRATION.json'
    if hashlib.sha256(calibration.read_bytes()).hexdigest()!=record['calibration_sha256']:
        raise ValueError('Source shader calibration proof differs')
    def inspect(plan,bindings):
        if set(record['images'])!=set(plan['textures']) or set(bindings)!=set(plan['textures']):
            raise ValueError('Incomplete connected texture pixel inventory')
        policy=validate_plan(plan)
        results={}
        for sha,row in plan['textures'].items():
            ref=record['images'][sha];path=folder/(sha+'.npz')
            if ref['file']!=path.name or hashlib.sha256(path.read_bytes()).hexdigest()!=ref['sha256']:
                raise ValueError('Source pixel reference payload differs')
            if ref['colorspace']!=row['image']['colorspace'] or ref['origin']!='Blender image.pixels row0 bottom':
                raise ValueError('Source pixel decode/orientation differs')
            encoding='Linear' if ref['image_is_float'] or ref['colorspace']=='Non-Color' else 'sRGB'
            if (ref['reference_encoding']!=encoding or
                    [ref['png_bit_depth'],ref['image_is_float'],ref['colorspace']] not in record['calibrated_classes']):
                raise ValueError('Uncalibrated source pixel buffer class')
            with np.load(path,allow_pickle=False) as packed:expected=packed['rgba']
            guard()
            texture=bindings[sha]['texture']
            reflected=read_encoding(U,texture,sha,row['image'],guard)
            guard();actual=json.loads(U.DinkMaterialArtLibrary.inspect_texture_source_pixels(texture))
            storage=verify_storage(actual,sha,row['image'],row['target'],policy[sha])
            results[sha]=compare_source_pixels(actual,expected,row['image'],row['target'],encoding,encoding_override=policy[sha])
            results[sha].update(raw_source_storage=storage,source_encoding_readback=reflected)
        return dict(source_images_compared=len(results),images=results,gpu_pixel_acceptance=False)
    return inspect
