import os

import numpy as np

from matplotlib.collections import LineCollection

from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox

from glue.config import qt_client
from glue.core.data_combo_helper import ComponentIDComboHelper

from glue.external.echo import CallbackProperty, SelectionCallbackProperty
from glue.external.echo.qt import (connect_checkable_button,
                                   autoconnect_callbacks_to_qt)

from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.matplotlib.state import MatplotlibDataViewerState, MatplotlibLayerState
from glue.viewers.matplotlib.qt.data_viewer import MatplotlibDataViewer

from glue.utils.qt import load_ui

from dendro_helpers import dendro_layout


class TutorialViewerState(MatplotlibDataViewerState):

    x_att = SelectionCallbackProperty(docstring='The attribute to use on the x-axis')
    y_att = SelectionCallbackProperty(docstring='The attribute to use on the y-axis')

    def __init__(self, *args, **kwargs):
        super(TutorialViewerState, self).__init__(*args, **kwargs)
        self._x_att_helper = ComponentIDComboHelper(self, 'x_att')
        self._y_att_helper = ComponentIDComboHelper(self, 'y_att')
        self.add_callback('layers', self._on_layers_change)
        self.add_callback('x_att', self._on_attribute_change)
        self.add_callback('y_att', self._on_attribute_change)



    def _on_layers_change(self, value):
        self._x_att_helper.set_multiple_data(self.layers_data)
        self._y_att_helper.set_multiple_data(self.layers_data)

    def _on_attribute_change(self, value):
        if self.x_att is not None:
            self.x_axislabel = self.x_att.label
        if self.y_att is not None:
            self.y_axislabel = self.y_att.label


class TutorialLayerState(MatplotlibLayerState):
    fill = CallbackProperty(False, docstring='Whether to show the markers as filled or not')

    


class TutorialLayerArtist(MatplotlibLayerArtist):

    _layer_state_cls = TutorialLayerState

    def __init__(self, axes, *args, **kwargs):

        super(TutorialLayerArtist, self).__init__(axes, *args, **kwargs)

        #self.artist = self.axes.plot([], [], 'o', mec='none')[0]
        self.lc = LineCollection([], color = 'k', linestyle = 'solid')
        self.artist = self.axes.add_collection(self.lc)
        self.mpl_artists.append(self.artist)

        self.state.add_callback('fill', self._on_visual_change)
        self.state.add_callback('visible', self._on_visual_change)
        self.state.add_callback('zorder', self._on_visual_change)
        self.state.add_callback('color', self._on_visual_change)
        self.state.add_callback('alpha', self._on_visual_change)

        self._viewer_state.add_callback('x_att', self._on_attribute_change)
        self._viewer_state.add_callback('y_att', self._on_attribute_change)

    def _on_visual_change(self, value=None):

        self.artist.set_visible(self.state.visible)
        self.artist.set_zorder(self.state.zorder)
        #self.artist.set_markeredgecolor(self.state.color)
        # if self.state.fill:
        #     self.artist.set_markerfacecolor(self.state.color)
        # else:
        #     self.artist.set_markerfacecolor('white')
        self.artist.set_alpha(self.state.alpha)

        self.redraw()

    def _on_attribute_change(self, value=None):

        if self._viewer_state.x_att is None or self._viewer_state.y_att is None:
            return

        x = self.state.layer[self._viewer_state.x_att]
        y = self.state.layer[self._viewer_state.y_att]

        ###
        orientation = 'vertical'
        verts = dendro_layout(x, y, orientation = orientation)

        print(len(verts), type(verts))

        #self.artist.set_data(x, y)
        self.lc.set_segments(verts)


        if orientation == 'vertical':
            self.axes.set_xlim(np.nanmin(x), np.nanmax(x))
            self.axes.set_ylim(np.nanmin(y), np.nanmax(y))
        elif orientation == 'horizontal':
            self.axes.set_ylim(np.nanmin(x), np.nanmax(x))
            self.axes.set_xlim(np.nanmin(y), np.nanmax(y))

        self.redraw()

    def update(self):
        self._on_attribute_change()
        self._on_visual_change()


class TutorialViewerStateWidget(QWidget):

    def __init__(self, viewer_state=None, session=None):

        super(TutorialViewerStateWidget, self).__init__()

        self.ui = load_ui('viewer_state.ui', self,
                          directory=os.path.dirname(__file__))

        self.viewer_state = viewer_state
        autoconnect_callbacks_to_qt(self.viewer_state, self.ui)


class TutorialLayerStateWidget(QWidget):

    def __init__(self, layer_artist):

        super(TutorialLayerStateWidget, self).__init__()

        self.checkbox = QCheckBox('Fill markers')
        layout = QVBoxLayout()
        layout.addWidget(self.checkbox)
        self.setLayout(layout)

        self.layer_state = layer_artist.state
        connect_checkable_button(self.layer_state, 'fill', self.checkbox)


class TutorialDataViewer(MatplotlibDataViewer):

    LABEL = 'Tutorial viewer'
    _state_cls = TutorialViewerState
    _options_cls = TutorialViewerStateWidget
    _layer_style_widget_cls = TutorialLayerStateWidget
    _data_artist_cls = TutorialLayerArtist
    _subset_artist_cls = TutorialLayerArtist

    #####
    tools = ['select:pick', 'select:rectangle']

    # def __init__(self, *args, **kwargs):
    #     super(TutorialDataViewer, self).__init__(*args, **kwargs)
        # self.axes.set_xticks([])
        # self.axes.spines['top'].set_visible(False)
        # self.axes.spines['bottom'].set_visible(False)
        #self.state.add_callback('_layout', self._update_limits)
        #self._update_limits()


    # def initialize_toolbar(self):
    #     super(TutorialDataViewer, self).initialize_toolbar()

        # def on_move(mode):
        #     if mode._drag:
        #         self.apply_roi(mode.roi())
        #
        # self.toolbar.tools['select:pick']._move_callback = on_move

    # def close(self, *args, **kwargs):
    #     self.toolbar.tools['select:pick']._move_callback = None
    #     super(TutorialDataViewer, self).close(*args, **kwargs)


qt_client.add(TutorialDataViewer)
