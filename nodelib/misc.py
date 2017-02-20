from pyqtgraph.flowchart.library.common import CtrlNode
from pyqtgraph.flowchart import Node
from pyqtgraph import PlotDataItem, LinearRegionItem, ScatterPlotItem, fn

from PyQt5 import QtCore, QtGui

import numpy as np


class ScatterPlotterNode(Node):
    nodeName = 'ScatterPlotter'
    sigUpdatePlot = QtCore.Signal(object)

    def __init__(self, name):
        Node.__init__(self, name, terminals={
            'x':{'io':'in'},
            'y':{'io':'in'},
            'color':{'io':'in'},
            'plotItem':{'io':'out'}
        })
        self.ScatterPlotItem = ScatterPlotItem(pen=None, symbol='o', size=4, brush=(255,255,255,160))
        self.sigUpdatePlot.connect(self.updatePlot)

    def updatePlot(self, xyc):
        x,y,color = xyc
        self.ScatterPlotItem.setData(x,y)
        if not color is None:
            brs = [fn.mkBrush(tuple(c)) for c in (color*255).astype(np.int32)]
            self.ScatterPlotItem.setBrush(brs)

    def process(self, x, y, color, display=True):
        if x is None or y is None:
            raise Exception('set proper inputs')
        self.sigUpdatePlot.emit((x,y,color))
        return {'plotItem': self.ScatterPlotItem}

class MultiplexerNode(CtrlNode):
    nodeName = 'Multiplexer'
    uiTemplate = [
        ('input_select',  'combo', {'values': ['A']})
    ]

    def __init__(self, name):
        CtrlNode.__init__(self, name, allowAddInput=True, terminals={
            'A' : {'io': 'in', 'multi':True},
            'B' : {'io': 'in', 'multi':True},
            'O' : {'io': 'out'},
        })

    def addInput(self, renamable=True, removable=True, multiable=True):  ## called when add input is clicked in context menu
        self.addTerminal('name', io='in', multi=True, removable=True, renamable=True)
        self.update()

    def process(self, display=True, **kwargs):

        selected_key = self.ctrls['input_select'].currentText()
        selected_index = self.ctrls['input_select'].currentIndex()
        
        self.ctrls['input_select'].blockSignals(True)
        self.ctrls['input_select'].clear()
        self.ctrls['input_select'].insertItems(0, kwargs.keys())
        self.ctrls['input_select'].setCurrentIndex(selected_index)
        self.ctrls['input_select'].blockSignals(False)

        if kwargs[selected_key]:
            O = []
            for v in kwargs[selected_key].values():
                if type(v) is list:
                    O.extend(v)
                else:
                    O.append(v)
        else:
            O = None

        return {
            'O':O
        }

class RandomColorMapperNode(Node):
    nodeName = 'RandomColorMapper'

    def __init__(self, name):
        Node.__init__(self, name, terminals={
            'values': {'io':'in'},
            'colors': {'io':'out'}
        })

    def process(self, values):
        colormap = {}
        for v in np.unique(values):
            colormap[v] = np.ones(4)
            colormap[v][:-1] = np.random.random(3)

        result = np.empty((len(values),4), dtype=np.float32)
        for i, v in enumerate(values):
            result[i] = colormap[v]

        return {'colors': result}

class arrayNormaliserNode(Node):
    nodeName = 'arrayNormaliser'
    sigUpdatePlot = QtCore.Signal(object)
    
    def __init__(self, name):
        Node.__init__(self, name, terminals={
            'dataIn': {'io':'in'},
            'dataOut': {'io':'out'},
            'plotItems': {'io': 'out'}
        })
        color = (220,220,25,255)
        self.plotDataItem = PlotDataItem(stepMode=True, fillLevel=0, pen={'color': color, 'width': 2})
        self.plotRegion = LinearRegionItem([0,1], movable=True)
        self.plotRegion.sigRegionChangeFinished.connect(self.regionChanged)
        self.sigUpdatePlot.connect(self.updatePlot)

    def updatePlot(self, xy):
        self.plotDataItem.setData(*xy)

    def regionChanged(self):
        self.regionLimits = self.plotRegion.getRegion()
        self.update()

    def process(self, dataIn, display=True):
        if len(dataIn.shape) != 1:
            data = dataIn[:,-1]
        else:
            data = dataIn

        self.extremeLimits = np.nanmin(data), np.nanmax(data)

            # if not self.plotWidget.closed: # the plotWidget attribute is never removed but it is invalidated when the widget is closed
        y,x = np.histogram(data, bins=100)
        # self.plotWidget.clear()
        self.sigUpdatePlot.emit((x,y))
        # self.plotWidget.addItem(self.plotRegion)

        if hasattr(self, 'regionLimits'):
            mi, ma = self.regionLimits
        else: 
            mi, ma = self.extremeLimits

        # if hasattr(self, 'plotRegion'):
        #     self.plotRegion.setRegion((mi, ma))
        
        dataOut =  (data - mi) / (ma-mi)

        # print (dataOut)

        return {
            'dataOut': dataOut,
            'plotItems': [self.plotRegion, self.plotDataItem]
        }


    # def saveState(self):
    #     state = super(arrayNormaliserNode, self).saveState()
    #     if hasattr(self, 'regionLimits'):
    #         state.update({'regionLimits':self.regionLimits})
    #     return state

    # def restoreState(self, state):
    #     super(arrayNormaliserNode, self).restoreState(state)
    #     if 'regionLimits' in state:
    #         self.regionLimits = state['regionLimits']

    # def ctrlWidget(self):
    #     self.plotWidget = PlotWidget()
        
    #     self.update()
    #     return self.plotWidget