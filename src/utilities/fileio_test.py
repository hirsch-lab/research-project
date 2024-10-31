import random
import string
import unittest
import tempfile
from pathlib import Path

import utilities.testing as testing
from utilities.fileio import (listContent,
                              ensureCountedPath, 
                              copyFiles,
                              ensureDir,
                              readYAML, writeYAML)


################################################################################
class TestEnsureFilename(testing.TestCase):
    def doSetUp(self):
        self.tmpDir = tempfile.TemporaryDirectory(prefix="phd-test")
        self.path = Path(self.tmpDir.name)
        self.fileStem = "file"
        self.fileExt = ".txt"
        self.fileName = self.fileStem+self.fileExt
        self.folderName = "folder"
        self.pattern = "-%02d-abc" # some non-default pattern
        self.verbose = False

    def _createFiles(self, suffixes):
        for suffix in suffixes:
            if suffix is None:
                filename = self.fileName
            else:
                filename = self.fileStem+suffix+self.fileExt
            fid = open(self.path/filename, "w")
            fid.close()
            self.assertTrue((self.path/filename).is_file())

    def _createFolders(self, suffixes):
        for suffix in suffixes:
            if suffix is None:
                folderName = self.folderName
            else:
                folderName = self.folderName+suffix
            self.assertTrue(ensureDir(self.path/folderName))

    def _testCore(self, testCases, mode, label):
        if mode=="file":
            inPath = self.path/self.fileName
        elif mode=="folder":
            inPath = self.path/self.folderName

        if self.verbose: print("\n%s:" % label)
        for args, outExpected in testCases.items():
            skipFirst, minCount = args
            if self.verbose:
                print("    skipFirst=%s, minCount=%s: %s ==> %s" %
                      (skipFirst, minCount, inPath.name, Path(outExpected).name))
            outPath = ensureCountedPath(path=inPath,
                                        fmt=self.pattern,
                                        skipFirst=skipFirst,
                                        minCount=minCount)
            self.assertEqual(outPath, self.path/outExpected)

    def tearDown(self):
        self.tmpDir.cleanup()
        self.assertFalse(self.path.exists())

    def testIsFirstFile(self):
        # File does not exist.
        testCases = {
            # (skipFirst, minCount)
            (False, 0) : self.fileStem+"-00-abc"+self.fileExt,
            (False, 1) : self.fileStem+"-01-abc"+self.fileExt,
            (True,  0) : self.fileName,
            (True,  1) : self.fileName,
        }
        self._testCore(testCases, mode="file", label="testIsFirstFile")

    def testIsFirstFolder(self):
        # Folder does not exist.
        testCases = {
            # (skipFirst, minCount)
            (False, 0) : self.folderName+"-00-abc",
            (False, 5) : self.folderName+"-05-abc",
            (True,  0) : self.folderName,
            (True,  1) : self.folderName,
        }
        self._testCore(testCases, mode="folder", label="testIsFirstFolder")

    def testIsSecondFileA(self):
        # File exists already: "file.txt"
        testCases = {
            # (skipFirst, minCount)
            (False, 0) : self.fileStem+"-00-abc"+self.fileExt,
            (False, 1) : self.fileStem+"-01-abc"+self.fileExt,
            (True,  0) : self.fileStem+"-00-abc"+self.fileExt,
            (True,  1) : self.fileStem+"-01-abc"+self.fileExt,
        }
        self._createFiles(suffixes=[None])
        self._testCore(testCases, mode="file", label="testIsSecondFileA")

    def testIsSecondFileB(self):
        # File exists already: "file-01-abc.txt"
        testCases = {
            # (skipFirst, minCount)
            (False, 0) : self.fileStem+"-02-abc"+self.fileExt,
            (False, 5) : self.fileStem+"-02-abc"+self.fileExt,
            (True,  0) : self.fileStem+"-02-abc"+self.fileExt,
            (True,  8) : self.fileStem+"-02-abc"+self.fileExt,
        }
        self._createFiles(suffixes=[self.pattern%1])
        self._testCore(testCases, mode="file", label="testIsSecondFileB")

    def testIsSecondFolderA(self):
        # Folder exists already: "folder"
        testCases = {
            # (skipFirst, minCount)
            (False, 0) : self.folderName+"-00-abc",
            (False, 1) : self.folderName+"-01-abc",
            (True, 0) : self.folderName+"-00-abc",
            (True, 1) : self.folderName+"-01-abc",
        }
        self._createFolders(suffixes=[None])
        self._testCore(testCases, mode="folder", label="testIsSecondFolderA")

    def testIsSecondFileB(self):
        # Folder exists already: "folder-01-abc"
        testCases = {
            # (skipFirst, minCount)
            (False, 0) : self.folderName+"-02-abc",
            (False, 5) : self.folderName+"-02-abc",
            (True, 0) : self.folderName+"-02-abc",
            (True, 8) : self.folderName+"-02-abc",
        }
        self._createFolders(suffixes=[self.pattern%1])
        self._testCore(testCases, mode="folder", label="testIsSecondFileB")

    def testIsXthFile(self):
        # Files exist already: "file.txt", "file-01-abc.txt", "file-05-abc.txt"
        testCases = {
            # (skipFirst, minCount)
            (False, 0) : self.fileStem+"-06-abc"+self.fileExt,
            (False, 5) : self.fileStem+"-06-abc"+self.fileExt,
            (True,  0) : self.fileStem+"-06-abc"+self.fileExt,
            (True,  8) : self.fileStem+"-06-abc"+self.fileExt,
        }
        self._createFiles(suffixes=[None, self.pattern%1, self.pattern%5])
        self._testCore(testCases, mode="file", label="testIsXthFile")

    def testIsXthFolder(self):
        # Folders exist already: "folder", "folder-01-abc", "folder-06-abc"
        testCases = {
            # (skipFirst, minCount)
            (False, 0) : self.folderName+"-07-abc",
            (False, 5) : self.folderName+"-07-abc",
            (True,  0) : self.folderName+"-07-abc",
            (True,  8) : self.folderName+"-07-abc",
        }
        self._createFolders(suffixes=[None, self.pattern%1, self.pattern%6])
        self._testCore(testCases, mode="folder", label="testIsXthFolder")

