import colorsys
import functools

import colorspacious
import scipy
import numpy as np

from core.colours import colours
from core.colours import Colour


is_valid_color = lambda r, g, b: 0 <= r < 256 and 0 <= g < 256 and 0 <= b < 256


class _GeneratorBase:

    def single(self) -> Colour:
        raise NotImplementedError

    def generate(self, n: int) -> list[Colour]:
        if n == 1:
            return [self.single()]
        return [self.single() for i in range(n)]


class RGBGenerator(_GeneratorBase):
    def single(self) -> Colour:
        rgb = tuple(np.random.randint(0, 256, 3))
        return colours.make(rgb)



class HSVGenerator(_GeneratorBase):
    def single(self) -> Colour:
        h = np.random.rand()
        s = np.random.rand()
        v = np.random.rand()
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return colours.make((int(r*255), int(g*255), int(b*255)))



## CIELCH constants

MIN_L_VALUE_CIELCH = 0
MAX_L_VALUE_CIELCH = 100
MIN_C_VALUE_CIELCH = 0
MIN_H_VALUE_CIELCH = 0
MAX_H_VALUE_CIELCH = 360
MIN_VALUE_RGB = 0
MAX_VALUE_RGB = 255

OUT_OF_GAMUT_C_VALUE_CIELCH = 250

L_SAMPLE_ALPHA = 1.4
L_SAMPLE_BETA = 1.4



'''
    Based on the provided lightness value, retrieve the maximum chroma
    value that still maps to a valid point in the RGB gamut

    We use a dynamically generated function that returns -1 or 1 to represent
    whether a sampled LCh value is in the RGB gamut, and then use scipy.optimize.bisect
    to identify at what value of C the value changes.
'''
@functools.cache
def get_max_chroma(L: float, h: float) -> float:
    def lch_is_in_rgb_gamut(C):
        rgb = colorspacious.cspace_convert(
            [L, C, h],
            "CIELCh",
            "sRGB1"  # sRGB1 is RGB 0->1
        )
        in_gamut = np.all(rgb >= 0) and np.all(rgb <= 1)
        return [1, -1][int(in_gamut)]
    
    # we take a value that's always in gamut, and one that's always out
    # then use those two to identify where the gamut boundary is for C values
    # (bisect will find when the 0 flips to 1)
    max_C_at_h = scipy.optimize.bisect(
        lch_is_in_rgb_gamut,
        MIN_C_VALUE_CIELCH,
        OUT_OF_GAMUT_C_VALUE_CIELCH,
        xtol=0.05
    )

    return max(MIN_C_VALUE_CIELCH, max_C_at_h)




class CIELChGenerator(_GeneratorBase):
    def single(self) -> Colour:
        scale = (MAX_L_VALUE_CIELCH - MIN_L_VALUE_CIELCH)
        loc = MIN_L_VALUE_CIELCH
        L = np.random.beta(L_SAMPLE_ALPHA, L_SAMPLE_BETA) * scale + loc
        h = np.random.uniform(0, MAX_H_VALUE_CIELCH)

        # bias toward higher chroma values
        C = np.sqrt(np.random.uniform(0, get_max_chroma(L, h)**2))
        
        rgb = colorspacious.cspace_convert([L, C, h], "CIELCh", "sRGB255")
        # clip and convert to int
        rgb = np.clip(rgb, MIN_VALUE_RGB, MAX_VALUE_RGB).astype(int)
        
        return colours.make(tuple(rgb))