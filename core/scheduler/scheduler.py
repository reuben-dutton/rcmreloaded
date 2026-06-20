'''
The Scheduler: register task notebooks with APScheduler and run each on its
configured trigger.

In-memory only - there is no job persistence. With ``misfire_grace_time`` kept
small, a run that can't fire on time (the process was down, or a previous run is
still going) is dropped rather than replayed late - the "cancelled, not delayed"
behaviour the fixed-time tasks want. Tick jobs additionally ``coalesce`` so a
backlog collapses into a single run.
'''

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from core.scheduler.runner import NotebookRunner
from core.scheduler.schedule import SchedulerSettings, TaskSchedule

logger = logging.getLogger(__name__)


class Scheduler:
    '''Wires :class:`TaskSchedule`s to a :class:`NotebookRunner` via APScheduler.'''

    def __init__(
        self,
        settings: SchedulerSettings,
        tasks: list[TaskSchedule],
        runner: NotebookRunner,
        scheduler: BlockingScheduler | None = None,
    ):
        self.settings = settings
        self.tasks = tasks
        self.runner = runner
        self._scheduler = scheduler or BlockingScheduler(
            timezone=settings.tzinfo,
            job_defaults={
                'misfire_grace_time': settings.misfire_grace_time,
                'max_instances': 1,
                'coalesce': False,
            },
        )
        self._register()

    def _register(self) -> None:
        for task in self.tasks:
            self._scheduler.add_job(
                self._run_task,
                trigger=task.trigger,
                args=[task],
                id=task.name,
                name=task.name,
                coalesce=task.coalesce,
                max_instances=task.max_instances,
                replace_existing=True,
            )
            logger.info('registered task %r (%s)', task.name, task.trigger)

    def _run_task(self, task: TaskSchedule) -> None:
        # one task failing must never take down the scheduler
        logger.info('running task %r', task.name)
        try:
            self.runner.run(task.notebook)
        except Exception:
            logger.exception('task %r failed', task.name)
            return
        logger.info('task %r finished', task.name)

    def start(self) -> None:
        '''Start the scheduler; blocks until interrupted (Ctrl-C / SIGTERM).'''
        logger.info('scheduler starting with %d task(s)', len(self.tasks))
        try:
            self._scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info('scheduler stopping')
            self.shutdown()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
