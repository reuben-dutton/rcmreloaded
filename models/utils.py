import pickle

TREE_PATH = 'data/tree.pickle'

with open(TREE_PATH, 'rb') as b:
    tree, labels = pickle.load(b)


def rgb_to_hex(rgb: tuple[int, int, int]):
    return ('#%02x%02x%02x' % rgb).upper()

def rgb_to_name(rgb: tuple[int, int, int]):
    dist, ind = tree.query(rgb, k=1)
    return labels[ind]

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError("Hex color must be 6 characters long")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

