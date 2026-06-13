'''
FastAPI app for the theme editor + library.

Run from the repo root (the layer code loads fonts via relative paths):

    poetry run uvicorn webeditor.app:app --port 8321

Design notes for performance:
  - The scored colour grid is shipped once per fit as a single binary
    payload; the threshold and saturation-penalty sliders are evaluated in
    the client's vertex shader, so dragging them never touches the server.
  - Fits, grids, themes and swatches are all cached (see service.py).
'''

import pathlib

from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from webeditor import service

app = FastAPI(title='rcm theme editor')

STATIC = pathlib.Path(__file__).parent / 'static'


# ---------------------------------------------------------------------------
# library

@app.get('/api/themes')
def get_themes():
    return service.list_themes()


@app.get('/api/themes/{tag}/swatches')
def get_theme_swatches(tag: str, n: int = 6):
    try:
        return service.theme_swatches(tag, min(n, 16))
    except FileNotFoundError:
        raise HTTPException(404, f'No theme: {tag}')


@app.get('/api/themes/{tag}/grid')
def get_theme_grid(tag: str, steps: int = service.GRID_STEPS_DEFAULT):
    '''Binary density grid for an existing theme (for the editor view).'''
    steps = max(4, min(steps, 40))
    try:
        theme = service.load_theme(tag)
    except FileNotFoundError:
        raise HTTPException(404, f'No theme: {tag}')
    grid_rgb, log_density = service.score_grid(theme._kd, steps, cache_key=f'theme:{tag}')
    meta = {
        'steps': steps,
        'tag': tag,
        'name': theme.name,
        'desc': theme.desc,
        'source': theme.source,
        'threshold': theme._log_density_threshold,
        'sat_penalty': theme._saturation_penalty,
        'shade_penalty': getattr(theme, '_shade_penalty', 0.0),
        'tint_penalty': getattr(theme, '_tint_penalty', 0.0),
    }
    payload = service.pack_grid(meta, grid_rgb, log_density)
    return Response(payload, media_type='application/octet-stream')


@app.delete('/api/themes/{tag}')
def remove_theme(tag: str):
    try:
        service.delete_theme(tag)
    except FileNotFoundError:
        raise HTTPException(404, f'No theme: {tag}')
    return {'deleted': tag}


@app.get('/api/themes/{tag}/file')
def download_theme(tag: str):
    try:
        data = service.theme_file_bytes(tag)
    except FileNotFoundError:
        raise HTTPException(404, f'No theme: {tag}')
    return Response(
        data,
        media_type='application/octet-stream',
        headers={'Content-Disposition': f'attachment; filename="{tag}.rcmt"'},
    )


# ---------------------------------------------------------------------------
# fitting

@app.post('/api/images')
async def upload_image(file: UploadFile):
    data = await file.read()
    if len(data) > 32 * 1024 * 1024:
        raise HTTPException(413, 'Image too large (32MB max)')
    try:
        image_id = service.store_image(data)
    except Exception:
        raise HTTPException(400, 'Could not decode image')
    return {'image_id': image_id}


@app.get('/api/fit/grid')
def fit_grid(image_id: str, bandwidth: float = 3, max_fit_px: int = 20000,
             steps: int = service.GRID_STEPS_DEFAULT):
    '''Fit (or reuse) a KDE for the image and return its binary density grid.'''
    steps = max(4, min(steps, 40))
    bandwidth = max(0.5, min(bandwidth, 50))
    max_fit_px = max(500, min(max_fit_px, 100_000))
    try:
        kde = service.fit_kde(image_id, bandwidth, max_fit_px)
    except KeyError as e:
        raise HTTPException(404, str(e))
    key = service.fit_key(image_id, bandwidth, max_fit_px)
    grid_rgb, log_density = service.score_grid(kde, steps, cache_key=key)
    payload = service.pack_grid({'steps': steps, 'fit_key': key}, grid_rgb, log_density)
    return Response(payload, media_type='application/octet-stream')


