from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import (QGuiApplication, QMatrix4x4, QOpenGLContext,
        QSurfaceFormat, QWindow)
from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QDockWidget

from OpenGL import GL as gl
import ctypes
import numpy as np
import math

from .linalg import quaternion as q
from .transforms import *
from .gloo import *

# import threading

DEFAULT_FORMAT = QSurfaceFormat()
DEFAULT_FORMAT.setVersion(3, 3)
DEFAULT_FORMAT.setProfile(QSurfaceFormat.CoreProfile)
DEFAULT_FORMAT.setStereo(False)
DEFAULT_FORMAT.setSwapBehavior(QSurfaceFormat.DoubleBuffer)
DEFAULT_FORMAT.setDepthBufferSize(24)
DEFAULT_FORMAT.setSamples(4)

class OpenGLWindow(QWindow):
    def __init__(self, parent=None):
        super(OpenGLWindow, self).__init__(parent)

        self.m_update_pending = False
        self.m_animating = False
        self.m_context = None
        self.m_gl = None

        self.setSurfaceType(QWindow.OpenGLSurface)

    def initialise(self):
        pass

    def setAnimating(self, animating):
        self.m_animating = animating

        if animating:
            self.renderLater()

    def renderLater(self):
        if not self.m_update_pending:
            self.m_update_pending = True
            QApplication.postEvent(self, QEvent(QEvent.UpdateRequest))

    def renderNow(self):
        if not self.isExposed():
            return

        self.m_update_pending = False

        needsInitialise = False

        if self.m_context is None:
            self.m_context = QOpenGLContext(self)
            self.m_context.setFormat(self.requestedFormat())
            self.m_context.create()

            needsInitialise = True

        self.m_context.makeCurrent(self)

        if needsInitialise:
            self.initialise()

        self.render()

        self.m_context.swapBuffers(self)

        if self.m_animating:
            self.renderLater()

    def event(self, event):
        if event.type() == QEvent.UpdateRequest:
            self.renderNow()
            return True

        return super(OpenGLWindow, self).event(event)

    def exposeEvent(self, event):
        self.renderNow()

    def resizeEvent(self, event):
        self.renderNow()

class crosshairPainter(Painter):
    vertexShaderSource = 'vertex', """
#version 330

in vec2  a_position;

void main (void) {
    gl_Position =  vec4(a_position, 0.0, 1.0);
}
"""

    fragmentShaderSource = 'fragment', """
#version 330

out vec4 color;

void main()
{
    color = vec4(0.5,0.5,0.5,1.0);
}
"""
    def __init__(self):
        shader_program = ShaderProgram()
        shader_program.vertexShaderSource = self.vertexShaderSource
        shader_program.fragmentShaderSource = self.fragmentShaderSource
        shader_program.attribute_names = ['a_position']
        crosshair_data  = np.zeros( 4, [('a_position', np.float32, 2)] )
        crosshair_data ['a_position'] = np.array([[-1, 0], [1,0], [0,-1], [0,1]], dtype=np.float32)
        buffer = Buffer(crosshair_data)
        super(crosshairPainter, self).__init__(shader_program, 'lines', buffer)

