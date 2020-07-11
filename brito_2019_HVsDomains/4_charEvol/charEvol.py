#!/usr/bin/python

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Created by: Anderson Brito
#
#   charEvol.py -> This code processes matrices from Mesquite's ancestral
#                   state reconstruction analyses, and outputs files for
#                   visualizing the results on iTOL (itol.embl.de). It allows
#                   a closer look at the dynamics of domain gains, losses and
#                   duplications along the branches of a given tree.
#
# Release date: 29/Nov/2017
# Last update: 03/Jul/2020
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

from Bio import Phylo
import networkx as nx
from collections import Counter
import random
from datetime import datetime
import os
import argparse
from io import StringIO

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="This script generates as output a matrix of domain counts per taxa.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--tree", required=True, help="Phylogeny of the taxa included in both matrices")
    parser.add_argument("--matrix1", required=True,  help="Matrix of domain counts generated by domMatrix.py")
    parser.add_argument("--matrix2", required=True, help="File exported from Mesquite, containing the ancestral reconstruction")
    args = parser.parse_args()

    workdir = os.getcwd() + '/'
    tree_file = args.tree
    domain_file = args.matrix1
    mesq_file = args.matrix2

    tree = open(workdir + tree_file, 'r').readlines()
    domain_matrix = open(workdir + domain_file, "r").readlines() # matrix of domain counts
    mesquite_matrix = open(workdir + mesq_file, "r").readlines() # 'Trace all characters' Mesquite output


    # generate a unique folder name each time the code is run
    day, time = str(datetime.today()).split()
    uniqueDir = day + '_' + ''.join(time.split('.')[0].split(':'))
    print('\n Results will be saved at \'results\/' + uniqueDir + '\'')


    # create output directories
    if 'results' not in os.listdir(workdir):
        print('creating folder')
        os.system("mkdir \"%s%s\"" % (workdir, 'results'))

    subDir = 'results/' + uniqueDir + '/'
    if uniqueDir not in os.listdir(workdir + 'results/'):
        os.system("mkdir \"%s%s\"" % (workdir, subDir))

    itolDir = 'itol_annotations'
    if itolDir not in os.listdir(workdir + subDir):
        os.system("mkdir \"%s%s%s\"" % (workdir, subDir, itolDir))

    textDir = 'raw_outputs'
    if textDir not in os.listdir(workdir + subDir):
        os.system("mkdir \"%s%s%s\"" % (workdir, subDir, textDir))



    # convert nexus into newick
    def beast2nwk(phylogeny):
        # to get numeric names, and create a dict with their clade names
        dicNames = {}
        for line in phylogeny:
            if line.startswith('\t\t  '):
                num, spp = line.strip().replace(',', '').split()
                dicNames[num] = spp

        # parse the line containing the tree data
        treedata = ''
        for line in phylogeny:
            if 'tree TREE1'.lower() in line.lower():
                line = line.replace("=", "£", 1)
                treedata = line.split("£")[1].strip()

        handle = StringIO(treedata)
        tree = Phylo.read(handle, "newick")

        # to rename clade names
        for clade in tree.find_clades():
            if str(clade.name) in dicNames.keys():
                clade.name = dicNames[clade.name]

        return tree
    tree = beast2nwk(tree)

    # annotate newick tree with custom node names
    c = 2
    for clade in tree.find_clades():
        if str(clade.name) == 'None':
            clade.comment = '&&NHX:name=n'+str(c)
            clade.name = 'n'+str(c)
            clade.confidence = None
        c += 1

    # convert first tree into a network
    vNet = Phylo.to_networkx(tree)
    # print(vNet.nodes())

    # create list of tree tips
    lstTips = [term.name for term in tree.get_terminals()]

    # change node names creating a new network
    vGraph = nx.Graph()
    for edge in vNet.edges():
        # print(edge)
        root = ('root', 'n2')
        if root not in vGraph:
            vGraph.add_edge('root', 'n2')
        vGraph.add_edge(edge[0].name, edge[1].name)

    # check the edges
    lstEdges = []
    for edge in vGraph.edges():
        # print(edge)
        lstEdges.append(edge)


    # print all node names and paths
    evolPaths = []
    for node in vGraph.nodes():
        # print(node)
        for path in nx.all_simple_paths(vGraph, source='root', target=node):
            if path[-1] in lstTips:
                evolPaths.append(','.join(path))

    # export an iTol format tree with comments, and no node.name
    for clade in tree.find_clades():
        if str(clade.name) not in lstTips:
            clade.name = None
        else:
            clade.comment = None

    # save itol tree
    Phylo.write([tree], workdir + subDir + itolDir + '/' + tree_file.split('.')[0] + '_itol.tree', 'newick')

    # get header of characters matrix
    lstDomains = [dom.strip() for dom in domain_matrix[0].split('\t')[1:]]

    # process and transpose original meristic matrix from Mesquite 'Trace all characters' function
    merLst = []
    start = ''
    for line in mesquite_matrix:
        line = line.strip()
        # print(line)
        if 'Char.\\Node' in line:
            start = 'Found'
            # print(line)
        if start == 'Found':
            if '(min.)' in line:
                line = line.replace(' (min.):', '', 10000).replace('(max.):', '', 10000).replace(';  ', '_', 10000).replace('; ', '', 10000)
                if line.endswith(';'):
                    line = line[:-1]
                fixed = []
                # print(line)
                for col in line.split('\t'):
                    if 'character' in col:
                        domNum = int(col.split()[-1])-1
                        fixed.append(lstDomains[domNum])

                    if len(col.split('_')) == 2:
                        minC, maxC = col.split('_')
                        if minC == maxC:
                            fixed.append(maxC)
                        else:
                            fixed.append(col)
                merLst.append(fixed)
            else:
                nNodeLst = []
                for nodeInfo in line.split('\t'):
                    if nodeInfo not in lstTips:
                        nNodeLst.append('n' + nodeInfo) # add an 'n' to each internal node name
                    else:
                        nNodeLst.append(nodeInfo)
                merLst.append(nNodeLst)


    # transpose the fixed meristic matrix and output it
    transpMerlist = []
    outTranspose = open(workdir + subDir + textDir + '/' + 'transposed_mesquite_matrix.mat', 'w')
    for pos in list(map(list, zip(*merLst))):
        tLine = '\t'.join(pos)
        transpMerlist.append(tLine)
        outTranspose.write('\t'.join(pos) + '\n')
        # print(tLine)
    outTranspose.close()


    # create a dictionary with parsimony estimates per node/domain
    dicNodes = {}
    for line in transpMerlist[1:]:
        # print(line.strip())
        dicNodes[line.split('\t')[0]] = [count.strip() for count in line.split('\t')[1:]]


    for edge in lstEdges[1:]: # <<<<<< excluding ('root', 'n1') branch
        # print(edge)
        bfNode = edge[0]
        afNode = edge[1]

        if afNode not in lstTips:
            for num, profile in enumerate(zip(dicNodes[bfNode], dicNodes[afNode])):
                # newCount = 999
                # print(num, profile)
                countBe, countAf = profile

                # Option 1: choose randomly one of multiple parsimonious solutions
                if '_' in str(countBe): # pick a count for before node
                    print(bfNode + ' → ' + afNode)
                    print('oldCountBe = ', dicNodes[bfNode][num])
                    lstNum = list(range(int(countBe.split('_')[0]), int(countBe.split('_')[1]) + 1))
                    print(lstNum)
                    # print(random.choice(lstNum))
                    dicNodes[bfNode][num] = random.choice(lstNum)
                    # newCount = random.choice(lstNum)
                    print('newCountBe = ', dicNodes[bfNode][num])
                    print((dicNodes[bfNode][num], dicNodes[afNode][num]), lstDomains[num], '\n')


                if '_' in str(countAf):  # pick a count for after node
                    print(bfNode + ' → ' + afNode)
                    print('oldCountAf = ', dicNodes[afNode][num])
                    lstNum = list(range(int(countAf.split('_')[0]), int(countAf.split('_')[1]) + 1))
                    print(lstNum)
                    if dicNodes[bfNode][num] in lstNum:  # if ancestral node bfNode was uncertain, assign the same value here
                        dicNodes[afNode][num] = dicNodes[bfNode][num]
                        print('newCountAf = ', dicNodes[afNode][num])
                    else:  # if ancestral node bfNode was pre-defined, assign random choice from lstNum
                        # print(random.choice(lstNum))
                        dicNodes[afNode][num] = random.choice(lstNum)
                        print('newCountAf = ', dicNodes[afNode][num])
                    print((dicNodes[bfNode][num], dicNodes[afNode][num]), lstDomains[num], '\n')


    # count the character changes (gain, loss, and duplication)
    dicChanges = {}
    for edge in lstEdges:
        bfNode = edge[0]
        afNode = edge[1]

        if bfNode == 'root':
            dicNodes['root'] = dicNodes['n2']

        dicEvents = {'gain': [], 'loss': [], 'dup': []}
        for pfam, countBe, countAf in zip(lstDomains, dicNodes[bfNode], dicNodes[afNode]):
            difference = int(countAf) - int(countBe)

            if int(countAf) > 1 and int(countBe) > 0 and difference > 0: # count multiple domain duplication events
                dicEvents['dup'].extend([pfam] * abs(difference))

            if int(countBe) == 0 and difference > 1:  # count domain gain followed by duplication events
                dicEvents['gain'].append(pfam)

                dicEvents['dup'].extend([pfam] * abs(difference - 1))

            if int(countBe) == 0 and difference == 1: # count single domain gain events
                dicEvents['gain'].append(pfam)

            if int(countBe) > 0 and difference == -1: # count single domain loss events
                dicEvents['loss'].append(pfam)

            if int(countBe) > 0 and difference < -1: # count multiple domain loss events
                dicEvents['loss'].extend([pfam] * abs(difference))

            if bfNode == 'root':
                if int(countAf) == 1:
                    dicEvents['gain'].append(pfam)
                if int(countAf) > 1:
                    dicEvents['gain'].append(pfam)
                    dicEvents['dup'].append(pfam)

        dicChanges[edge] = dicEvents


    # list of events per branch
    desFile = open(workdir + subDir + textDir + '/' + 'events_per_branch.txt', 'w')
    desFile.write('branch\tgain events\tgained domains\tloss events\tlost domais\tduplication events\tduplicated domains\n')
    for edge, events in dicChanges.items():
        newDic = {}
        for type, doms in events.items():
            # print(type)
            newDic[type] = []
            for pfam in doms:
                newDic[type] += [pfam]
        result = '\t'.join([(str(len(occ))) + '\t' + '; '.join(occ) for eve, occ in newDic.items()])
        desFile.write(edge[0] + ' → ' + edge[1] + '\t' + result + '\n')

    print('\n')

    print('\n\n###### Generating iTOL annotation files')
    # generate itol annotations for labeling domains in branches
    c = 1
    newDic = {}
    dicRes = {}
    dicRes['domain'] = []
    recEvents = {}
    recEvents['gain'] = []
    recEvents['loss'] = []
    recEvents['dup'] = []
    for edge, events in dicChanges.items():
        node = edge[1]
        if edge[1].isdigit():
            node = 'n' + edge[1]

        # define the spacing between elements mapped on a branch
        allDoms = [item for sublist in list(events.values()) for item in list(set(sublist))]
        # print(allDoms)
        if len(allDoms) > 1:
            step = 1 / (len(allDoms) + 1)
        elif len(allDoms) == 1:
            step = 0.5
        else:
            pass

        pos = step
        o = 1
        for type, doms in events.items():
            # print(type, doms)
            if node != 'n2':
                dicCount = dict(Counter(doms))
                duplicates = [item for item, count in dicCount.items() if count > 1]
                # print('duplicates', duplicates)

                for d in list(set(doms)):
                    # print(edge[1], type, pos)
                    # Using generic IDs as labels
                    if d not in newDic.keys():
                        dId = 'd' + (3 - len(str(c))) * '0' + str(c)
                        newDic[d] = dId
                        dName = dId + '\t' + d
                        c += 1

                    dLabel = newDic[d]
                    if d in duplicates: # to show/identify only one domain representation when event happens multiple times
                        dLabel = dLabel + "*"
                    # print(d, dLabel)

                    if type == 'gain':
                        dicRes['domain'] += [','.join([node, '1', '1', '#54A800', '1', str(pos)[:4], d])]

                        if 'label' + str(o) not in dicRes.keys():
                            dicRes['label' + str(o)] = []
                        dicRes['label' + str(o)] += [','.join([node, dLabel, str(pos)[:4], '#54A800', 'normal', '1'])]

                        recEvents['gain'] += [dName]  # to add to the recurrent events list

                        print('domain' + '\t' + ','.join([node, '1', '1', '#54A800', '1', str(pos)[:4], d]))
                        print('label' + str(o) + '\t' + ','.join([node, dLabel, str(pos)[:4], '#54A800', 'normal', '1']))

                    if type == 'loss':
                        dicRes['domain'] += [','.join([node, '1', '1', '#000000', '0', str(pos)[:4], d])]

                        if 'label' + str(o) not in dicRes.keys():
                            dicRes['label' + str(o)] = []
                        dicRes['label' + str(o)] += [','.join([node, dLabel, str(pos)[:4], '#000000', 'normal', '1'])]

                        recEvents['loss'] += [dName]  # to add to the recurrent events list

                        print('domain' + '\t' + ','.join([node, '1', '1', '#000000', '0', str(pos)[:4], d]))
                        print('label' + str(o) + '\t' + ','.join([node, dLabel, str(pos)[:4], '#000000', 'normal', '1']))

                    if type == 'dup':
                        dicRes['domain'] += [','.join([node, '1', '1', '#7849A8', '1', str(pos)[:4], d])]

                        if 'label' + str(o) not in dicRes.keys():
                            dicRes['label' + str(o)] = []
                        dicRes['label' + str(o)] += [','.join([node, dLabel, str(pos)[:4], '#7849A8', 'normal', '1'])]

                        recEvents['dup'] += [dName]  # to add to the recurrent events list

                        print('domain' + '\t' + ','.join([node, '1', '1', '#7849A8', '1', str(pos)[:4], d]))
                        print('label' + str(o) + '\t' + ','.join([node, dLabel, str(pos)[:4], '#7849A8', 'normal', '1']))

                    pos += step
                    o += 1
            else:  # to add domains present at the root → n2 branch
                for d in doms:
                    dName = 'dxx' + '\t' + d

                    if type == 'gain':
                        recEvents['gain'] += [dName]  # to add to the recurrent events list

                    if type == 'loss':
                        recEvents['loss'] += [dName]  # to add to the recurrent events list

                    if type == 'dup':
                        recEvents['dup'] += [dName]  # to add to the recurrent events list


    # outputs a list of recurrent events
    recFile = open(workdir + subDir + textDir + '/' + 'list_events.txt', 'w')
    for ev, domNames in recEvents.items():
        # print(id, pfam)
        recFile.write('\n' + ev + '\n')
        for d in domNames:
            recFile.write(d + '\n')


    # outputs the legend for the current run
    legFile = open(workdir + subDir + textDir + '/' + 'legend.txt', 'w')
    for pfam, id in newDic.items():
        # print(id, pfam)
        legFile.write(id + ': ' + pfam + '\n')

    # save itol annotation files
    for out, info in dicRes.items():
        outputFile = open(workdir + subDir + itolDir + '/itol-' + out + '.txt', 'w')
        if 'domain' in out:
            outputFile.write('DATASET_SYMBOL\n\nSEPARATOR COMMA\n\nDATASET_LABEL,domain symbols\n\nCOLOR,#ffff00\n\nMAXIMUM_SIZE,3\n\nDATA\n\n')
        else:
            outputFile.write('DATASET_TEXT\n\nSEPARATOR COMMA\n\nDATASET_LABEL,'+out+'\n\nCOLOR,#ffff00\n\nLABEL_ROTATION,-45\n\nSIZE_FACTOR,1\n\nDATA\n\n')

        for line in info:
            outputFile.write(line + '\n')

    print('\n\nitol-files saved in sub-directory \'results/' + uniqueDir + '\'\n')
