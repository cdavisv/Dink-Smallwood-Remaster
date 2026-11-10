import unittest
import numpy as np
from dinkex.runtime_hardness import runtime_layers as actual_runtime_layers

def runtime_layers(hard,tiles,sprites,box,**kwargs):
    flags=[0]*99
    for index,sprite in sprites.items():
        if 1<=index<=99:flags[index-1]=sprite["hard"]
    return actual_runtime_layers(hard,tiles,sprites,box,editor_hard_flags=flags,**kwargs)
from dinkex.hard import CODE_SPRITE, build_hitmap

class FakeHard:
    def __init__(self):
        self.tiles = np.zeros((1,50,50),dtype=np.uint8)
        self.tiles[0,0,0] = 2
        self.tiles[0,0,1] = 1
    def lookup(self,num,althard):
        return (0,'index',num != -1)

def sprite(x=20,y=0,que=0,hard=0,vision=0,prop=0):
    return dict(active=True,x=x,y=y,que=que,hard=hard,vision=vision,prop=prop)

def box(s):
    return dict(left=0,top=0,right=4,bottom=3)

class RuntimeHardnessExportTests(unittest.TestCase):
    def setUp(self):
        self.hard=FakeHard();self.tiles=[dict(num=0,althard=0) for _ in range(96)]
    def test_tile_base_survives_hidden_stamp_and_exact_existing_composition(self):
        sprites={1:sprite(),2:sprite(x=22,que=1,prop=1),3:sprite(hard=1),4:sprite(vision=2)}
        packet=runtime_layers(self.hard,self.tiles,sprites,box)
        self.assertEqual([s['owner'] for s in packet['ordered_stamps']],[1,2])
        self.assertEqual(packet['tile_base_rle'][0][:3],[[1,2],[1,1],[48,0]])
        raster=np.array([[code for count,code in row for _ in range(count)]
                         for row in packet['tile_base_rle']],dtype=np.uint8)
        for s in packet['ordered_stamps']:
            x0,y0,x1,y1=s['rect'];raster[y0:y1,x0:x1]=s['code']
        codes,owners,_=build_hitmap(self.hard,self.tiles,sprites,box)
        codes[codes>=CODE_SPRITE]=100+owners[codes>=CODE_SPRITE]
        np.testing.assert_array_equal(raster,codes)
        self.assertTrue(packet['ordered_stamps'][1]['warp'])
    def test_vision_and_tie_order_are_preserved(self):
        sprites={5:sprite(y=10,vision=2),2:sprite(y=10),1:sprite(y=10)}
        packet=runtime_layers(self.hard,self.tiles,sprites,box,vision=2)
        self.assertEqual([s['owner'] for s in packet['ordered_stamps']],[1,2,5])
    def test_clipped_rectangles_and_missing_picture(self):
        sprites={1:sprite(x=18,y=-1),2:sprite(x=-30),3:sprite()}
        packet=runtime_layers(self.hard,self.tiles,sprites,lambda s:None if s is sprites[3] else box(s))
        self.assertEqual(packet['ordered_stamps'],[dict(owner=1,code=101,rect=[0,0,2,2],warp=False)])
    def test_skipped_tiles_explicit_never_inferred_from_composed_owners(self):
        self.tiles[7]['num']=-1
        self.assertEqual(runtime_layers(self.hard,self.tiles,{},box)['skipped_tile_indices'],[7])
        self.hard.tiles[0,0,0]=100
        with self.assertRaises(ValueError):runtime_layers(self.hard,self.tiles,{},box)

