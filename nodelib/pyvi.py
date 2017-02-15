from pyqtgraph.flowchart.library.common import CtrlNode
from pyqtgraph.flowchart import Node
from .types import pvPainterNode

from PyQt5 import QtCore

from pyvi.gloo import *
from pyvi.util import *


class pvBBoxNode(CtrlNode):
    nodeName = 'pvBBox'
    uiTemplate = [
        ('points', 'text', )
    ]

    def __init__(self, name):
        CtrlNode.__init__(self, name, terminals={
        'points': {'io':'in'},
        'bbox': {'io':'out'},
        'idx': {'io':'out'}
        })

    def process(self, points, display=True):
        s = self.ctrls['points'].text()
        ps = []
        for p in s.split(','):
            cs = p.split()
            ps.append((float(cs[0]), float(cs[1]), float(cs[2])))

        bbox_clip = BBox(np.array(ps))
        result = {'bbox': bbox_clip}
        if not points is None:
            result['idx'] = np.all(np.logical_and(bbox_clip.mi <= points, points <= bbox_clip.ma), axis=1), 's'

        return result

class pvPointPainterNode(pvPainterNode):
    nodeName = 'pvPointPainter'
    uiTemplate = [
        ('point_size',  'doubleSpin', {'min':1.0, 'max':200.0, 'value':3.0, 'step':0.2}),
        ('lightning',  'check', {'checked':True}),
        ('draw_mode',  'combo', {'values':['simple', 'disk', 'oriented_disk']}),
        ('color_mode',  'combo', {'values':['fixed', 'texture', 'color']}),
        ('color',  'color', {'color':(128,128,0)}),
        ('gradient',  'gradient', {})
    ]
    
    def __init__(self, name):
        ## Initialize node with only a single input terminal
        pvPainterNode.__init__(self, name, draw_type='points', terminals={
        'a_position': {'io':'in'},
        'a_normal': {'io':'in'},
        'a_color': {'io':'in'},
        'a_intensity': {'io':'in'},
        'bbox_clip': {'io':'in'},
        'out': {'io':'out'},
        'bbox': {'io':'out'}
        })
        self.ctrls['color_mode'].currentIndexChanged.connect(self.changeColorMode)
        self.ctrls['draw_mode'].currentIndexChanged.connect(self.changeDrawMode)
        self.ctrls['lightning'].stateChanged.connect(self.changeLightning)
        self.ctrls['gradient'].sigGradientChangeFinished.connect(self.changeGradient)

    def changeGradient(self, gradientItem):
        if self.pvPainter.colormap.is_initialised:
            self.pvPainter.colormap.setImage(gradientItem.getLookupTable(nPts=self.pvPainter.colormap.width, alpha=False))
            self.update()

    def changeDrawMode(self, index):
        if self.pvPainter.program.is_initialised:
            if index == 0:
                draw_mode = 'simple'
            elif index == 1:
                draw_mode = 'disk'
            else:
                draw_mode = 'oriented_disk'
            self.pvPainter.program.rebuild(draw_mode=draw_mode)

    def changeColorMode(self, index):
        if self.pvPainter.program.is_initialised:
            if index == 0:
                color_mode = 'fixed'
            elif index == 1:
                color_mode = 'texture'
            elif index == 2:
                color_mode = 'color'
            self.pvPainter.program.rebuild(color_mode=color_mode)

    def changeLightning(self, state):
        if self.pvPainter.program.is_initialised:
            checked = state > 0
            self.pvPainter.program.rebuild(lightning=checked)

    def updateGL(self, struct_array, image_gradient, options):
        self.pvPainter.program.setOptions(**options)
        self.pvPainter.colormap.setImage(image_gradient)
        self.pvPainter.buffer.setData(struct_array)

        if 'u_point_size' in self.pvPainter.program.uniforms:
            self.pvPainter.program.setUniformValue('u_point_size', options['point_size'])
        if 'u_color' in self.pvPainter.program.uniforms: # should only be true if the program is initialised
            self.pvPainter.program.setUniformValue('u_color', options['color'])

    def process(self, a_position, a_normal, a_color, a_intensity, bbox_clip, display=True):
        dtypes=[('a_position', np.float32, 3)]
        if not a_normal is None:
            dtypes.append(('a_normal', np.float32, 3))
        if not a_intensity is None:
            dtypes.append(('a_intensity', np.float32, 1))
        if not a_color is None:
            dtypes.append(('a_color', np.float32, 4))

        struct_array = np.empty( len(a_position), dtype=dtypes )
        struct_array['a_position'] = a_position
        if not a_normal is None:
            struct_array['a_normal'] = a_normal
        if not a_intensity is None:
            struct_array['a_intensity'] = a_intensity
        if not a_color is None:
            struct_array['a_color'] = a_color

        # bbox clipping
        if bbox_clip:
            bbox_clip_mask = np.all(np.logical_and(bbox_clip.mi <= a_position, a_position <= bbox_clip.ma), axis=1)
            struct_array = struct_array[bbox_clip_mask]

        options = {}
        options['point_size'] = self.ctrls['point_size'].value()
        options['color'] = np.array(self.ctrls['color'].color(mode='float'), dtype=np.float32)
        options['lightning'] = self.ctrls['lightning'].checkState() > 0
        options['color_mode'] = self.ctrls['color_mode'].currentText()
        options['draw_mode'] = self.ctrls['draw_mode'].currentText()
        image_gradient = self.ctrls['gradient'].getLookupTable(nPts=self.pvPainter.colormap.width, alpha=False)

        self.sigUpdateGL.emit(struct_array, image_gradient, options)

        if self.pvPainter.is_initialised:
            bbox=self.pvPainter.getBBox()
        else:
            bbox=None

        return {
            'out': self.pvPainter,
            'bbox': bbox
        }

