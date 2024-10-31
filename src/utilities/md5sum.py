import os
import sys
import hashlib
import fnmatch
import logging
import argparse
import pandas as pd
from pathlib import Path as p

from utilities.logging import loggingConfig
from utilities.fileio import ensureDir

def _printSum(md5sum, filePath, verbose):
    if verbose=="filemode":
        print(md5sum)
    elif verbose:
        print("%s : %s" % (md5sum, filePath))

################################################################################
def _calcChecksumForFile(filePath, verbose=False):
    md5 = hashlib.md5()
    with open(filePath, "rb") as fid:
        buffer = fid.read(2 ** 20)
        while buffer:
            md5.update(buffer)
            buffer = fid.read(2 ** 20)
    md5sum = md5.hexdigest()
    _printSum(md5sum, filePath, verbose)
    return md5sum

################################################################################
def _calcChecksumForDir(folderPath,
                        pattern="*",
                        recursive=False,
                        verbose=False,
                        silent=False):
    data = []
    if recursive:
        files = folderPath.rglob(pattern)
        logging.info("Recursive search for pattern '%s'.", pattern)
    else:
        files = folderPath.glob(pattern)
        logging.info("Search for pattern '%s'.", pattern)

    for filePath in files:
        if filePath.is_dir():
            continue
        if filePath.suffix == ".md5":
            # Ignore files that end with md5.
            continue
        try:
            md5sum = _calcChecksumForFile(filePath, verbose=verbose)
        except:
            if silent:
                logging.warning("Failed to compute md5sum for: %s", filePath)
            else:
                raise
        _printSum(md5sum, filePath, verbose)
        data.append((filePath.name, filePath.relative_to(folderPath), md5sum))

    data = pd.DataFrame(data, columns=["filename", "filepath", "md5sum"])
    # Files are sorted in a meaningless order.
    data = data.sort_values("filepath")

    if data.empty:
        logging.warn("No matches for: %s", folderPath)
        return None

    return data

################################################################################
def _queryMode(path):
    path = p(path).resolve()
    if path.is_file():
        return "file"
    elif path.is_dir():
        return "folder"
    else:
        None

################################################################################
def computeChecksum(path,
                    pattern="*",
                    recursive=False,
                    verbose=False,
                    silent=False,
                    mode=None):
    path = p(path).resolve()
    mode = _queryMode(path) if mode is None else mode

    if mode == "file":
        # verbose==True  => True
        # verbose==False => "filemode"
        verbose = verbose or "filemode"
        ret = _calcChecksumForFile(filePath=path, verbose=verbose)
    elif mode == "folder":
        ret = _calcChecksumForDir(folderPath=path,
                                  pattern=pattern,
                                  recursive=recursive,
                                  verbose=verbose,
                                  silent=silent)
    else:
        logging.error("Path does not exist: %s", path)
        ret = None
    return ret

################################################################################
def main(args):
    verbosity = args.verbosity if args.verbosity is not None else 0
    loggingConfig(verbosity=verbosity+1)

    outFile = None
    mode = _queryMode(args.path)
    if mode == "folder" and args.outFile:
        outFile = p(args.outFile)
        if outFile.is_file() and not args.force:
            logging.error("Out file already exists: %s", args.outFile)
            return
    data = computeChecksum(path=args.path,
                           pattern=args.pattern,
                           recursive=args.recursive,
                           verbose=verbosity>1,
                           silent=False,
                           mode=mode)

    if (outFile and
        isinstance(data, (pd.DataFrame, pd.Series)) and
        ensureDir(outFile.parent)):
            logging.info("Writing md5 sums to file: %s", outFile)
            data.to_csv(outFile, index=False)

################################################################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to file or folder.")
    parser.add_argument("-p", "--pattern", default="*", type=str,
                        help="Glob pattern.")
    parser.add_argument("-o", "--outFile", default="md5sums.csv", type=str,
                        help="Output file for folder mode.")
    parser.add_argument("-f", "--force", action="store_true",
                        help="Force writing of output file.")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="Search forlders recursively.")
    parser.add_argument("-v", "--verbosity", action="count",
                        help="Enable verbose output.")
    parser.set_defaults(func=main)
    args = parser.parse_args()
    args.func(args)
    sys.exit(0)
