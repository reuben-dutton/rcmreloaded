import pickle

TREE_PATH = 'data/tree.pickle'

with open(TREE_PATH, 'rb') as b:
    tree, labels = pickle.load(b)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return ('#%02x%02x%02x' % rgb).upper()

def rgb_to_name(rgb: tuple[int, int, int]) -> str:
    _, ind = tree.query(rgb, k=1)
    return labels[ind]

def hex_to_rgb(hex_color) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError("Hex color must be 6 characters long")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16)
    )

