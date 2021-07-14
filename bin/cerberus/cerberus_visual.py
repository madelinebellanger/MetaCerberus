# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from functools import reduce
import plotly.express as px  # (version 4.7.0)
import plotly.graph_objects as go
from plotly.subplots import make_subplots


######### Create PCA Graph ##########
def graphPCA(table_list):

    dfFOAM = pd.DataFrame()
    dfKEGG = pd.DataFrame()
    types = ["Foam", "KO"]
    
    for sample,table in table_list.items():
        # FOAM
        X = table[table['Type']=="Foam"]
        row = dict(zip(X['Name'].tolist(), X['Count'].tolist()))
        row = pd.Series(row, name=sample)
        dfFOAM = dfFOAM.append(row)

        # KEGG
        X = table[table['Type']=="KO"]
        row = dict(zip(X['Name'].tolist(), X['Count'].tolist()))
        row = pd.Series(row, name=sample)
        dfKEGG = dfKEGG.append(row)

    dfFOAM = dfFOAM.fillna(0).astype(int)
    dfKEGG = dfKEGG.fillna(0).astype(int)

    # Run PCA and add to Plots
    figPCA = {}
    for count,df in enumerate([dfFOAM, dfKEGG], 0):
        data_type = types[count]

        # Do PCA
        X = df
        scaler = StandardScaler()
        scaler.fit(X)
        X_scaled = scaler.transform(X)

        pca = PCA()
        X_pca = pca.fit_transform(X_scaled)
        #print("Original Data:\n", X)
        #print("Fit and transformed data:\n", X_pca)
        #print("N Components\n", pca.n_components_, pca.components_)
        #print("Explained Variance:\n", pca.explained_variance_)
        #print("Explained Variance Ratio\n", pca.explained_variance_ratio_*100)
        
        # Create Scree Plot
        figScree = px.line(
            x=range(1, pca.n_components_+1),
            y=pca.explained_variance_ratio_*100,
            labels={'x':'Principal Component', 'y':'Percent Variance Explained'}
        )
        figPCA[data_type+"_scree"] = figScree
        
        # Create 3D Plot
        labels = {
            str(i): f"PC {str(i+1)} ({var:.2f}%)"
                for i,var in enumerate(pca.explained_variance_ratio_ * 100)}
        
        fig3d = px.scatter_3d(
            X_pca, x=0, y=1, z=2, color=X.index,
            #title=data_type,
            labels=labels)
        figPCA[data_type] = fig3d
    
    return figPCA


########## Create Sunburst Figures ##########
def graphSunburst(table):
    dfFoam = table[table["Type"]=='Foam']
    dfKO = table[table["Type"]=='KO']
    count = table['Count']
    midpoint = np.average(count, weights=count)*2

    dfKO = dfKO.replace("KO", "KEGG")

    # Create Sunburst Figures
    figSunburst = go.Figure(layout=dict(
        grid = dict(columns=2, rows=1),
        margin = dict(t=0, l=0, r=0, b=0)))
    figSunburst.update_traces(font=dict(size=[40]))
    col=0
    for df in [dfFoam, dfKO]:
        sun = px.sunburst(df, path = ['Type','Level','Name'],
            values = 'Count', color = 'Count',
            color_continuous_scale = 'RdBu',
            color_continuous_midpoint = midpoint)
        sun.update_traces(textfont=dict(size=[40]))
        figSunburst.add_trace(go.Sunburst(
            labels = sun['data'][0]['labels'],
            parents = sun['data'][0]['parents'],
            values = sun['data'][0]['values'],
            ids = sun['data'][0]['ids'],
            domain = dict(column=col),
            textfont = dict(size=[40])
            ))
        sun.update_traces(textfont=dict(size=[40]))
        figSunburst.update_traces(textfont=dict(size=[40]))
        col += 1
    figSunburst.update_traces(textfont=dict(size=[40]))

    return figSunburst


