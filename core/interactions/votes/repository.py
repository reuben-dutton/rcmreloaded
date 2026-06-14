'''
The theme-vote repository: persist and query ``ThemeVote`` DTOs against the
theme_votes / theme_options tables.
'''

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.database.models import ThemeOptionRecord, ThemeRecord, ThemeVoteRecord
from core.interactions.votes.schemas import ThemeVote

# eager-load options (and each option's theme) so the DTO can be built without
# a second query and the record stays valid while we read it
_VOTE_LOAD = selectinload(ThemeVoteRecord.options).selectinload(
    ThemeOptionRecord.theme
)


def add_theme_vote(session: Session, vote: ThemeVote) -> ThemeVote:
    '''
    Persist a ``ThemeVote`` DTO (typically produced by ThemeVoteGenerator) and
    return the saved DTO, with ids and managed timestamps filled in. Each
    option's ``theme_tag`` is resolved to a stored theme; raises ``KeyError`` if
    any tag has no match.
    '''
    record = ThemeVoteRecord(
        type=vote.type,
        post_uri=vote.post_uri,
        post_cid=vote.post_cid,
        vote_start_date=vote.vote_start_date,
        vote_end_date=vote.vote_end_date,
        theme_start_date=vote.theme_start_date,
        theme_end_date=vote.theme_end_date,
    )
    for option in vote.options:
        theme = session.scalar(
            select(ThemeRecord).where(ThemeRecord.tag == option.theme_tag)
        )
        if theme is None:
            raise KeyError(f'No theme: {option.theme_tag}')
        record.options.append(ThemeOptionRecord(
            theme=theme,
            comment_uri=option.comment_uri,
            comment_cid=option.comment_cid,
            likes=option.likes,
        ))
    session.add(record)
    session.flush()  # populate ids / managed defaults before we build the DTO
    return ThemeVote.model_validate(record)


def get_theme_vote(session: Session, vote_id: int) -> ThemeVote | None:
    record = session.scalar(
        select(ThemeVoteRecord)
        .where(ThemeVoteRecord._id == vote_id)
        .options(_VOTE_LOAD)
    )
    return ThemeVote.model_validate(record) if record is not None else None


def all_theme_votes(session: Session) -> list[ThemeVote]:
    records = session.scalars(
        select(ThemeVoteRecord).order_by(ThemeVoteRecord._id).options(_VOTE_LOAD)
    )
    return [ThemeVote.model_validate(r) for r in records]


def active_theme_vote(
    session: Session, at: datetime.datetime | None = None
) -> ThemeVote | None:
    '''
    The theme vote whose window currently contains ``at`` (defaults to now in
    UTC), i.e. ``vote_start_date <= at <= theme_end_date``. Votes never overlap,
    so there is at most one - returns its DTO, or None if nothing is active.
    '''
    at = at or datetime.datetime.now(datetime.timezone.utc)
    record = session.scalar(
        select(ThemeVoteRecord)
        .where(
            ThemeVoteRecord.vote_start_date <= at,
            ThemeVoteRecord.theme_end_date >= at,
        )
        .order_by(ThemeVoteRecord.vote_start_date)
        .options(_VOTE_LOAD)
    )
    return ThemeVote.model_validate(record) if record is not None else None


def delete_theme_vote(session: Session, vote_id: int) -> bool:
    '''Delete a vote (and its options) by id; True if a row was removed.'''
    record = session.scalar(
        select(ThemeVoteRecord).where(ThemeVoteRecord._id == vote_id)
    )
    if record is None:
        return False
    session.delete(record)
    return True
