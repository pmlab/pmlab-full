import copy
from collections import defaultdict, namedtuple, deque
from .. log import Log, EnhancedLog

from matplotlib.pyplot import show
from hcluster import pdist, linkage, dendrogram

import numpy
from numpy.random import rand
from numpy import zeros
from pandas import DataFrame
from pylab import plot,show
from scipy.cluster.vq import kmeans,vq

def random_balanced_clusters(log, clusters=2):
    """Returns a list of logs obtained from [log] by random
    balancing clustering. 
    
    Actually the order is not random but follows the original log order. Works
    with plain and enhanced logs."""
    enhanced = isinstance(log,EnhancedLog)
    cases = log.get_cases(True) if enhanced else log.get_cases()
    LogClass = EnhancedLog if enhanced else Log
    base_size = len(cases)/clusters
    cluster_sizes = [base_size]*clusters
    for i in xrange(len(cases)%clusters):
        cluster_sizes[i] += 1
    print 'Generating', clusters, 'clusters with sizes:'
    print cluster_sizes
    current_case = 0
    logs = []
    for cluster, size in enumerate(cluster_sizes):
        new_log = LogClass(cases=copy.deepcopy(cases[current_case:current_case+size]))
        logs.append(new_log)
        current_case += size
    return logs

TreeNode = namedtuple('TreeNode','cases sons selectable_act')

def optional_clusters(log, threshold):
    """Returns n clusters such that they all have a size less than threshold by 
    splitting cases that contain and do not contain a particular activity. The
    activity chosen is the one that gives the more balanced splitting. If no
    splitting activity is available, then the cluster is not further split, 
    regardless of its size."""
    cases = log.get_uniq_cases().items()
    cases_per_activity = log.cases_per_activity(uniq_cases=True)
    all_cases = set(range(len(cases)))
    all_activities = cases_per_activity.keys()
    selectable_act = [act for act in all_activities 
                    if len(cases_per_activity[act]) not in [0, len(all_cases)]]
    splits = []
    tree_nodes = [TreeNode(all_cases,[], selectable_act),]
    nodes_to_expand = deque([0])
    leafs = []
    while len(nodes_to_expand) > 0:
        #split current node if it is above threshold an there are selectable activities
        current_node = nodes_to_expand.pop()
        tn = tree_nodes[current_node]
        #print tn
        if (len(tn.cases) <= threshold or 
            len(tn.selectable_act) == 0):
            leafs.append(tn)
            continue
        print 'Expanding node', current_node, 'of size', len(tn.cases)
        #selecting most balanced split
        dif_sizes = [(act,abs(len(tn.cases&cases_per_activity[act]) - len(tn.cases)/2)) 
                        for act in tn.selectable_act]
        sorted_size = sorted(dif_sizes,key = lambda x: x[1])
        selected_act = sorted_size[0][0]
        cases_son1 = tn.cases&cases_per_activity[selected_act]
        cases_son2 = tn.cases-cases_son1
        print "Splitting using activity '{0}' that appears in {1} cases".format(selected_act,len(cases_son1))
        tn.sons.append(len(tree_nodes))
        tn.sons.append(len(tree_nodes)+1)
        selectable1 = [act for act in tn.selectable_act 
                        if len(cases_son1&cases_per_activity[act]) not in [0,len(cases_son1)]]
        selectable2 = [act for act in tn.selectable_act 
                        if len(cases_son2&cases_per_activity[act]) not in [0,len(cases_son2)]]
        tree_nodes.append( TreeNode(cases_son1, [], selectable1) )
        tree_nodes.append( TreeNode(cases_son2, [], selectable2) )
        nodes_to_expand.append( tn.sons[0] )
        nodes_to_expand.append( tn.sons[1] )
    print 'Generating', len(leafs), 'clusters'
    logs = []
    for node in leafs:
        cluster_cases = defaultdict(int)
        for c in node.cases:
            cluster_cases[cases[c][0]] = cases[c][1]
        new_log = Log(uniq_cases=cluster_cases)
        logs.append(new_log)
    return logs

def max_alphabet_clusters(log, threshold):
    """Creates n clusters. The first n-1 contain cases such that the
    alphabet of the log is below [threshold]. The last one contains all 
    remaining cases."""
    cases = log.get_cases()
    alphabets = []
    wholeAlphabet = set()
    for case in cases:
        alphabet = set(case)
        alphabets.append( alphabet )
        wholeAlphabet.update( alphabet )
    print "Complete alphabet has",len(wholeAlphabet),"elements"
    unassigned = set(range(len(alphabets)))
    logs = []
    while True:
        #take smallest alphabet in unassigned
        (index,alph) = min((len(e[1]), e) for e in [(i,alphabets[i]) for i in unassigned])[1]
        if len(alph) > threshold:
            print "#Remaining", len(unassigned),"cases have alphabets greater than the threshold"
            break
        #find all traces with same alphabet, and the one that yields smaller alphabet increment
        unassigned.remove( index )
        cluster = [index]
        print (index, alph)
        while True:
            differences = [(i,alphabets[i]-alph) for i in unassigned]
            mindif = len(wholeAlphabet)
            d_index=None
            for e in differences:
                if len(e[1]) == 0:
                    cluster.append(e[0])
                    unassigned.remove( e[0] )
                elif len(e[1]) < mindif:
                    #print "Prev min", mindif, "Prev index", d_index
                    mindif = len(e[1])
                    d_index = e[0]
                    d_alph = e[1]
                    #print "New min", mindif,"New idx",d_index
            #d_alph = alphabets[d_index]
            #print "selected with index", d_index, "and alphabet",d_alph
            #(d_index,d_alph) = min((len(e[1]), e) for e in differences)[1]
            if len(d_alph)+len(alph) > threshold:
                break
            cluster.append(d_index)
            alph |= d_alph
            #print "current alphabet",alph
            unassigned.remove( d_index )
        print "#Cluster found with",len(cluster),"cases with alphabet size",len(alph)

        cluster_cases = [cases[i] for i in cluster]
        logs.append(Log(cases=cluster_cases))
    #final cluster
    garbage_cases = [cases[i] for i in unassigned]
    logs.append(Log(cases=garbage_cases))
    return logs

