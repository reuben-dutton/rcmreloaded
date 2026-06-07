import base64
import hashlib
import io
import re

import httpx
import numpy as np
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html, callback, no_update
from PIL import Image
from skimage import color
from sklearn.neighbors import KernelDensity

from models.themes import KDETheme

app = Dash(__name__)


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

    steps = np.linspace(0, 255, grid_steps, dtype=int)
    r, g, b = np.meshgrid(steps, steps, steps)
    grid_rgb = np.stack([r.ravel(), g.ravel(), b.ravel()], axis=1)
    grid_rgb_norm = grid_rgb / 255.0

    grid_lab = color.rgb2lab(grid_rgb_norm.reshape(-1, 1, 3)).reshape(-1, 3)
    log_density = kde.score_samples(grid_lab)

    grid_hsv = color.rgb2hsv(grid_rgb_norm.reshape(-1, 1, 3)).reshape(-1, 3)
    saturation = grid_hsv[:, 1]
    log_density = log_density - saturation_penalty * (1 - saturation)

    return kde, grid_rgb, log_density

app.layout = html.Div([
    html.Div([
        html.H3("Image source"),
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
        html.Button("Save theme", id="save-btn", disabled=True, style={"marginTop": "8px", "width": "100%"}),
        html.Div(id="save-status", style={"marginTop": "8px", "fontSize": "12px", "color": "grey"}),
        dcc.Download(id="theme-download"),
    ], style={
        "width": "280px", "padding": "20px", "position": "fixed",
        "top": 0, "left": 0, "height": "100vh", "overflowY": "auto",
        "boxSizing": "border-box", "background": "#f8f8f8", "borderRight": "1px solid #ddd",
    }),

    html.Div(
        dcc.Graph(id="plot", style={"height": "100vh"}, config={"scrollZoom": True}, figure=go.Figure().update_layout(
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            paper_bgcolor="white", plot_bgcolor="white",
            annotations=[dict(text="No image selected", showarrow=False, font=dict(size=18, color="#aaa"))],
        )),
        style={"marginLeft": "280px"},
    ),

    dcc.Store(id="img-store"),
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
    Input("upload", "contents"),
    Input("url-input", "value"),
    State("source", "value"),
    prevent_initial_call=True,
)
def load_image(contents, url, source):
    if source == "Upload":
        if not contents:
            return None, ""
        _, b64 = contents.split(",", 1)
        img_bytes = base64.b64decode(b64)
    else:
        if not url:
            return None, ""
        try:
            r = httpx.get(url, follow_redirects=True, timeout=10)
            r.raise_for_status()
            img_bytes = r.content
        except Exception as e:
            return None, f"Error: {e}"

    encoded = base64.b64encode(img_bytes).decode()
    img = Image.open(io.BytesIO(img_bytes))
    return encoded, f"Loaded {img.width}×{img.height}"


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
    if not img_b64:
        return go.Figure().update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            paper_bgcolor="white",
            plot_bgcolor="white",
            annotations=[dict(text="No image selected", showarrow=False, font=dict(size=18, color="#aaa"))],
        )

    img_bytes = base64.b64decode(img_b64)
    img_hash = hashlib.md5(img_bytes).hexdigest()

    _, grid_rgb, log_density = compute_density(
        img_bytes, grid_steps, bandwidth, saturation_penalty, max_fit_px
    )

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
        uirevision=img_hash,
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


@callback(
    Output("save-btn", "disabled"),
    Input("img-store", "data"),
    Input("theme-name", "value"),
)
def toggle_save(img_b64, name):
    return not (img_b64 and name and name.strip())


@callback(
    Output("theme-download", "data"),
    Output("save-status", "children"),
    Input("save-btn", "n_clicks"),
    State("img-store", "data"),
    State("theme-name", "value"),
    State("grid-steps", "value"),
    State("bandwidth", "value"),
    State("threshold", "value"),
    State("saturation-penalty", "value"),
    State("max-fit-px", "value"),
    prevent_initial_call=True,
)
def save_theme(n_clicks, img_b64, name, grid_steps, bandwidth, threshold, saturation_penalty, max_fit_px):
    if not (img_b64 and name and name.strip()):
        return no_update, "Provide an image and a name first."

    img_bytes = base64.b64decode(img_b64)
    kde, _, log_density = compute_density(
        img_bytes, grid_steps, bandwidth, saturation_penalty, max_fit_px
    )

    theme = KDETheme(
        name=name.strip(),
        _kd=kde,
        _log_density_threshold=float(threshold),
        _log_density_maximum=float(log_density.max()),
        _saturation_penalty=float(saturation_penalty),
    )

    filename = re.sub(r"[^\w\-]+", "_", name.strip()) + ".rcmt"
    return dcc.send_bytes(theme.serialize(), filename), f"Saved “{theme.name}”."


if __name__ == "__main__":
    app.run(debug=True)