class pvLinePainterNode(pvPainterNode):
    nodeName = 'pvLinePainter'
    uiTemplate = [
        ('color_mode',  'combo', {'values':['fixed', 'texture']}),
        ('alternate_vcolor',  'check', {'checked':True}),
        ('color',  'color', {'color':(128,128,0)}),
        ('gradient',  'gradient', {})
    ]
    
    def __init__(self, name):
        ## Initialize node with only a single input terminal
        pvPainterNode.__init__(self, name, draw_type='lines', terminals={
        'start': {'io':'in', 'optional':False},
        'end': {'io':'in'},
        'intensity': {'io':'in'},
        'out': {'io':'out'},
        'bbox': {'io':'out'}
        })
        self.ctrls['color_mode'].currentIndexChanged.connect(self.changeColorMode)
        self.ctrls['alternate_vcolor'].stateChanged.connect(self.changeAlternateVColor)
        self.ctrls['gradient'].sigGradientChangeFinished.connect(self.changeGradient)

    def changeGradient(self, gradientItem):
        if self.pvPainter.colormap.is_initialised:
            self.pvPainter.colormap.setImage(gradientItem.getLookupTable(nPts=self.pvPainter.colormap.width, alpha=False))
            self.update()

    def changeColorMode(self, index):
        if self.pvPainter.program.is_initialised:
            if index == 0:
                color_mode = 'fixed'
            else:
                color_mode = 'texture'
            self.pvPainter.program.rebuild(color_mode=color_mode)

    def changeAlternateVColor(self, state):
        if self.pvPainter.program.is_initialised:
            checked = state > 0
            self.pvPainter.program.rebuild(alternate_vcolor=checked)
    
    def updateGL(self, struct_array, image_gradient, options):
        self.pvPainter.program.setOptions(**options)
        self.pvPainter.colormap.setImage(image_gradient)
        self.pvPainter.buffer.setData(struct_array)

        if 'u_color' in self.pvPainter.program.uniforms: # should only be true if the program is initialised
            self.pvPainter.program.setUniformValue('u_color', options['color'])

    def process(self, start, end, intensity, display=True):
        if start is None:
            raise Exception('Set Input')

        m,n = start.shape
        m *= 2
        dtypes=[('a_position', np.float32, 3)]
        if not intensity is None:
            dtypes.append(('a_intensity', np.float32, 1))

        struct_array = np.empty( m, dtype=dtypes )
        struct_array['a_position'][0::2] = start
        struct_array['a_position'][1::2] = end
        if not intensity is None:
            struct_array['a_intensity'][0::2] = intensity
            struct_array['a_intensity'][1::2] = intensity

        options = {}
        options['color'] = np.array(self.ctrls['color'].color(mode='float'), dtype=np.float32)
        options['alternate_vcolor'] = self.ctrls['alternate_vcolor'].checkState() > 0
        options['color_mode'] = self.ctrls['color_mode'].currentText()
        image_gradient = self.ctrls['gradient'].getLookupTable(nPts=self.pvPainter.colormap.width, alpha=False)
        
        self.sigUpdateGL.emit(struct_array, image_gradient, options)

        if self.pvPainter.is_initialised:
            bbox=self.pvPainter.getBBox()
        else:
            bbox=None

        return {
            'out': self.pvPainter,
            'bbox': bbox
        }
            
    
