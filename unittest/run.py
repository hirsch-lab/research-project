import logging
import argparse
import unittest

from utilities.logging import loggingConfig

def parseArguments():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-p", "--pattern", default="*_test.py", type=str,
                        help="Pattern to select tests. Default: *_test.py")
    parser.add_argument("-x", "--xml", action="store_true",
                        help="Write testing output in xUnit-style.")
    parser.add_argument("-o", "--outDir", default="./test-reports",
                        help="Path to output directory. Default: ./test-reports")
    parser.add_argument("--logDir", default="./test-logs",
                        help="Path to logging directory. Default: ./test-logs")
    parser.add_argument("-h", "--help", action="help",
                        help="Show this help text.")
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parseArguments()
    loggingConfig(level=None,
                  levelFile=logging.DEBUG,
                  outDir=args.logDir)
    loader = unittest.TestLoader()
    print(args.pattern)
    tests = loader.discover(pattern=args.pattern,
                            start_dir="../src/utilities")
    if args.xml:
        # Output must be placed in a folder "test-reports".
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output=args.outDir)
    else:
        runner = unittest.runner.TextTestRunner()
    runner.run(tests)
