import base64
import copy
from pathlib import Path
import sys
import unittest
import json
import tempfile
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from RoofNative.closed_eaves_texture_pixel_compare import compare_source_pixels,make_texture_pixel_readback


def fixture():
    payload=bytes([0,0,128,255,0,255,0,128,255,0,0,64,255,255,255,0])
    snapshot=dict(schema='dink-texture-source-pixels/1',valid=True,texture='/Trial/T.T',
                  width=2,height=2,format='BGRA8',texture_srgb=True,source_gamma='sRGB',row_origin='top_left',byte_order='little',
                  byte_count=len(payload),base64=base64.b64encode(payload).decode(),gpu_pixels_read=False)
    snapshot.update(source_encoding_override_none=True,source_color_space_none=True)
    expected=np.array([[[0,0,1,64/255],[1,1,1,0]],[[128/255,0,0,1],[0,1,0,128/255]]],dtype=np.float32)
    return snapshot,expected,dict(size=[2,2],colorspace='sRGB'),'/Trial/T','sRGB'


class TexturePixelTests(unittest.TestCase):
    def test_float_srgb_shader_cache_is_already_linear(self):
        data=np.array([[[.25,.4,.75,1]]],dtype='<f2')
        snapshot=dict(schema='dink-texture-source-pixels/1',valid=True,texture='/Trial/F.F',width=1,height=1,
            format='RGBA16F',texture_srgb=True,source_gamma='Linear',row_origin='top_left',byte_order='little',
            byte_count=data.nbytes,base64=base64.b64encode(data.tobytes()).decode(),gpu_pixels_read=False,
            source_encoding_override_none=True,source_color_space_none=True)
        report=compare_source_pixels(snapshot,data.astype(np.float32),dict(size=[1,1],colorspace='sRGB'),'/Trial/F','Linear')
        self.assertEqual(report['max_RGBA_error'],[0,0,0,0])
        wrong=compare_source_pixels(snapshot,data.astype(np.float32),dict(size=[1,1],colorspace='sRGB'),'/Trial/F','sRGB')
        self.assertGreater(max(wrong['max_RGBA_error']),.2)

    def test_universal_reference_metadata_refused_before_native_access(self):
        for basis in (None,'png_encoded_rgba'):
            with tempfile.TemporaryDirectory() as temp:
                record=dict(material_source_sha256='95ac660d0d21c932d6187a9a569902e6c79862cb3f006500abe6aaaa2bb30577',reference_basis=basis)
                (Path(temp)/'REFERENCE.json').write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError,'Per-image Cycles-calibrated'):
                    make_texture_pixel_readback(object(),temp,lambda:None)

    def test_float_source_gamma_is_linear_even_with_texture_srgb_flag(self):
        native=np.array([[[.25,.4,.75,1]]],dtype='<f2');linear=native.astype(np.float32)
        expected=linear.copy();expected[:,:,:3]=1.055*expected[:,:,:3]**(1/2.4)-.055
        snapshot=dict(schema='dink-texture-source-pixels/1',valid=True,texture='/Trial/BC.BC',width=1,height=1,
            format='RGBA16F',texture_srgb=True,source_gamma='Linear',row_origin='top_left',byte_order='little',
            byte_count=native.nbytes,base64=base64.b64encode(native.tobytes()).decode(),gpu_pixels_read=False)
        snapshot.update(source_encoding_override_none=True,source_color_space_none=True)
        report=compare_source_pixels(snapshot,expected,dict(size=[1,1],colorspace='sRGB'),'/Trial/BC','sRGB')
        self.assertLess(max(report['max_RGBA_error']),3e-7)
        self.assertEqual(report['native_source_gamma'],'Linear')

    def test_pow22_is_explicitly_decoded_and_difference_from_srgb_measured(self):
        snapshot,expected,image,target,encoding=fixture();snapshot['source_gamma']='Pow22'
        report=compare_source_pixels(snapshot,expected,image,target,encoding)
        self.assertEqual(report['native_source_gamma'],'Pow22')
        self.assertAlmostEqual(report['max_RGBA_error'][0],abs((128/255)**2.2-.21586050011389926),places=7)
        self.assertFalse(report['pixel_equivalence_accepted'])

    def test_native_bgra_orientation_srgb_and_linear_alpha_measurement(self):
        report=compare_source_pixels(*fixture())
        self.assertLess(max(report['max_RGBA_error']),2e-7)
        self.assertFalse(report['pixel_equivalence_accepted']);self.assertFalse(report['gpu_pixels_read'])

    def test_float_source_preserves_xyz_and_does_not_apply_srgb_decode(self):
        actual=np.array([[[.25,.4,.75,1]]],dtype='<f2')
        snapshot=dict(schema='dink-texture-source-pixels/1',valid=True,texture='/Trial/N.N',
            width=1,height=1,format='RGBA16F',texture_srgb=False,source_gamma='Linear',row_origin='top_left',byte_order='little',
            byte_count=actual.nbytes,base64=base64.b64encode(actual.tobytes()).decode(),gpu_pixels_read=False)
        snapshot.update(source_encoding_override_none=True,source_color_space_none=True)
        report=compare_source_pixels(snapshot,actual.astype(np.float32),dict(size=[1,1],colorspace='Non-Color'),'/Trial/N','Linear')
        self.assertEqual(report['max_RGBA_error'],[0,0,0,0])

    def test_provenance_payload_format_and_orientation_corruptions_refused(self):
        for field,value in [('texture','/Wrong/T.T'),('row_origin','bottom_left'),('byte_count',1),
                            ('width',3),('texture_srgb',False),('source_gamma','unknown'),('format','BC5'),('gpu_pixels_read',True),
                            ('source_encoding_override_none',False),('source_color_space_none',False)]:
            snapshot,expected,image,target,encoding=fixture();snapshot[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):compare_source_pixels(snapshot,expected,image,target,encoding)

    def test_pixel_corruption_is_measured_and_never_silently_accepted(self):
        snapshot,expected,image,target,encoding=fixture();data=bytearray(base64.b64decode(snapshot['base64']));data[2]=255
        snapshot['base64']=base64.b64encode(data).decode()
        report=compare_source_pixels(snapshot,expected,image,target,encoding)
        self.assertGreater(report['max_RGBA_error'][0],.7);self.assertFalse(report['pixel_equivalence_accepted'])


if __name__=='__main__':unittest.main()
