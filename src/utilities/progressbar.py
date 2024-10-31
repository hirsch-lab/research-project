import progressbar as pg

###############################################################################
def createProgressBar(size=None,
                      label="Processing...",
                      enabled=True,
                      width=100,
                      **kwargs):
    """
    Create a progress bar with a given label and size.

    To create a progress bar with a prefix that varies:
        prefix = "Converting {variables.file_name:<3}..."
        variables={"file_name": "N/A"}
        progress = create_progress_bar(label=None,
                                       ..., 
                                       prefix=prefix, 
                                       variables=variables)
        progress.update(0, file_name="file1")
    """
    widgets = []
    if label:
        widgets.append(pg.FormatLabel("%-5s:" % label))
        widgets.append(" ")
    if size is not None and size>0:
        digits = 3
        fmt_counter = f"%(value){digits}d/{size:{digits}d}"
        widgets.append(pg.Bar())
        widgets.append(" ")
        widgets.append(pg.Counter(fmt_counter))
        widgets.append(" (")
        widgets.append(pg.Percentage())
        widgets.append(")")
    else:
        widgets.append(pg.BouncingBar())
    ProgressBarType: pg.ProgressBar = pg.ProgressBar if enabled else pg.NullBar
    progress = ProgressBarType(max_value=size,
                               widgets=widgets,
                               redirect_stdout=True,
                               poll_interval=0.02,
                               term_width=width,
                               **kwargs)
    return progress

