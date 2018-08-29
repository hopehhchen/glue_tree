import os
from operator import itemgetter

import numpy as np

from matplotlib.collections import LineCollection
import matplotlib.cm as cm
import matplotlib.colors as mplcolors
from glue.config import viewer_tool
from glue.viewers.common.qt.tool import CheckableTool

from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QButtonGroup, QRadioButton, QHBoxLayout

from glue.config import qt_client, colormaps
from glue.core.data_combo_helper import ComponentIDComboHelper

from glue.external.echo import (CallbackProperty,
                                SelectionCallbackProperty,
                                delay_callback)
from glue.external.echo.qt import (connect_checkable_button,
                                   autoconnect_callbacks_to_qt,
                                   connect_value)

from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.matplotlib.state import (MatplotlibDataViewerState,
                                           MatplotlibLayerState,
                                           DeferredDrawCallbackProperty as DDCProperty,
                                           DeferredDrawSelectionCallbackProperty as DDSCProperty)
from glue.viewers.matplotlib.qt.data_viewer import MatplotlibDataViewer

from glue.utils.qt import load_ui, fix_tab_widget_fontsize, messagebox_on_error
from glue.utils import defer_draw

from dendro_helpers import (dendro_layout,
                            calculate_nleaf,
                            sort1Darrays,
                            calculate_leafness,
                            calculate_children,
                            calculate_subtree,
                            calculate_xpos)

from glue.core.roi import PointROI, RectangularROI, XRangeROI, YRangeROI
from glue.core.subset import CategorySubsetState
from glue.core.exceptions import IncompatibleDataException
from glue.core.subset import Subset

from glue.plugins.dendro_viewer.compat import update_dendrogram_viewer_state

CMAP_PROPERTIES = set(['cmap_mode', 'cmap_att', 'cmap_vmin', 'cmap_vmax', 'cmap'])
DATA_PROPERTIES = set(['layer', 'x_att', 'y_att', 'cmap_mode'])










# TODO
# move this back to data factory part
# works as of now :)
"""
adding data factory part here
to do 'kind of' integration testing
"""


from glue.config import data_factory
from glue.core import Data
import numpy as np
import re


def is_newick(filename, **kwargs):
    return filename.endswith('.nwk')


def parse(newick):
    tokens = re.findall(r"([^:;,()\s]*)(?:\s*:\s*([\d.]+)\s*)?([,);])|(\S)", newick+";")

    def recurse(nextid = 0, parentid = -1): # one node
        thisid = nextid;
        children = []
        name, length, delim, ch = tokens.pop(0)
        if ch == "(":
            while ch in "(,":
                node, ch, nextid = recurse(nextid+1, thisid)
                children.append(node)
            name, length, delim, ch = tokens.pop(0)

        return {"id": thisid, "name": name, "length": float(length) if length else None,
                "parentid": parentid, "children": children}, delim, nextid

    return recurse()[0]

# names = []
# size = []
# parent = []

# def clear_arrays(names, size, parent):
#     names.clear()
#     size.clear()
#     parent.clear()
#     return names, size, parent


def extract_arrays(tree_structure, names, parent, size):
    names.append(tree_structure['name'])
    parent.append(tree_structure['parentid'])
    size.append(tree_structure['length'])
    if tree_structure['children']:
        for sub_dicts in tree_structure['children']:
            extract_arrays(sub_dicts, names, parent, size)


@data_factory('Newick data loader', is_newick, priority=10000)
def read_newick(file_name):

    with open(file_name, 'r') as f:
        newick_tree = f.readline()

    # Open and parse newick file
    # convert newick file into parent array
    names = []
    size = []
    parent = []

    newick_in = parse(newick_tree)
    # names, size, parent = clear_arrays(names, size, parent)
    extract_arrays(newick_in, names, parent, size)

    # TODO
    # optimize this
    # currently storing everything in a
    # test object and then
    # using the test object to calculate height

    if (size[0] == None):
        size[0] = 0

    data = Data(label='newick file')
    data['parent'] = parent
    data['names'] = names
    data['size'] = size

    heights = np.zeros(len(data['parent']))
    idx = np.array(range(len(data['parent'])))

    for pix in idx:
        heights[idx[(data['parent'] == pix)]] += (data['size'][pix] + heights[pix])

    heights = heights + data['size']

    data['height'] = heights

    # data = Data(label='newick file')
    # data['parent'] = parent
    # data['names'] = names
    # data['size'] = size
    # data['height'] = [0,0.1,0.2,0.5,0.8,.9,.35,.6,.75,.85,.9,0.25,.3,.4,.5]

    return data


