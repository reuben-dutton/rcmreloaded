from PIL import Image

from layers.canvas import CanvasLayer
from layers.text import (
    NameTextLayer,
    HexcodeTextLayer,
)

from models.colour import Colour
from generators import Generator
from generators.palettes import Palette
from layers.utils import compile_layers



class Frame:

    def __init__(self, slide_size: tuple[int, int]):
        self.slide_size = slide_size
        self.sw, self.sh = slide_size

    def _construct_slides(self, colours: list[Colour]):
        slides = []
        for i, colour in enumerate(colours):
            name_layer = NameTextLayer(text=colour.name.upper())
            hexcode_layer = HexcodeTextLayer(text=colour.hexcode)
            canvas_layer = CanvasLayer(rgb=colour.rgb)
            slide = compile_layers(self.slide_size, canvas_layer, name_layer, hexcode_layer)

            slides.append(slide)

        return slides

    def construct_frame(self, colours: Colour | list[Colour]):
        raise NotImplementedError



class SingleFrame(Frame):

    def construct_frame(self, colours: Colour | list[Colour]):
        if not isinstance(colours, Colour) and len(colours) != 1:
            raise Exception('SingleFrame cannot have more than one colour')

        if isinstance(colours, Colour):
            colours = [colours]

        slides = self._construct_slides(colours)

        full = Image.new("RGBA", size=self.slide_size, color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (0, 0))

        return full


class HorizontalFrame(Frame):

    def construct_frame(self, colours: list[Colour]):
        if isinstance(colours, Colour) or len(colours) <= 1:
            raise Exception('Vertical frame must have more than one colour')

        slides = self._construct_slides(colours)

        n = len(slides)

        full = Image.new("RGBA", size=(self.sw*n, self.sh), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (self.sw*i, 0))

        return full


class VerticalFrame(Frame):

    def construct_frame(self, colours: list[Colour]):
        if isinstance(colours, Colour) or len(colours) <= 1:
            raise Exception('Vertical frame must have more than one colour')

        slides = self._construct_slides(colours)

        n = len(slides)

        full = Image.new("RGBA", size=(self.sw, self.sh*n), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (0, self.sh*i))

        return full


class TwoByTwoFrame(Frame):

    def construct_frame(self, colours: list[Colour]):
        if isinstance(colours, Colour) or len(colours) != 4:
            raise Exception('TwoByTwoFrame must be 4 colours')

        slides = self._construct_slides(colours)

        n = len(slides)

        full = Image.new("RGBA", size=(self.sw*2, self.sh*2), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (self.sw*(i // 2), self.sh*(i % 2)))

        return full



class FourByFourFrame(Frame):

    def construct_frame(self, colours: list[Colour]):
        if isinstance(colours, Colour) or len(colours) != 16:
            raise Exception('FourByFourFrame must be 16 colours')

        slides = self._construct_slides(colours)

        n = len(slides)

        full = Image.new("RGBA", size=(self.sw*4, self.sh*4), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (self.sw*(i // 4), self.sh*(i % 4)))

        return full




    
        


