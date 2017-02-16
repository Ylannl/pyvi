from pyqtgraph.flowchart.library.common import CtrlNode
from pyqtgraph.flowchart import Node

import numpy as np

from CGAL.CGAL_Kernel import Point_3
from CGAL.CGAL_Triangulation_3 import Delaunay_triangulation_3, Delaunay_triangulation_3_Facet

class cgalTertrahedraliserNode(Node):
    nodeName = 'cgalTertrahedraliser'

    def __init__(self, name):
        Node.__init__(self, name, allowAddOutput=False, terminals={
            'coords': {'io':'in'},
            'triangulation_3': {'io':'out'}
        })

    def process(self, coords, display=True):
        L = [Point_3(c[0],c[1],c[2]) for c in coords.astype(np.double)]
        T = Delaunay_triangulation_3(L)

        return {'triangulation_3':T}        

class cgalTriangleExpanderNode(Node):
    nodeName = 'cgalTriangleExpander'

    vertexid_map = {0:[1,2,3], 1:[0,2,3], 2:[0,1,3], 3:[0,1,2]}

    def __init__(self, name):
        Node.__init__(self, name, allowAddOutput=False, terminals={
            'triangulation_3': {'io':'in'},
            'triangles': {'io':'out'},
            'normals': {'io':'out'}
        })

    def process(self, triangulation_3, display=True):
        fit = triangulation_3.finite_facets()
        
        nf = triangulation_3.number_of_facets()

        triangles = np.empty((3*nf,3), dtype=np.float32)
        normals = np.empty((nf,3), dtype=np.float32)
        
        if fit.hasNext():
            # done = fit.next()
            facet = Delaunay_triangulation_3_Facet()
            j=0
            k=0
            while(1):
                facet=fit.next()
                cell, i = facet
                for vid in self.vertexid_map[i]:
                    p = cell.vertex(vid).point()
                    triangles[j,0] = p.x()
                    triangles[j,1] = p.y()
                    triangles[j,2] = p.z()
                    j+=1
                p1=triangles[-3]
                p2=triangles[-2]
                p3=triangles[-1]
                v=p2-p1
                w=p3-p1
                normals[k]= np.array([
                        v[1]*w[2]-v[2]*w[1],
                        v[2]*w[0]-v[0]*w[2],
                        v[0]*w[1]-v[1]*w[0] ])
                k+=1
                # if facet == done:
                if not fit.hasNext():
                    break

        return {'triangles':triangles, 'normals':normals}
        
        
