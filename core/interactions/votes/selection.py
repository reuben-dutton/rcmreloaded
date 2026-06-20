'''
Theme-selection strategies: choose which themes make up a vote's ballot.

A strategy is any object with a ``select() -> list[str]`` method that returns
the theme tags to put on the ballot, so different ways of choosing themes
(curated sets, by source, weighted, ...) can be swapped in freely. Themes come
from the in-memory ``core.themes.themes`` library, so selection needs no database
session. ``AllThemesSelection`` is the current default - a random handful drawn
from every theme in the library.
'''

from __future__ import annotations

import random

from core.themes import themes
from core.themes.library import ThemeLibrary


class _ThemeSelection:
    '''Returns the theme tags for a vote's ballot. Subclass and override.'''

    def select(self) -> list[str]:
        raise NotImplementedError


class AllThemesSelection(_ThemeSelection):
    '''
    The current default: pick a random handful of themes from the whole
    library. ``count`` is either a fixed number or an inclusive ``(min, max)``
    range to draw from (defaults to 3-3, the size of the post's ballot). If the
    library holds fewer themes than asked for, every theme is used.
    '''

    def __init__(self, library: ThemeLibrary = themes, count: int | tuple[int, int] = (3, 3)):
        self.count = count
        self.tlibrary = library

    def select(self) -> list[str]:
        available = self.tlibrary.tags()
        n = self.count if isinstance(self.count, int) else random.randint(*self.count)
        n = min(n, len(available))
        return random.sample(available, n)
