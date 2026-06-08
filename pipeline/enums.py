import enum

import config
from pipeline.generators import (
    RGBGenerator,
    HSVGenerator,
    CIELChGenerator,
)
from pipeline.themes import (
    DefaultTheme,
    KDETheme,
)
from pipeline.palettes import (
    DefaultPalette,
    GradientPalette,
    ComplementaryPalette,
    AnalogousPalette,
    TriadicPalette,
)
from pipeline.frames import (
    SingleFrame,
    HorizontalFrame,
    VerticalFrame,
    TwoByTwoFrame,
)


class _Random(): ...

class _Default(): ...


class Generator(enum.Enum):
    RANDOM = _Random
    DEFAULT = CIELChGenerator
    CIELCH = CIELChGenerator
    RGB = RGBGenerator
    HSV = HSVGenerator

    @staticmethod
    def choices():
        return [g.value() for g in Generator if g not in (Generator.RANDOM, Generator.DEFAULT,)]        


class Theme(enum.Enum):
    RANDOM = _Random
    DEFAULT = DefaultTheme

    @staticmethod
    def load(tag) -> KDETheme:
        with open(config.THEME_DIRECTORY / f'{tag}.rcmt', 'rb') as f:
            return KDETheme.deserialize(f.read())
        
    @staticmethod
    def choices():
        return [Theme.load(f.stem) for f in config.THEME_DIRECTORY.glob('*.rcmt')]
    
class Palette(enum.Enum):
    RANDOM = _Random
    DEFAULT = _Default
    DEFAULT_ONE = DefaultPalette((1, 1))
    DEFAULT_TWO = DefaultPalette((2, 2))
    DEFAULT_THREE = DefaultPalette((3, 3))
    DEFAULT_FOUR = DefaultPalette((4, 4))
    GRADIENT_PLUS_ONE = GradientPalette((2, 3))
    GRADIENT_PLUS_TWO = GradientPalette((2, 4))
    COMPLEMENTARY = ComplementaryPalette((1, 2))
    ANALOGOUS = AnalogousPalette((1, 3))
    TRIADIC = TriadicPalette((1, 3))

    @staticmethod
    def choices():
        return [p.value for p in Palette if p not in (Palette.RANDOM, Palette.DEFAULT,)]
    
    @staticmethod
    def defaults():
        return [
            Palette.DEFAULT_ONE.value,
            Palette.DEFAULT_TWO.value,
            Palette.DEFAULT_THREE.value,
            Palette.DEFAULT_FOUR.value,
        ]


class _Double: ...
class _Triple: ...
class _Quad: ...


class Frame(enum.Enum):
    RANDOM = _Random
    DEFAULT = SingleFrame(1, (1200, 1200))
    DOUBLE = _Double
    TRIPLE = _Triple
    QUAD = _Quad
    SINGLE = SingleFrame(1, (1200, 1200))
    DOUBLE_HORIZONTAL = HorizontalFrame(2, (600, 1200))
    DOUBLE_VERTICAL = VerticalFrame( 2, (1200, 600))
    TRIPLE_HORIZONTAL = HorizontalFrame(3, (600, 1800))
    TRIPLE_VERTICAL = VerticalFrame(3, (1800, 600))
    QUAD_HORIZONTAL = HorizontalFrame(4, (600, 2400))
    QUAD_VERTICAL = VerticalFrame(4, (2400, 600))
    QUAD_GRID = TwoByTwoFrame(4, (800, 800))

    @staticmethod
    def choices():
        return [f.value for f in Frame if f not in (
            Frame.RANDOM,
            Frame.DEFAULT,
            Frame.DOUBLE,
            Frame.TRIPLE,
            Frame.QUAD,
        )]
    
    @staticmethod
    def doubles():
        return [Frame.DOUBLE_HORIZONTAL.value, Frame.DOUBLE_VERTICAL]
    
    @staticmethod
    def triples():
        return [Frame.TRIPLE_HORIZONTAL.value, Frame.TRIPLE_VERTICAL.value]
    
    @staticmethod
    def quads():
        return [Frame.QUAD_HORIZONTAL.value, Frame.QUAD_VERTICAL.value, Frame.QUAD_GRID.value]


class Sample(enum.Enum):
    RANDOM = _Random
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4

    @staticmethod
    def choices():
        return [s.value for s in Sample if s not in (Sample.RANDOM,)]