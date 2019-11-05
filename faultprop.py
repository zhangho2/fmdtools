# -*- coding: utf-8 -*-
"""
File name: faultprop.py
Author: Daniel Hulse
Created: December 2018
Forked from the IBFM toolkit, original author Matthew McIntire

Description: functions to propagate faults through a user-defined fault model
"""
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import copy
from astropy.table import Table, Column
import pandas as pd


##PLOTTING AND RESULTS DISPLAY

#plotflowhist
# displays plots of a history of flow states over time
# inputs: 
#   - flowhist, the history of one or more flows over time stored in a dictionary with structure:
#       {nominal/faulty: {flow: {attribute: [values]}}}, where
#           - nominal/nominal keeps the history ifor both faulty and nominal flows
#           - flow is all flows that were tracked 
#           - attribute is the defined attributes of that flow (e.g. rate/effort/etc)
#           - values is a list of values that attribute takes over time
#   - fault, name of the fault that was injected (for the titles)
#   - time, the time in which the fault was initiated (so that time is displayed on the graph)
def plotflowhist(flowhist, fault='', time=0):
    flowhists={}
    if 'nominal' not in flowhist: flowhists['nominal']=flowhist
    else: flowhists=flowhist
    
    for flow in flowhists['nominal']:
        fig = plt.figure()
        plots=len(flowhists['nominal'][flow])
        fig.add_subplot(np.ceil((plots+1)/2),2,plots)
        plt.tight_layout(pad=2.5, w_pad=2.5, h_pad=2.5, rect=[0, 0.03, 1, 0.95])
        n=1
        for var in flowhists['nominal'][flow]:
            plt.subplot(np.ceil((plots+1)/2),2,n, label=flow+var)
            n+=1
            if 'faulty' in flowhists:
                a, = plt.plot(list(flowhists['faulty'][flow][var].keys()), list(flowhists['faulty'][flow][var].values()), color='r')
                c = plt.axvline(x=time, color='k')
            b, =plt.plot(list(flowhists['nominal'][flow][var].keys()), list(flowhists['nominal'][flow][var].values()), color='b')
            plt.title(var)
        if 'faulty' in flowhists:
            plt.subplot(np.ceil((plots+1)/2),2,n, label=flow+'legend')
            plt.legend([a,b],['faulty', 'nominal'])
        fig.suptitle('Dynamic Response of '+flow+' to fault'+' '+fault)
        plt.show()

#plotghist
# displays plots of the graph over time
# inputs:
#   - ghist, a dictionary of the history of the graph over time with structure:
#       {time: graphobject}, where
#           - time is the time where the snapshot of the graph was recorded
#           - graphobject is the snapshot of the graph at that time
#    - faultscen, the name of the fault scenario where this graph occured
def plotghist(ghist,faultscen=[]):
    for time, graph in ghist.items():
        showgraph(graph, faultscen, time)

#showgraph
# plots a single graph at a single time
# inputs:
#   - g, the graph object
#   - faultscen, the name of the fault scenario (for the title)
#   - time, the time of the fault scenario (also for the title)
#   - showfaultprops, whether to list the faults occuring on functions and list degraded flows
#       #(only works well for relatively simple models)
def showgraph(g, faultscen=[], time=[], showfaultlabels=True):
    labels=dict()
    for edge in g.edges:
        flows=list(g.get_edge_data(edge[0],edge[1]).keys())
        labels[edge[0],edge[1]]=''.join(flow for flow in flows)
    
    pos=nx.shell_layout(g)
    #Add ability to label modes/values
    
    nx.draw_networkx(g,pos,node_size=2000,node_shape='s', node_color='g', \
                     width=3, font_weight='bold')
    nx.draw_networkx_edge_labels(g,pos,edge_labels=labels)
    
    if list(g.nodes(data='status'))[0][1]:
        statuses=dict(g.nodes(data='status', default='Nominal'))
        faultnodes=[node for node,status in statuses.items() if status=='Faulty']
        degradednodes=[node for node,status in statuses.items() if status=='Degraded']
        
        nx.draw_networkx_nodes(g, pos, nodelist=degradednodes,node_color = 'y',\
                          node_shape='s',width=3, font_weight='bold', node_size = 2000)
        nx.draw_networkx_nodes(g, pos, nodelist=faultnodes,node_color = 'r',\
                          node_shape='s',width=3, font_weight='bold', node_size = 2000)
        
        
        faultedges = [edge for edge in g.edges if any([g.edges[edge][flow]['status']=='Degraded' for flow in g.edges[edge]])]
        faultflows = {edge:''.join([' ',''.join(flow+' ' for flow in g.edges[edge] if g.edges[edge][flow]['status']=='Degraded')]) for edge in faultedges}
        nx.draw_networkx_edges(g,pos,edgelist=faultedges, edge_color='r', width=2)
        
        if showfaultlabels:
            faults=dict(g.nodes(data='modes', default={'nom'}))
            faultlabels = {node:''.join(['\n\n ',''.join(f+' ' for f in fault if f!='nom')]) for node,fault in faults.items() if fault!={'nom'}}
            nx.draw_networkx_labels(g, pos, labels=faultlabels, font_size=12, font_color='k')
            nx.draw_networkx_edge_labels(g,pos,edge_labels=faultflows, font_color='r')
            
    
    if faultscen:
        plt.title('Propagation of faults to '+faultscen+' at t='+str(time))
    
    plt.show()

