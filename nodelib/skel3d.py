from pyqtgraph.flowchart.library.common import CtrlNode
from pyqtgraph.flowchart import Node

from PyQt5.QtWidgets import QWidget

from skel3d.util import MAHelper, MAHelper_ma_io_arrays, MAHelper_ma_arrays, MAHelper_s_arrays
MAHelper_arrays = MAHelper_ma_arrays + MAHelper_s_arrays
from skel3d.io import npy
from skel3d.clustering import get_clusters, classify_cluster, CLASSDICT

import numpy as np

class maReaderNode(Node):
    nodeName = 'maReader'

    def __init__(self, name):
        Node.__init__(self, name, allowAddOutput=False, terminals={
            'path': {'io':'in'},
            'datadict': {'io':'out'},
            'coords': {'io':'out'},
            'normals': {'io':'out'},
            'colors': {'io':'out'},
            'clusters': {'io':'out'},
            'segment_graph': {'io':'out'}
        })

    def process(self, path, display=True):
        datadict = npy.read(path)
        # mah = MAHelper(datadict)
        # data_arrays = {}
        # for key in mah.arrays: data_arrays[key] = mah.D[key]
        clusters = None
        segment_graph = None
        if 'ma_clusters' in datadict:
            clusters = datadict['ma_clusters']
        if 'ma_segment_graph' in datadict:
            segment_graph = datadict['ma_segment_graph']

        coords = normals = colors = None
        if 'coords' in datadict:
            coords = datadict['coords']
        if 'normals' in datadict:
            normals = datadict['normals']
        if 'colors' in datadict:
            colors = datadict['colors']

        return {
            'datadict': datadict,
            'coords': coords,
            'normals': normals,
            'colors': colors,
            'clusters': clusters,
            'segment_graph': segment_graph
        }

class maWriterNode(Node):
    nodeName = 'maWriter'

    def __init__(self, name):
        Node.__init__(self, name, allowAddOutput=False, terminals={
            'path': {'io':'in'},
            'datadict': {'io':'in'}
            # 'clusters': {'io':'in'},
            # 'segment_graph': {'io':'out'}
        })

    def process(self, path, datadict, display=True):
        # for key in datadict:
        #     w = QtGui.QCheckBox()
        datadict = npy.write(path, datadict, keys['ma_clusters'])

class maExpanderNode(Node):
    nodeName = 'maExpander'
    
    def __init__(self, name):
        ## Initialize node with only a single input terminal
        terminals={
            'datadict': {'io':'in'},
            'mah': {'io':'out'}
        }
        for key in MAHelper_arrays + MAHelper_ma_io_arrays:
            terminals[key] = {'io':'out'}
        Node.__init__(self, name, allowAddOutput=False, terminals=terminals)
        
    def process(self, datadict, display=True):
        assert(not datadict is None)
        if not hasattr(self, 'ma_hlpr'):
            self.ma_hlpr = MAHelper(datadict)
        out = {'mah':self.ma_hlpr}
        for key in MAHelper_arrays + MAHelper_ma_io_arrays:
            if key in self.ma_hlpr.D:
                out[key] = self.ma_hlpr.D[key]
        return out

class maMaskNode(Node):
    nodeName = 'maMask'
    
    def __init__(self, name):
        ## Initialize node with only a single input terminal
        terminals={
            'mah': {'io':'in'},
            'ma_idx': {'io':'in', 'multi':True}
        }
        for key in MAHelper_arrays:
            terminals[key] = {'io':'out'}
        Node.__init__(self, name, allowAddOutput=False, terminals=terminals)

        
    def process(self, mah, ma_idx=None, display=True):
        out = {}

        for key in MAHelper_arrays:
            if key in mah.D:
                out[key] = mah.f(list(ma_idx.values()), key)

        return out

class maClusterFinderNode(CtrlNode):
    nodeName = 'maClusterFinder'
    uiTemplate = [
        ('edge_cnt_threshold',  'doubleSpin', {'min':1, 'max':1000, 'value':20}),
        ('delete_high_degree_vs',  'intSpin', {'min':0, 'max':100, 'value':0})
    ]

    def __init__(self, name):
        CtrlNode.__init__(self, name, terminals={
            'ma_segment_graph': {'io':'in'},
            'mah': {'io':'in'},
            'clusters': {'io':'out'},
            'ma_segment': {'io':'out'}
        })

    def process(self, ma_segment_graph, mah, display=True):
        ecount = self.ctrls['edge_cnt_threshold'].value()
        hdvs = self.ctrls['delete_high_degree_vs'].value()
        get_clusters(mah, ecount, hdvs)

        return {
            'clusters':mah.D['ma_clusters'], 
            'ma_segment':mah.D['ma_segment']
        }
        

