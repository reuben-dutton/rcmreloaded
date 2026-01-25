import sys
import pathlib

root = str(pathlib.Path().cwd().parent)
if root not in sys.path:
    sys.path.append(root)

import io
import os

import atproto
import dotenv
import numpy as np

from layers.constants import (
    DEFAULT_SIZE,
    DEFAULT_NONE_COLOUR,
)
from layers.canvas import CanvasLayer
from layers.text import (
    NameTextLayer,
    HexcodeTextLayer,
)
from layers.utils import compile_layers
from models.colour import Colour

dotenv.load_dotenv()


USERNAME = os.getenv('ATPROTO_CLIENT_USERNAME')
PASSWORD = os.getenv('ATPROTO_CLIENT_PASSWORD')

rgb = tuple(np.random.randint(0, 256, size=3))
colour = Colour.from_rgb(rgb[:3])

name_layer = NameTextLayer(text=colour.name.upper())
hexcode_layer = HexcodeTextLayer(text=colour.hexcode)
canvas_layer = CanvasLayer(rgb=colour.rgb)


image = compile_layers(canvas_layer, name_layer, hexcode_layer)
buffer = io.BytesIO()
image.save(buffer, format="PNG")

client = atproto.Client()
client.login(USERNAME, PASSWORD)

client.send_image("", image=buffer.getvalue(), image_alt = f"A picture of the color '{colour.name}'. In the centre of the image is the name and hex code of the color ({colour.hexcode})")