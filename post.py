import sys
import pathlib

root = str(pathlib.Path().cwd().parent)
if root not in sys.path:
    sys.path.append(root)

import io
import math
import os
import random

import atproto
import dotenv
import numpy as np

from generators import RGBGenerator, HSVGenerator, CIELChGenerator
from generators.palettes import (
    GradientPalette,
    SinglePalette,
    RandomPalette,
    ComplementaryPalette,
    AnalogousPalette,
    TriadicPalette
)
from layers.frames import SingleFrame, HorizontalFrame, VerticalFrame, TwoByTwoFrame

dotenv.load_dotenv()

USERNAME = os.getenv('ATPROTO_CLIENT_USERNAME')
PASSWORD = os.getenv('ATPROTO_CLIENT_PASSWORD')


generator = CIELChGenerator()
options = {
    1: {  # 1200 x 1200
        'frames': [SingleFrame((1200, 1200))],
        'palettes': [RandomPalette]
    },
    2: {  # 1200 x 1200
        'frames': [HorizontalFrame((600, 1200)), VerticalFrame((1200, 600))],
        'palettes': [RandomPalette, ComplementaryPalette]
    },
    3: {  # 1800 x 1800
        'frames': [HorizontalFrame((600, 1800)), VerticalFrame((1800, 600))],
        'palettes': [RandomPalette, GradientPalette, AnalogousPalette, TriadicPalette]
    },
    4: {  # 2400 x 2400, except the two-by-two, which is 1600 x 1600
        'frames': [HorizontalFrame((600, 2400)), VerticalFrame((2400, 600)), TwoByTwoFrame((800, 800))],
        'palettes': [RandomPalette, GradientPalette]
    },
}


n = np.random.choice(
    [1, 2, 3, 4],
    p=[0.25, 0.25, 0.30, 0.2]  # slightly more 3-colours, less 4-colours
)
frame = random.choice(options[n]['frames'])
palette = random.choice(options[n]['palettes'])
colours = palette(generator).generate(n)
image = frame.construct_frame(colours)

buffer = io.BytesIO()
image.save(buffer, format="PNG")

client = atproto.Client()
client.login(USERNAME, PASSWORD)

alt_text = f"A picture of the following colors: {str([colour.name for colour in colours])}. Their hex codes are {str([colour.hexcode for colour in colours])}."

client.send_image("", image=buffer.getvalue(), image_alt = alt_text)