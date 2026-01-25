import textwrap

import numpy as np
from PIL import (
    Image,
    ImageDraw,
    ImageFilter,
    ImageFont,
)


DEFAULT_WHITE_COLOUR = (255, 255, 255, 255)
DEFAULT_BLACK_COLOUR = (10, 10, 10, 255)
DEFAULT_NONE_COLOUR = (0, 0, 0, 0)
DEFAULT_SIZE = (1200, 1200)

PRIMARY_FONT_PATH = 'fonts/Bayemalt-Regular.otf'
PRIMARY_FONT = ImageFont.truetype(
    font=PRIMARY_FONT_PATH,
    size=144,
)

SECONDARY_FONT_PATH = 'fonts/SairaCondensed-Bold.ttf'
SECONDARY_FONT = ImageFont.truetype(
    font=SECONDARY_FONT_PATH,
    size=72,
)





base = np.float64(
    np.asarray(
        Image.new(
            "RGBA",
            size=DEFAULT_SIZE,
            color=(40, 117, 163, 255)
        )
    )
)

image = Image.fromarray(base.astype(np.uint8))
image.putalpha(255)


text_offsets = 20

text_layer = Image.new("RGBA", size=DEFAULT_SIZE, color=DEFAULT_NONE_COLOUR)



text = "PROMINENT BLUE"
pos = (600, 600 - text_offsets)


for i in range(2):
    blur = Image.new("RGBA", size=DEFAULT_SIZE, color=DEFAULT_NONE_COLOUR)
    blurcanvas = ImageDraw.Draw(blur)
    blurcanvas.text(pos, text, font=SECONDARY_FONT, fill=DEFAULT_BLACK_COLOUR, anchor="mb")
    blur = blur.filter(ImageFilter.GaussianBlur(radius=6))
    text_layer = Image.alpha_composite(text_layer, blur)

front = Image.new("RGBA", size=DEFAULT_SIZE, color=DEFAULT_NONE_COLOUR)
frontcanvas = ImageDraw.Draw(front)
frontcanvas.text(pos, text, font=SECONDARY_FONT, fill=DEFAULT_WHITE_COLOUR, anchor="mb")

text_layer = Image.alpha_composite(text_layer, front)


text = "#2875A3"
pos = (600, 600)

for i in range(2):
    blur = Image.new("RGBA", size=DEFAULT_SIZE, color=DEFAULT_NONE_COLOUR)
    blurcanvas = ImageDraw.Draw(blur)
    blurcanvas.text(pos, text, font=PRIMARY_FONT, fill=DEFAULT_BLACK_COLOUR, anchor="mt")
    blur = blur.filter(ImageFilter.GaussianBlur(radius=6))
    text_layer = Image.alpha_composite(text_layer, blur)

front = Image.new("RGBA", size=DEFAULT_SIZE, color=DEFAULT_NONE_COLOUR)
frontcanvas = ImageDraw.Draw(front)
frontcanvas.text(pos, text, font=PRIMARY_FONT, fill=DEFAULT_WHITE_COLOUR, anchor="mt")

text_layer = Image.alpha_composite(text_layer, front)









text_layer.save('test_image.png')
