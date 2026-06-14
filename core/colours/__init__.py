'''
The colour domain: the ``Colour`` DTO, its factory/library, the naming tree,
the rgb<->hex helpers, and the colour-table repository.
'''

from core.colours.convert import hex_to_rgb, rgb_to_hex
from core.colours.naming import load_tree, rgb_to_name, save_tree
from core.colours.schemas import Colour
from core.colours.library import ColourLibrary, colours
from core.colours.repository import all_colours, get_colour, upsert_colour

__all__ = [
    'Colour',
    'ColourLibrary',
    'colours',
    'hex_to_rgb',
    'rgb_to_hex',
    'rgb_to_name',
    'load_tree',
    'save_tree',
    'all_colours',
    'get_colour',
    'upsert_colour',
]
