# Drawing-Equation — Project Memory

> Persistent context for OpenCode / VS Code sessions. Updated 2026-10-20.

## What this project is

An interactive **Fourier epicycles** drawing app. Take any closed shape (crown,
bird, signature), decompose it into a Discrete Fourier Transform, and animate a
chain of rotating circles whose pen traces the shape. More terms → more
accuracy. Based on the truncated Fourier series:

```
        N
x(t) =  Σ  ( a_k·cos(kt) + b_k·sin(kt) )
       k=1

        N
y(t) =  Σ  ( c_k·cos(kt) + d_k·sin(kt) )
       k=1
```

## Goal & approach

Two-week learning project. **Hybrid path:** Python prototype proves/verifies the
math → polished, shareable **web app** with great animation.

- Repo: https://github.com/RamyRxr/Drawing-Equation
- Branch: `main` (tracking `origin/main`)
- Remote: `https://github.com/RamyRxr/Drawing-Equation.git`

## Current status (2026-10-20)

- ✅ Python prototype complete, numerically verified, committed & pushed (`1412638`)
- ⬜ Web app (`web/`) — NOT started yet
- Empty leftover file `test.js` at repo root — can be deleted

## Repo layout

```
Drawing-Equation/
├── AGENTS.md          ← this file (project memory)
├── EXPLANATION.md     ← full guide: idea, layout, .venv, math, panels, shapes
├── README.md          ← short front door, points at EXPLANATION.md
├── requirements.txt   ← pinned versions (numpy, matplotlib, pillow, imageio)
├── .gitignore         ← ignores .venv/, __pycache__/, output/
├── .venv/             ← virtual environment at the REPO ROOT (not inside python/)
├── python/
│   ├── shapes.py      ← crown, star, heart, infinity; arc-length resampling
│   ├── fourier.py     ← DFT coefficients, reconstruct, chain, rmse, relative_error
│   ├── panels.py      ← multi-panel animation (GIF + MP4), freeze logic
│   └── main.py        ← CLI: static PNG, single-shape GIF, panels mode
├── output/            ← generated files (git-ignored)
│   ├── crown_static.png
│   ├── crown_epicycles.gif
│   ├── crown_panels.gif / .mp4          (auto: last panel < target)
│   ├── crown_panels_strict.gif / .mp4   (strict: every panel < target)
│   └── <shape>_panels.gif / .mp4        for star / heart / infinity
└── web/               ← (to build) interactive Canvas app
```

## Environment

- Python 3.15.0
- venv lives at `Drawing-Equation/.venv` (NOT `python/.venv`)
- Packages: numpy 2.5.4, matplotlib 3.11.2
- Windows / PowerShell

### Run commands

```powershell
cd Drawing-Equation\python
..\.venv\Scripts\python.exe main.py --shape crown --static
..\.venv\Scripts\python.exe main.py --shape crown --animate --terms 32 --frames 100
..\.venv\Scripts\python.exe main.py --shape heart --static --animate
..\.venv\Scripts\python.exe main.py --shape crown --panels
..\.venv\Scripts\python.exe main.py --shape crown --panels strict
```

`--shape` ∈ {crown, star, heart, infinity} · `--terms` = epicycle count ·
`--frames` = frames per loop. Output goes to `output/`.
`--panels` (bare) = target-driven, `--panels strict` = every panel under the
target, `--panels 2,8,32,128` = explicit list.

## Verified math (do not regress this)

RMSE vs number of terms on the crown (512 samples):

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

## Core math reference

Treat the outline as a complex signal `z = x + iy`, evenly sampled at `θ_n = 2πn/N`.

- DFT: `c_k = (1/N) Σ_n z_n · e^(-i 2π k n / N)`  → `np.fft.fft(z)/N`
- Frequencies: `np.fft.fftfreq(N, d=1/N)` → integers, negative after N/2
- Sort coefficients by `|c_k|` descending (keeps best approximation per term)
- Reconstruction: `z(θ) = Σ_k c_k · e^(i·freq_k·θ)`
- Epicycle chain = `np.cumsum(c_k · e^(i·freq_k·θ))`; last entry is the pen tip
- Error energy = tail of dropped coefficients (Parseval); exact at N = sample count
- Sharp corners (crown spikes) converge slowly and show **Gibbs phenomenon**