#printresult (maybe find a better name?)
# prints the results of a run in a nice FMEA-style table
# inputs:
#   - function: the function the mode occured in
#   - mode: the mode of the scenario
#   - time: the time the fault occured in
#   - endresult: the results dict given by the model after propagation
def printresult(function, mode, time, endresult):
    
    #FUNCTION  | MODE  | TIME  | FAULT EFFECTS | FLOW EFFECTS |  RATE  |  COST  |  EXP COST
    vals=  [[function],[mode],[time], [str(list(endresult['faults'].keys()))], \
            [str(list(endresult['flows'].keys()))] ,\
            [endresult['classification']['rate']], \
            [endresult['classification']['cost']],[endresult['classification']['expected cost']]]
    cnames=['Function', 'Mode', 'Time', 'End Faults', 'End Flow Effects', 'Rate', 'Cost', 'Expected Cost']
    t = Table(vals, names=cnames)
    return t

def showbipartite(g, scale=1, faultscen=[], time=[], showfaultlabels=True):
    labels={node:node for node in g.nodes}
    nodesize=scale*700
    fontsize=scale*6
    pos=nx.spring_layout(g)
    nx.draw(g, pos, labels=labels,font_size=fontsize, node_size=nodesize,node_color = 'g', font_weight='bold')
    if list(g.nodes(data='status'))[0][1]:
        nx.draw(g, pos, labels=labels,font_size=fontsize, node_size=nodesize, font_weight='bold')
        statuses=dict(g.nodes(data='status', default='Nominal'))
        faultnodes=[node for node,status in statuses.items() if status=='Faulty']
        degradednodes=[node for node,status in statuses.items() if status=='Degraded']
        nx.draw_networkx_nodes(g, pos, nodelist=degradednodes,node_color = 'y',\
                          font_weight='bold', node_size = nodesize)
        nx.draw_networkx_nodes(g, pos, nodelist=faultnodes,node_color = 'r',\
                          font_weight='bold', node_size = nodesize)
        if showfaultlabels:
            faults=dict(g.nodes(data='modes', default={'nom'}))
            faultlabels = {node:''.join(['\n\n ',''.join(f+' ' for f in fault if f!='nom')]) for node,fault in faults.items() if fault!={'nom'}}
            nx.draw_networkx_labels(g, pos, labels=faultlabels, font_size=fontsize, font_color='k')
    if faultscen:
        plt.title('Propagation of faults to '+faultscen+' at t='+str(time))
    plt.show()


## FAULT PROPAGATION

#constructnomscen
# creates a nominal scenario nomscen given a graph object g by setting all function modes to nominal
def constructnomscen(mdl):
    nomscen={'faults':{},'properties':{}}
    for fxnname in mdl.fxns:
        nomscen['faults'][fxnname]='nom'
    nomscen['properties']['time']=0.0
    nomscen['properties']['type']='nominal'
    return nomscen

