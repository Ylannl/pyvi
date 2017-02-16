from pyqtgraph.flowchart.NodeLibrary import NodeLibrary, isNodeClass
from pyqtgraph.reload import reload as pqtgreload

# nodetypes
from . import pyvi, skel3d, misc, cgal
from pyqtgraph.flowchart.library import Operators, Display, Data

class MyNodeLib(NodeLibrary):

    def __init__(self):
        NodeLibrary.__init__(self)

    def reload(self):
        pqtgreload(pyvi)
        pqtgreload(skel3d)

LIBRARY = MyNodeLib()
# Add all nodes to the default library
for mod in [pyvi, skel3d, misc, cgal, Operators, Display, Data]:
    nodes = [getattr(mod, name) for name in dir(mod) if isNodeClass(getattr(mod, name))]
    for node in nodes:
        LIBRARY.addNodeType(node, [(mod.__name__.split('.')[-1],)])