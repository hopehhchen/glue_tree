import os

import numpy as np

from matplotlib.collections import LineCollection
import matplotlib.cm as cm
import matplotlib.colors as mplcolors

from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QButtonGroup, QRadioButton, QHBoxLayout

from glue.config import qt_client
from glue.core.data_combo_helper import ComponentIDComboHelper

from glue.external.echo import CallbackProperty, SelectionCallbackProperty
from glue.external.echo.qt import (connect_checkable_button,
                                   autoconnect_callbacks_to_qt,
                                   connect_value)

from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.matplotlib.state import MatplotlibDataViewerState, MatplotlibLayerState
from glue.viewers.matplotlib.qt.data_viewer import MatplotlibDataViewer

from glue.utils.qt import load_ui, fix_tab_widget_fontsize

from dendro_helpers import dendro_layout, calculate_nleaf, sort1Darrays


class TutorialViewerState(MatplotlibDataViewerState):
    x_att = SelectionCallbackProperty(docstring='The attribute to use on the x-axis')
    y_att = SelectionCallbackProperty(docstring='The attribute to use on the y-axis')
    # change to parent and height
    # Tom is awesome!
    orientation = SelectionCallbackProperty(docstring='The orientation ....')
    sort_by = SelectionCallbackProperty(docstring='Sort by option ....')

    def __init__(self, *args, **kwargs):
        super(TutorialViewerState, self).__init__(*args, **kwargs)
        self._x_att_helper = ComponentIDComboHelper(self, 'x_att')
        self._y_att_helper = ComponentIDComboHelper(self, 'y_att')
        self.add_callback('layers', self._on_layers_change)
        self.add_callback('x_att', self._on_attribute_change)
        self.add_callback('y_att', self._on_attribute_change)
        TutorialViewerState.orientation.set_choices(self, ['bottom-up', 'left-right', 'top-down', 'right-left'])
        self.add_callback('orientation', self._on_attribute_change)
        TutorialViewerState.sort_by.set_choices(self, ['parent', 'height'])
        self.add_callback('sort_by', self._on_attribute_change)

    def _on_layers_change(self, value):
        self._x_att_helper.set_multiple_data(self.layers_data)
        self._y_att_helper.set_multiple_data(self.layers_data)

    def _on_attribute_change(self, value):
        if self.y_att is not None:

            if (self.orientation == 'bottom-up') or (self.orientation == 'top-down'):
                self.x_axislabel = ''
                self.y_axislabel = self.y_att.label
            elif (self.orientation == 'left-right') or (self.orientation == 'right-left'):
                self.x_axislabel = self.y_att.label
                self.y_axislabel = ''


class TutorialLayerState(MatplotlibLayerState):
    linewidth = CallbackProperty(1, docstring='line width')


