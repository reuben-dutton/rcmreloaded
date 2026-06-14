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
from core.interactions.votes import content


def _as_naive_utc(dt: datetime.datetime) -> datetime.datetime:
    '''
    Drop tz info (converting to UTC first) so naive timestamps - how SQLite
    stores them - and aware ones - how Postgres does - compare consistently.
    '''
    if dt.tzinfo is not None:
        dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return dt


class ThemeOption(BaseModel):
    '''One theme on a vote's ballot, with its Bluesky reply id and like tally.'''

    model_config = ConfigDict(from_attributes=True)

    # None until persisted (a generated, not-yet-saved option has no id)
    id: int | None = None
    theme_tag: str
    theme_name: str
    theme_source: str = 'generic'
    theme_desc: str = ''
    comment_uri: str | None = None
    comment_cid: str | None = None
    likes: int | None = None

    @property
    def comment_text(self) -> str:
        '''
        The Bluesky reply text for this option - people vote by liking it.
        Wording comes from ``content.COMMENT_TEXT`` (the theme's name, source
        and description).
        '''
        source = "" if self.theme_source == 'generic' else f" ({self.theme_source})"
        return content.COMMENT_TEXT.format(
            theme_name=self.theme_name,
            theme_source=source,
            theme_desc=self.theme_desc,
        )


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
    def post_text(self) -> str:
        '''
        The Bluesky text for the main poll post. Wording comes from
        ``content.POST_TEXT``; ``{themes}`` is filled with the ballot's theme
        names, one per line.
        '''
        themes = '\n'.join(option.theme_name for option in self.options)
        return content.POST_TEXT.format(themes=themes)

    @property
    def winner(self) -> ThemeOption | None:
        '''The option with the most likes, or None if nothing is tallied yet.'''
        tallied = [o for o in self.options if o.likes is not None]
        return max(tallied, key=lambda o: o.likes or 0) if tallied else None

    @property
    def voting(self) -> bool:
        '''
        True if voting is currently open - now (UTC) falls within
        ``vote_start_date <= now <= vote_end_date``.
        '''
        return self._window_contains_now(self.vote_start_date, self.vote_end_date)

    @property
    def active(self) -> bool:
        '''
        True if the winning theme is currently active - now (UTC) falls within
        ``theme_start_date <= now <= theme_end_date``.
        '''
        return self._window_contains_now(self.theme_start_date, self.theme_end_date)

    def _window_contains_now(
        self,
        start: datetime.datetime | None,
        end: datetime.datetime | None,
    ) -> bool:
        '''True if now (UTC) is within [start, end]; False if either is unset.'''
        if start is None or end is None:
            return False
        now = _as_naive_utc(datetime.datetime.now(datetime.timezone.utc))
        return _as_naive_utc(start) < now <= _as_naive_utc(end)
