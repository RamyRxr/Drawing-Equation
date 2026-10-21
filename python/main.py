"""Fourier drawing prototype — watch a shape emerge from rotating circles.

Examples
--------
Compare how 3 / 8 / 20 / 60 terms approximate a crown:

    python main.py --shape crown --static

Render the spinning-epicycle animation to a GIF:

    python main.py --shape crown --animate --terms 32 --frames 100

Both at once:

    python main.py --shape star --static --animate
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files; no blocking window

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Circle

from fourier import chain, coefficients, reconstruct, relative_error, rmse
from panels import plot_panels
from shapes import SHAPES

OUT = Path(__file__).resolve().parent.parent / "output"

BG = "#0b0b12"
GRID = "#333355"
INK = "#c8c8e0"
MINT = "#00ffcc"
CIRCLE = "#3a6d8c"
SPOKE = "#4d7a99"


def _bare_axes(ax, lim: float, title: str) -> None:
    ax.set_facecolor(BG)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    if title:
        ax.set_title(title, color=INK, fontsize=10)


def plot_static(points, coeffs, freqs, term_options, shape_name: str) -> Path:
    n = len(points)
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    true = points[:, 0] + 1j * points[:, 1]
    lim = float(np.max(np.abs(points))) * 1.15

    fig, axes = plt.subplots(1, len(term_options), figsize=(4 * len(term_options), 4.8))
    fig.patch.set_facecolor(BG)

    for ax, terms in zip(np.atleast_1d(axes), term_options):
        approx = reconstruct(coeffs, freqs, theta, terms)
        err = relative_error(points, coeffs, freqs, terms)
        _bare_axes(ax, lim, f"RMSE {rmse(points, coeffs, freqs, terms):.4f}")
        ax.plot(true.real, true.imag, "--", color=GRID, lw=1.2)
        ax.plot(approx.real, approx.imag, color=MINT, lw=2.2)

        # Same under-graph labels as the multi-panel animation.
        ax.text(0.5, -0.075, f"N = {terms}", transform=ax.transAxes, ha="center",
                va="top", color=MINT, fontsize=14, fontweight="bold")
        ax.text(0.5, -0.135, f"Error = {err:.2f} %", transform=ax.transAxes, ha="center",
                va="top", color=INK, fontsize=10)

    fig.suptitle(f"Fourier reconstruction — {shape_name}", color="white", fontsize=13)
    fig.tight_layout()
    out = OUT / f"{shape_name}_static.png"
    fig.savefig(out, dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


def plot_animation(points, coeffs, freqs, shape_name: str, terms: int, frames: int) -> Path:
    true = points[:, 0] + 1j * points[:, 1]
    lim = float(np.max(np.abs(points))) * 1.18
    m = min(terms, len(coeffs))

    fig, ax = plt.subplots(figsize=(6.4, 6.4))
    fig.patch.set_facecolor(BG)
    _bare_axes(ax, lim, f"{shape_name} — {m} epicycles")
    ax.plot(true.real, true.imag, ":", color=GRID, lw=1)

    circles = [Circle((0, 0), 0, fill=False, color=CIRCLE, lw=0.8, alpha=0.7) for _ in range(m)]
    for c in circles:
        ax.add_patch(c)
    spokes = [ax.plot([], [], color=SPOKE, lw=0.8, alpha=0.65)[0] for _ in range(m)]

    glow, = ax.plot([], [], color=MINT, lw=5, alpha=0.16)
    trail, = ax.plot([], [], color=MINT, lw=1.8)
    tip, = ax.plot([], [], "o", color="white", ms=4)

    xs: list[float] = []
    ys: list[float] = []

    def update(frame: int):
        t = 2 * np.pi * frame / frames
        joints = chain(coeffs, freqs, t, m)
        prev = 0 + 0j
        for i, joint in enumerate(joints):
            circles[i].set_center((prev.real, prev.imag))
            circles[i].set_radius(abs(coeffs[i]))
            spokes[i].set_data([prev.real, joint.real], [prev.imag, joint.imag])
            prev = joint

        xs.append(joints[-1].real)
        ys.append(joints[-1].imag)
        glow.set_data(xs, ys)
        trail.set_data(xs, ys)
        tip.set_data([joints[-1].real], [joints[-1].imag])
        return (*circles, *spokes, glow, trail, tip)

    anim = FuncAnimation(fig, update, frames=frames, interval=1000 / 30, blit=False)
    out = OUT / f"{shape_name}_epicycles.gif"
    anim.save(out, writer=PillowWriter(fps=30))
    plt.close(fig)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Fourier drawing prototype")
    ap.add_argument("--shape", default="crown", choices=sorted(SHAPES))
    ap.add_argument("--static", action="store_true", help="save an N-terms comparison image")
    ap.add_argument("--animate", action="store_true", help="save the epicycle animation as GIF")
    ap.add_argument("--terms", type=int, default=32, help="epicycles used in the animation")
    ap.add_argument("--frames", type=int, default=100, help="frames in one full loop")
    ap.add_argument(
        "--panels",
        type=str,
        default=None,
        metavar="N,N,N",
        help="multi-panel animation: comma-separated term counts, e.g. 2,8,32,128",
    )
    ap.add_argument(
        "--freeze",
        type=int,
        default=2,
        help="how many of the largest circles are drawn static (0 = every circle spins)",
    )
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    points = SHAPES[args.shape]()
    coeffs, freqs = coefficients(points)

    if args.panels:
        term_list = [int(x) for x in args.panels.replace(" ", "").split(",") if x]
        for out in plot_panels(
            points, coeffs, freqs, args.shape, term_list, args.frames, args.freeze, OUT
        ):
            print(f"saved {out}")

    if args.static or (not args.animate and not args.panels):
        out = plot_static(points, coeffs, freqs, [3, 8, 20, 60], args.shape)
        print(f"saved {out}")
    if args.animate:
        out = plot_animation(points, coeffs, freqs, args.shape, args.terms, args.frames)
        print(f"saved {out}")


if __name__ == "__main__":
    main()