# ---------------------------------------------------------------------------
# previews + saving — these accept either a fit_key (new theme from an image)
# or a tag (editing an existing theme's KDE)

class PreviewRequest(BaseModel):
    fit_key: str | None = None
    tag: str | None = None
    threshold: float
    log_max: float
    sat_penalty: float
    shade_penalty: float = 0
    tint_penalty: float = 0
    n: int = 6
    layout: str | None = None


def _resolve_kde(req) -> 'object':
    if req.fit_key:
        return service.kde_for_fit_key(req.fit_key)
    if req.tag:
        return service.load_theme(req.tag)._kd
    raise HTTPException(422, 'Provide fit_key or tag')


@app.post('/api/preview/swatches')
def preview_swatches(req: PreviewRequest):
    try:
        kde = _resolve_kde(req)
        kde_key = req.fit_key or service.theme_kde_key(req.tag)
    except (KeyError, FileNotFoundError) as e:
        raise HTTPException(404, str(e))
    return service.swatches_cached(
        kde_key, kde, req.threshold, req.log_max, req.sat_penalty,
        req.shade_penalty, req.tint_penalty, min(req.n, 100),
    )


@app.post('/api/preview/frame')
def preview_frame(req: PreviewRequest):
    if not req.layout:
        raise HTTPException(422, 'Provide a layout')
    try:
        kde = _resolve_kde(req)
        n = service.layout_count(req.layout)
    except (KeyError, FileNotFoundError) as e:
        raise HTTPException(404, str(e))

    colours = service.sample_accepted(
        kde, req.threshold, req.log_max, req.sat_penalty,
        req.shade_penalty, req.tint_penalty, n,
    )
    if len(colours) < n:
        raise HTTPException(409, 'Theme region too small to sample enough colours')
    png = service.render_frame(colours, req.layout)
    return Response(png, media_type='image/png')


class MixRequest(BaseModel):
    tags: list[str]
    n: int = 100
    layout: str | None = None


@app.post('/api/mix/swatches')
def mix_swatches(req: MixRequest):
    if not req.tags:
        raise HTTPException(422, 'Provide at least one theme tag')
    try:
        return service.mix_swatches_cached(req.tags, min(req.n, 100))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@app.post('/api/mix/frame')
def mix_frame(req: MixRequest):
    if not req.tags:
        raise HTTPException(422, 'Provide at least one theme tag')
    if not req.layout:
        raise HTTPException(422, 'Provide a layout')
    try:
        n = service.layout_count(req.layout)
        colours_raw = service.sample_mix(req.tags, n)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except KeyError:
        raise HTTPException(422, f'Unknown layout: {req.layout}')
    if len(colours_raw) < n:
        raise HTTPException(409, 'Mixed region too small to sample enough colours')
    png = service.render_frame(colours_raw, req.layout)
    return Response(png, media_type='image/png')


class SaveRequest(BaseModel):
    fit_key: str | None = None
    tag: str | None = None  # source theme when editing
    name: str
    desc: str = ''
    source: str = ''
    threshold: float
    sat_penalty: float
    shade_penalty: float = 0
    tint_penalty: float = 0
    previous_tag: str | None = None  # delete this file after saving (a rename)


@app.post('/api/themes')
def post_theme(req: SaveRequest):
    try:
        kde = _resolve_kde(req)
    except (KeyError, FileNotFoundError) as e:
        raise HTTPException(404, str(e))
    try:
        saved = service.save_theme(
            kde, req.name, req.desc, req.source, req.threshold,
            req.sat_penalty, req.shade_penalty, req.tint_penalty,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))

    if req.previous_tag and req.previous_tag != saved['tag']:
        try:
            service.delete_theme(req.previous_tag)
        except FileNotFoundError:
            pass
    return saved


app.mount('/', StaticFiles(directory=STATIC, html=True), name='static')
