from pyqtgraph.flowchart.library.common import CtrlNode

from PyQt5 import QtCore

from pyvi.gloo import *
from pyvi.util import *
from pyvi.shaders import PointShaderProgram, LineShaderProgram, TriangleShaderProgram


class pvPainterNode(CtrlNode):
    sigUpdateGL = QtCore.Signal(object, object, object)
    
    def __init__(self, name, draw_type, **kwargs):
        CtrlNode.__init__(self, name, **kwargs)
        self.sigClosed.connect(self.destroy)
        self.sigRenamed.connect(self.renamed)
        self.sigUpdateGL.connect(self.updateGL)

        if draw_type == 'points':
            shader = PointShaderProgram()
        elif draw_type == 'lines':
            shader = LineShaderProgram()
        elif draw_type == 'triangles':
            shader = TriangleShaderProgram()
        buffer = Buffer()
        colormap = ColorMap()
        self.pvPainter = Painter(shader, draw_type, buffer, colormap)
        self.pvPainter.name = self.name

    def renamed(self, old_name):
        self.update()

    def updateGL(self, struct_array, image_gradient, options):
        pass

    def destroy(self, node):
        self.pvPainter.buffer.delete()
        self.pvPainter.colormap.delete()
        self.pvPainter.program.delete()
        self.pvPainter.delete()