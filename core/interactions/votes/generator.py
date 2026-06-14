'''
``ThemeVoteGenerator`` ties a theme-selection strategy and a schedule strategy
together to build a theme vote.

Both halves are plug-and-play: pass any :class:`_ThemeSelection` and any
:class:`_ScheduleStrategy` to mix and match. With neither supplied it uses the
current defaults - :class:`AllThemesSelection` and :class:`DefaultSchedule`.

``generate`` does no I/O: it returns an unsaved ``ThemeVote`` DTO. Persisting it
is the caller's job, via ``core.interactions.add_theme_vote``:

    from core.interactions.votes import ThemeVoteGenerator, add_theme_vote
    from core.database import session_scope

    vote = ThemeVoteGenerator().generate()      # build (no database)
    with session_scope() as session:
        vote = add_theme_vote(session, vote)     # persist
'''

from __future__ import annotations

import datetime

from core.database.models import ThemeVoteType
from core.interactions.votes.schemas import ThemeOption, ThemeVote
from core.interactions.votes.schedules import DefaultSchedule, _ScheduleStrategy
from core.interactions.votes.selection import AllThemesSelection, _ThemeSelection
from core.themes import themes


class ThemeVoteGenerator:
    '''
    Builds a :class:`ThemeVote` from a selection strategy (which themes go on
    the ballot) and a schedule strategy (how the start date maps to the vote's
    lifecycle dates). The returned DTO is unsaved - ids are filled in only once
    a caller persists it.
    '''

    def __init__(
        self,
        selection: _ThemeSelection | None = None,
        schedule: _ScheduleStrategy | None = None,
    ):
        self.selection = selection or AllThemesSelection()
        self.schedule = schedule or DefaultSchedule()

    def generate(
        self,
        start_date: datetime.datetime | None = None,
        *,
        type: ThemeVoteType = ThemeVoteType.DEFAULT,
    ) -> ThemeVote:
        '''
        Build an unsaved theme vote. ``start_date`` defaults to now in UTC; the
        schedule strategy expands it into the four lifecycle dates and the
        selection strategy chooses the ballot.
        '''
        start_date = start_date or datetime.datetime.now(datetime.timezone.utc)
        schedule = self.schedule.schedule(start_date)

        options = []
        for tag in self.selection.select():
            theme = themes.get(tag)
            options.append(ThemeOption(
                theme_tag=tag,
                theme_name=theme.name if theme is not None else tag,
            ))

        return ThemeVote(
            type=type,
            vote_start_date=schedule.vote_start_date,
            vote_end_date=schedule.vote_end_date,
            theme_start_date=schedule.theme_start_date,
            theme_end_date=schedule.theme_end_date,
            options=options,
        )
