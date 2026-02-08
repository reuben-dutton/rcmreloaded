import functools

import colorspacious
import scipy
import numpy as np

from generators.base import Generator
from models.colour import Colour


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

    max_C_at_h = scipy.optimize.bisect(
        lch_is_in_rgb_gamut,
        MIN_C_VALUE_CIELCH,
        OUT_OF_GAMUT_C_VALUE_CIELCH,
        xtol=0.05
    )

    return max(MIN_C_VALUE_CIELCH, max_C_at_h)




class CIELChGenerator(Generator):
    def single(self) -> Colour:
        scale = (MAX_L_VALUE_CIELCH - MIN_L_VALUE_CIELCH)
        loc = MIN_L_VALUE_CIELCH
        L = np.random.beta(L_SAMPLE_ALPHA, L_SAMPLE_BETA) * scale + loc
        h = np.random.uniform(0, MAX_H_VALUE_CIELCH)

        # bias against lower chroma values
        C = np.sqrt(np.random.uniform(0, get_max_chroma(L, h)**2))
        
        
        rgb = colorspacious.cspace_convert([L, C, h], "CIELCh", "sRGB255")
        # clip and convert to int
        rgb = np.clip(rgb, MIN_VALUE_RGB, MAX_VALUE_RGB).astype(int)
        
        return Colour.from_rgb(tuple(rgb))