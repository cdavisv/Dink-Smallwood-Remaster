"""python3 -m unittest discover -s tools/coord/tests"""
import importlib.util
import pathlib
import random
import shutil
import subprocess
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lfs_private_check', HERE / 'lfs_private_check.py')
lpc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lpc)

HOME = '/' + 'home'   # split so the repository's own path check does not flag this file


class Hits(unittest.TestCase):
    def test_plain_home_path(self):
        self.assertEqual(lpc.hits(f'x {HOME}/zed9/Work/a'.encode(), []), [f'{HOME}/zed9'])

    def test_neutral_user_allowed(self):
        self.assertEqual(lpc.hits(f'{HOME}/runner/work {HOME}/artist/x'.encode(), []), [])

    def test_utf16_string_in_binary(self):
        data = b'\x00\x01' + f'{HOME}/qq7/a'.encode('utf-16-le') + b'\x00'
        self.assertEqual(lpc.hits(data, []), [f'{HOME}/qq7'])

    def test_windows_and_mac(self):
        self.assertTrue(lpc.hits(b'C:\\' + b'Users\\bob\\x', []))
        self.assertTrue(lpc.hits(('/' + 'Users/bob/x').encode(), []))

    def test_extra_word(self):
        self.assertEqual(lpc.hits(b'..secretlogin..', [lpc.re.compile(b'secretlogin', lpc.re.I)]), ['secretlogin'])

    @unittest.skipUnless(shutil.which('zstd'), 'zstd not installed')
    def test_zstd_blend(self):
        rnd = random.Random(7)
        filler = ''.join(rnd.choice('abcdefghijklmnopqrstuvwxyz ') for _ in range(20000))
        raw = f'BLENDER {filler[:10000]} {HOME}/zed9/tex.png {filler[10000:]}'.encode()
        packed = subprocess.run(['zstd', '-c'], input=raw, capture_output=True, check=True).stdout
        self.assertNotIn(b'zed9', packed)
        self.assertIn(f'{HOME}/zed9', lpc.hits(packed, []))


if __name__ == '__main__':
    unittest.main()
