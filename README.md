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
  panels.py       # multi-panel animation (GIF + MP4)
  sequence.py     # two-group animation: x(t) chain + y(t) chain -> one pen
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
..\.venv\Scripts\python main.py --shape crown --panels
```

The term counts are derived from the shape's real error curve, so the last
panel always lands **under the error target** (0.1 % by default). Each panel
carries its term count and error percentage under the graph:

```
N = 256
Error = 0.0438 %
```

You get **both** a GIF and an MP4 in `output/` — no system ffmpeg needed,
because `imageio-ffmpeg` ships its own binary inside the venv.

| Flag | Meaning | Default |
|---|---|---|
| `--panels [LIST]` | `auto`/bare picks N from the error target; `strict` makes **every** panel beat it; a list uses exactly those N | off |
| `--target-error PCT` | the error target in percent | `0.1` |
| `--panel-count N` | how many panels to create | `4` |
| `--freeze N` | how many of the largest circles are drawn **static** | `2` |
| `--tag NAME` | suffix for the output file names | off |

At the 0.1 % target, the crown lands on N = 32, 64, 128, 256 (errors 0.984 %,
0.382 %, 0.133 %, **0.0438 %**). With `--panels strict` *every* panel beats the
target: N = 158, 199, 251, 316 → 0.0944 %, 0.0660 %, 0.0453 %, 0.0274 %. That
run writes to `crown_panels_strict.gif` / `.mp4` so it does not overwrite the
`auto` version.

The two largest circles are held still (dashed) so the shape's skeleton stays
anchored while the smaller circles spin. The freeze is visual only — the pen
still traces the exact N-term reconstruction, so the error shown is real.

> **New to virtual environments?** See
> [EXPLANATION.md → The virtual environment](EXPLANATION.md#the-virtual-environment-venv)
> for what `.venv/` actually contains and how to activate it.

## The two-group animation

`--panels` shows *how accurate* the shape is at a given N. `--sequence` shows
*how the two halves of the formula build it*: an `x(t)` group of circles and a
`y(t)` group, separated, driving a single pen.

```powershell
..\.venv\Scripts\python main.py --shape crown --sequence
```

```
|  x(t) chain  |   THE DRAWING   |  y(t) chain  |
```

- The **left** panel is the epicycle chain of the real signal `x(t)` — its tip
  slides along the horizontal axis.
- The **right** panel is the same for `y(t)`, turned a quarter turn so its tip
  slides up and down the vertical axis.
- The **middle** panel is the pen at `(x(t), y(t))` drawing the shape, with a
  dashed line from each group's tip to the pen.

Under the drawing the two formulas are printed with the current step's `N` and
error percentage, and they are *literally* the series being evaluated:

```
Step 2 / 4     N = 15     Error = 1.3790 %
x(t) =  Σ  ( a_k·cos(kt) + b_k·sin(kt) )
y(t) =  Σ  ( c_k·cos(kt) + d_k·sin(kt) )
```

The animation walks through four N values and stops at the first one whose
error is under the target (0.1 % by default) — for the crown:
6, 15, 40, 102 → 4.55 %, 1.38 %, 0.35 %, **0.09 %**.

| Flag | Meaning | Default |
|---|---|---|
| `--sequence` | two-group animation | off |
| `--step-count N` | how many N steps to walk through | `4` |
| `--target-error PCT` | the error target in percent | `0.1` |
| `--frames N` | frames **per step** | `100` |
| `--tag NAME` | suffix for the output file names | off |

## The math in one line

Treat the outline as `z = x + iy`, take `np.fft.fft(z)/N`, and the coefficients
are the radii + phases of the circles. Keeping the largest `|c_k|` gives the
best approximation for a given number of circles.
