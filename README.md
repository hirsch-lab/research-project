# Project structure for PhD students





During a PhD, a student might be involved in multiple projects that involve an extensive amount of programming. A reasonable project structure is essential to keep the code organized and maintainable. This here is a template for a project structure that I have found useful in the past.



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