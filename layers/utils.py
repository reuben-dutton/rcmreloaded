from PIL import (
    Image,
)

from layers.base import BaseLayer
from layers.constants import (
    DEFAULT_SIZE,
    DEFAULT_NONE_COLOUR,
)


def compile_layers(size, *args: list[BaseLayer]):
    if size is None:
        size = DEFAULT_SIZE
    image = Image.new("RGBA", size=size, color=DEFAULT_NONE_COLOUR)
    for arg in args:
        image = Image.alpha_composite(image, arg._create_layer(size=size))
    return image