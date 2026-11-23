"""Scripts/AnimationQA/arm_clearance.py: the posture turn goes towards the trunk, and the clearance follows it."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'AnimationQA'))
import arm_clearance as ac  # noqa: E402


def bones(elbow_out=30.0):
    """A standing figure in mesh space (x = its left, y = forward, z = up, cm): arms hanging a little out."""
    b = {'pelvis': (0, 0, 95), 'spine_01': (0, 0, 100), 'spine_03': (0, 0, 113), 'spine_05': (0, 0, 141), 'neck_01': (0, 0, 152),
         'thigh_l': (10, 0, 93), 'thigh_r': (-10, 0, 93), 'upperarm_l': (19, 0, 143), 'upperarm_r': (-19, 0, 143),
         'lowerarm_l': (elbow_out, 0, 118), 'lowerarm_r': (-elbow_out, 0, 118), 'hand_l': (elbow_out + 6, 2, 92), 'hand_r': (-elbow_out - 6, 2, 92)}
    return {k: np.array(v, float) for k, v in b.items()}


TRUNK = {'slices': [[z, -15.0, 15.0, -10.0, 12.0] for z in range(80, 156)],
         'bones': {k: list(v) for k, v in bones().items()}}


class ArmClearance(unittest.TestCase):
    def test_turn_brings_both_arms_in(self):
        b = bones()
        for sd, side in (('l', 1.0), ('r', -1.0)):
            before = b['lowerarm_' + sd]
            after = ac.turn_arm(b['upperarm_' + sd], before, 8.0, side)
            self.assertLess(abs(after[0]), abs(before[0]))
            self.assertAlmostEqual(np.linalg.norm(after - b['upperarm_' + sd]), np.linalg.norm(before - b['upperarm_' + sd]), places=6)
            self.assertAlmostEqual(after[1], before[1], places=9)

    def test_clearance_shrinks_with_w_and_goes_negative_inside(self):
        trunk = ac.Trunk(TRUNK)
        res = ac.measure([(1, 'idle', bones())], trunk, [0.0, 6.0, 12.0])
        elbow = [np.array(res['idle'][w])[0, :, 0].min() for w in (0.0, 6.0, 12.0)]
        self.assertGreater(elbow[0], elbow[1])
        self.assertGreater(elbow[1], elbow[2])
        self.assertAlmostEqual(elbow[0], 30.0 - 15.0 - ac.LIMB['elbow'], delta=0.6)
        inside = ac.Trunk(TRUNK).clearance(np.array([5.0, 0.0, 110.0]), bones(), 3.0)
        self.assertLess(inside, 0)

    def test_report_names_states(self):
        trunk = ac.Trunk(TRUNK)
        frames = [(i, 'idle', bones()) for i in range(12)] + [(20 + i, 'run', bones(26.0)) for i in range(12)]
        text = ac.report(ac.measure(frames, trunk, [0.0, 6.0]), [0.0, 6.0])
        self.assertIn('idle', text)
        self.assertIn('run', text)
        picked = ac.pick_frames(frames)
        self.assertEqual(set(picked['idle']), {'near', 'mid', 'far'})


if __name__ == '__main__':
    unittest.main()
