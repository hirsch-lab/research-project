import os
import sys
import logging
import logging.config
from functools import partial

from utilities.context_info import inferAppName
from utilities.fileio import ensureCountedPath

"""
Logging related stuff.

As for logging with multiprocessing, the solution found here has been heavily
inspired by the Python 3.x Logging Cookbook:
    https://docs.python.org/3/howto/logging-cookbook.html
An interesting alternative (MultiProcessingLog handler) was described here:
    https://stackoverflow.com/a/894284/3388962
    https://gist.github.com/JesseBuesking/10674086
However, from the comments I inferred that it won't run on Windows.

Other resources related to logging:
    http://python-guide-pt-br.readthedocs.io/en/latest/writing/logging/
    https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/
    https://docs.python.org/3/library/logging.handlers.html
    https://docs.python.org/2/howto/logging.html
    https://logutils.readthedocs.io/en/latest/
"""

# When importing logging_config, the root logger is initialized.
# By having the basic logger configs in one location, we can ensure that
# there is no "config-race" between the different modules that request the
# initialization of a root logger. This "config-race" is not a big deal unless
# the configs are not identical. If there is just one basicConfig, it is easier
# to modify the global logging settings.
# Reading:
#   https://stackoverflow.com/questions/12158048
#   https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/
#
################################################################################
#
# There are two logging channels:
#   (1) logging within the main process
#   (2) logging within the child processes
# Logging performed in channel (1) is configured in loggingConfig(). Logs from
# channel (2) are sent by means of inter-process communication to the main
# process and are handled there. LogListener is responsible to receive the logs
# in the main process. They are handled by a separate logger named "listener".
# Currently, the name of sending logger is ignored.
# For easier debugging, the messages from child processes are logged in a file
# with high verbosity, whereas on the console only
# warnings and errors are shown.
#
# TODO: - Use specific logger objects on module or library level.
#       - Configure logging per library level (vtkutils, utils, ...).
#         How: In the preample of a .py file call logger = getModuleLogger(),
#         where getModuleLogger() infers the logger name from the directory
#         of the sources file. Also, a concept has to exist how to specify the
#         the loggers per module/library.
#       - Use ini files for logging configuration. For now, we don't use them
#         for easier bundling (.conf files need to be bundled too...)
################################################################################

_DEFAULT_FILE_MODE = "w"
#_DEFAULT_FMT = "%(asctime)s.%(msecs)03d - %(levelname)-5s - [%(name)-8s]: %(message)s"
_DEFAULT_FMT = "%(asctime)s.%(msecs)03d - %(levelname)-5s: %(message)s"
#_DEFAULT_FMT = "%(asctime)s.%(msecs)03d - %(levelname)-5s - [%(processName)s] - [%(name)s]: %(message)s"
#_DEFAULT_DATEFMT = "%Y-%m-%d, %H:%M:%S"
_DEFAULT_DATEFMT = "%H:%M:%S"
_DEFAULT_VERBOSITY = "N/A"
_DEFAULT_LOG_LEVEL = logging.INFO
_DEFAULT_LOG_LEVEL_FILE = logging.DEBUG
_DEFAULT_FMT_SUBP = "%(asctime)s.%(msecs)03d - %(levelname)-5s - {%(processName)s} - [%(name)-8s]: %(message)s"
_DEFAULT_DATEFMT_SUBP = "%H:%M:%S"
_DEFAULT_LOG_LEVEL_SUBP = logging.DEBUG
_DEFAULT_LOG_LEVEL_SUBP_FILE = logging.DEBUG
_DEFAULT_LOG_LEVEL_SUBP_CONSOLE = logging.WARN
_DEFAULT_FORMATTER = logging.Formatter(fmt=_DEFAULT_FMT,
                                       datefmt=_DEFAULT_DATEFMT)
_DEFAULT_FORMATTER_SUBP = logging.Formatter(fmt=_DEFAULT_FMT_SUBP,
                                            datefmt=_DEFAULT_DATEFMT_SUBP)

# This is a global state...
_CURRENT_LOG_DIR = None
_CURRENT_APP_ID = None

