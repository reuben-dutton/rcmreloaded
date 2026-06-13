import collections
import dataclasses
import itertools

import numpy as np
import skimage.color
from PIL import Image


from models.colour import Colour
from pipeline.generators import (
    _GeneratorBase
)
from pipeline.palettes import (
    _PaletteBase
)
from pipeline.frames import (
    _FrameBase
)
from pipeline.themes import (
    _ThemeBase
)
from pipeline.enums import (
    Generator,
    Theme,
    Palette,
    Frame,
    Sample,
)


MAX_THEME_ACCEPTANCE_ITERATIONS = 100000
# bail early if this many consecutive candidates are rejected: the region is
# saturated and the remaining budget would be wasted
MAX_STALL_ITERATIONS = 15000



@dataclasses.dataclass
class SourceOp:
    generator: Generator

    def resolve(self):
        if self.generator == Generator.RANDOM:
            return Generator.choices()
        return [self.generator.value()]

        
@dataclasses.dataclass
class ThemeOp:
    theme: Theme | _ThemeBase

    def resolve(self):
        if isinstance(self.theme, _ThemeBase):
            return [self.theme]
        if self.theme == Theme.RANDOM:
            return Theme.choices()
        return [self.theme.value()]
    
@dataclasses.dataclass
class PaletteOp:
    palette: Palette

    def resolve(self):
        match self.palette:
            case Palette.RANDOM:
                return Palette.choices()
            case Palette.DEFAULT:
                return Palette.defaults()
        return [self.palette.value]

@dataclasses.dataclass
class FrameOp:
    frame: Frame

    def resolve(self):
        match self.frame:
            case Frame.RANDOM:
                return Frame.choices()
            case Frame.DOUBLE:
                return Frame.doubles()
            case Frame.TRIPLE:
                return Frame.triples()
            case Frame.QUAD:
                return Frame.quads()
        return [self.frame.value]


@dataclasses.dataclass
class SampleOp:
    sample: Sample

    def resolve(self):
        if self.sample == Sample.RANDOM:
            return Sample.choices()
        return [self.sample.value]


PipelineOp = SourceOp | ThemeOp | PaletteOp, FrameOp | SampleOp




@dataclasses.dataclass
class Plan:
    generator: _GeneratorBase
    theme: _ThemeBase
    palette: _PaletteBase
    n: int
    frame: _FrameBase

    @property
    def valid(self) -> bool:
        if not self.theme.INVARIANT and not self.palette.INVARIANT:
            # either palette or theme must be the default
            # we can't have both set
            return False
        # colours generated and frame size must match the reshaping
        # done by the palette
        if self.palette.shape != (self.n, self.frame.count):
            return False
        return True


