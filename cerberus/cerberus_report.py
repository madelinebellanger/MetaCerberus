# -*- coding: utf-8 -*-

import os
import time
import shutil
import base64
import re
from dominate.util import raw
import pandas as pd
import pkg_resources as pkg
import plotly.express as px
import dominate
from dominate.tags import *


### GLOBAL Variables ###

# standard html header to include plotly script
htmlHeader = [
    '<html>',
    '<head><meta charset="utf-8" />',
    '    <script src="plotly-2.0.0.min.js"></script>',
    '</head>',
    '<body>\n']

# TODO: Option for how to include plotly.js.
# False uses script in <head>, 'cdn' loads from internet.
# Can I use both???
PLOTLY_SOURCE = 'cdn'

# style.css
STYLESHEET = pkg.resource_stream('cerberus_data', 'style.css').read().decode()


######### Create Report ##########
def createReport(figSunburst, figCharts, config, subdir):
    path = f"{config['DIR_OUT']}/{subdir}"
    os.makedirs(path, exist_ok=True)

    plotly = pkg.resource_filename('cerberus_data', 'plotly-2.0.0.min.js')
    shutil.copy(plotly, path)
    
    # Sunburst HTML files
    for sample,figures in figSunburst.items():
        outpath = os.path.join(path, sample)
        for name,fig in figures.items():
            with open(f"{outpath}/sunburst_{name}.html", 'w') as htmlOut:
                htmlOut.write("\n".join(htmlHeader))
                htmlOut.write(f"<H1>Sunburst summary of {name} Levels</H1>\n")
                htmlFig = fig.to_html(full_html=False, include_plotlyjs=PLOTLY_SOURCE)
                htmlOut.write(htmlFig + '\n')
                htmlOut.write("\n</body>\n</html>\n")

    # Bar Charts
    for sample,figures in figCharts.items():
        outpath = os.path.join(path, sample)
        for name,fig in figures[0].items():
            outfile = os.path.join(outpath, f"barchart_{name}.html")
            write_HTML_files(outfile, fig, sample, name)
        continue

    return None


