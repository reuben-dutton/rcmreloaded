# rcmreloaded

A Bluesky bot that generates and posts images of randomly generated colour
palettes — themed via KDE models over colour space, arranged into frames,
and annotated with colour names and hex codes.

## Setup

Requires Python 3.12+ and [Poetry](https://python-poetry.org/):

```
poetry install
```

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

## Theme studio (web editor)

Run from the repo root (frame previews load fonts via relative paths):

```
poetry run uvicorn webeditor.app:app --port 8321 --reload
```

Then open http://127.0.0.1:8321/. The `--reload` flag is optional; it picks
up backend changes without a restart.

Three tabs:

- **Library** — browse, search, edit, download, or delete the themes in
  `data/themes/`.
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
from pipeline.pipeline import Pipeline
from pipeline.enums import Theme, Palette, Frame, Sample

image, colours = (
    Pipeline()
    .filter(Theme.load('sunset') | Theme.load('vaporwave'))  # | mixes themes
    .palette(Palette.RANDOM)
    .generate({'blank': False, 'min_delta_e': 15})  # min CIEDE2000 between samples
)
```

Unset stages resolve randomly; see `pipeline/enums.py` for all generators,
palettes, frames, and sample counts.
