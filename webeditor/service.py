'''
Heavy lifting for the theme editor web app.

Everything here is vectorised: KDE grids are scored in one score_samples
call, and preview colours are drawn with a batched version of the bot's
CIELCh generator (vectorised bisection for the gamut boundary) so previews
are faithful to what the bot actually posts.

Themes live in the database (see the db package); this module loads, lists,
saves and deletes them there. Caching layers (all in-memory, keyed so stale
entries can't be served):
  - uploaded images by content hash
  - fitted KDEs by (image hash, bandwidth, max fit pixels)
  - scored grids by (fit key, grid steps)
  - library themes and their swatches by (tag, content hash of the stored blob)
'''

import hashlib
import io
import json
import pathlib
import random
import struct
import threading

import numpy as np
import skimage.color
import sklearn.neighbors
from PIL import Image

from db import repository, session_scope
from db.schemas import Colour
from pipeline.themes import KDETheme, to_tag


GRID_STEPS_DEFAULT = 20
GRID_STEPS_SAVE = 24  # fixed grid used when computing a theme's log-density maximum
SWATCH_BATCH = 4096
SWATCH_MAX_BATCHES = 12

SWATCH_CACHE_DIR = pathlib.Path(__file__).parent / 'cache' / 'swatches'

_lock = threading.Lock()
_images: dict[str, bytes] = {}
_fits: dict[tuple, sklearn.neighbors.KernelDensity] = {}
_grids: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
_themes: dict[tuple, KDETheme] = {}
_swatches: dict[str, list[dict]] = {}


# ---------------------------------------------------------------------------
# images + fitting

def store_image(data: bytes) -> str:
    image_id = hashlib.sha1(data).hexdigest()[:16]
    # validate it decodes before accepting it
    Image.open(io.BytesIO(data)).verify()
    with _lock:
        _images[image_id] = data
    return image_id


def get_image(image_id: str) -> bytes:
    with _lock:
        data = _images.get(image_id)
    if data is None:
        raise KeyError(f'No uploaded image with id {image_id}')
    return data


def fit_kde(image_id: str, bandwidth: float, max_fit_px: int) -> sklearn.neighbors.KernelDensity:
    key = (image_id, float(bandwidth), int(max_fit_px))
    with _lock:
        cached = _fits.get(key)
    if cached is not None:
        return cached

    img = Image.open(io.BytesIO(get_image(image_id))).convert('RGBA')
    # bound the pixel count before colour conversion, not after: rgb2lab on a
    # full-size photo costs more than the KDE fit itself
    if img.width * img.height > 4 * max_fit_px:
        scale = (4 * max_fit_px / (img.width * img.height)) ** 0.5
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))

    pixels = np.asarray(img).reshape(-1, 4)
    rgb = pixels[pixels[:, 3] > 0, :3] / 255.0
    if len(rgb) > max_fit_px:
        idx = np.random.choice(len(rgb), max_fit_px, replace=False)
        rgb = rgb[idx]
    lab = skimage.color.rgb2lab(rgb.reshape(-1, 1, 3)).reshape(-1, 3)

    # rtol trades a negligible amount of accuracy for much faster tree queries
    kde = sklearn.neighbors.KernelDensity(
        kernel='gaussian', bandwidth=bandwidth, leaf_size=1000, rtol=1e-4,
    )
    kde.fit(lab)

    with _lock:
        _fits[key] = kde
    return kde


def fit_key(image_id: str, bandwidth: float, max_fit_px: int) -> str:
    return f'{image_id}:{float(bandwidth)}:{int(max_fit_px)}'


def kde_for_fit_key(key: str) -> sklearn.neighbors.KernelDensity:
    image_id, bandwidth, max_fit_px = key.split(':')
    return fit_kde(image_id, float(bandwidth), int(max_fit_px))


# ---------------------------------------------------------------------------
# grid scoring

def score_grid(kde: sklearn.neighbors.KernelDensity, steps: int,
               cache_key: str | None = None) -> tuple[np.ndarray, np.ndarray]:
    '''
    Score a uniform RGB grid against the KDE. Returns (rgb uint8 [n,3],
    raw log densities float32 [n]) with NO saturation penalty applied -
    the client applies threshold and penalty on the GPU.
    '''
    if cache_key is not None:
        with _lock:
            cached = _grids.get((cache_key, steps))
        if cached is not None:
            return cached

    axis = np.linspace(0, 255, steps, dtype=np.uint8)
    r, g, b = np.meshgrid(axis, axis, axis, indexing='ij')
    grid_rgb = np.stack([r.ravel(), g.ravel(), b.ravel()], axis=1)
    grid_lab = skimage.color.rgb2lab((grid_rgb / 255.0).reshape(-1, 1, 3)).reshape(-1, 3)
    log_density = kde.score_samples(grid_lab).astype(np.float32)

    result = (grid_rgb.astype(np.uint8), log_density)
    if cache_key is not None:
        with _lock:
            _grids[(cache_key, steps)] = result
    return result