########## Write Stats ##########
def write_Stats(outpath: os.PathLike, readStats: dict, protStats: dict, config: dict):
    dictStats = protStats.copy()

    # Merge Stats
    nstatLabels = ['N25', 'N50', 'N75', 'N90']
    trimLabels = ['passed', 'low quality', 'too many Ns', 'too short', 'low complexity', 'adapter trimmed', 'bases: adapters', 'duplication rate %']
    deconLabels = ['contaminants', 'QTrimmed', 'Total Removed', 'Results']
    reNstats = re.compile(r"N25[\w\s:%()]*>= ([0-9]*)[\w\s:%()]*>= ([0-9]*)[\w\s:%()]*>= ([0-9]*)[\w\s:%()]*>= ([0-9]*)")
    reGC = re.compile(r"GC count:\s*([0-9]*)[\w\s]*%:\s*([.0-9]*)")
    reTrim = re.compile(r"Filtering result:[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)")
    reDecon = re.compile(r"([0-9]*) reads \([0-9%.]*\)[\s]*([0-9]*)[\w\s(0-9-.%)]*:[\s]*([0-9]*) reads \([0-9%.]*\)[\s]*([0-9]*)[\w\s(0-9-.%)]*:[\s]*([0-9]*) reads \([0-9%.]*\)[\s]*([0-9]*)[\w\s(0-9-.%)]*:[\s]*([0-9]*) reads \([0-9%.]*\)[\s]*([0-9]*)")
    for key,value in readStats.items():
        # GC Count
        gcCount = reGC.search(value, re.MULTILINE)
        if gcCount: dictStats[key]['GC count'] = gcCount.group(1)
        if gcCount: dictStats[key]['GC %'] = gcCount.group(2)
        # N25-N90
        Nstats = reNstats.search(value, re.MULTILINE)
        if Nstats:
            for i,label in enumerate(nstatLabels, 1):
                dictStats[key][label] = Nstats.group(i)
        # Trimmed stats
        infile = os.path.join(config['DIR_OUT'], config['STEP'][3], key, "stderr.txt")
        try:
            trimStats = '\n'.join(open(infile).readlines())
            trim = reTrim.search(trimStats, re.MULTILINE)
            if trim:
                for i,label in enumerate(trimLabels, 1):
                    dictStats[key]['trim: '+label] = trim.group(i)
        except: pass
        # Decon stats
        infile = os.path.join(config['DIR_OUT'], config['STEP'][4], key, "stderr.txt")
        try:
            deconStats = '\n'.join(open(infile).readlines())
            decon = reDecon.search(deconStats, re.MULTILINE)
            if decon:
                for i,label in enumerate(deconLabels, 0):
                    dictStats[key]['decon: reads'+label] = decon.group(i*2+1)
                    dictStats[key]['decon: bases'+label] = decon.group(i*2+2)
        except: pass
        # Write fasta stats to file
        outfile = os.path.join(outpath, key, "fasta_stats.txt")
        os.makedirs(os.path.join(outpath, key), exist_ok=True)
        with open(outfile, 'w') as writer:
            writer.write(value)

    #Write Combined Stats to File
    outfile = os.path.join(outpath, "combined", "stats.tsv")
    os.makedirs(os.path.join(outpath, "combined"), exist_ok=True)
    dfStats = pd.DataFrame(dictStats)
    dfStats.to_csv(outfile, sep='\t')

    # HTML Plots of Stats
    outfile = os.path.join(outpath, "combined", "stats.html")
    dfStats = dfStats.apply(pd.to_numeric)
    df = dfStats.T[['Total Protein Count', 'Proteins Above Min Score']].reset_index()
    df = df.melt(id_vars=['index'], var_name='proteins', value_name='value')
    figCounts = px.bar(df, x='index', y='value',
        color='proteins', barmode='overlay',
        labels=dict(proteins="", index="Sample Name", value="Protein Count")
    )
    df = dfStats.T.reset_index()
    figLength = px.bar(df, x='index', y='Average Protein Length',
        labels={'index':"Sample Name", 'Average Protein Length':"Number of Peptides"}
    )
    df = dfStats.T[['FOAM KO Count', 'KEGG KO Count']].reset_index()
    df = df.melt(id_vars=['index'], var_name='group', value_name='value')
    figKOCounts = px.bar(df, x='index', y='value',
        color='group', barmode='group',
        labels=dict(group="", index="Sample Name", value="Protein Count")
    )
    df = dfStats.T[['GC %']].reset_index()
    print(df)
    figGC = px.bar(df, x='index', y='GC %',
        labels={'index':"Sample Name", 'GC %':'Percent'}
    )
    df = dfStats.T[['N25', 'N50', 'N75', 'N90']].reset_index()
    df = df.melt(id_vars=['index'], var_name='group', value_name='value')
    print(df)
    figN = px.bar(df, x='index', y='value',
        color='group', barmode='group',
        labels=dict(group="", index="Sample Name", value="Nucleotide Threshold")
    )
    with dominate.document(title='Stats Report') as doc:
        with doc.head:
            meta(charset="utf-8")
            script(type="text/javascript", src="plotly-2.0.0.min.js")
            with style(type="text/css"):
                raw('\n'+STYLESHEET)
        with div(cls="document", id="cerberus-summary"):
            with h1(cls="title"):
                a("CERBERUS", cls="reference external", href="https://github.com/raw-lab/cerberus")
                raw(" - Assembly Summary")
            with div(cls="contents topic", id="contents"):
                with ul(cls="simple"):
                    li(a("Summary", cls="reference internal", href="#summary"))
                    with ul():
                        li(a("Protein Counts", cls="reference internal", href="#Protein Counts"))
                        li(a("Average Protein Length", cls="reference internal", href="#Average Protein Length"))
                        li(a("KO Counts", cls="reference internal", href="#KO Counts"))
                        li(a("GC Counts", cls="reference internal", href="#GC Counts"))
                        li(a("N Stats", cls="reference internal", href="#N Stats"))
                    li(a("Downloads", cls="reference internal", href="#downloads"))
            with div(h1("Summary"), cls="section", id="summary"):
                with div(h2('Protein Counts'), cls="section", id="Protein Counts"):
                    raw(figCounts.to_html(full_html=False, include_plotlyjs=PLOTLY_SOURCE))
                with div(h2('Average Protein Length'), cls="section", id="Average Protein Length"):
                    raw(figLength.to_html(full_html=False, include_plotlyjs=PLOTLY_SOURCE))
                with div(h2('KO Counts'), cls="section", id="KO Counts"):
                    raw(figKOCounts.to_html(full_html=False, include_plotlyjs=PLOTLY_SOURCE))
                with div(h2('GC Counts'), cls="section", id="GC Counts"):
                    raw(figGC.to_html(full_html=False, include_plotlyjs=PLOTLY_SOURCE))
                with div(h2('N Stats'), cls="section", id="N Stats"):
                    raw(figN.to_html(full_html=False, include_plotlyjs=PLOTLY_SOURCE))
            with div(cls="section", id="downloads"):
                h1("Downloads")
                with div(cls="docutils container", id="attachments"):
                    with blockquote():
                        with div(cls="docutils container", id="table-1"):
                            with dl(cls="docutils"):
                                tsv_stats = base64.b64encode(dfStats.to_csv(sep='\t').encode('utf-8')).decode('utf-8')
                                data_URI = f"data:text/tab-separated-values;base64,{tsv_stats}"
                                dt("Combined Stats:")
                                dd(a("combined_stats.tsv", href=data_URI, download="combined_stats.tsv", draggable="true"))
                div(time.strftime("%Y-%m-%d", time.localtime()), cls="docutils container", id="metadata")


    with open(outfile, 'w') as writer:
        writer.write(doc.render())
    #figStats.write_html(outfile, full_html=False, include_plotlyjs=PLOTLY_SOURCE)

    return dfStats


