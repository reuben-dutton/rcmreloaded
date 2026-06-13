/*
 * RCM Theme Studio frontend.
 *
 * Performance model: the server ships the scored colour grid once per fit as
 * a binary ArrayBuffer (rgb bytes + raw float32 log-densities). The threshold
 * and saturation-penalty sliders are uniforms evaluated in the vertex shader,
 * so reshaping the theme is pure GPU work - no network, no re-layout.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const $ = (id) => document.getElementById(id);

/* ── state ─────────────────────────────────────────── */

const state = {
  fitKey: null,      // set when a fitted image is driving the editor
  tag: null,         // set when editing an existing theme's KDE
  originalTag: null, // file to replace on save (rename handling)
  imageId: null,
  grid: null,        // { meta, logd: Float32Array, rgb: Uint8Array, sat: Float32Array }
  logMax: 0,
};

/* ── toast ─────────────────────────────────────────── */

let toastTimer = null;
function toast(msg, isError = false) {
  const el = $('toast');
  el.textContent = msg;
  el.classList.toggle('err', isError);
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2600);
}

const debounce = (fn, ms) => {
  let t = null;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
};

/* ── three.js viewer ───────────────────────────────── */

const canvas = $('viewer');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0e1116);

const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 20);
camera.position.set(1.15, 0.75, 1.15);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.8;
canvas.addEventListener('pointerdown', () => { controls.autoRotate = false; }, { once: true });

// faint cube outline so the colour space has a reference frame
scene.add(new THREE.LineSegments(
  new THREE.EdgesGeometry(new THREE.BoxGeometry(1, 1, 1)),
  new THREE.LineBasicMaterial({ color: 0x232c3a }),
));

const uniforms = {
  uThreshold: { value: -15 },
  uPenalty: { value: 0 },
  uShade: { value: 0 },
  uTint: { value: 0 },
  uLogMax: { value: 0 },
  uSize: { value: 1 },
};

const material = new THREE.ShaderMaterial({
  uniforms,
  vertexShader: /* glsl */`
    attribute vec3 aColor;
    attribute float aLogd;
    uniform float uThreshold, uPenalty, uShade, uTint, uLogMax, uSize;
    varying vec3 vColor;
    varying float vAlpha;
    void main() {
      vColor = aColor;
      float mx = max(aColor.r, max(aColor.g, aColor.b));
      float mn = min(aColor.r, min(aColor.g, aColor.b));
      float sat = mx > 0.0 ? (mx - mn) / mx : 0.0;
      float pld = aLogd - uPenalty * (1.0 - sat) - uShade * (1.0 - mx) - uTint * mn;
      float a = clamp((pld - uThreshold) / max(uLogMax - uThreshold, 1e-3), 0.0, 1.0);
      vAlpha = a;
      vec4 mv = modelViewMatrix * vec4(position, 1.0);
      gl_PointSize = a < 0.1 ? 0.0 : (1.5 + a * 9.0) * uSize / -mv.z;
      gl_Position = projectionMatrix * mv;
    }`,
  fragmentShader: /* glsl */`
    varying vec3 vColor;
    varying float vAlpha;
    void main() {
      if (vAlpha < 0.1) discard;
      vec2 d = gl_PointCoord - 0.5;
      if (dot(d, d) > 0.25) discard;
      gl_FragColor = vec4(vColor, 1.0);
    }`,
});

let points = null;

function resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  uniforms.uSize.value = (h / 480) * Math.min(window.devicePixelRatio, 2);
}

new ResizeObserver(resize).observe(canvas);

renderer.setAnimationLoop(() => {
  controls.update();
  renderer.render(scene, camera);
});

/* ── binary grid handling ──────────────────────────── */

function parseGrid(buffer) {
  const view = new DataView(buffer);
  const jsonLen = view.getUint32(0, true);
  const meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 4, jsonLen)));
  const logd = new Float32Array(buffer, 4 + jsonLen, meta.count);
  const rgb = new Uint8Array(buffer, 4 + jsonLen + meta.count * 4, meta.count * 3);
  return { meta, logd, rgb };
}

