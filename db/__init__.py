'''
SQLite database layer: SQLAlchemy 2.0 ORM records, pydantic DTOs and helpers.

Typical use:

    from db import session_scope, all_colours, all_themes

    with session_scope() as session:
        colours = all_colours(session)      # list[Colour]
        themes = all_themes(session)        # list[KDETheme]
'''

from db.engine import DB_PATH, ENGINE, SessionLocal, init_db, session_scope
from db.models import ArtifactRecord, Base, ColourRecord, ThemeRecord
from db.repository import (
    all_colours,
    all_themes,
    delete_theme,
    get_artifact,
    get_colour,
    get_theme,
    get_theme_blob,
    put_artifact,
    theme_tags,
    upsert_colour,
    upsert_theme,
)
from db.utils.convert import hex_to_rgb, rgb_to_hex
from db.utils.naming import load_tree, rgb_to_name, save_tree
from db.schemas import Colour

__all__ = [
    'DB_PATH',
    'ENGINE',
    'SessionLocal',
    'init_db',
    'session_scope',
    'Base',
    'ColourRecord',
    'ThemeRecord',
    'ArtifactRecord',
    'Colour',
    'all_colours',
    'get_colour',
    'upsert_colour',
    'all_themes',
    'get_theme',
    'get_theme_blob',
    'theme_tags',
    'upsert_theme',
    'delete_theme',
    'get_artifact',
    'put_artifact',
    'rgb_to_hex',
    'hex_to_rgb',
    'rgb_to_name',
    'load_tree',
    'save_tree',
]
