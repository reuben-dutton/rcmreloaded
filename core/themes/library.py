'''
The theme library: the in-memory, process-wide view of the stored themes.

Each stored row is one colour-space *region*; the library deserialises each
(dispatching on its ``kind`` column to the right region class) and wraps it in
a single-region ``Theme``. Callers combine those with ``|`` to build
multi-region themes. The cache is loaded lazily and can be refreshed after the
library changes underneath it.
'''

from __future__ import annotations

from core.database.engine import session_scope
from core.themes.regions import KDEThemeRegion, _ThemeRegionBase
from core.themes.repository import all_theme_records
from core.themes.schemas import Theme, default_theme

# region kind -> class, used to deserialise a stored blob
_REGION_KINDS: dict[str, type[_ThemeRegionBase]] = {
    'kde': KDEThemeRegion,
}


def _region(kind: str, data: bytes) -> _ThemeRegionBase:
    try:
        region_cls = _REGION_KINDS[kind]
    except KeyError:
        raise ValueError(f'Unknown theme region kind: {kind!r}')
    return region_cls.deserialize(data)


class ThemeLibrary:

    def __init__(self):
        self._by_tag: dict[str, Theme] | None = None

    def _load(self) -> None:
        with session_scope() as session:
            rows = all_theme_records(session)
        # one stored region per Theme; callers combine with | for mixes
        self._by_tag = {tag: Theme([_region(kind, data)]) for tag, kind, data in rows}

    def _ensure(self) -> dict[str, Theme]:
        if self._by_tag is None:
            self._load()
        assert self._by_tag is not None
        return self._by_tag

    def refresh(self) -> None:
        '''Reload the cache from the database (call after the library changes).'''
        self._load()

    def all(self) -> list[Theme]:
        return list(self._ensure().values())

    def tags(self) -> list[str]:
        return list(self._ensure().keys())

    def get(self, tag: str) -> Theme | None:
        return self._ensure().get(tag)

    def default(self) -> Theme:
        '''The unconstrained 'everything' theme.'''
        return default_theme()


# process-wide theme library
themes = ThemeLibrary()