def xor_activities_clusters( log ):
    """Splits in clusters selecting a pair of mutually exclusive activities.
    Produces three logs: one containing all the cases in which the first 
    exclusive activity appears, the second containing all the cases of the 
    second activity, and the last one containing all the cases in which none of
    the previous activities appears."""
    cases = log.get_cases()
    cases_per_activity = log.cases_per_activity()
    all_cases = set(range(len(cases)))
    all_activities = cases_per_activity.keys()
    splits = []
    for i, act1 in enumerate(all_activities):
        for j in range(i+1,len(all_activities)):
            #print i, j
            act2 = all_activities[j]
            t1 = cases_per_activity[act1]
            t2 = cases_per_activity[act2]
            intersection = t1 & t2
            if len(intersection) == 0:
                print 'Candidates',act1,'and',act2
                #order
                if sorted(t1)[0] < sorted(t2)[0]:
                    tup = (t1,t2,act1,act2)
                else:
                    tup = (t2,t1,act2,act1)
                if tup not in splits:
                    splits.append(tup)
    #sort splits, use the one involving more traces
    #print splits
    max_traces = 0
    max_split = 0
    for i, tup in enumerate(splits):
        val = len(tup[0])+len(tup[1])
        if max_traces < val:
            max_traces = val
            max_split = i
    #split
    print ("Splitting using activities '{0}' ({1} cases) "
        "and '{2}' ({3} cases)").format(splits[max_split][2],
                                        len(splits[max_split][0]),
                                        splits[max_split][3],
                                        len(splits[max_split][1]))
    logs = []
    for cluster in range(2):
        logs.append( Log(cases=[cases[t] for t in splits[max_split][cluster]]) )
    #remainder cluster
    remaining_cases = all_cases - splits[max_split][0] - splits[max_split][1]
    logs.append( Log(cases=[cases[t] for t in remaining_cases]) )
    return logs

def hierarchical_clusters( log, show_plot=None ):
    """Translates traces to Parikh vectors and computes in the vector space
       a hierarchical clustering."""
    def get_parikh(case,alphabet):
        v = zeros(len(alphabet),dtype=int)
        for act in case:
            v[alphabet[act]] = v[alphabet[act]] +1
        # canonical representation
        m = min(v)
        return v - m   
    
    actsind = {}
    i = 0
    for act in log.get_alphabet():
        actsind[act] = i
        i = i +1

    uniq_cases = log.get_uniq_cases()
    N = len(uniq_cases)
    M = len(actsind)
    data = zeros((N,M),dtype=int)
    i = 0
    parikhdict = {}
    for case in uniq_cases.keys():
        data[i] = get_parikh(case,actsind)
        str_i = ','.join(map(str,data[i]))
        if str_i not in parikhdict:
            parikhdict[str_i] = [i]
        else:
            parikhdict[str_i].append(i)
        i = i + 1
    df = DataFrame(data)
    data_uniq = df.drop_duplicates()
    Y = pdist(data_uniq,metric='euclidean')
    Z = linkage(Y,method='average')
    dendrogram(Z)
    show()
 

def similarity_clusters( log, show_plot=None ):
    """Translates traces to Parikh vectors and computes in the vector space
       a K-means clustering."""
    
    def get_parikh(case,alphabet):
        v = zeros(len(alphabet),dtype=int)
        for act in case:
            v[alphabet[act]] = v[alphabet[act]] +1
        return v    
    
    actsind = {}
    i = 0
    for act in log.alphabet:
        actsind[act] = i
        i = i +1

    uniq_cases = log.get_uniq_cases()
    N = len(uniq_cases)
    M = len(actsind)
    data = zeros((N,M),dtype=int)
    i = 0
    for case in uniq_cases.keys():
        data[i] = get_parikh(case,actsind)
        i = i + 1
    print data
#    data = vstack((rand(150,2) + array([.5,.5]),rand(150,2)))
    # computing K-Means with K = 2 (2 clusters)
    centroids,_ = kmeans(data,2)
    # assign each sample to a cluster
    idx,_ = vq(data,centroids)

    # some plotting using numpy's logical indexing
#    plot(data[idx==0,0],data[idx==0,1],'ob',
#     data[idx==1,0],data[idx==1,1],'or')
    plot(data[idx==0],'ob',data[idx==1],'or')
    plot(centroids[:,0],centroids[:,1],'sg',markersize=8)
    show()  
    return data
    
    
 
            
