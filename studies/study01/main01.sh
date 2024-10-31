#!/usr/bin/env bash

# Exit on Ctrl+C.
trap "exit" INT

# Exit on error.
set -e

OUTDIR="results/new"

################################################################################
function title(){
    MESSAGE=$1
    echo
    echo "############################################################"
    echo $MESSAGE
    echo "############################################################"
    echo
}

################################################################################
# STEP 1
################################################################################
STEPNAME="step01"
mkdir -p "$OUTDIR/$STEPNAME/"

title "STEP 1"
python "scripts/step01.py" \
        --outDir "$OUTDIR/$STEPNAME/" \
        2>&1 | tee "$OUTDIR/$STEPNAME/console.txt"


################################################################################
# STEP 2
################################################################################
STEPNAME="step02"
mkdir -p "$OUTDIR/$STEPNAME/"

title "STEP 2"
python "scripts/step02.py" \
        --outDir "$OUTDIR/$STEPNAME/" \
        2>&1 | tee "$OUTDIR/$STEPNAME/console.txt"
