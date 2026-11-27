# ADR-001: Interactive Mandelbrot and Julia Explorer — Dash + Plotly with a Vectorized NumPy Engine

## Status

Accepted

## Date

2026-11-25

## Deciders

Project owner

## Context

The goal is an interactive web application for exploring the Mandelbrot set, selected
Julia sets, and generalized powers (`z_{k+1} = z_k^n + c`), with user-adjustable:

- fractal mode (Mandelbrot or a named Julia set),
- color palette,
- iteration depth,
- fractal power `n`,
- zoom level and viewport center (Real/Imaginary).

Constraints and considerations that shaped the design (as reflected in `plotlyv2.py`):

1. **Pure-Python stack.** The project lives in a Python workspace; the developer wants to
   author the UI without a JavaScript framework. Dash (callback-based, built on Plotly)
   satisfies this: layout, controls, and callbacks are all Python.
2. **Performance.** A naive per-pixel Python loop (700,000 pixels × up to 500 iterations)
   is too slow to feel interactive. The computation must be vectorized.
3. **Correct aspect ratio.** The complex plane is isotropic: one unit of Re must equal one
   unit of Im on screen, otherwise the fractal is visibly distorted.
4. **Generalized powers.** The engine must support arbitrary integer powers `n`, not just
   the classical `n = 2`.
5. **Local development reliability.** Repeatedly starting the dev server leaves zombie
   processes holding port 8050, causing "address already in use" failures on restart.
6. **Deterministic navigation.** The viewport is driven by explicit numeric controls
   and by Plotly click coordinates. A view is fully described by (zoom, cx, cy) and
   can be reproduced exactly.

## Decision

### 1. Stack: Dash + Plotly Heatmap, single-page layout

- The app is a single Dash application (`plotlyv2.py`) with a left/right flex layout:
  `dcc.Graph` (heatmap, `flex: 1`) on the left, a fixed 300 px controls sidebar on the
  right.
- The figure is a single `go.Heatmap` whose `z` values are the escape-time iteration
  counts, colored by a user-selected Plotly colorscale. The color dropdown exposes
  Plotly's curated named colorscale set and defaults to `turbo`; a separate fractal
  dropdown selects Mandelbrot or one of the named Julia sets.
- One `@app.callback` re-renders the figure whenever any control, graph click, or
  graph viewport update changes (fractal mode, color, iterations, power, zoom, center
  X, center Y, clicked coordinates, or wheel-driven axis ranges).

### 2. Math engine: vectorized Mandelbrot and Julia escape-time algorithm

`calculate_fractal(h, w, y_range, x_range, iterations, intPower, julia_constant=None)`
works entirely on NumPy arrays:

- The complex coordinate grid is built with `linspace` + `meshgrid` (700 × 1000
  complex128 array).
- In Mandelbrot mode (`julia_constant=None`), the grid supplies `c` and `z` starts at
  zero. In Julia mode, the grid supplies initial `z` and `c` is the selected fixed
  constant. Both use `z = z**n + c`.
- Each iteration updates **only pixels that have not escaped yet**, selected by a
  boolean `mask`; newly escaped pixels are stamped with iteration index `i` and removed
  from the mask.
- The result is an integer array of first-escape iteration counts, which feeds directly
  into the heatmap colorscale (colorbar titled "Iterations").
- Power `n` is a runtime parameter (`z**intPower`) for both modes.

The Julia dropdown provides these constants:

| Set | `c` |
|---|---|
| Classic Beauty | `-0.4 + 0.6i` |
| Classic Beauty | `-0.8 + 0.156i` |
| Douady Rabbit | `-0.123 + 0.745i` |
| Dendrite | `0 + 1.0i` |
| San Marco | `-0.75 + 0.1i` |

**Chosen over:** per-pixel Python loops (unacceptably slow), WebGPU/WebGL shader
rendering (breaks the pure-Python constraint), and a dedicated fractal library
(unneeded for this feature set and adds a dependency).

### 3. Viewport model: fixed "world" view + numeric zoom/center

- The base world is fixed: Re ∈ [-2.25, 1.25], Im ∈ [-1.5, 1.5] (the classic full view).
- Zoom shrinks the viewport *around the center point*:
  `half = (world_size / max(zoom, 0.0001)) / 2`, giving
  `x_range = (cx - half_w, cx + half_w)`, `y_range = (cy - half_h, cy + half_h)`.
- `max(zoom, 0.0001)` guards against division by zero / negative zoom from stray input.
- All zoom and pan state is expressed through explicit numeric values (zoom factor,
  center X, and center Y). Clicking the heatmap updates the center-X and center-Y
  inputs to the clicked `(x, y)` coordinates. The resulting view state remains a
  small, serializable, reproducible tuple.
- Plotly's `scrollZoom` is enabled. Wheel zoom emits axis ranges through `relayoutData`;
  the callback converts those ranges back to the zoom factor and viewport center,
  updates the numeric controls, and re-renders the fractal at that view.