function setGrid(grid) {
  const n = grid.meta.count;
  const positions = new Float32Array(n * 3);
  const colors = new Float32Array(n * 3);
  const sat = new Float32Array(n);
  const mxs = new Float32Array(n);
  const mns = new Float32Array(n);

  for (let i = 0; i < n; i++) {
    const r = grid.rgb[i * 3] / 255, g = grid.rgb[i * 3 + 1] / 255, b = grid.rgb[i * 3 + 2] / 255;
    positions[i * 3] = r - 0.5;
    positions[i * 3 + 1] = g - 0.5;
    positions[i * 3 + 2] = b - 0.5;
    colors[i * 3] = r; colors[i * 3 + 1] = g; colors[i * 3 + 2] = b;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
    sat[i] = mx > 0 ? (mx - mn) / mx : 0;
    mxs[i] = mx;
    mns[i] = mn;
  }
  grid.sat = sat;
  grid.mx = mxs;
  grid.mn = mns;

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('aColor', new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute('aLogd', new THREE.BufferAttribute(grid.logd, 1));

  if (points) {
    points.geometry.dispose();
    points.geometry = geometry;
  } else {
    points = new THREE.Points(geometry, material);
    scene.add(points);
  }

  state.grid = grid;
  $('viewer-hint').classList.add('hidden');
  updateShape();
}

// the alpha scale ceiling depends on the penalties, so recompute it client-side
function penalisedMax(grid, penalty, shade, tint) {
  let max = -Infinity;
  for (let i = 0; i < grid.logd.length; i++) {
    const v = grid.logd[i]
      - penalty * (1 - grid.sat[i])
      - shade * (1 - grid.mx[i])
      - tint * grid.mn[i];
    if (v > max) max = v;
  }
  return max;
}

function updateShape() {
  if (!state.grid) return;
  const threshold = parseFloat($('threshold').value);
  const penalty = parseFloat($('penalty').value);
  const shade = parseFloat($('shade').value);
  const tint = parseFloat($('tint').value);
  state.logMax = penalisedMax(state.grid, penalty, shade, tint);
  uniforms.uThreshold.value = threshold;
  uniforms.uPenalty.value = penalty;
  uniforms.uShade.value = shade;
  uniforms.uTint.value = tint;
  uniforms.uLogMax.value = state.logMax;
  refreshSwatchesSoon();
}

/* ── api helpers ───────────────────────────────────── */

async function api(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch { /* not json */ }
    throw new Error(detail);
  }
  return res;
}

function previewBody(extra = {}) {
  return JSON.stringify({
    fit_key: state.fitKey,
    tag: state.fitKey ? null : state.tag,
    threshold: parseFloat($('threshold').value),
    log_max: state.logMax,
    sat_penalty: parseFloat($('penalty').value),
    shade_penalty: parseFloat($('shade').value),
    tint_penalty: parseFloat($('tint').value),
    ...extra,
  });
}

/* ── editor: image upload + fitting ────────────────── */

async function attachImage(file) {
  $('image-status').textContent = 'Uploading…';
  try {
    const form = new FormData();
    form.append('file', file);
    const res = await api('/api/images', { method: 'POST', body: form });
    state.imageId = (await res.json()).image_id;
    $('image-status').textContent = `${file.name} — fitting…`;
    for (const id of ['bandwidth', 'steps', 'maxpx']) $(id).disabled = false;
    await refit();
    $('image-status').textContent = file.name;
  } catch (e) {
    $('image-status').textContent = '';
    toast(`Image failed: ${e.message}`, true);
  }
}

let fitToken = 0;
async function refit() {
  if (!state.imageId) return;
  const token = ++fitToken;
  const params = new URLSearchParams({
    image_id: state.imageId,
    bandwidth: $('bandwidth').value,
    max_fit_px: $('maxpx').value,
    steps: $('steps').value,
  });
  try {
    const res = await api(`/api/fit/grid?${params}`);
    const grid = parseGrid(await res.arrayBuffer());
    if (token !== fitToken) return; // a newer fit superseded this one
    state.fitKey = grid.meta.fit_key;
    setGrid(grid);
    updateSaveEnabled();
  } catch (e) {
    toast(`Fit failed: ${e.message}`, true);
  }
}

const refitSoon = debounce(refit, 350);

