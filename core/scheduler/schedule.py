'''
Parse schedule.toml into APScheduler triggers.

The TOML maps each task name to a notebook plus a trigger spec (cron / interval
/ tick). This module turns that into plain :class:`TaskSchedule` objects the
:class:`~core.scheduler.scheduler.Scheduler` registers, keeping every bit of
trigger-building in one place.
'''

from __future__ import annotations

import dataclasses
import datetime
import pathlib
import tomllib
import zoneinfo

from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# interval/tick keys -> IntervalTrigger kwargs (identical names)
_INTERVAL_FIELDS = ('weeks', 'days', 'hours', 'minutes', 'seconds')
# cron keys accepted instead of (or alongside) a `cron` crontab string
_CRON_FIELDS = (
    'year', 'month', 'day', 'week', 'day_of_week', 'hour', 'minute', 'second',
)


def _resolve_timezone(name: str) -> datetime.tzinfo:
    '''
    Resolve a timezone name to a tzinfo. ``UTC`` maps to the stdlib UTC so the
    default config works on Windows without the ``tzdata`` package; any other
    name goes through ``zoneinfo`` (which needs ``tzdata`` on Windows).
    '''
    if name.upper() == 'UTC':
        return datetime.timezone.utc
    return zoneinfo.ZoneInfo(name)


@dataclasses.dataclass(frozen=True)
class SchedulerSettings:
    '''Top-level ``[scheduler]`` options.'''

    timezone: str = 'UTC'
    misfire_grace_time: int = 30

    @property
    def tzinfo(self) -> datetime.tzinfo:
        return _resolve_timezone(self.timezone)


@dataclasses.dataclass(frozen=True)
class TaskSchedule:
    '''A single task: which notebook to run, on which trigger.'''

    name: str
    notebook: str
    trigger: BaseTrigger
    # tick jobs poll and must collapse a backlog to one run; fixed-time jobs
    # should drop missed runs instead.
    coalesce: bool
    max_instances: int = 1


def load_schedule(
    path: str | pathlib.Path,
) -> tuple[SchedulerSettings, list[TaskSchedule]]:
    '''Parse a schedule.toml file into settings plus a list of TaskSchedules.'''
    with open(path, 'rb') as handle:
        data = tomllib.load(handle)

    section = data.get('scheduler', {})
    settings = SchedulerSettings(
        timezone=section.get('timezone', 'UTC'),
        misfire_grace_time=int(section.get('misfire_grace_time', 30)),
    )
    tz = settings.tzinfo
    tasks = [
        _task(name, spec, tz)
        for name, spec in data.get('tasks', {}).items()
    ]
    return settings, tasks


def _task(name: str, spec: dict, tz: datetime.tzinfo) -> TaskSchedule:
    try:
        notebook = spec['notebook']
        kind = spec['trigger']
    except KeyError as missing:
        raise ValueError(f'task {name!r} is missing required key {missing}') from None

    trigger, coalesce = _trigger(name, kind, spec, tz)
    return TaskSchedule(
        name=name, notebook=notebook, trigger=trigger, coalesce=coalesce,
    )


def _trigger(
    name: str, kind: str, spec: dict, tz: datetime.tzinfo,
) -> tuple[BaseTrigger, bool]:
    if kind == 'cron':
        return _cron_trigger(name, spec, tz), False
    if kind == 'interval':
        return _interval_trigger(name, spec, tz), False
    if kind == 'tick':
        # a tick is just an interval whose backed-up runs collapse into one
        return _interval_trigger(name, spec, tz), True
    raise ValueError(
        f'task {name!r}: unknown trigger {kind!r} (expected cron/interval/tick)'
    )


def _cron_trigger(name: str, spec: dict, tz: datetime.tzinfo) -> CronTrigger:
    crontab = spec.get('cron')
    if crontab is not None:
        return CronTrigger.from_crontab(crontab, timezone=tz)
    fields = {field: spec[field] for field in _CRON_FIELDS if field in spec}
    if not fields:
        raise ValueError(
            f'task {name!r}: cron trigger needs a `cron` string or cron fields'
        )
    return CronTrigger(timezone=tz, **fields)


def _interval_trigger(name: str, spec: dict, tz: datetime.tzinfo) -> IntervalTrigger:
    fields = {field: spec[field] for field in _INTERVAL_FIELDS if field in spec}
    if not fields:
        raise ValueError(
            f'task {name!r}: {spec.get("trigger")} trigger needs at least one of '
            f'{", ".join(_INTERVAL_FIELDS)}'
        )
    return IntervalTrigger(timezone=tz, **fields)
