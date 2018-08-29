import numpy as np

from matplotlib.collections import LineCollection


def dendro_layout(parent, height, orientation='bottom-up'):
    """
    Summarizing functions that outputs the line collectionself.
    """

    leafness = calculate_leafness(parent)
    children = calculate_children(parent, leafness)

    xpos = calculate_xpos(parent, leafness, children)
    verts, verts_horiz = calculate_verts(parent, height, leafness, xpos,
                                         orientation=orientation)

    # line_collection = LineCollection(verts,
    #                                  colors = 'k',
    #                                  linestyle = 'solid')

    # return line_collection
    return verts, verts_horiz
    # return xpos, height


def calculate_leafness(parent):
    leafness = []

    for idx in range(len(parent)):
        if idx != (len(parent) - 1):
            leafness.append('leaf' if (parent[idx] >= parent[idx + 1]) else 'branch')
        else:
            leafness.append('leaf')

    return leafness


def calculate_nleaf(parent):
    leafness = calculate_leafness(parent)
    leafness = np.asarray(leafness)

    return np.sum(leafness == 'leaf')


def calculate_children(parent, leafness):
    children = []

    iter_array = np.array(range(len(parent)))

    for idx in iter_array:
        if leafness[idx] == 'branch':
            child = iter_array[(parent == idx)]
        else:
            child = np.array([])

        children.append(child)

    return children


def calculate_subtree(parent, leafness):
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
    # sortby_array = height

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


'''
Below is the function(s) taken from the old dendroviewer to help selection.
'''

def _substructures(parent, idx):
    """
    Return an array of all substructure indices of a given index.
    The input is included in the output.
    Parameters
    ----------
    idx : int
        The structure to extract.
    Returns
    -------
    array
    """
    children = _dendro_children(parent)
    result = []
    if np.isscalar(idx):
        todo = [idx]
    else:
        todo = idx.tolist()

    while todo:
        result.append(todo.pop())
        todo.extend(children[result[-1]])
    return np.array(result, dtype=np.int)
