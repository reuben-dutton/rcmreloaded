'''
Pydantic DTO for colours.

``Colour`` supersedes the old ``models.colour.Colour`` dataclass. It is built
straight from the ORM record with ``from_attributes`` (``model_validate(record)``)
and carries the same convenience interface the dataclass exposed so callers
barely change.

Themes have no DTO: the db layer deserializes the stored blob straight into the
live ``pipeline.themes.KDETheme`` (see db/repository.py).
'''

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from db.utils.convert import hex_to_rgb, rgb_to_hex
from db.utils.naming import rgb_to_name


class Colour(BaseModel):
    '''A named colour. Mirrors the old Colour dataclass interface.'''

    model_config = ConfigDict(from_attributes=True)

    name: str
    rgb: tuple[int, int, int]
    hexcode: str

    @property
    def rgb1(self) -> tuple[float, float, float]:
        return (self.rgb[0] / 255, self.rgb[1] / 255, self.rgb[2] / 255)

    @classmethod
    def from_rgb(cls, rgb: tuple[int, int, int]) -> 'Colour':
        # callers pass numpy scalars; coerce so pydantic validation accepts them
        rgb = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        return cls(rgb=rgb, name=rgb_to_name(rgb), hexcode=rgb_to_hex(rgb))

    @classmethod
    def from_hex(cls, hexcode: str) -> 'Colour':
        return cls.from_rgb(hex_to_rgb(hexcode))
