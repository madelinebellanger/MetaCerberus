#!/usr/bin/env python3

import json
import re
import pandas as pd
from collections import OrderedDict


in_FOAM = "FOAM-onto_rel1.tsv"
out_FOAM = "FOAM-onto_rel1.tsv"
in_KEGG = "ko00001_2021-07.json"
out_KEGG = "KEGG-onto_rel1.tsv"

ECregex = re.compile(" \[EC:([^;]*)\]")


#### Recursive Method to load nested json file ####
def convert_json(dicData, writer, level=0, parents={}):
    table = {}
    if level > 0: #first level contains no writable data
        name = dicData['name'].split(maxsplit=1)
        if level < 4:
            parents[level] = name[1]
        else:
            match = ECregex.search(name[1])
            ec = match.group(1) if match else ''
            name[1] = ECregex.sub("", name[1])
            print('\t'.join(parents.values()), name[0], name[1], ec, sep='\t', file=writer)
            table[ name[0] ] = name[1]
    for value in dicData.values():
        if type(value) is list:
            for item in value:
                table.update( convert_json(item, writer, level+1, parents) )
    return table


#### START ####

# read file
with open(in_KEGG) as reader:
    data = json.load(reader)

# parse json
with open(out_KEGG, 'w') as writer:
    print("L1", "L2", "L3", "KO", "Function", "EC", sep='\t', file=writer)
    table = convert_json(data, writer)

# add functions from KEGG to FOAM
koNames = {}
koEC = {}
for key,val in table.items(): # split the names and the EC
    koNames[key] = ECregex.sub("", val)
    match = ECregex.search(val)
    if match:
        koEC[key] = match.group(1)

df = pd.read_csv(in_FOAM, sep='\t')
df['Function'] = df['KO'].map(koNames)
df['EC'] = df['KO'].map(koEC)

df.to_csv(out_FOAM, sep='\t', index=False)
