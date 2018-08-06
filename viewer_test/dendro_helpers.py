import numpy as np

from matplotlib.collections import LineCollection


def dendro_layout(parent, height, orientation = 'vertical'):
    '''
    Summarizing functions that outputs the line collectionself.
    '''

    leafness = calculate_leafness(parent)
    children = calculate_children(parent, leafness)

    xpos = calculate_xpos(parent, leafness, children)
    verts = calculate_verts(parent, height, leafness, xpos,
                            orientation = orientation)

    line_collection = LineCollection(verts,
                                     colors = 'k',
                                     linestyle = 'solid')

    #return line_collection
    return verts
    #return xpos, height




def calculate_leafness(parent):

    leafness = []


    for idx in range(len(parent)):

        if idx != (len(parent)-1):
            leafness.append('leaf' if (parent[idx] >= parent[idx+1]) else 'branch')
        else:
            leafness.append('leaf')

    return leafness


def calculate_children(parent, leafness):

    children = []

    iter_array = np.array(range(len(parent)))

    for idx in iter_array:

        if leafness[idx] == 'branch':

            child = iter_array[(parent == iter_array[idx])]

        else:

            child = np.array([])

        children.append(child)

    return children


######


def calculate_xpos(parent, leafness, children):

    x_pos = np.zeros(len(parent))

    iter_array = np.array(range(len(parent)))

    ## leaves
    _cached_pos = 1.
    for idx in iter_array[(np.array(leafness) == 'leaf')]:

        x_pos[idx] = _cached_pos
        _cached_pos += 1.


    ## branches
    #nlevels = 5
    nlevels = len(set(parent))  ### optimize this.
    for level in np.array(range(nlevels)):
        for idx in iter_array[(np.array(leafness) == 'branch')]:

            if x_pos[idx] == 0.:
                if np.all(x_pos[children[idx]] != 0.):
                    x_pos[idx] = np.mean(x_pos[children[idx]])

                else:
                    continue

            else:
                continue

    return x_pos



def calculate_verts(parent, height, leafness, x_pos, orientation = 'vertical'):

    verts = []

    iter_array = np.array(range(len(parent)))

    # vertices for vertical lines
    for idx in iter_array:

        if parent[idx] == -1:

            vert = np.array([[x_pos[idx], 0.],
                             [x_pos[idx], height[idx]]])

        else:

            vert = np.array([[x_pos[idx], height[parent[idx]]],
                             [x_pos[idx], height[idx]]])

        verts.append(vert)


    # vertices for horizontal lines
    for idx in iter_array:

        if leafness[idx] == 'branch':

            vert = np.array([[x_pos[iter_array[(parent == idx)][0]], height[idx]],
                             [x_pos[iter_array[(parent == idx)][-1]], height[idx]]])

        else:

            continue

        verts.append(vert)


    if orientation == 'vertical':
        return verts

    elif orientation == 'horizontal':

        verts_rot = []

        for vert in verts:

            _cache = np.zeros(vert.shape)

            _cache[:, 0] = vert[:, 1]
            _cache[:, 1] = vert[:, 0]

            verts_rot.append(_cache)

        return verts_rot