class SimpleWindow(OpenGLWindow):
    def __init__(self, format=DEFAULT_FORMAT, size=(700,700)):
        super(SimpleWindow, self).__init__()

        self.setFormat(format)
        self.resize(*size)

        self.m_program = None
        self.m_frame = 0
        self.buffer = None
        # self.scene = scene
        # scene.window = self
        self.layers = []

        # background color
        self.clearcolor = (1,1,1,1)

        # model paramenters
        self.m_translation = np.zeros(3, dtype=np.float32)

        # view parameters
        self.v_scale = 0.1
        self.v_cam_distance = 2
        self.v_translation = np.zeros(3, dtype=np.float32)
        self.v_rotation = q.quaternion()

        # projection parameters
        self.p_nclip = 0.1
        self.p_fclip = 100
        self.p_fov = 60
        self.p_ratio = 4.0/3.0

        self.last_mouse_pos = None

        # self.disableCentering = False

        self.layerWidget = QTreeWidget()
        self.layerWidget.headerItem().setHidden(True)
        self.layerWidget.setSelectionMode(QAbstractItemView.MultiSelection)
        self.layerWidget.itemClicked.connect(self.updateLayerVisibility)

        # self.layerDockWidget.show()

    def updateLayerVisibility(self, item, col):
        selected_names = [item.text(0) for item in self.layerWidget.selectedItems()]
        for layer in self.layers:
            layer.is_visible = layer.name() in selected_names
            for painter in layer.painters:
                painter.is_visible = painter.name() in selected_names
        self.renderLater()

    def setBBox(self, bbox):
        self.bbox = bbox

    def setLayer(self, layer):
        assert(type(layer) is Layer)

        if layer in self.layers:
            self.unsetLayer(layer)
        
        self.layers.append(layer)
        item = QTreeWidgetItem([layer.name()], 0)
        layer.tree_item = item
        self.layerWidget.addTopLevelItem(item)
        item.setSelected(layer.is_visible)
        for painter in layer.painters:
            child_item = QTreeWidgetItem([painter.name()], 0)
            item.addChild(child_item)
            child_item.setSelected(painter.is_visible)
        self.layerWidget.expandItem(item)
    
    def unsetLayer(self, layer):
        self.layerWidget.blockSignals(True)
        index = self.layerWidget.indexOfTopLevelItem(layer.tree_item)
        self.layerWidget.takeTopLevelItem(index)
        self.layerWidget.blockSignals(False)
        try:
            self.layers.remove(layer)
        except KeyError:
            print('attemped to delete crap that doesnt exist')
            pass

    # def clearLayers(self):
    #     self.layerWidget.clear()
        

    def initialise(self):
        self.crosshair_painter = crosshairPainter()
        gl.glClearColor(*self.clearcolor)
        gl.glEnable(gl.GL_PROGRAM_POINT_SIZE)
        gl.glDepthMask(gl.GL_TRUE)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LESS)
        # gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        # gl.glEnable(gl.GL_BLEND)
        print(gl.glGetIntegerv(gl.GL_MAX_VIEWPORT_DIMS))
        self.center()
        self.renderLater()

    def center(self, bbox=None):
        # if not self.disableCentering:
        if bbox is None:
            self.v_scale = 0.1
            self.v_translation = np.zeros(3)
        elif bbox.is_empty:
            self.v_scale = 0.1
            self.v_translation = np.zeros(3)
        else:    
            w, h = self.width(), self.height()
            mi = min(w, h)
            self.v_scale = .8 * 2*min((w/mi)/bbox.width[0], (h/mi)/bbox.width[1])
            self.v_translation = -bbox.center

    def setClearColor(self, color):
        self.clearcolor = color

    def render(self):
        # if self.scene.is_changed:
        #     self.center(self.scene.bbox)
        #     self.scene.is_changed = False

        gl.glViewport(0, 0, self.width(), self.height())

        gl.glClearColor(*self.clearcolor)
        
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        bits = 0
        bits |= gl.GL_COLOR_BUFFER_BIT
        bits |= gl.GL_DEPTH_BUFFER_BIT
        bits |= gl.GL_STENCIL_BUFFER_BIT
        gl.glClear(bits)

        for layer in self.layers:
            if layer.is_visible:
                for painter in layer.painters:
                    if painter.is_visible:
                        painter.render(view=self)
        if self.crosshair_painter.is_visible:
            self.crosshair_painter.render()

        self.m_frame += 1

    def screen2view(self, x,y):
        w, h = self.width(), self.height()
        r = 2*self.radius
        return (x-w/2.)/r, ((h-y)-h/2.)/r

    @property
    def radius(self):
        return 0.5 * min(self.width(), self.height())

    @property
    def mat_view(self):
        mat = np.eye(4, dtype=np.float32)
        translate(mat, *self.v_translation )
        scale(mat, self.v_scale, self.v_scale, self.v_scale)
        mat = mat.dot( np.array(q.matrix(self.v_rotation), dtype=np.float32) )
        translate(mat, 0,0, -self.v_cam_distance)
        return mat

    @property
    def mat_model(self):
        return translate(np.eye(4, dtype=np.float32), *self.m_translation )

    @property
    def mat_projection(self):
        return perspective(self.p_fov, self.p_ratio, self.p_nclip, self.p_fclip)

    def computeMVPMatrix(self):
        mvp_matrix = np.eye(4, dtype=np.float32)
        # model
        translate(mvp_matrix, *self.m_translation )
        # view
        mvp_matrix = mvp_matrix.dot(self.mat_view)
        # projection
        projection = perspective(self.p_fov, self.p_ratio, self.p_nclip, self.p_fclip)
        return mvp_matrix.dot(projection)
    
    def resizeEvent(self, event):
        size = event.size()
        self.p_ratio = size.width()/size.height()
        self.renderNow()

    def wheelEvent(self, event):        
        modifiers = event.modifiers()
        ticks = float(event.angleDelta().y()+event.angleDelta().x())/50
        if modifiers == Qt.ShiftModifier:
            # if self.projection_mode == 'perspective':
            old_fov = self.p_fov
            # do `dolly zooming` so that world appears at same size after canging fov
            self.p_fov = max(5.,self.p_fov + ticks)
            self.p_fov = min(120.,self.p_fov)
            self.v_cam_distance = self.v_cam_distance * (math.tan(math.radians(old_fov)/2.)) / (math.tan(math.radians(self.p_fov)/2.))
        else:
            self.v_scale *= (ticks/30 + 1.)
            self.v_scale = max(1E-3, self.v_scale)
            self.v_scale = min(1E3, self.v_scale)
        self.renderNow()

    def mouseMoveEvent(self, event):
        modifiers = event.modifiers()
        buttons = event.buttons()
        pos_x, pos_y = event.x(), event.y()

        if self.last_mouse_pos is None:
            self.last_mouse_pos = pos_x, pos_y

        if Qt.ShiftModifier == modifiers:
            x0,y0 = self.last_mouse_pos
            x1,y1 = pos_x, pos_y
            dx, dy = (x1-x0), (y1-y0)
            #scale to zero plane in projection frustrum
            scale = self.v_cam_distance * math.tan(math.radians(self.p_fov/2.))
            dx, dy = scale*dx, scale*dy
            r = self.radius
            #multiply with inverse view matrix and apply translation in world coordinates
            self.v_translation += np.array([dx/r, -dy/r, 0., 0.]).dot( np.linalg.inv(self.mat_view)) [:3]
            self.crosshair_painter.is_visible = True
        elif Qt.LeftButton == buttons:
            x0,y0 = self.screen2view(*self.last_mouse_pos)
            x1,y1 = self.screen2view(pos_x, pos_y)

            v0 = q.arcball(x0, y0)
            v1 = q.arcball(x1, y1)

            self.v_rotation = q.product(v1, v0, self.v_rotation)
            self.crosshair_painter.is_visible = True
        else:
            self.crosshair_painter.is_visible = False
        
        self.last_mouse_pos = pos_x, pos_y
        self.renderNow()

    def keyPressEvent(self, event):
        key = event.key()
        repeat = event.isAutoRepeat()
        if key == Qt.Key_T:
            self.v_rotation = q.quaternion()
        elif key == Qt.Key_U:
            if hasattr(self, 'bbox'):
                self.center(self.bbox)
        self.renderNow()