class pvLayerNode(CtrlNode):
    nodeName = 'pvLayer'
    
    uiTemplate = [
        # ('is_visible',  'check', {'checked':True})
    ]
    
    def __init__(self, name):
        ## Initialize node with only a single input terminal
        CtrlNode.__init__(self, name, terminals={
        'painters': {'io':'in', 'multi':True},
        'out': {'io':'out'}
        })
        self.sigRenamed.connect(self.renamed)

    def renamed(self, old_name):
        # print(self.name(), self._name, name)
        # if not self.pvLayer is None:
        #     self.pvLayer.name = self.name()
        self.update()
    
    def disconnected(self, localTerm, remoteTerm):
        if hasattr(self, 'pvLayer'):
            if localTerm.name() == 'painters':
                painterNode = remoteTerm.node()
                if hasattr(painterNode,'pvPainter'):
                    self.pvLayer.unsetPainter(painterNode.pvPainter)
        self.update()

    def process(self, painters, display=True):
        if not hasattr(self, 'pvLayer'):
            self.pvLayer = Layer()
            self.pvLayer.name = self.name
        for painter in painters.values():
            self.pvLayer.setPainter(painter)
        
        return {
            'out': self.pvLayer
        }

class pvWindowNode(CtrlNode):
    nodeName = 'pvWindow'
    
    sigLayerUpdated = QtCore.Signal(object)

    uiTemplate = [
        ('near_clip',  'doubleSpin', {'min':0.1, 'max':500., 'value':0.1}),
        ('far_clip',  'doubleSpin', {'min':1., 'max':500., 'value':100.}),
        ('fov',  'doubleSpin', {'min':1., 'max':100., 'value':60.})
    ]

    def __init__(self, name):
        CtrlNode.__init__(self, name, terminals={
        'layers': {'io':'in', 'multi':True},
        'bbox': {'io':'in'}
        })

    def setPyViWindow(self, window):
        self.pvWindow = window
        self.sigLayerUpdated.connect(window.setLayer)
        self.update()
    
    def setWidgetPane(self, widget):
        self.widgetPane = widget

    def disconnected(self, localTerm, remoteTerm):
        if hasattr(self, 'pvWindow'):
            if localTerm.name() == 'layers':
                layerNode = remoteTerm.node()
                if hasattr(layerNode,'pvLayer'):
                    self.pvWindow.unsetLayer(layerNode.pvLayer)

    def process(self, layers, bbox):
        if not hasattr(self, 'pvWindow'):
            raise Exception('No window is set')

        for layer in layers.values():
            if not layer is None:
                self.sigLayerUpdated.emit(layer)

        self.pvWindow.p_nclip = self.ctrls['near_clip'].value()
        self.pvWindow.p_fclip = self.ctrls['far_clip'].value()
        self.pvWindow.p_fov = self.ctrls['fov'].value()

        self.pvWindow.setBBox(bbox)
        self.pvWindow.renderLater()