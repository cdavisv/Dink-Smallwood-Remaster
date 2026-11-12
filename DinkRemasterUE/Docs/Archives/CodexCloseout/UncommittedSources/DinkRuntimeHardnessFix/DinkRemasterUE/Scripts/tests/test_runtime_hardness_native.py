"""Compile and execute the actual engine-independent production transition core."""
from pathlib import Path
import subprocess
import tempfile
import unittest

class RuntimeHardnessCoreTests(unittest.TestCase):
    def test_native_transition_and_collision_partition(self):
        self.compile_run('runtime_hardness.cpp', 'PASS removal/restoration/overlap')

    def test_native_session_transaction(self):
        self.compile_run('runtime_hardness_session.cpp', 'PASS session isolation/transaction')

    def test_native_original_open_shell(self):
        self.compile_run('runtime_hardness_shell.cpp', 'PASS original open-bottom shell')

    def compile_run(self, filename, expected):
        project = Path(__file__).resolve().parents[2]
        include = project / 'Plugins/DinkNarrative/Source/DinkNarrative/Public'
        source = Path(__file__).parent / 'native' / filename
        with tempfile.TemporaryDirectory(prefix='dink-hardness-core-') as work:
            binary = Path(work) / 'hardness'
            subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                            '-fno-exceptions', '-fno-rtti', '-I', str(include),
                            '-I', str(project / 'Plugins/DinkCore/Source/DinkCore/Public'),
                            str(source), '-o', str(binary)], check=True, capture_output=True)
            result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
            self.assertIn(expected, result.stdout)
