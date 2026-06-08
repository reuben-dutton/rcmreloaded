import base64
import hashlib
import io

import httpx
import numpy as np
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html, callback, no_update
from PIL import Image
from skimage import color
from sklearn.neighbors import KernelDensity

from pipeline.themes import KDETheme, to_tag

app = Dash(__name__)


def score_grid(kde, grid_steps, saturation_penalty):
    '''
    Score a uniform RGB grid against a fitted KDE (in LAB), applying the
    saturation penalty. Returns the grid points and their (penalised) log
    densities.
    '''
    steps = np.linspace(0, 255, grid_steps, dtype=int)
    r, g, b = np.meshgrid(steps, steps, steps)
    grid_rgb = np.stack([r.ravel(), g.ravel(), b.ravel()], axis=1)
    grid_rgb_norm = grid_rgb / 255.0

    grid_lab = color.rgb2lab(grid_rgb_norm.reshape(-1, 1, 3)).reshape(-1, 3)
    log_density = kde.score_samples(grid_lab)

    saturation = color.rgb2hsv(grid_rgb_norm.reshape(-1, 1, 3)).reshape(-1, 3)[:, 1]
    log_density = log_density - saturation_penalty * (1 - saturation)

    return grid_rgb, log_density


def compute_density(img_bytes, grid_steps, bandwidth, saturation_penalty, max_fit_px):
    '''
    Fit a KDE on the image's pixels (in LAB) and score a uniform RGB grid,
    applying the saturation penalty. Returns the fitted KDE plus the grid
    points and their (penalised) log densities.
    '''
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    pixels_rgba = np.array(img).reshape(-1, 4)
    pixels_rgb = pixels_rgba[pixels_rgba[:, 3] > 0, :3] / 255.0
    pixels_lab = color.rgb2lab(pixels_rgb.reshape(-1, 1, 3)).reshape(-1, 3)

    if len(pixels_lab) > max_fit_px:
        idx = np.random.choice(len(pixels_lab), max_fit_px, replace=False)
        pixels_lab = pixels_lab[idx]

    kde = KernelDensity(kernel="gaussian", bandwidth=bandwidth, leaf_size=1000)
    kde.fit(pixels_lab)

    grid_rgb, log_density = score_grid(kde, grid_steps, saturation_penalty)
    return kde, grid_rgb, log_density


def blank_figure(text):
    '''A placeholder figure shown when nothing is loaded.'''
    return go.Figure().update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        paper_bgcolor="white",
        plot_bgcolor="white",
        annotations=[dict(text=text, showarrow=False, font=dict(size=18, color="#aaa"))],
    )


def density_figure(grid_rgb, log_density, threshold, uirevision):
    '''
    Build the 3D scatter of grid points whose density, scaled from threshold
    up to the grid maximum, clears a small visibility cutoff.
    '''
    hi = log_density.max()
    alpha = np.clip((log_density - threshold) / (hi - threshold), 0, 1)

    mask = alpha > 0.1
    grid_rgb_vis = grid_rgb[mask]
    sizes = 2 + alpha[mask] * 10
    colours = [f"rgb({r},{g},{b})" for r, g, b in grid_rgb_vis]

    fig = go.Figure(go.Scatter3d(
        x=grid_rgb_vis[:, 0],
        y=grid_rgb_vis[:, 1],
        z=grid_rgb_vis[:, 2],
        mode="markers",
        marker=dict(size=sizes, color=colours, line=dict(width=0)),
    ))

    fig.update_layout(
        uirevision=uirevision,
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            bgcolor="white",
            camera=dict(center=dict(x=0, y=0, z=-0.15)),
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="white",
    )

    return fig

