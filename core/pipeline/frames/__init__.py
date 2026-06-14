from PIL import Image

from core.pipeline.frames.layers.canvas import CanvasLayer
from core.pipeline.frames.layers.text import (
    NameTextLayer,
    HexcodeTextLayer,
    ThemeTextLayer,
)

from core.colours import Colour
from core.pipeline.frames.layers.utils import compile_layers



class _FrameBase:

    def __init__(self, count: int, slide_size: tuple[int, int]):
        self.count = count
        self.slide_size = slide_size
        self.sw, self.sh = slide_size

    def _construct_slides(self, colours: list[Colour], blank=False, sizes=None):
        # sizes optionally overrides the slide size per index, for frames
        # whose panels are not all the same shape
        slides = []
        for i, colour in enumerate(colours):
            size = sizes[i] if sizes else self.slide_size
            layers = []
            layers.append(CanvasLayer(rgb=colour.rgb))
            if not blank:
                layers.append(HexcodeTextLayer(text=colour.hexcode))
                layers.append(NameTextLayer(text=colour.name.upper()))
            # if i == len(colours) - 1:
            #     layers.append(ThemeTextLayer(text="[THEME TEXT]"))
            slide = compile_layers(size, *layers)

            slides.append(slide)

        return slides

    def construct_frame(self, colours: list[Colour], blank=False):
        raise NotImplementedError



class SingleFrame(_FrameBase):

    def construct_frame(self, colours: list[Colour], blank=False):
        if not isinstance(colours, Colour) and len(colours) != 1:
            raise Exception('SingleFrame cannot have more than one colour')

        if isinstance(colours, Colour):
            colours = [colours]

        slides = self._construct_slides(colours, blank=blank)

        full = Image.new("RGBA", size=self.slide_size, color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (0, 0))

        return full


class HorizontalFrame(_FrameBase):

    def construct_frame(self, colours: list[Colour], blank=False):
        if isinstance(colours, Colour) or len(colours) <= 1:
            raise Exception('Vertical frame must have more than one colour')

        slides = self._construct_slides(colours, blank=blank)

        n = len(slides)

        full = Image.new("RGBA", size=(self.sw*n, self.sh), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (self.sw*i, 0))

        return full


class VerticalFrame(_FrameBase):

    def construct_frame(self, colours: list[Colour], blank=False):
        if isinstance(colours, Colour) or len(colours) <= 1:
            raise Exception('Vertical frame must have more than one colour')

        slides = self._construct_slides(colours, blank=blank)

        n = len(slides)

        full = Image.new("RGBA", size=(self.sw, self.sh*n), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (0, self.sh*i))

        return full