################################################################################
class Logger:
    def __init__(self, loggerId=None):
        self._logger = logging.getLogger(loggerId)
        self._stash = []

    @property
    def logger(self):
        return self._logger

    def _log(self, level, message, stack=False, stackDepth=4):
        self._logger.log(level, message)

        if stack:
            import inspect
            stack = inspect.stack()
            nstack = min(len(stack), stackDepth)
            stack = stack[1:nstack]
            for i, call in enumerate(stack):
                funcName = call[3]+"()"
                lineno = call[2]
                modulePath = call[1]
                moduleFile = os.path.basename(modulePath)
                fmt = ("Stack: %d) %s:%d: %s" if i==0 else
                       "       %d) %s:%d: %s")
                msg = fmt % (i, moduleFile, lineno, funcName)
                self._logger.log(level, msg)

    def log(self, level, message, stack=False, stackDepth=4):
        self._log(level=level, message=message,
                  stack=stack, stackDepth=stackDepth)
    def debug(self, message, stack=False, stackDepth=4):
        self._log(level=logging.DEBUG, message=message, 
                  stack=stack, stackDepth=stackDepth)
    def info(self, message, stack=False, stackDepth=4):
        self._log(level=logging.INFO, message=message,
                  stack=stack, stackDepth=stackDepth)
    def warn(self, message, stack=False, stackDepth=4):
        self._log(level=logging.WARN, message=message,
                  stack=stack, stackDepth=stackDepth)
    def error(self, message, stack=False, stackDepth=4):
        self._log(level=logging.ERROR, message=message,
                  stack=stack, stackDepth=stackDepth)
    def exception(self, message, stack=False, stackDepth=4):
        self._log(level=logging.ERROR, message=message,
                  stack=stack, stackDepth=stackDepth)
        logging.exception("Exception message:")

    def enter(self, level=logging.DEBUG):
        self._log(level=level, message="Entering: %s()" % _callerName())

    def leave(self, level=logging.DEBUG):
        self._log(level=level, message="Leaving: %s()" % _callerName())

    def stashLevel(self, newLevel=logging.INFO):
        """
        Temporarily set the log-level for all handlers to a new level.
        """
        logger = logging.getLogger() # root logger => apply to all!
        levels = {}
        levels["logger"] = logger.level
        levels["handlers"] = []
        for h in logger.handlers:
            levels["handlers"].append(h.level)
            h.setLevel(newLevel)
        logger.setLevel(newLevel)
        self._stash.append(levels)

    def popLevel(self):
        if self._stash:
            logger = logging.getLogger() # root logger
            levels = self._stash.pop()
            logger.setLevel(levels["logger"])
            # Assumption: Number of handlers is the
            # same since last call to stashLevel().
            levels = levels["handlers"]
            assert(len(levels)==len(logger.handlers))
            for handler, level in zip(logger.handlers, levels):
                handler.setLevel(level)

################################################################################
def _resolveLevel(level, default):
    if level is None:
        return level
    if level < 0:
        return default
    return level

################################################################################
# MULTI-PROCESSING.
################################################################################
import threading as thr
import multiprocessing as mp
try:
    # Python3
    from queue import Empty as EmptyException
except ImportError:
    # Python2
    from Queue import Empty as EmptyException

