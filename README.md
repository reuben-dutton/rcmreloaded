# rcmreloaded

A Bluesky bot that generates and posts images of randomly generated colour
palettes — themed via KDE models over colour space, arranged into frames,
and annotated with colour names and hex codes.

## Setup

Requires Python 3.12+ and [Poetry](https://python-poetry.org/):

```
poetry install
```

Colours and themes live in a SQLite database at `data/rcm.db`, which both
generation and the editor read from. (To rebuild the colour-naming lookup tree
after changing the colour set, run `tools/build_tree.ipynb`.)

To post to Bluesky, create a `.env` in the repo root:

```
ATPROTO_CLIENT_USERNAME=your-handle.bsky.social
ATPROTO_CLIENT_PASSWORD=your-app-password
```

## Posting

```
poetry run python post.py
```

Generates a random palette image and posts it.

## Scheduler

A long-running scheduler posts on a timetable, executing task notebooks from
`core/tasks/` with [APScheduler](https://apscheduler.readthedocs.io/) and
[papermill](https://papermill.readthedocs.io/):

```
poetry run python run.py
```

What runs, and when, is declared in `schedule.toml` in the repo root. Each
`[tasks.<name>]` names a notebook in `core/tasks/` and a trigger:

- `cron` — fire at fixed clock times. Use a 5-field crontab string
  (`cron = "0 9 * * mon"`) or individual fields (`hour`, `minute`, …).
- `interval` — fire every N units (`hours = 2`, `minutes = 30`, …).
- `tick` — a recurring poll for database-driven work: the notebook itself
  decides whether there's anything to do and no-ops otherwise. Used by
  `update_vote_likes`, which refreshes the active vote's like counts.

The scheduler keeps no job store. If the process is down when a fixed-time run
was due, that run is dropped rather than replayed late ("cancelled, not
delayed"); `misfire_grace_time` under `[scheduler]` sets how late a run may
start before it's skipped, and `tick` jobs coalesce a backlog into a single
run.

Each task notebook takes a papermill `dry_run` parameter (build/compute but
skip the Bluesky post and database write) and can be run on its own from VSCode
for testing.

## Theme studio (web editor)

Run from the repo root (so the `webeditor`, `core`, and `config` imports
resolve):

```
poetry run uvicorn webeditor.app:app --port 8321 --reload
```

Then open http://127.0.0.1:8321/. The `--reload` flag is optional; it picks
up backend changes without a restart.

Three tabs:

- **Library** — browse, search, edit, download, or delete the themes stored
  in the database. (Saving and deleting here affect what the bot posts.)
- **Editor** — create a theme from an image (drop one on the dropzone) or
  edit an existing one. Fit sliders refit the model server-side; the shape
  sliders (threshold, saturation/shade/tint penalties) run on the GPU and
  reshape the 3D colour cloud instantly. Preview sampled colours, a 10×10
  grid, and full frame renders, then save to the library.
- **Mixer** — select multiple themes and preview their mix (the `|`
  operator on themes; each colour is equally likely to come from each
  member): a 10×10 sample and frame renders.

## Generating in code

```python
from core.pipeline.pipeline import Pipeline
from core.pipeline.enums import Theme, Palette, Frame, Sample

image, colours = (
    Pipeline()
    .filter(Theme.load('sunset') | Theme.load('vaporwave'))  # | mixes themes
    .palette(Palette.RANDOM)
    .layout(Frame.RANDOM)
    .sample(Sample.RANDOM)
    .options(min_delta_e=15, blank=False)  # generation options
    .generate()
)
```

Generation options moved to a dedicated `.options()` step — `generate()` no
longer takes any arguments:

- `min_delta_e` — minimum CIEDE2000 distance enforced between sampled colours,
  so multi-sample frames can't come out near-identical (default `0`, off).
- `blank` — render frames as plain colour panels, without the name/hex
  annotations (default `False`).

The builder stages — `.filter()` (theme), `.palette()`, `.sample()`,
`.layout()` (frame), and `.options()` — are all optional; unset stages resolve
randomly. See `core/pipeline/enums.py` for all generators, palettes, frames,
and sample counts.

## Project layout

Application code lives under `core/`, organised by domain with a one-way
dependency flow — `database ← colours ← themes ← pipeline ← interactions` —
so each domain owns its own database access and imports stay close to use.

- `core/database/` — SQLAlchemy engine/session and the ORM record models.
- `core/colours/` — the `Colour` value type, the KD-tree colour naming, and
  the `colours` factory/library that constructs (and names) every colour.
- `core/themes/` — colour-space regions (e.g. `KDEThemeRegion`), the `Theme`
  container that composes them (`|` mixes), and the `themes` library.
- `core/pipeline/` — the declarative `Pipeline` and `enums`, plus
  `generators/`, `palettes/`, and `frames/` (with its `layers/`).
- `core/interactions/` — Bluesky/atproto-facing features; currently theme
  votes (`core/interactions/votes/`).
- `core/tasks/` — the scheduled task notebooks (post a generation, post a
  theme vote, update vote likes), run headlessly via papermill.
- `core/scheduler/` — the APScheduler-based `Scheduler` that runs those tasks
  on the schedule in `schedule.toml` (entry point: `run.py`).
- `webeditor/` — the theme studio (FastAPI backend + WebGL frontend).
- `data/` — the SQLite database (`rcm.db`) and fonts.