app.layout = html.Div([
    html.Div([
        html.H3("Open theme"),
        dcc.Upload(
            id="theme-upload",
            children=html.Button("Open .rcmt theme", style={"width": "100%"}),
            accept=".rcmt",
        ),
        html.Div(id="theme-status", style={"marginTop": "8px", "fontSize": "12px", "color": "grey"}),

        html.H3("Image source", style={"marginTop": "24px"}),
        dcc.RadioItems(id="source", options=["Upload", "URL"], value="Upload", inline=True),
        html.Div(dcc.Upload(
            id="upload",
            children=html.Button("Choose image", style={"marginTop": "8px"}),
            accept="image/*",
        ), id="upload-wrap"),
        html.Div(dcc.Input(
            id="url-input", type="text", placeholder="https://...",
            debounce=True, style={"width": "100%", "marginTop": "8px"},
        ), id="url-wrap", style={"display": "none"}),
        html.Div(id="img-status", style={"marginTop": "8px", "fontSize": "12px", "color": "grey"}),

        html.H3("Parameters", style={"marginTop": "24px"}),
        html.Label("Grid steps"), dcc.Slider(id="grid-steps", min=4, max=32, step=1, value=16, marks=None, tooltip={"placement": "bottom"}),
        html.Label("Bandwidth"),  dcc.Slider(id="bandwidth",   min=1, max=20, step=1, value=3,  marks=None, tooltip={"placement": "bottom"}),
        html.Label("Threshold"),  dcc.Slider(id="threshold",   min=-50, max=-1, step=1, value=-15, marks=None, tooltip={"placement": "bottom"}),
        html.Label("Saturation penalty"), dcc.Slider(id="saturation-penalty", min=0, max=30, step=1, value=10, marks=None, tooltip={"placement": "bottom"}),
        html.Label("Max fit pixels"), dcc.Slider(id="max-fit-px", min=1000, max=50000, step=1000, value=20000, marks=None, tooltip={"placement": "bottom"}),

        html.H3("Save theme", style={"marginTop": "24px"}),
        dcc.Input(id="theme-name", type="text", placeholder="Theme name", style={"width": "100%"}),
        dcc.Input(id="theme-source", type="text", placeholder="Source (e.g. Arcane, or blank for generic)", style={"width": "100%", "marginTop": "8px"}),
        dcc.Textarea(id="theme-desc", placeholder="Description (optional)", style={"width": "100%", "marginTop": "8px", "height": "60px"}),
        html.Button("Save theme", id="save-btn", disabled=True, style={"marginTop": "8px", "width": "100%"}),
        html.Div(id="save-status", style={"marginTop": "8px", "fontSize": "12px", "color": "grey"}),
        dcc.Download(id="theme-download"),
    ], style={
        "width": "280px", "padding": "20px", "position": "fixed",
        "top": 0, "left": 0, "height": "100vh", "overflowY": "auto",
        "boxSizing": "border-box", "background": "#f8f8f8", "borderRight": "1px solid #ddd",
    }),

    html.Div(
        dcc.Graph(id="plot", style={"height": "100vh"}, config={"scrollZoom": True},
                  figure=blank_figure("No image or theme selected")),
        style={"marginLeft": "280px"},
    ),

    dcc.Store(id="img-store"),
    dcc.Store(id="theme-store"),
])


@callback(
    Output("upload-wrap", "style"),
    Output("url-wrap", "style"),
    Input("source", "value"),
)
def toggle_source(source):
    show = {"display": "block"}
    hide = {"display": "none"}
    return (show, hide) if source == "Upload" else (hide, show)


@callback(
    Output("img-store", "data"),
    Output("img-status", "children"),
    Output("theme-store", "data", allow_duplicate=True),
    Input("upload", "contents"),
    Input("url-input", "value"),
    State("source", "value"),
    prevent_initial_call=True,
)
def load_image(contents, url, source):
    if source == "Upload":
        if not contents:
            return None, "", no_update
        _, b64 = contents.split(",", 1)
        img_bytes = base64.b64decode(b64)
    else:
        if not url:
            return None, "", no_update
        try:
            r = httpx.get(url, follow_redirects=True, timeout=10)
            r.raise_for_status()
            img_bytes = r.content
        except Exception as e:
            return None, f"Error: {e}", no_update

    encoded = base64.b64encode(img_bytes).decode()
    img = Image.open(io.BytesIO(img_bytes))
    # Clear any opened theme so the image drives the view.
    return encoded, f"Loaded {img.width}×{img.height}", None


@callback(
    Output("plot", "figure"),
    Input("img-store", "data"),
    Input("grid-steps", "value"),
    Input("bandwidth", "value"),
    Input("threshold", "value"),
    Input("saturation-penalty", "value"),
    Input("max-fit-px", "value"),
    prevent_initial_call=True,
)
def update_plot(img_b64, grid_steps, bandwidth, threshold, saturation_penalty, max_fit_px):
    # Leave the current figure untouched (e.g. a loaded theme) when there's no image.
    if not img_b64:
        return no_update

    img_bytes = base64.b64decode(img_b64)
    img_hash = hashlib.md5(img_bytes).hexdigest()

    _, grid_rgb, log_density = compute_density(
        img_bytes, grid_steps, bandwidth, saturation_penalty, max_fit_px
    )

    return density_figure(grid_rgb, log_density, threshold, img_hash)


