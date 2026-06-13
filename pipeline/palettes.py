from ctypes import ArgumentError

import coloraide

from db.schemas import Colour






'''
    Takes a generator and uses it to create a set of colours, prespecified

    Each palette class has a .shape, which determines how the input colours can be
    reshaped downstream. Note that these are representative of how the number of
    colours change -> (1, 1) means that one input becomes one output.
'''
class _PaletteBase:

    INVARIANT = False

    def __init__(self, shape: tuple[int, int]):
        self.shape = shape

    def _validate_input(self, input: list[Colour]):
        if len(input) != self.shape[0]:
            raise ArgumentError(f"Input provided does not conform to palette shape {self.shape}")
        
    def _validate_output(self, output: list[Colour]):
        if len(output) != self.shape[1]:
            raise ArgumentError(f"Output generated does not conform to palette shape {self.shape}")
        
    def _reshape(self, input: list[Colour]) -> list[Colour]:
        raise NotImplementedError

    def generate(self, input: list[Colour]) -> list[Colour]:
        self._validate_input(input)
        output = self._reshape(input)
        self._validate_output(output)
        return output


'''
    Used for generating single colours
'''
class DefaultPalette(_PaletteBase):

    INVARIANT = True
    
    def _reshape(self, input: list[Colour]) -> list[Colour]:
        return input


'''
    Generates two colours and then interpolates between them.
    We use the JCh colour space for linear interpolation, as we will get a
    more perceptually uniform gradient.
'''
class GradientPalette(_PaletteBase):
    
    def _reshape(self, input: list[Colour]) -> list[Colour]:
        start, end = input
        n = self.shape[1]

        colours = [
            coloraide.Color(start.hexcode),
            coloraide.Color(end.hexcode)
        ]

        i = coloraide.Color.interpolate(colours, space='oklab', method='linear')
        output = [
            Colour.from_hex(i(x / (n-1)).convert('srgb').to_string(hex=True))
            for x in range(n)
        ]
        return output


def _rotated(base: "coloraide.Color", degrees: float) -> Colour:
    '''The base oklch colour with its hue rotated, as a Colour.'''
    rotated = base.clone().set('h', base['h'] + degrees).convert('srgb')
    return Colour.from_hex(rotated.to_string(hex=True))


class ComplementaryPalette(_PaletteBase):

    def __init__(self, shape: tuple[int, int]):
        if shape != (1, 2):
            raise ArgumentError('Shape must be (1, 2) for ComplementaryPalette')
        super().__init__(shape)

    def _reshape(self, input: list[Colour]) -> list[Colour]:
        start = input[0]
        base = coloraide.Color(start.hexcode).convert('oklch')
        return [start, _rotated(base, 180)]


class AnalogousPalette(_PaletteBase):

    def __init__(self, shape: tuple[int, int]):
        if shape != (1, 3):
            raise ArgumentError('Shape must be (1, 3) for AnalogousPalette')
        super().__init__(shape)

    def _reshape(self, input: list[Colour]) -> list[Colour]:
        start = input[0]
        base = coloraide.Color(start.hexcode).convert('oklch')
        return [_rotated(base, -30), start, _rotated(base, 30)]


class TriadicPalette(_PaletteBase):

    def __init__(self, shape: tuple[int, int]):
        if shape != (1, 3):
            raise ArgumentError('Shape must be (1, 3) for TriadicPalette')
        super().__init__(shape)

    def _reshape(self, input: list[Colour]) -> list[Colour]:
        start = input[0]
        base = coloraide.Color(start.hexcode).convert('oklch')
        return [start, _rotated(base, 120), _rotated(base, 240)]


'''
    Base colour plus the two colours either side of its complement:
    softer contrast than a straight complementary pair.
'''
class SplitComplementaryPalette(_PaletteBase):

    def __init__(self, shape: tuple[int, int]):
        if shape != (1, 3):
            raise ArgumentError('Shape must be (1, 3) for SplitComplementaryPalette')
        super().__init__(shape)

    def _reshape(self, input: list[Colour]) -> list[Colour]:
        start = input[0]
        base = coloraide.Color(start.hexcode).convert('oklch')
        return [start, _rotated(base, 150), _rotated(base, -150)]


'''
    Four hues evenly spaced around the wheel (a square tetrad).
'''
class TetradicPalette(_PaletteBase):

    def __init__(self, shape: tuple[int, int]):
        if shape != (1, 4):
            raise ArgumentError('Shape must be (1, 4) for TetradicPalette')
        super().__init__(shape)

    def _reshape(self, input: list[Colour]) -> list[Colour]:
        start = input[0]
        base = coloraide.Color(start.hexcode).convert('oklch')
        return [start, _rotated(base, 90), _rotated(base, 180), _rotated(base, 270)]


'''
    Three muted, slightly hue-shifted variants of the base, then the base
    itself at boosted chroma as the accent.
'''
class AccentPalette(_PaletteBase):

    MUTED_CHROMA_FACTOR = 0.3
    ACCENT_CHROMA = 0.25  # oklch chroma floor for the accent

    def __init__(self, shape: tuple[int, int]):
        if shape != (1, 4):
            raise ArgumentError('Shape must be (1, 4) for AccentPalette')
        super().__init__(shape)

    def _reshape(self, input: list[Colour]) -> list[Colour]:
        start = input[0]
        base = coloraide.Color(start.hexcode).convert('oklch')

        output = []
        for hue_shift, light_shift in ((-25, 0.12), (0, 0), (25, -0.12)):
            muted = base.clone()
            muted.set('h', base['h'] + hue_shift)
            muted.set('c', base['c'] * self.MUTED_CHROMA_FACTOR)
            muted.set('l', min(max(base['l'] + light_shift, 0.15), 0.92))
            output.append(Colour.from_hex(muted.convert('srgb').to_string(hex=True)))

        accent = base.clone().set('c', max(base['c'], self.ACCENT_CHROMA))
        output.append(Colour.from_hex(accent.convert('srgb').to_string(hex=True)))
        return output


'''
    A ramp through the base colour's shades (mixed toward black) and tints
    (mixed toward white), darkest to lightest. Mixing happens in oklab so the
    steps are perceptually even; the ends stop short of pure black/white.
'''
class ShadesTintsPalette(_PaletteBase):

    MAX_MIX = 0.8  # how far the ramp ends reach toward black/white

    def _reshape(self, input: list[Colour]) -> list[Colour]:
        start = input[0]
        base = coloraide.Color(start.hexcode)
        n = self.shape[1]

        output = []
        for i in range(n):
            position = (i / (n - 1)) * 2 - 1  # -1 (shade) .. +1 (tint)
            if position < 0:
                mixed = base.mix('black', -position * self.MAX_MIX, space='oklab')
            elif position > 0:
                mixed = base.mix('white', position * self.MAX_MIX, space='oklab')
            else:
                mixed = base.clone()
            output.append(Colour.from_hex(mixed.convert('srgb').to_string(hex=True)))
        return output