async function regrid() {
  // resolution change for an existing theme being edited without an image
  if (state.fitKey) return refitSoon();
  if (!state.tag) return;
  try {
    const res = await api(`/api/themes/${state.tag}/grid?steps=${$('steps').value}`);
    setGrid(parseGrid(await res.arrayBuffer()));
  } catch (e) {
    toast(e.message, true);
  }
}

/* ── editor: previews ──────────────────────────────── */

async function refreshSwatches() {
  if (!state.fitKey && !state.tag) return;
  try {
    const res = await api('/api/preview/swatches', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: previewBody({ n: 6 }),
    });
    const colours = await res.json();
    const list = $('swatch-list');
    list.innerHTML = '';
    for (const c of colours) {
      const row = document.createElement('div');
      row.className = 'swatch-row';
      row.title = 'Click to copy hex';
      row.innerHTML = `
        <div class="chip" style="background:${c.hex}"></div>
        <div class="meta"><div class="name"></div><div class="hex"></div></div>`;
      row.querySelector('.name').textContent = c.name;
      row.querySelector('.hex').textContent = c.hex;
      row.addEventListener('click', () => {
        navigator.clipboard.writeText(c.hex);
        toast(`Copied ${c.hex}`);
      });
      list.appendChild(row);
    }
    if (!colours.length) {
      list.innerHTML = '<div class="status">Region too small to sample — raise the threshold.</div>';
    }
  } catch (e) {
    toast(`Swatches failed: ${e.message}`, true);
  }
}

const refreshSwatchesSoon = debounce(refreshSwatches, 450);

function renderGridCells(holder, colours) {
  holder.innerHTML = '';
  for (const c of colours) {
    const cell = document.createElement('div');
    cell.className = 'cell';
    cell.style.background = c.hex;
    cell.title = `${c.name} ${c.hex} — click to copy`;
    cell.addEventListener('click', () => {
      navigator.clipboard.writeText(c.hex);
      toast(`Copied ${c.hex}`);
    });
    holder.appendChild(cell);
  }
}

$('grid-sample-btn').addEventListener('click', async () => {
  if (!state.fitKey && !state.tag) return toast('Load an image or theme first', true);
  const btn = $('grid-sample-btn');
  btn.disabled = true;
  btn.textContent = 'Sampling…';
  try {
    const res = await api('/api/preview/swatches', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: previewBody({ n: 100 }),
    });
    const colours = await res.json();
    renderGridCells($('grid-sample'), colours);
    if (colours.length < 100) {
      toast(`Only ${colours.length} colours accepted — region may be small`, true);
    }
  } catch (e) {
    toast(`Sample failed: ${e.message}`, true);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sample 10 × 10';
  }
});

$('frame-btn').addEventListener('click', async () => {
  if (!state.fitKey && !state.tag) return toast('Load an image or theme first', true);
  const btn = $('frame-btn');
  btn.disabled = true;
  btn.textContent = 'Generating…';
  try {
    const res = await api('/api/preview/frame', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: previewBody({ layout: $('layout-select').value }),
    });
    const url = URL.createObjectURL(await res.blob());
    const holder = $('frame-preview');
    const old = holder.querySelector('img');
    if (old) URL.revokeObjectURL(old.src);
    holder.innerHTML = '';
    const img = document.createElement('img');
    img.src = url;
    holder.appendChild(img);
  } catch (e) {
    toast(`Preview failed: ${e.message}`, true);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate preview';
  }
});

/* ── editor: saving ────────────────────────────────── */

function updateSaveEnabled() {
  const ready = (state.fitKey || state.tag) && $('theme-name').value.trim();
  $('save-btn').disabled = !ready;
}

