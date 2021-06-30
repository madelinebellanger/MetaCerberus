#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""cerberus.py: Versatile Functional Ontology Assignments for Metagenomes

Uses Hidden Markov Model (HMM) searching with environmental focus of shotgun metaomics data.
"""

__version__ = "1.0"

import sys
import os
import subprocess
import argparse
import re
import multiprocessing as mp
import time
import socket
import ray

import cerberusQC, cerberusTrim, cerberusDecon, cerberusFormat
import cerberusGenecall, cerberusHMMER, cerberusParser, cerberusVisual


## Global variables
FILES_FASTQ = ['.fastq', '.fastq.gz']
FILES_FASTA = [".fasta", ".fa", ".fna", ".ffn"]
FILES_AMINO = [".faa"]

DEPENDENCIES = {
        'EXE_FASTQC': 'fastqc',
        'EXE_FASTP': 'fastp',
        'EXE_BBDUK': 'bbduk.sh',
        'EXE_PRODIGAL': 'prodigal'
        }

STEP = {
    1:"step_01-loadFiles",
    2:"step_02-QC",
    3:"step_03-trim",
    4:"step_04-decontaminate",    
    5:"step_05-format",
    6:"step_06-geneCall",
    7:"step_07-hmmer",
    8:"step_08-parse",
    9:"step_09-visualizeData"
    }


## PRINT to stderr ##
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


## RAY WORKER THREAD ##
@ray.remote
def rayWorker(func, key, value, config, path):
    start = time.time()
    eprint(f"{socket.gethostname()} | {func.__name__} | {path}")
    ret = func(value, config, path)
    with open(f'{config["DIR_OUT"]}/time.txt', 'a+') as outTime:
        outTime.write(f'{func.__name__}\t{path}\t{time.time()-start:.2f} seconds\n')
    return key, ret


## MAIN
def main():
    ## Parse the command line
    parser = argparse.ArgumentParser(add_help=False)
    required = parser.add_argument_group('required arguments')
    required = parser.add_argument_group('''At least one sequence is required
<accepted formats {.fastq .fasta .faa .fna .ffn .rollup}>
Example:
& cerberus.py --euk file1.fasta --euk file2.fasta --mic file3.fasta
& cerberus.py --config file.config''')
    required.add_argument('-e', '--euk', action='append', default=[], help='Eukaryote sequence (includes other viruses)')
    required.add_argument('-m', '--mic', action='append', default=[], help='Microbial sequence (includes bacteriophage)')
    optional = parser.add_argument_group('optional arguments')
    optional.add_argument("-c", "--config", help = "path to configuration file", type=argparse.FileType('r'))
    optional.add_argument("-o", "--outpath", help = "path to output directory. Defaults to current directory.", type=str)
    optional.add_argument('--version', '-v', action='version',
                        version='Cerberus: \n version: {} June 24th 2021'.format(__version__),
                        help='show the version number and exit')
    optional.add_argument("-h", "--help", action="help", help="show this help message and exit")
    args = parser.parse_args()

    if not any([args.euk, args.mic, args.config]):
        parser.print_help()
        parser.error('At least one of --euk or --mic must be declared either in the command line or through --config file')

    # Initialize RAY for Multithreading
    ray.init()

    config = {}
    if args.config is not None:
        print("\nLoading Configuration")
        config = loadConfig(args.config)
        args.config.close()

    # Merge config with parsed arguments
    if args.euk:
        config['EUK'] = args.euk
    if args.mic:
        config['MIC'] = args.mic
    if args.outpath:
        config['DIR_OUT'] = args.outpath
    print(config)

    # search dependency paths
    # TODO: Check versions as well
    print("Checking environment for dependencies:")
    for key,value in DEPENDENCIES.items():
        try:
            proc = subprocess.run(["which", value], stdout=subprocess.PIPE, text=True)
            path = proc.stdout.strip()
            if proc.returncode == 0:
                print(f"{value:20} {path}")
                DEPENDENCIES[key] = path
            else:
                print(f"{value:20} NOT FOUND, must be defined in config file as {key}:(path)")
        except:
            print(f"ERROR executing 'which {value}'")
    
    # Update config with dependencies found in environment
    DEPENDENCIES.update(config)
    config = DEPENDENCIES

    # Script path and relative dependencies
    config['PATH'] = os.path.dirname(os.path.abspath(__file__))
    config['EXE_FGS+'] = os.path.abspath(f"{config['PATH']}/FGS+/FGS+")


    # Sanity Check
    #TODO: fix due to change in input options
    #config['IN_PATH'] = config['IN_PATH'].rstrip('/')
    #for item in config:
    #    config[item] = os.path.abspath(os.path.expanduser(config[item]))
    #    print("Checking if exists: " + config[item])
    #    if item.startswith("DIR_"):
    #        if not os.path.isdir(config[item]):
    #            parser.error(f"Unable to find path: {config[item]}")
        
    #    if item.startswith("EXE_") and not os.path.isfile(config[item]):
    #        parser.error(f"Unable to find file: {config[item]}")

    config['EXT_FASTA'] = FILES_FASTA
    config['EXT_FASTQ'] = FILES_FASTQ
    config['EXT_AMINO'] = FILES_AMINO

    # Add CPU info to config
    if "CPUS" not in config:
        config["CPUS"] = mp.cpu_count()
    print(f"Using {config['CPUS']} CPUs per node")

    if 'DIR_OUT' not in config:
        config['DIR_OUT'] = os.path.abspath("./pipeline")
    else:
        os.path.join(config['DIR_OUT'], "pipeline")
    os.makedirs(config['DIR_OUT'], exist_ok=True)

    # Step 1 - Load Input Files
    fastq = fastq = {}
    fasta = fasta = {}
    amino = {}
    print("\nLoading input files:")
    #TODO: Implementing EUK and MIC options
    # Check
    for item in args.mic:
        item = os.path.abspath(os.path.expanduser(item))
        if os.path.isfile(item):
            name, ext = os.path.splitext(os.path.basename(item))
            if ext in FILES_FASTQ:
                fastq['mic_'+name] = item
            elif ext in FILES_FASTA:
                fasta['mic_'+name] = item
            elif ext in FILES_AMINO:
                amino[name] = item
        elif os.path.isdir(item):
            print(f'{item} is a directory, not a file') #TODO: ???implement loading all files in directory???
            # fastq, fasta = readFiles(item)
        else:
            print(f'{item} is not a valid file')
    for item in args.euk:
        item = os.path.abspath(os.path.expanduser(item))
        if os.path.isfile(item):
            name, ext = os.path.splitext(os.path.basename(item))
            if ext in FILES_FASTQ:
                fastq['euk_'+name] = item
            elif ext in FILES_FASTA:
                fasta['euk_'+name] = item
            elif ext in FILES_AMINO:
                amino[name] = item
        elif os.path.isdir(item):
            print(f'{item} is a directory, not a file') #TODO: ???implement loading all files in directory???
            # fastq, fasta = readFiles(item)
        else:
            print(f'{item} is not a valid file')

    print(f"\nFastq files: {fastq}")
    print(f"\nFasta files: {fasta}")


    # Step 2 (check quality of fastq files)
    jobs = []
    if fastq:
        print("\nSTEP 2: Checking quality of fastq files")
        for key,value in fastq.items():
            jobs.append(rayWorker.remote(cerberusQC.checkQuality, key, value, config, f"{STEP[2]}/{key}"))


    # Step 3 (trim fastq files)
    jobTrim = []
    if fastq:
        print("\nSTEP 3: Trimming fastq files")
        for key,value in fastq.items():
            jobTrim.append(rayWorker.remote(cerberusTrim.trimReads, key, [key, value], config, f"{STEP[3]}/{key}"))

    # Waitfor Trimmed Reads
    trimmedReads = {}
    for job in jobTrim:
        key,value = ray.get(job)
        trimmedReads[key] = value
    if trimmedReads:
        print(f"\nTrimmed Files: {trimmedReads}")

    if trimmedReads:
        print("\nChecking quality of trimmed files")
        for key,value in trimmedReads.items():
            jobs.append(rayWorker.remote(cerberusQC.checkQuality, key, value, config, f"{STEP[3]}/{key}/quality"))


    # step 4 Decontaminate (adapter free read to clean quality read + removal of junk)
    jobDecon = []
    if trimmedReads:
        print("\nSTEP 4: Decontaminating trimmed files")
        for key,value in trimmedReads.items():
            jobDecon.append(rayWorker.remote(cerberusDecon.deconReads, key, [key, value], config, f"{STEP[4]}/{key}"))

    deconReads = {}
    for job in jobDecon:
        key,value = ray.get(job)
        deconReads[key] = value
    if deconReads:
        print(f"Decontaminated reads: {deconReads}")


    # step 5a for cleaning contigs
    jobContigs = [] #TODO: Add config flag for contigs/scaffolds/raw reads
    if fasta:
        print("\nSTEP 5a: Removing N's from contig files")
        for key,value in fasta.items():
            jobContigs.append(rayWorker.remote(cerberusFormat.removeN, key, value, config, f"{STEP[5]}/{key}"))
    
    for job in jobContigs:
        key,value = ray.get(job)
        fasta[key] = value

    # step 5b Format (convert fq to fna. Remove quality scores and N's)
    jobFormat = []
    if deconReads:
        print("\nSTEP 5b: Reformating FASTQ files to FASTA format")
        for key,value in deconReads.items():
            jobFormat.append(rayWorker.remote(cerberusFormat.reformat, key, value, config, f"{STEP[5]}/{key}"))

    for job in jobFormat:
        key, value = ray.get(job)
        fasta[key] = value
    if fasta:
        print(f"FASTA reads: {fasta}")


    # step 6 (ORF Finder)
    jobGenecall = []
    if fasta:
        print("STEP 6: ORF Finder")
        for key,value in fasta.items():
            if key.startswith("euk_"):
                jobGenecall.append(rayWorker.remote(cerberusGenecall.findORF_euk, key, value, config, f"{STEP[6]}/{key}"))
            else:
                jobGenecall.append(rayWorker.remote(cerberusGenecall.findORF_mic, key, value, config, f"{STEP[6]}/{key}"))

    # Waiting for GeneCall
    for job in jobGenecall:
        key,value = ray.get(job)
        amino[key] = value
    print(f"Amino Acids: {amino}")


    # step 7 (HMMER)
    print("STEP 7: HMMER Search")
    jobHMM = []
    for key,value in amino.items():
        jobHMM.append(rayWorker.remote(cerberusHMMER.search, key, value, config, f"{STEP[7]}/{key}"))

    hmmFoam = {}
    print("Waiting for HMMER")
    for job in jobHMM:
        key,value = ray.get(job)
        hmmFoam[key] = value

    print(f"HMM Foam: {hmmFoam}")


    # step 8 (Parser)
    print("STEP 8: Parse HMMER results")
    jobParse = []
    for key,value in hmmFoam.items():
        jobParse.append(rayWorker.remote(cerberusParser.parseHmmer, key, value, config, f"{STEP[8]}/{key}"))

    hmmRollup = {}
    print("Waiting for parsed results")
    for job in jobParse:
        key,value = ray.get(job)
        hmmRollup[key] = value


    # step 9 (Visual)
    print("Creating plots COMMING SOON") #TODO: Implement plots once confident on FOAM/KO Results
    for key,value in hmmRollup.items():
        cerberusVisual.createReport(value, config, f"{STEP[9]}/{key}")


    # Wait for misc jobs
    print("Waiting for lingering jobs")
    for job in jobs:
        key,value = ray.get(job)

    # Finished!
    print("\nFinished Pipeline")
    return 0


## loadConfig
def loadConfig(configFile):
    config = {}
    for line in configFile:
        line = line.strip()
        if re.match("#", line) or line == "":
            continue
        line = line.split(":", 1)
        config[line[0].strip()] = line[1].strip()
    
    return config


## readFiles
def readFiles(config):
    rawReads = {}
    contigs = {}
    indir = config['DIR_IN']
    for filename in os.listdir(indir):
        filepath = f"{indir}/{filename}"
        print(f"Checking file: {filename}:")
        if (os.path.abspath(filepath) == os.path.abspath(config['REFSEQ']) or
                os.path.abspath(filepath) == os.path.abspath(config['REF_LAMBDA'])):
            print("Skipping Reference Sequence")
            continue
        if os.path.abspath(filepath) == os.path.abspath(config['ADAPTER']):
            print("ADAPTER file, skipping")
            continue
        if filename.endswith(tuple(FILES_QUALITY)): # With quality scores
            ext = list(filter(filename.endswith, FILES_QUALITY))[0]
            if "_R2.fastq" in filename:
                print("reverse read")
                continue
            if "_R1.fastq" in filename:
                baseName = filename.replace("_R1"+ext, "")
                reverseFile = filepath.replace("_R1"+ext, "_R2"+ext)
                if not os.path.exists(filepath):
                    # print("The reverse file does not exist, assuming single read.")
                    rawReads[filename] = filepath
                    continue
                else:
                    print(f"Paired End File")
                    rawReads[baseName] = (filepath, reverseFile)
                    continue
            else:
                print(f"Single Read File")
                rawReads[filename] = filepath
                continue
        elif filename.endswith(tuple(FILES_CONTIG)):
            print(f"Assembly File")
            contigs[filename] = filepath
        else:
            print("not a sequence file")
    return (rawReads, contigs)


## Start main method
if __name__ == "__main__":
    sys.exit(main())

## End of script