################################################################################
class TestCopyDir(testing.TestCase):
    def doSetUp(self):
        self.tmpDir = tempfile.TemporaryDirectory(prefix="phd-test")
        self.src = Path(self.tmpDir.name).resolve() / "in"
        self.dst = Path(self.tmpDir.name).resolve() / "out"

        # Populate input directory with fake files:
        self.filesA = []
        self.filesB = []
        self.filesC = []
        self.dirsA = set()
        self.dirsB = set()
        self.dirsC = set()
        for i in range(4):
            for j in range(5):
                file = self.src / ("sub%02d" % i) / ("file%02d.a" % j)
                file.parent.mkdir(parents=True, exist_ok=True)
                file.touch()
                assert(file.exists())
                self.filesA.append(file.relative_to(self.src))
                self.dirsA.add(file.parent.relative_to(self.src))
        for i in range(3):
            for j in range(2):
                file = self.src / ("sub%02d" % i) / ("file%02d.b" % j)
                file.parent.mkdir(parents=True, exist_ok=True)
                file.touch()
                assert(file.exists())
                self.filesB.append(file.relative_to(self.src))
                self.dirsB.add(file.parent.relative_to(self.src))
        for i in range(2):
            for j in range(3):
                file = self.src / ("sub%02d" % i) / ("sub%02d" % i) / ("file%02d.c" % j)
                file.parent.mkdir(parents=True, exist_ok=True)
                file.touch()
                assert(file.exists())
                self.filesC.append(file.relative_to(self.src))
                self.dirsC.add(file.parent.relative_to(self.src))
        self.files = set(self.filesA + self.filesB + self.filesC)
        self.dirs = self.dirsA.union(self.dirsB).union(self.dirsC)

    def tearDown(self):
        tmpDirName = self.tmpDir.name
        self.tmpDir.cleanup()
        self.assertFalse(Path(tmpDirName).exists())

    def testListContent(self):
        files, dirs, symlinks = listContent(self.src,
                                            relto=self.src,
                                            symlinks=True)
        files = sorted(files)
        dirs = sorted(dirs)
        symlinks = sorted(symlinks)
        expectedFiles = sorted(self.files)
        expectedDirs = sorted(self.dirs)
        expectedSymlinks = []
        self.assertListEqual(files, expectedFiles)
        self.assertListEqual(dirs, expectedDirs)
        self.assertListEqual(symlinks, expectedSymlinks)

    def testCopyDirBasic(self):
        # Copy stuff from src dir to dst dir.
        copyFiles(self.src, self.dst)

        # Check copied content.
        files, dirs = listContent(self.dst, relto=self.dst)
        self.assertSetEqual(set(dirs), self.dirs)
        self.assertSetEqual(set(files), self.files)

    def testCopyDirGlob(self):
        # Copy stuff from src dir to dst dir.
        copyFiles(self.src, self.dst, globExp=["**/*.a", "sub01/*.b"])

        # Check copied content.
        files, dirs = listContent(self.dst, relto=self.dst)
        expectedDirs = self.dirsA.union(self.dirsB)
        expectedFiles = [ f for f in self.files if (f.suffix == ".a" or
                                                    (f.suffix == ".b" and
                                                     f.parent.name == "sub01"))]

        # Check copied content.
        files, dirs = listContent(self.dst, relto=self.dst)
        self.assertSetEqual(set(dirs), set(expectedDirs))
        self.assertSetEqual(set(files), set(expectedFiles))

    def testCopyFilesFlat(self):
        with self.assertLogs(level="WARN") as cm:
            # Warnings must be issued because multiple files are copied to
            # the same destination. (sub01/file01.a, sub02/file01.a, ...)
            copyFiles(self.src, self.dst, relative=False, globExp="**/*.*")

        # Check copied content.
        files, dirs = listContent(self.dst, relto=self.dst)
        expectedFiles = set(Path(f.name) for f in self.files)
        self.assertSetEqual(set(files), set(expectedFiles))
        self.assertEqual(len(dirs), 0)

    def testCopyListOnly(self):
        # This tests the dictionaries returned by copyFiles.
        files, dirs = copyFiles(self.src, self.dst, listOnly=True)

        # Expected output of the list.
        expectedDirs = [ self.dst / d for d in self.dirs ]
        expectedFiles = [ self.dst / f for f in self.files ]
        expectedDirs = dict(zip([self.src / d for d in self.dirs],
                                expectedDirs))
        expectedDirs[self.src] = self.dst
        expectedFiles = dict(zip([self.src / f for f in self.files],
                                 expectedFiles))

        self.assertDictEqual(dirs, expectedDirs)
        self.assertDictEqual(files, expectedFiles)

        # Check copied content.
        files, dirs = listContent(self.dst, relto=self.dst)
        self.assertListEqual(files, [])
        self.assertListEqual(dirs, [])

    def testCopyFilesFlatListOnly(self):
        # No warnings will be issued here, because the copy action is
        # not performed, so no copy collision occurs immediately.
        files, dirs = copyFiles(self.src, self.dst,
                                relative=False,
                                globExp="*/*",
                                listOnly=True)
        # However, the collisions should be apparent in the list of mapped
        # file locations.
        nUniqueSrcFiles = len(set(files.keys()))
        nUniqueDstFiles = len(set(files.values()))
        self.assertNotEqual(nUniqueSrcFiles, nUniqueDstFiles)

        # Check copied content.
        files, dirs = listContent(self.dst, relto=self.dst)
        self.assertListEqual(files, [])
        self.assertListEqual(dirs, [])

    def testInvalidGlob(self):
        with self.assertLogs(level="WARN") as cm:
            # A warning is issued per invalid glob expression.
            files, dirs = copyFiles(self.src, self.dst,
                                    globExp=["*/*/*/*", "**/*.d"])
        self.assertEqual(len(cm.output), 2)
        self.assertFalse(bool(files)) # Empty dict
        self.assertFalse(bool(dirs))  # Empty dict

    def testRenameFeature(self):
        suffix = "_haha"
        appendSuffix = lambda p: p.parent / (p.stem + suffix + p.suffix)
        files, dirs = copyFiles(self.src, self.dst, renameFun=appendSuffix)
        filesTest, dirsTest = listContent(self.dst)
        self.assertTrue(all(map(lambda p: p.stem.endswith(suffix), filesTest)))
        self.assertListEqual(sorted(list(files.values())), sorted(filesTest))
        self.assertListEqual(sorted(dirsTest), sorted(list(dirs.values())))

    def testRenameFeatureListOnly(self):
        # Append suffix to the file names, unary version.
        suffix = "_haha"
        appendSuffix = lambda p: p.parent / (p.stem + suffix + p.suffix)
        filesRef, dirsRef = copyFiles(self.src, self.dst, renameFun=appendSuffix)
        files, dirs = copyFiles(self.src, self.dst,
                                renameFun=appendSuffix, listOnly=True)
        self.assertDictEqual(files, filesRef)
        self.assertDictEqual(dirs, dirsRef)
        self.assertTrue(all(map(lambda p: p.stem.endswith(suffix), files.values())))

        # Append suffix to the file names, binary version.
        suffix = "_hoho"
        appendSuffix = lambda src, dst: dst.parent / (src.stem + suffix + src.suffix)
        filesRef, dirsRef = copyFiles(self.src, self.dst, renameFun=appendSuffix)
        files, dirs = copyFiles(self.src, self.dst,
                                renameFun=appendSuffix, listOnly=True)
        self.assertDictEqual(files, filesRef)
        self.assertDictEqual(dirs, dirsRef)
        self.assertTrue(all(map(lambda p: p.stem.endswith(suffix), files.values())))

    def testRenameFeatureThrowsException(self):
        # Resulting path must remain within the dst file tree.
        # An exception is thrown, if this is not the case.
        rename = lambda p: Path("some/strange/path") / p.name
        with self.assertRaises(ValueError):
            files, dirs = copyFiles(self.src, self.dst, renameFun=rename)

        # The function must be either unary or binary. An exception is
        # thrown in case it is not.
        rename = lambda a, b, c: we + never + come + here
        with self.assertRaises(ValueError):
            files, dirs = copyFiles(self.src, self.dst, renameFun=rename)

