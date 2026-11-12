"""Lossless sample/depth contracts; synthetic PNG ground truth, no UE/Pillow."""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import hashlib,struct,sys,tempfile,unittest,zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'RoofNative'))
from png_source_v11 import png_rgb,png_rgb_profile,png_format
from fireplace_mesh_readback import make_pixel_verifier

def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
def prediction(kind,left,up,upper):
    if kind==0:return 0
    if kind==1:return left
    if kind==2:return up
    if kind==3:return(left+up)//2
    p=left+up-upper;return min((left,up,upper),key=lambda v:abs(p-v))
def png(bits=16,channels=3,filter_kind=0,alpha=None,low_delta=0,header_color=None,interlace=0):
    values=[0,1,255,256,32768,65534,65535,0x1200,0x12ff,0x0100,0x00ff,0x8001,0x101,0xff00,2,3,0xabc,0xfefe]
    if bits==8:values=[v%256 for v in values]
    values=values.copy();values[7]+=low_delta
    rgb=b''.join(v.to_bytes(bits//8,'big')for v in values);rows=[];bpp=channels*(bits//8)
    for y in range(3):
        row=bytearray()
        for x in range(2):
            start=(y*2+x)*3;row.extend(b''.join(v.to_bytes(bits//8,'big')for v in values[start:start+3]))
            if channels==4:row.extend(((1<<bits)-1 if alpha is None else alpha).to_bytes(bits//8,'big'))
        rows.append(row)
    encoded=bytearray();previous=bytearray(len(rows[0]))
    for row in rows:
        encoded.append(filter_kind)
        for i,value in enumerate(row):
            pred=prediction(filter_kind,row[i-bpp]if i>=bpp else 0,previous[i],previous[i-bpp]if i>=bpp else 0)
            encoded.append((value-pred)&255)
        previous=row
    color=header_color if header_color is not None else 2 if channels==3 else 6
    raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,3,bits,color,0,0,interlace))+chunk(b'IDAT',zlib.compress(encoded))+chunk(b'IEND',b'')
    return raw,rgb

class PNGProfileTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def put(self,data,name='input.png'):p=self.root/name;p.write_bytes(data);return p
    def test_all_filters_all_four_formats_exact_bytes(self):
        for bits in(8,16):
            for channels in(3,4):
                for kind in range(5):
                    with self.subTest(bits=bits,channels=channels,filter=kind):
                        data,rgb=png(bits,channels,kind);p=self.put(data)
                        self.assertEqual(png_rgb_profile(p,bits),(2,3,bytearray(rgb)))
                        if bits==8:self.assertEqual(png_rgb(p),(2,3,bytearray(rgb)))
    def test_legacy8_refuses16(self):
        with self.assertRaisesRegex(RuntimeError,'Expected RGB8'):png_rgb(self.put(png()[0]))
    def test_explicit_depth_mismatch_both_directions(self):
        for bits,expected in[(8,16),(16,8)]:
            with self.assertRaises(RuntimeError):png_rgb_profile(self.put(png(bits)[0]),expected)
    def test_low_bytes_and_big_endian_preserved(self):
        a,rgb=png();b,_=png(low_delta=1);first=png_rgb_profile(self.put(a,'a.png'),16)[2];second=png_rgb_profile(self.put(b,'b.png'),16)[2]
        self.assertEqual(first,rgb);self.assertNotEqual(first,second)
        self.assertIn(b'\x12\x00\x12\xff',first)
    def test_16bit_alpha_requires_full65535(self):
        for value in[0,255,65280,65534]:
            with self.assertRaisesRegex(RuntimeError,'alpha'):png_rgb_profile(self.put(png(channels=4,alpha=value)[0]),16)
    def test_8bit_alpha_requires255(self):
        with self.assertRaisesRegex(RuntimeError,'alpha'):png_rgb(self.put(png(8,4,alpha=254)[0]))
    def test_bad_crc_refused(self):
        data=bytearray(png()[0]);data[-1]^=1
        with self.assertRaisesRegex(RuntimeError,'CRC'):png_rgb_profile(self.put(data),16)
    def test_truncated_chunk_and_missing_end_refused(self):
        data=png()[0]
        for broken in[data[:-2],data[:-12]]:
            with self.assertRaises(RuntimeError):png_rgb_profile(self.put(broken),16)
    def test_unsupported_format_interlace_and_filter_refused(self):
        for data in[png(header_color=0)[0],png(interlace=1)[0]]:
            with self.assertRaises(RuntimeError):png_rgb_profile(self.put(data),16)
        data=png()[0];ihdr=data[:33];payload=zlib.decompress(data[41:-16]);payload=bytes([5])+payload[1:]
        with self.assertRaisesRegex(RuntimeError,'filter'):png_rgb_profile(self.put(ihdr+chunk(b'IDAT',zlib.compress(payload))+chunk(b'IEND',b'')),16)
    def test_no_implicit_depth_or_boolean_profile(self):
        for value in[None,True,8.,32]:
            with self.assertRaises(RuntimeError):png_rgb_profile(self.put(png()[0]),value)
    def verify_export(self,source_data,export_data,bits):
        source=self.put(source_data,'source.png');diag=self.root/'diagnostics';diag.mkdir();recipe=dict(package='/Game/Dink/Refinements/FireplaceFiredClayV4/Textures/T0',bit_depth=bits,source_sha256=hashlib.sha256(source_data).hexdigest())
        recipes=[dict(recipe,package=recipe['package'][:-1]+str(i))for i in range(24)];recipes[0]=recipe
        def export(task):Path(task.filename).write_bytes(export_data);return True
        U=NS(AssetExportTask=lambda:NS(),TextureExporterPNG=lambda:object(),Exporter=NS(run_asset_export_task=export))
        with patch('native_texture_tools_v11._configure_profile',return_value=None):
            verify=make_pixel_verifier(U,diag,dict(textures=recipes),lambda:None)
            return verify(object(),source,recipe)
    def test_real_comparison_helper_accepts_rgb16_rgba16_and_reports_depth(self):
        a,rgb=png();b,_=png(channels=4,filter_kind=4);r=self.verify_export(a,b,16)
        self.assertEqual(r['decoded_RGB_sha256'],hashlib.sha256(rgb).hexdigest());self.assertEqual(r['decoded_bit_depth'],16)
        self.assertEqual((r['source_PNG_format']['color_type'],r['export_PNG_format']['color_type']),(2,6))
        self.assertEqual(r['RGB_sample_byte_order'],'big-endian16')
    def test_real_comparison_helper_rejects_low_byte_change(self):
        with self.assertRaisesRegex(RuntimeError,'pixels differ'):self.verify_export(png()[0],png(channels=4,low_delta=1)[0],16)
    def test_real_comparison_helper_rejects_export_depth_loss(self):
        with self.assertRaisesRegex(RuntimeError,'Expected RGB16'):self.verify_export(png()[0],png(8,4)[0],16)
    def test_real_comparison_helper_rejects_export_nonopaque_alpha(self):
        with self.assertRaisesRegex(RuntimeError,'alpha'):self.verify_export(png()[0],png(channels=4,alpha=65280)[0],16)
if __name__=='__main__':unittest.main()
