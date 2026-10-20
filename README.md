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
python/           # prototype: prove the math
  shapes.py       # crown, star, heart, infinity
  fourier.py      # DFT, reconstruction, chain, error
  main.py         # static comparison + GIF animation
web/              # polished interactive app (coming next)
```

## Run the Python prototype

```powershell
cd python
python -m venv .venv
.\.venv\Scripts\pip install numpy matplotlib

# compare 3 / 8 / 20 / 60 terms
.\.venv\Scripts\python main.py --shape crown --static

# spinning epicycles -> output/crown_epicycles.gif
.\.venv\Scripts\python main.py --shape crown --animate --terms 32 --frames 100
```

Output goes to `output/`.

## The math in one line

Treat the outline as `z = x + iy`, take `np.fft.fft(z)/N`, and the coefficients
are the radii + phases of the circles. Keeping the largest `|c_k|` gives the
best approximation for a given number of circles.
