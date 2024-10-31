import os
import logging
import unittest
import importlib
import numpy as np
import pandas as pd
from pathlib import Path as p
from contextlib import redirect_stdout

# NOTE: It may occur that RuntimeWarnings are issued that usually are not
# present outside unittests. For example:
#       "numpy.ufunc size changed, may indicate binary incompatibility."
#       "numpy.dfunc size changed, may indicate binary incompatibility."
#       "numpy.ndarray size changed, may indicate binary incompatibility."
# I described the issue here:
#       https://github.com/numpy/numpy/issues/14920
# Resolution: don't bother too much. Either import everything outside of
#             TestCases, or inside TestCases.
#             The problem arises because unittest may disable some warning
#             filters set by numpy.__init__.

################################################################################
# UTILITIES
################################################################################
def logStartOfTestCase(name):
    name = name.replace("__main__.","")
    logger = logging.getLogger("test")
    logger.info("#"*60)
    logger.info("Test: %s", name)
    logger.info("#"*60)

################################################################################
def isModuleAvailable(name):
    try:
        ret = importlib.import_module(name)
        return bool(ret)
    except:
        return False

################################################################################
def isEnvAvailable(env):
    ret = os.getenv(env)
    return bool(ret)

################################################################################
def checkModule(name):
    ret = not isModuleAvailable(name)
    msg = "Module %s is not available." % name
    return ret, msg

################################################################################
def checkEnv(env):
    ret = not isEnvAvailable(env)
    msg = "Environment variable %s is not set." % env
    return ret, msg

################################################################################
def skipIfModuleNotFound(name):
    return unittest.skipIf(*checkModule(name))

################################################################################
def skipIfEnvNotSet(env):
    return unittest.skipIf(*checkEnv(env))

################################################################################
class StdoutRedirectionContext():
    # https://stackoverflow.com/questions/59201313/
    class ListIO():
        def __init__(self):
            self.output = []
        def write(self, s):
            if s in ("\n", ""): return
            self.output.append(s)

    def __enter__(self):
        self._buf = self.ListIO()
        self._ctx = redirect_stdout(self._buf)
        self._ctx.__enter__()
        return self._buf

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._ctx.__exit__(exc_type, exc_value, exc_traceback)
        del self._ctx

################################################################################
# TEST CASE
################################################################################
class TestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The child class must never override setUp().
        # Instead, it should override doSetUp().
        # Check if this is the case and raise an exception otherwise.
        # Source: https://stackoverflow.com/a/1777092/3388962
        baseMethod = getattr(TestCase, "setUp")
        childMethod = getattr(self, "setUp")
        if baseMethod is not childMethod.__func__:
            qualName = ".".join([self.__module__, type(self).__name__])
            msg = ("%s must not override setUp(). "
                   "Implement doSetUp() instead!") % qualName
            raise AttributeError(msg)

    def assertIsFile(self, path):
        if path is None:
            raise AssertionError("None is not a valid path.")
        if not p(path).resolve().is_file():
            raise AssertionError("File does not exist: %s" % str(path))

    def assertIsNotFile(self, path):
        if path is None:
            raise AssertionError("None is not a valid path.")
        if p(path).resolve().is_file():
            raise AssertionError("File should not exist: %s" % str(path))

    def assertIsDir(self, path):
        if path is None:
            raise AssertionError("None is not a valid path.")
        if not p(path).resolve().is_dir():
            raise AssertionError("Dir does not exist: %s" % str(path))

    def assertIsNotDir(self, path):
        if path is None:
            raise AssertionError("None is not a valid path.")
        if p(path).resolve().is_dir():
            raise AssertionError("Dir should not exist: %s" % str(path))

    def assertExists(self, path):
        if path is None:
            raise AssertionError("None is not a valid path.")
        if not p(path).resolve().exists():
            raise AssertionError("Path does not exist: %s" % str(path))

    def assertNotExists(self, path):
        if path is None:
            raise AssertionError("None is not a valid path.")
        if p(path).resolve().exists():
            raise AssertionError("Path should not exist: %s" % str(path))

    def assertArrayEqual(self, x, y):
        np.testing.assert_array_equal(x, y)

    def assertAlmostEqual(self, x, y, places=7):
        # Overrides the corresponding method of unittest.TestCase.
        np.testing.assert_almost_equal(x, y, decimal=places)

    def assertFrameEqual(self, x, y, **kwargs):
        pd.testing.assert_frame_equal(x, y, **kwargs)

    def assertStdout(self):
        """
        Use similarly as assertLogs():
            https://docs.python.org/3/library/unittest.html
            https://stackoverflow.com/questions/59201313

            class SomeTest(TestCase):
                def test_stdout(self):
                    with self.assertStdout() as cm:
                        print("foo!")
                        print("bar!")
                    self.assertIn("foo!", cm.output)
                    self.assertIn("baz!", cm.output)
        """
        return StdoutRedirectionContext()

    def setUp(self):
        logStartOfTestCase(self.id())
        if hasattr(self, "doSetUp"):
            self.doSetUp()
