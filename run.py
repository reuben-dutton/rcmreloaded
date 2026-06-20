'''
Entry point for the task scheduler:  ``python run.py``

Loads ``schedule.toml`` from the repo root, wires a papermill
``NotebookRunner`` over ``core/tasks``, and starts a blocking ``Scheduler`` that
runs each task notebook on its configured cron/interval/tick trigger.
'''

from __future__ import annotations

import logging

import config
from core.scheduler import NotebookRunner, Scheduler, load_schedule
from core.tasks import TASKS_DIR

SCHEDULE_PATH = config.ROOT / 'schedule.toml'


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    settings, tasks = load_schedule(SCHEDULE_PATH)
    runner = NotebookRunner(tasks_dir=TASKS_DIR, cwd=config.ROOT)
    Scheduler(settings, tasks, runner).start()


if __name__ == '__main__':
    main()
