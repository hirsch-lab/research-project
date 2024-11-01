import sys
import logging
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from utilities.context_info import ContextInfo
from utilities.data_types import StructContainer
from utilities.logging import loggingConfig
from utilities.plotting import saveFigure
from utilities.fileio import readYAML, writeYAML


################################################################################
def loadConfigs(args):
    configs_all = readYAML(args.configsFile)
    configs = configs_all["step01"]
    configs = StructContainer(configs)
    
    # Use the command line arguments to override the matching configs.
    configs.outDir = args.outDir if args.outDir else configs.outDir
    configs.outDir = Path(configs.outDir)
    if not args.save:
        # Disables saving figures.
        configs.save_kwargs = {}
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
    logging.info("This is another Info")
    logging.warning("This is another Warning")
    logging.error("This is another Error")

    # ... some real work here ...

    fig, ax = plt.subplots()
    x = np.random.default_rng().uniform(low=0, high=5, size=20)
    x = np.sort(x)
    y = x**2
    plt.plot(x, y, "o-")
    
    if configs.save_kwargs:
        fileName = ("plot" + ".", configs.save_kwargs.format)
        filePath = Path(configs.outDir) / fileName
        saveFigure(fig=fig, path=filePath, **configs.save_kwargs)


################################################################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true",
                        help="Enable saving figures.")
    parser.add_argument("--outDir", type=str, default=None,
                        help="Output directory.")
    parser.add_argument("--configsFile", type=str, default=None,
                        help="Path to the configs file.")
    parser.add_argument("-v", "--verbose", action="count", 
                        help="Increase verbosity level.")
    args = parser.parse_args()
    run(args)
