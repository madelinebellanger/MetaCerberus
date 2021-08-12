# -*- coding: utf-8 -*-

"""cerberusQCcontigs.py: Module for checking quality of .fastq files
Uses checkm [https://www.bioinformatics.babraham.ac.uk/projects/fastqc/]
Uses countfasta.py

$ countfasta.py -f FASTA -i INTERVAL > assembly-stats.txt
"""

#TODO Only run this when using contigs, not RAW Reads, or filtered reads

import os
import subprocess


## checkContigs
def getReadStats(contig, config, subdir):
    path = f"{config['DIR_OUT']}/{subdir}"
    os.makedirs(path, exist_ok=True)
    
    # countAssembly.py
    try:
        command = [ config['EXE_COUNT_ASSEMBLY'], '-f', contig, '-i 100' ]
        with open(f"{path}/stderr.txt", 'a') as ferr:
            proc = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=ferr)
            stats = proc.stdout.decode('utf-8', 'ignore')
    except:
        print("Error: countAssembly.py failed: " + subdir)
        print(command)

    return stats
