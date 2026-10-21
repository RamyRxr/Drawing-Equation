# Drawing-Equation — How It Works

A complete guide to this project: what it is, how the folder is organised
(including the virtual environment), how to run it, what the math actually
does, and how to add your own shapes.

If you only read one section, read
**[The idea in one paragraph](#the-idea-in-one-paragraph)**,
**[Repository layout](#repository-layout)** and
**[How to add a new shape](#how-to-add-a-new-shape)**.

---

## Table of contents

1. [The idea in one paragraph](#the-idea-in-one-paragraph)
2. [Repository layout](#repository-layout)
3. [The virtual environment (`.venv`)](#the-virtual-environment-venv)
4. [Quick start](#quick-start)
5. [Command-line options](#command-line-options)
6. [The end-to-end data flow](#the-end-to-end-data-flow)
7. [The math](#the-math)
8. [How the rendering works](#how-the-rendering-works)
9. [How to add a new shape](#how-to-add-a-new-shape)
10. [Design decisions already locked in](#design-decisions-already-locked-in)
11. [Porting to the web (`web/`, not started)](#porting-to-the-web-web-not-started)
12. [Troubleshooting](#troubleshooting)

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
│
├── .git/                      Git's own database (history, branches, index)
│
├── .venv/                     ← THE VIRTUAL ENVIRONMENT  [see section 3]
│   ├── .gitignore             contains just "*" — the venv hides itself from Git
│   ├── pyvenv.cfg             venv config: Python version + base interpreter
│   ├── Include/               empty on Windows (C headers on Linux/macOS)
│   ├── Lib/
│   │   └── site-packages/     ← pip installs every package HERE
│   ├── Scripts/               ← python.exe, pip.exe, activate scripts, etc.
│   └── share/
│       └── man/man1/          man pages (ttx.1, shipped by fontTools)
│
├── output/                    generated artwork (git-ignored, safe to delete)
│   ├── crown_static.png       4-panel comparison: 3 / 8 / 20 / 60 terms
│   ├── crown_epicycles.gif    spinning epicycles, 32 circles
│   ├── heart_static.png
│   └── heart_epicycles.gif
│
├── python/                    the prototype
│   ├── __pycache__/           compiled .pyc cache (git-ignored, auto-created)
│   ├── shapes.py              shape definitions + arc-length resampling
│   ├── fourier.py             the math: DFT, reconstruction, epicycle chain, RMSE
│   └── main.py                CLI: writes the static PNG and the animated GIF
│
├── .gitignore                 ignores .venv/, __pycache__/, output/
├── AGENTS.md                  project memory (status, decisions, verified numbers)
├── EXPLANATION.md             ← you are here
└── README.md                  short front door — points at this file
```

### The three Python files, one job each

| File | Responsibility | Knows about |
|---|---|---|
| `shapes.py` | Produce a shape as an `(N, 2)` array of points | NumPy only |
| `fourier.py` | Turn those points into coefficients and back again | NumPy only |
| `main.py` | Command-line interface + all the drawing/rendering | Matplotlib |

`fourier.py` **never touches matplotlib**. `main.py` **never does math** beyond
calling `fourier.py`. Keeping the math pure is what makes it testable and
portable to JavaScript later — when the web app arrives, `fourier.py` can be
translated to `dft.js` one-to-one with no drawing code in the way.

### Which folders are tracked by Git?

| Folder | In Git? | Why |
|---|---|---|
| `python/` | ✅ yes | this is the actual source code |
| `AGENTS.md`, `README.md`, `EXPLANATION.md` | ✅ yes | documentation |
| `.gitignore` | ✅ yes | tells Git what to skip |
| `.venv/` | ❌ **no** | 133 MB of third-party binaries — machine-specific, regenerated on demand |
| `output/` | ❌ **no** | build artifacts — 2 MB of PNGs/GIFs you can regenerate |
| `python/__pycache__/` | ❌ **no** | Python's byte-code cache, rebuilt automatically |
| `.git/` | ❌ **no** | Git's internals |

---

## The virtual environment (`.venv`)

This is the single most confusing thing for a newcomer, so this section is
long. Read it once and the rest of the project becomes obvious.

### What problem does it solve?

Python packages are installed **globally** by default: `pip install numpy`
drops NumPy into your system Python's `site-packages`. That causes three
classic problems:

1. **Version conflicts.** Project A needs NumPy 1.x, project B needs NumPy 2.x.
   Installed globally, they fight over the same folder and one of them breaks.
2. **Permission errors.** Global installs often need administrator rights on
   Windows, and you get `Access is denied` half-way through.
3. **No record of what the project needs.** Six months later you cannot tell
   which packages a project actually requires.

A **virtual environment** solves all three. It is just a private, isolated
folder containing its own Python interpreter and its own package folder. When
you install into it, nothing touches the system Python.

The name `.venv` is a convention. The leading dot makes it **hidden** on Unix
(`ls -a` needed to see it) and makes most tools skip it by default.

### Where it lives — an important detail

```
C:\Users\Ramy\Desktop\HQP\Drawing-Equation\.venv      ← THIS one, at the REPO ROOT
C:\Users\Ramy\Desktop\HQP\Drawing-Equation\python\.venv ← NOT this
```

The venv sits **next to `python/`, not inside it**. That is why every command
in this project has to reach *up* one level:

```powershell
..\.venv\Scripts\python.exe main.py --shape crown --static
```

That `..` means "parent directory". From inside `python/`, `..` is the repo
root, where `.venv` actually is.

> **Note:** an older version of `README.md` told you to create the venv inside
> `python/`. That has been corrected — the venv lives at the repo root, and
> that is what is on disk right now.

### Anatomy of the folder

| Path | What it is | Do you ever edit it? |
|---|---|---|
| `.venv/pyvenv.cfg` | The venv's identity card: Python version, path to the base interpreter, whether system site-packages are visible | Never |
| `.venv/Scripts/` | The executables: `python.exe`, `pythonw.exe`, `pip.exe`, `pip3.exe`, `activate.ps1`, `deactivate.bat`, plus small wrappers for every installed package (`f2py.exe`, `ttx.exe`, `fonttools.exe`…) | Never |
| `.venv/Lib/site-packages/` | **Where every installed package lives.** This is the folder `pip` writes to | Never |
| `.venv/Include/` | C headers for building native extensions. Empty on Windows (no compiler by default) | Never |
| `.venv/share/` | Data files that aren't Python modules — here, `man/man1/ttx.1`, a man page from fontTools | Never |
| `.venv/.gitignore` | Contains a single `*`. The venv marks itself as ignorable, so even a broken root `.gitignore` won't accidentally commit 133 MB | Never |

**The rule of thumb: you never type a file inside `.venv/`. You only run
things from it and let `pip` write into it.**

### What's actually installed

Right now the venv contains exactly these packages:

| Package | Version | Why it's here |
|---|---|---|
| `numpy` | 2.5.4 | The math: arrays, `np.fft.fft`, `np.cumsum`, `np.linalg` |
| `matplotlib` | 3.11.2 | All the drawing: plots, GIF animation, `Circle` patches |
| `pillow` | 13.0.0 | GIF writing (matplotlib's `PillowWriter` backend) |
| `contourpy` | 1.4.0 | Dependency of matplotlib (contour plots) |
| `cycler` | 0.12.1 | Dependency of matplotlib |
| `fonttools` | 4.67.0 | Dependency of matplotlib (font handling) |
| `kiwisolver` | 1.5.1 | Dependency of matplotlib (font cache building) |
| `packaging` | 26.3 | Dependency of matplotlib (version comparisons) |
| `pyparsing` | 3.3.3 | Dependency of matplotlib (used by mathtext) |
| `python-dateutil` | 2.9.0 | Dependency of matplotlib (date handling) |
| `six` | 1.17.0 | Dependency of python-dateutil |
| `pip` | 26.2.1 | The package installer itself |

You install **two** packages (`numpy`, `matplotlib`) and pip pulls in the other
ten as dependencies. That is normal.

### How to check which Python you're running

The venv's Python reports two different paths. This is how you know you're
inside it:

```powershell
.\.venv\Scripts\python.exe -c "import sys; print(sys.prefix); print(sys.base_prefix)"
```

```
C:\Users\Ramy\Desktop\HQP\Drawing-Equation\.venv   ← prefix (venv)
C:\Python315                                       ← base_prefix (system)
```

If the two lines are **identical**, you are running the system Python and the
venv's packages are invisible to you.

### Activating the venv (optional but convenient)

Activation doesn't install anything — it just temporarily rewires your shell so
that the bare word `python` means the venv's `python.exe`.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force   # once per shell
cd C:\Users\Ramy\Desktop\HQP\Drawing-Equation
.\.venv\Scripts\Activate.ps1
```

Your prompt changes to show `(.venv)`. Now `python` and `pip` point at the
venv:

```powershell
python main.py --shape crown --static
pip install numpy
```

Leave with:

```powershell
deactivate
```

> `Set-ExecutionPolicy ... -Scope Process` is needed because Windows blocks
> running PowerShell scripts from the internet by default. `-Scope Process`
> means "just this terminal window" — it does not change your machine-wide
> settings.

### Running without activating (the shortcut)

Activation is optional. You can always call the venv's interpreter by full
path, which is more explicit and works in scripts:

```powershell
cd C:\Users\Ramy\Desktop\HQP\Drawing-Equation\python
..\.venv\Scripts\python.exe main.py --shape crown --static
```

`pip` works the same way:

```powershell
..\.venv\Scripts\pip.exe install numpy
```

### Recreating the venv from scratch

If you delete `.venv/`, or clone the repo on a new machine, you rebuild it in
about a minute. Nothing is lost — `.venv/` holds no source code, only
third-party binaries.

```powershell
cd C:\Users\Ramy\Desktop\HQP\Drawing-Equation

# 1. Create the venv at the repo root
C:\Python315\python.exe -m venv .venv

# 2. Install the two packages you actually need
.\.venv\Scripts\pip.exe install numpy matplotlib

# 3. Confirm
.\.venv\Scripts\python.exe -c "import numpy, matplotlib; print('ok')"
```

Step 1 needs a real interpreter — `C:\Python315\python.exe` is what
`pyvenv.cfg` records as the base. Using `python -m venv .venv` works too as
long as that `python` is 3.15.

### Common `.venv` problems

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'numpy'` | You're running the system Python, not the venv's | Use `..\.venv\Scripts\python.exe` from `python/`, or activate the venv |
| `cannot be loaded because running scripts is disabled` | PowerShell execution policy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force` |
| `The term '.\.venv\Scripts\Activate.ps1' is not recognized` | You're in the wrong directory | `cd` to the repo root first |
| `No module named venv` | Python installed without the `venv` module | Reinstall Python with the optional features |
| `Access is denied` on `pip install` | You tried a global install | Use the venv's `pip.exe` |
| Venv seems "empty" in the file explorer | Windows Explorer hides some folders by default, and the `.` prefix makes it hidden-ish | Use `dir /a` in PowerShell, or enable "Hidden items" in View → Show |

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
matplotlib's `Agg` backend (`main.py` line 25) so it renders straight to files.

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

## The end-to-end data flow

This is the whole program in one picture:

```
  shapes.py                      fourier.py                   main.py
  ─────────                      ─────────                   ───────
  crown(512)
     │  resample by arc length
     │  normalize to [-1,1]²
     ▼
  points: (512, 2)  ─────────►  coefficients(points)
  x₁ y₁ x₂ y₂ …                   │
                                  │  z = x + iy
                                  │  coeffs = fft(z)/N
                                  │  freqs  = fftfreq(N, 1/N)
                                  │  sort by |coeffs| desc
                                  ▼
                            coeffs (512,)  freqs (512,)
                            c₀ = 0.736 + 0.105j  @ freq +1
                            c₁ = 0.248 - …       @ freq +2
                            …
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
        reconstruct(coeffs, freqs, θ)   chain(coeffs, freqs, θ, m)
        → one point per angle             → joint positions of the chain
        (used by the STATIC image)       (used by the ANIMATION)
                    │                           │
                    ▼                           ▼
        plot 3 / 8 / 20 / 60 terms       circles + spokes + trail
        → crown_static.png               → crown_epicycles.gif
```

Two different reconstruction helpers exist because the two outputs need
different things:

- The **static image** wants the whole curve at once → `reconstruct` evaluates
  the sum at 512 angles in one matrix product.
- The **animation** wants to know where each *joint* of the chain is, frame by
  frame → `chain` returns the cumulative sum, whose last entry is the pen tip.

Both produce the same pen-tip position for the same `θ`. They differ only in
how the result is packaged.

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

Step by step:

```python
v = np.vstack([vertices, vertices[0]])   # close the loop
seg = np.diff(v, axis=0)                 # edge vectors
seg_len = np.hypot(seg[:, 0], seg[:, 1]) # edge lengths
cum = np.concatenate([[0.0], np.cumsum(seg_len)])  # distance at each vertex
total = cum[-1]                          # perimeter
```

then for each target distance `d` (evenly spread over `[0, total)`):

```python
j = min(int(np.searchsorted(cum, d, side="right") - 1), len(seg) - 1)
frac = (d - cum[j]) / seg_len[j]
out[i] = v[j] + frac * seg[j]            # linear interpolation inside edge j
```

`np.searchsorted` finds which edge contains `d`; `frac` says how far along that
edge we are; the last line slides the point along the edge. Because the
targets are evenly spaced in distance, the samples are evenly spaced in
arc length — which is exactly what the DFT wants.

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

Here are the first eight circles for the crown (measured, not guessed):

| Circle | `\|c_k\|` (radius) | frequency | start angle |
|---:|---:|---:|---:|
| 0 | 0.736110 | +1 | −2.3329 rad |
| 1 | 0.248185 | +2 | −3.0951 rad |
| 2 | 0.125077 | +4 | −1.4778 rad |
| 3 | 0.118099 | −1 | +2.3330 rad |
| 4 | 0.107031 | −4 | −1.6638 rad |
| 5 | 0.070333 | −5 | +2.2400 rad |
| 6 | 0.048050 | +5 | +0.9016 rad |
| 7 | 0.045686 | −2 | +3.0951 rad |

The first circle alone is a big circle of radius 0.736 — that is the shape's
overall size and position. Everything after it adds progressively finer
detail.

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
one reconstructed point per angle. `reconstruct` is used for the **static**
image, where you want the whole curve at once.

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

### Verified accuracy

All numbers below were re-measured from the current code and are reproducible
with the one-liner in the next section.

**Crown, 512 samples** (sharp corners → slow convergence):

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

**All four presets, side by side:**

| Shape | 1 term | 3 terms | 8 terms | 20 terms | 60 terms |
|---|---:|---:|---:|---:|---:|
| crown | 0.340229 | 0.196254 | 0.061400 | 0.015410 | 0.003405 |
| star | 0.173610 | 0.020671 | 0.006100 | 0.001523 | 0.000305 |
| heart | 0.283637 | 0.166378 | 0.000000 | 0.000000 | 0.000000 |
| infinity | 0.492586 | 0.204036 | 0.018946 | 0.000096 | 0.000000 |

Three things to notice:

- **Exact at 512 = N.** With as many terms as samples, the reconstruction is
  perfect. This is a property of the DFT, not a coincidence.
- **Sharp corners converge slowly.** The crown's spikes need many terms because a
  corner is mathematically "infinitely sharp". Near a corner you'll see
  overshoot ripples — the **Gibbs phenomenon**.
- **The heart is nearly free.** `heart` is *defined* by a sum of cosines
  (`shapes.py` lines 65–66), so it is already a Fourier series — its DFT
  coefficients are almost exactly the handful of cosines you started with. It
  reaches zero error by 8 terms while the crown is still at 0.06.

Reproduce the table yourself from the repo root:

```powershell
.\.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, 'python')
from shapes import SHAPES
from fourier import coefficients, rmse
for name in SHAPES:
    pts = SHAPES[name]()
    c, f = coefficients(pts)
    print(name, ' '.join(f'{t}:{rmse(pts,c,f,t):.6f}' for t in [1,3,8,20,60]))
"
```

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

### Output files

| File | Produced by | Contents |
|---|---|---|
| `output/<shape>_static.png` | `--static` | 4 side-by-side panels (3/8/20/60 terms) with per-panel RMSE |
| `output/<shape>_epicycles.gif` | `--animate` | One loop of the spinning epicycle chain with a growing trail |

Both are overwritten each run. `output/` is git-ignored, so the repo stays
clean; if you delete it, just run the tool again.

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

The pattern `heart` and `infinity` already use (`shapes.py` lines 62–76).
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
built from `sorted(SHAPES)` (`main.py` line 129), so the new shape shows up
in `--help` and in the "invalid choice" error message automatically.

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

**Sample count:** 512 for every shape. Large enough that the DFT is accurate,
small enough that the matrix product in `reconstruct` is instant.

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

The web app will need no virtual environment — it's plain HTML/CSS/JS served
statically, which is exactly why GitHub Pages is the eventual home for it.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `can't open file ...\Scripts\main.py` | You're not in the `python` folder | `cd` into `Drawing-Equation\python` |
| `ModuleNotFoundError: numpy` | Running the system Python, not the venv's | Use `..\.venv\Scripts\python.exe`, or activate the venv |
| `cannot be loaded because running scripts is disabled` | PowerShell execution policy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force` |
| `The term '.\.venv\Scripts\Activate.ps1' is not recognized` | Wrong directory | `cd` to the repo root — `.venv` is one level up from `python/` |
| `invalid choice: 'bird'` | Shape isn't registered in the `SHAPES` dict | Add it to `SHAPES` in `shapes.py` |
| Nothing appears on screen | Expected: output goes to `output/` as files | Open `output/<shape>_static.png` |
| Shape looks like a bow-tie | Vertices out of order, or first vertex repeated | Reorder the vertex list; don't repeat the first point |
| Shape looks squashed | Something bypassed `_normalize`, or `set_aspect("equal")` was removed | Route every shape through `_normalize` |
| Animation is slow with many terms | Every circle is a separate matplotlib `Circle` patch | Cap `--terms` around 32–60 |
| `output/` is huge | GIFs are uncompressed-ish video | Delete `output/`; it regenerates |