def pack_grid(meta: dict, grid_rgb: np.ndarray, log_density: np.ndarray) -> bytes:
    '''
    Pack the grid into one binary payload the client reads as an ArrayBuffer:
      uint32 LE json length | json meta (padded to 4 bytes) | float32 logd | uint8 rgb
    Saturation is not sent - it's derived from rgb in the vertex shader.
    '''
    meta = dict(meta, count=len(grid_rgb))
    raw = json.dumps(meta).encode()
    raw += b' ' * (-len(raw) % 4)  # keep the float32 view 4-byte aligned
    return struct.pack('<I', len(raw)) + raw + log_density.tobytes() + grid_rgb.tobytes()


def _apply_penalties(log_density: np.ndarray, rgb1: np.ndarray, sat_penalty: float,
                     shade_penalty: float, tint_penalty: float) -> np.ndarray:
    '''
    Penalise unsaturated (HSV S), dark (HWB blackness = 1 - max) and light
    (HWB whiteness = min) colours. rgb1 is [n, 3] in 0-1.
    '''
    mx = rgb1.max(axis=1)
    mn = rgb1.min(axis=1)
    sat = np.divide(mx - mn, mx, out=np.zeros_like(mx), where=mx > 0)
    return (
        log_density
        - sat_penalty * (1 - sat)
        - shade_penalty * (1 - mx)
        - tint_penalty * mn
    )


def penalised_max(log_density: np.ndarray, grid_rgb: np.ndarray, sat_penalty: float,
                  shade_penalty: float, tint_penalty: float) -> float:
    penalised = _apply_penalties(
        log_density, grid_rgb / 255.0, sat_penalty, shade_penalty, tint_penalty,
    )
    return float(penalised.max())


# ---------------------------------------------------------------------------
# vectorised CIELCh sampling (batched twin of pipeline.generators.CIELChGenerator)

import colorspacious  # noqa: E402  (heavy import kept near its only use)

_L_ALPHA, _L_BETA = 1.4, 1.4
_MAX_C = 250.0


def _max_chroma_batch(L: np.ndarray, h: np.ndarray, iterations: int = 12) -> np.ndarray:
    '''Vectorised bisection for the sRGB gamut boundary in CIELCh.'''
    lo = np.zeros_like(L)
    hi = np.full_like(L, _MAX_C)
    for _ in range(iterations):
        mid = (lo + hi) / 2
        rgb = colorspacious.cspace_convert(np.stack([L, mid, h], axis=1), 'CIELCh', 'sRGB1')
        in_gamut = np.all((rgb >= 0) & (rgb <= 1), axis=1)
        lo = np.where(in_gamut, mid, lo)
        hi = np.where(in_gamut, hi, mid)
    return lo


def _candidate_batch(n: int) -> np.ndarray:
    '''n candidate colours as uint8 rgb [n,3], matching the bot's generator.'''
    L = np.random.beta(_L_ALPHA, _L_BETA, n) * 100
    h = np.random.uniform(0, 360, n)
    max_c = _max_chroma_batch(L, h)
    c = np.sqrt(np.random.uniform(0, max_c ** 2))  # bias toward higher chroma
    rgb = colorspacious.cspace_convert(np.stack([L, c, h], axis=1), 'CIELCh', 'sRGB255')
    return np.clip(rgb, 0, 255).astype(np.uint8)


def sample_accepted(kde: sklearn.neighbors.KernelDensity | None, threshold: float,
                    log_max: float, sat_penalty: float, shade_penalty: float,
                    tint_penalty: float, n: int) -> list[Colour]:
    '''
    Draw n colours accepted by the theme, by scoring whole candidate batches
    at once instead of one rejection round-trip per colour.
    A None kde means the default (accept everything) theme.
    '''
    accepted: list[np.ndarray] = []
    for _ in range(SWATCH_MAX_BATCHES):
        need = n - len(accepted)
        if need <= 0:
            break
        rgb = _candidate_batch(SWATCH_BATCH if kde is not None else need)
        if kde is None:
            accepted.extend(rgb)
            continue

        rgb1 = rgb / 255.0
        lab = skimage.color.rgb2lab(rgb1.reshape(-1, 1, 3)).reshape(-1, 3)
        logd = kde.score_samples(lab)
        logd = _apply_penalties(logd, rgb1, sat_penalty, shade_penalty, tint_penalty)

        p = np.clip((logd - threshold) / (log_max - threshold), 0, 1)
        hits = rgb[np.random.rand(len(rgb)) < p]
        accepted.extend(hits[:need])

    return [Colour.from_rgb(tuple(int(v) for v in rgb)) for rgb in accepted[:n]]


