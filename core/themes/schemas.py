'''
The ``Theme`` DTO: the application shape of a theme.

A ``Theme`` is a plain container over one or more colour-space regions (defined
in core.themes.regions), which core.themes.library deserialises from the stored
blobs. A colour is accepted by drawing one region uniformly at random and
testing it, so over a generation every accepted colour is equally likely to
have come from each region. Combine single-region Themes with ``|``:

    themes.get('sunset') | themes.get('vaporwave')

A Theme carries no stored metadata of its own; ``name`` is derived from its
regions for display.
'''

from __future__ import annotations

import random
import typing

from core.themes.regions import DefaultThemeRegion, _ThemeRegionBase

if typing.TYPE_CHECKING:
    from core.colours.schemas import Colour


class Theme:

    def __init__(self, regions: list[_ThemeRegionBase]):
        # flatten so a | b | c stays one level deep
        flat: list[_ThemeRegionBase] = []
        for region in regions:
            flat.extend(region.regions if isinstance(region, Theme) else [region])
        self.regions = flat

    @property
    def INVARIANT(self) -> bool:
        # unconstrained only if every region is (i.e. the default theme)
        return all(region.INVARIANT for region in self.regions) if self.regions else True

    @property
    def name(self) -> str:
        return ' + '.join(region.name for region in self.regions)

    def accepted(self, colour: Colour) -> bool:
        if not self.regions:
            return True
        active = random.randrange(len(self.regions))
        return self.regions[active].accepted(colour)

    def __or__(self, other: "Theme | _ThemeRegionBase") -> "Theme":
        if isinstance(other, Theme):
            return Theme(self.regions + other.regions)
        if isinstance(other, _ThemeRegionBase):
            return Theme(self.regions + [other])
        return NotImplemented


def default_theme() -> Theme:
    '''The unconstrained 'everything' theme - a single default region.'''
    return Theme([DefaultThemeRegion()])