- Empty or missing callback values are normalized to defaults: iterations 100,
  power 2, zoom 1, center X -0.5, center Y 0, and palette `turbo`. Zoom is clamped
  to a minimum of 0.0001. Iterations and power are converted to positive integers.
- Changing fractal mode resets zoom to 1 and centers the view at `(-0.5, 0)` for
  Mandelbrot or `(0, 0)` for Julia sets.

**Chosen over:** freeform box zoom and drag navigation as the primary viewport
controls. Wheel zoom is supported as a convenience, while its resulting view is
synchronized to the same explicit numeric state.

### 4. Rendering fidelity details

- Fixed rendering resolution 1000 × 700 pixels, displayed in an 80 vh graph container.
- Aspect ratio locked with `yaxis: {scaleanchor: "x", scaleratio: 1}` so Re and Im
  scales stay 1:1 regardless of browser window size.
- `connectgaps=False` on the heatmap.
- Compact 50 px margins so the plot area dominates.

### 5. Control ergonomics (v1 → v2)

- v1 used `dcc.Slider`s for iterations/zoom/center and a 2–10 power dropdown; v2
  replaces them with `dcc.Input` number fields (iterations step 10, power step 1,
  zoom step 0.5, center step 0.001), allowing precise values (e.g. fractional zoom,
  iteration counts beyond a slider's max).
- The color dropdown exposes a curated set of Plotly named colorscales rather than
  requiring a custom CSS or JavaScript control.
- Layout heights tightened to `80vh` (graph and sidebar) so the page fits a standard
  viewport without scrolling.

### 6. Development ergonomics: "port janitor" + no-reloader startup

- `cleanup_port(8050)` runs only in `__main__`: it `lsof -ti :8050`s the port,
  `kill -9`s every foreign PID found, and **skips its own PID** to avoid suicide.
- The server starts with `use_reloader=False` so the janitor (and any other
  `__main__`-level side effects) run exactly once, and `debug=True` for fast
  browser-side iteration.
- This makes `python plotlyv2.py` reliably re-runnable without manual `kill` steps.

**Chosen over:** leaving port conflicts to the user to resolve, or wrapping the app in
`gunicorn`/Docker (overkill for a local exploratory tool).

## Consequences

**Positive**

- Entirely Python end-to-end; no JS build tooling, no new non-Python runtime.
- Vectorized iteration with early-exit masking keeps renders fast (only
  still-iterating pixels are touched each step) and scales cleanly with iteration
  depth.
- Order-n generalization is a single parameter, trivially testable from the UI.
- Mandelbrot and several Julia sets are available through the same vectorized engine
  and UI; no extra runtime dependency is needed.
- Reproducible views: any image is fully determined by (fractal mode and Julia
  constant, palette, iterations, power, zoom, cx, cy).
- Clicking the plot provides a direct way to center at real/imaginary coordinates
  while retaining the reproducible numeric-view model.
- Reliable local restarts — the single biggest friction in the v1 workflow is
  removed by the port janitor.

**Negative / trade-offs**

- Escape-time values are the *raw iteration index* (0..N), so the colorbar is linear
  in iteration count, not in smooth/normalized escape time; banding appears in
  low-iteration regions. (Acceptable for an explorer; a future ADR could cover
  smooth iteration counts + `log` normalization.)
- Points that never escape keep the initial value `0`, which is the same as a pixel
  that escaped on iteration 0 (i.e. `|c| >= 2` at the first step); the interior and
  a thin exterior band can share a color at the palette's lowest end.
- Rendering is synchronous inside the callback: high iteration counts × high power on
  a 1000 × 700 grid can block the request for seconds. No progress feedback, no
  cancellation, no worker pool.
- `kill -9` is a blunt instrument: it can only kill processes the user owns, and on a
  shared machine it will terminate *any* listener on 8050 without asking.
- Numeric zoom has no logarithmic scale (v1's slider did 1×→1000× linearly); reaching
  deep zoom requires typing large values.
- Fixed 1000 × 700 resolution does not adapt to display pixel density or window size.
- `debug=True` is a development default; it must not be shipped as-is in any
  hosted/production context.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Streamlit | Viable, but the project already invested in Dash/Plotly (`plotlyv1.py`), and Dash gives finer control over layout, callbacks, and the port/startup lifecycle. |
| Matplotlib + Flask | More boilerplate; Plotly heatmap + colorscales deliver the interactivity (hover, export, zoom toolbar) for free. |
| WebGPU/shader renderer | Fastest at deep zoom, but requires a JS/WASM stack and breaks the pure-Python constraint. |
| Mouse-driven zoom/pan (Dash `relayout` events) | More natural UX, but state is fragmented across events and hard to reproduce/share; explicit numeric viewport is simpler and deterministic. |
| Background worker + queue for renders | Needed only if renders become slow enough to warrant it; premature for the current 1000 × 700 × ≤500-iteration budget. |

## References

- `plotlyv2.py` — implementation described by this ADR.
- `plotlyv1.py` — prior revision (sliders, 800 × 800, 90-color list) used as the
  baseline for the v2 ergonomics decisions.
- Plotly Dash documentation — callbacks, `dcc` components, `dcc.Graph` layout.
