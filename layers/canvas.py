
import numpy as np
from PIL import (
    Image,
    ImageDraw,
)

from layers.base import BaseLayer
from layers.constants import (
    DEFAULT_SIZE,
    DEFAULT_NONE_COLOUR,
)



class CanvasLayer(BaseLayer):

    def __init__(self, rgb: tuple[int, int, int]):
        self.rgb = rgb 

    def _create_layer(self, size: tuple[int, int] = DEFAULT_SIZE):
        base = np.float64(
            np.asarray(
                Image.new(
                    "RGBA",
                    size=size,
                    color=self.rgb + (255,)
                )
            )
        )

        base_layer = Image.fromarray(base.astype(np.uint8))
        base_layer.putalpha(255)
        
        return base_layer