## Decisions already made

- Palette: background `#0b0b12`, mint `#00ffcc`, ink `#c8c8e0`, circle `#3a6d8c`,
  spoke `#4d7a99`, grid `#333355`
- Animation: 30 fps, glow underlay + bright trail line + white pen tip
- Python `main.py` writes files with the Agg backend (no blocking window)

## Roadmap — web app (`web/`)

| Milestone | Feature |
|-----------|---------|
| W1 | Canvas + `requestAnimationFrame` loop (60 fps, `devicePixelRatio` crisp) |
| W2 | Port `dft.js`; verify outputs match the Python numbers |
| W3 | Epicycles + glow/fading trail + pen tip |
| W4 | `N` term slider — watch accuracy live, show error |
| W5 | Mouse drawing → record path → FFT |
| W6 | Presets, share/export, deploy to GitHub Pages |

## Working style (important)

The user chose **Mode B**: explain the existing code carefully, block by block.
They are learning, not just shipping. Do not dump giant unexplained code; explain
the "why" of each part and tie it back to the math. When building new code,
favor small, reviewable steps and keep the animation quality high.

## Session log (newest first)

### 2026-10-21 — Error-target mode: `--target-error`, `auto` / `strict`
- User wanted error **< 0.1 %**. Rather than hardcode N, the panel term
  counts are now derived from the shape's **actual error curve**.
- New `fourier.py::relative_error_curve` → error % for every term count in
  one O(N) pass, via Parseval: `RMSE(t)² = Σ_{k≥t} |c_k|²` (valid because
  the coefficients are sorted by |c|). Verified against the direct
  reconstruction to **9e-14 across all 512 term counts × 4 shapes**. Being a
  running tail total, the curve is **monotonically non-increasing**, which is
  what makes the "smallest N under target" search exact.
- New `fourier.py::select_terms(points, coeffs, freqs, target_pct, count,
  strict)`. `strict=False` → ladder of powers of two whose **last** panel is
  the first to beat the target. `strict=True` → ladder where **every** panel
  beats it (with a 5 % safety margin so the printed number is not on the
  boundary).
- CLI: `--panels` is now `nargs="?"` — bare or `auto` = target-driven,
  `strict` = every panel under target, anything else = explicit list.
  New `--target-error PCT` (default 0.1) and `--panel-count N` (default 4).
- **Fixed a display bug**: `format_pct` now adapts precision. Rounding
  0.0996 % to 2 decimals printed "0.10 %", which *reads* as not under a
  0.1 % target. Small errors now keep 4–5 digits.
- At the 0.1 % target — crown: auto N = 32/64/128/256 → 0.984/0.382/0.133/
  **0.0438 %**; strict N = 158/199/251/316 → **0.0944/0.0660/0.0453/0.0274 %**.
  star: strict N = 35/44/56/70. heart: strict N = 8/10/13/16 (all 0.0000 %).
  infinity: strict N = 16/20/25/32.
- Also fixed a bug found during verification: the tail-energy formula needs
  `cumsum(sq[::-1])[::-1]`, not `cumsum(sq)[::-1]` — the latter silently
  computes the *head* sum and made every shape resolve to N = 512.
- Verified: 240 combinations (4 shapes × 6 targets × 5 counts × 2 modes) all
  keep their error guarantee, stay sorted, in range and duplicate-free.
- `--panels strict` now writes to `<shape>_panels_strict.gif/.mp4` so it does
  not overwrite the `auto` output; new `--tag NAME` for any other suffix.
- Final artefact check (0 failures): printed label == `format_pct(real error)`
  for all 8 shape×mode combos; pen tip == `reconstruct()` to 1e-12 in all
  panels; frozen circles byte-identical at θ=0 vs θ=2.1 while animated ones
  move; every GIF 1600×500 × 100 frames, every MP4 h264/yuv420p.

### 2026-10-21 — Multi-panel mode (`--panels`): GIF + MP4, frozen main circles
- **New mode** `python main.py --shape crown --panels 2,8,32,128` draws the
  same shape in 4 panels, one per N, each with its own epicycle chain, trail
  and pen tip. Writes **both** `output/<shape>_panels.gif` and `.mp4`.
