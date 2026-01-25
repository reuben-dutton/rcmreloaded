import dataclasses

from models.utils import (
    rgb_to_hex,
    rgb_to_name,
)


@dataclasses.dataclass
class Colour:
    
    rgb: tuple[int, int, int]
    name: str
    hexcode: str

    @classmethod
    def from_rgb(cls, rgb: tuple[int, int, int]):
        return Colour(
            rgb=rgb,
            name=rgb_to_name(rgb),
            hexcode=rgb_to_hex(rgb),
        )