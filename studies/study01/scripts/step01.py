import sys
import logging
import argparse
from pathlib import Path

from utilities.context_info import ContextInfo
from utilities.data_types import StructContainer
from utilities.logging import loggingConfig
from utilities.fileio import readYAML, writeYAML

################################################################################
def loadConfigs(args):
    configs_all = readYAML(args.configsFile)
    configs = configs_all["step01"]
    configs = StructContainer(configs)
    
    # Use the command line arguments to override the matching configs.
    configs.outDir = args.outDir if args.outDir else configs.outDir
    configs.outDir = Path(configs.outDir)
    configs.method = args.method if args.method else configs.method
    return configs


################################################################################
def setupIO(configs):
    # Collect and save some context info.
    info = ContextInfo()
    # Also dump the configs.
    dumpConfigs=lambda filename: writeYAML(filename, configs)
    info.addContext("configs.yaml", dumpConfigs)
    info.dump(configs.outDir)

    # Set up logging.
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
    configs = loadConfigs(args)
    setupIO(configs)
    setupMatplotlib()

    # These messages go to log files.
    logging.info("This is an Info")
    logging.warning("This is a Warning")
    logging.error("This is an Error")
    
    logging.debug("Executing '%s'", configs.method)

    # ... some real work here ...

################################################################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", type=str, default=None,
                        choices=["methodA","methodB"],
                        help="Choose your favorite method.")
    parser.add_argument("--outDir", type=str, default=None,
                        help="Output directory.")
    parser.add_argument("--configsFile", type=str, default=None,
                        help="Path to the configs file.")
    parser.add_argument("-v", "--verbose", action="count", 
                        help="Increase verbosity level.")
    args = parser.parse_args()
    run(args)
