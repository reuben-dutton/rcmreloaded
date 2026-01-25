import pickle

TREE_PATH = 'data/tree.pickle'

with open(TREE_PATH, 'rb') as b:
    tree, labels = pickle.load(b)


def rgb_to_hex(rgb: tuple[int, int, int]):
    return ('#%02x%02x%02x' % rgb).upper()

def rgb_to_name(rgb: tuple[int, int, int]):
    dist, ind = tree.query(rgb, k=1)
    return labels[ind]
