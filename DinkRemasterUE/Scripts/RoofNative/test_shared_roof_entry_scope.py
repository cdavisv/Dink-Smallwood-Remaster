"""Native-wrapper surrogate lifetime, not a claim about actual UE finalization."""
import gc
import sys
from pathlib import Path
import weakref
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import shared_roof_entry_template as E


class EntryScope(unittest.TestCase):
    def exercise(self, failure=False, chained=False):
        events, refs = [], []
        real_collect = gc.collect
        enabled = gc.isenabled()
        gc.disable()
        class Alias:
            def __init__(self):
                self.cycle = self
        def helper():
            alias = Alias()
            refs.append(weakref.ref(alias))
            raise ValueError('inner native scope failure')
        def scope():
            try:
                if chained:
                    try:
                        helper()
                    except ValueError as error:
                        raise RuntimeError('outer native scope failure') from error
                alias = Alias()
                refs.append(weakref.ref(alias))
                if failure:
                    raise RuntimeError('native scope failure')
                return {'plain': True}
            finally:
                events.append('scope_exited')
        def collect():
            self.assertIn('scope_exited', events)
            events.append('collected')
            value = real_collect()
            self.assertTrue(all(r() is None for r in refs), 'Native-frame alias survived to teardown')
            return value
        try:
            with patch.object(E, '_native_scope', scope), patch.object(E.gc, 'collect', collect):
                if failure or chained:
                    with self.assertRaisesRegex(RuntimeError, 'native scope failure'):
                        E.run_phase()
                else:
                    self.assertEqual(E.run_phase(), {'plain': True})
            self.assertEqual(events, ['scope_exited', 'collected'])
        finally:
            if enabled:
                gc.enable()

    def test_non_json_native_result_is_rejected_and_released(self):
        refs = []
        real_collect = gc.collect
        class Alias:
            def __init__(self):
                self.cycle = self
        def scope():
            alias = Alias()
            refs.append(weakref.ref(alias))
            return alias
        def collect():
            n = real_collect()
            self.assertTrue(all(r() is None for r in refs))
            return n
        with patch.object(E, '_native_scope', scope), patch.object(E.gc, 'collect', collect):
            with self.assertRaises(TypeError):
                E.run_phase()

    def test_success_scope_releases_CDO_closure_surrogates_before_collection(self):
        self.exercise()

    def test_failure_frames_are_cleared_before_collection(self):
        self.exercise(failure=True)

    def test_chained_exception_frames_are_all_cleared(self):
        self.exercise(chained=True)


if __name__ == '__main__':
    unittest.main()