#runnominal
# runs the model over time in the nominal scenario
# inputs:
#   - mdl, the python model module set up in mdl.py
#   - track, the flows to track (a list of strings)
#   - gtrack, the times to snapshot the graph
# outputs:
#   - endresults, a dictionary summary of results at the end of the simulation with structure
#    {flows:{flow:attribute:value},faults:{function:{faults}}, classification:{rate:val, cost:val, expected cost: val} }
#   - resgraph, a graph object with function faults and degraded flows noted
#   - flowhist, a dictionary with the history of the flow over time
#   - graphhist, a dictionary of results graph objects over time with structure {time:graph}
def runnominal(mdl, track={}, gtrack={}, gtype='normal'):
    nomscen=constructnomscen(mdl)
    scen=nomscen.copy()
    flowhist, graphhist, _ =proponescen(mdl, scen, track, gtrack, gtype=gtype)
    
    resgraph = mdl.returnstategraph(gtype)   
    endfaults, endfaultprops = mdl.returnfaultmodes()
    endflows={}
    endclass=mdl.findclassification(resgraph, endfaultprops, endflows, scen)
    
    endresults={'flows': endflows, 'faults': endfaults, 'classification':endclass}
    
    mdl.reset()
    return endresults, resgraph, flowhist, graphhist

#proponefault
# runs the model given a single function and fault mode
# inputs:
#   - mdl, the python model module set up in mdl.py
#   - fxnname, the function the fault is initiated in
#   - faultmode, the mode to initiate
#   - time, the time when the mode is to be initiated
#   - track, the flows to track (a list of strings)
#   - gtrack, the times to snapshot the graph
# outputs:
#   - endresults, a dictionary summary of results at the end of the simulation with structure
#    {flows:{flow:attribute:value},faults:{function:{faults}}, classification:{rate:val, cost:val, expected cost: val} }
#   - resgraph, a graph object with function faults and degraded flows noted
#   - flowhist, a dictionary with the history of the flow over time
#   - graphhist, a dictionary of results graph objects over time with structure {time:graph}
def runonefault(mdl, fxnname, faultmode, time=0, track={}, gtrack={},graph={}, staged=False, gtype='normal'):
    
    #run model nominally, get relevant results
    nomscen=constructnomscen(mdl)
    if staged:
        nomflowhist, nomgraphhist, mdls = proponescen(mdl, nomscen, track, gtrack, ctimes=[time])
        nomresgraph = mdl.returnstategraph(gtype)
        mdl.reset()
        mdl = mdls[time]
    else:
        nomflowhist, nomgraphhist, _ = proponescen(mdl, nomscen, track, gtrack)
        nomresgraph = mdl.returnstategraph(gtype)
        mdl.reset()
    #run with fault present, get relevant results
    scen=nomscen.copy() #note: this is a shallow copy, so don't define it earlier
    scen['faults'][fxnname]=faultmode
    scen['properties']['type']='single fault'
    scen['properties']['function']=fxnname
    scen['properties']['fault']=faultmode
    scen['properties']['rate']=mdl.fxns[fxnname].faultmodes[faultmode]['rate']
    scen['properties']['time']=time
    
    faultflowhist, faultgraphhist, _ = proponescen(mdl, scen, track, gtrack, staged=staged, prevhist=nomflowhist, prevghist=nomgraphhist)
    faultresgraph = mdl.returnstategraph(gtype)
    
    #process model run
    endfaults, endfaultprops = mdl.returnfaultmodes()
    endflows = comparegraphflows(faultresgraph, nomresgraph, gtype) 
    
    endclass = mdl.findclassification(faultresgraph, endfaultprops, endflows, scen)
    if gtype=='normal': resgraph = makeresultsgraph(faultresgraph, nomresgraph)
    elif gtype=='bipartite': resgraph = makebipresultsgraph(faultresgraph, nomresgraph)
    resgraphhist = makeresultsgraphs(faultgraphhist, nomgraphhist, gtype)
    
    flowhist={'nominal':nomflowhist, 'faulty':faultflowhist}
    
    endresults={'flows': endflows, 'faults': endfaults, 'classification':endclass}  
    
    mdl.reset()
    return endresults,resgraph, flowhist, resgraphhist