# This class certainly can be replaced by QueueListener
class LogListener():
    """
    Use LogListener to collect logs from other processes.
    """
    loggerId = "ICPLogListener"
    def __init__(self,
                 appId=None,
                 outDir=None,
                 level=None,
                 levelFile=None):
        # Better use a managed Queue object instead of a naked mp.Queue.
        # It's worthwhile reading some documentation about multiprocessing:
        # https://docs.python.org/2/library/multiprocessing.html#multiprocessing-managers
        self._manager = mp.Manager()
        self._queue = self._manager.Queue(maxsize=-1)
        self._stopEvent = thr.Event()
        self._thread = None
        # Infer the appId automagically
        appId = appId if appId else inferAppName()
        # Initialize logger and handlers.
        self._initLogger(appId, outDir, level, levelFile)

    @staticmethod
    def _initLogger(appId, outDir, level, levelFile):
        # Create a logger for the listener.
        logger = logging.getLogger(LogListener.loggerId)
        logger.setLevel(logging.DEBUG)   # Handle ALL logs received by ICP logger.
        logger.propagate = False         # Don't forward messages to parent (root).
        # Set up logging to console.
        fmt = _DEFAULT_FORMATTER
        logLevel = _resolveLevel(level, _DEFAULT_LOG_LEVEL_SUBP_CONSOLE)
        _addConsoleHandler(logger=logger, level=logLevel, fmt=fmt)
        # Set up logging to file.
        fmt = _DEFAULT_FORMATTER_SUBP
        logLevel = _resolveLevel(levelFile, _DEFAULT_LOG_LEVEL_SUBP_FILE)
        _addFileHandler(logger=logger, level=logLevel, fmt=fmt,
                        outDir=outDir, subDir=appId,
                        filename="subprocess.log", override=False)

    def logQueue(self):
        return self._queue

    @staticmethod
    def listen(queue, stopEvent):
        while not stopEvent.is_set():
            try:
                record = queue.get(timeout=0.05)
                # We would create a new logger named "root" if we call:
                #     logging.getLogger(name)
                # However, in order to get the actual root logger call:
                #     logging.getLogger(None)
                # NOTE: We redirect all messages from the subprocesses to the
                # listener logger. For now, we don't care about the logger name.
                # TODO: Take care of the different logger names...
                #name = LogListener.loggerId if record.name == "root" else record.name
                logger = logging.getLogger(LogListener.loggerId)
                logger.handle(record)
            except EmptyException:
                # Thrown if queue remained empty within the timeout period.
                pass
            except (EOFError, BrokenPipeError):
                # Hide errors present on Keyboard-interrupt.
                # Still log a warning that might be helpful when debugging
                # other failure modes.
                msg = "Log listening is interrupted."
                logger = logging.getLogger(LogListener.loggerId)
                logger.warning(msg)
                break

    def start(self):
        self._thread = thr.Thread(target=LogListener.listen,
                                  args=(self._queue, self._stopEvent,))
        self._thread.start()

    def stop(self):
        self._stopEvent.set()
        self._thread.join()

