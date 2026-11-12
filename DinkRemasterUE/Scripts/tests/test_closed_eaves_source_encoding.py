"""Portable counterparts of the reviewed external encoding controls.

Native storage uses an explicitly synthetic16-byte fixture, not private GPU-run
files. Actual32-source policy pins are tested separately; no GPU/native claim.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from RoofNative import closed_eaves_house_texture_encoding as H

class Enum:
    def __init__(self,value):
        self.value=value;self.name={0:'NONE',2:'S_RGB'}.get(value,'OTHER')
class Encoding(Enum):
    @classmethod
    def cast(cls,value):return cls(value)
class Space(Enum):pass
U=SimpleNamespace(EnumBase=Enum,TextureSourceEncoding=Encoding,TextureColorSpace=Space)

class Settings:
    def __init__(self):
        self.values=dict(encoding_override=Encoding(0),color_space=Space(0),
                         white_point={'x':.3127,'y':.329},unknown_future_field=17)
    def get_editor_property(self,key):return self.values[key]
    def set_editor_property(self,key,value):self.values[key]=value
    def copy(self):return copy.deepcopy(self)
    def to_dict(self):return self.values
    def export_text(self):return json.dumps(H.snapshot(self.values,U),sort_keys=True)

class Texture:
    def __init__(self,target,metadata):
        self.target=target;self.metadata=metadata;self.settings=Settings();self.writes=0;self.defect=None
    def get_path_name(self):return self.target+'.'+self.target.rsplit('/',1)[1]
    def get_editor_property(self,key):return self.settings
    def set_editor_property(self,key,value):
        self.settings=value;self.writes+=1
        if self.defect=='field':self.settings.values['unknown_future_field']=99
        elif self.defect=='enum':self.settings.values['encoding_override']=Encoding(1)
    def inspect(self):
        out=dict(self.metadata,texture=self.get_path_name(),
                 source_encoding_override_none=self.settings.values['encoding_override'].value==0,
                 source_color_space_none=self.settings.values['color_space'].value==0)
        if self.writes and self.defect=='gamma':out['source_gamma']='Pow22'
        if self.writes and self.defect=='bytes':out['base64']=base64.b64encode(b'x'*16).decode()
        return out
U.DinkMaterialArtLibrary=SimpleNamespace(inspect_texture_source_pixels=lambda obj:json.dumps(obj.inspect()))

class SourceEncodingControls(unittest.TestCase):
    def fixture(self,changed=True):
        classes,pins,values=H.policy()
        sha=next(k for k,v in values.items()if v==(2 if changed else 0))
        pins=copy.deepcopy(pins);raw=bytes(range(16))
        pins[sha].update(width=2,height=2,native_expected_format='BGRA8',
            expected_native_storage_bytes=len(raw),expected_native_storage_sha256=hashlib.sha256(raw).hexdigest())
        image=dict(sha256=sha,colorspace=classes[sha]['colorspace'],size=[2,2]);target=H.target_for(sha)
        metadata=dict(schema='dink-texture-source-pixels/1',valid=True,format='BGRA8',width=2,height=2,
            texture_srgb=image['colorspace']=='sRGB',gpu_pixels_read=False,row_origin='top_left',
            byte_order='little',source_gamma='Linear',base64=base64.b64encode(raw).decode(),byte_count=len(raw))
        return (classes,pins,values),sha,dict(target=target,image=image),Texture(target,metadata)
    def configure(self,fixture):
        policy,sha,row,texture=fixture
        with patch.object(H,'policy',return_value=policy):
            return H.configure_texture(U,texture,sha,row,lambda:None)
    def test_actual_policy_exact_eight_and_twentyfour(self):
        classes,pins,values=H.policy()
        self.assertEqual(len(classes),32);self.assertEqual(set(classes),set(pins))
        self.assertEqual(sum(v==2 for v in values.values()),8);self.assertEqual(sum(v==0 for v in values.values()),24)
    def test_policy_payload_tamper_refused(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp)
            for p in H.DATA.iterdir():
                if p.is_file():(root/p.name).write_bytes(p.read_bytes())
            p=root/'CLASSES.json';p.write_bytes(p.read_bytes()+b' ')
            with patch.object(H,'DATA',root),self.assertRaises(ValueError):H.policy()
    def test_changed_class_preserves_other_settings_storage_gamma(self):
        f=self.fixture();texture=f[3];prior=texture.settings;before=prior.export_text();result=self.configure(f)
        self.assertEqual(texture.writes,1);self.assertEqual(prior.export_text(),before)
        self.assertEqual(result['reflected_encoding']['override_value'],2)
        self.assertEqual(texture.settings.values['unknown_future_field'],17)
        self.assertTrue(result['raw_source_storage']['source_storage_exact'])
        self.assertEqual(result['raw_source_storage']['native_source_gamma'],'Linear')
        self.assertFalse(result['gpu_pixel_equivalence_accepted'])
    def test_other_class_no_write(self):
        f=self.fixture(False);result=self.configure(f)
        self.assertEqual(f[3].writes,0);self.assertFalse(result['changed'])
        self.assertEqual(result['reflected_encoding']['override_value'],0)
    def test_identity_or_prestate_refused_before_write(self):
        for defect in('identity','enum','space'):
            f=self.fixture();texture=f[3]
            if defect=='identity':texture.target+='_Other'
            elif defect=='enum':texture.settings.values['encoding_override']=Encoding(1)
            else:texture.settings.values['color_space']=Space(1)
            with self.subTest(defect=defect),self.assertRaises(ValueError):self.configure(f)
            self.assertEqual(texture.writes,0)
    def test_native_readback_drift_refused(self):
        for defect in('field','enum','gamma','bytes'):
            f=self.fixture();f[3].defect=defect
            with self.subTest(defect=defect),self.assertRaises((ValueError,RuntimeError)):self.configure(f)
    def test_revoked_guard_before_write(self):
        policy,sha,row,texture=self.fixture()
        def revoked():raise RuntimeError('revoked')
        with patch.object(H,'policy',return_value=policy),self.assertRaisesRegex(RuntimeError,'revoked'):
            H.configure_texture(U,texture,sha,row,revoked)
        self.assertEqual(texture.writes,0)
    def test_wrong_class_override_and_storage_provenance_refused(self):
        policy,sha,row,texture=self.fixture(False)
        with patch.object(H,'policy',return_value=policy),self.assertRaises(ValueError):
            H.verify_storage(texture.inspect(),sha,row['image'],row['target'],2)
        for key,value in [('gpu_pixels_read',True),('byte_order','big'),('base64',base64.b64encode(b'x'*16).decode())]:
            policy,sha,row,texture=self.fixture();actual=texture.inspect();actual[key]=value
            with self.subTest(field=key),patch.object(H,'policy',return_value=policy),self.assertRaises(ValueError):
                H.verify_storage(actual,sha,row['image'],row['target'],0)

if __name__=='__main__':unittest.main()
