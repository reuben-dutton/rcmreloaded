'''
Schedule strategies: turn a single "start" date into the four lifecycle dates
a theme vote needs (when voting opens/closes and when the winning theme's
window opens/closes).

A strategy is any object with a ``schedule(start) -> VoteSchedule`` method, so
new cadences can be dropped in without touching the generator. ``DefaultSchedule``
is the current behaviour.
'''

from __future__ import annotations

import dataclasses
import datetime


@dataclasses.dataclass
class VoteSchedule:
    '''The four lifecycle dates a theme vote is built from.'''

    vote_start_date: datetime.datetime
    vote_end_date: datetime.datetime
    theme_start_date: datetime.datetime
    theme_end_date: datetime.datetime


class _ScheduleStrategy:
    '''Maps a start date to a :class:`VoteSchedule`. Subclass and override.'''

    def schedule(self, start: datetime.datetime) -> VoteSchedule:
        raise NotImplementedError


class DefaultSchedule(_ScheduleStrategy):
    '''
    The current default. From the provided ``start`` date:

      - ``vote_start_date``  = start
      - ``vote_end_date``    = start + 1 day
      - ``theme_start_date`` = start + 1 day
      - ``theme_end_date``   = start + 3 days
    '''

    def schedule(self, start: datetime.datetime) -> VoteSchedule:
        return VoteSchedule(
            vote_start_date=start,
            vote_end_date=start + datetime.timedelta(days=1),
            theme_start_date=start + datetime.timedelta(days=1),
            theme_end_date=start + datetime.timedelta(days=3),
        )
