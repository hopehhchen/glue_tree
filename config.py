from glue.config import data_factory
from glue.core import Data
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

    if (size[0] == None):
        size[0] = 0

    data = Data(label='newick file')
    data['parent'] = parent
    data['names'] = names
    data['size'] = size

    return data
