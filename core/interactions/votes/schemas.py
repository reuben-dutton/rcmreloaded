'''
The theme-vote DTOs: ``ThemeVote`` and its nested ``ThemeOption``.

Built from the ThemeVoteRecord / ThemeOptionRecord ORM rows via
``model_validate(record)``; the managed bookkeeping columns (insert/update/check
timestamps) live on the records only and are intentionally not surfaced here.
'''

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict

from core.database.models import ThemeVoteType


class ThemeOption(BaseModel):
    '''One theme on a vote's ballot, with its Bluesky reply id and like tally.'''

    model_config = ConfigDict(from_attributes=True)

    # None until persisted (a generated, not-yet-saved option has no id)
    id: int | None = None
    theme_tag: str
    theme_name: str
    comment_uri: str | None = None
    comment_cid: str | None = None
    likes: int | None = None


class ThemeVote(BaseModel):
    '''
    A theme poll and its options. Built from a ThemeVoteRecord via
    ``model_validate(record)``; the nested options come from the record's
    ``options`` relationship (each a ThemeOptionRecord -> ThemeOption).
    '''

    model_config = ConfigDict(from_attributes=True)

    # None until persisted (a generated, not-yet-saved vote has no id)
    id: int | None = None
    type: ThemeVoteType
    post_uri: str | None = None
    post_cid: str | None = None
    vote_start_date: datetime.datetime | None = None
    vote_end_date: datetime.datetime | None = None
    theme_start_date: datetime.datetime | None = None
    theme_end_date: datetime.datetime | None = None
    options: list[ThemeOption] = []

    @property
    def winner(self) -> ThemeOption | None:
        '''The option with the most likes, or None if nothing is tallied yet.'''
        tallied = [o for o in self.options if o.likes is not None]
        return max(tallied, key=lambda o: o.likes or 0) if tallied else None