################################################################################
# INSPECTION.
################################################################################
def _callerName(skip=2):
    import inspect
    """
    Get a name of a caller in the format module.class.method

    skip specifies how many levels of stack to skip while getting caller
    name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.
    An empty string is returned if skipped levels exceed stack height

    Source: https://stackoverflow.com/a/9812105/3388962 (anatoly techtonik)

    Note: inspect is not perfectly portable!
    """
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
        return ""
    parentframe = stack[start][0]

    name = []
    module = inspect.getmodule(parentframe)
    # `modname` can be None when frame is executed directly in console
    # TODO(techtonik): consider using __main__
    if module:
        name.append(module.__name__)
    # detect classname
    if "self" in parentframe.f_locals:
        # I don't know any way to detect call from the object method
        # XXX: there seems to be no way to detect static method call - it will
        #      be just a function call
        name.append(parentframe.f_locals["self"].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != "<module>":  # top level usually
        name.append( codename ) # function or a method

    ## Avoid circular refs and frame leaks
    #  https://docs.python.org/2.7/library/inspect.html#the-interpreter-stack
    del parentframe, stack

    # NJU: just add the last two parts of the name.
    # This works also if len(nam) < 2.
    name = name[-2:]

    return ".".join(name)

################################################################################
# CONFIGURATION.
################################################################################
def _constructLoggingDir(outDir, subDir):
    if not outDir:
        return None
    subDir = str(subDir) if subDir else ""
    subDir = subDir.lower()
    subDir = subDir.replace(" ", "_")
    logDir = os.path.join(outDir, "_logs", subDir)
    return logDir

def _addHandler(logger, handler, level, fmt):
    if level is None:
        return
    handler.setLevel(level)
    handler.setFormatter(fmt)
    logger.addHandler(handler)

def _addFileHandler(logger, level, fmt, outDir, subDir, filename, override):
    # If outDir is None, logging to file will be disabled.
    if outDir is None or filename is None:
        return
    logDir = _constructLoggingDir(outDir=outDir, subDir=subDir)
    filepath = os.path.join(logDir, filename)
    outPath = ensureCountedPath(os.path.join(logDir, filename), disable=override)
    handler = logging.FileHandler(outPath, mode=_DEFAULT_FILE_MODE)
    _addHandler(logger, handler, level, fmt)

def _addConsoleHandler(logger, level, fmt):
    handler = logging.StreamHandler()
    _addHandler(logger, handler, level, fmt)

def _setLevelStrings():
    logging.TRACE = logging.DEBUG - 1
    logging.DRYRUN = 1000    # Custom log level.
    logging.STATUS = 1001    # Custom log level.
    logging.addLevelName(logging.TRACE,   "TRACE")
    logging.addLevelName(logging.DEBUG,   "DEBUG")
    logging.addLevelName(logging.INFO,    "INFO")
    logging.addLevelName(logging.WARNING, "WARN")
    logging.addLevelName(logging.ERROR,   "ERROR")
    logging.addLevelName(logging.CRITICAL,"CRIT")
    logging.addLevelName(logging.DRYRUN,  "DRY")
    logging.addLevelName(logging.STATUS,  "STATUS")

    logging.trace = partial(logging.log, logging.TRACE)
    logging.dryrun = partial(logging.log, logging.DRYRUN)
    logging.status = partial(logging.log, logging.STATUS)

def getLoggingDir():
    """
    Return the logging dir for the same parameters that are passed to
    loggingConfig.
    """
    if not _CURRENT_LOG_DIR:
        raise RuntimeError("Call loggingConfig() prior to calling this function.")
    return _CURRENT_LOG_DIR

def getCurrentAppId():
    if not _CURRENT_APP_ID:
        raise RuntimeError("Call loggingConfig() prior to calling this function.")
    return _CURRENT_APP_ID

def ensureLogLevels():
    _setLevelStrings()

def loggingConfig(appId=None,
                  logger=None,
                  level=_DEFAULT_LOG_LEVEL,          # log level console handler
                  levelFile=_DEFAULT_LOG_LEVEL_FILE, # log level file handler
                  outDir=None,
                  verbosity=_DEFAULT_VERBOSITY,
                  override=False):                   # Disable counted log files
    # This introduces new log levels:
    #   - TRACE
    #   - DRYRUN
    #   - STATUS
    ensureLogLevels()

    # If verbosity is set: override the log level of the console handler.
    if (verbosity == _DEFAULT_VERBOSITY or
        verbosity is None):
       # If verbosity is not set, do nothing.
        pass
    elif verbosity >= 3:
        level = logging.TRACE
    elif verbosity == 2:
        level = logging.DEBUG
    elif verbosity == 1:
        level = logging.INFO
    elif verbosity == 0:
        level = logging.WARN
    else:
        pass

    level = _resolveLevel(level, _DEFAULT_LOG_LEVEL)
    levelFile = _resolveLevel(levelFile, _DEFAULT_LOG_LEVEL_FILE)

    # Use root logger if logger has not been specified.
    logger = logger if logger else logging.getLogger()

    # Infer the appId automagically
    appId = appId if appId else inferAppName()

    # This sets the current log dir as (global) state of the logging system.
    logDir = _constructLoggingDir(outDir=outDir, subDir=appId)
    global _CURRENT_LOG_DIR, _CURRENT_APP_ID
    _CURRENT_LOG_DIR = logDir
    _CURRENT_APP_ID = appId

    nStreamers = [isinstance(h,logging.StreamHandler) for h in logger.handlers].count(True)
    if nStreamers >= 1:
        #TODO: revise this... This seems smelly...

        # Test if there is already a stream handler installed. This can happen if
        #     (A) loggingConfig() already has been called
        #     (B) logging.basicConfig() has been called
        #     (C) any logging has taken place (which leads also to (B))
        #logger.warn("The logging system already has been configured. " +
        #            "Is loggingConfig() or logging.basicConfig() called multiple times?")

        # Reset all StreamHandlers.
        # I assume here that loggingConfig() is called before other modules try
        # to expand the logging system with their own handlers.
        logger.handlers = [ h for h in logger.handlers if not isinstance(h, logging.StreamHandler)]

    # Add a console logger for all the messages.
    fmt = _DEFAULT_FORMATTER
    fmtSubp = _DEFAULT_FORMATTER_SUBP
    if level is not None:
        _addConsoleHandler(logger=logger, level=level, fmt=fmt)
    if levelFile is not None:
        # If not disabled, use patterned log-file: main-%03d.log
        _addFileHandler(logger=logger, level=levelFile, fmt=fmt,
                        outDir=outDir, subDir=appId, filename="main.log",
                        override=override)

    getLevel = lambda func, *args: func(a for a in args if a is not None)
    if level is not None or levelFile is not None:
        logger.setLevel(getLevel(min, level, levelFile))

    logging.getLogger("git").setLevel(logging.WARN) # Used in ContextInfo.
    logging.getLogger("matplotlib").setLevel(logging.INFO) # Is very verbose...