# ---------------------------------------------------------------------------
# theme library

def theme_blob(tag: str) -> bytes:
    '''Raw serialized theme bytes from the DB; raises if the tag is unknown.'''
    with session_scope() as session:
        blob = repository.get_theme_blob(session, tag)
    if blob is None:
        raise FileNotFoundError(f'No theme: {tag}')
    return blob


def load_theme(tag: str) -> KDETheme:
    blob = theme_blob(tag)
    version = hashlib.sha1(blob).hexdigest()[:16]
    with _lock:
        cached = _themes.get((tag, version))
    if cached is not None:
        return cached
    theme = KDETheme.deserialize(blob)
    with _lock:
        _themes[(tag, version)] = theme
    return theme


def list_themes() -> list[dict]:
    with session_scope() as session:
        tags = repository.theme_tags(session)
    entries = []
    for tag in tags:
        try:
            theme = load_theme(tag)
        except Exception as e:
            entries.append({'tag': tag, 'name': tag, 'error': str(e)})
            continue
        entries.append({
            'tag': tag,
            'name': theme.name,
            'desc': theme.desc,
            'source': theme.source,
            'threshold': theme._log_density_threshold,
            'log_max': theme._log_density_maximum,
            'sat_penalty': theme._saturation_penalty,
            'shade_penalty': getattr(theme, '_shade_penalty', 0.0),
            'tint_penalty': getattr(theme, '_tint_penalty', 0.0),
        })
    return entries


def _cached_swatches(raw_key: str, produce) -> list[dict]:
    '''
    Memory + disk (webeditor/cache/swatches) cache around a swatch producer.
    Keys must cover the inputs' identity exactly, so any change resamples and
    stale entries are never served.
    '''
    key = hashlib.sha1(raw_key.encode()).hexdigest()[:24]

    with _lock:
        cached = _swatches.get(key)
    if cached is not None:
        return cached

    path = SWATCH_CACHE_DIR / f'{key}.json'
    result = None
    if path.exists():
        try:
            result = json.loads(path.read_text())
        except Exception:
            result = None  # corrupt cache entry: fall through and regenerate

    if result is None:
        colours = produce()
        result = [{'hex': c.hexcode, 'name': c.name} for c in colours]
        SWATCH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result))

    with _lock:
        _swatches[key] = result
    return result


def swatches_cached(kde_key: str, kde, threshold: float, log_max: float,
                    sat_penalty: float, shade_penalty: float, tint_penalty: float,
                    n: int) -> list[dict]:
    raw = (f'{kde_key}|{threshold:.4f}|{log_max:.4f}|{sat_penalty:.4f}'
           f'|{shade_penalty:.4f}|{tint_penalty:.4f}|{n}')
    return _cached_swatches(raw, lambda: sample_accepted(
        kde, threshold, log_max, sat_penalty, shade_penalty, tint_penalty, n,
    ))


def theme_kde_key(tag: str) -> str:
    '''Cache key for a saved theme's KDE: changes whenever its stored blob does.'''
    return f'theme:{tag}:{hashlib.sha1(theme_blob(tag)).hexdigest()[:16]}'


def theme_swatches(tag: str, n: int) -> list[dict]:
    theme = load_theme(tag)
    return swatches_cached(
        theme_kde_key(tag), theme._kd, theme._log_density_threshold,
        theme._log_density_maximum, theme._saturation_penalty,
        getattr(theme, '_shade_penalty', 0.0),
        getattr(theme, '_tint_penalty', 0.0), n,
    )


# ---------------------------------------------------------------------------
# theme mixes (the | operator, vectorised)

def sample_mix(tags: list[str], n: int) -> list[Colour]:
    '''
    Sample n colours from a mix of themes, batched. Mirrors CombinedTheme:
    each colour's source theme is chosen uniformly at random (a multinomial
    split, not a forced even one), then sampled from that theme alone.
    '''
    themes = [load_theme(tag) for tag in tags]
    counts = np.random.multinomial(n, [1 / len(themes)] * len(themes))

    colours: list[Colour] = []
    for theme, count in zip(themes, counts):
        colours.extend(sample_accepted(
            theme._kd, theme._log_density_threshold, theme._log_density_maximum,
            theme._saturation_penalty,
            getattr(theme, '_shade_penalty', 0.0),
            getattr(theme, '_tint_penalty', 0.0),
            int(count),
        ))
    random.shuffle(colours)
    return colours