$('save-btn').addEventListener('click', async () => {
  try {
    const res = await api('/api/themes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fit_key: state.fitKey,
        tag: state.fitKey ? null : state.tag,
        name: $('theme-name').value.trim(),
        desc: $('theme-desc').value,
        source: $('theme-source').value,
        threshold: parseFloat($('threshold').value),
        sat_penalty: parseFloat($('penalty').value),
        shade_penalty: parseFloat($('shade').value),
        tint_penalty: parseFloat($('tint').value),
        previous_tag: state.originalTag,
      }),
    });
    const saved = await res.json();
    state.originalTag = saved.tag;
    if (!state.fitKey) state.tag = saved.tag;
    $('save-status').textContent = `Saved as ${saved.tag}.rcmt`;
    setBanner(`Editing “${saved.name}”`);
    toast(`Saved “${saved.name}” to the library`);
    libraryStale = true;
  } catch (e) {
    toast(`Save failed: ${e.message}`, true);
  }
});

/* ── editor: opening / resetting ───────────────────── */

function setBanner(text) {
  const banner = $('editing-banner');
  banner.textContent = text || '';
  banner.classList.toggle('hidden', !text);
}

function resetEditor() {
  Object.assign(state, { fitKey: null, tag: null, originalTag: null, imageId: null, grid: null });
  if (points) { scene.remove(points); points.geometry.dispose(); points = null; }
  $('viewer-hint').classList.remove('hidden');
  setBanner('');
  $('image-status').textContent = '';
  $('save-status').textContent = '';
  $('swatch-list').innerHTML = '';
  $('grid-sample').innerHTML = '';
  $('frame-preview').innerHTML = '';
  for (const [id, value] of [['theme-name', ''], ['theme-source', ''], ['theme-desc', '']]) $(id).value = value;
  for (const [id, value] of [['threshold', -15], ['penalty', 0], ['shade', 0], ['tint', 0], ['bandwidth', 3], ['steps', 20], ['maxpx', 20000]]) {
    $(id).value = value;
    $(`${id}-out`).textContent = value;
  }
  for (const id of ['bandwidth', 'steps', 'maxpx']) $(id).disabled = true;
  updateSaveEnabled();
}

async function openTheme(tag) {
  showView('editor');
  resetEditor();
  setBanner('Loading…');
  try {
    const res = await api(`/api/themes/${tag}/grid?steps=${$('steps').value}`);
    const grid = parseGrid(await res.arrayBuffer());
    const m = grid.meta;
    state.tag = tag;
    state.originalTag = tag;
    $('theme-name').value = m.name;
    $('theme-source').value = m.source === 'generic' ? '' : m.source;
    $('theme-desc').value = m.desc;
    $('threshold').value = Math.max(-50, Math.min(-1, m.threshold));
    $('penalty').value = Math.max(0, Math.min(30, m.sat_penalty));
    $('shade').value = Math.max(0, Math.min(30, m.shade_penalty || 0));
    $('tint').value = Math.max(0, Math.min(30, m.tint_penalty || 0));
    for (const id of ['threshold', 'penalty', 'shade', 'tint']) {
      $(`${id}-out`).textContent = $(id).value;
    }
    $('steps').disabled = false; // regridding works without a source image
    setBanner(`Editing “${m.name}”`);
    setGrid(grid);
    updateSaveEnabled();
  } catch (e) {
    setBanner('');
    toast(`Could not open theme: ${e.message}`, true);
  }
}

/* ── trigram search ────────────────────────────────── */

// pg_trgm-style trigrams: each word padded with two leading spaces and one
// trailing, so short words and word starts still produce useful grams
function trigrams(text) {
  const grams = new Set();
  const words = text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim().split(' ');
  for (const word of words) {
    if (!word) continue;
    const padded = `  ${word} `;
    for (let i = 0; i + 3 <= padded.length; i++) grams.add(padded.slice(i, i + 3));
  }
  return grams;
}

function trigramSimilarity(a, b) {
  if (!a.size || !b.size) return 0;
  let shared = 0;
  for (const gram of a) if (b.has(gram)) shared++;
  return shared / (a.size + b.size - shared); // Jaccard
}

let libraryIndex = []; // { card, nameGrams, metaGrams, position }