class maSelectorNode(CtrlNode):
    nodeName = 'maSelector'
    uiTemplate = [
        ('cluster_id',  'combo', {'values': ['All']}),
        ('sheet_id',  'combo', {'values': ['All']})
    ]

    # current_sheet = None
    current_cluster = None

    def __init__(self, name):
        CtrlNode.__init__(self, name, terminals={
            'clusters': {'io':'in'},
            'ma_idx': {'io':'out'},
            'cluster': {'io':'out'},
            'sheet': {'io':'out'}
        })

    def process(self, clusters, display=True):
        assert(not clusters is None)
        
        cluster_values = ['All']+['Cluster '+str(i) for i,c in enumerate(clusters)]

        cluster_cid = self.ctrls['cluster_id'].currentIndex()
        new_cluster = None
        if cluster_cid > 0:
            new_cluster = clusters[cluster_cid-1]
        
        sheet=None
        if (not new_cluster is None) and new_cluster == self.current_cluster: # we proceed to finding the shelected sheet in this cluster
            sheet_cid = self.ctrls['sheet_id'].currentIndex()
            if sheet_cid != 0:
                sheet = new_cluster.vs[sheet_cid-1]

        else: # we repopulate the sheet list and set it to 'All'
            sheet_values = ['All']
            if new_cluster is None:
                pass
                #sheet list remains ['All']
            else:
                sheet_values += ['Sheet '+str(c.index) for c in new_cluster.vs]
            oldstate = self.ctrls['sheet_id'].blockSignals(True)
            self.ctrls['sheet_id'].clear()
            self.ctrls['sheet_id'].insertItems(0, sheet_values)
            self.ctrls['sheet_id'].blockSignals(False)

        if not sheet is None:
            ma_idx = sheet['ma_idx']
        elif not new_cluster is None:
            ma_idx = np.concatenate(new_cluster.vs['ma_idx'])
        else:
            ma_idx = None

        oldstate = self.ctrls['cluster_id'].blockSignals(True)
        self.ctrls['cluster_id'].clear()
        self.ctrls['cluster_id'].insertItems(0, cluster_values)
        if cluster_cid == -1: cluster_cid = 0
        self.ctrls['cluster_id'].setCurrentIndex(cluster_cid)
        self.ctrls['cluster_id'].blockSignals(False)

        self.current_cluster = new_cluster

        return {
            'ma_idx': (ma_idx, 'ma'),
            'cluster': self.current_cluster,
            'sheet': sheet,
        }

class maClusterLineExpanderNode(Node):
    nodeName = 'maClusterLineExpander'
    
    def __init__(self, name):
        Node.__init__(self, name, terminals={
            'clusters': {'io':'in'},
            'start': {'io':'out'},
            'end': {'io':'out'},
            'n': {'io':'out'},
            'count': {'io':'out'},
            'classification': {'io':'out'}
        })

    def process(self, clusters):
        # l = len(clusters)
        # n = np.array(l, dtype=np.int32)
        # cnt = np.array(l, dtype=np.int32)
        if not type(clusters) is list:
            clusters = [clusters]
        n = []
        cnt = []
        classification = []
        start = []
        end = []
        for i, cluster in enumerate(clusters):
            for e in cluster.es:
                start.append(cluster.vs[e.source]['ma_coords_mean'])
                end.append(cluster.vs[e.target]['ma_coords_mean'])
                n.append(i)
                cnt.append(e['adj_count'])
                if 'classification' in cluster.attributes():
                    classification.append(cluster['classification'])

        if classification:
            classification = np.array(classification, dtype=np.int32)
        else:
            classification = None
        
        return {
            'start': np.array(start, dtype=np.float32),
            'end': np.array(end, dtype=np.float32),
            'n': np.array(n, dtype=np.int32),
            'count': np.array(cnt, dtype=np.int32),
            'classification': classification
        }

class maClusterClassifierNode(Node):
    nodeName = 'maClusterClassifier'

    def __init__(self, name):

        terminals={
            'clustersin': {'io':'in'},
            'mah': {'io':'in'},
            'clusters': {'io':'out'}
        }
        for classname in CLASSDICT.values():
            terminals[classname] = {'io':'out'}
        
        Node.__init__(self, name, terminals=terminals)

    def process(self, clustersin, mah, display=True):
        result = {'clusters':clustersin}
        for classname in CLASSDICT.values():
            result[classname] = []

        for cluster in clustersin:
            cluster, classification = classify_cluster(cluster, mah)
            result[CLASSDICT[classification]].append(cluster)

        return result#, 'classdict':classdict}

class maClusterLabeler(CtrlNode):
    nodeName = 'maClusterLabeler'

    uiTemplate = [
        ('label',  'combo', {'values': list(CLASSDICT.values())})
    ]

    def __init__(self, name):

        terminals={
            'clusteri': {'io':'in'},
            # 'mah': {'io':'in'},
            'clustero': {'io':'out'}
        }
        CtrlNode.__init__(self, name, terminals=terminals)

    def process(self, clusteri, display=True):
        # i = self.ctrls['label']
        self.ctrls['label'].setIndex(i)
        clusteri['classification'] = self.ctrls['label'].currentText()
        return {'clustero': clusteri}#, 'classdict':classdict}