@callback(
    Output("theme-store", "data"),
    Output("img-store", "data", allow_duplicate=True),
    Output("img-status", "children", allow_duplicate=True),
    Output("theme-name", "value"),
    Output("theme-source", "value"),
    Output("theme-desc", "value"),
    Output("threshold", "value"),
    Output("saturation-penalty", "value"),
    Output("theme-status", "children"),
    Input("theme-upload", "contents"),
    prevent_initial_call=True,
)
def load_theme(contents):
    '''
    Deserialise an uploaded .rcmt theme into the theme store and sync the
    name/source/description fields and the threshold + saturation sliders to its
    saved values. The actual render is handled by render_theme, so dragging those
    sliders re-scores the theme live.
    '''
    if not contents:
        return (no_update,) * 8 + ("",)

    _, b64 = contents.split(",", 1)
    try:
        theme = KDETheme.deserialize(base64.b64decode(b64))
    except Exception as e:
        return (no_update,) * 8 + (f"Could not read theme: {e}",)

    # 'generic' is the implicit default, so leave the box blank for it.
    source = "" if theme.source == "generic" else theme.source

    # Store the theme, clear any loaded image, and seed the sliders so the
    # initial render matches how the theme was saved.
    return (
        b64,
        None,
        "",
        theme.name,
        source,
        theme.desc,
        theme._log_density_threshold,
        theme._saturation_penalty,
        f"Loaded theme “{theme.name}”. Adjust the sliders, then Save theme.",
    )


@callback(
    Output("plot", "figure", allow_duplicate=True),
    Input("theme-store", "data"),
    Input("grid-steps", "value"),
    Input("threshold", "value"),
    Input("saturation-penalty", "value"),
    prevent_initial_call=True,
)
def render_theme(theme_b64, grid_steps, threshold, saturation_penalty):
    '''
    Re-score the opened theme's stored KDE against the RGB grid with the current
    threshold and saturation penalty. No refit needed - the penalty is applied
    at scoring time - so lowering it simply expands the accepted region.
    '''
    if not theme_b64:
        return no_update

    theme = KDETheme.deserialize(base64.b64decode(theme_b64))
    grid_rgb, log_density = score_grid(theme._kd, grid_steps, saturation_penalty)
    return density_figure(grid_rgb, log_density, threshold, f"theme-{theme.name}")


@callback(
    Output("save-btn", "disabled"),
    Input("img-store", "data"),
    Input("theme-store", "data"),
    Input("theme-name", "value"),
)
def toggle_save(img_b64, theme_b64, name):
    return not ((img_b64 or theme_b64) and name and name.strip())


@callback(
    Output("theme-download", "data"),
    Output("save-status", "children"),
    Input("save-btn", "n_clicks"),
    State("img-store", "data"),
    State("theme-store", "data"),
    State("theme-name", "value"),
    State("theme-source", "value"),
    State("theme-desc", "value"),
    State("grid-steps", "value"),
    State("bandwidth", "value"),
    State("threshold", "value"),
    State("saturation-penalty", "value"),
    State("max-fit-px", "value"),
    prevent_initial_call=True,
)
def save_theme(n_clicks, img_b64, theme_b64, name, source, desc, grid_steps, bandwidth, threshold, saturation_penalty, max_fit_px):
    if not (name and name.strip()):
        return no_update, "Provide a name first."

    # Use the image's pixels when one is loaded, otherwise re-score the opened
    # theme's existing KDE (only the threshold / saturation penalty change).
    if img_b64:
        kde, _, log_density = compute_density(
            base64.b64decode(img_b64), grid_steps, bandwidth, saturation_penalty, max_fit_px
        )
    elif theme_b64:
        kde = KDETheme.deserialize(base64.b64decode(theme_b64))._kd
        _, log_density = score_grid(kde, grid_steps, saturation_penalty)
    else:
        return no_update, "Open an image or theme first."

    name = name.strip()
    tag = to_tag(name)
    theme = KDETheme(
        name=name,
        desc=(desc or "").strip(),
        source=(source or "").strip() or "generic",
        tag=tag,
        _kd=kde,
        _log_density_threshold=float(threshold),
        _log_density_maximum=float(log_density.max()),
        _saturation_penalty=float(saturation_penalty),
    )

    return dcc.send_bytes(theme.serialize(), f"{tag}.rcmt"), f"Saved “{theme.name}” ({tag}.rcmt)."


if __name__ == "__main__":
    app.run(debug=True)
