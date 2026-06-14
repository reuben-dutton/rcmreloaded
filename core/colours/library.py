'''
The colour library: the single factory for ``Colour`` value objects.

``Colour`` itself is a dumb data container; construction lives here. ``make``
(and ``make_hex``) always name the colour via the DB-backed nearest-neighbour
lookup tree (core.colours.naming), so every ``Colour`` the library hands out is
fully populated - there is no such thing as an unnamed colour.
'''

from __future__ import annotations

from core.colours.convert import hex_to_rgb, rgb_to_hex
from core.colours.naming import rgb_to_name
from core.colours.schemas import Colour


class ColourLibrary:
    '''Constructs named ``Colour`` objects from rgb or hex.'''

    def make(self, rgb: tuple[int, int, int]) -> Colour:
        # callers pass numpy scalars; coerce so pydantic validation accepts them
        rgb = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        return Colour(rgb=rgb, hexcode=rgb_to_hex(rgb), name=rgb_to_name(rgb))

    def make_hex(self, hexcode: str) -> Colour:
        return self.make(hex_to_rgb(hexcode))


# process-wide colour library
colours = ColourLibrary()
