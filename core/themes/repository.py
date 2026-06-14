'''
Read/write helpers for the theme table. Themes are handled as raw blobs here
(tag, kind, data); deserialising a blob into a live region/Theme is the job of
core.themes.library, which keeps this repository free of any pipeline dependency.
'''

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database.models import ThemeRecord


def all_theme_records(session: Session) -> list[tuple[str, str, bytes]]:
    '''(tag, kind, data) for every stored theme region, ordered by tag.'''
    rows = session.execute(
        select(ThemeRecord.tag, ThemeRecord.kind, ThemeRecord.data)
        .order_by(ThemeRecord.tag)
    )
    return [(row.tag, row.kind, row.data) for row in rows]


def get_theme_blob(session: Session, tag: str) -> bytes | None:
    '''The raw serialized theme, without deserializing it (for caching/download).'''
    return session.scalar(select(ThemeRecord.data).where(ThemeRecord.tag == tag))


def theme_tags(session: Session) -> list[str]:
    return list(session.scalars(select(ThemeRecord.tag).order_by(ThemeRecord.tag)))


def upsert_theme(session: Session, tag: str, name: str, desc: str,
                 source: str, kind: str, data: bytes) -> None:
    record = session.scalar(select(ThemeRecord).where(ThemeRecord.tag == tag))
    if record is None:
        session.add(ThemeRecord(
            tag=tag, name=name, desc=desc, source=source, kind=kind, data=data,
        ))
    else:
        record.name, record.desc = name, desc
        record.source, record.kind, record.data = source, kind, data


def delete_theme(session: Session, tag: str) -> bool:
    '''Delete a theme by tag; returns True if a row was removed.'''
    record = session.scalar(select(ThemeRecord).where(ThemeRecord.tag == tag))
    if record is None:
        return False
    session.delete(record)
    return True