########## Create Bar Chart Figures ##########
def graphBarcharts(rollupFiles):
    #TODO: restructure code to avoid loading rollup files and counting twice (fist in parser.py)
    df_FOAM = pd.read_csv(rollupFiles[0], names=['Id','Count','Info'], delimiter='\t')
    df_KEGG = pd.read_csv(rollupFiles[1], names=['Id','Count','Info'], delimiter='\t')

    # Reformat data. This lambda method avoids chained indexing
    # Splits string into list, strips brackets and quotes
    helper = lambda x : [i.strip("'") for i in x.strip('[]').split("', ")]
    # call helper method to reformat 'FOAM' and 'KO' columns
    df_FOAM['Info'] = df_FOAM['Info'].apply(helper)
    df_KEGG['Info'] = df_KEGG['Info'].apply(helper)
    # Convert 'Count" column to numeric
    df_FOAM["Count"] = pd.to_numeric(df_FOAM["Count"])
    df_KEGG["Count"] = pd.to_numeric(df_KEGG["Count"])


    # Enumerate data
    foamCounts = {}
    for row in range(len(df_FOAM)):
        for name in df_FOAM['Info'][row]:
            if name not in foamCounts:
                foamCounts[name] = df_FOAM['Count'][row]
            foamCounts[name] += 1
    koCounts = {}
    for row in range(len(df_KEGG)):
        for name in df_KEGG['Info'][row]:
            if name not in koCounts:
                koCounts[name] = df_KEGG['Count'][row]
            koCounts[name] += 1
    # TODO: Refactor this
    def countLevels(df):
        dictDF = {}
        for row in range(len(df)):
            for j in range(len(df['Info'][row])):
                dictDF[df['Info'][row][j]] = dictDF.get(df['Info'][row][j],["", 0])
                n,m = dictDF[df['Info'][row][j]]
                dictDF[df['Info'][row][j]] = [j+1, m+df['Count'][row]]
        return dictDF
    #foamCounts = countLevels(df_FOAM)
    #koCounts = countLevels(df_KEGG)

    # FOAM
    dictFoam = {}
    for row in range(len(df_FOAM)):
        for i,name in enumerate(df_FOAM['Info'][row], 1):
            if name == '':
                continue
            if i == 1:
                level1 = name
                if name not in dictFoam:
                    dictFoam[level1] = {}, foamCounts[name]
            elif i == 2:
                level2 = name
                if name not in dictFoam[level1][0]:
                    dictFoam[level1][0][level2] = {}, foamCounts[name]
            elif i == 3:
                level3 = name
                if name not in dictFoam[level1][0][level2][0]:
                    dictFoam[level1][0][level2][0][level3] = {}, foamCounts[name]
            else:
                level4 = name
                if level4 not in dictFoam[level1][0][level2][0][level3][0]:
                    dictFoam[level1][0][level2][0][level3][0][level4] = foamCounts[name]
                #else:
                    #print("WARNING: duplicate line in rollup: FOAM: ", row, name, df_FOAM['Info'][row]) #TODO: Remove when bugs not found

    # KO
    dictKO = {}
    for row in range(len(df_KEGG)):
        for i,name in enumerate(df_KEGG['Info'][row], 1):
            if name == '':
                continue
            if i == 1:
                level1 = name
                if name not in dictKO:
                    dictKO[level1] = {}, koCounts[name]
            elif i == 2:
                level2 = name
                if name not in dictKO[level1][0]:
                    dictKO[level1][0][level2] = {}, koCounts[name]
            elif i == 3:
                level3 = name
                if name not in dictKO[level1][0][level2][0]:
                    dictKO[level1][0][level2][0][level3] = {}, koCounts[name]
            else:
                level4 = name
                if level4 not in dictKO[level1][0][level2][0][level3][0]:
                    dictKO[level1][0][level2][0][level3][0][level4] = koCounts[name]
                #else:
                    #print("WARNING: duplicate line in rollup: KEGG: ", row, name, df_KEGG['Info'][row]) #TODO: Remove when bugs not found

    return createHierarchyFigures(dictFoam), createHierarchyFigures(dictKO)

# TODO: recursive function for replacing createHierarchyFigures()
#chart = {}
#def hierarchy(level, i):
#    print(type(level), i)
#    if type(level) is dict:
#        for k,v in level.items():
#            print(i, k, v[1])
#            chart[k] = {}
#            hierarchy(v[0], i+1)
#    return chart
#print(hierarchy(data, 1))


### Create hierarchy figures from table with levels
def createHierarchyFigures(data):
    ### Helper method for conciseness below ###
    def buildFigure(x, y, title):
        return go.Figure(layout={'title':title,
                #'xaxis_title':"Name",
                'yaxis_title':"Count"},
                data=[go.Bar(x=list(x), y=list(y))])
    
    # Create figures in hierarchy format
    # TODO: This is probably better as a recursive function
    charts = {}
    data1 = {}
    for k1,v1 in data.items():
        #print("\t", k1, v1[1])
        data1[k1] = v1[1]
        data2 = {}
        for k2,v2 in v1[0].items():
            #print("\t\t", k2, v2[1])
            data2[k2] = v2[1]
            data3 = {}
            for k3,v3 in v2[0].items():
                #print("\t\t\t", k3, v3[1])
                data3[k3] = v3[1]
                data4 = {}
                for k4,v4 in v3[0].items():
                    #print("\t\t\t\t", k4, v4)
                    data4[k4] = v4
                if len(data4):
                    title = f"Level 4: {k3}"
                    charts[title] = buildFigure(data4.keys(), data4.values(), title)
            if len(data3):
                title = f"Level 3: {k2}"
                charts[title] = buildFigure(data3.keys(), data3.values(), title)
        if len(data2):
            title = f"Level 2: {k1}"
            charts[title] = buildFigure(data2.keys(), data2.values(), title)
    if len(data1):
        title = "Level 1"
        charts[title] = buildFigure(data1.keys(), data1.values(), title)
    return charts
