# Drawing-Equation — Fourier Epicycles

Draw any shape with rotating circles. Every closed curve can be rebuilt from a
sum of spinning motions:

```
        N
x(t) =  Σ  ( a_k·cos(kt) + b_k·sin(kt) )
       k=1

        N
y(t) =  Σ  ( c_k·cos(kt) + d_k·sin(kt) )
       k=1
```

More terms `N` → higher accuracy. This project finds the coefficients from a
real shape (via the DFT) and animates the circles that draw it.

## Layout

```
.venv/            # virtual environment (numpy + matplotlib) — repo root, git-ignored
output/           # generated PNG/GIFs — git-ignored
python/           # prototype: prove the math
  shapes.py       # crown, star, heart, infinity
  fourier.py      # DFT, reconstruction, chain, error
  main.py         # static comparison + GIF animation
web/              # polished interactive app (coming next)
```

## Run the Python prototype

The virtual environment lives at the **repo root** (`.venv/`), not inside
`python/`. To create it from scratch:

```powershell
cd Drawing-Equation
C:\Python315\python.exe -m venv .venv
.\.venv\Scripts\pip install numpy matplotlib
```

Then run the prototype:

```powershell
cd python

# compare 3 / 8 / 20 / 60 terms
..\.venv\Scripts\python main.py --shape crown --static

# spinning epicycles -> output/crown_epicycles.gif
..\.venv\Scripts\python main.py --shape crown --animate --terms 32 --frames 100
```

Output goes to `output/`.

## The multi-panel animation

Draw the **same shape four times at once**, each panel using a different
number of Fourier terms, so you can watch the approximation tighten:

```powershell
..\.venv\Scripts\python main.py --shape crown --panels 2,8,32,128
```

Each panel carries its term count and error percentage under the graph:

```
N = 32
Error = 0.98 %
```

You get **both** a GIF and an MP4 in `output/` — no system ffmpeg needed,
because `imageio-ffmpeg` ships its own binary inside the venv.

| Flag | Meaning | Default |
|---|---|---|
| `--panels N,N,N` | multi-panel animation; the list of term counts | off |
| `--freeze N` | how many of the largest circles are drawn **static** | `2` |

The two largest circles are held still (dashed) so the shape's skeleton stays
anchored while the smaller circles spin. The freeze is visual only — the pen
still traces the exact N-term reconstruction, so the error shown is real.

> **New to virtual environments?** See
> [EXPLANATION.md → The virtual environment](EXPLANATION.md#the-virtual-environment-venv)
> for what `.venv/` actually contains and how to activate it.

## The math in one line

Treat the outline as `z = x + iy`, take `np.fft.fft(z)/N`, and the coefficients
are the radii + phases of the circles. Keeping the largest `|c_k|` gives the
best approximation for a given number of circles.