function applySearch() {
  const query = $('theme-search').value.trim();
  const grid = $('library-grid');

  if (!query) {
    // restore the original alphabetical order and show everything
    for (const entry of [...libraryIndex].sort((x, y) => x.position - y.position)) {
      entry.card.classList.remove('hidden');
      grid.appendChild(entry.card);
    }
    $('search-empty').classList.add('hidden');
    return;
  }

  const queryGrams = trigrams(query);
  const scored = libraryIndex.map((entry) => ({
    entry,
    // name matches dominate, desc/source break ties
    score: trigramSimilarity(queryGrams, entry.nameGrams)
      + 0.3 * trigramSimilarity(queryGrams, entry.metaGrams),
  }));
  scored.sort((x, y) => y.score - x.score);

  let shown = 0;
  for (const { entry, score } of scored) {
    const visible = score >= 0.08;
    entry.card.classList.toggle('hidden', !visible);
    if (visible) {
      grid.appendChild(entry.card); // append order = rank order
      shown++;
    }
  }
  $('search-empty').classList.toggle('hidden', shown > 0);
}

$('theme-search').addEventListener('input', applySearch);

/* ── library ───────────────────────────────────────── */

let libraryStale = true;

const swatchObserver = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    if (!entry.isIntersecting) continue;
    swatchObserver.unobserve(entry.target);
    loadStrip(entry.target);
  }
}, { rootMargin: '200px' });

async function loadStrip(strip) {
  try {
    const res = await api(`/api/themes/${strip.dataset.tag}/swatches?n=6`);
    const colours = await res.json();
    strip.classList.remove('loading');
    strip.innerHTML = '';
    for (const c of colours) {
      const sw = document.createElement('div');
      sw.className = 'sw';
      sw.style.background = c.hex;
      sw.dataset.label = c.hex;
      strip.appendChild(sw);
    }
  } catch {
    strip.classList.remove('loading');
  }
}

