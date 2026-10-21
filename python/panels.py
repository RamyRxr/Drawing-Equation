"""Multi-panel epicycle animation: one shape, several term counts at once.

Every panel draws the *same* outline with a different number of Fourier
terms, so you can watch the approximation tighten left to right while the
spinning circles do the work.

    python main.py --shape crown --panels 2,8,32,128

Under each panel it prints the term count and the reconstruction error as a
percentage of the shape's size.

The two largest circles can be drawn **static** (``--freeze 2``, the default):
they are held at their t=0 pose while every smaller circle spins. That keeps
the skeleton of the shape visually anchored. The freeze is purely cosmetic --
the pen still traces the exact N-term reconstruction, so the error shown under
each panel is the true error. Use ``--freeze 0`` for the classic look where
every circle spins.

Two files are written: a GIF (via Pillow) and an MP4 (via ffmpeg, using the
binary bundled with ``imageio-ffmpeg`` so no system install is needed).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter
from matplotlib.patches import Circle

from fourier import chain, relative_error_curve

BG = "#0b0b12"
GRID = "#333355"
INK = "#c8c8e0"
MINT = "#00ffcc"
CIRCLE = "#3a6d8c"
SPOKE = "#4d7a99"
FROZEN = "#7fb8d4"  # brighter tint for the circles that are held still

FPS = 30


def format_pct(value: float) -> str:
    """Format an error percentage so the target comparison is unambiguous.

    Rounding 0.0996 % to two decimals gives "0.10 %", which *reads* as not
    being under a 0.1 % target even though it is. So the precision adapts:
    small numbers keep enough digits to be judged correctly.
    """
    if value == 0:
        return "0.000 %"
    if value < 0.001:
        return f"{value:.5f} %"
    if value < 0.1:
        return f"{value:.4f} %"
    if value < 10:
        return f"{value:.3f} %"
    return f"{value:.2f} %"


def _blank_axes(ax, lim: float) -> None:
    ax.set_facecolor(BG)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def _frozen_pose(coeffs: np.ndarray, freqs: np.ndarray, terms: int) -> np.ndarray:
    """Chain positions at theta = 0 -- the pose the static circles are held in."""
    return chain(coeffs, freqs, 0.0, terms)


def build_figure(
    points: np.ndarray,
    coeffs: np.ndarray,
    freqs: np.ndarray,
    shape_name: str,
    term_list: list[int],
    freeze: int,
    target_error: float | None = None,
):
    """Build the multi-panel figure and return ``(fig, panels)``.

    Kept separate from :func:`plot_panels` so the artist state can be
    inspected in tests without rendering anything to disk.
    """
    true = points[:, 0] + 1j * points[:, 1]
    lim = float(np.max(np.abs(points))) * 1.18
    terms = [min(max(int(t), 1), len(coeffs)) for t in term_list]
    curve = relative_error_curve(points, coeffs)
    errors = [float(curve[t]) for t in terms]

    fig, axes = plt.subplots(1, len(terms), figsize=(4.0 * len(terms), 5.0))
    axes = np.atleast_1d(axes)
    fig.patch.set_facecolor(BG)

    panels: list[dict] = []

    for ax, m, err in zip(axes, terms, errors):
        _blank_axes(ax, lim)
        ax.plot(true.real, true.imag, ":", color=GRID, lw=1.0)

        n_frozen = min(freeze, m)

        circles = []
        for i in range(m):
            is_frozen = i < n_frozen
            circle = Circle(
                (0, 0),
                0,
                fill=False,
                color=FROZEN if is_frozen else CIRCLE,
                lw=1.2 if is_frozen else 0.8,
                alpha=0.85 if is_frozen else 0.5,
                linestyle="--" if is_frozen else "-",
            )
            ax.add_patch(circle)
            circles.append(circle)

        spokes = [ax.plot([], [], color=SPOKE, lw=0.8, alpha=0.6)[0] for _ in range(m)]
        glow, = ax.plot([], [], color=MINT, lw=5, alpha=0.16)
        trail, = ax.plot([], [], color=MINT, lw=1.8)
        tip, = ax.plot([], [], "o", color="white", ms=4)

        # The two labels the user asked for, sitting under the graph.
        ax.text(
            0.5,
            -0.075,
            f"N = {m}",
            transform=ax.transAxes,
            ha="center",
            va="top",
            color=MINT,
            fontsize=14,
            fontweight="bold",
        )
        ax.text(
            0.5,
            -0.135,
            f"Error = {format_pct(err)}",
            transform=ax.transAxes,
            ha="center",
            va="top",
            color=INK,
            fontsize=10,
        )

        panels.append(
            {
                "ax": ax,
                "m": m,
                "n_frozen": n_frozen,
                "circles": circles,
                "spokes": spokes,
                "glow": glow,
                "trail": trail,
                "tip": tip,
                "xs": [],
                "ys": [],
            }
        )

    subtitle = f"  ({freeze} main circles held static)" if freeze else ""
    if target_error is not None:
        subtitle += f"  •  error target < {target_error:g} %"
    fig.suptitle(
        f"Fourier epicycles — {shape_name}{subtitle}",
        color="white",
        fontsize=14,
        y=0.99,
    )
    fig.subplots_adjust(left=0.02, right=0.98, top=0.90, bottom=0.18, wspace=0.10)
    return fig, panels


def plot_panels(
    points: np.ndarray,
    coeffs: np.ndarray,
    freqs: np.ndarray,
    shape_name: str,
    term_list: list[int],
    frames: int,
    freeze: int,
    out_dir: Path,
    target_error: float | None = None,
    tag: str = "",
) -> list[Path]:
    """Render the multi-panel animation and return the files written.

    ``tag`` is inserted into the file name (``crown_panels.gif`` ->
    ``crown_panels_strict.gif``) so different modes can live side by side.
    """
    fig, panels = build_figure(
        points, coeffs, freqs, shape_name, term_list, freeze, target_error
    )

    def reset() -> None:
        for panel in panels:
            panel["xs"].clear()
            panel["ys"].clear()

    def update(frame: int):
        theta = 2 * np.pi * frame / frames
        for panel in panels:
            m = panel["m"]
            n_frozen = panel["n_frozen"]
            joints = chain(coeffs, freqs, theta, m)
            frozen = _frozen_pose(coeffs, freqs, m) if n_frozen else None

            for i in range(m):
                if i < n_frozen:
                    # Held still: centre and rim both come from the t=0 pose.
                    centre = 0 + 0j if i == 0 else frozen[i - 1]
                    rim = frozen[i]
                else:
                    centre = joints[i - 1]
                    rim = joints[i]
                panel["circles"][i].set_center((centre.real, centre.imag))
                panel["circles"][i].set_radius(abs(coeffs[i]))
                panel["spokes"][i].set_data(
                    [centre.real, rim.real], [centre.imag, rim.imag]
                )

            tip_pos = joints[-1]
            panel["xs"].append(tip_pos.real)
            panel["ys"].append(tip_pos.imag)
            panel["glow"].set_data(panel["xs"], panel["ys"])
            panel["trail"].set_data(panel["xs"], panel["ys"])
            panel["tip"].set_data([tip_pos.real], [tip_pos.imag])
        return []

    written: list[Path] = []

    # --- GIF -------------------------------------------------------------
    gif_path = out_dir / f"{shape_name}_panels{tag}.gif"
    anim = FuncAnimation(fig, update, frames=frames, interval=1000 / FPS, blit=False)
    anim.save(gif_path, writer=PillowWriter(fps=FPS))
    written.append(gif_path)

    # --- MP4 -------------------------------------------------------------
    # imageio-ffmpeg ships its own ffmpeg binary, so point matplotlib at that
    # instead of requiring ffmpeg on the user's PATH.
    try:
        import imageio_ffmpeg

        matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
        reset()
        mp4_path = out_dir / f"{shape_name}_panels{tag}.mp4"
        anim2 = FuncAnimation(fig, update, frames=frames, interval=1000 / FPS, blit=False)
        anim2.save(
            mp4_path,
            writer=FFMpegWriter(
                fps=FPS,
                codec="libx264",
                extra_args=["-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20"],
            ),
        )
        written.append(mp4_path)
    except Exception as exc:  # pragma: no cover - depends on the environment
        print(f"skipped MP4 ({exc.__class__.__name__}: {exc})")

    plt.close(fig)
    return written
