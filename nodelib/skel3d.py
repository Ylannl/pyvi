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
            'segment_graph': {'io':'out'},
            'seg_link_flip': {'io':'out'},
            'ma_segment_lidx': {'io':'out'},
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

        coords = normals = colors = seg_link_flip = ma_segment_lidx = None
        if 'coords' in datadict:
            coords = datadict['coords']
        if 'normals' in datadict:
            normals = datadict['normals']
        if 'colors' in datadict:
            colors = datadict['colors']
        if 'seg_link_flip' in datadict:
            seg_link_flip = datadict['seg_link_flip'].astype(np.int32)
        if 'ma_segment_lidx' in datadict:
            ma_segment_lidx = datadict['ma_segment_lidx']

        return {
            'datadict': datadict,
            'coords': coords,
            'normals': normals,
            'colors': colors,
            'clusters': clusters,
            'segment_graph': segment_graph,
            'seg_link_flip': seg_link_flip,
            'ma_segment_lidx': ma_segment_lidx
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
            'ma_idx': {'io':'in', 'multi':True},
            'pass_throughi': {'io':'in'},
            'pass_through': {'io':'out'}
        }
        for key in MAHelper_arrays:
            terminals[key] = {'io':'out'}
        Node.__init__(self, name, allowAddOutput=False, terminals=terminals)

        
    def process(self, mah, ma_idx=None, pass_throughi=None, display=True):
        out = {}

        for key in MAHelper_arrays:
            if key in mah.D:
                out[key] = mah.f(list(ma_idx.values()), key)

        if pass_throughi is None:
            out['pass_through'] = None
        else:    
            mah.D['pass_through'] = pass_throughi
            out['pass_through'] = mah.f(list(ma_idx.values()), 'pass_through')

        return out

class maSegmentGraphEnricherNode(Node):
    nodeName = 'maSegmentGraphEnricher'
    # uiTemplate = [
    #     ('delete_high_degree_vs',  'intSpin', {'min':0, 'max':100, 'value':0})
    # ]

    def __init__(self, name):
        Node.__init__(self, name, terminals={
            'gi': {'io':'in'},
            'mah': {'io':'in'},
            'go': {'io':'out'}
        })

    def process(self, gi, mah, display=True):
        for v in gi.vs:
            ma_idx = v['ma_idx']
            r = mah.D['ma_radii'][ma_idx]
            t = mah.D['ma_theta'][ma_idx]
            r_mi, r_ma, r_avg = np.nanmin(r), np.nanmax(r), np.nanmean(r)
            t_mi, t_ma = np.nanmin(t), np.nanmax(t)
            bz_avg = np.nanmean(mah.D['ma_bisec'][:,-1][ma_idx])
            v['r_min']=r_mi
            v['r_max']=r_ma
            v['r_avg']=r_avg
            v['t_min']=t_mi
            v['t_max']=t_ma
            v['bz_avg']=bz_avg

        return {
            'go':gi,
        }