#listinitfaults
# creates a list of single-fault scenarios for the graph, given the modes set up in the fault model
# inputs: model graph, a vector of times for the scenarios to occur
# outputs: a list of fault scenarios, where a scenario is defined as:
#   {faults:{functions:faultmodes}, properties:{(changes depending scenario type)} }
def listinitfaults(mdl):
    faultlist=[]
    for time in mdl.times:
        for fxnname, fxn in mdl.fxns.items():
            modes=fxn.faultmodes
            
            for mode in modes:
                nomscen=constructnomscen(mdl)
                newscen=nomscen.copy()
                newscen['faults'][fxnname]=mode
                rate=mdl.fxns[fxnname].faultmodes[mode]['rate']
                newscen['properties']={'type': 'single-fault', 'function': fxnname, 'fault': mode, 'rate': rate, 'time': time}
                faultlist.append(newscen)

    return faultlist

#proplist
# creates and propagates a list of failure scenarios in a model
# input: mdl, the module where the model was set up
# output: resultstab, a FMEA-style table of results
def runlist(mdl, reuse=False, staged=False):
    
    if reuse and staged:
        print("invalid to use reuse and staged options at the same time. Using staged")
        reuse=False

    scenlist=listinitfaults(mdl)
    resultsdict={} 
    
    numofscens=len(scenlist)
    
    fxns=np.zeros(numofscens, dtype='S25')
    modes=np.zeros(numofscens, dtype='S25')
    times=np.zeros(numofscens, dtype=int)
    floweffects=['']*numofscens
    faulteffects=['']*numofscens
    rates=np.zeros(numofscens, dtype=float)
    costs=np.zeros(numofscens, dtype=float)
    expcosts=np.zeros(numofscens, dtype=float)
    
    #run model nominally, get relevant results
    nomscen=constructnomscen(mdl)
    if staged:
        nomflowhist, nomgraphhist, c_mdl = proponescen(mdl, nomscen, {}, {}, ctimes=mdl.times)
    else:
        nomflowhist, nomgraphhist, c_mdl = proponescen(mdl, nomscen, {}, {})
    nomresgraph = mdl.returnstategraph()
    mdl.reset()
    
    for i, scen in enumerate(scenlist):
        #run model with fault scenario
        if staged:
            mdl=c_mdl[scen['properties']['time']].copy()
            endresults, resgraph, _ =proponescen(mdl, scen, {}, {}, staged=True)
        else:
            endresults, resgraph, _ =proponescen(mdl, scen, {}, {})
        endfaults, endfaultprops = mdl.returnfaultmodes()
        resgraph = mdl.returnstategraph()
        
        endflows = comparegraphflows(resgraph, nomresgraph)
        endclass = mdl.findclassification(resgraph, endfaultprops, endflows, scen)
        if reuse: mdl.reset()
        elif staged: _
        else: mdl = mdl.__class__()
        #populate columns for results table
        fxns[i]=scen['properties']['function']
        modes[i]=scen['properties']['fault']
        times[i]=scen['properties']['time']
        floweffects[i] = str(endflows)
        faulteffects[i] = str(endfaults)        
        rates[i]=endclass['rate']
        costs[i]=endclass['cost']
        expcosts[i]=endclass['expected cost']
    #create results table
    vals=[fxns, modes, times, faulteffects, floweffects, rates, costs, expcosts]
    cnames=['Function', 'Mode', 'Time', 'End Faults', 'End Flow Effects', 'Rate', 'Cost', 'Expected Cost']
    resultstab = Table(vals, names=cnames)
    
    return resultstab

