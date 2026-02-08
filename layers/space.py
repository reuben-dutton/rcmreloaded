from PIL import (
    Image,
    ImageDraw,
    ImageFilter,
    ImageFont,
)

from layers.base import BaseLayer
from layers.constants import (
    DEFAULT_WHITE_COLOUR,
    DEFAULT_BLACK_COLOUR,
    DEFAULT_NONE_COLOUR,
    DEFAULT_SIZE,
)


RGB_ICON_BASE_PATH = 'rgb_base.png'
RGB_ICON_SHADOW_PATH = 'rgb_shadow.png'

ICON_SIZE = (48, 48)

BLUR_RADIUS = 2



class SwatchLayer(BaseLayer):
    def __init__(self, start: int):
        self.start = start
    
    def _create_layer(self):
        layer = Image.new("RGBA", size=DEFAULT_SIZE, color=DEFAULT_NONE_COLOUR)

        swatch_size = (DEFAULT_SIZE[0], DEFAULT_SIZE[1] - self.start)
        swatch = Image.new("RGBA", size=swatch_size, color=DEFAULT_WHITE_COLOUR)

        layer.paste(swatch, (0, self.start))

        return layer


class SpaceIconLayer(BaseLayer):
    
    def __init__(self, position: tuple[int, int]):
        self.position = position


    def _create_layer(self):
        # create shadow layer

        shadow_layer = Image.new("RGBA", size=DEFAULT_SIZE, color=DEFAULT_NONE_COLOUR)
        icon_shadow = Image.open(RGB_ICON_SHADOW_PATH).convert('RGBA')

        icon_shadow = icon_shadow.resize(ICON_SIZE)

        shadow_layer.paste(icon_shadow, self.position, icon_shadow)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=BLUR_RADIUS))

        # create base layer

        base_layer = Image.new("RGBA", size=DEFAULT_SIZE, color=DEFAULT_NONE_COLOUR)
        icon_base = Image.open(RGB_ICON_BASE_PATH).convert("RGBA")

        icon_base = icon_base.resize(ICON_SIZE)

        base_layer.paste(icon_base, self.position, icon_base)

        result = Image.alpha_composite(shadow_layer, base_layer)
        
        return result
