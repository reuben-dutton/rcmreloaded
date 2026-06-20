import sys
import pathlib

root = str(pathlib.Path().cwd().parent)
if root not in sys.path:
    sys.path.append(root)

import io
import os

import atproto
import config

from core.interactions import InteractionsService
from core.pipeline.pipeline import Pipeline
from core.pipeline.enums import (
    Palette,
    Theme,
    Frame,
)

# the current winning theme while a vote's theme window is active, else default
theme = InteractionsService().vote.active or Theme.DEFAULT

p = (
        Pipeline()
        .filter(theme)
        .random()
)

buffer = io.BytesIO()
image, colours = p.generate()
image.save(buffer, format="PNG")

client = atproto.Client()
client.login(
    config.ATPROTO_CLIENT_USERNAME,
    config.ATPROTO_CLIENT_PASSWORD
)

alt_text = f"A picture of the following colors: {str([colour.name for colour in colours])}. Their hex codes are {str([colour.hexcode for colour in colours])}."

client.send_image("", image=buffer.getvalue(), image_alt = alt_text)