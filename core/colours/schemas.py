'''
The ``Colour`` DTO: a frozen, immutable data container with no logic.

Construction (and the colour naming that fills ``name``) lives in
core.colours.library (the ``ColourLibrary``); this class is pure data. It is
still built from a ``ColourRecord`` via ``from_attributes``
(``model_validate(record)``).
'''

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Colour(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    name: str
    rgb: tuple[int, int, int]
    hexcode: str

    @property
    def rgb1(self) -> tuple[float, float, float]:
        return (self.rgb[0] / 255, self.rgb[1] / 255, self.rgb[2] / 255)
