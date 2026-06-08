from ctypes import ArgumentError

import coloraide

from models.colour import Colour






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


class ComplementaryPalette(_PaletteBase):

    def __init__(self, shape: tuple[int, int]):
        if shape != (1, 2):
            raise ArgumentError('Shape must be (1, 2) for ComplementaryPalette')
        super().__init__(shape)

    def _reshape(self, input: list[Colour]) -> list[Colour]:
        start = input[0]

        start_c = coloraide.Color(start.hexcode).convert("oklch")
        end_c = start_c.set('h', start_c['h'] + 180).convert('srgb')

        end = Colour.from_hex(end_c.to_string(hex=True))

        return [start, end]


class AnalogousPalette(_PaletteBase):

    def __init__(self, shape: tuple[int, int]):
        if shape != (1, 3):
            raise ArgumentError('Shape must be (1, 3) for AnalogousPalette')
        super().__init__(shape)

    def _reshape(self, input: list[Colour]) -> list[Colour]:
        start = input[0]

        start_c = coloraide.Color(start.hexcode).convert("oklch")
        one_c = start_c.set('h', start_c['h'] + 30).convert('srgb')
        two_c = start_c.set('h', start_c['h'] + 30).convert('srgb')

        one = Colour.from_hex(one_c.to_string(hex=True))
        two = Colour.from_hex(two_c.to_string(hex=True))

        return [start, one, two]


class TriadicPalette(_PaletteBase):

    def __init__(self, shape: tuple[int, int]):
        if shape != (1, 3):
            raise ArgumentError('Shape must be (1, 3) for TriadicPalette')
        super().__init__(shape)

    def _reshape(self, input: list[Colour]) -> list[Colour]:
        start = input[0]

        start_c = coloraide.Color(start.hexcode).convert("oklch")
        one_c = start_c.set('h', start_c['h'] + 120).convert('srgb')
        two_c = start_c.set('h', start_c['h'] + 120).convert('srgb')

        one = Colour.from_hex(one_c.to_string(hex=True))
        two = Colour.from_hex(two_c.to_string(hex=True))

        return [start, one, two]