async function loadLibrary() {
  let themes;
  try {
    themes = await (await api('/api/themes')).json();
  } catch (e) {
    return toast(`Could not load library: ${e.message}`, true);
  }
  libraryStale = false;

  const grid = $('library-grid');
  grid.innerHTML = '';
  libraryIndex = [];
  $('library-empty').classList.toggle('hidden', themes.length > 0);

  for (const t of themes) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <h4></h4>
      <p class="desc"></p>
      <div class="strip loading" data-tag="${t.tag}"></div>
      <div class="actions">
        <button class="edit" title="Edit" aria-label="Edit">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>
        </button>
        <button class="download" title="Download" aria-label="Download">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        </button>
        <button class="danger" title="Delete" aria-label="Delete">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </div>`;
    const h4 = card.querySelector('h4');
    h4.textContent = t.name;
    if (t.source && t.source !== 'generic') {
      const badge = document.createElement('span');
      badge.className = 'source';
      badge.textContent = t.source;
      h4.appendChild(badge);
    }
    card.querySelector('.desc').textContent = t.error ? `⚠ ${t.error}` : (t.desc || '');
    card.querySelector('.edit').addEventListener('click', () => openTheme(t.tag));
    card.querySelector('.download').addEventListener('click', () => {
      window.location = `/api/themes/${t.tag}/file`;
    });
    card.querySelector('.danger').addEventListener('click', async () => {
      if (!confirm(`Delete theme “${t.name}”? This removes ${t.tag}.rcmt from disk.`)) return;
      try {
        await api(`/api/themes/${t.tag}`, { method: 'DELETE' });
        toast(`Deleted “${t.name}”`);
        loadLibrary();
      } catch (e) {
        toast(`Delete failed: ${e.message}`, true);
      }
    });
    grid.appendChild(card);
    swatchObserver.observe(card.querySelector('.strip'));
    libraryIndex.push({
      card,
      nameGrams: trigrams(`${t.name} ${t.tag}`),
      metaGrams: trigrams(`${t.source || ''} ${t.desc || ''}`),
      position: libraryIndex.length,
    });
  }
  applySearch(); // keep an active query filtering across reloads
}

/* ── mixer ─────────────────────────────────────────── */

const mixSelected = new Set();
const mixNames = new Map();

async function loadMixList() {
  let themes;
  try {
    themes = await (await api('/api/themes')).json();
  } catch (e) {
    return toast(`Could not load themes: ${e.message}`, true);
  }
  const known = new Set(themes.map((t) => t.tag));
  for (const tag of mixSelected) if (!known.has(tag)) mixSelected.delete(tag);

  mixNames.clear();
  const list = $('mix-list');
  list.innerHTML = '';
  for (const t of themes) {
    mixNames.set(t.tag, t.name);
    const btn = document.createElement('button');
    btn.className = 'mix-item' + (mixSelected.has(t.tag) ? ' selected' : '');
    btn.textContent = t.name;
    btn.addEventListener('click', () => {
      if (mixSelected.has(t.tag)) mixSelected.delete(t.tag);
      else mixSelected.add(t.tag);
      btn.classList.toggle('selected');
      updateMixTitle();
      mixSampleSoon();
    });
    list.appendChild(btn);
  }
  updateMixTitle();
}

function updateMixTitle() {
  const names = [...mixSelected].map((tag) => mixNames.get(tag) || tag);
  $('mix-title').textContent = names.length
    ? names.join(' + ')
    : 'Select themes to mix';
}

async function mixSample() {
  const grid = $('mix-grid');
  const status = $('mix-grid-status');
  if (!mixSelected.size) {
    grid.innerHTML = '';
    status.textContent = '';
    return;
  }
  status.textContent = 'Sampling…';
  try {
    const res = await api('/api/mix/swatches', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tags: [...mixSelected], n: 100 }),
    });
    const colours = await res.json();
    renderGridCells(grid, colours);
    status.textContent = colours.length < 100
      ? `Only ${colours.length} colours accepted — mixed region may be small`
      : '';
  } catch (e) {
    status.textContent = '';
    toast(`Mix sample failed: ${e.message}`, true);
  }
}

const mixSampleSoon = debounce(mixSample, 400);

$('mix-frame-btn').addEventListener('click', async () => {
  if (!mixSelected.size) return toast('Select at least one theme', true);
  const btn = $('mix-frame-btn');
  btn.disabled = true;
  btn.textContent = 'Generating…';
  try {
    const res = await api('/api/mix/frame', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tags: [...mixSelected], layout: $('mix-layout').value }),
    });
    const url = URL.createObjectURL(await res.blob());
    const holder = $('mix-frame');
    const old = holder.querySelector('img');
    if (old) URL.revokeObjectURL(old.src);
    holder.innerHTML = '';
    const img = document.createElement('img');
    img.src = url;
    holder.appendChild(img);
  } catch (e) {
    toast(`Preview failed: ${e.message}`, true);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate preview';
  }
});

/* ── navigation + input wiring ─────────────────────── */

function showView(view) {
  for (const name of ['library', 'editor', 'mixer']) {
    $(`${name}-view`).classList.toggle('hidden', view !== name);
    $(`nav-${name}`).classList.toggle('active', view === name);
  }
  if (view === 'library' && libraryStale) loadLibrary();
  if (view === 'editor') resize();
  if (view === 'mixer') loadMixList();
}

$('nav-library').addEventListener('click', () => showView('library'));
$('nav-editor').addEventListener('click', () => showView('editor'));
$('nav-mixer').addEventListener('click', () => showView('mixer'));
$('new-theme-btn').addEventListener('click', () => { showView('editor'); resetEditor(); });

// sliders: live readouts, then route to GPU update or server refit
for (const id of ['threshold', 'penalty', 'shade', 'tint', 'bandwidth', 'steps', 'maxpx']) {
  $(id).addEventListener('input', () => { $(`${id}-out`).textContent = $(id).value; });
}
for (const id of ['threshold', 'penalty', 'shade', 'tint']) {
  $(id).addEventListener('input', updateShape);
}
$('bandwidth').addEventListener('input', refitSoon);
$('maxpx').addEventListener('input', refitSoon);
$('steps').addEventListener('input', debounce(regrid, 350));
$('theme-name').addEventListener('input', updateSaveEnabled);

// dropzone
const dropzone = $('dropzone');
$('file-input').addEventListener('change', (e) => {
  if (e.target.files[0]) attachImage(e.target.files[0]);
});
for (const evt of ['dragover', 'dragleave', 'drop']) {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.toggle('drag', evt === 'dragover');
    if (evt === 'drop' && e.dataTransfer.files[0]) attachImage(e.dataTransfer.files[0]);
  });
}

/* ── boot ──────────────────────────────────────────── */

resetEditor();
loadLibrary();
showView('library');