"""
end of data factory part
"""










class TutorialViewerState(MatplotlibDataViewerState):
    # x is parent; y is height.
    x_att = SelectionCallbackProperty(docstring='The attribute to use on the x-axis')
    y_att = SelectionCallbackProperty(docstring='The attribute to use on the y-axis')
    # change to parent and height
    # Tom is awesome!
    orientation = SelectionCallbackProperty(docstring='The orientation ....')
    sort_by = SelectionCallbackProperty(docstring='Sort by option ....')
    select_substruct = DDCProperty(True)


    def __init__(self, *args, **kwargs):
        # provides dropdown, parent, height etc. for plot options
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
        # populates attributes
        self._x_att_helper.set_multiple_data(self.layers_data)
        self._y_att_helper.set_multiple_data(self.layers_data)

    def _on_attribute_change(self, value):
        if self.y_att is not None:
            # used for labels and axes depedning on orientation

            if (self.orientation == 'bottom-up') or (self.orientation == 'top-down'):
                self.x_axislabel = ''
                self.y_axislabel = self.y_att.label
            elif (self.orientation == 'left-right') or (self.orientation == 'right-left'):
                self.x_axislabel = self.y_att.label
                self.y_axislabel = ''


class TutorialLayerState(MatplotlibLayerState):

    # cmap is stuff used for colormap

    linewidth = CallbackProperty(1, docstring='line width')
    cmap_mode = DDSCProperty(docstring="Whether to use color to encode an attribute")
    cmap_att = DDSCProperty(docstring="The attribute to use for the color")
    cmap_vmin = DDCProperty(docstring="The lower level for the colormap")
    cmap_vmax = DDCProperty(docstring="The upper level for the colormap")
    cmap = DDCProperty(docstring="The colormap to use (when in colormap mode)")

    def __init__(self, viewer_state=None, layer=None, **kwargs):
        super(TutorialLayerState, self).__init__(viewer_state=viewer_state, layer=layer)

        # set choices basically poplutes drop down menus

        TutorialLayerState.cmap_mode.set_choices(self, ['Fixed', 'Linear'])

        self.cmap_att_helper = ComponentIDComboHelper(self, 'cmap_att',
                                                      numeric = True, categorical = False)
        self.add_callback('layer', self._on_layers_change)

        # kind of initializing. not having this line
        # made errors for cmap initialization- didn't pull
        # up linear part
        # thanks tom
        self._on_layers_change()

    def _on_layers_change(self, layer=None):

        # not exactly sure of this
        with delay_callback(self, 'cmap_vmin', 'cmap_vmax'):

            self.cmap_att_helper.set_multiple_data([self.layer])
            # not having this line threw None resulting in an error- can't
            # iterate over None....
            # this initializes some colormap
            # thanks tom
            self.cmap = colormaps.members[0][1]


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
        #
        self.state.add_callback('cmap_mode', self._on_visual_change)
        self.state.add_callback('cmap_att', self._on_visual_change)
        self.state.add_callback('cmap_vmin', self._on_visual_change)
        self.state.add_callback('cmap_vmax', self._on_visual_change)
        self.state.add_callback('cmap', self._on_visual_change)

        self._viewer_state.add_callback('x_att', self._on_attribute_change)
        self._viewer_state.add_callback('y_att', self._on_attribute_change)
        self._viewer_state.add_callback('orientation', self._on_attribute_change)
        self._viewer_state.add_callback('sort_by', self._on_attribute_change)


    def _on_visual_change(self, value=None):

        # parent
        x = self.state.layer.data[self._viewer_state.x_att]
        # height
        y = self.state.layer.data[self._viewer_state.y_att]
        if len(self.state.layer[self._viewer_state.x_att]) == 0:
            return

        orientation = self._viewer_state.orientation
        sort_by_array = self.state.layer.data[self._viewer_state.sort_by]
        x, y, iter_array_updated = sort1Darrays(x, y, sort_by_array)
        verts, verts_horiz = dendro_layout(x, y, orientation=orientation)


        self.artist.set_visible(self.state.visible)
        self.artist.set_zorder(self.state.zorder)

        ## set colors
        if self.state.cmap_mode is not None:
            color_code = self.state.cmap_mode
            color_code_by = self.state.layer.data[self.state.cmap_att]
            color_code_by = color_code_by[iter_array_updated]
            color_code_cmap = self.state.cmap
            color_code_vmin = self.state.cmap_vmin
            color_code_vmax = self.state.cmap_vmax
        else:
            color_code = 'Fixed'


        if color_code == 'Fixed':

            colors_final = self.state.color

        elif color_code == 'Linear':

            cmap = color_code_cmap
            normalize = mplcolors.Normalize(color_code_vmin, color_code_vmax)
            colors = [cmap(normalize(yi)) for yi in color_code_by]
            colors_horiz = []
            
            for i in range(len(verts_horiz)):
                colors_horiz.append((0., 0., 0., 1.))

            colors_final = np.concatenate([colors, colors_horiz])

        self.lc.set_color(colors_final)


        # linewidth
        self.lc.set_linewidth(self.state.linewidth)
        # self.artist.set_markeredgecolor(self.state.color)
        # if self.state.fill:
        #     self.artist.set_markerfacecolor(self.state.color)
        # else:
        #     self.artist.set_markerfacecolor('white')
        # opacity
        self.artist.set_alpha(self.state.alpha)

        self.redraw()

    def _on_attribute_change(self, value=None):

        if self._viewer_state.x_att is None or self._viewer_state.y_att is None:
            return

        # parent
        x = self.state.layer.data[self._viewer_state.x_att]
        # height
        y = self.state.layer.data[self._viewer_state.y_att]

        if len(self.state.layer[self._viewer_state.x_att]) == 0:
            return

        leafness = calculate_leafness(x)


        orientation = self._viewer_state.orientation

        # sort_by_array = None for using the original order
        # sort_by_array = y for sort by height
        sort_by_array = self.state.layer.data[self._viewer_state.sort_by]
        x, y, iter_array_updated = sort1Darrays(x, y, sort_by_array)

        verts, verts_horiz = dendro_layout(x, y, orientation=orientation)
        if isinstance(self.state.layer, Subset):
            subset_mask = self.state.layer.to_index_list()
            subset_mask = np.array([ID in subset_mask for ID in iter_array_updated])
            subset_mask = np.where(subset_mask)[0]
            verts = itemgetter(*subset_mask)(verts)
            #id_horiz = np.where([ID in np.where(np.array(leafness) == 'branch')[0] for ID in subset_mask])[0]
            #id_horiz = np.where((subset_mask in id_horiz))
            verts_horiz = []

        verts = verts if (np.ndim(verts) == 3.) else [verts]
        #verts_horiz = verts_horiz if (np.ndim(verts_horiz) == 3.) else [verts_horiz]

        nleaf = calculate_nleaf(x)

        if len(verts_horiz) != 0.:
            verts_final = np.concatenate([verts, verts_horiz])
        else:
            verts_final = verts


        if self.state.cmap_mode is 'Linear':
            color_code = self.state.cmap_mode
            color_code_by = self.state.layer.data[self.state.cmap_att]
            color_code_by = color_code_by[iter_array_updated]
            color_code_cmap = self.state.cmap
            color_code_vmin = self.state.cmap_vmin
            color_code_vmax = self.state.cmap_vmax


            cmap = color_code_cmap
            normalize = mplcolors.Normalize(color_code_vmin, color_code_vmax)

            print(cmap, color_code_vmin, color_code_vmax, color_code_by)

            colors = [cmap(normalize(yi)) for yi in color_code_by]
            colors_horiz = []
            for i in range(len(verts_horiz)):
                colors_horiz.append((0., 0., 0., 1.))

            colors_final = np.concatenate([colors, colors_horiz])

            self.lc.set_color(colors_final)

        # self.artist.set_data(x, y)
        self.lc.set_segments(verts_final)


        # parent
        xmin = (-.5)
        xmax = nleaf + 1.5
        # height
        ymin, ymax = np.nanmin(y), np.nanmax(y)


        # y_log = True
        # if y_log:
        #
        #     ymin = np.min(y[y > 0.])
        #     ###
        #     ymin = np.exp(np.log(ymin)-.05*(np.log(ymax) - np.log(ymin)))
        #     ymax = np.exp(np.log(ymax)+.05*(np.log(ymax) - np.log(ymin)))
        #
        # else:
        #
        #     ymin = ymin - .05 * (ymax - ymin)
        #     ymax = ymax + .05 * (ymax - ymin)

        ymin = ymin - .05 * (ymax - ymin)
        ymax = ymax + .05 * (ymax - ymin)

        self.axes.set_xscale('linear')
        self.axes.set_yscale('linear')

        # handling all 4 orientations

        if orientation == 'bottom-up':
            self.axes.set_xlim(xmin, xmax)
            self.axes.set_ylim(ymin, ymax)

            self.axes.tick_params(bottom = False,
                                  top = False,
                                  left = True,
                                  right = False,
                                  labelbottom = False,
                                  labeltop = False,
                                  labelleft = True,
                                  labelright = False)
            self.axes.spines['top'].set_visible(False)
            self.axes.spines['bottom'].set_visible(False)
            self.axes.spines['left'].set_visible(True)
            self.axes.spines['right'].set_visible(True)

            # if y_log:
            #     self.axes.set_yscale('log')

        elif orientation == 'top-down':
            self.axes.set_xlim(xmin, xmax)
            self.axes.set_ylim(ymax, ymin)

            self.axes.tick_params(bottom = False,
                                  top = False,
                                  left = True,
                                  right = False,
                                  labelbottom = False,
                                  labeltop = False,
                                  labelleft = True,
                                  labelright = False)
            self.axes.spines['top'].set_visible(False)
            self.axes.spines['bottom'].set_visible(False)
            self.axes.spines['left'].set_visible(True)
            self.axes.spines['right'].set_visible(True)

            # if y_log:
            #     self.axes.set_yscale('log')

        elif orientation == 'left-right':
            self.axes.set_ylim(xmin, xmax)
            self.axes.set_xlim(ymin, ymax)

            self.axes.tick_params(bottom = True,
                                  top = False,
                                  left = False,
                                  right = False,
                                  labelbottom = True,
                                  labeltop = False,
                                  labelleft = False,
                                  labelright = False)
            self.axes.spines['top'].set_visible(True)
            self.axes.spines['bottom'].set_visible(True)
            self.axes.spines['left'].set_visible(False)
            self.axes.spines['right'].set_visible(False)

            # if y_log:
            #     self.axes.set_xscale('log')

        elif orientation == 'right-left':
            self.axes.set_ylim(xmin, xmax)
            self.axes.set_xlim(ymax, ymin)

            self.axes.tick_params(bottom = True,
                                  top = False,
                                  left = False,
                                  right = False,
                                  labelbottom = True,
                                  labeltop = False,
                                  labelleft = False,
                                  labelright = False)
            self.axes.spines['top'].set_visible(True)
            self.axes.spines['bottom'].set_visible(True)
            self.axes.spines['left'].set_visible(False)
            self.axes.spines['right'].set_visible(False)

            # if y_log:
            #     self.axes.set_xscale('log')


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
        
        self.setLayout(layout)
        self.layer_state = layer_artist.state