class TwoByTwoFrame(_FrameBase):

    def construct_frame(self, colours: list[Colour], blank=False):
        if isinstance(colours, Colour) or len(colours) != 4:
            raise Exception('TwoByTwoFrame must be 4 colours')

        slides = self._construct_slides(colours, blank=blank)

        n = len(slides)

        full = Image.new("RGBA", size=(self.sw*2, self.sh*2), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (self.sw*(i // 2), self.sh*(i % 2)))

        return full



class ThreeByThreeFrame(_FrameBase):

    def construct_frame(self, colours: list[Colour], blank=False):
        if isinstance(colours, Colour) or len(colours) != 9:
            raise Exception('ThreeByThreeFrame must be 9 colours')

        slides = self._construct_slides(colours, blank=blank)

        full = Image.new("RGBA", size=(self.sw*3, self.sh*3), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (self.sw*(i // 3), self.sh*(i % 3)))

        return full


class FourByFourFrame(_FrameBase):

    def construct_frame(self, colours: list[Colour], blank=False):
        if isinstance(colours, Colour) or len(colours) != 16:
            raise Exception('FourByFourFrame must be 16 colours')

        slides = self._construct_slides(colours, blank=blank)

        n = len(slides)

        full = Image.new("RGBA", size=(self.sw*4, self.sh*4), color=(0, 0, 0, 0))
        for i, slide in enumerate(slides):
            full.paste(slide, (self.sw*(i // 4), self.sh*(i % 4)))

        return full


'''
    Rule-of-thirds frames: two panels split at one third. The provided slide
    size is the smaller panel; the larger panel doubles it along the split
    axis. The first colour takes the larger panel; the name says where the
    smaller panel sits.
'''

class _ThirdsFrameBase(_FrameBase):

    # (canvas size, large position, large size, small position) factories per
    # subclass; the small panel always uses the provided slide size
    def _layout(self) -> tuple[tuple, tuple, tuple, tuple]:
        raise NotImplementedError

    def construct_frame(self, colours: list[Colour], blank=False):
        if isinstance(colours, Colour) or len(colours) != 2:
            raise Exception(f'{type(self).__name__} must be 2 colours')

        canvas, large_pos, large_size, small_pos = self._layout()
        slides = self._construct_slides(
            colours, blank=blank, sizes=[large_size, self.slide_size],
        )

        full = Image.new("RGBA", size=canvas, color=(0, 0, 0, 0))
        full.paste(slides[0], large_pos)
        full.paste(slides[1], small_pos)

        return full


class ThirdsRightFrame(_ThirdsFrameBase):

    def _layout(self):
        return (self.sw * 3, self.sh), (0, 0), (self.sw * 2, self.sh), (self.sw * 2, 0)


class ThirdsLeftFrame(_ThirdsFrameBase):

    def _layout(self):
        return (self.sw * 3, self.sh), (self.sw, 0), (self.sw * 2, self.sh), (0, 0)


class ThirdsBottomFrame(_ThirdsFrameBase):

    def _layout(self):
        return (self.sw, self.sh * 3), (0, 0), (self.sw, self.sh * 2), (0, self.sh * 2)


class ThirdsTopFrame(_ThirdsFrameBase):

    def _layout(self):
        return (self.sw, self.sh * 3), (0, self.sh), (self.sw, self.sh * 2), (0, 0)


'''
    Split frames: one full-bleed panel beside a stacked pair. The provided
    slide size is the paired slides; the single panel spans both (double
    along the stacking axis). The first colour takes the single panel; the
    name says where the pair sits.
'''

class _SplitFrameBase(_FrameBase):

    # (single position, pair positions, single size) factories per subclass
    def _layout(self) -> tuple[tuple, list[tuple], tuple]:
        raise NotImplementedError

    def construct_frame(self, colours: list[Colour], blank=False):
        if isinstance(colours, Colour) or len(colours) != 3:
            raise Exception(f'{type(self).__name__} must be 3 colours')

        single_pos, pair_pos, single_size = self._layout()
        slides = self._construct_slides(
            colours, blank=blank,
            sizes=[single_size, self.slide_size, self.slide_size],
        )

        full = Image.new("RGBA", size=(self.sw * 2, self.sh * 2), color=(0, 0, 0, 0))
        full.paste(slides[0], single_pos)
        full.paste(slides[1], pair_pos[0])
        full.paste(slides[2], pair_pos[1])

        return full


class SplitRightFrame(_SplitFrameBase):

    def _layout(self):
        return (0, 0), [(self.sw, 0), (self.sw, self.sh)], (self.sw, self.sh * 2)


class SplitLeftFrame(_SplitFrameBase):

    def _layout(self):
        return (self.sw, 0), [(0, 0), (0, self.sh)], (self.sw, self.sh * 2)


class SplitBottomFrame(_SplitFrameBase):

    def _layout(self):
        return (0, 0), [(0, self.sh), (self.sw, self.sh)], (self.sw * 2, self.sh)


class SplitTopFrame(_SplitFrameBase):

    def _layout(self):
        return (0, self.sh), [(0, 0), (self.sw, 0)], (self.sw * 2, self.sh)