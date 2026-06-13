from __future__ import annotations

import dataclasses
import pickle
import random
import re
import typing

import numpy as np
import skimage
import sklearn.neighbors

if typing.TYPE_CHECKING:
    # Colour is only referenced in annotations here; a runtime import would make
    # pipeline depend on db (db.repository imports KDETheme from this module).
    from db.schemas import Colour


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

    def __or__(self, other: "_ThemeBase") -> "CombinedTheme":
        if not isinstance(other, _ThemeBase):
            return NotImplemented
        return CombinedTheme([self, other])
    


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
    _shade_penalty: float = 0.0  # penalty for darker colours (HWB blackness)
    _tint_penalty: float = 0.0  # penalty for lighter colours (HWB whiteness)

    def _scaled_log_density(self, colour: Colour) -> float:
        '''
        Score a colour against the KDE and scale the result to [0, 1],
        applying the same saturation/shade/tint penalties used when the
        theme was built.
        '''
        rgb1 = np.array(colour.rgb1).reshape(1, 1, 3)
        lab = skimage.color.rgb2lab(rgb1).reshape(1, 3)
        log_density = self._kd.score_samples(lab)

        # HSV saturation, HWB blackness (1 - max) and whiteness (min)
        hsv = skimage.color.rgb2hsv(rgb1).reshape(1, 3)
        log_density -= self._saturation_penalty * (1 - hsv[:, 1])
        log_density -= self._shade_penalty * (1 - hsv[:, 2])
        log_density -= self._tint_penalty * rgb1.min()

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
        theme = pickle.loads(data)
        # themes pickled before these penalties existed load without the
        # attributes (pickle bypasses __init__, so field defaults never run)
        for attr in ('_shade_penalty', '_tint_penalty'):
            if not hasattr(theme, attr):
                setattr(theme, attr, 0.0)
        return theme



'''
A mix of two or more themes, built with the | operator:

    Theme.load('sunset') | Theme.load('vaporwave')

Each accepted colour is drawn from one member chosen uniformly at random:
a member is picked, candidates are tested against it alone until one is
accepted, then a fresh member is picked. Every accepted colour therefore
has equal probability of coming from each theme (the split within a single
generation is multinomial, not forced to be exactly even), rather than
being dominated by whichever theme has the larger acceptance region.
'''

@dataclasses.dataclass
class CombinedTheme(_ThemeBase):

    _themes: list

    def __init__(self, themes: list[_ThemeBase]):
        # flatten nested combinations so a | b | c stays one level deep
        flat: list[_ThemeBase] = []
        for theme in themes:
            if isinstance(theme, CombinedTheme):
                flat.extend(theme._themes)
            else:
                flat.append(theme)
        self._themes = flat
        self._active = random.randrange(len(flat))

        self.name = ' + '.join(theme.name for theme in flat)
        self.desc = ' | '.join(theme.desc for theme in flat if theme.desc)
        # deduplicate sources, preserving order
        sources = dict.fromkeys(
            theme.source for theme in flat if theme.source != 'generic'
        )
        self.source = ', '.join(sources) or 'generic'
        self.tag = to_tag(self.name)

    def accepted(self, colour: Colour) -> bool:
        if self._themes[self._active].accepted(colour):
            self._active = random.randrange(len(self._themes))
            return True
        return False

    def serialize(self) -> bytes:
        return pickle.dumps(self)

    @classmethod
    def deserialize(cls, data: bytes) -> "CombinedTheme":
        return pickle.loads(data)



