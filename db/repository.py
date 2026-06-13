'''
Read/write helpers that bridge ORM records and their application shapes.

Colours come back as the ``Colour`` DTO; themes come back as live
``pipeline.themes.KDETheme`` objects (deserialized from the stored blob), never
as raw ORM records. Importing KDETheme at the top level is safe because
pipeline.themes carries no runtime dependency on db (it references Colour only
in annotations), so the db -> pipeline edge is one-directional.
'''

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import ArtifactRecord, ColourRecord, ThemeRecord
from db.schemas import Colour
from pipeline.themes import KDETheme


# --------------------------------------------------------------------------- #
# colours

def all_colours(session: Session) -> list[Colour]:
    records = session.scalars(select(ColourRecord).order_by(ColourRecord.name))
    return [Colour.model_validate(r) for r in records]


def get_colour(session: Session, name: str) -> Colour | None:
    record = session.scalar(select(ColourRecord).where(ColourRecord.name == name))
    return Colour.model_validate(record) if record is not None else None


def upsert_colour(session: Session, name: str, rgb: tuple[int, int, int]) -> None:
    record = session.scalar(select(ColourRecord).where(ColourRecord.name == name))
    if record is None:
        session.add(ColourRecord(name=name, r=rgb[0], g=rgb[1], b=rgb[2]))
    else:
        record.r, record.g, record.b = rgb


# --------------------------------------------------------------------------- #
# themes

def all_themes(session: Session) -> list[KDETheme]:
    records = session.scalars(select(ThemeRecord).order_by(ThemeRecord.tag))
    return [KDETheme.deserialize(r.data) for r in records]


def get_theme(session: Session, tag: str) -> KDETheme | None:
    record = session.scalar(select(ThemeRecord).where(ThemeRecord.tag == tag))
    return KDETheme.deserialize(record.data) if record is not None else None


def get_theme_blob(session: Session, tag: str) -> bytes | None:
    '''The raw serialized theme, without deserializing it (for caching/download).'''
    return session.scalar(select(ThemeRecord.data).where(ThemeRecord.tag == tag))


def theme_tags(session: Session) -> list[str]:
    return list(session.scalars(select(ThemeRecord.tag).order_by(ThemeRecord.tag)))


def upsert_theme(session: Session, theme: KDETheme) -> None:
    record = session.scalar(select(ThemeRecord).where(ThemeRecord.tag == theme.tag))
    if record is None:
        session.add(ThemeRecord(
            tag=theme.tag, name=theme.name, desc=theme.desc,
            source=theme.source, data=theme.serialize(),
        ))
    else:
        record.name, record.desc = theme.name, theme.desc
        record.source, record.data = theme.source, theme.serialize()


def delete_theme(session: Session, tag: str) -> bool:
    '''Delete a theme by tag; returns True if a row was removed.'''
    record = session.scalar(select(ThemeRecord).where(ThemeRecord.tag == tag))
    if record is None:
        return False
    session.delete(record)
    return True


# --------------------------------------------------------------------------- #
# artifacts (named binary blobs)

def get_artifact(session: Session, key: str) -> bytes | None:
    record = session.scalar(select(ArtifactRecord).where(ArtifactRecord.key == key))
    return record.data if record is not None else None


def put_artifact(session: Session, key: str, data: bytes) -> None:
    record = session.scalar(select(ArtifactRecord).where(ArtifactRecord.key == key))
    if record is None:
        session.add(ArtifactRecord(key=key, data=data))
    else:
        record.data = data
