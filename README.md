# Project structure for researchers



A researcher might be involved in multiple studies that involve an extensive amount of programming. A reasonable project structure is essential to keep the code organized and maintainable. This here is a template for a project structure that I have found useful in the past.



The structure consists of the following directories:

- **src**: Contains the source code for common functionality that is used in multiple projects. This directory should be added to the PYTHONPATH: 

  ```bash
  export PYTHONPATH=$PYTHONPATH:/path/to/src
  ```

* **studies**: Contains the source code for the individual studies. Each study should have its own directory. I recommend that the entry point for each study is a script called `main.sh` that is located in the study directory. Using Jupyter notebooks can also be an option, depending on the nature of the study.

* **unittests**: Contains the file `run.py` that runs all unit tests in the project. The files implementing the unit tests are marked with the suffix `_test.py` and can be found under src. To run the unit tests, `python run.py`



The structure also contains the following files:

- **README.md**: A file that describes the project and provides instructions on how to run the code.
- **requirements.txt**: A file that lists all dependencies of the project.

- **.gitignore**: A file with rules for files and folders that should not be tracked by git.



Some hints for writing maintainable code:

- It is recommended to strictly separate the code from other resources, like data and results.

- Work with [`pyenv`](https://github.com/pyenv/pyenv) and [`virtualenv`](https://github.com/pyenv/pyenv-virtualenv) to manage multiple Python versions and create isolated environments for each project.
- Always log context information like the current time, the name of the script, the git hash and additional information that might be useful for reproducing the results.





With this template in place, the automatic logging of context information is already implemented. The following snippet demonstrates the output of the log information. It also keeps track of uncommitted changes in the repository, and (optional) config files.



```None
Context information
===================
Author:    normanius
Date:      31.10.2024 02:55:17
Git:       8441acca (research-project.git)

----------------------------
This file is auto-generated!
----------------------------

System:
-------
       OS: Mac (macOS-14.7-arm64-arm-64bit)
     Arch: 64bit
    Cores: 10
     Node: clt-mob-n-2962
     User: juch
   Python: 3.10.5 (main, Jul 19 2022, 23:32:53) [Clang 13.1.6 (clang-1316.0.21.2.5)]

Console:
--------
scripts/step01.py --outDir results/new/step01/

Notes:
------
...
```





## Instructions



Install the requirements:

```bash
pip install -r requirements.txt
```

Make sure to expand the `PYTHONPATH` 

```bash
# To identify the correct path, you could use the following command
# echo "$(abspath '.')/src"...
export PYTHONPATH=$PYTHONPATH:/path/to/src
```

Then run the main script in study01 and the unit tests:

```bash
# Run study
./studies/study01/main01.sh

# Run unittests
python unittest/run.py
```

