'''
Run a task notebook headlessly with papermill.

The scheduler hands a notebook filename to :meth:`NotebookRunner.run`; the
runner executes that notebook from ``core/tasks`` with the repository root as
the working directory (so the notebook's ``import config`` / ``from core...``
resolve exactly as they do interactively). The executed copy is not saved - a
failing notebook surfaces as an exception carrying the failing cell's traceback.
'''

from __future__ import annotations

import pathlib

import papermill


class NotebookRunner:
    '''Executes notebooks from ``tasks_dir`` with ``cwd`` as the working dir.'''

    def __init__(
        self,
        tasks_dir: str | pathlib.Path,
        cwd: str | pathlib.Path,
    ):
        self.tasks_dir = pathlib.Path(tasks_dir)
        self.cwd = pathlib.Path(cwd)

    def run(self, notebook: str, parameters: dict | None = None) -> None:
        '''
        Execute ``notebook`` (a filename in ``tasks_dir``). ``parameters`` are
        injected into the notebook's papermill ``parameters`` cell (e.g.
        ``{'dry_run': True}``). Raises if the notebook errors.
        '''
        input_path = self.tasks_dir / notebook
        if not input_path.exists():
            raise FileNotFoundError(f'task notebook not found: {input_path}')

        papermill.execute_notebook(
            str(input_path),
            None,  # don't persist the executed notebook
            parameters=parameters or {},
            cwd=str(self.cwd),
            progress_bar=False,
        )
