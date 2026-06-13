'''
SQLAlchemy 2.0 declarative ORM models.

The database holds:
  - colour names (the ``name -> rgb`` table that used to live in colors.json)
  - serialized theme objects (the pickled KDEThemes that used to be .rcmt files)
  - named binary artifacts (e.g. the colour-name lookup tree, ex tree.pickle)

These are storage records only. The application-facing shapes are the pydantic
DTOs in db/schemas.py, which are built from these via ``from_attributes``.
'''

from __future__ import annotations

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from db.utils.convert import rgb_to_hex


class Base(DeclarativeBase):
    pass


class ColourRecord(Base):
    '''A named point in RGB space (one entry of the old colors.json).'''

    __tablename__ = 'colours'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    r: Mapped[int] = mapped_column()
    g: Mapped[int] = mapped_column()
    b: Mapped[int] = mapped_column()

    @property
    def rgb(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)

    @property
    def hexcode(self) -> str:
        return rgb_to_hex(self.rgb)

    def __repr__(self) -> str:
        return f'ColourRecord(name={self.name!r}, rgb={self.rgb})'


class ThemeRecord(Base):
    '''
    A serialized theme. ``data`` is the pickled KDETheme blob (the same bytes
    that were written to .rcmt files); the scalar columns are denormalised
    copies of the theme metadata so the library can be listed without
    unpickling every entry.
    '''

    __tablename__ = 'themes'

    id: Mapped[int] = mapped_column(primary_key=True)
    tag: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    desc: Mapped[str] = mapped_column(String, default='')
    source: Mapped[str] = mapped_column(String, default='generic')
    data: Mapped[bytes] = mapped_column(LargeBinary)

    def __repr__(self) -> str:
        return f'ThemeRecord(tag={self.tag!r}, name={self.name!r})'


class ArtifactRecord(Base):
    '''
    A named binary blob that does not belong in a typed table - currently the
    pickled colour-name lookup tree (KDTree + labels) that used to live in
    data/tree.pickle, keyed by db.utils.naming.TREE_KEY.
    '''

    __tablename__ = 'artifacts'

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True, index=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)

    def __repr__(self) -> str:
        return f'ArtifactRecord(key={self.key!r}, bytes={len(self.data)})'