class TutorialLayerStyleEditor(QWidget):

    def __init__(self, layer, parent=None):

        super(TutorialLayerStyleEditor, self).__init__(parent=parent)

        self.ui = load_ui('layer_style_editor.ui', self,
                          directory=os.path.dirname(__file__))

        connect_kwargs = {'alpha': dict(value_range=(0, 1))}
                          # 'size_scaling': dict(value_range=(0.1, 10), log=True),
                          # 'density_contrast': dict(value_range=(0, 1)),
                          # 'vector_scaling': dict(value_range=(0.1, 10), log=True)
        autoconnect_callbacks_to_qt(layer.state, self.ui, connect_kwargs)

        # connect_value(layer.state.viewer_state, 'dpi', self.ui.value_dpi,
        #               value_range=(12, 144), log=True)

        fix_tab_widget_fontsize(self.ui.tab_widget)

        self.layer_state = layer.state
        self.layer_state.add_callback('cmap_mode', self._update_cmap_mode)
        self.layer_state.add_callback('layer', self._update_warnings)

        self._update_cmap_mode()

        self._update_warnings()

    def _update_warnings(self, *args):

        if self.layer_state.layer is None:
            n_points = 0
        else:
            n_points = np.product(self.layer_state.layer.shape)

        warning = " (may be slow given data size)"

        for combo, threshold in [(self.ui.combosel_cmap_mode, 50000)]:

            if n_points > threshold and not self.layer_state.density_map:
                for item in range(combo.count()):
                    text = combo.itemText(item)
                    if text != 'Fixed':
                        combo.setItemText(item, text + warning)
                        combo.setItemData(item, QtGui.QBrush(Qt.red), Qt.TextColorRole)
            else:
                for item in range(combo.count()):
                    text = combo.itemText(item)
                    if text != 'Fixed':
                        if warning in text:
                            combo.setItemText(item, text.replace(warning, ''))
                            combo.setItemData(item, QtGui.QBrush(), Qt.TextColorRole)


    def _update_line_visible(self, *args):
        self.ui.value_linewidth.setEnabled(self.layer_state.line_visible)
        self.ui.combosel_linestyle.setEnabled(self.layer_state.line_visible)


    def _update_cmap_mode(self, cmap_mode=None):

        if self.layer_state.cmap_mode == 'Fixed':
            self.ui.label_cmap_attribute.hide()
            self.ui.combosel_cmap_att.hide()
            self.ui.label_cmap_limits.hide()
            self.ui.valuetext_cmap_vmin.hide()
            self.ui.valuetext_cmap_vmax.hide()
            self.ui.button_flip_cmap.hide()
            self.ui.combodata_cmap.hide()
            self.ui.label_colormap.hide()
            self.ui.color_color.show()
        else:
            self.ui.label_cmap_attribute.show()
            self.ui.combosel_cmap_att.show()
            self.ui.label_cmap_limits.show()
            self.ui.valuetext_cmap_vmin.show()
            self.ui.valuetext_cmap_vmax.show()
            self.ui.button_flip_cmap.show()
            self.ui.combodata_cmap.show()
            self.ui.label_colormap.show()
            self.ui.color_color.hide()


