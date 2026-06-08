from PIL import Image

from layers.canvas import CanvasLayer
from layers.text import (
    NameTextLayer,
    HexcodeTextLayer,
    ThemeTextLayer,
)

from models.colour import Colour
from layers.utils import compile_layers



class _FrameBase:

    def __init__(self, count: int, slide_size: tuple[int, int]):
        self.count = count
        self.slide_size = slide_size
        self.sw, self.sh = slide_size

    def _construct_slides(self, colours: list[Colour]):
        slides = []
        for i, colour in enumerate(colours):
            layers = []
            layers.append(CanvasLayer(rgb=colour.rgb))
            layers.append(HexcodeTextLayer(text=colour.hexcode))
            layers.append(NameTextLayer(text=colour.name.upper()))
            # if i == len(colours) - 1:
            #     layers.append(ThemeTextLayer(text="[THEME TEXT]"))
            slide = compile_layers(self.slide_size, *layers)

            slides.append(slide)

        return slides

    def construct_frame(self, colours: list[Colour]):
        raise NotImplementedError



class SingleFrame(_FrameBase):

    def construct_frame(self, colours: list[Colour]):
        if not isinstance(colours, Colour) and len(colours) != 1:
            raise Exception('SingleFrame cannot have more than one colour')

        if isinstance(colours, Colour):
            colours = [colours]

        slides = self._construct_slides(colours)

        full = Image.new("RGBA", size=self.slide_size, color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (0, 0))

        return full


class HorizontalFrame(_FrameBase):

    def construct_frame(self, colours: list[Colour]):
        if isinstance(colours, Colour) or len(colours) <= 1:
            raise Exception('Vertical frame must have more than one colour')

        slides = self._construct_slides(colours)

        n = len(slides)

        full = Image.new("RGBA", size=(self.sw*n, self.sh), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (self.sw*i, 0))

        return full


class VerticalFrame(_FrameBase):

    def construct_frame(self, colours: list[Colour]):
        if isinstance(colours, Colour) or len(colours) <= 1:
            raise Exception('Vertical frame must have more than one colour')

        slides = self._construct_slides(colours)

        n = len(slides)

        full = Image.new("RGBA", size=(self.sw, self.sh*n), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (0, self.sh*i))

        return full


class TwoByTwoFrame(_FrameBase):

    def construct_frame(self, colours: list[Colour]):
        if isinstance(colours, Colour) or len(colours) != 4:
            raise Exception('TwoByTwoFrame must be 4 colours')

        slides = self._construct_slides(colours)

        n = len(slides)

        full = Image.new("RGBA", size=(self.sw*2, self.sh*2), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (self.sw*(i // 2), self.sh*(i % 2)))

        return full



class FourByFourFrame(_FrameBase):

    def construct_frame(self, colours: list[Colour]):
        if isinstance(colours, Colour) or len(colours) != 16:
            raise Exception('FourByFourFrame must be 16 colours')

        slides = self._construct_slides(colours)

        n = len(slides)

        full = Image.new("RGBA", size=(self.sw*4, self.sh*4), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (self.sw*(i // 4), self.sh*(i % 4)))

        return full