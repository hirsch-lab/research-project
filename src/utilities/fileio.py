import os
import re
import sys
import copy
import json
import errno
import shutil
import logging
import warnings
import numpy as np
from pathlib import Path
from itertools import chain, repeat
from collections import OrderedDict
from contextlib import contextmanager
from utilities.progressbar import createProgressBar
from utilities.data_types import StructContainer

try:
    import oyaml as yaml
except ImportError:
    warnings.warn("Failed to load oyaml. Using yaml instead.")
    import yaml

_loggerId = "utils.fileio"


################################################################################
@contextmanager
def cwd(path):
    """
    Current working directory context.

    Argument path can be None, cwd then will behave like a nullcontext:
    https://docs.python.org/3/library/contextlib.html#contextlib.nullcontext

    Usage:
        with cwd("some/path"):
            # ...

    Source: https://stackoverflow.com/a/37996581/3388962
    """
    if path is None:
        yield
    else:
        oldpwd=os.getcwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(oldpwd)


################################################################################
def queryConfirmation(question, default="yes"):
    """
    Arguments:
        question:   A string presented to the user.
        default:    The presumed answer if user just hits <Enter>.
                    Must be "yes", "no" or None (answer is mandatory).
    Returns True for "yes", False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: %s" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Invalid answer. Please try again.\n")

################################################################################
# DIRECTORIES
################################################################################
def listDirnames(path, exclude=None):
    if os.path.isdir(path):
        # Credits: https://stackoverflow.com/a/142535/3388962
        dirnames = next(os.walk(path))[1]
        # Filter.
        if exclude:
            exclude = set(exclude)
            dirnames = [ d for d in dirnames if d not in exclude ]
        return dirnames
    else:
        return []


################################################################################
def listContent(path, relto=None, symlinks=False):
    """
    List the files, subdirs and optionally the symlinks of the target.
    The function returns lists of pathlib.Path objects.

    Arguments:
        path:       Path to directory to examine
        relto:      If not None, return paths relative to this location
        symlinks:   If True, the function also returns a list of symlinks
    """
    path = Path(path).resolve(strict=False)
    content = list(path.glob("**/*"))
    info = lambda p: p.relative_to(relto) if relto else p
    dirs = [ info(p) for p in content if p.is_dir() ]
    files = [ info(p) for p in content if p.is_file() ]
    if symlinks:
        # Also return symlinks if requested.
        symlinks = [ info(p) for p in content if p.is_symlink() ]
        return files, dirs, symlinks
    else:
        return files, dirs


################################################################################
def ensureDir(dirPath, logger=None):
    if logger is None:
        logger = logging.getLogger(_loggerId)
    if not dirPath: # None or empty string.
        logger.error("Invalid dirPath: %s", dirPath)
        return False
    if not os.path.isdir(dirPath):
        logger.debug("Creating output directory: %s", dirPath)
        # NOTE: To check isdir() and then to call makedirs() is not thread-safe.
        #       In python3, the flag exist_ok was introduced to achieve this.
        #       Catching the "File exists" exception works also on python2.
        dirPath = os.path.abspath(dirPath)
        try:
            os.makedirs(dirPath)
        except OSError as e:
            # Only catch the "file/folder exists" exception.
            if e.errno != errno.EEXIST:
                raise
        if not os.path.isdir(dirPath):
            logger.error("Could not create output directory: %s", dirPath)
            return False
    return True


################################################################################
def ensureEmptyDir(dirPath, enforce=False, logger=None):
    if logger is None:
        logger = logging.getLogger(_loggerId)
    dirPath = Path(dirPath)
    if dirPath.is_dir():
        if enforce:
            answer = True
        else:
            question = ("The folder %s will be deleted.\n"
                        "Do you want to proceed?") % dirPath
            answer = queryConfirmation(question=question, default="no")
        if answer:
            logger.info("Removing folder: %s", dirPath)
            removeFileOrFolder(path=dirPath)
    if ensureDir(dirPath, logger=logger):
        exclude = [".DS_Store"]
        folderContent = dirPath.glob("*")
        folderContent = [f for f in folderContent if f.name not in exclude]
        return len(folderContent) == 0
    return False


################################################################################
def ensureCountedPath(path, fmt="-%03d",
                      skipFirst=False,
                      minCount=1,
                      step=1,
                      ensureParent=True,
                      disable=False):
    """
    Transform path such that it will not collide with existing files or folders
    by appending the filename with a formatted count.

    Arguments:
        path:           Target path for file or folder.
        fmt:            Format for indexer.
        skipFirst:      If True, path is returned unmodified if no existing
                        item was identified. Otherwise, append a counter
                        already for the first item.
        minCount:       Index of first count. Has an effect only if the current
                        count is smaller than minCount.
        step:           Step by which the current index is incremented.
        ensureParent:   Ensure parent directory. Default: enabled.
        disable:        Disable the functionality, simply return path.

    Examples:
        - File already exists in folder:
            ensureCountedPath(folder/file.txt) => folder/file001.txt
        - File already exists 10x in folder:
            ensureCountedPath(folder/file.txt) => folder/file010.txt
        - File does not exist yet
            ensureCountedPath(folder/file.txt, first=False) => folder/file.txt
            ensureCountedPath(folder/file.txt, first=True) => folder/file001.txt
    """
    def _constructPath(path, fmt, count):
        if path.exists() and count is None and skipFirst:
            count = minCount
        if count is None:
            count = None if skipFirst else minCount
        if count is None:
            return path
        else:
            return path.parent / (path.stem + fmt%count + path.suffix)

    # Check arguments.
    assert(isinstance(fmt, str))
    assert(isinstance(skipFirst, bool))
    assert(isinstance(step, int) and step > 0)
    assert(isinstance(minCount, int) and minCount >= 0)
    assert(isinstance(disable, bool))
    # Match patterns such as the following ones:
    #   "%d", "%10d", "-prefix-%03d-suffix", "%04d-suffix-%s"
    match = re.match(".*(%0?[0-9]*d).*", fmt)
    if not match:
        raise ValueError("Invalid format specifier: %s" % fmt)

    path = Path(path)
    parent = path.parent
    if ensureParent:
        if not ensureDir(parent):
            # raise?
            pass
    if disable:
        return path
    if not parent.exists():
        return _constructPath(path, fmt, count=None)

    # Extract the counts of existing items      # Example:
    # that match with the current one.          # fmt = "-pre-%03d"
    pattern = match.group(1)                    # pattern = "%03d"
    fmtRegex = fmt.replace(pattern,"([0-9]*)")  # fmtRegex = "-pre-([0-9]*)"

    stem = path.stem                            # stem = "file"
    suffix = path.suffix                        # suffix = ".txt"
    regex = re.compile("%s%s$" %                # regex = "file-pre-([0-9]*)"
                       (stem, fmtRegex))

    match = lambda x: regex.match(x.stem)
    matches = [match(i) for i in parent.iterdir() if i.suffix==suffix]
    #print("%s%s$" % (stem, fmtRegex), len(matches))
    matches = [m.group(1) for m in matches if m]
    counts = [int(m) for m in matches if m]
    newCount = max(counts)+step if counts else None
    ensuredPath = _constructPath(path, fmt, count=newCount)
    assert(not ensuredPath.exists())
    return ensuredPath


################################################################################
def removeFilesGlob(path, globExp, listOnly=False, logger=None):
    """
    Returns a dictionary, mapping the paths to the success state.
    See removeFileOrFolder() for the possible success states.
    """
    path = Path(path)
    paths = sorted(path.glob(globExp))
    if not listOnly:
        paths = removeFilesOrFolders(paths, logger=logger)
    else:
        paths = {path: True if path.exists() else "no-op" for path in paths}
    return paths


################################################################################
def removeFilesOrFolders(paths, logger=None):
    """
    Returns a dictionary, mapping the paths to the success state.
    """
    ret = {}
    for path in paths:
        ret[path] = removeFileOrFolder(path, logger=None)
    return ret


################################################################################
def removeFileOrFolder(path, logger=None):
    """
    Returns:
        True:       If file exists and is removed properly.
        "no-op":    If file does not exist.
        False:      If removal failed.
    """
    path = Path(path)
    if not path or not path.exists():
        return "no-op"
    path = Path(path)
    if path.is_dir():
        try:
            shutil.rmtree(path, ignore_errors=True)
        except:
            if logger:
                logger.exception("Failed to remove folder: %s", path)
    elif path.is_file():
        try:
            path.unlink()
        except:
            if logger:
                logger.exception("Failed to remove file: %s", path)
    # Return True if path was successfully removed.
    return not path.exists()


################################################################################
# COPYING
################################################################################
def copyMultipleFiles(srcs, dsts, force=False, move=False,
                      count=False, cache=None, showProgress=False):
    if not isinstance(dsts, (list, tuple)):
        srcs = [Path(src) for src in srcs]
        dsts = [Path(dsts)/src.name for src in srcs]
    rets = []
    if showProgress:
        progress = createProgressBar(size=len(srcs),
                                     enabled=showProgress,
                                     label="Copying...")
    for i, (src, dst) in enumerate(zip(srcs, dsts)):
        ret = copySingleFile(src=src, dst=dst, force=force,
                             move=move, count=count, cache=cache)
        rets.append(ret)
        progress.update(i+1)
    return rets


################################################################################
def copySingleFile(src, dst, force=False, move=False, count=False, cache=None):
    """
    Utility function to copy files or file trees.

    Cache is a set of (src,dst) pairs, it is updated for every successful
    copy task. The task is omitted if (src,dst) is found in the cache.

    Argument count permits to ensure counted filenames if dst already exists.
    See ensureCountedPath() for details. It does not make much sense to
    enable counting and caching at the same time. Set count="skipFirst" in
    order to skip counting the first filename.

    Returns False if the src was not copied to dst, and returns dst if
    the copy action was either performed or cached.

    Set move=True to move instead of copy a file.
    """
    # Use resolve() to get the absolute path!
    # https://stackoverflow.com/a/44569249/3388962
    # https://bugs.python.org/issue39090
    # Windows requires strict=False.
    src = Path(src).resolve(strict=False)
    dst = Path(dst).resolve(strict=False)
    if count:
        dst = ensureCountedPath(dst, ensureParent=False,
                                skipFirst=count=="skipFirst")
    assert(cache is None or isinstance(cache, set))
    if not src.exists():
        logging.error("File does not exist: %s", src)
        return False
    if not force and (cache and (src,dst) in cache):
        # The item has been copied already.
        return dst
    if not dst.parent.is_dir():
        dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not force:
        logging.warning("File already exists: %s", dst)
        return False
    if move:
        # Applies to both files and folders.
        shutil.move(src=str(src), dst=str(dst))
    elif src.is_dir():
        shutil.copytree(src=src, dst=dst)
    elif src.is_file():
        shutil.copy2(src=src, dst=dst)
    else:
        raise ValueError("Cannot process this input: %s" % src)
    if not dst.exists():
        logging.warning("Failed to write file to: %s", dst)
        return False
    if cache is not None:
        cache.add((src,dst))
    return dst


################################################################################
def copyFiles(src, dst,
              relative=True,
              globExp=None,
              force=False,
              move=False,
              listOnly=False,
              renameFun=None,
              counted=False,
              verbose=False,
              showProgress=False):
    """
    relative:       Flag to preserve folder structure, relative to src.
    globExp:        Globular expressions as list to select files or folders.
    force:          If True, enforce the copying if target already exists.
    move:           Move files or folders instead of copying them.
    listOnly:       Returns only the files and dirs that will be copied.
    renameFun:      A function object that receives dst and/or src of the file
                    to be copied and returns the modified dst. Use with care!
                    Currently, only the renaming of files is supported.
    counted:        Extend the destination file by a count suffix that is
                    incremented for every copy. See ensureCountedPath().
    verbose:        Verbose if True, only warn if False, and silent if None.
    showProgress:   Show progressbar.

    To avoid peculiar behavior, dst is not allowed to be a child of src.

    The function returns two dicts mapping the old and new file and folder
    destinations, respectively.

    The rename function must have one of the following signatures:
        def renameFun(dst):
            newDst = someFunction(dst)
            return newDst
        def renameFun(src, dst):
            newDst = someFunction(src, dst)
            return newDst

    Examples:
        # Copy <src> to <dst>
        copyFiles(<src>, <dst>)

        # Copy all files and folders (equivalent to first example)
        copyFiles(<src>, <dst>, globExp="**/*")

        # Copy all files (with a suffix)
        copyFiles(<src>, <dst>, globExp="**/*.*")

        # Copy all files and folders with depth 2
        copyFiles(<src>, <dst>, globExp="*/*")
    """
    def _verifyGlobExp(globExp):
        if globExp is None or isinstance(globExp, str):
            globExp = [globExp]
        return globExp

    def _verifyRenameFun(renameFun):
        if renameFun is None:
            return None
        from inspect import signature
        sig = signature(renameFun)
        if len(sig.parameters) not in [1,2]:
            message = ("The renameFun must have one of the following " +
                       "signatures:\n"
                       "    def renameFun(dst): ...; return newDst\n"
                       "    def renameFun(src, dst): ...; return newDst")
            raise ValueError(message)
        isUnaryFun = len(sig.parameters) == 1
        _renameFunUser = renameFun
        def _renameFunExtended(fileSrc, fileDst):
            if isUnaryFun:
                fileDstNew = Path(_renameFunUser(fileDst))
            else:
                fileDstNew = Path(_renameFunUser(fileSrc, fileDst))
            if not dst in fileDstNew.parents:
                # Raise an exception if newPath points outside the destination
                # file tree, hoping that this reduces the chance to inadvertenly
                # mess up the file system.
                message = ("The target path must be modified such that it " +
                           "remains within the dst file tree.\n" +
                           "Path (in):  '%s',\n" % fileDst +
                           "Path (out): '%s',\n" % fileDstNew +
                           "Path dst:   '%s'" % dst)
                raise ValueError(message)
            return fileDstNew
        return _renameFunExtended

    def _collectContent(src, dst, globExp):
        dirs = {}
        files = {}
        # True if dst is subdir of src.
        dstInSrc = src in dst.parents
        for g in globExp:
            # Only use the src dir if g is an empty string or None.
            paths = list(src.glob(g)) if g else [src]
            if not paths and verbose is not None:
                logging.warning("Could not find a match for glob: %s", g)
            for i,p in enumerate(paths):
                p = Path(p)
                if dstInSrc and (p==dst or dst in p.parents):
                    # Copy nothing from the destination folder.
                    continue
                if relative:
                    # Preserve folder structure.
                    dstpath = dst / p.relative_to(src)
                else:
                    # Copy flat.
                    dstpath = dst / p.name
                if p.is_dir():
                    dirs[p] = dstpath
                elif p.is_file():
                    files[p] = dstpath
        return files, dirs

    def _expandSubdirs(files, dirs):
        """
        Update the files dict with the content of the subdirs
        to give a complete account of files and dirs copied.
        """
        files = dict(files) # Shallow copy to avoid that the
        dirs = dict(dirs)   # changes are seen outside.
        # Again copy to not modify the container we're iterating.
        for src, dst in dict(dirs).items():
            srcFiles, srcDirs = listContent(src, relto=src)
            dstFiles = [ dst / d for d in srcFiles ]
            srcFiles = [ src / d for d in srcFiles ]
            dstDirs = [ dst / d for d in srcDirs ]
            srcDirs = [ src / d for d in srcDirs ]
            files.update(zip(srcFiles, dstFiles))
            dirs.update(zip(srcDirs, dstDirs))
        return files, dirs

    def _copyFiles(filesMap):
        """
        Copy files or entire folders/file trees.
        """
        progress = createProgressBar(size=len(filesMap),
                                     enabled=showProgress,
                                     label="Copying...")
        for i, (src, dst) in enumerate(filesMap):
            copySingleFile(src=src, dst=dst, move=move,
                           force=force, count=counted)
            progress.update(i+1)

    def _renameFiles(files, dirs, renameFun):
        if renameFun:
            renamed = map(lambda x: renameFun(*x), files.items())
            files = dict(zip(files.keys(), renamed))

            # Update the map of dirs (that result from copying single files).
            dirs = { k.parent:v.parent for k,v in files.items() }

        return files, dirs


    def _logCopyActions(src, dst, files, dirs):
        allData = sorted(chain(files.items(), dirs.items()))
        logging.info("Copy <src>: %s", src)
        logging.info("Copy <dst>: %s", dst)
        if not allData:
            logging.info("Nothing to copy!")
        for srcFile, dstFile in allData:
            fType = "dir" if srcFile.is_dir() else "file"
            logging.info("Copy %-5s '<src>/%s' to '<dst>/%s'", fType+":",
                         srcFile.relative_to(src), dstFile.relative_to(dst))

    ############################################################################

    assert(isinstance(globExp, (type(None), str, list, tuple)))
    src = Path(src).resolve(strict=False)
    dst = Path(dst).resolve(strict=False)
    renameFun = _verifyRenameFun(renameFun)
    globExp = _verifyGlobExp(globExp)

    # Copying a folder is faster than copying all files separately that it
    # contains. The renaming operates on the single files. Hence, fast 
    # copying (with folders) is supported only if no renaming function is set.
    fastCopy = not bool(renameFun)

    # Collect files/folders to copy.
    files, dirs = _collectContent(src, dst, globExp)

    # Expand data.
    dataFast = sorted(chain(files.items(), dirs.items()))
    files, dirs = _expandSubdirs(files, dirs) # Always return expanded data!
    files, dirs = _renameFiles(files, dirs, renameFun)

    if verbose:
        if listOnly:
            logging.info("Running copy in dry mode.")
        _logCopyActions(src, dst, files, dirs)

    if listOnly:
        return files, dirs
    # For fastCopy, use the data before subdir-expansion.
    # For slowCopy, files contains everything to copy.
    dataToCopy = dataFast if fastCopy else sorted(files.items())
    _copyFiles(dataToCopy)
    return files, dirs


################################################################################
# JSON & YAML
################################################################################
def readJSON(src, convertUnicode=True, strict=True):
    """
    convertUnicode is ignored for python 3.x.
    """
    if not os.path.isfile(src):
        raise FileNotFoundError("File does not exist: %s" % src)
        return None
    with open(src) as fid:
        # Preserve the ordering with an OrderedDict.
        data = json.load(fid, object_pairs_hook=OrderedDict, strict=strict)

    if (sys.version_info < (3, 0)):
        def byteify(input):
            # Source: https://stackoverflow.com/a/33571117/3388962
            # This is needed only for python2!
            if isinstance(input, dict):
                return {byteify(key): byteify(value)
                        for key, value in input.iteritems()}
            elif isinstance(input, list):
                return [byteify(element) for element in input]
            elif isinstance(input, str):
                return input.encode("utf-8")
            else:
                return input
        data = byteify(data) if convertUnicode else data
    return data


################################################################################
def writeJSON(dst, data, indent=4, logger=None):
    # Source: https://stackoverflow.com/a/47626762/3388962
    class Encoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, set):
                return list(obj)
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, slice):
                # Warning: A slice cannot be read from a .json file.
                # Nevertheless, convert it into a string.
                return str(obj)
            if isinstance(obj, StructContainer):
                return obj.asdict()
            return json.JSONEncoder.default(self, obj)

    if logger is None:
        logger = logging.getLogger(_loggerId)
    dirname = os.path.dirname(dst)
    if not ensureDir(dirname, logger=logger):
        return False
    try:
        with open(dst, "w") as fid:
            json.dump(data, fid, indent=indent, cls=Encoder)
    except:
        logger.error("Failed to dump data to JSON file: %s", dst)
        logger.exception("Exception message:")
        return False
    return True


################################################################################
def readYAML(src, logger=None):
    if logger is None:
        logger = logging.getLogger(_loggerId)
    src = Path(src).resolve(strict=False)
    if not src.is_file():
        raise FileNotFoundError("File does not exist: %s" % src)
        return None
    if not src.suffix.lower() in (".yaml", ".gyaml", ".json"):
        logger.warning("Reading unknown YAML file type: %s", src.name)
    with open(src, "r") as fid:
        data = yaml.safe_load(fid)
    return data


################################################################################
def writeYAML(dst, data, mode="block", indent=None, width=None,
              encode=True, logger=None):
    """
    Arguments:
        flow:       Switch between block and flow style (for nested structures)
                    Pure flow-style is hard to read, but memory efficient.
                    Block-style is best to read, but less memory efficient.
                    Mixed style is a trade-off.

                    Example: data = {a=dict(i=1,ii=2),b=None)
                        # Block style (mode="block")
                        a:
                          i: 1
                          ii: 2
                        b: null

                        # Mixed style (mode="flow"):
                        {a: {i: 1, ii: 2}, b: null}

                        # Mixed style (mode="mixed"):
                        a: {i: 1, ii: 2}
                        b: null
        indent:     Amount of indent. Default: 2
        width:      Affects the line-breaks for flow-style...
        encode:     PyYAML cannot write non-default data types. Standard
                    objects such as pathlib.Path, numpy.ndarray, need
                    to be transformed into a default data type.
    """
    def _encode(obj):
        if isinstance(obj, np.ndarray):
            dtype = obj.dtype
            obj = obj.tolist()
            return _encode(obj) if dtype=="object" else obj
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, StructContainer):
            obj = obj.asdict()
            return _encode(obj)
        if isinstance(obj, dict):
            return dict(zip(_encode(list(obj.keys())),
                            _encode(list(obj.values()))))
        if isinstance(obj, (list, tuple, set)):
            return type(obj)(map(_encode, obj))
        return obj
    if encode:
        data = copy.deepcopy(data)
        data = _encode(data)
    modeMap = dict(block=False, flow=True, mixed=None)
    assert(mode in modeMap)
    if logger is None:
        logger = logging.getLogger(_loggerId)
    dst = Path(dst).resolve(strict=False)
    if not ensureDir(dst.parent, logger=logger):
        return False
    try:
        with open(dst, "w") as fid:
            yaml.safe_dump(data, fid,
                           indent=indent,
                           width=width,
                           default_flow_style=modeMap[mode])
    except:
        logger.error("Failed to dump data to YAML file: %s", dst)
        logger.exception("Exception message:")
        return False
    return True