class TutorialDataViewer(MatplotlibDataViewer):
    LABEL = 'Tree Viewer'
    _state_cls = TutorialViewerState
    _options_cls = TutorialViewerStateWidget
    _layer_style_widget_cls = TutorialLayerStateWidget
    _data_artist_cls = TutorialLayerArtist
    _subset_artist_cls = TutorialLayerArtist
    _layer_style_widget_cls = TutorialLayerStyleEditor

    tools = ['select:rectangle',  'select:xrange', 'select:yrange', 'select:pick'] ### rectangle in the future?

    def __init__(self, *args, **kwargs):
        super(TutorialDataViewer, self).__init__(*args, **kwargs)

        # self.state.add_callback('_layout', self._update_limits)
        # self._update_limits()


    def initialize_toolbar(self):

        super(TutorialDataViewer, self).initialize_toolbar()

        def on_move(mode):
            if mode._drag:
                self.apply_roi(mode.roi())

        self.toolbar.tools['select:pick']._press_callback = on_move

    def close(self, *args, **kwargs):
        self.toolbar.tools['select:pick']._press_callback = None
        super(TutorialDataViewer, self).close(*args, **kwargs)

    @messagebox_on_error('Failed to add data')
    def add_data(self, data):
        if data.ndim != 1:
            raise IncompatibleDataException("Only 1-D data can be added to "
                                            "the dendrogram viewer (tried to add a {}-D "
                                            "dataset)".format(data.ndim))
        return super(TutorialDataViewer, self).add_data(data)

    # TODO: move some of the ROI stuff to state class?

    @defer_draw
    def apply_roi(self, roi, override_mode=None):

        # Force redraw to get rid of ROI. We do this because applying the
        # subset state below might end up not having an effect on the viewer,
        # for example there may not be any layers, or the active subset may not
        # be one of the layers. So we just explicitly redraw here to make sure
        # a redraw will happen after this method is called.
        self.redraw()

        # TODO Does subset get applied to all data or just visible data?

        # if self.state._layout is None:
        #     return

        if self.state.x_att is None or self.state.y_att is None:
            return

        if not roi.defined():
            return

        if len(self.layers) == 0:
            return

        if isinstance(roi, PointROI):

            x, y = roi.x, roi.y

            # calculate everything
            parent = self.state.layers_data[0][self.state.x_att]
            ys = self.state.layers_data[0][self.state.y_att]
            leafness = calculate_leafness(parent)
            children = calculate_children(parent, leafness)
            xs = calculate_xpos(parent, leafness, children)
            parent_ys = ys[parent]
            parent_ys[0] = ys[0]

            # sort everything
            sort_by_array = self.state.layers_data[0][self.state.sort_by]
            parent, ys, iter_array_updated = sort1Darrays(parent, ys, sort_by_array)
            leafness = calculate_leafness(parent)
            children = calculate_children(parent, leafness)
            xs = calculate_xpos(parent, leafness, children)
            parent_ys = parent_ys[np.asarray(iter_array_updated, dtype = np.int)]

            orientation = self.state.orientation

            if orientation in ['bottom-up', 'top-down']:
                delt = np.abs(x - xs)
                delt[y > ys] = np.nan
                delt[y < parent_ys] = np.nan
            elif orientation in ['left-right', 'right-left']:
                delt = np.abs(y - xs)
                delt[x > ys] = np.nan
                delt[x < parent_ys] = np.nan

            if np.isfinite(delt).any():
                select = np.nanargmin(delt)

                if self.state.select_substruct:
                    #leafness = calculate_leafness(parent)
                    subtree = calculate_subtree(parent, leafness)
                    select = np.concatenate([[int(select)],
                                             np.asarray(subtree[select], dtype = np.int)])
                select = np.asarray(select, dtype=np.int)
            else:
                select = np.array([], dtype=np.int)

            select = iter_array_updated[select]
            subset_state = CategorySubsetState(self.state.layers_data[0].components[0], select)

            self.apply_subset_state(subset_state)

        elif isinstance(roi, RectangularROI):

            xmin, xmax = roi.xmin, roi.xmax
            ymin, ymax = roi.ymin, roi.ymax


            # calculate everything
            parent = self.state.layers_data[0][self.state.x_att]
            ys = self.state.layers_data[0][self.state.y_att]
            leafness = calculate_leafness(parent)
            children = calculate_children(parent, leafness)
            xs = calculate_xpos(parent, leafness, children)
            parent_ys = ys[parent]
            parent_ys[0] = ys[0]

            # sort everything
            sort_by_array = self.state.layers_data[0][self.state.sort_by]
            parent, ys, iter_array_updated = sort1Darrays(parent, ys, sort_by_array)
            leafness = calculate_leafness(parent)
            children = calculate_children(parent, leafness)
            xs = calculate_xpos(parent, leafness, children)
            parent_ys = parent_ys[np.asarray(iter_array_updated, dtype = np.int)]

            orientation = self.state.orientation

            if orientation in ['bottom-up', 'top-down']:
                delt = np.arange(len(xs), dtype = np.float)
                delt[xs < xmin] = np.nan
                delt[xs > xmax] = np.nan
                delt[ymin > ys] = np.nan
                delt[ymax < parent_ys] = np.nan
            elif orientation in ['left-right', 'right-left']:
                delt = np.arange(len(xs), dtype = np.float)
                delt[xs < ymin] = np.nan
                delt[xs > ymax] = np.nan
                delt[xmin > ys] = np.nan
                delt[xmax < parent_ys] = np.nan

            if np.isfinite(delt).any():
                select = np.where(np.isfinite(delt))[0]

                if self.state.select_substruct:

                    subtree = calculate_subtree(parent, leafness)

                    for sl in select:

                        select = np.concatenate([select,
                                                 np.asarray(subtree[sl], dtype = np.int)])

                select = np.asarray(select, dtype=np.int)
            else:
                select = np.array([], dtype=np.int)

            select = iter_array_updated[select]
            subset_state = CategorySubsetState(self.state.layers_data[0].components[0], select)

            self.apply_subset_state(subset_state)



        elif isinstance(roi, XRangeROI):

            xmin, xmax = roi.min, roi.max

            # calculate everything
            parent = self.state.layers_data[0][self.state.x_att]
            ys = self.state.layers_data[0][self.state.y_att]
            leafness = calculate_leafness(parent)
            children = calculate_children(parent, leafness)
            xs = calculate_xpos(parent, leafness, children)
            parent_ys = ys[parent]
            parent_ys[0] = ys[0]

            # sort everything
            sort_by_array = self.state.layers_data[0][self.state.sort_by]
            parent, ys, iter_array_updated = sort1Darrays(parent, ys, sort_by_array)
            leafness = calculate_leafness(parent)
            children = calculate_children(parent, leafness)
            xs = calculate_xpos(parent, leafness, children)
            parent_ys = parent_ys[np.asarray(iter_array_updated, dtype = np.int)]

            orientation = self.state.orientation

            if orientation in ['bottom-up', 'top-down']:
                delt = np.arange(len(xs), dtype = np.float)
                delt[xs < xmin] = np.nan
                delt[xs > xmax] = np.nan
            elif orientation in ['left-right', 'right-left']:
                delt = np.arange(len(xs), dtype = np.float)
                delt[xmin > ys] = np.nan
                delt[xmax < parent_ys] = np.nan

            if np.isfinite(delt).any():
                select = np.where(np.isfinite(delt))[0]

                if self.state.select_substruct:

                    subtree = calculate_subtree(parent, leafness)

                    for sl in select:

                        select = np.concatenate([select,
                                                 np.asarray(subtree[sl], dtype = np.int)])

                select = np.asarray(select, dtype=np.int)
            else:
                select = np.array([], dtype=np.int)

            select = iter_array_updated[select]
            subset_state = CategorySubsetState(self.state.layers_data[0].components[0], select)

            self.apply_subset_state(subset_state)



        elif isinstance(roi, YRangeROI):

            ymin, ymax = roi.min, roi.max

            # calculate everything
            parent = self.state.layers_data[0][self.state.x_att]
            ys = self.state.layers_data[0][self.state.y_att]
            leafness = calculate_leafness(parent)
            children = calculate_children(parent, leafness)
            xs = calculate_xpos(parent, leafness, children)
            parent_ys = ys[parent]
            parent_ys[0] = ys[0]

            # sort everything
            sort_by_array = self.state.layers_data[0][self.state.sort_by]
            parent, ys, iter_array_updated = sort1Darrays(parent, ys, sort_by_array)
            leafness = calculate_leafness(parent)
            children = calculate_children(parent, leafness)
            xs = calculate_xpos(parent, leafness, children)
            parent_ys = parent_ys[np.asarray(iter_array_updated, dtype = np.int)]

            orientation = self.state.orientation

            if orientation in ['bottom-up', 'top-down']:
                delt = np.arange(len(xs), dtype = np.float)
                delt[ymin > ys] = np.nan
                delt[ymax < parent_ys] = np.nan
            elif orientation in ['left-right', 'right-left']:
                delt = np.arange(len(xs), dtype = np.float)
                delt[xs < ymin] = np.nan
                delt[xs > ymax] = np.nan

            if np.isfinite(delt).any():
                select = np.where(np.isfinite(delt))[0]

                if self.state.select_substruct:

                    subtree = calculate_subtree(parent, leafness)

                    for sl in select:

                        select = np.concatenate([select,
                                                 np.asarray(subtree[sl], dtype = np.int)])

                select = np.asarray(select, dtype=np.int)
            else:
                select = np.array([], dtype=np.int)

            select = iter_array_updated[select]
            subset_state = CategorySubsetState(self.state.layers_data[0].components[0], select)

            self.apply_subset_state(subset_state)
        else:
            raise TypeError("Only PointROI selections are supported")


    @staticmethod
    def update_viewer_state(rec, context):
        return update_dendrogram_viewer_state(rec, context)


qt_client.add(TutorialDataViewer)
