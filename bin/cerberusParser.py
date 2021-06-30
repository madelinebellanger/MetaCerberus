# -*- coding: utf-8 -*-
"""cerberusParser.py Parses HMMER output and identifies KOs with FOAM and KEGG DB info
1) Get top hits
2) Store best score
3) Save rollup file
"""

import os
import csv
from collections import Counter


def parseHmmer(hmmer, config, subdir):
    path = f"{config['DIR_OUT']}/{subdir}"
    os.makedirs(path, exist_ok=True)

    # Calculate Best Hit
    BH_dict = {}
    minscore = 25 #TODO: Move to config file, user specifies this
    with open(hmmer, "r") as reader:
        for line in reader:
            if line.startswith("#"):        # Skip commented lines
                continue
            line = line.split()
            try:
                query = line[0]             # Column 0 is our query
                line[13] = float(line[13])  # Column 14 is the score, convert to float
            except:
                continue
            score = line[13]
            if score < minscore:            # Skip scores less than minscore
                continue
            # Check for Best Score per query
            if query not in BH_dict:
                BH_dict[query] = line
            elif score > BH_dict[query][13]:
                BH_dict[query] = line


    # Create dictionary with found KO IDs and counts
    KO_ID_dict = {}
    for line in BH_dict.values():
        KO_IDs = [KO_ID.split(":")[1].split("_")[0] for KO_ID in line[3].split(",") if "KO:" in KO_ID]
        for KO_ID in KO_IDs:
            if KO_ID not in KO_ID_dict:
                KO_ID_dict[KO_ID] = 0
            KO_ID_dict[KO_ID] += 1

    rollup_file = f"{path}/FOAM.BH.KO.rollup"
    return roll_up(KO_ID_dict, rollup_file, f'{config["PATH"]}/cerberusDB')


######### Roll-Up #########
def roll_up(KO_ID_dict, rollup_file, dbPath):

    # Read FOAM information
    FOAM_file = os.path.join(dbPath, "FOAM-onto_rel1.tsv")
    FOAM_dict = {}
    with open(FOAM_file, "r") as csvFile:
        reader = csv.reader(csvFile, delimiter="\t")
        next(reader)    # Skip header
        for line in reader:
            KO_ID = line[4]
            FOAM_info = line[0:4]
            FOAM_dict[KO_ID] = FOAM_info

    # Read KEGG information
    KEGG_file = f"{dbPath}/KO_classification.txt"
    KEGG_dict = {}
    with open(KEGG_file, "r") as csvFile:
        reader = csv.reader(csvFile, delimiter="\t")
        for line in reader:
            if line[0] != "":
                tier_1 = line[0]
                continue
            if line[1] != "":
                tier_2 = line[1]
                continue
            if line[2] != "":
                pathway = line[3]
                continue
            KO_ID = line[3]
            KEGG_info = [tier_1, tier_2, pathway] + line[4:]
            KEGG_dict[KO_ID] = KEGG_info

    # Match FOAM and KEGG info with found KO
    with open(rollup_file, "w") as outfile:
        for KO_ID in sorted(KO_ID_dict.keys()):
            FOAM_info = FOAM_dict[KO_ID] if KO_ID in FOAM_dict else ["NA"]
            KEGG_info = KEGG_dict[KO_ID] if KO_ID in KEGG_dict else ["NA"]
            outline = "\t".join([str(s) for s in [KO_ID, KO_ID_dict[KO_ID], FOAM_info, KEGG_info]])
            outfile.write(outline + "\n")

    return rollup_file
