from pyqtgraph.flowchart import Flowchart
from pyqtgraph.flowchart.library.Display import PlotWidgetNode
from pyqtgraph import PlotWidget
from pyqtgraph import configfile

# from pyqtgraph import dockarea as dockarea

from PyQt5.Qt import QWidget
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QDockWidget, QAction
from PyQt5.QtCore import Qt

from pyvi.window import SimpleWindow

from nodelib import LIBRARY
from nodelib.pyvi import pvWindowNode

import click

import sys

INFILE = '/Users/ravi/Sync/phd/data/mat_samples/blender/corner_gable/NPY'
# INFILE = '/Users/ravi/git/masbcpp/rdam_blokken_npy'


class pyviViewerWindow(QtGui.QMainWindow):

    def __init__(self, flowchart):
        QtGui.QMainWindow.__init__(self)
        self.resize(1000,800)
        self.setWindowTitle('Viewer')
        
        self.fc = flowchart
        self.fc.sigChartChanged.connect(self.nodeEvent)
        self.fc.sigChartLoaded.connect(self.loadChartEvent)
        self.fc.widget().resize(1000,800)
        
        
        self.pyviwin = SimpleWindow()
        ## http://blog.qt.io/blog/2013/02/19/introducing-qwidgetcreatewindowcontainer/
        pyvi_widget = QWidget.createWindowContainer(self.pyviwin)
        pyvi_widget.setMinimumSize(200,200)
        pyvi_widget.resize(800,800)
        self.setCentralWidget(pyvi_widget)

        self.layerDockWidget = QDockWidget('Layers')
        self.layerDockWidget.setFeatures(QDockWidget.DockWidgetFloatable|QDockWidget.DockWidgetMovable)
        self.layerDockWidget.setWidget(self.pyviwin.layerWidget)
        self.pyviwin.layerWidget.resize(200,500)
        self.addDockWidget(Qt.RightDockWidgetArea, self.layerDockWidget)
        
        
        self.plotDockWidget = QDockWidget('Plot')
        self.plotDockWidget.setFeatures(QDockWidget.DockWidgetFloatable|QDockWidget.DockWidgetMovable|QDockWidget.DockWidgetClosable)
        self.plotWidget = PlotWidget()
        self.plotDockWidget.setWidget(self.plotWidget)
        self.plotWidget.resize(100,100)
        # self.plotDockWidget.show()
        # self.addDockWidget(Qt.RightDockWidgetArea, self.plotDockWidget)

        self.plotList = {'plot 1':self.plotWidget}

        # self.dockWidgetDict = {}

        self.createActions()
        self.createMenus()

        self.show()
        self.fc.widget().show()

    def save(self):
        try:
            self.fc.saveFile()
        except:
            raise

    def open(self):
        self.fc.loadFile()

    def createActions(self):
        self.saveAct = QAction("&Save...", self,
            shortcut=QtGui.QKeySequence.Save,
            statusTip="Save the current form letter", 
            triggered=self.save)

        self.openAct = QAction("&Open...", self,
            shortcut=QtGui.QKeySequence.Open,
            statusTip="Save the current form letter", 
            triggered=self.open)
        
        self.reloadAct = QAction("&Reload nodelibs...", self,
            shortcut=QtGui.QKeySequence.Refresh,
            statusTip="Reload nodelibraries", 
            triggered=self.fc.widget().reloadLibrary)

        self.quitAct = QAction("&Quit", self, 
            shortcut=QtGui.QKeySequence.Quit,
            statusTip="Quit the application", 
            triggered=self.close)

        self.toggleViewerAct = QAction("&Toggle Viewer", self, 
            statusTip="Toggle viewer window", 
            triggered=self.toggleViewer)

        self.toggleFlowchartAct = QAction("&Toggle Flowchart", self, 
            statusTip="Toggle flowchart window", 
            triggered=self.toggleFlowchart)

        self.togglePlotterAct = QAction("&Toggle Plotter", self, 
            statusTip="Toggle plot window", 
            triggered=self.togglePlotter)

    def toggleViewer(self):
        if self.isHidden():
            self.show()
        else:
            self.hide()
    
    def togglePlotter(self):
        if self.plotDockWidget.isHidden():
            self.plotDockWidget.show()
        else:
            self.plotDockWidget.hide()

    def toggleFlowchart(self):
        if self.fc.widget().isHidden():
            self.fc.widget().show()
        else:
            self.fc.widget().hide()

    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(self.openAct)
        self.fileMenu.addAction(self.saveAct)
        self.fileMenu.addAction(self.reloadAct)
        # self.fileMenu.addSeparator()
        # self.fileMenu.addAction(self.quitAct)

        # self.editMenu = self.menuBar().addMenu("&Edit")
        # self.editMenu.addAction(self.undoAct)

        self.viewMenu = self.menuBar().addMenu("&View")
        self.viewMenu.addAction(self.toggleViewerAct)
        self.viewMenu.addAction(self.toggleFlowchartAct)
        self.viewMenu.addAction(self.togglePlotterAct)

    def loadChartEvent(self):
        # self.clearDock()
        for node in self.fc.nodes().values():
            self.addNode(node)

    def nodeEvent(self, flowchart, action, node):
        if action == 'add':
            self.addNode(node)
        elif action == 'remove':
            self.removeNode(node)
        elif action == 'rename':
            pass
            # try:
            #     self.dockWidgetDict[node].setWindowTitle(node.name())
            # except KeyError:
            #     pass
    
    def addNode(self, node):
        # ctrlWidget = node.ctrlWidget()
        # if ctrlWidget:
        #     dock = QDockWidget(node.name(), self)
        #     dock.setWidget(node.ctrlWidget())
        #     dock.hide()
        #     # nodeDock.hideTitleBar()
        #     # self.da.addDock(nodeDock, 'right', )
        #     self.addDockWidget(Qt.RightDockWidgetArea, dock)
        #     self.viewMenu.addAction(dock.toggleViewAction())
        #     self.dockWidgetDict[node] = dock
        if type(node) is pvWindowNode:
            node.setPyViWindow(self.pyviwin)
        elif type(node) is PlotWidgetNode:
            node.setPlotList(self.plotList)
            node.setPlot(self.plotWidget)
    
    def removeNode(self, node):
        print("removing...",node)
        # try:
        #     dock = self.dockWidgetDict[node]
        #     self.viewMenu.removeAction(dock.toggleViewAction())
        #     self.removeDockWidget(dock)
        #     del self.dockWidgetDict[node]
        # except KeyError:
        #     pass

    # def clearDock(self):
    #     nodes = list(self.dockWidgetDict.keys())
    #     for node in nodes:
    #         self.removeNode(node)


@click.command()
@click.argument("dataset", type=click.Path(exists=True), default=INFILE)
@click.option("--flowchart", required=False, type=click.Path(exists=True))
def cli(dataset, flowchart):
    app = QtGui.QApplication.instance() # retrieves the ipython qt application if any
    if app is None:
        app = QtGui.QApplication([]) # create one if standalone execution

    fc = Flowchart(library=LIBRARY, terminals={
        'dataIn': {'io': 'in'}
        })
    win = pyviViewerWindow(fc)

    fc.setInput(dataIn=dataset)
    if flowchart:
        fc_state = configfile.readConfigFile(flowchart)
        fc.restoreState(fc_state, clear=False)
        fc.viewBox.autoRange()

    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        app.exec_()
        app.deleteLater()
        sys.exit()

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    cli()