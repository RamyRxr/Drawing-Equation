"""Fourier (DFT) helpers: turn an outline into a chain of rotating epicycles.

The key idea
------------
Treat the points of a closed outline as one complex signal:

    z_n = x_n + i * y_n

Then the Discrete Fourier Transform gives complex coefficients c_k such that

    z(theta) = sum_k c_k * exp(i * freq_k * theta)

Each term is a point rotating in a circle: ``c_k`` sets the circle's radius and
starting angle, ``freq_k`` sets how fast it spins. Stack the circles tip-to-tail
and the pen at the end traces the original shape.
"""

from __future__ import annotations

import numpy as np


def coefficients(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(coeffs, freqs)`` sorted by magnitude, largest first.

    ``coeffs[k]`` is the complex amplitude and ``freqs[k]`` its integer
    frequency (may be negative), so that

        z(theta) = sum(coeffs * exp(1j * freqs * theta))
    """
    z = points[:, 0] + 1j * points[:, 1]
    n = len(z)

    coeffs = np.fft.fft(z) / n
    freqs = np.fft.fftfreq(n, d=1 / n)

    order = np.argsort(-np.abs(coeffs))
    return coeffs[order], freqs[order]


def reconstruct(
    coeffs: np.ndarray,
    freqs: np.ndarray,
    theta: np.ndarray | float,
    terms: int | None = None,
) -> np.ndarray:
    """Evaluate the (optionally truncated) Fourier sum at angles ``theta``."""
    c = coeffs if terms is None else coeffs[:terms]
    f = freqs if terms is None else freqs[:terms]
    theta = np.atleast_1d(theta)
    return np.exp(1j * f[None, :] * theta[:, None]) @ c


def chain(coeffs: np.ndarray, freqs: np.ndarray, theta: float, terms: int) -> np.ndarray:
    """Joint positions of the epicycle chain for a single angle ``theta``.

    The last entry is the pen tip: ``sum(coeffs[:terms] * exp(1j*freqs[:terms]*theta))``.
    """
    c = coeffs[:terms]
    f = freqs[:terms]
    return np.cumsum(c * np.exp(1j * f * theta))


def rmse(points: np.ndarray, coeffs: np.ndarray, freqs: np.ndarray, terms: int) -> float:
    """Root-mean-square reconstruction error using ``terms`` coefficients."""
    n = len(points)
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    true = points[:, 0] + 1j * points[:, 1]
    approx = reconstruct(coeffs, freqs, theta, terms)
    return float(np.sqrt(np.mean(np.abs(true - approx) ** 2)))


def relative_error(
    points: np.ndarray, coeffs: np.ndarray, freqs: np.ndarray, terms: int
) -> float:
    """Reconstruction error as a **percentage** of the shape's own size.

    The raw RMSE is measured in shape units, so it is not comparable between
    a big shape and a small one. Dividing by the RMS distance of the true
    outline from its centre turns it into "how wrong is the drawing, as a
    percentage of the drawing's typical radius?".
    """
    z = points[:, 0] + 1j * points[:, 1]
    radius = float(np.sqrt(np.mean(np.abs(z - z.mean()) ** 2))) or 1.0
    return 100.0 * rmse(points, coeffs, freqs, terms) / radius
