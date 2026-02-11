import coloraide

from models.colour import Colour
from generators.base import Generator






'''
    Takes a generator and uses it to create a set of colours, prespecified
'''
class Palette:

    def __init__(self, generator: Generator):
        self._generator = generator


    def generate(self, n: int) -> Colour | list[Colour]:
        raise NotImplementedError


'''
    Used for generating single colours
'''
class SinglePalette(Palette):
    
    def generate(self, n: int):
        return self._generator.generate(1)



'''
    Generates a random palette, i.e. colours have no association with each other
'''
class RandomPalette(Palette):
    
    def generate(self, n: int) -> Colour | list[Colour]:
        return self._generator.generate(n)



'''
    Generates two colours and then interpolates between them.
    We use the JCh colour space for linear interpolation, as we will get a
    more perceptually uniform gradient.
'''
class GradientPalette(Palette):
    
    def generate(self, n: int) -> Colour | list[Colour]:
        if n < 2:
            raise Exception('Need at least two colours for a GradientPalette')
        start, end = self._generator.generate(2)

        colours = [
            coloraide.Color(start.hexcode),
            coloraide.Color(end.hexcode)
        ]

        i = coloraide.Color.interpolate(colours, space='oklab', method='linear')
        results = [
            Colour.from_hex(i(x / (n-1)).convert('srgb').to_string(hex=True))
            for x in range(n)
        ]
        return results


class ComplementaryPalette(Palette):

    def generate(self, n: int) -> list[Colour]:
        start = self._generator.generate(1)[0]

        start_c = coloraide.Color(start.hexcode).convert("oklch")
        end_c = start_c.set('h', start_c['h'] + 180).convert('srgb')

        end = Colour.from_hex(end_c.to_string(hex=True))

        return [start, end]


class AnalogousPalette(Palette):

    def generate(self, n: int) -> list[Colour]:
        start = self._generator.generate(1)[0]

        start_c = coloraide.Color(start.hexcode).convert("oklch")
        one_c = start_c.set('h', start_c['h'] + 30).convert('srgb')
        two_c = start_c.set('h', start_c['h'] + 30).convert('srgb')

        one = Colour.from_hex(one_c.to_string(hex=True))
        two = Colour.from_hex(two_c.to_string(hex=True))

        return [start, one, two]


class TriadicPalette(Palette):

    def generate(self, n: int) -> list[Colour]:
        start = self._generator.generate(1)[0]

        start_c = coloraide.Color(start.hexcode).convert("oklch")
        one_c = start_c.set('h', start_c['h'] + 120).convert('srgb')
        two_c = start_c.set('h', start_c['h'] + 120).convert('srgb')

        one = Colour.from_hex(one_c.to_string(hex=True))
        two = Colour.from_hex(two_c.to_string(hex=True))

        return [start, one, two]

