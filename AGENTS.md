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
├── README.md
├── .gitignore         ← ignores .venv/, __pycache__/, output/
├── python/
│   ├── shapes.py      ← crown, star, heart, infinity; arc-length resampling
│   ├── fourier.py     ← DFT coefficients, reconstruct, chain, rmse
│   └── main.py        ← CLI: static comparison PNG + epicycle GIF
├── output/            ← generated files (git-ignored)
│   ├── crown_static.png
│   └── crown_epicycles.gif
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
```

`--shape` ∈ {crown, star, heart, infinity} · `--terms` = epicycle count ·
`--frames` = frames per loop. Output goes to `output/`.

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
