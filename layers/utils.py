from PIL import (
    Image,
)

from layers.base import BaseLayer
from layers.constants import (
    DEFAULT_SIZE,
    DEFAULT_NONE_COLOUR,
)


def compile_layers(*args: list[BaseLayer]):
    image = Image.new("RGBA", size=DEFAULT_SIZE, color=DEFAULT_NONE_COLOUR)
    for arg in args:
        image = Image.alpha_composite(image, arg._create_layer())
    return image