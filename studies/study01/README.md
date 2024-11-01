# Study 1: Title of the study



## Context

Here follow some information about the context of the study, the research questions being addressed by the study, the data that was collected, and implementation details of the analysis. I recommend to strictly separate the data from the analysis, and to use configuration files or command line arguments to parameterize the analysis. This will make it easier to rerun the analysis with different data.



## Instructions

To re-create all the results of this study, run

```bash
./main01.sh
```



If you want to easily switch between multiple datasets or different sets of input parameters, you may want to work with multiple scripts or use command line arguments.



```bash
# If working with different datasets...
./main01_datasetA.sh
./main01_datasetB.sh

# or, even better, with multiple config files...
./main01.sh path/to/configA.yaml
./main01.sh path/to/configB.yaml
```



## Comments

- Briefly describe here your experiences and insights.
- Make sure to properly label and archive the results that you want to use for publication.