#proponescen
# runs a single fault scenario in the model over time
# inputs:
#   - mdl, the model object 
#   - scen, the fault scenario for a given model
#   - track, a list of flows to track
#   - gtrack, the times to take a snapshot of the graph 
#   - staged, the starting time for the propagation
#   - ctimes, the time to copy the models 
# outputs:
#   - flowhist, a dictionary with the history of the flow over time
#   - graphhist, a dictionary of results graph objects over time with structure {time:graph}
#   (note, this causes changes in the model of interest, also)
#   - c_mdls, copies of the model object taken at each time listed in ctime
def proponescen(mdl, scen, track={}, gtrack={}, staged=False, ctimes=[], prevhist={}, prevghist={}, gtype='normal'):
    #if staged, we want it to start a new run from the starting time of the scenario,
    # using a copy of the input model (which is the nominal run) at this time
    if staged:
        timerange=range(scen['properties']['time'], mdl.times[-1]+1, mdl.tstep)
        flowhist=copy.deepcopy(prevhist)
        graphhist=copy.deepcopy(prevghist)
    else: 
        timerange= range(mdl.times[0], mdl.times[-1]+1, mdl.tstep) 
        # initialize dict of tracked flows
        flowhist={}
        graphhist=dict.fromkeys(gtrack)
        if track:
            for flowname in track:
                    flowhist[flowname]=mdl.flows[flowname].status()
                    for var in flowhist[flowname]:
                        flowhist[flowname][var]={i:[] for i in timerange}
    # run model through the time range defined in the object
    nomscen=constructnomscen(mdl)
    c_mdl=dict.fromkeys(ctimes)
    flowstates={}
    for rtime in timerange:
       # inject fault when it occurs, track defined flow states and graph
        if rtime==scen['properties']['time']: flowstates = propagate(mdl, scen['faults'], rtime, flowstates)
        else: flowstates = propagate(mdl,nomscen['faults'],rtime, flowstates)
        if track:
            for flowname in track:
                for var in flowstates[flowname]:
                    flowhist[flowname][var][rtime]=flowstates[flowname][var]
        if rtime in gtrack: graphhist[rtime]=mdl.returnstategraph(gtype)
        if rtime in ctimes: c_mdl[rtime]=mdl.copy()
    return flowhist, graphhist, c_mdl

#propogate
# propagates faults through the graph at one time-step
# inputs:
#   g, the graph object of the model
#   initfaults, the faults (or lack of faults) to initiate in the model
#   time, the time propogation occurs at
#   flowstates, if generated in the last iteration
def propagate(mdl, initfaults, time, flowstates={}):
    #set up history of flows to see if any has changed
    n=0
    activefxns=mdl.timelyfxns.copy()
    nextfxns=set()
    #Step 1: Find out what the current value of the flows are (if not generated in the last iteration)
    if not flowstates:
        for flowname, flow in mdl.flows.items():
            flowstates[flowname]=flow.status()
    #Step 2: Inject faults if present     
    for fxnname in initfaults:
        if initfaults[fxnname]!='nom':
            fxn=mdl.fxns[fxnname]
            fxn.updatefxn(faults=[initfaults[fxnname]], time=time)
            activefxns.update([fxnname])
    #Step 3: Propagate faults through graph
    while activefxns:
        for fxnname in list(activefxns).copy():
            #Update functions with new values, check to see if new faults or states
            oldstates, oldfaults = mdl.fxns[fxnname].returnstates()
            mdl.fxns[fxnname].updatefxn(time=time)
            newstates, newfaults = mdl.fxns[fxnname].returnstates() 
            if oldstates != newstates or oldfaults != newfaults: nextfxns.update([fxnname])
        #Check to see what flows have new values and add connected functions
        for flowname, flow in mdl.flows.items():
            if flowstates[flowname]!=flow.status():
                nextfxns.update(set([n for n in mdl.bipartite.neighbors(flowname)]))
            flowstates[flowname]=flow.status()
        activefxns=nextfxns.copy()
        nextfxns.clear()
        n+=1
        if n>1000: #break if this is going for too long
            print("Undesired looping in function")
            print(initfaults)
            print(fxnname)
            break
    return flowstates

#updatemdlhist
# find a way to make faster (e.g. by automatically getting values by reference)
def updatemdlhist(mdl, mdlhist, t):
    updateflowhist(mdl, mdlhist, t)
    updatefxnhist(mdl, mdlhist, t)
def updateflowhist(mdl, mdlhist, t):
    for flowname, flow in mdl.flows.items():
        atts=flow.status()
        for att, val in atts.items():
            mdlhist["flows"][flowname][att][t] = val
def updatefxnhist(mdl, mdlhist, t):
    for fxnname, fxn in mdl.fxns.items():
        states, faults = fxn.returnstates()
        mdlhist["flows"][fxnname]["faults"][t]=faults
        for state, value in states.items():
            mdlhist["functions"][fxnname][state][t] = value 

#initmdlhist
# initialize history of model
def initmdlhist(mdl, timerange):
    mdlhist={}
    mdlhist["flows"]=initflowhist(mdl, timerange)
    mdlhist["functions"]=initfxnhist(mdl, timerange)
    mdlhist["time"]=[i for i in timerange]
    return mdlhist
