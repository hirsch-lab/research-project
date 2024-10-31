import os
import sys
import getpass  # getuser()
import inspect
import logging
import datetime
import warnings
import platform  # system information
import multiprocessing # cpu_count()
from pathlib import Path

from utilities.fileio import ensureDir, ensureCountedPath

_loggerId = 'utils.ctxinfo'


################################################################################
def inferAppName(stackDepth=2):
    stackDepth = -1 if stackDepth is None else stackDepth
    caller = inspect.getframeinfo(inspect.stack()[stackDepth][0])
    appId = Path(caller.filename).stem
    return appId

################################################################################
# Template text (not in a separate file to avoid an additional dependency):
INFO_TEMPLATE = \
    "Context information\n" +                    \
    "===================\n" +                    \
    "Author:    <AUTHOR>\n" +                    \
    "Date:      <DATE>\n" +                      \
    "Git:       <GIT-HASH>\n\n" +                \
    "----------------------------\n" +           \
    "This file is auto-generated!\n" +           \
    "----------------------------\n\n" +         \
    "System:\n" +                                \
    "-------\n" +                                \
    "       OS: <OS>\n" +                        \
    "     Arch: <ARCH>\n" +                      \
    "    Cores: <CORES>\n" +                     \
    "     Node: <NODE>\n" +                      \
    "     User: <USER>\n" +                      \
    "   Python: <PYTHON>\n\n"                    \
    "Console:\n" +                               \
    "--------\n" +                               \
    "<COMMAND>\n\n" +                            \
    "Notes:\n" +                                 \
    "------\n" +                                 \
    "<NOTES>"

################################################################################
def getGitRepo(pathToRepo, logger=None):
    """
    Return a git.Repo object and the repository name.
    """
    if logger is None:
        logger = logging.getLogger(_loggerId)
    if not pathToRepo:
        pathToRepo = Path(__file__).parent.parent
    pathToRepo = Path(pathToRepo)
    if pathToRepo.is_file():
        pathToRepo = pathToRepo.parent
    if not pathToRepo.is_dir():
        #logger.warn("This is not a valid path: %s", pathToRepo)
        return None, None

    # Try to load git.Repo.
    try:
        from git import Repo
        from git.exc import InvalidGitRepositoryError
    except ImportError:
        logger.warn("Module git is not available.")
        return None, None

    # Only if the module is available...
    try:
        repo = Repo(pathToRepo)
        repoName = 'geomtk.git' # TODO adjust!
    except InvalidGitRepositoryError:
        #logger.warn("This is not a valid repository: %s", pathToRepo)
        repoName = "N/A"
        repo = None
    return repo, repoName


################################################################################
class ContextInfo:
    """
    Warning: It is not safe to use ContextInfo across multiple threads or processes!
    """

    # Default settings
    author = "normanius"
    time = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    overwrite = False
    subDir = '_context'  # where the dump goes

    def __init__(self, pathToRepo=None):
        # Some imports may take a while...
        self.logger = logging.getLogger(_loggerId)
        self.repo, self.repoName = getGitRepo(pathToRepo, self.logger)
        self.extraContext = {}    # extra dump

        self.info = INFO_TEMPLATE

        self.system = {}
        self.system['os'] = self.getOperatingSystem()
        self.system['arch'] = platform.architecture()[0]
        self.system['cores'] = multiprocessing.cpu_count()
        self.system['node'] = platform.node()
        self.system['user'] = getpass.getuser()
        self.system['python'] = sys.version.split("\n")[0]

    @staticmethod
    def getOperatingSystem(short=False):
        osType = platform.system()
        if platform.mac_ver()[0]:
            osType = 'Mac'
        elif platform.win32_ver()[0]:
            osType = 'Win'
        elif any(platform.linux_distribution()):
            osType = 'Linux'
        osName = platform.platform()
        return osType if short else '%s (%s)' % (osType, osName)

    def _fillInfoTag(self, tag, info, indent=None):
        info = str(info)
        if indent:
            indent = " "*indent
            info = info.replace("\n", "\n"+indent)
            info = indent + info
        self.info = self.info.replace(tag, info)

    def _fillTemplate(self, notes):
        self.info = INFO_TEMPLATE

        try:
            gitHash = self.repo.head.object.hexsha[0:8] if self.repo else "<N/A>"
            repoName = " (%s)" % self.repoName if self.repo else ""
            self._fillInfoTag("<AUTHOR>", self.author)
            self._fillInfoTag("<DATE>", self.time)
            self._fillInfoTag("<GIT-HASH>", gitHash + repoName)
            self._fillInfoTag("<COMMAND>", " ".join(sys.argv))
            self._fillInfoTag("<OS>", self.system['os'])
            self._fillInfoTag("<ARCH>", self.system['arch'])
            self._fillInfoTag("<CORES>", self.system['cores'])
            self._fillInfoTag("<NODE>", self.system['node'])
            self._fillInfoTag("<USER>", self.system['user'])
            self._fillInfoTag("<PYTHON>", self.system['python'])
            if notes is not None:
                self._fillInfoTag("<NOTES>", notes)
        except Exception as ex:
            self.logger.exception("Failed to fill template data.")

    def _ensureFilename(self, candidatePath):
        return ensureCountedPath(path=candidatePath, fmt="_%03d",
                                 disable=self.overwrite)

    def _dumpExtraContext(self, outDir):
        for filename, dumpFct in self.extraContext.items():
            filepath = self._ensureFilename(Path(outDir)/filename)
            try:
                dumpFct(filepath)
            except Exception as e:
                warnings.warn("Failed to dump item '%s'" % filename)
                warnings.warn("The error message: %s" % e)

    @staticmethod
    def _ensureAppId(appId=None):
        # Construct appId
        appId = appId if appId else inferAppName(stackDepth=None)
        appId = str(appId) if appId else ""
        appId = appId.lower()
        appId = appId.replace(" ", "_")
        return appId

    def addContext(self, filename, dumpFct):
        # Add additional material to dump. The mechanism is very generic,
        # but requires the caller to know how to dump the new item.
        #
        # Arguments:
        #   basename:   unique filename specifier.
        #   dumpFct:    a unary function receiving a filepath.
        if filename in self.extraContext:
            warnings.warn("Overriding existing context: %s", filename)
        self.extraContext[filename] = dumpFct

    def print(self):
        self._fillTemplate(notes=None, appId=None)
        print(self.info)

    @staticmethod
    def contextDir(outDir, appId=None):
        appId = ContextInfo._ensureAppId(appId)
        outDir = Path(outDir) / ContextInfo.subDir / appId
        return outDir

    def dump(self, outDir, notes=None, appId=None):
        outDir = self.contextDir(outDir=outDir, appId=appId)
        self._fillTemplate(notes=notes)
        if not ensureDir(outDir):
            msg = "Failed to create output directory: %s" % outDir
            self.logger.error(msg)
            return
        try:
            infoFile = self._ensureFilename(Path(outDir) / "info.txt")
            diffFile = self._ensureFilename(Path(outDir) / "local.diff")
            if self.repo:
                with open(diffFile,'wb') as fid:
                    t = self.repo.head.commit.tree
                    fid.write(self.repo.git.diff(t).encode('utf-8').strip())
            with open(infoFile, 'w') as fid:
                fid.write(self.info)
        except Exception as ex:
            self.logger.exception("Failed to dump context info.")
            return
        self._dumpExtraContext(outDir)
