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

import datetime
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, LargeBinary, String
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def _utcnow() -> datetime.datetime:
    '''
    Timezone-aware current time in UTC. All stored datetimes are UTC: on
    Postgres the ``DateTime(timezone=True)`` columns keep this as a proper
    timestamptz instant; on SQLite (which has no tz storage) it is stored as
    the naive UTC wall time. Convert to a local zone only when displaying.
    '''
    return datetime.datetime.now(datetime.timezone.utc)


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
        return ('#%02x%02x%02x' % self.rgb).upper()

    def __repr__(self) -> str:
        return f'ColourRecord(name={self.name!r}, rgb={self.rgb})'


class ThemeRecord(Base):
    '''
    A serialized theme region. ``data`` is the pickled region blob; ``kind``
    names the region class it deserializes to (e.g. 'kde'), so the library can
    dispatch without unpickling. The scalar columns are denormalised copies of
    the region metadata so the library can be listed cheaply.
    '''

    __tablename__ = 'themes'

    id: Mapped[int] = mapped_column(primary_key=True)
    tag: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    desc: Mapped[str] = mapped_column(String, default='')
    source: Mapped[str] = mapped_column(String, default='generic')
    # the region class to deserialize ``data`` into (see core.themes.library)
    kind: Mapped[str] = mapped_column(String, default='kde')
    data: Mapped[bytes] = mapped_column(LargeBinary)

    def __repr__(self) -> str:
        return f'ThemeRecord(tag={self.tag!r}, name={self.name!r}, kind={self.kind!r})'


class ArtifactRecord(Base):
    '''
    A named binary blob that does not belong in a typed table - currently the
    pickled colour-name lookup tree (KDTree + labels) that used to live in
    data/tree.pickle, keyed by core.colours.naming.TREE_KEY.
    '''

    __tablename__ = 'artifacts'

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True, index=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)

    def __repr__(self) -> str:
        return f'ArtifactRecord(key={self.key!r}, bytes={len(self.data)})'


class ThemeVoteType(enum.Enum):
    '''
    The kind of theme vote. Only ``DEFAULT`` exists for now - a post that lists
    a handful of random themes and collects votes as likes on per-theme replies.
    '''

    DEFAULT = 'default'


class ThemeVoteRecord(Base):
    '''
    A poll over a handful of themes run on Bluesky: one main post lists the
    options, a reply is then made per theme, and after ``vote_end_date`` the
    likes on each reply are tallied to pick a winner.

    The scheduling dates drive the lifecycle (when to start posting, when to
    stop, when voting closes). The per-theme options live in the related
    :class:`ThemeOptionRecord` rows. The application-facing shape is the
    ``ThemeVote`` DTO in db/schemas.py.

    The ``_``-prefixed columns are managed bookkeeping: ``_id`` is the primary
    key, and ``_insert_date`` / ``_update_date`` / ``_checked_date`` are set
    automatically (insert time, last write, last like-check). They stay on the
    record only - the ``ThemeVote`` DTO carries the business fields, not these.
    '''

    __tablename__ = 'theme_votes'

    _id: Mapped[int] = mapped_column(primary_key=True)
    _insert_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    _update_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=_utcnow, onupdate=_utcnow,
    )
    # last time the likes were checked; seeded to insert time until first check
    _checked_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    type: Mapped[ThemeVoteType] = mapped_column(
        Enum(ThemeVoteType), default=ThemeVoteType.DEFAULT
    )

    # bluesky id of the main post (at:// uri + cid); null until it is posted
    post_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    post_cid: Mapped[str | None] = mapped_column(String, nullable=True)

    # when voting opens and the post is made
    vote_start_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # when voting closes and likes are tallied
    vote_end_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # window during which the theme applies
    theme_start_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    theme_end_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    options: Mapped[list['ThemeOptionRecord']] = relationship(
        back_populates='vote',
        cascade='all, delete-orphan',
        order_by='ThemeOptionRecord._id',
    )

    @property
    def id(self) -> int:
        return self._id

    def __repr__(self) -> str:
        return (
            f'ThemeVoteRecord(id={self._id}, '
            f'type={self.type.value!r}, options={len(self.options)})'
        )


class ThemeOptionRecord(Base):
    '''
    One theme on the ballot of a :class:`ThemeVoteRecord`. After the main post
    goes out a reply is made for this option; its bluesky id (uri + cid) is
    stored here, and the likes on that reply are the votes.

    Like the vote, the ``_``-prefixed columns are managed bookkeeping (primary
    key, FK to the parent vote, and the insert/update/check timestamps); they
    stay on the record and are not carried on the ``ThemeOption`` DTO.
    '''

    __tablename__ = 'theme_options'

    _id: Mapped[int] = mapped_column(primary_key=True)
    _vote_id: Mapped[int] = mapped_column(ForeignKey('theme_votes._id'), index=True)
    _insert_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    _update_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=_utcnow, onupdate=_utcnow,
    )
    # last time this option's likes were checked; seeded to insert time
    _checked_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # the theme this option offers (the row in the `themes` table)
    theme_id: Mapped[int] = mapped_column(ForeignKey('themes.id'))

    # bluesky id of the per-theme reply (at:// uri + cid); null until posted
    comment_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    comment_cid: Mapped[str | None] = mapped_column(String, nullable=True)

    # likes tallied at the last check; null until first checked
    likes: Mapped[int | None] = mapped_column(nullable=True)

    vote: Mapped['ThemeVoteRecord'] = relationship(back_populates='options')
    theme: Mapped['ThemeRecord'] = relationship()

    @property
    def id(self) -> int:
        return self._id

    # denormalised theme fields, so the DTO can be built straight from this
    # record (mirrors ColourRecord.rgb / .hexcode feeding the Colour DTO)
    @property
    def theme_tag(self) -> str:
        return self.theme.tag

    @property
    def theme_name(self) -> str:
        return self.theme.name

    @property
    def theme_source(self) -> str:
        return self.theme.source

    @property
    def theme_desc(self) -> str:
        return self.theme.desc

    def __repr__(self) -> str:
        return (
            f'ThemeOptionRecord(id={self._id}, '
            f'theme_id={self.theme_id}, likes={self.likes})'
        )
