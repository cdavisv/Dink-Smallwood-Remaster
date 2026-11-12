import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sync_gameplay_data as sync
from sync_gameplay_data import release_picture_keys

class ReleasedPictureMetadata(unittest.TestCase):
    def frame(self, **updates):
        return dict({'frame': 6, 'width': 84, 'height': 64, 'origin': {'x': 41, 'y': 44}}, **updates)

    def test_canonical_reader_origin_and_descriptor(self):
        result = sync.picture_descriptor(173, self.frame())
        self.assertEqual((result['origin_x'], result['origin_y']), (41, 44))
        self.assertEqual(result['picture_descriptor_sha1'], hashlib.sha1(b'DinkPictureDescriptor/1:173,6,84,64,41,44').hexdigest())

    def test_pivot_is_frame_specific_not_assumed_sequence_constant(self):
        a = sync.picture_descriptor(173, self.frame())
        b = sync.picture_descriptor(173, self.frame(origin={'x': 40, 'y': 43}))
        self.assertNotEqual(a['picture_descriptor_sha1'], b['picture_descriptor_sha1'])
        self.assertEqual(b['origin_x'], 40)

    def test_missing_canonical_origin_refuses_instead_of_guessing(self):
        with self.assertRaises(ValueError):
            sync.picture_descriptor(173, self.frame(origin=None))
        with self.assertRaises(ValueError):
            sync.picture_descriptor(173, self.frame(origin={'x': 41.0, 'y': 44}))

    def test_empty_frame_is_not_a_presentable_picture(self):
        self.assertEqual(sync.picture_descriptor(173, self.frame(empty=True))['picture_descriptor_sha1'], '')

    def test_release_exports_all_nonempty_canonical_frames_only_for_opted_sources(self):
        policy={'collision_fit':{'origins':[{'origin':'S031_P03'}]}}
        placements=[{'id':'S031_P03','seq':173},{'id':'S031_P04','seq':12}]
        frames=[dict(self.frame(frame=i), image=f'sprites/173/{i:02d}.png') for i in range(1,7)]
        frames.append(self.frame(frame=7,empty=True))
        keys=release_picture_keys(policy,placements,[{'seq':173,'frames':frames}])
        self.assertEqual(set(keys), {f'173_{i:02d}' for i in range(1,7)})
        with self.assertRaises(ValueError):
            release_picture_keys(policy,placements,[])
        frames[2].pop('image')
        with self.assertRaises(ValueError):
            release_picture_keys(policy,placements,[{'seq':173,'frames':frames}])

    def test_export_preserves_gameplay_fields_and_actual_frame_pivots(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            frames=[self.frame(frame=1, width=56, height=55), self.frame(origin={'x': 39, 'y': 42})]
            for frame in frames:
                frame.update(delay_ms=75, hardbox={'left':-17,'top':-15,'right':20,'bottom':6})
            (root/'sequences.json').write_text(json.dumps({'sequences':[{'seq':173,'frames':frames}]}))
            rows=sync.frames(root)
            self.assertEqual([r['origin_x'] for r in rows], [41,39])
            self.assertEqual([r['width'] for r in rows],[56,84])
            self.assertEqual([r['delay_ms'] for r in rows],[75,75])
            self.assertEqual(rows[1]['left'],-17)

if __name__=='__main__': unittest.main()
