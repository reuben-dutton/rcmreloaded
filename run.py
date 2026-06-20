'''
Entry point for the task scheduler:  ``python run.py``

Loads ``schedule.toml`` from the repo root, wires a papermill
``NotebookRunner`` over ``core/tasks``, and starts a blocking ``Scheduler`` that
runs each task notebook on its configured cron/interval/tick trigger.
'''

from __future__ import annotations

import glob
import importlib.util
import logging
import os
import sys

import config
from core.scheduler import NotebookRunner, Scheduler, load_schedule
from core.tasks import TASKS_DIR

logger = logging.getLogger(__name__)

SCHEDULE_PATH = config.ROOT / 'schedule.toml'


def _bundled_libgomp() -> str | None:
    '''
    Path to scikit-learn's vendored OpenMP runtime
    (``.../site-packages/scikit_learn.libs/libgomp-<hash>.so.1``), or None.
    Found via the import machinery without importing sklearn - importing it is
    what triggers the TLS failure we're trying to avoid.
    '''
    spec = importlib.util.find_spec('sklearn')
    if spec is None or not spec.origin:
        return None
    site_packages = os.path.dirname(os.path.dirname(spec.origin))
    matches = sorted(
        glob.glob(os.path.join(site_packages, 'scikit_learn.libs', 'libgomp*.so*'))
    )
    return matches[0] if matches else None


def _fix_static_tls() -> None:
    '''
    Work around scikit-learn failing to load its OpenMP runtime on aarch64
    Linux with "cannot allocate memory in static TLS block".

    sklearn lazily ``dlopen``s its *bundled* libgomp deep in the generation
    path, by which point the process's static-TLS surplus is exhausted. We
    (1) enlarge that surplus via ``GLIBC_TUNABLES`` (soname-agnostic) and
    (2) preload that exact bundled libgomp so it is mapped at startup while the
    surplus is still available. The papermill task subprocesses (which import
    sklearn) inherit both and their loader applies them. No-op off Linux.
    '''
    if not sys.platform.startswith('linux'):
        return

    # 1. enlarge the static-TLS surplus (needs glibc >= 2.34)
    tunables = os.environ.get('GLIBC_TUNABLES', '')
    if 'optional_static_tls' not in tunables:
        tunable = 'glibc.rtld.optional_static_tls=2000000'
        os.environ['GLIBC_TUNABLES'] = f'{tunables}:{tunable}' if tunables else tunable

    # 2. preload the bundled libgomp so it loads before the surplus runs out
    libgomp = _bundled_libgomp()
    if libgomp:
        preload = os.environ.get('LD_PRELOAD', '')
        if libgomp not in preload.split(':'):
            os.environ['LD_PRELOAD'] = f'{libgomp}:{preload}' if preload else libgomp

    logger.info(
        'static-TLS workaround applied: GLIBC_TUNABLES=%s LD_PRELOAD=%s',
        os.environ.get('GLIBC_TUNABLES'), os.environ.get('LD_PRELOAD'),
    )


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )
    _fix_static_tls()

    settings, tasks = load_schedule(SCHEDULE_PATH)
    runner = NotebookRunner(tasks_dir=TASKS_DIR, cwd=config.ROOT)
    Scheduler(settings, tasks, runner).start()


if __name__ == '__main__':
    main()