class maClusterFinderNode(CtrlNode):
    nodeName = 'maClusterFinder'
    uiTemplate = [
        ('delete_high_degree_vs',  'intSpin', {'min':0, 'max':100, 'value':0}),
        ('del_flip', 'check', {'checked':True}),
        ('edge_cnt_threshold',  'intSpin', {'min':1, 'max':1000, 'value':20}),
        ('r_thres',  'doubleSpin', {'min':0, 'max':500, 'value':9}),
        ('theta_thres',  'doubleSpin', {'min':0, 'max':3.15, 'value':1})
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
        min_r = self.ctrls['r_thres'].value()
        max_t = self.ctrls['theta_thres'].value()
        del_flip = self.ctrls['del_flip'].checkState()>0
        get_clusters(mah, ecount, hdvs, min_r=min_r, max_theta=max_t, del_flip=del_flip)

        return {
            'clusters':mah.D['ma_clusters'], 
            'ma_segment':mah.D['ma_segment']
        }
        
# class maCluster2IDXNode(Node):
#     nodeName = 'maCluster2IDX'
#     # uiTemplate = [
#     #     ('delete_high_degree_vs',  'intSpin', {'min':0, 'max':100, 'value':0})
#     # ]

#     def __init__(self, name):
#         Node.__init__(self, name, terminals={
#             'clusters': {'io':'in'},
#             'mah': {'io':'in'},
#             'idx': {'io':'out'}
#         })

#     def process(self, gi, mah, display=True):
#         for v in gi.vs:
#             ma_idx = v['ma_idx']
#             r = mah.D['ma_radii'][ma_idx]
#             t = mah.D['ma_theta'][ma_idx]
#             r_mi, r_ma, r_avg = np.nanmin(r), np.nanmax(r), np.nanmean(r)
#             t_mi, t_ma = np.nanmin(t), np.nanmax(t)
#             bz_avg = np.nanmean(mah.D['ma_bisec'][:,-1][ma_idx])
#             v['r_min']=r_mi
#             v['r_max']=r_ma
#             v['r_avg']=r_avg
#             v['t_min']=t_mi
#             v['t_max']=t_ma
#             v['bz_avg']=bz_avg

#         return {
#             'go':gi,
#         }

class maSegmentLIDXEnricherNode(Node):
    nodeName = 'maSegmentLIDXEnricher'
    # uiTemplate = [
    #     ('delete_high_degree_vs',  'intSpin', {'min':0, 'max':100, 'value':0})
    # ]

    def __init__(self, name):
        Node.__init__(self, name, terminals={
            'mah': {'io':'in'},
            'seg_id_range': {'io':'out'},
            'stats': {'io':'out'}
        })

    def process(self, mah, display=True):
        stats = np.empty(len(mah.D['ma_segment_lidx'].values()), dtype=[('r_ma','f4'), ('t_avg','f4'), ('bz_avg','f4')])
        for i,ma_idx in enumerate(mah.D['ma_segment_lidx'].values()):
            r = mah.D['ma_radii'][ma_idx]
            t = mah.D['ma_theta'][ma_idx]
            r_mi, r_ma = np.nanmin(r), np.nanmax(r)
            # t_mi, t_ma = np.nanmin(t), np.nanmax(t)
            t_avg = np.nanmean(t)
            bz_avg = np.nanmean(mah.D['ma_bisec'][:,-1][ma_idx])
            # stats['r_mi'][i] = r_mi
            stats['r_ma'][i] = r_ma
            # stats['t_mi'][i] = t_mi
            # stats['t_ma'][i] = t_ma
            stats['t_avg'][i] = t_avg
            stats['bz_avg'][i] = bz_avg

        seg_id_range = (mah.D['ma_segment'].min(), mah.D['ma_segment'].max())
        return {
            'stats':stats,
            'seg_id_range':seg_id_range
        }


class maSegmentFiltererNode(CtrlNode):
    nodeName = 'maSegmentFilterer'
    uiTemplate = [
        ('min_maxr',  'doubleSpin', {'min':0, 'max':9999, 'value':0}),
        ('max_maxr',  'doubleSpin', {'min':0, 'max':9999, 'value':199}),
        ('min_avgt',  'doubleSpin', {'min':0, 'max':np.pi, 'value':0}),
        ('min_count',  'intSpin', {'min':0, 'max':9999, 'value':5}),
        ('pos_bzavg', 'check', {'checked':True})
        # ('max_t',  'doubleSpin', {'min':0, 'max':np.pi, 'value':np.pi})
        # ('minavg_theta',  'doubleSpin', {'min':0, 'max':np.pi, 'value':np.pi/5})
    ]

    def __init__(self, name):
        CtrlNode.__init__(self, name, terminals={
            'mah': {'io':'in'},
            'stats': {'io':'in'},
            'coords_values': {'io':'out'},
            'ma_idx': {'io':'out'}
        })

    def process(self, mah, stats, display=True):

        ma_idx = np.zeros(mah.m*2, dtype=np.bool)
        coords_values = -1*np.ones(mah.m, dtype=int)
        for i,(seg_id, idx) in enumerate(mah.D['ma_segment_lidx'].items()):
            f = True
            # f &= self.ctrls['min_r'].value() < stats['r_mi'][i] 
            f &= self.ctrls['min_maxr'].value() < stats['r_ma'][i] < self.ctrls['max_maxr'].value()
            f &= self.ctrls['min_avgt'].value() < stats['t_avg'][i] 
            f &= self.ctrls['min_count'].value() < len(idx)
            # f &= self.ctrls['max_t'].value() > stats['t_ma'][i] 
            if self.ctrls['pos_bzavg'].checkState()>0:
                f &= stats['bz_avg'][i] > 0
            if f:
                ma_idx[idx] = 1
                s_idx = mah.s_idx(idx)
                coords_values[s_idx] = seg_id
            # print(coords_values)

        return {'ma_idx':(ma_idx,'ma'), 'coords_values':coords_values}

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
            ma_idx = np.array(sheet['ma_idx'])
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

class maVertexPairLineExtractorNode(Node):
    nodeName='maVertexPairLineExtractor'

    def __init__(self, name):
        Node.__init__(self, name, terminals={
            'vpairs': {'io':'in'},
            'gi': {'io':'in'},
            'start': {'io':'out'},
            'end': {'io':'out'},
            'count': {'io':'out'}
        })
    def process(self, vpairs, gi, display=True):
        l = len(vpairs)
        start = np.zeros((l,3), dtype=np.float32)
        end = np.zeros((l,3), dtype=np.float32)
        i=0
        for s,e in vpairs[:,:2]:
            start[i] = gi.vs[s]['ma_coords_mean']
            end[i] = gi.vs[e]['ma_coords_mean']
            i+=1
        return {'start':start, 'end':end, 'count':vpairs[:,2]}

class maClusterINEXClassifierNode(CtrlNode):
    nodeName = 'maClusterINEXClassifier'
    uiTemplate = [
        ('color_int',  'color', {'color':(128,0,0)}),
        ('color_default',  'color', {'color':(20,20,20)})
    ]
    def __init__(self, name):
        terminals={
            'clustersin': {'io':'in'},
            'mah': {'io':'in'},
            'int_clusters': {'io':'out'},
            'ext_clusters': {'io':'out'},
            'coords_color': {'io':'out'},
            'coords_idx': {'io':'out'},
            'clusters': {'io':'out'}
        }
        CtrlNode.__init__(self, name, terminals=terminals)

    def process(self, clustersin, mah, display=True):
        result = {'clusters':clustersin}

        int_clusters = []
        ext_clusters = []
        coords_color = np.tile(self.ctrls['color_default'].color(mode='float'), (mah.m,1))
        coords_idx = -1*np.ones(mah.m, dtype=np.int)

        for i, cluster in enumerate(clustersin):
            if np.mean(cluster.vs['bz_avg']) > 0:
                int_clusters.append(cluster)
                ma_idx = np.concatenate(cluster.vs['ma_idx'])
                coords_color[mah.s_idx(ma_idx)] = np.array(self.ctrls['color_int'].color(mode='float'), dtype=np.float32)
                coords_idx[mah.s_idx(ma_idx)] = i
            else:
                ext_clusters.append(cluster)


        
        result['int_clusters'] = int_clusters
        result['ext_clusters'] = ext_clusters
        result['coords_color'] = coords_color
        result['coords_idx'] = coords_idx

        return result#, 'classdict':classdict}

class maClusterClassifierNode(CtrlNode):
    nodeName = 'maClusterClassifier'
    uiTemplate = [
        ('skip_first',  'intSpin', {'min':0, 'max':100, 'value':4}),
    ]
    def __init__(self, name):
        terminals={
            'clustersin': {'io':'in'},
            'mah': {'io':'in'},
            'clusters': {'io':'out'}
        }
        for classname in CLASSDICT.values():
            terminals[classname] = {'io':'out'}
        
        CtrlNode.__init__(self, name, terminals=terminals)

    def process(self, clustersin, mah, display=True):
        result = {'clusters':clustersin}
        for classname in CLASSDICT.values():
            result[classname] = []
        skip_first = self.ctrls['skip_first'].value()
        for cluster in clustersin[skip_first:]:
            cluster, classification = classify_cluster(cluster, mah)
            result[CLASSDICT[classification]].append(cluster)

        return result#, 'classdict':classdict}

# class maSheetClassifierNode(Node):
#     nodeName = 'maSheetClassifier'

#     def __init__(self, name):
#         terminals={
#             'sheetsin': {'io':'in'},
#             'mah': {'io':'in'},
#             'sheetsout': {'io':'out'}
#         }
#         for classname in ['']:
#             terminals[classname] = {'io':'out'}
        
#         Node.__init__(self, name, terminals=terminals)

#     def process(self, clustersin, mah, display=True):
#         result = {'clusters':clustersin}
#         for classname in CLASSDICT.values():
#             result[classname] = []

#         for cluster in clustersin:
#             cluster, classification = classify_cluster(cluster, mah)
#             result[CLASSDICT[classification]].append(cluster)

#         return result#, 'classdict':classdict}

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