################################################################################
class TestYAML(testing.TestCase):
    def doSetUp(self):
        self.data = {
            "case1": None,
            "case2": list(range(5)),
            "case3": dict(a=1, b=2, c=3),
            "case4": set(range(5))
        }

    # def testYAML(self):
    #     # Test reading and writing of YAML file.
    #     with tempfile.TemporaryDirectory(prefix="phd-test") as tmpDir:
    #         dst = Path(tmpDir)/"test.yaml"
    #         self.assertTrue(writeYAML(dst, data=self.data))
    #         data = readYAML(src=dst)
    #         self.assertEqual(data, self.data)

    def testCompatbility(self):
        # Test reading and writing of YAML file.
        import numpy as np
        from pathlib import Path
        from utilities.data_types import StructContainer
        data = {}
        case = [{1,2,3}]
        data["sets"] = case
        case = dict(set={1,2,3}, lst=[{1,2,3}, {4,1,2}])
        data["nested sets"] = case
        case = [Path("a/b/c.txt")]
        data["pathlib.Path"] = case
        case = StructContainer(a=[1,2,3], b="test", c=None, d={1,2,3})
        data["StructContainer"] = case
        case = StructContainer(a=StructContainer(x=0, y="42", z=None))
        data["Nested StructContainer"] = case
        data["np.ndarray1"] = np.arange(10)
        data["np.ndarray2"] = np.array([{1,2,3}, [1,2,3], None], dtype=object)

        for key, case in data.items():
            with self.subTest(key):
                with tempfile.TemporaryDirectory(prefix="phd-test") as tmpDir:
                    dst = Path(tmpDir)/"test.yaml"
                    self.assertTrue(writeYAML(dst, data=case))
                    #dataOut = readYAML(src=dst)
                    #self.assertEqual(dataOut, dataIn)


################################################################################
if __name__ == "__main__":
    unittest.main(verbosity=2)