- New file `python/panels.py` (build_figure + plot_panels). `build_figure` is
  split out so artist state is inspectable in tests without writing files.
- New `fourier.py::relative_error` → error % = `100 * RMSE / RMS radius of the
  true outline`, so the number is comparable across shapes. Crown: N=2 → 28.70 %,
  N=8 → 7.57 %, N=32 → 0.98 %, N=128 → 0.13 %.
- `--freeze N` (default 2) holds the **two largest circles static** (dashed,
  brighter `#7fb8d4`); `--freeze 0` gives the classic all-spinning look.
  **The freeze is visual only** — the pen still traces the exact N-term
  reconstruction, so the printed error is the true error.
- **Measured and rejected** the alternative: freezing the two biggest terms'
  *contribution* gives ~150 % error at every N and never improves (the two
  biggest terms are the low-frequency ones carrying size/position). It must
  stay in the rendering, not the maths.
- Labels under every graph (`N = 32` in mint + `Error = 0.98 %` in ink) were
  also added to the existing `--static` PNG for consistency.
- MP4 needs **no system ffmpeg**: `imageio-ffmpeg` ships its own binary inside
  the venv and `panels.py` points matplotlib at it via
  `matplotlib.rcParams["animation.ffmpeg_path"]`. Added `imageio`,
  `imageio-ffmpeg` to the venv and a new `requirements.txt`.
- Verified programmatically: frozen circles never move, animated circles do,
  pen tip == `reconstruct()` to 1e-12 in every panel, MP4 is h264/yuv420p
  1600×500 @30fps, GIF is 1600×500 × 100 frames.

### 2026-10-21 — EXPLANATION.md rewrite: `.venv` documented
- Rewrote `EXPLANATION.md` (446 → ~560 lines). Main gap fixed: **`.venv` was
  never mentioned** in the repo layout.
- New section 3 "The virtual environment (`.venv`)" covers: what a venv solves,
  that it lives at the **repo root** (not `python/`), full internal anatomy
  (`pyvenv.cfg`, `Scripts/`, `Lib/site-packages/`, `Include/`, `share/`,
  internal `.gitignore`), the exact installed package list with versions, how
  to detect the venv via `sys.prefix != sys.base_prefix`, activation, the
  `..\.venv\Scripts\python.exe` shortcut, full rebuild procedure, and a table of
  common venv failure modes.
- Added: table of contents, end-to-end data-flow diagram (shapes → fourier →
  main), repo-layout table with Git-tracked status per folder, per-shape RMSE
  comparison table (crown/star/heart/infinity at 1/3/8/20/60 terms), the first
  8 crown circles with measured radii + frequencies + start angles, expanded
  `_resample_polygon` walkthrough, output-file reference table, expanded
  troubleshooting table.
- **Fixed a real bug in `README.md`**: it said to create the venv inside
  `python/` (`cd python; python -m venv .venv`), which contradicts the actual
  layout. Now documents the repo-root venv and `..\.venv\Scripts\python.exe`.
- All RMSE numbers re-measured from current code and confirmed unchanged.
- Verified every documented command runs: `--static`, `--animate`, the
  `..\.venv\Scripts\python.exe` form, and the activation form.

### 2026-10-20 — Python prototype + code walkthrough
- Built the Python prototype: `python/shapes.py`, `python/fourier.py`,
  `python/main.py`. Committed `1412638`, pushed to `origin/main`.
- Verified numerically: crown RMSE falls 0.34 → 0.000000 as terms go 1 → 512.
  Generated `output/crown_static.png` and `output/crown_epicycles.gif`.
- Created this `AGENTS.md` (commit `bf98df4`).
- **Walked the user through all three Python files line by line (Mode B).**
  Covered: arc-length resampling, complex-signal DFT trick, `fft/N` vs `fftfreq`,
  sort-by-|c| optimality, `reconstruct` vs `chain` (pen tip vs joints),
  RMSE at matching thetas, artist-reuse animation performance.
- **Next up:** user was choosing between (A) small exercises to cement the math,
  or (B) starting the `web/` app. Nothing in `web/` exists yet; `test.js` is still
  an empty leftover. Do not regress the verified math above.
