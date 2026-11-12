"""Run the real packaging shell entry against a recording fake UAT, never Unreal.

The ShaderPrint wrapper is replaced only at the external tool boundary; its
source/overlay contract has separate tests in test_shaderprint_vulkan_workaround.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]


class PackageCookDirs(unittest.TestCase):
    def run_package(self, override=None):
        with tempfile.TemporaryDirectory(prefix='dink-package-test-') as folder:
            root = Path(folder)
            project = root / 'project with spaces'
            engine = root / 'fake engine'
            scripts = project / 'Scripts'
            scripts.mkdir(parents=True)
            shutil.copyfile(SCRIPTS / 'package.sh', scripts / 'package.sh')
            # Deliberate test-only passthrough: the child is solely our fake UAT.
            (scripts / 'shaderprint_vulkan_workaround.py').write_text(
                'import subprocess,sys\n'
                'raise SystemExit(subprocess.call(sys.argv[sys.argv.index("--")+1:]))\n')
            fixtures = {
                'DinkRemaster.uproject': '{}',
                'Config/DefaultEngine.ini': 'GameDefaultMap=/Game/Dink/_Generated/Maps/L_Greybox_World\n',
                'Binaries/Linux/libUnrealEditor-DinkRemaster.so': 'fake editor marker',
                'Content/Dink/Data/Story/dink.json': '{}',
                'Content/Dink/Data/Facts/dink_globals.csv': 'name,value\n',
                'Content/Dink/_Generated/Maps/L_Greybox_World.umap': 'fake map marker',
            }
            for name, content in fixtures.items():
                path = project / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            for name in ('Dink/_Generated/Sprites', 'Dink/Props', 'Characters', 'Input'):
                (project / 'Content' / name).mkdir(parents=True, exist_ok=True)
            uat = engine / 'Engine/Build/BatchFiles/RunUAT.sh'
            uat.parent.mkdir(parents=True)
            uat.write_text('#!/usr/bin/env python3\n'
                           'import json,os,pathlib,sys\n'
                           'args=sys.argv[1:]\n'
                           'pathlib.Path(os.environ["FAKE_UAT_ARGS"]).write_text(json.dumps(args))\n'
                           'stage=next(x.split("=",1)[1] for x in args if x.startswith("-stagingdirectory="))\n'
                           'binary=pathlib.Path(stage)/"Linux/DinkRemaster/Binaries/Linux/DinkRemaster"\n'
                           'binary.parent.mkdir(parents=True);binary.write_text("fake packaged marker");binary.chmod(0o755)\n'
                           'print("BUILD SUCCESSFUL")\n')
            uat.chmod(0o755)
            argv_file = root / 'uat.json'
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith('DINK_') and key != 'UE_ROOT'}
            env.update(UE_ROOT=str(engine), DINK_ALLOW_CONCURRENT='1', FAKE_UAT_ARGS=str(argv_file))
            if override is not None:
                env['DINK_COOK_DIRS'] = override
            result = subprocess.run(['bash', str(scripts / 'package.sh'), str(root / 'stage')],
                                    env=env, text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PACKAGE OK:', result.stdout)
            args = json.loads(argv_file.read_text())
            cook = [value for value in args if value.startswith('-cookdir=')]
            self.assertLessEqual(len(cook), 1)
            return ([value.removeprefix(str(project / 'Content') + '/')
                     for value in cook[0].split('=', 1)[1].split('+')] if cook else [])

    def test_default_cooks_dynamic_sprite_frames_alongside_existing_defaults(self):
        self.assertEqual(set(self.run_package()),
                         {'Dink/_Generated/Sprites', 'Dink/Props', 'Characters', 'Input'})

    def test_explicit_override_replaces_defaults_without_appending_sprite_directory(self):
        self.assertEqual(self.run_package('/chosen/one+/chosen/two'), ['/chosen/one', '/chosen/two'])

    def test_none_still_disables_extra_cook_directories(self):
        self.assertEqual(self.run_package('none'), [])


if __name__ == '__main__':
    unittest.main()
