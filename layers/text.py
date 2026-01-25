import textwrap

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


# TODO: Replace the hard-coded positions with a more dynamic position
# created based on the provided DEFAULT_SIZE


# text-specific constants, not needed outside of this module

DEFAULT_BLUR_ITERATIONS = 2
DEFAULT_SHADOW_BLUR_RADIUS = 6


PRIMARY_FONT_PATH = 'fonts/Bayemalt-Regular.otf'
PRIMARY_FONT_SIZE = 144
PRIMARY_FONT = ImageFont.truetype(
    font=PRIMARY_FONT_PATH,
    size=PRIMARY_FONT_SIZE,
)

SECONDARY_FONT_PATH = 'fonts/SairaCondensed-Bold.ttf'
SECONDARY_FONT_SIZE = 72
SECONDARY_FONT = ImageFont.truetype(
    font=SECONDARY_FONT_PATH,
    size=SECONDARY_FONT_SIZE,
)


'''
    Utility function to generate text shadow.
'''
def create_text_shadow_sublayer(
    position: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    anchor: str,
    size: tuple[int, int] = DEFAULT_SIZE,
    color: tuple[int, int, int] = DEFAULT_BLACK_COLOUR,
    iterations: int = DEFAULT_BLUR_ITERATIONS,  # how thick the shadow should be
    blur_radius: int = DEFAULT_SHADOW_BLUR_RADIUS,  # how far the shadow should extend
):
    shadow_base = Image.new("RGBA", size=size, color=DEFAULT_NONE_COLOUR)
    shadow_layer = shadow_base
    for i in range(iterations):
        shadow_iteration = Image.new("RGBA", size=size, color=DEFAULT_NONE_COLOUR)
        shadow_canvas = ImageDraw.Draw(shadow_iteration)
        shadow_canvas.text(position, text, font=font, fill=DEFAULT_BLACK_COLOUR, anchor=anchor)
        shadow_iteration = shadow_iteration.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        shadow_layer = Image.alpha_composite(shadow_layer, shadow_iteration)
    return shadow_layer


class TextLayer(BaseLayer):

    def __init__(self, text: str):
        # position, font and anchor are hard-coded for each text layer
        if not self.font:
            raise Exception('Font should be set in __init__')
        if not self.position:
            raise Exception('Position should be set in __init__')
        if not self.anchor:
            raise Exception('Anchor should be set in __init__')

        if not text:
            raise Exception('Text must be provided')

        self.text = text

    def _create_layer(self):
        # create a layer for text shadow
        shadow_layer = create_text_shadow_sublayer(
            self.position,
            self.text,
            self.font,
            self.anchor
        )

        # create a layer for the raw text
        text_layer = Image.new("RGBA", size=DEFAULT_SIZE, color=DEFAULT_NONE_COLOUR)
        text_layer_canvas = ImageDraw.Draw(text_layer)
        text_layer_canvas.text(
            self.position,
            self.text,
            font=self.font,
            fill=DEFAULT_WHITE_COLOUR,
            anchor=self.anchor
        )

        # composit the layers
        result = Image.alpha_composite(shadow_layer, text_layer)

        return result


class NameTextLayer(TextLayer):

    def __init__(self, text: str):
        self.font = SECONDARY_FONT
        self.position = (600, 600 - 20) # slightly above center image
        self.anchor = "mb" # middle bottom
        super().__init__(text)


class HexcodeTextLayer(TextLayer):

    def __init__(self, text: str):
        self.font = PRIMARY_FONT
        self.position = (600, 600) # center image
        self.anchor = "mt"  # middle top
        super().__init__(text)