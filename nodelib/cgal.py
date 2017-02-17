from pyqtgraph.flowchart.library.common import CtrlNode
from pyqtgraph.flowchart import Node

import numpy as np

from CGAL.CGAL_Kernel import Point_3
from CGAL.CGAL_Triangulation_3 import Delaunay_triangulation_3, Delaunay_triangulation_3_Facet

class cgalTertraCarverNode(Node):
    nodeName = 'cgalTertraCarver'

    def __init__(self, name):
        Node.__init__(self, name, allowAddOutput=False, terminals={
            'info_map': {'io':'in'},
            'triangulation_3i': {'io':'in'},
            'triangulation_3o': {'io':'out'},
            'interior_cells': {'io':'out'},
            'boundary_triangles': {'io':'out'},
            'interior_triangles': {'io':'out'},
            'exterior_triangles': {'io':'out'}
        })

    def process(self, info_map, triangulation_3i, display=True):
        T = triangulation_3i
        SE = set([c for c in T.finite_cells()])
        SI = set()
        for vh, isma in info_map.items():
            if isma:
                l=[]
                T.finite_incident_cells(vh,l)
                for cell in l:
                    SI.add(cell)

        SE -= SI

        boundary_triangles = []
        interior_triangles = []
        for cell in SI:
            for i in range(3):
                if not cell.neighbor(i) in SI:
                    boundary_triangles.append( T.triangle(cell,i) )
                interior_triangles.append( T.triangle(cell,i) )
        exterior_triangles = []
        for cell in SE:
            for i in range(3):
                exterior_triangles.append( T.triangle(cell,i) )

        return {'triangulation_3o':T,
                'interior_cells':SI,
                'boundary_triangles':boundary_triangles,
                'interior_triangles':interior_triangles,
                'exterior_triangles':exterior_triangles
                }

class cgalTertrahedraliserNode(Node):
    nodeName = 'cgalTertrahedraliser'

    def __init__(self, name):
        Node.__init__(self, name, allowAddOutput=False, terminals={
            'mah': {'io':'in'},
            'ma_idx': {'io':'in'},
            'triangulation_3': {'io':'out'},
            'info_map': {'io':'out'}
        })

    def process(self, mah, ma_idx, display=True):
        ma_idx, t = ma_idx
        T = Delaunay_triangulation_3()
        I = {}

        L = [Point_3(c[0],c[1],c[2]) for c in mah.D['ma_coords'][ma_idx].astype(np.double)]
        for p in L:
            vh = T.insert(p)  
            I[vh]=True
        
        s_idx = mah.s_idx(ma_idx)
        L = [Point_3(c[0],c[1],c[2]) for c in mah.D['coords'][s_idx].astype(np.double)]
        for p in L:
            vh = T.insert(p)  
            I[vh]=False

        return {'triangulation_3':T, 'info_map':I}

class cgalTriangleExpanderNode(Node):
    nodeName = 'cgalTriangleExpander'

    def __init__(self, name):
        Node.__init__(self, name, allowAddOutput=False, terminals={
            'triangulation_3': {'io':'in'},
            'triangles': {'io':'out'},
            'normals': {'io':'out'}
        })

    def process(self, triangulation_3, display=True):
        if not type(triangulation_3) is list:
            triangle_list = []
            
            for facet in triangulation_3.finite_facets():
                cell, i = facet
                triangle_list.append(triangulation_3.triangle(cell,i))
        else:
            triangle_list = triangulation_3

        nt = len(triangle_list)
        triangles = np.empty((3*nt,3), dtype=np.float32)
        normals = np.empty((nt,3), dtype=np.float32)

        for i, triangle in enumerate(triangle_list):
            for j in range(3):
                p=triangle.vertex(j)
                triangles[i*3+j] = [p.x(), p.y(), p.z()]
            plane = triangle.supporting_plane()
            normal_vector = plane.orthogonal_vector()
            normals[i] = [normal_vector.x(), normal_vector.y(), normal_vector.z()]
        normals = normals/np.linalg.norm(normals, axis=1)[:,None]

        return {'triangles':triangles, 'normals':normals}