class RuntimeHardnessSchemaTests(unittest.TestCase):
    def test_decoder_accepts_exact_export(self):
        from dinkex.runtime_hardness import decode_runtime_layers
        packet=runtime_layers(FakeHard(),[dict(num=0,althard=0) for _ in range(96)],{1:sprite()},box)
        base,stamps=decode_runtime_layers(packet)
        self.assertEqual(len(base),240000)
        self.assertEqual(base[:3],bytes([2,1,0]))
        self.assertEqual(stamps[0]['code'],101)
    def test_decoder_refuses_inferred_missing_base_bad_owner_and_skipped_cells(self):
        import copy
        from dinkex.runtime_hardness import decode_runtime_layers
        good=runtime_layers(FakeHard(),[dict(num=0,althard=0) for _ in range(96)],{1:sprite()},box)
        faults=[('schema','legacy'),('tile_base_rle',[]),('skipped_tile_indices',[7])]
        for field,value in faults:
            bad=copy.deepcopy(good);bad[field]=value
            with self.assertRaises(ValueError):decode_runtime_layers(bad)
        for value in [100,101,-1]:
            bad=copy.deepcopy(good);bad['tile_base_rle'][0][0][1]=value
            with self.assertRaises(ValueError):decode_runtime_layers(bad)
        bad=copy.deepcopy(good);bad['tile_base_rle'][0][0][0]=601
        with self.assertRaises(ValueError):decode_runtime_layers(bad)
        bad=copy.deepcopy(good);bad['ordered_stamps'][0]['code']=200
        with self.assertRaises(ValueError):decode_runtime_layers(bad)
        bad=copy.deepcopy(good);bad['ordered_stamps']*=2
        with self.assertRaises(ValueError):decode_runtime_layers(bad)

    def test_decoder_binds_signed_int32_vision_and_strict_dimensions(self):
        import copy
        from dinkex.runtime_hardness import decode_runtime_layers
        good=runtime_layers(FakeHard(),[dict(num=0,althard=0) for _ in range(96)],{},box,vision=-1)
        decode_runtime_layers(good,expected_vision=-1)
        for value in [None,True,1.0,'-1',2**31,-(2**31)-1]:
            bad=copy.deepcopy(good);bad['vision']=value
            with self.assertRaises(ValueError):decode_runtime_layers(bad,expected_vision=-1)
        bad=copy.deepcopy(good);del bad['vision']
        with self.assertRaises(ValueError):decode_runtime_layers(bad,expected_vision=-1)
        with self.assertRaises(ValueError):decode_runtime_layers(good,expected_vision=0)
        for field in ['width','height']:
            for value in [True,600.0 if field=='width' else 400.0]:
                bad=copy.deepcopy(good);bad[field]=value
                with self.assertRaises(ValueError):decode_runtime_layers(bad)


class RawEditorHardFlagsTests(unittest.TestCase):
    def test_inactive_slots_read_from_actual_raw_record(self):
        import struct
        from dinkex.mapdata import parse_screen, SMALL_MAP_SIZE, SPRITE_BASE, SPRITE_SIZE
        raw=bytearray(SMALL_MAP_SIZE)
        struct.pack_into('<i',raw,SPRITE_BASE+13*SPRITE_SIZE+120,-7)
        screen=parse_screen(raw,1)
        self.assertNotIn(13,screen.sprites)
        self.assertEqual(len(screen.editor_hard_flags),99)
        self.assertEqual(screen.editor_hard_flags[12],-7)
        packet=actual_runtime_layers(FakeHard(),[dict(num=0,althard=0)for _ in range(96)],screen.sprites,box,editor_hard_flags=screen.editor_hard_flags)
        self.assertEqual(packet['editor_hard_flags'][12],-7)
    def test_missing_bool_short_and_overflow_refuse_producer_and_consumer(self):
        from dinkex.runtime_hardness import decode_runtime_layers
        tiles=[dict(num=0,althard=0)for _ in range(96)]
        good=actual_runtime_layers(FakeHard(),tiles,{},box,editor_hard_flags=[0]*99)
        for flags in [None,[],[0]*98,[False]+[0]*98,[2**31]+[0]*98,[-2**31-1]+[0]*98,[0.0]+[0]*98]:
            with self.assertRaises(ValueError):actual_runtime_layers(FakeHard(),tiles,{},box,editor_hard_flags=flags)
            bad=dict(good);bad['editor_hard_flags']=flags
            with self.assertRaises(ValueError):decode_runtime_layers(bad)
        bad=dict(good);del bad['editor_hard_flags']
        with self.assertRaises(ValueError):decode_runtime_layers(bad)
