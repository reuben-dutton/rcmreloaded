'''
The theme domain: colour-space regions, the ``Theme`` DTO that composes them,
the theme-table repository, and the in-memory theme library.
'''

from core.themes.regions import (
    DefaultThemeRegion,
    KDEThemeRegion,
    _ThemeRegionBase,
    to_tag,
)
from core.themes.schemas import Theme, default_theme
from core.themes.repository import (
    all_theme_records,
    delete_theme,
    get_theme_blob,
    pick_random_theme_tags,
    theme_tags,
    upsert_theme,
)
from core.themes.library import ThemeLibrary, themes

__all__ = [
    'Theme',
    'default_theme',
    '_ThemeRegionBase',
    'KDEThemeRegion',
    'DefaultThemeRegion',
    'to_tag',
    'ThemeLibrary',
    'themes',
    'all_theme_records',
    'get_theme_blob',
    'theme_tags',
    'upsert_theme',
    'delete_theme',
    'pick_random_theme_tags',
]
