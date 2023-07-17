#!/usr/bin/env bash

set -e

ENV_NAME=metacerberus

# initialize conda environment in bash script
eval "$(conda shell.bash hook)"

# create the metacerberus environment in conda
mamba create -n $ENV_NAME -y -c conda-forge -c bioconda python grpcio'=1.43' git fastqc flash2 fastp porechop bbmap prodigal hmmer ray-default ray-core ray-tune ray-dashboard gitpython pandas plotly scikit-learn dominate python-kaleido configargparse psutil metaomestats

conda activate $ENV_NAME

pip install .

metacerberus.py --setup
