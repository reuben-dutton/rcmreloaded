import enum

from db import session_scope
from db.repository import all_themes, get_theme
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
    SplitComplementaryPalette,
    TetradicPalette,
    AccentPalette,
    ShadesTintsPalette,
)
from pipeline.frames import (
    SingleFrame,
    HorizontalFrame,
    VerticalFrame,
    TwoByTwoFrame,
    ThreeByThreeFrame,
    FourByFourFrame,
    ThirdsRightFrame,
    ThirdsLeftFrame,
    ThirdsBottomFrame,
    ThirdsTopFrame,
    SplitRightFrame,
    SplitLeftFrame,
    SplitBottomFrame,
    SplitTopFrame,
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
        with session_scope() as session:
            theme = get_theme(session, tag)
        if theme is None:
            raise KeyError(f'No theme: {tag}')
        return theme

    @staticmethod
    def choices():
        with session_scope() as session:
            return all_themes(session)
    
class Palette(enum.Enum):
    RANDOM = _Random
    DEFAULT = _Default
    DEFAULT_ONE = DefaultPalette((1, 1))
    DEFAULT_TWO = DefaultPalette((2, 2))
    DEFAULT_THREE = DefaultPalette((3, 3))
    DEFAULT_FOUR = DefaultPalette((4, 4))
    DEFAULT_NINE = DefaultPalette((9, 9))
    DEFAULT_SIXTEEN = DefaultPalette((16, 16))
    GRADIENT_PLUS_ONE = GradientPalette((2, 3))
    GRADIENT_PLUS_TWO = GradientPalette((2, 4))
    COMPLEMENTARY = ComplementaryPalette((1, 2))
    ANALOGOUS = AnalogousPalette((1, 3))
    TRIADIC = TriadicPalette((1, 3))
    SPLIT_COMPLEMENTARY = SplitComplementaryPalette((1, 3))
    TETRADIC = TetradicPalette((1, 4))
    ACCENT = AccentPalette((1, 4))
    SHADES_TINTS = ShadesTintsPalette((1, 4))
    SHADES_TINTS_NINE = ShadesTintsPalette((1, 9))
    SHADES_TINTS_SIXTEEN = ShadesTintsPalette((1, 16))
    GRADIENT_NINE = GradientPalette((2, 9))
    GRADIENT_SIXTEEN = GradientPalette((2, 16))

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
            Palette.DEFAULT_NINE.value,
            Palette.DEFAULT_SIXTEEN.value,
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
    NINE_GRID = ThreeByThreeFrame(9, (800, 800))
    SIXTEEN_GRID = FourByFourFrame(16, (600, 600))
    THIRDS_RIGHT = ThirdsRightFrame(2, (600, 1800))
    THIRDS_LEFT = ThirdsLeftFrame(2, (600, 1800))
    THIRDS_BOTTOM = ThirdsBottomFrame(2, (1800, 600))
    THIRDS_TOP = ThirdsTopFrame(2, (1800, 600))
    SPLIT_RIGHT = SplitRightFrame(3, (600, 600))
    SPLIT_LEFT = SplitLeftFrame(3, (600, 600))
    SPLIT_BOTTOM = SplitBottomFrame(3, (600, 600))
    SPLIT_TOP = SplitTopFrame(3, (600, 600))

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
        return [
            Frame.DOUBLE_HORIZONTAL.value,
            Frame.DOUBLE_VERTICAL.value,
            Frame.THIRDS_RIGHT.value,
            Frame.THIRDS_LEFT.value,
            Frame.THIRDS_BOTTOM.value,
            Frame.THIRDS_TOP.value,
        ]

    @staticmethod
    def triples():
        return [
            Frame.TRIPLE_HORIZONTAL.value,
            Frame.TRIPLE_VERTICAL.value,
            Frame.SPLIT_RIGHT.value,
            Frame.SPLIT_LEFT.value,
            Frame.SPLIT_BOTTOM.value,
            Frame.SPLIT_TOP.value,
        ]
    
    @staticmethod
    def quads():
        return [Frame.QUAD_HORIZONTAL.value, Frame.QUAD_VERTICAL.value, Frame.QUAD_GRID.value]


class Sample(enum.Enum):
    RANDOM = _Random
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    NINE = 9
    SIXTEEN = 16

    @staticmethod
    def choices():
        return [s.value for s in Sample if s not in (Sample.RANDOM,)]