def mix_swatches_cached(tags: list[str], n: int) -> list[dict]:
    # v2: equal probability per theme (old entries used union weighting)
    raw = 'mix:v2:' + '|'.join(sorted(theme_kde_key(tag) for tag in tags)) + f'|{n}'
    return _cached_swatches(raw, lambda: sample_mix(tags, n))


def save_theme(kde: sklearn.neighbors.KernelDensity, name: str, desc: str,
               source: str, threshold: float, sat_penalty: float,
               shade_penalty: float, tint_penalty: float) -> dict:
    tag = to_tag(name)
    if not tag:
        raise ValueError('Theme name must contain at least one letter or digit')

    grid_rgb, log_density = score_grid(kde, GRID_STEPS_SAVE)
    theme = KDETheme(
        name=name.strip(),
        desc=(desc or '').strip(),
        source=(source or '').strip() or 'generic',
        tag=tag,
        _kd=kde,
        _log_density_threshold=float(threshold),
        _log_density_maximum=penalised_max(
            log_density, grid_rgb, sat_penalty, shade_penalty, tint_penalty,
        ),
        _saturation_penalty=float(sat_penalty),
        _shade_penalty=float(shade_penalty),
        _tint_penalty=float(tint_penalty),
    )
    with session_scope() as session:
        repository.upsert_theme(session, theme)
    return {'tag': tag, 'name': theme.name}


def delete_theme(tag: str):
    with session_scope() as session:
        deleted = repository.delete_theme(session, tag)
    if not deleted:
        raise FileNotFoundError(f'No theme: {tag}')


def theme_file_bytes(tag: str) -> bytes:
    '''Serialized theme for download as a .rcmt file; raises if unknown.'''
    return theme_blob(tag)


# ---------------------------------------------------------------------------
# frame preview

def render_frame(colours: list[Colour], layout: str) -> bytes:
    # imported lazily: layers.text loads font files from a relative path at
    # import time, so this keeps the rest of the app alive if fonts are missing
    from pipeline.frames import (
        SingleFrame, HorizontalFrame, VerticalFrame,
        TwoByTwoFrame, ThreeByThreeFrame, FourByFourFrame,
        ThirdsRightFrame, ThirdsLeftFrame, ThirdsBottomFrame, ThirdsTopFrame,
        SplitRightFrame, SplitLeftFrame, SplitBottomFrame, SplitTopFrame,
    )
    layouts = {
        'single': SingleFrame(1, (1200, 1200)),
        'double-horizontal': HorizontalFrame(2, (600, 1200)),
        'double-vertical': VerticalFrame(2, (1200, 600)),
        'triple-horizontal': HorizontalFrame(3, (600, 1800)),
        'triple-vertical': VerticalFrame(3, (1800, 600)),
        'quad-horizontal': HorizontalFrame(4, (600, 2400)),
        'quad-vertical': VerticalFrame(4, (2400, 600)),
        'quad-grid': TwoByTwoFrame(4, (800, 800)),
        'nine-grid': ThreeByThreeFrame(9, (800, 800)),
        'sixteen-grid': FourByFourFrame(16, (600, 600)),
        'thirds-right': ThirdsRightFrame(2, (600, 1200)),
        'thirds-left': ThirdsLeftFrame(2, (600, 1200)),
        'thirds-bottom': ThirdsBottomFrame(2, (1200, 600)),
        'thirds-top': ThirdsTopFrame(2, (1200, 600)),
        'split-right': SplitRightFrame(3, (600, 600)),
        'split-left': SplitLeftFrame(3, (600, 600)),
        'split-bottom': SplitBottomFrame(3, (600, 600)),
        'split-top': SplitTopFrame(3, (600, 600)),
    }
    frame = layouts.get(layout)
    if frame is None:
        raise ValueError(f'Unknown layout: {layout}')
    if len(colours) != frame.count:
        raise ValueError(f'Layout {layout} needs {frame.count} colours, got {len(colours)}')

    image = frame.construct_frame(colours)
    # half resolution is indistinguishable in a preview pane and 4x smaller
    image = image.resize((image.width // 2, image.height // 2))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def layout_count(layout: str) -> int:
    return {
        'single': 1, 'double-horizontal': 2, 'double-vertical': 2,
        'triple-horizontal': 3, 'triple-vertical': 3,
        'quad-horizontal': 4, 'quad-vertical': 4, 'quad-grid': 4,
        'nine-grid': 9, 'sixteen-grid': 16,
        'thirds-right': 2, 'thirds-left': 2, 'thirds-bottom': 2, 'thirds-top': 2,
        'split-right': 3, 'split-left': 3, 'split-bottom': 3, 'split-top': 3,
    }[layout]
