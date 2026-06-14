'''Generic named binary-blob access (the artifacts table).'''

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database.models import ArtifactRecord


def get_artifact(session: Session, key: str) -> bytes | None:
    record = session.scalar(select(ArtifactRecord).where(ArtifactRecord.key == key))
    return record.data if record is not None else None


def put_artifact(session: Session, key: str, data: bytes) -> None:
    record = session.scalar(select(ArtifactRecord).where(ArtifactRecord.key == key))
    if record is None:
        session.add(ArtifactRecord(key=key, data=data))
    else:
        record.data = data
