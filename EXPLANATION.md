# Drawing-Equation — How It Works

This document explains what the project is, how to run it, what the math is
actually doing, and how to add your own shapes.

If you only read one section, read **[The idea in one paragraph](#the-idea-in-one-paragraph)**
and **[How to add a new shape](#how-to-add-a-new-shape)**.

---

## The idea in one paragraph

Take any closed outline — a crown, a heart, your signature. Walk around it and
record the position of the pen as it moves. That is a function of time: `x(t)`
and `y(t)`. Any such periodic function can be written as a **sum of rotating
circles** (a Fourier series). Each circle spins at its own speed, and if you
attach them tip-to-tail, the pen at the very end of the chain retraces the
original outline. Add more circles and you get closer to the exact shape. That
chain of circles is called **epicycles**, and this project draws them.

---

## Repository layout

```
Drawing-Equation/
├── AGENTS.md          project memory (status, decisions, verified numbers)
├── EXPLANATION.md     <- you are here
├── README.md
├── .gitignore         ignores .venv/, __pycache__/, output/
├── python/
│   ├── shapes.py      shape definitions + arc-length resampling
│   ├── fourier.py     the math: DFT, reconstruction, epicycle chain, RMSE
│   └── main.py        CLI: writes the static PNG and the animated GIF
├── output/            generated files (git-ignored)
│   ├── crown_static.png
│   └── crown_epicycles.gif
└── web/               interactive Canvas app (not built yet)
```

The three Python files have one job each:

| File | Responsibility |
|---|---|
| `shapes.py` | Produce a shape as an `(N, 2)` array of points |
| `fourier.py` | Turn those points into coefficients and back again |
| `main.py` | Command-line interface + all the drawing/rendering |

`fourier.py` never touches matplotlib. `main.py` never does math beyond calling
`fourier.py`. Keeping the math pure is what makes it testable and portable to
JavaScript later.

---

## Quick start

### One-time setup

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
cd C:\Users\Ramy\Desktop\HQP\Drawing-Equation
.\.venv\Scripts\Activate.ps1
```

### Run

Always run from the `python` folder.

```powershell
cd C:\Users\Ramy\Desktop\HQP\Drawing-Equation\python

# static comparison of 3 / 8 / 20 / 60 terms, with RMSE printed on each panel
python main.py --shape crown --static

# animated epicycles -> GIF
python main.py --shape crown --animate --terms 32 --frames 100

# both at once
python main.py --shape heart --static --animate
```

Output lands in `output/`. There is no pop-up window — `main.py` forces
matplotlib's `Agg` backend (line 25) so it renders straight to files.

### If you don't want to activate the venv

From the `python` folder:

```powershell
..\.venv\Scripts\python.exe main.py --shape heart --static --animate
```

### Command-line options

| Flag | Meaning | Default |
|---|---|---|
| `--shape NAME` | one of `crown`, `star`, `heart`, `infinity` | `crown` |
| `--static` | save an N-terms comparison PNG | off |
| `--animate` | save the epicycle animation GIF | off |
| `--terms N` | epicycles used **in the animation only** | `32` |
| `--frames N` | frames per full loop **in the animation only** | `100` |

Two gotchas worth knowing:

- `--shape` takes exactly **one** value. `--shape bird heart` is an error, not
  "two shapes".
- `--terms` does **not** affect the static image. The static image always uses
  the hardcoded list `[3, 8, 20, 60]` (`main.py` line 141).
- If you pass **neither** flag you get the static image anyway, because line 140
  reads `if args.static or not args.animate`.

---

## The math

### 1. Represent the outline as a complex signal

Instead of two real functions `x(t)` and `y(t)`, store each point as one
complex number:

```
z_n = x_n + i * y_n
```

This is a trick, not a new idea — `i` is just a bookkeeping device that keeps
the two coordinates glued together. It means we can write one Fourier sum
instead of two. `fourier.py` line 31 does exactly this.

### 2. Sample evenly by arc length

The DFT assumes your samples are evenly spaced in the parameter `t`. If you feed
it a polygon's raw vertices, short edges get the same weight as long edges and
the reconstruction is distorted.

`shapes.py::_resample_polygon` fixes this. It walks the closed polygon,
accumulates distance along the perimeter, then picks `n` points at equal
*arc-length* intervals by interpolating inside the right segment
(`shapes.py` lines 12–25). This is why a triangle and a circle both behave well.

`_normalize` then centres the shape at the origin and scales it to fit inside
roughly `[-1, 1]²`, so every shape renders at a comparable size.

### 3. The DFT

For `N` samples, the coefficient of frequency `k` is:

```
c_k = (1/N) * Σ_n  z_n * e^(−i 2π k n / N)
```

That is precisely what `np.fft.fft(z) / N` computes (`fourier.py` line 34).
**The `/N` matters** — NumPy's FFT is unnormalised, so without it every radius
would be `N` times too big.

Then `np.fft.fftfreq(N, d=1/N)` gives the matching integer frequencies
(`fourier.py` line 35). Because of how the FFT is laid out, these start at 0,
count up to `N/2−1`, then go **negative**. Negative frequencies are not a
mistake — they are circles spinning the other way, and you need them to
represent arbitrary shapes.

### 4. Sort by magnitude — and why that's optimal

`fourier.py` line 37 sorts the coefficients by `|c_k|`, largest first:

```python
order = np.argsort(-np.abs(coeffs))
```

`|c_k|` is the radius of circle `k`. Sorting by radius is what makes "N terms"
mean something useful: if you are only allowed `N` circles, taking the `N`
biggest ones is the best possible approximation under the standard squared-error
measure. This is why truncating the series degrades gracefully instead of
falling apart.

### 5. Reconstruction

```
z(θ) = Σ_k  c_k * e^(i * freq_k * θ)
```

In code (`fourier.py` line 51):

```python
return np.exp(1j * f[None, :] * theta[:, None]) @ c
```

That `@` is a matrix product: build an `(angles × terms)` matrix of complex
exponentials, multiply by the `(terms,)` vector of coefficients, and out comes
one reconstructed point per angle. `reconstruct` is used for the **static** image,
where you want the whole curve at once.

### 6. The epicycle chain

For the **animation** you need something different: the joint positions, not just
the endpoint. That's `chain` (`fourier.py` line 61):

```python
return np.cumsum(c * np.exp(1j * f * theta))
```

`cumsum` is the tip-to-tail stacking. Entry `0` is the first circle's centre
offset, entry `1` is the position after two circles, and so on. **The last entry
is the pen tip** — and it equals `reconstruct` at the same `θ`, just built
incrementally instead of all at once.

`main.py` uses this in `update()` (lines 103–118): it walks the joints, drawing a
circle centred on the previous joint with radius `|c_i|`, and a spoke from the
previous joint to the current one. That's the entire visual.

### 7. Measuring the error

`rmse` (`fourier.py` line 64) evaluates the reconstruction at the *same* angles
the original points were sampled at, then reports:

```
RMSE = sqrt( mean( |true − approx|² ) )
```

Same-angles comparison matters — comparing at different angles would measure
phase misalignment rather than shape error.

### Verified accuracy (crown, 512 samples)

| Terms | RMSE |
|------:|-----:|
| 1 | 0.340229 |
| 3 | 0.196254 |
| 5 | 0.114511 |
| 8 | 0.061400 |
| 12 | 0.035246 |
| 20 | 0.015410 |
| 40 | 0.006066 |
| 80 | 0.002229 |
| 160 | 0.000749 |
| 320 | 0.000215 |
| 512 | 0.000000 (exact) |

Two things to notice:

- **Exact at 512 = N.** With as many terms as samples, the reconstruction is
  perfect. This is a property of the DFT, not a coincidence.
- **Sharp corners converge slowly.** The crown's spikes need many terms because a
  corner is mathematically "infinitely sharp". Near a corner you'll see
  overshoot ripples — the **Gibbs phenomenon**. The heart, being smooth, needs
  far fewer terms for the same RMSE. Try it and compare.

---

## How the rendering works

### Static image (`plot_static`, `main.py` lines 58–78)

One panel per term count from `[3, 8, 20, 60]`. Each panel draws:

- the true outline as a dashed grey guide (`GRID` colour)
- the truncated reconstruction as a solid mint line

The title of each panel is the term count plus its RMSE, so you can watch
accuracy improve left to right.

### Animation (`plot_animation`, `main.py` lines 81–124)

The important design choice: **the artists are created once, outside `update`**.

```python
circles = [Circle(...) for _ in range(m)]
spokes  = [ax.plot([], [], ...) for _ in range(m)]
glow, = ax.plot([], [], ...)   # wide, low-alpha mint line
trail, = ax.plot([], [], ...)  # thin bright mint line
tip, = ax.plot([], [], "o", ...)
```

matplotlib's `FuncAnimation` reuses these objects every frame. Creating new
`Circle` patches inside `update` would be correct but very slow — this is the
standard performance pattern for animated plots.

The trail is drawn twice: a 5px-wide line at alpha `0.16` underneath, and a
1.8px bright line on top. That's the glow effect — no expensive blur needed.

`xs` and `ys` accumulate the pen tip each frame, so the trail grows into the
finished shape over one loop, then resets when `frames` wraps around.

Frames are saved at 30 fps through `PillowWriter`, so no ffmpeg is required.

---

## How to add a new shape

This is the part you'll do most often. It's a small, well-defined change in
**`python/shapes.py`** — three steps.

### Step 1 — write a function that returns `(N, 2)` points

A shape function takes no required arguments (defaults are fine) and returns a
NumPy array of shape `(N, 2)`.

**Polygon style — you supply corner vertices:**

```python
def bird(n: int = 512) -> np.ndarray:
    """A simple side-profile bird."""
    vertices = np.array(
        [
            [-1.00,  0.00],
            [-0.50,  0.35],
            [-0.10,  0.30],
            [ 0.30,  0.75],
            [ 0.55,  0.55],
            [ 0.95,  0.85],
            [ 0.75,  0.25],
            [ 0.30,  0.00],
            [-0.60, -0.40],
        ]
    )
    return _normalize(_resample_polygon(vertices, n))
```

Rules for this style:

- List vertices **in order** around the outline (clockwise or counter-clockwise
  — but be consistent, or you'll get a bow-tie).
- **Do not repeat the first vertex at the end.** `_resample_polygon` closes the
  loop itself (`shapes.py` line 14).
- Coordinates are arbitrary — `_normalize` rescales them.
- The outline must be **closed and non-self-intersecting**, or the DFT will
  still run but the resampling will zig-zag.

**Formula style — you supply a parametric curve:**

```python
def blob(n: int = 512) -> np.ndarray:
    """A wobbly circle, as a formula."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    r = 0.6 + 0.25 * np.sin(3 * t) + 0.1 * np.cos(5 * t)
    return _normalize(np.column_stack([r * np.cos(t), r * np.sin(t)]))
```

This is the pattern `heart` and `infinity` already use (`shapes.py` lines 62–76).
Use it when you have a neat equation; use the polygon style when you're tracing
a silhouette by hand.

### Step 2 — register it in `SHAPES`

At the bottom of `shapes.py`:

```python
SHAPES = {
    "crown": crown,
    "star": star,
    "heart": heart,
    "infinity": infinity,
    "bird": bird,        # <- add this line
}
```

The dictionary **key is the value you type on the command line**. So `"bird"`
means `--shape bird`. Use lowercase, no spaces.

### Step 3 — run it

```powershell
cd C:\Users\Ramy\Desktop\HQP\Drawing-Equation\python
python main.py --shape bird --static --animate
```

That's it. `main.py` needs **no changes** — its `--shape` argument is already
built from `sorted(SHAPES)` (`main.py` line 129), so the new shape shows up in
`--help` and in the "invalid choice" error message automatically.

### Checklist

- [ ] Function returns `(N, 2)` — check with `.shape`
- [ ] Vertices in consistent order, **first vertex not repeated at the end**
- [ ] Shape is closed and doesn't self-intersect
- [ ] Passed through `_normalize(_resample_polygon(...))` (polygon style) or
      `_normalize(...)` (formula style)
- [ ] Added to the `SHAPES` dict at the bottom of `shapes.py`
- [ ] Tested with `--static` before you bother with `--animate`

### Tuning an existing shape without editing much

`star` already exposes parameters, so you can call it directly:

```python
star(points=7, inner=0.30)   # 7-pointed, spikier star
```

If you want to reach those from the command line, that's a small addition to
`main.py`'s argparse section — ask and it can be wired up.

---

## Design decisions already locked in

These are settled; change them deliberately, not by accident.

**Palette** (defined at the top of `main.py`):

| Name | Hex | Used for |
|---|---|---|
| `BG` | `#0b0b12` | background |
| `GRID` | `#333355` | true-outline guide |
| `INK` | `#c8c8e0` | titles / text |
| `MINT` | `#00ffcc` | reconstruction + trail |
| `CIRCLE` | `#3a6d8c` | epicycle circles |
| `SPOKE` | `#4d7a99` | epicycle spokes |

**Animation:** 30 fps, glow underlay plus bright trail line plus white pen tip.

**Backend:** `Agg` — always writes files, never opens a blocking window.

**Cosmetic note:** `_bare_axes` (lines 45–55) sets `set_aspect("equal")`. Without
it the shapes would look stretched, because data coordinates wouldn't match
screen coordinates.

---

## Porting to the web (`web/`, not started)

The roadmap, and the reason `fourier.py` is kept free of matplotlib:

| Milestone | Feature |
|---|---|
| W1 | Canvas + `requestAnimationFrame` loop (60 fps, `devicePixelRatio` crisp) |
| W2 | Port `fourier.py` to `dft.js`; verify outputs match the Python numbers |
| W3 | Epicycles + glow/fading trail + pen tip |
| W4 | `N`-term slider — watch accuracy live, show error |
| W5 | Mouse drawing → record path → FFT |
| W6 | Presets, share/export, deploy to GitHub Pages |

The math maps over directly: complex numbers in JS become `{re, im}` pairs or
plain `Float64Array` pairs, `np.fft.fft` becomes a hand-written DFT (fine at
`N = 512`), and `cumsum` is a running sum in the draw loop.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| `can't open file ...\Scripts\main.py` | You're not in the `python` folder |
| `invalid choice: 'bird'` | Shape isn't registered in the `SHAPES` dict |
| `ModuleNotFoundError: numpy` | Wrong Python — use the venv one |
| Nothing appears on screen | Expected: output goes to `output/` as files |
| Shape looks like a bow-tie | Vertices out of order, or first vertex repeated |
| Shape looks squashed | Something bypassed `_normalize`, or `set_aspect("equal")` was removed |
