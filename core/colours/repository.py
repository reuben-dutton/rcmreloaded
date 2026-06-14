'''Read/write helpers for the colour table, bridging ColourRecord and Colour.'''

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.colours.schemas import Colour
from core.database.models import ColourRecord


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
