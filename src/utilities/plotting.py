import os
import matplotlib.pyplot as plt
from pathlib import Path
from utilities.data_types import static_vars
from utilities.fileio import ensureDir


def saveFigure(fig=None, path="figure.pdf", **kwargs):
    if fig is None:
        fig = plt.gcf()
    kwargs.setdefault("transparent", True)
    kwargs.setdefault("bbox_inches", "tight")
    kwargs.setdefault("dpi", 300)
    path = Path(path)
    ensureDir(path.parent)
    plt.savefig(path, **kwargs)





