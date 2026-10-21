"""The sequence animation: two circle groups driving one pen, step by step.

The picture has three panels side by side:

    |  x(t) chain  |   THE DRAWING   |  y(t) chain  |

- **Left** -- the epicycle chain of the *real* signal ``x(t)``. Because the
  ``+k`` and ``-k`` circles are drawn as a pair, the running total stays
  real, so the chain's tip slides along the horizontal axis at ``x(t)``.
- **Right** -- the same construction for ``y(t)``, turned a quarter turn so
  its tip slides up and down the vertical axis at ``y(t)``.
- **Middle** -- the pen at ``(x(t), y(t))`` tracing the shape.

A dashed line runs from each chain's tip to the pen, so you can see the two
groups feed the same drawing: the x value sets the pen's column, the y value
sets its row.

The animation walks through four term counts ``[start, mid1, mid2, end]``,
where ``end`` is the smallest N whose error is under the target. The current
step's ``N`` and error percentage are printed under the drawing, next to the
two formulas that are being evaluated.

    python main.py --shape crown --sequence
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

from fourier import harmonic_chains, harmonic_error_curve

BG = "#0b0b12"
GRID = "#333355"
INK = "#c8c8e0"
MINT = "#00ffcc"
SPOKE = "#4d7a99"
XCOL = "#ff9d5c"  # the x(t) group
YCOL = "#7fb8d4"  # the y(t) group

FPS = 30

FORMULAS = (
    "x(t) =  Σ  ( a_k·cos(kt) + b_k·sin(kt) )\n"
    "y(t) =  Σ  ( c_k·cos(kt) + d_k·sin(kt) )"
)


def pick_steps(
    points: np.ndarray,
    coeffs: np.ndarray,
    freqs: np.ndarray,
    target_pct: float = 0.1,
    count: int = 4,
) -> list[int]:
    """Pick ``[start, mid1, mid2, end]`` harmonic counts.

    ``end`` is the smallest N whose error is comfortably under the target (a
    5 % margin keeps the printed number off the boundary). The other three
    are spread geometrically from a small, visibly rough start up to ``end``.
    """
    curve = harmonic_error_curve(points, coeffs, freqs)
    n = len(curve) - 1

    margin = target_pct * 0.95
    qualifying = np.nonzero(curve[1:] < margin)[0]
    end = int(qualifying[0]) + 1 if len(qualifying) else n

    if count <= 1 or end <= 1:
        return [end]

    # Start low enough that the first step is visibly rough, but high enough
    # that the shape is still recognisable.
    start = max(2, min(end, end // 16))
    if end <= start:
        return [end]

    ladder = [
        int(round(start * (end / start) ** (i / (count - 1)))) for i in range(count)
    ]
    ladder[-1] = end
    ladder = sorted(set(ladder))

    # Keep exactly `count` distinct values, all below `end` except the last.
    while len(ladder) < count:
        gaps = [
            (ladder[i + 1] - ladder[i], i) for i in range(len(ladder) - 1)
        ]
        if not gaps or max(gaps)[0] <= 1:
            ladder.insert(0, max(1, ladder[0] - 1))
        else:
            gap, i = max(gaps)
            ladder.insert(i + 1, (ladder[i] + ladder[i + 1]) // 2)
    return ladder[:count]


def _style_axes(ax, lim: float) -> None:
    ax.set_facecolor(BG)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def _make_chain(ax, count: int, color: str):
    """Create the circle + spoke artists for one chain panel."""
    circles = []
    spokes = []
    for _ in range(count):
        patch = Circle((0, 0), 0, fill=False, color=color, lw=0.8, alpha=0.6)
        ax.add_patch(patch)
        circles.append(patch)
        spokes.append(ax.plot([], [], color=SPOKE, lw=0.8, alpha=0.6)[0])
    return circles, spokes


def _write_gif_from_mp4(mp4_path: Path, gif_path: Path, fps: int = FPS) -> bool:
    """Turn the finished MP4 into a GIF with one ffmpeg pass.

    Rendering the frames once and converting afterwards keeps the memory
    use flat; a GIF written straight from matplotlib has to hold every
    frame in RAM at the same time.
    """
    try:
        import subprocess

        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        vf = (
            f"fps={fps},split[a][b];"
            "[a]palettegen=max_colors=256[p];"
            "[b][p]paletteuse=dither=bayer:bayer_scale=3"
        )
        subprocess.run(
            [exe, "-y", "-loglevel", "error", "-i", str(mp4_path), "-vf", vf,
             "-loop", "0", str(gif_path)],
            check=True,
        )
        return gif_path.exists()
    except Exception:  # pragma: no cover - depends on the environment
        return False


def plot_sequence(
    points: np.ndarray,
    coeffs: np.ndarray,
    freqs: np.ndarray,
    shape_name: str,
    frames: int,
    out_dir: Path,
    target_error: float = 0.1,
    step_count: int = 4,
    tag: str = "",
) -> list[Path]:
    """Render the sequence animation and return the files written."""
    true = points[:, 0] + 1j * points[:, 1]
    steps = pick_steps(points, coeffs, freqs, target_error, step_count)
    errors = list(harmonic_error_curve(points, coeffs, freqs)[steps])

    # Pre-compute both chains for every step, all frames at once.
    chains = []
    for m in steps:
        x_chain, y_chain = harmonic_chains(coeffs, freqs, m, frames)
        # The y chain is turned a quarter turn so its tip runs up the
        # vertical axis instead of along the horizontal one.
        chains.append((x_chain, 1j * y_chain))

    # One camera limit for every panel, so the layout never jumps and the
    # two chains stay lined up with the drawing.
    reach = 0.0
    for x_chain, y_chain in chains:
        for arr in (x_chain, y_chain):
            reach = max(reach, float(np.max(np.abs(arr))))
    lim = max(reach, float(np.max(np.abs(true)))) * 1.12
    # Circles below ~1.5 px are invisible, so skipping them speeds the
    # render up a lot once N gets large, without changing a visible pixel.
    min_radius = lim * 0.008

    fig = plt.figure(figsize=(15.0, 8.4), dpi=100)
    fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(
        2, 3, height_ratios=[3.0, 1.05], width_ratios=[1, 1, 1], hspace=0.16, wspace=0.16
    )
    ax_x = fig.add_subplot(gs[0, 0])
    ax_draw = fig.add_subplot(gs[0, 1])
    ax_y = fig.add_subplot(gs[0, 2])
    ax_info = fig.add_subplot(gs[1, :])
    ax_info.axis("off")

    for ax in (ax_x, ax_draw, ax_y):
        _style_axes(ax, lim)

    ax_x.set_title("x(t)  chain", color=XCOL, fontsize=12)
    ax_y.set_title("y(t)  chain", color=YCOL, fontsize=12)
    ax_draw.set_title("the drawing", color=INK, fontsize=12)

    # The true outline only belongs in the drawing panel.
    ax_draw.plot(true.real, true.imag, ":", color=GRID, lw=1.1)

    max_circles = 2 * max(steps) + 1
    x_circles, x_spokes = _make_chain(ax_x, max_circles, XCOL)
    y_circles, y_spokes = _make_chain(ax_y, max_circles, YCOL)

    # Accumulates every step (dim) so the improvement stays visible, plus the
    # current step only (bright) so each drawing is seen cleanly.
    glow_all, = ax_draw.plot([], [], color=MINT, lw=6, alpha=0.07)
    trail_all, = ax_draw.plot([], [], color=MINT, lw=1.4, alpha=0.30)
    glow_now, = ax_draw.plot([], [], color=MINT, lw=6, alpha=0.18)
    trail_now, = ax_draw.plot([], [], color=MINT, lw=2.0)
    tip, = ax_draw.plot([], [], "o", color="white", ms=5)

    x_tip, = ax_x.plot([], [], "o", color=XCOL, ms=5)
    y_tip, = ax_y.plot([], [], "o", color=YCOL, ms=5)

    # Dashed connectors: chain tip -> pen.
    link_x = Line2D([], [], color=XCOL, lw=1.1, ls="--", alpha=0.6, transform=fig.transFigure)
    link_y = Line2D([], [], color=YCOL, lw=1.1, ls="--", alpha=0.6, transform=fig.transFigure)
    fig.add_artist(link_x)
    fig.add_artist(link_y)

    step_text = ax_info.text(
        0.5, 0.86, "", transform=ax_info.transAxes, ha="center", va="center",
        color=MINT, fontsize=17, fontweight="bold",
    )
    # Both formulas in a single text artist: every text artist costs a
    # re-layout and a re-raster on every single frame.
    ax_info.text(
        0.5, 0.48, FORMULAS, transform=ax_info.transAxes, ha="center", va="center",
        color=INK, fontsize=13, family="monospace", linespacing=1.7,
    )
    history_text = ax_info.text(
        0.5, 0.12, "", transform=ax_info.transAxes, ha="center", va="center",
        color=INK, fontsize=11, family="monospace",
    )
    # Kept inside the panels: text placed below an axes can be clipped once
    # `set_aspect("equal")` shrinks the axes box.
    value_x = ax_x.text(
        0.04, 0.96, "", transform=ax_x.transAxes, ha="left", va="top",
        color=XCOL, fontsize=14, fontweight="bold",
    )
    value_y = ax_y.text(
        0.04, 0.96, "", transform=ax_y.transAxes, ha="left", va="top",
        color=YCOL, fontsize=14, fontweight="bold",
    )

    fig.suptitle(
        f"Fourier epicycles — {shape_name}   (error target < {target_error:g} %)",
        color="white", fontsize=15, y=0.985,
    )

    total_frames = frames * len(steps)
    all_x: list[float] = []
    all_y: list[float] = []
    now_x: list[float] = []
    now_y: list[float] = []
    fig_w, fig_h = fig.get_size_inches() * fig.dpi

    # Every string that only changes once per step is precomputed here, so the
    # render loop never has to rebuild (and re-lay-out) them.
    step_lines = []
    history_lines = []
    for i, (m, err) in enumerate(zip(steps, errors)):
        marker = "  ← current" if i < len(steps) - 1 else "  ← best"
        step_lines.append(
            f"Step {i + 1} / {len(steps)}     N = {m}     Error = {err:.4f} %{marker}"
        )
        history_lines.append(
            "   ".join(
                f"{'✓' if j < i else '•'} N={steps[j]} {errors[j]:.2f}%"
                for j in range(len(steps))
            )
        )

    last = {"step": -1, "vx": "", "vy": ""}

    def update(frame: int):
        step_idx = min(frame // frames, len(steps) - 1)
        local = frame % frames
        m = steps[step_idx]
        x_chain, y_chain = chains[step_idx]
        n_circles = 2 * m + 1

        # --- the two circle groups -------------------------------------
        for circles, spokes, arr in (
            (x_circles, x_spokes, x_chain),
            (y_circles, y_spokes, y_chain),
        ):
            for i in range(n_circles):
                centre = arr[i, local]
                rim = arr[i + 1, local]
                radius = abs(rim - centre)
                circles[i].set_center((centre.real, centre.imag))
                circles[i].set_radius(radius)
                # A circle smaller than a pixel cannot be seen, so hiding it
                # is a pure speed-up with no visual change.
                visible = radius > min_radius
                circles[i].set_visible(visible)
                spokes[i].set_visible(visible)
                if visible:
                    spokes[i].set_data(
                        [centre.real, rim.real], [centre.imag, rim.imag]
                    )
            for i in range(n_circles, max_circles):
                circles[i].set_visible(False)
                spokes[i].set_visible(False)

        # --- the pen ----------------------------------------------------
        # The x chain runs along the real axis, the y chain has been turned a
        # quarter turn so it runs along the vertical one.
        px = float(x_chain[-1, local].real)
        py = float(y_chain[-1, local].imag)

        if local == 0:
            now_x.clear()
            now_y.clear()
        now_x.append(px)
        now_y.append(py)
        all_x.append(px)
        all_y.append(py)

        glow_all.set_data(all_x, all_y)
        trail_all.set_data(all_x, all_y)
        glow_now.set_data(now_x, now_y)
        trail_now.set_data(now_x, now_y)
        tip.set_data([px], [py])

        x_tip.set_data([px], [0.0])
        y_tip.set_data([0.0], [py])

        # --- read-out ----------------------------------------------------
        vx_text = f"x(t) = {px:+.3f}"
        vy_text = f"y(t) = {py:+.3f}"
        if vx_text != last["vx"]:
            value_x.set_text(vx_text)
            last["vx"] = vx_text
        if vy_text != last["vy"]:
            value_y.set_text(vy_text)
            last["vy"] = vy_text

        if step_idx != last["step"]:
            step_text.set_text(step_lines[step_idx])
            history_text.set_text(history_lines[step_idx])
            last["step"] = step_idx

        # --- connectors ---------------------------------------------------
        # A dashed line from each group's tip to the pen: the two machines
        # feed the same drawing.
        p_x = ax_x.transData.transform((px, 0.0))
        p_y = ax_y.transData.transform((0.0, py))
        p_pen = ax_draw.transData.transform((px, py))
        link_x.set_data(
            [p_x[0] / fig_w, p_pen[0] / fig_w],
            [p_x[1] / fig_h, p_pen[1] / fig_h],
        )
        link_y.set_data(
            [p_y[0] / fig_w, p_pen[0] / fig_w],
            [p_y[1] / fig_h, p_pen[1] / fig_h],
        )

        return []

    anim = FuncAnimation(fig, update, frames=total_frames, interval=1000 / FPS, blit=False)

    written: list[Path] = []
    mp4_path = out_dir / f"{shape_name}_sequence{tag}.mp4"
    gif_path = out_dir / f"{shape_name}_sequence{tag}.gif"

    try:
        import imageio_ffmpeg

        matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
        anim.save(
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

    # The GIF is made from the finished MP4, so the frames are only ever
    # rendered once.
    if mp4_path.exists() and _write_gif_from_mp4(mp4_path, gif_path):
        written.append(gif_path)
    else:
        anim.save(gif_path, writer=PillowWriter(fps=FPS))
        written.append(gif_path)

    plt.close(fig)
    return written