########## Write PCA Report ##########
def write_PCA(outpath, pcaFigures):
    # PCA Files
    os.makedirs(os.path.join(outpath), exist_ok=True)

    for database,figures in pcaFigures.items():
        prefix = f"{outpath}/{database}"
        with open(prefix+"_PCA.htm", 'w') as htmlOut:
            htmlOut.write("\n".join(htmlHeader))
            htmlOut.write(f"<h1>PCA Report for {database}<h1>\n")
            for graph,fig in figures.items():
                if type(fig) is pd.DataFrame:
                    fig.to_csv(f"{prefix}_{graph}.tsv", index=False, header=True, sep='\t')
                else:
                    # type= plotly.graph_objs._figure.Figure
                    #htmlOut.write(f"<h2 style='text-align:center'>{graph.replace('_', ' ')}</h2>")
                    htmlFig = fig.to_html(full_html=False, include_plotlyjs=PLOTLY_SOURCE)
                    htmlOut.write(htmlFig + '\n')
            htmlOut.write('\n</body>\n</html>\n')
    return None


########## Write Tables ##########
def writeTables(table: pd.DataFrame, filePrefix: os.PathLike):
    table = table.copy()

    regex = re.compile(r"^lvl[0-9]: ")
    table['Name'] = table['Name'].apply(lambda x : regex.sub('',x))

    levels = int(max(table[table.Level != 'Function'].Level))
    for i in range(1,levels+1):
        filter = table['Level']==str(i)
        table[filter][['Name','Count']].to_csv(f"{filePrefix}_level-{i}.tsv", index = False, header=True, sep='\t')
    regex = re.compile(r"^K[0-9]*: ")
    table['Name'] = table['Name'].apply(lambda x : regex.sub('',x))
    table[table['Level']=='Function'][['KO Id','Name','Count']].to_csv(f"{filePrefix}_level-ko.tsv", index = False, header=True, sep='\t')


########## Write HTML Files ##########
def write_HTML_files(outfile, figure, sample, name):

    with open(outfile, 'w') as htmlOut:
        htmlOut.write("\n".join(htmlHeader))
        htmlOut.write(f"<h1>Cerberus {name} Report for '{sample}<h1>\n")
        levels = {}
        htmlOut.write(f'<H2>{name} Levels</H2>\n')
        htmlOut.write("<H4>*Clicking on a bar in the graph displays the next level.</br>The graph will cycle back to the first level after reaching the last level.</H4>")
        for title, figure in figure.items():
            htmlFig = figure.to_html(full_html=False, include_plotlyjs=PLOTLY_SOURCE)
            try:
                id = re.search('<div id="([a-​z0-9-]*)"', htmlFig).group(1)
            except:
                continue
            levels[id] = title
            display = "block" if title=="Level 1" else "none"
            htmlFig = htmlFig.replace('<div>', f'<div id="{title}" style="display:{display};">', 1)
            htmlOut.write(htmlFig + '\n')
        # Scripts
        htmlOut.write('<script>\n')
        for id, title in levels.items():
            level = int(title.split(':')[0][-1])
            htmlOut.write(f"""
        document.getElementById("{id}").on('plotly_click', function(data){{
            var name = data.points[0].x;
            var id = "Level {level+1}: " + name
            element = document.getElementById(id)
            if (element !== null)
                element.style.display = "block";
            else
                document.getElementById("Level 1").style.display = "block";
            document.getElementById("{title}").style.display = "none";
            // Refresh size
            var event = document.createEvent("HTMLEvents");
            event.initEvent("resize", true, false);
            document.dispatchEvent(event);
        }});""")
        htmlOut.write('</script>\n')
        htmlOut.write('\n</body>\n</html>\n')

        return
