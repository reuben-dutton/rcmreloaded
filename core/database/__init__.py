'''
The database layer: SQLAlchemy engine/session plus the ORM Record models.

This is the base layer of ``core`` - it depends on nothing else in the project
(only ``config``). The domain packages (core.colours, core.themes,
core.interactions) build their repositories and DTOs on top of it.
'''

from core.database.engine import (
    DB_PATH,
    ENGINE,
    SessionLocal,
    init_db,
    session_scope,
)
from core.database.models import (
    ArtifactRecord,
    Base,
    ColourRecord,
    ThemeOptionRecord,
    ThemeRecord,
    ThemeVoteRecord,
    ThemeVoteType,
)
from core.database.artifacts import get_artifact, put_artifact

__all__ = [
    'DB_PATH',
    'ENGINE',
    'SessionLocal',
    'init_db',
    'session_scope',
    'Base',
    'ArtifactRecord',
    'ColourRecord',
    'ThemeRecord',
    'ThemeVoteRecord',
    'ThemeOptionRecord',
    'ThemeVoteType',
    'get_artifact',
    'put_artifact',
]