class Pipeline:

    _source: SourceOp | None
    _theme: ThemeOp | None
    _palette: PaletteOp | None
    _sample: SampleOp | None
    _frame: FrameOp | None
    _plan: Plan | None
    _options: dict

    def __init__(self):
        self._source = None
        self._theme = None
        self._palette = None
        self._sample = None
        self._frame = None
        self._plan = None
        self._options = {}

    @property
    def _resolved(self) -> bool:
        return self._plan is not None

    @classmethod
    def source(cls, g: Generator):
        instance = cls()
        instance._source = SourceOp(g)
        return instance
    
    def filter(self, t: Theme | _ThemeBase) -> "Pipeline":
        if self._theme:
            raise Exception('Theme is already defined.')
        self._theme = ThemeOp(t)
        return self
    
    def palette(self, p: Palette) -> "Pipeline":
        if self._palette:
            raise Exception('Palette is already defined.')
        self._palette = PaletteOp(p)
        return self
    
    def sample(self, s: Sample | int) -> "Pipeline":
        if self._sample:
            raise Exception('Sample is already defined.')
        if isinstance(s, int):
            sample = Sample(s)
        else:
            sample = s
        self._sample = SampleOp(sample)
        return self
    
    def layout(self, f: Frame) -> "Pipeline":
        if self._frame:
            raise Exception('Frame is already defined.')
        self._frame = FrameOp(f)
        return self

    # configure generation options applied when generate() is called
    def options(self, *, min_delta_e: int = 0, blank: bool = False) -> "Pipeline":
        self._options = {'min_delta_e': min_delta_e, 'blank': blank}
        return self
    
    # generate a list of possible plans
    def _resolve(self):
        
        # if something isn't set, we choose a random one
        if not self._source:
            self._source = SourceOp(Generator.DEFAULT)
        if not self._theme:
            self._theme = ThemeOp(Theme.DEFAULT)
        if not self._palette:
            self._palette = PaletteOp(Palette.DEFAULT)
        if not self._sample:
            self._sample = SampleOp(Sample.RANDOM)
        if not self._frame:
            self._frame = FrameOp(Frame.RANDOM)

        # now we get all choices for each
        options = [
            Plan(*option) for option in itertools.product(
                self._source.resolve(),
                self._theme.resolve(),
                self._palette.resolve(),
                self._sample.resolve(),
                self._frame.resolve()
            )
        ]

        choices = [plan for plan in options if plan.valid]

        if len(choices) == 0:
            raise Exception('No valid plans exist for this specification.')
        
        return choices
    
    # take the first plan
    def _resolve_first(self):
        choices = self._resolve()
        self._plan = choices[0]
    
    # take a random plan
    def _resolve_random(self) -> Plan:
        choices = self._resolve()

        # relative probability mass for each palette shape
        # (normalised below, so only the ratios matter)
        desired = {
            (1, 1): 0.2,
            (1, 2): 0.15,
            (1, 3): 0.1,
            (1, 4): 0.1,
            (2, 2): 0.125,
            (2, 3): 0.125,
            (2, 4): 0.15,
            (3, 3): 0.125,
            (4, 4): 0.125,
            (1, 9): 0.04,
            (2, 9): 0.03,
            (9, 9): 0.03,
            (1, 16): 0.02,
            (2, 16): 0.03,
            (16, 16): 0.02,
        }

        # count how many choices share each shape so we can dilute
        counts = collections.Counter(choice.palette.shape for choice in choices)

        # each choice gets its shape's target mass split evenly among the
        # choices sharing that shape, so every shape is picked per its desired
        # probability regardless of how many concrete plans produce it
        weights = np.array([
            desired.get(choice.palette.shape, 0) /
            counts[choice.palette.shape] for choice in choices
        ])
        if weights.sum() == 0:
            # every valid plan has a shape with no assigned mass (e.g. an
            # explicitly requested palette): fall back to a uniform pick
            weights = np.ones(len(choices))
        weights = weights / weights.sum()

        plan = np.random.choice(np.array(choices), replace=False, p=weights)
        self._plan = plan
        return plan

    # select a random plan
    def random(self) -> "Pipeline":
        self._resolve_random()
        return self

    # select the first plan
    def first(self) -> "Pipeline":
        self._resolve_first()
        return self

    # generate an image using the current plan
    def generate(self) -> tuple[Image.Image, list[Colour]]:
        plan = self._plan if self._plan is not None else self._resolve_random()

        # minimum CIEDE2000 distance enforced between sampled colours, so
        # multi-sample frames can't come out with near-identical colours
        min_delta_e = self._options.get('min_delta_e', 0)

        n = plan.n
        accepted: list[Colour] = []
        accepted_lab: list[np.ndarray] = []
        i = 0
        stall = 0
        while len(accepted) < n and i < MAX_THEME_ACCEPTANCE_ITERATIONS:
            i += 1
            stall += 1
            if stall > MAX_STALL_ITERATIONS:
                break
            colour = plan.generator.single()
            if not plan.theme.accepted(colour):
                continue
            if min_delta_e > 0:
                lab = skimage.color.rgb2lab(np.array(colour.rgb1).reshape(1, 1, 3)).reshape(3)
                if accepted_lab and skimage.color.deltaE_ciede2000(
                    np.stack(accepted_lab), lab.reshape(1, 3),
                ).min() < min_delta_e:
                    continue
                accepted_lab.append(lab)
            accepted += [colour]
            stall = 0

        if len(accepted) < n:
            raise Exception(
                f'Only sampled {len(accepted)}/{n} colours within {i} '
                f'iterations. The theme region is likely too small to hold '
                f'{n} colours '
                f'{f"at min_delta_e={min_delta_e}" if min_delta_e else ""}'.rstrip()
                + ' - lower min_delta_e, sample fewer colours, or widen the theme.'
            )

        colours = plan.palette.generate(accepted)
        return plan.frame.construct_frame(colours, blank=self._options.get('blank', False)), colours
