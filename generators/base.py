import colorsys
import math

import colorspacious
import numpy as np

from models.colour import Colour


is_valid_color = lambda r, g, b: 0 <= r < 256 and 0 <= g < 256 and 0 <= b < 256


class Generator:

    def single(self) -> Colour:
        raise NotImplementedError

    def generate(self, n: int) -> Colour | list[Colour]:
        if n == 1:
            return [self.single()]
        return [self.single() for i in range(n)]


class RGBGenerator(Generator):
    def single(self) -> Colour:
        rgb = tuple(np.random.randint(0, 255, 3))
        return Colour.from_rgb(rgb)



class HSVGenerator(Generator):
    def single(self) -> Colour:
        h = np.random.rand()
        s = np.random.rand()
        v = np.random.rand()
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return Colour.from_rgb((int(r*255), int(g*255), int(b*255)))


    
# class PerceptuallyUniformGenerator(Generator):

#     def single(self) -> Colour:
#         r, g, b = -1, -1, -1
#         while not is_valid_color(r, g, b):
#             J, C, H = np.random.random()*100, np.random.random()*80, np.random.random()*360
#             r, g, b = colorspacious.cspace_convert((J, C, H), start="JCh", end="sRGB255")
#         rgb = (math.floor(r), math.floor(g), math.floor(b))
#         return Colour.from_rgb(rgb)