def initflowhist(mdl, timerange):
    flowhist={}
    for flowname, flow in mdl.flows.items():
        atts=flow.status()
        flowhist[flowname] = {}
        for att, val in atts.items():
            flowhist[flowname][att] = [val for i in timerange]
    return flowhist
def initfxnhist(mdl, timerange):
    fxnhist = {}
    for fxnname, fxn in mdl.fxns.items():
        states, faults = fxn.returnstates()
        fxnhist[fxnname]={}
        fxnhist[fxnname]["faults"]=[faults for i in timerange]
        for state, value in states.items():
            fxnhist[fxnname][state] = [value for i in timerange]
    return fxnhist

#makehisttable
# put history in a tabular format
def makehisttable(mdlhist):
    df = pd.DataFrame()
    label = ("Time", "t")
    labels= [label]
    df[label]=mdlhist["time"]
    for flow, atts in mdlhist["flows"].items():
        for att, val in atts.items():
            label=(flow,att)
            labels=labels+[label]
            df[label]=val
    for fxn, atts in mdlhist["functions"].items():
        for att, val in atts.items():
            label=(fxn, att)
            labels=labels+[label]
            df[label]=val
    
    index = pd.MultiIndex.from_tuples(labels)
    df = df.reindex(index, axis="columns")
    return df
            

#makeresultsgraph
# creates a snapshot of the graph structure with model results superimposed
# inputs: g, the graph, and nomg, the graph in its nominal state
# outputs: rg, the graph snapshot
def makeresultsgraph(g, nomg):
    rg=g.copy() 
    for edge in g.edges:
        for flow in list(g.edges[edge].keys()):            
            if g.edges[edge][flow]!=nomg.edges[edge][flow]: status='Degraded'
            else:                               status='Nominal' 
            rg.edges[edge][flow]={'values':g.edges[edge][flow],'status':status}
    for node in g.nodes:        
        if g.nodes[node]['modes'].difference(['nom']): status='Faulty' 
        elif g.nodes[node]['states']!=nomg.nodes[node]['states']: status='Degraded'
        else: status='Nominal'
        rg.nodes[node]['status']=status
    return rg
def makebipresultsgraph(g, nomg):
    rg=g.copy() 
    for node in g.nodes:        
        if g.nodes[node]['bipartite']==0: #condition only checked for functions
            if g.nodes[node].get('modes').difference(['nom']): status='Faulty'
            else: status='Nominal'
        elif g.nodes[node]['states']!=nomg.nodes[node]['states']: status='Degraded'
        else: status='Nominal'
        rg.nodes[node]['status']=status
    return rg

def makeresultsgraphs(ghist, nomghist, gtype='normal'):
    rghist = dict.fromkeys(ghist.keys())
    for i,rg in rghist.items():
        if gtype=='normal': rghist[i] = makeresultsgraph(ghist[i],nomghist[i])
        elif  gtype=='bipartite': rghist[i] = makebipresultsgraph(ghist[i],nomghist[i])
    return rghist

#comparegraphflows
# extracts non-nominal flows by comparing the a results graph with a nominal results graph
# inputs:   g, a graph of results, with states of each flow in each provided
#           nomg, the same graph for the nominal system
# outputs:  endflows, a dictionary of degraded flows
# (maybe do this for values also???)
def comparegraphflows(g, nomg, gtype='normal'):
    endflows=dict()
    if gtype=='normal':
        for edge in g.edges:
            flows=g.get_edge_data(edge[0],edge[1])
            nomflows=nomg.get_edge_data(edge[0],edge[1])
            for flow in flows:
                if flows[flow]!=nomflows[flow]:
                    endflows[flow]={}
                    vals=flows[flow]
                    for val in vals:
                        if vals[val]!=nomflows[flow][val]: endflows[flow][val]=flows[flow][val]
    elif gtype=='bipartite':
        for node in g.nodes:
            if g.nodes[node]['bipartite']==1: #only flow states
                if g.nodes[node]['states']!=nomg.nodes[node]['states']:
                    endflows[node]={}
                    vals=g.nodes[node]['states']
                    for val in vals:
                        if vals[val]!=nomg.nodes[node]['states'][val]: endflows[node][val]=vals[val]     
    return endflows

        
            



    
    
    
    
