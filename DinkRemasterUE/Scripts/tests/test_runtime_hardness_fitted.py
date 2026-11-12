import unittest
import test_runtime_hardness_native as core
class FittedHardnessTests(unittest.TestCase):
 compile_run=core.RuntimeHardnessCoreTests.compile_run
 def test_fitted_production_session_and_raster(self):
  self.compile_run('runtime_hardness_fitted.cpp','PASS fitted order/same-code residual')
