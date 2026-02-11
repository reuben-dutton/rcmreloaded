import dataclasses

from models.utils import (
    rgb_to_hex,
    rgb_to_name,
    hex_to_rgb,
)


@dataclasses.dataclass
class Colour:
    
    rgb: tuple[int, int, int]
    name: str
    hexcode: str

    @property
    def rgb1(self) -> tuple[float, float, float]:
        return (self.rgb[0] / 255, self.rgb[1] / 255, self.rgb[2] / 255)

    @classmethod
    def from_rgb(cls, rgb: tuple[int, int, int]):
        return Colour(
            rgb=rgb,
            name=rgb_to_name(rgb),
            hexcode=rgb_to_hex(rgb),
        )

    @classmethod
    def from_hex(cls, hexcode: str):
        rgb = hex_to_rgb(hexcode)
        return Colour(
            rgb=rgb,
            name=rgb_to_name(rgb),
            hexcode=rgb_to_hex(rgb),
        )