class TutorialLayerArtist(MatplotlibLayerArtist):
    _layer_state_cls = TutorialLayerState

    def __init__(self, axes, *args, **kwargs):

        super(TutorialLayerArtist, self).__init__(axes, *args, **kwargs)

        # self.artist = self.axes.plot([], [], 'o', mec='none')[0]
        self.lc = LineCollection([], color='k', linestyle='solid')
        self.artist = self.axes.add_collection(self.lc)
        self.mpl_artists.append(self.artist)

        self.state.add_callback('visible', self._on_visual_change)
        self.state.add_callback('zorder', self._on_visual_change)
        self.state.add_callback('color', self._on_visual_change)
        self.state.add_callback('alpha', self._on_visual_change)
        self.state.add_callback('linewidth', self._on_visual_change)

        self._viewer_state.add_callback('x_att', self._on_attribute_change)
        self._viewer_state.add_callback('y_att', self._on_attribute_change)
        self._viewer_state.add_callback('orientation', self._on_attribute_change)
        self._viewer_state.add_callback('sort_by', self._on_attribute_change)

    def _on_visual_change(self, value=None):

        self.artist.set_visible(self.state.visible)
        self.artist.set_zorder(self.state.zorder)
        self.lc.set_color(self.state.color)
        self.lc.set_linewidth(self.state.linewidth)
        # self.artist.set_markeredgecolor(self.state.color)
        # if self.state.fill:
        #     self.artist.set_markerfacecolor(self.state.color)
        # else:
        #     self.artist.set_markerfacecolor('white')
        self.artist.set_alpha(self.state.alpha)

        self.redraw()

    def _on_attribute_change(self, value=None):

        if self._viewer_state.x_att is None or self._viewer_state.y_att is None:
            return

        # parent
        x = self.state.layer[self._viewer_state.x_att]
        # height
        y = self.state.layer[self._viewer_state.y_att]

        orientation = self._viewer_state.orientation

        # sort_by_array = None for using the original order
        # sort_by_array = y for sort by height
        sort_by_array = self.state.layer[self._viewer_state.sort_by]
        x, y = sort1Darrays(x, y, sort_by_array)

        verts, verts_horiz = dendro_layout(x, y, orientation=orientation)
        nleaf = calculate_nleaf(x)

        #  Fix the input!
        color_code = 'linear'
        color_code_by = y  # height
        color_code_cmap = cm.Reds

        if color_code == 'fixed':

            verts_final = np.concatenate([verts, verts_horiz])
            colors_final = list(np.ones(len(verts_final)))

        elif color_code == 'linear':

            cmap = color_code_cmap
            normalize = mplcolors.Normalize(np.nanmin(y), np.nanmax(y))

            colors = [cmap(normalize(yi)) for yi in y]
            colors_horiz = []
            for i in range(len(verts_horiz)):
                colors_horiz.append((0., 0., 0., 1.))

            verts_final = np.concatenate([verts, verts_horiz])

            colors_final = np.concatenate([colors, colors_horiz])

        # self.artist.set_data(x, y)
        self.lc.set_segments(verts_final)
        # uncomment the next line to
        # turn on the colormap for vertical lines
        # self.lc.set_color(colors_final)

        # parent
        xmin = (-.5)
        xmax = nleaf + 1.5
        # height
        ymin = np.nanmin(y) - .05 * (np.nanmax(y) - np.nanmin(y))
        ymax = np.nanmax(y) + .05 * (np.nanmax(y) - np.nanmin(y))

        if orientation == 'bottom-up':
            self.axes.set_xlim(xmin, xmax)
            self.axes.set_ylim(ymin, ymax)
        elif orientation == 'top-down':
            self.axes.set_xlim(xmin, xmax)
            self.axes.set_ylim(ymax, ymin)
        elif orientation == 'left-right':
            self.axes.set_ylim(xmin, xmax)
            self.axes.set_xlim(ymin, ymax)
        elif orientation == 'right-left':
            self.axes.set_ylim(xmin, xmax)
            self.axes.set_xlim(ymax, ymin)

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

        # was experimenting with radio buttons
        # for orientation. doesn't work
        # keeping it here for a while for future reference

        # layout = QVBoxLayout()
        #
        # widget = QWidget(self)  # central widget
        # widget.setLayout(layout)
        #
        # self.orientation_radio = QButtonGroup(widget)
        #
        # self.horizontal_radio = QRadioButton("Horizontal")
        # self.orientation_radio.addButton(self.horizontal_radio)
        # self.vertical_radio = QRadioButton("Vertical")
        # self.vertical_radio.setChecked(True)
        # self.orientation_radio.addButton(self.vertical_radio)
        # layout.addWidget(self.horizontal_radio)
        # layout.addWidget(self.vertical_radio)

        self.checkbox = QCheckBox('Orientation')
        layout = QVBoxLayout()
        layout.addWidget(self.checkbox)
        self.setLayout(layout)

        self.layer_state = layer_artist.state


class TutorialLayerStyleEditor(QWidget):

    def __init__(self, layer, parent=None):
        super(TutorialLayerStyleEditor, self).__init__(parent=parent)

        self.ui = load_ui('layer_style_editor.ui', self,
                          directory=os.path.dirname(__file__))

        connect_kwargs = {'alpha': dict(value_range=(0, 1))}

        autoconnect_callbacks_to_qt(layer.state, self.ui, connect_kwargs)


from glue.config import viewer_tool
from glue.viewers.common.qt.tool import CheckableTool


@viewer_tool
class MyCustomButton(CheckableTool):
    icon = 'myicon.png'
    tool_id = 'custom_tool'
    action_text = 'Does cool stuff'
    tool_tip = 'Does cool stuff'
    status_tip = 'Instructions on what to do now'
    shortcut = 'D'

    def __init__(self, viewer):
        super(MyCustomMode, self).__init__(viewer)

    def activate(self):
        pass

    def deactivate(self):
        pass

    def close(self):
        pass


class TutorialDataViewer(MatplotlibDataViewer):
    LABEL = 'Tree Viewer'
    _state_cls = TutorialViewerState
    _options_cls = TutorialViewerStateWidget
    _layer_style_widget_cls = TutorialLayerStateWidget
    _data_artist_cls = TutorialLayerArtist
    _subset_artist_cls = TutorialLayerArtist
    _tool = MyCustomButton
    _layer_style_widget_cls = TutorialLayerStyleEditor

    tools = ['select:rectangle']

    def __init__(self, *args, **kwargs):
        super(TutorialDataViewer, self).__init__(*args, **kwargs)
        self.axes.set_xticks([])
        self.axes.spines['top'].set_visible(False)
        self.axes.spines['bottom'].set_visible(False)
        # self.state.add_callback('_layout', self._update_limits)
        # self._update_limits()

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
