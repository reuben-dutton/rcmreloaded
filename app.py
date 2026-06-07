import io

import httpx
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from PIL import Image
from skimage import color
from sklearn.neighbors import KernelDensity

st.set_page_config(page_title="Colour Density Explorer", layout="wide")
st.title("Colour Density Explorer")

with st.sidebar:
    st.header("Image source")
    source = st.radio("Source", ["Upload", "URL"])

    img_bytes = None
    if source == "Upload":
        f = st.file_uploader("Upload image", type=["jpg", "jpeg", "png", "webp"])
        if f:
            img_bytes = f.read()
    else:
        url = st.text_input("Image URL")
        if url:
            try:
                r = httpx.get(url, follow_redirects=True, timeout=10)
                r.raise_for_status()
                img_bytes = r.content
            except Exception as e:
                st.error(f"Failed to fetch image: {e}")

    st.header("Parameters")
    grid_steps    = st.slider("Grid steps",        4,      32,     16)
    bandwidth     = st.slider("Bandwidth",         1,      20,      3)
    threshold     = st.slider("Threshold",       -50,     -1,    -15)
    grey_penalty  = st.slider("Grey penalty",      0,      30,     10)
    max_fit_px    = st.slider("Max fit pixels", 1000,  50000,  20000, step=1000)

@st.cache_data(show_spinner=False)
def compute(img_bytes, bandwidth, max_fit_px, grid_steps, grey_penalty):
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
    log_density = log_density - grey_penalty * (1 - saturation)

    return grid_rgb, log_density


if img_bytes is None:
    st.info("Upload an image or provide a URL to get started.")
else:
    with st.spinner("Computing density..."):
        grid_rgb, log_density = compute(img_bytes, bandwidth, max_fit_px, grid_steps, grey_penalty)

    hi = log_density.max()
    alpha = np.clip((log_density - threshold) / (hi - threshold), 0, 1)

    mask = alpha > 0.1
    grid_rgb_vis = grid_rgb[mask]
    alpha_vis = alpha[mask]
    sizes = 2 + alpha_vis * 10
    colours = [f"rgb({r},{g},{b})" for r, g, b in grid_rgb_vis]

    fig = go.Figure(go.Scatter3d(
        x=grid_rgb_vis[:, 0],
        y=grid_rgb_vis[:, 1],
        z=grid_rgb_vis[:, 2],
        mode="markers",
        marker=dict(size=sizes, color=colours, line=dict(width=0)),
    ))

    fig.update_layout(
        scene=dict(
            xaxis_title="R", yaxis_title="G", zaxis_title="B",
            xaxis=dict(range=[0, 255]),
            yaxis=dict(range=[0, 255]),
            zaxis=dict(range=[0, 255]),
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=700,
        uirevision="stable",
    )

    st.plotly_chart(fig, use_container_width=True)
