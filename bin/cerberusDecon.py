# -*- coding: utf-8 -*-
"""rheaDecon.py: Module to clean trimmed .fastq files
Uses bbduk [https://sourceforge.net/projects/bbmap/]

$ bbduk.sh -Xmx1g in=trim.fastq out=decon.fastq qtrim=rtrimq=25 maq=25 minlen=50 outm=matched.fq ref=~/bbmap/resources/phix174_ill.ref.fa.gz k=31 stats=out.txt
$ bbduk.sh -Xmx1g in1=trim_R1.fastq in2=trim_R2.fastq out1=decon_R1.fastq out2=decon_R2.fastq qtrim=r trimq=25 maq=25 minlen=50 outm=matched.fq ref=~/bbma/resource/phix174_ill.ref.fa.gz k=31 stats=out.txt
"""

import os
import subprocess


# deconReads
def deconReads(rawRead, config, subdir):
    if type(rawRead[1]) is str:
        return deconSingleReads(rawRead, config, subdir)
    elif type(rawRead[1]) is tuple:
        return deconPairedReads(rawRead, config, subdir)


## deconSingleReads
#
def deconSingleReads(fileFQ, config, subdir):
    # TODO: Find good long read mapper
    path = f"{config['DIR_OUT']}/{subdir}"
    os.makedirs(path, exist_ok=True)
    fout = open(f"{path}/stdout.txt", 'w')
    ferr = open(f"{path}/stderr.txt", 'w')
    key = fileFQ[0]
    value = fileFQ[1]
    outFile = f""
    deconReads = f'{path}/decon-{key}.fastq'
    matched = f"matched-{key}"
    #command = f"{config['EXE_BBDUK']} -Xmx1g in={value} out={path}/{outFile} qin=33 qtrim=r trimq=25 maq=25 minlen=50 outm={path}/{matched} ref={config['REFSEQ']} k=31 stats={path}/{outFile}.txt"
    #command = f"{config['EXE_BBDUK']} -Xmx1g in={value} out={path}/{outFile} qin=33 qtrim=r minlen=50 outm={path}/{matched} ref={config['REFSEQ']} k=31 stats={path}/{outFile}.txt"
    #TODO: Add reference file
    command = f"{config['EXE_BBDUK']} -Xmx1g in={value} out={deconReads} qin=33 qtrim=r minlen=50 outm={path}/{matched} k=31 stats={path}/{outFile}.txt"
    try:
        subprocess.run(command, shell=True, check=True, stdout=fout, stderr=ferr)
    except:
        print("Failed to execute bbduk Single End")
    fout.close()
    ferr.close()
    return deconReads


## deconPairedReads
#
def deconPairedReads(fileFQ, config, subdir):
    path = f"{config['DIR_OUT']}/{subdir}"
    os.makedirs(path, exist_ok=True)
    fout = open(f"{path}/stdout.txt", 'w')
    ferr = open(f"{path}/stderr.txt", 'w')
    deconReads = None
    #TODO: Check extension of file to match original (fastq vs fastq.gz)
    key = fileFQ[0]
    value = fileFQ[1]
    outR1 = f"decon_{os.path.basename(value[0])}"
    outR2 = f"decon_{os.path.basename(value[1])}"
    matched = f"matched.{os.path.basename(value[0]).replace('_R1', '')}"
    command = f"{config['EXE_BBDUK']} -Xmx1g in1={value[0]} in2={value[1]} out1={path}/{outR1} out2={path}/{outR2} qtrim=r trimq=25 maq=25 minlen=50 outm={path}/{matched} k=31 stats={path}/{key}.txt"
    deconReads = None
    try:
        subprocess.run(command, shell=True, check=True, stdout=fout, stderr=ferr)
        deconReads = (f"{path}/{outR1}", f"{path}/{outR2}")
    except:
        print("Failed to execute bbduk Paired End")
            
    fout.close()
    ferr.close()
    return deconReads


## End of script