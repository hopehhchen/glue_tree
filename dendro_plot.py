from scipy.cluster.hierarchy import dendrogram, linkage
import sys
import matplotlib
matplotlib.use("Qt5Agg")
import numpy as np
from numpy import arange, sin, pi
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import pyplot as plt
from PyQt5.QtWidgets import QWidget, QMainWindow, QApplication, QSizePolicy, QVBoxLayout, QPushButton
from PyQt5.QtCore import *
from PyQt5.QtGui import QCursor
from ete3 import ClusterTree, TreeStyle
import scipy.cluster.hierarchy as sch
import scipy.spatial.distance
import matplotlib.pyplot as plt
from itertools import combinations
# found most of this in
# on of GitHub issues comments

class MyMplCanvas(FigureCanvas):
    # QWidget
    def __init__(self, parent=None, width=50, height=50, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)

        self.fig = fig
        self.axes = fig.add_subplot(111)

        self.compute_initial_figure()
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

    def compute_initial_figure(self):
        pass


class MyStaticMplCanvas(MyMplCanvas):
    #Simple canvas with dendrogram plot
    def compute_initial_figure(self):
        self.createSampleData()

        # linkage matrix
        Z = linkage(self.X, 'single')

        self.custom_dendrogram(
          Z,
          leaf_rotation=90.,
          leaf_font_size=6.
        )

    def createSampleData(self):

      # hardcoded data for now
      tree = ClusterTree('(A:0.1,B:0.2,(C:0.3,D:0.4):0.5);')
      leaves = tree.get_leaf_names()

      idx_dict = {'A':0,'B':1,'C':2,'D':3}
      idx_labels = sorted(idx_dict, key=idx_dict.get)

      dmat = np.zeros((4,4))

      for l1,l2 in combinations(leaves,2):
          d = tree.get_distance(l1,l2)
          dmat[idx_dict[l1],idx_dict[l2]] = dmat[idx_dict[l2],idx_dict[l1]] = d

      self.X = dmat

    def custom_dendrogram(self, *args, **kwargs):
          kwargs['ax'] = self.axes

          annotate_above = kwargs.pop('annotate_above', 0)

          ddata = dendrogram(*args, **kwargs)

          if not kwargs.get('no_plot', False):
              self.axes.set_title('Hierarchical Clustering Dendrogram')
              self.axes.set_xlabel('clusters')
              self.axes.set_ylabel('distance')
              for i, d, c in zip(ddata['icoord'], ddata['dcoord'], ddata['color_list']):
                  x = 0.5 * sum(i[1:3])
                  y = d[1]
                  if y > annotate_above:
                      self.axes.plot(x, y, 'o', c=c)
                      self.axes.annotate("%.3g" % y, (x, y), xytext=(0, -5),
                                   textcoords='offset points',
                                   va='top', ha='center')
          return ddata

class PlotDialog(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.plot_layout = QVBoxLayout(self)
        self.plot_canvas = MyStaticMplCanvas(self, width=50, height=50, dpi=100)
        self.navi_toolbar = NavigationToolbar(self.plot_canvas, self)
        self.plot_layout.addWidget(self.plot_canvas)
        self.plot_layout.addWidget(self.navi_toolbar)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PlotDialog()
    window.show()
    sys.exit(app.exec_())
