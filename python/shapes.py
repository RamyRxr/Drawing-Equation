"""Shape definitions for the Fourier drawing prototype.

Every shape is returned as an (N, 2) array of outline points, sampled roughly
evenly by arc length and normalized to sit inside roughly [-1, 1]^2.
"""

from __future__ import annotations

import numpy as np


def _resample_polygon(vertices: np.ndarray, n: int) -> np.ndarray:
    """Sample ``n`` points evenly (by arc length) around a closed polygon."""
    v = np.vstack([vertices, vertices[0]])
    seg = np.diff(v, axis=0)
    seg_len = np.hypot(seg[:, 0], seg[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    total = cum[-1]

    out = np.empty((n, 2))
    for i, d in enumerate(np.linspace(0.0, total, n, endpoint=False)):
        j = min(int(np.searchsorted(cum, d, side="right") - 1), len(seg) - 1)
        frac = (d - cum[j]) / seg_len[j]
        out[i] = v[j] + frac * seg[j]
    return out


def _normalize(points: np.ndarray) -> np.ndarray:
    """Center the shape and scale it to fit inside roughly [-1, 1]."""
    pts = points - points.mean(axis=0)
    scale = float(np.max(np.abs(pts))) or 1.0
    return pts / scale


def crown(n: int = 512) -> np.ndarray:
    """A three-spiked crown. Sharp corners -> slow Fourier convergence."""
    vertices = np.array(
        [
            [-1.00, -0.55],
            [1.00, -0.55],
            [1.00, 0.05],
            [0.62, 0.80],
            [0.30, 0.12],
            [0.00, 1.00],
            [-0.30, 0.12],
            [-0.62, 0.80],
            [-1.00, 0.05],
        ]
    )
    return _normalize(_resample_polygon(vertices, n))


def star(points: int = 5, inner: float = 0.45, n: int = 512) -> np.ndarray:
    """A classic n-pointed star."""
    verts = []
    for a in np.linspace(0, 2 * np.pi, points, endpoint=False):
        verts.append([np.cos(a), np.sin(a)])
        verts.append([inner * np.cos(a + np.pi / points), inner * np.sin(a + np.pi / points)])
    return _normalize(_resample_polygon(np.array(verts), n))


def heart(n: int = 512) -> np.ndarray:
    """A smooth heart curve."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    return _normalize(np.column_stack([x, y]))


def infinity(n: int = 512) -> np.ndarray:
    """A figure-eight / infinity loop."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    denom = 1 + np.sin(t) ** 2
    x = np.cos(t) / denom
    y = np.sin(t) * np.cos(t) / denom
    return _normalize(np.column_stack([x, y]))


SHAPES = {
    "crown": crown,
    "star": star,
    "heart": heart,
    "infinity": infinity,
}
