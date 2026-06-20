'''
Entry point for the task scheduler:  ``python run.py``

Loads ``schedule.toml`` from the repo root, wires a papermill
``NotebookRunner`` over ``core/tasks``, and starts a blocking ``Scheduler`` that
runs each task notebook on its configured cron/interval/tick trigger.
'''

from __future__ import annotations

import logging
import os

import config
from core.scheduler import NotebookRunner, Scheduler, load_schedule
from core.tasks import TASKS_DIR

logger = logging.getLogger(__name__)

SCHEDULE_PATH = config.ROOT / 'schedule.toml'

# scikit-learn lazily dlopens libgomp deep in the generation path; on the
# aarch64 Linux host this fails with "cannot allocate memory in static TLS
# block". Preloading libgomp so it is mapped at process startup avoids it. The
# papermill task subprocesses (which import sklearn) inherit this env, and the
# library only exists on that host, so this is a no-op elsewhere (e.g. Windows).
_LIBGOMP = '/usr/lib/aarch64-linux-gnu/libgomp.so.1'


def _preload_libgomp() -> None:
    if not os.path.exists(_LIBGOMP):
        return
    preload = os.environ.get('LD_PRELOAD', '')
    if _LIBGOMP in preload.split(':'):
        return
    os.environ['LD_PRELOAD'] = f'{_LIBGOMP}:{preload}' if preload else _LIBGOMP
    logger.info('preloading libgomp (LD_PRELOAD=%s)', os.environ['LD_PRELOAD'])


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )
    _preload_libgomp()

    settings, tasks = load_schedule(SCHEDULE_PATH)
    runner = NotebookRunner(tasks_dir=TASKS_DIR, cwd=config.ROOT)
    Scheduler(settings, tasks, runner).start()


if __name__ == '__main__':
    main()
