import dataclasses
import pickle
import random
import re
import typing

import numpy as np
import skimage
import sklearn.neighbors

from models.colour import Colour


def to_tag(name: str) -> str:
    '''
    Canonical theme tag: the name lowercased with each run of non-alphanumeric
    characters collapsed to a single hyphen. Used as the .rcmt filename.
    '''
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


'''
Themes restrict the generation of colours to specific areas in color space,
to produce a thematic consistency for a particular frame or group of frames.

They accomplish this by defining a set of valid regions in colour space,
and then generating colours until the valid space is hit (fairly naive).
'''


@dataclasses.dataclass
class _ThemeBase:

    INVARIANT: typing.ClassVar[bool] = False

    name: str
    desc: str
    source: str  # where the theme draws from, e.g. 'Arcane'; 'generic' if none
    tag: str  # lowercase-with-hyphens of the name; used as the filename

    def accepted(self, colour: Colour) -> bool:
        raise NotImplementedError
    

    def serialize(self) -> bytes:
        raise NotImplementedError

    @classmethod
    def deserialize(cls, data: bytes) -> "_ThemeBase":
        raise NotImplementedError
    


'''
We include a trivial 'everything' theme, which acts as the default.

'''

@dataclasses.dataclass
class DefaultTheme(_ThemeBase):

    INVARIANT: typing.ClassVar[bool] = True

    def __init__(self):
        self.name = "default"
        self.desc = "default theme"
        self.source = "generic"
        self.tag = "default"

    def accepted(self, colour: Colour) -> bool:
        return True
    
    def serialize(self) -> bytes:
        raise Exception('Default theme cannot be serialized')

    @classmethod
    def deserialize(cls, data: bytes) -> "DefaultTheme":
        raise Exception('Default theme cannot be deserialized')
    


'''
Theme based on a kernel density estimate

These contain a kernel density model, which is then clipped and normalized.
Probability of acceptance is equal to the normalized log density for that colour.
'''
@dataclasses.dataclass
class KDETheme(_ThemeBase):

    _kd: sklearn.neighbors.KernelDensity
    _log_density_threshold: float  # cutoff for low log densities
    _log_density_maximum: float  # highest log density, used for scaling to 0-1
    _saturation_penalty: float  # penalty to log density for unsaturated colours

    def _scaled_log_density(self, colour: Colour) -> float:
        '''
        Score a colour against the KDE and scale the result to [0, 1],
        applying the same saturation penalty used when the theme was built.
        '''
        rgb1 = np.array(colour.rgb1).reshape(1, 1, 3)
        lab = skimage.color.rgb2lab(rgb1).reshape(1, 3)
        log_density = self._kd.score_samples(lab)

        saturation = skimage.color.rgb2hsv(rgb1).reshape(1, 3)[:, 1]
        log_density -= self._saturation_penalty * (1 - saturation)

        scaled = (
            (log_density - self._log_density_threshold) /
            (self._log_density_maximum - self._log_density_threshold)
        )

        return float(np.clip(scaled, 0.0, 1.0)[0])

    def accepted(self, colour: Colour) -> bool:
        return random.random() < self._scaled_log_density(colour)

    def serialize(self) -> bytes:
        return pickle.dumps(self)

    @classmethod
    def deserialize(cls, data: bytes) -> "KDETheme":
        return pickle.loads(data)



