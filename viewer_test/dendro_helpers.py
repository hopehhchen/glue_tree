import numpy as np

from matplotlib.collections import LineCollection

'''
Notes.
* The functions below assume the 1D arrays are derived from the data factory.
'''


def dendro_layout(parent, height, orientation='bottom-up'):
    '''
    Calculates the line coordinates.

    The function wraps around several other functions in this file.
    '''

    # calculate leafness (needed as input below)
    leafness = calculate_leafness(parent)
    # calculate children (needed as input below)
    children = calculate_children(parent, leafness)

    # calculate the x-position
    xpos = calculate_xpos(parent, leafness, children)
    # calculate the list of coordinates that can be used by LineCollection
    verts, verts_horiz = calculate_verts(parent, height, leafness, xpos,
                                         orientation=orientation)


    return verts, verts_horiz


def calculate_leafness(parent):
    '''
    Calculates whether structures are leaves or branches.
    '''

    leafness = []

    for idx in range(len(parent)):
        # A structure is a leaf if its parent has an id (index)
        # larger than the parent of the next structure.
        if idx != (len(parent) - 1):

            leafness.append('leaf' if (parent[idx] >= parent[idx + 1]) else 'branch')

        else:
            ## The last structure is always a leaf.
            leafness.append('leaf')

    return leafness


def calculate_nleaf(parent):
    '''
    Calculate the total number of leaves.

    The result is used for looping through the leaves in the calculation of
    the x-positions.
    '''

    leafness = calculate_leafness(parent)
    leafness = np.asarray(leafness)

    return np.sum(leafness == 'leaf')


def calculate_children(parent, leafness):
    '''
    Calculate the (direct) children of each structure.
    '''

    children = []

    iter_array = np.array(range(len(parent)))

    for idx in iter_array:
        # Does the calculation only for the branches.
        if leafness[idx] == 'branch':
            child = iter_array[(parent == idx)]
        else:
            child = np.array([])

        children.append(child)

    return children


def calculate_subtree(parent, leafness):
    '''
    Calculate the full subtree of each structure.

    The output is used for sorting to move subtrees together with their parents.
    '''

    subtree = []
    iter_array = np.array(range(len(parent)))
    nlevels = len(set(parent))

    for idx in iter_array:
        if leafness[idx] == 'branch':
            parent_own = parent[idx]
            if sum(parent == parent_own) == 1.:
                descendent = iter_array[1:]
            else:
                if sum((parent <= parent_own) & (iter_array > idx)) == 0.:
                    descendent = iter_array[(idx + 1):]
                else:
                    descendent = iter_array[(idx + 1):
                                            iter_array[np.where((parent <= parent_own) & (iter_array > idx))][0]]
        else:
            descendent = np.array([])

        subtree.append(descendent)

    return subtree


def calculate_xpos(parent, leafness, children):
    '''
    Calculate the x-positions of the structures.

    The output from this function is used to calculate the coordinates of the line segments.
    '''


    x_pos = np.zeros(len(parent))
    iter_array = np.array(range(len(parent)))

    # leaves
    _cached_pos = 1.
    for idx in iter_array[(np.array(leafness) == 'leaf')]:
        x_pos[idx] = _cached_pos
        _cached_pos += 1.

    # branches
    # nlevels = 5

    nlevels = len(set(parent))  # optimize this

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


def calculate_verts(parent, height, leafness, x_pos, orientation='bottom-up'):
    '''
    Calculate the coordinates of the line segments used by LineCollection.

    The output is a list of 2 by 2 array, corresponding to the starting and end points.
    '''

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

    verts_horiz = []

    # vertices for horizontal lines
    for idx in iter_array:
        if leafness[idx] == 'branch':
            vert = np.array([[x_pos[iter_array[(parent == idx)][0]], height[idx]],
                             [x_pos[iter_array[(parent == idx)][-1]], height[idx]]])
        else:
            continue

        verts_horiz.append(vert)

    if (orientation == 'bottom-up') or (orientation == 'top-down'):
        return verts, verts_horiz
    elif (orientation == 'left-right') or (orientation == 'right-left'):

        verts_rot = []

        for vert in verts:
            _cache = np.zeros(vert.shape)

            _cache[:, 0] = vert[:, 1]
            _cache[:, 1] = vert[:, 0]

            verts_rot.append(_cache)

        verts_horiz_rot = []

        for vert in verts_horiz:
            _cache = np.zeros(vert.shape)

            _cache[:, 0] = vert[:, 1]
            _cache[:, 1] = vert[:, 0]

            verts_horiz_rot.append(_cache)

        return verts_rot, verts_horiz_rot


def sort1Darrays(parent, height, sortby_array):
    '''
    Sorts array according to `sortby_array`.
    '''

    if sortby_array is None:
        return parent, height

    leafness = calculate_leafness(parent)
    subtree = calculate_subtree(parent, leafness)

    iter_array = np.array(range(len(parent)))

    iter_array_updated = iter_array.copy()
    parent_updated = parent.copy()

    for idx in iter_array:

        if sum(parent == idx) > 0.:
            args_0 = iter_array[parent == idx]
            sortby = sortby_array[parent == idx]
            args_sorted = args_0[np.argsort(sortby)]

            idx_j = np.where(iter_array_updated == idx)[0][0]

            for jdx in args_sorted:
                iter_array_updated[(idx_j + 1)] = jdx
                parent_updated[(idx_j + 1)] = np.where(iter_array_updated == idx)[0][0]

                descendent = subtree[jdx]
                if len(descendent) > 0.:
                    iter_array_updated[(idx_j + 2):(idx_j + 2 + len(descendent))] = descendent
                    parent_updated[(idx_j + 2):(idx_j + 2 + len(descendent))] = parent[descendent] + ((idx_j + 1) - jdx)
                idx_j = idx_j + (1 + len(descendent))
        else:
            continue

    # parent_updated = parent[iter_array_updated]
    height_updated = height[np.asarray(iter_array_updated, dtype = np.int)]

    return parent_updated, height_updated, iter_array_updated
