import sys
import logging
import argparse
from pathlib import Path

from utilities.context_info import ContextInfo
from utilities.data_types import StructContainer
from utilities.logging import loggingConfig

################################################################################
def loadSettings(args):
    if args.outDir:
        outDir = Path(args.outDir)
    else:
        outDir = Path("..") / "results" / "new"

    # Some configs...
    configs = StructContainer()
    configs.outDir = outDir
    configs.verbose = args.verbose
    configs.method = args.method

    # Using struct container, it is possible to nest configs.
    configs.vis = StructContainer()
    configs.vis.enablePNG = False
    configs.vis.skipFirst = False
    configs.plots = StructContainer()
    configs.plots.bright = "#F9F9F9"
    configs.plots.dark = "#404040"

    return configs

################################################################################
def setupIO(configs):
    # A functor to dump the configs.
    from utilities.fileio import writeYAML
    dumpConfigs=lambda filename: writeYAML(filename, configs)
    info = ContextInfo()
    info.addContext("configs.yaml", dumpConfigs)
    info.dump(configs.outDir)

    logLevelMap = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG
    }
    logLevel = logLevelMap.get(configs.verbose, logging.WARNING)
    loggingConfig(outDir=configs.outDir, level=logLevel)

################################################################################
def setupMatplotlib():
    # This line is required if the plots should be editable with Adobe
    # Illustrator. The problem: https://stackoverflow.com/questions/5956182/
    import matplotlib as mpl
    mpl.rcParams["pdf.fonttype"] = 42
    #mpl.rcParams["font.sans-serif"] = ["Helvetica", "sans-serif"]

################################################################################
def run(args):
    configs = loadSettings(args)
    setupIO(configs)
    setupMatplotlib()

    # These messages go to log files.
    logging.info("This is an Info")
    logging.warning("This is a Warning")
    logging.error("This is an Error")

    # ... some real work here ...

################################################################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", type=str, default="methodA",
                        choices=["methodA","methodB"],
                        help="Choose your favorite method.")
    parser.add_argument("--outDir", type=str, default=None,
                        help="Output directory.")
    parser.add_argument("-v", "--verbose", action="count", 
                        help="Increase verbosity level.")
    args = parser.parse_args()
    run(args)
