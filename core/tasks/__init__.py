'''
Scheduled tasks: one notebook per unit of work the scheduler runs.

Each notebook here is a self-contained, headless job (post a generation, post a
theme vote, update the latest vote's likes). They are executed by
``core.scheduler`` via papermill with the repository root as the working
directory, so they ``import config`` / ``from core...`` exactly like the
interactive notebooks at the repo root.

A notebook may declare a papermill ``parameters`` cell; the only one used today
is ``dry_run`` (build/compute but skip the Bluesky post and DB write).
'''

from __future__ import annotations

import pathlib

# Directory holding the task notebooks; the scheduler resolves notebook names
# (e.g. "post_generation.ipynb") relative to this.
TASKS_DIR = pathlib.Path(__file__).resolve().parent

__all__ = ['TASKS_DIR']
