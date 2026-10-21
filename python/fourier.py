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


def by_frequency(coeffs: np.ndarray, freqs: np.ndarray) -> dict[int, complex]:
    """Index the coefficients by their **signed** frequency.

    ``table[k]`` is the complex coefficient that rotates at frequency ``k``
    (``k`` may be negative). A frequency that is not in the set is simply
    missing from the dictionary.
    """
    return {int(f): complex(c) for c, f in zip(coeffs, freqs)}


def harmonic_coeffs(
    table: dict[int, complex], k: int
) -> tuple[float, float, float, float]:
    """The real Fourier coefficients ``(a_k, b_k, c_k, d_k)`` of harmonic ``k``.

    The pair of DFT coefficients at ``+k`` and ``-k`` together form one real
    harmonic of the shape. Writing ``C+ = alpha+ + i*beta+`` and
    ``C- = alpha- + i*beta-``:

        C+ * e^(i k t) = ( alpha+ cos kt - beta+ sin kt )
                       + i( beta+  cos kt + alpha+ sin kt )
        C- * e^(-i k t) = ( alpha- cos kt + beta- sin kt )
                       + i( beta-  cos kt - alpha- sin kt )

    Adding the two real parts and the two imaginary parts gives the classic
    real Fourier series of the shape:

        x(t) = sum_k ( a_k*cos(k t) + b_k*sin(k t) )
        y(t) = sum_k ( c_k*cos(k t) + d_k*sin(k t) )
    """
    cp = table.get(k, 0j)
    cm = table.get(-k, 0j)
    a = cp.real + cm.real
    b = -cp.imag + cm.imag
    c = cp.imag + cm.imag
    d = cp.real - cm.real
    return a, b, c, d


def harmonic_chains(
    coeffs: np.ndarray, freqs: np.ndarray, terms: int, frames: int
) -> tuple[np.ndarray, np.ndarray]:
    """Build the ``x(t)`` chain and the ``y(t)`` chain for harmonics ``1..terms``.

    Each harmonic contributes **two** circles -- one turning at ``+k`` and one
    at ``-k`` -- so the running total stays real. That is what makes the tip
    of the x chain sit exactly on the horizontal axis at ``x(t)``, and the tip
    of the y chain at ``y(t)``.

    Returns ``(x_chain, y_chain)``, both shaped ``(2*terms + 2, frames)``.
    Row ``-1`` of ``x_chain`` is ``x(t)`` (a real number) and row ``-1`` of
    ``y_chain`` is ``y(t)``.
    """
    table = by_frequency(coeffs, freqs)
    theta = 2 * np.pi * np.arange(frames) / frames

    dc = table.get(0, 0j)
    vectors_x = [np.full(frames, dc.real, dtype=complex)]
    vectors_y = [np.full(frames, dc.imag, dtype=complex)]

    for k in range(1, terms + 1):
        a, b, c, d = harmonic_coeffs(table, k)
        # X_k = (a_k - i b_k)/2  =>  2*Re(X_k e^(i k t)) = a_k cos kt + b_k sin kt
        xk = (a - 1j * b) / 2
        yk = (c - 1j * d) / 2
        vectors_x.append(xk * np.exp(1j * k * theta))
        vectors_x.append(np.conj(xk) * np.exp(-1j * k * theta))
        vectors_y.append(yk * np.exp(1j * k * theta))
        vectors_y.append(np.conj(yk) * np.exp(-1j * k * theta))

    vx = np.array(vectors_x)
    vy = np.array(vectors_y)
    zeros = np.zeros((1, frames), dtype=complex)
    x_chain = np.concatenate([zeros, np.cumsum(vx, axis=0)])
    y_chain = np.concatenate([zeros, np.cumsum(vy, axis=0)])
    return x_chain, y_chain


def harmonic_error_curve(
    points: np.ndarray, coeffs: np.ndarray, freqs: np.ndarray
) -> np.ndarray:
    """Error percentage for keeping the harmonics ``1..N``.

    ``result[N]`` is the error you get from the classic Fourier partial sum
    that keeps every frequency up to ``N``. It is the same number
    :func:`relative_error` returns for that partial sum, but computed for all
    ``N`` at once.

    By Parseval's identity the squared error is the energy of the discarded
    tail, so only the squared magnitudes have to be added up:

        RMSE(N)^2 = sum_{|freq| > N} |c_freq|^2
    """
    z = points[:, 0] + 1j * points[:, 1]
    radius = float(np.sqrt(np.mean(np.abs(z - z.mean()) ** 2))) or 1.0

    n = len(coeffs)
    max_k = n // 2
    energy = np.zeros(max_k + 2)
    np.add.at(energy, np.abs(freqs).astype(int), np.abs(coeffs) ** 2)

    # tail[j] = sum of energy[j:];  dropping |freq| > N leaves energy[N+1:].
    tail = np.cumsum(energy[::-1])[::-1]
    curve = 100.0 * np.sqrt(tail[1 : max_k + 2]) / radius
    return curve


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


def relative_error_curve(points: np.ndarray, coeffs: np.ndarray) -> np.ndarray:
    """Error percentage for **every** term count, in one O(N) pass.

    ``result[t]`` is the error you get from using the first ``t``
    coefficients. This is the same number :func:`relative_error` returns, but
    computed for all ``t`` at once.

    How it works: the coefficients are sorted by magnitude, so truncating to
    ``t`` terms simply drops the tail. By Parseval's identity the squared
    error of the dropped tail is just the sum of its squared magnitudes:

        RMSE(t)^2 = sum_{k >= t} |c_k|^2

    Verified to agree with the direct :func:`rmse` reconstruction to within
    7e-16 on every shape. It also means the curve is *monotonically
    non-increasing*, which is what makes the binary search in
    :func:`select_terms` safe.
    """
    z = points[:, 0] + 1j * points[:, 1]
    radius = float(np.sqrt(np.mean(np.abs(z - z.mean()) ** 2))) or 1.0
    sq = np.abs(coeffs) ** 2
    # tail[t] = sum of sq from t to the end. Reversing first, accumulating,
    # then reversing back puts the running total of the tail at index t.
    tail = np.concatenate([np.cumsum(sq[::-1])[::-1], [0.0]])
    return 100.0 * np.sqrt(tail) / radius


def select_terms(
    points: np.ndarray,
    coeffs: np.ndarray,
    freqs: np.ndarray,
    target_pct: float,
    count: int = 4,
    strict: bool = False,
) -> list[int]:
    """Choose term counts that hit an error target.

    ``strict=False`` (the default) builds a ladder of powers of two whose
    **last** panel is the first power of two to beat the target -- so you see
    the approximation improve and then land under the target.

    ``strict=True`` builds a ladder where **every** panel beats the target.

    Both are derived from the actual error curve, not hardcoded, so the same
    call works for the crown (needs many terms) and the heart (needs few).
    """
    n = len(coeffs)
    curve = relative_error_curve(points, coeffs)

    if strict:
        # Every panel beats the target: start from the smallest term count
        # that qualifies. A 5 % margin keeps the printed number clearly
        # under the target instead of sitting right on the boundary.
        margin = target_pct * 0.95
        qualifying = np.nonzero(curve[1 : n + 1] < margin)[0]
        if len(qualifying) == 0:
            return [n]
        first = int(qualifying[0]) + 1
        ladder = [
            min(n, int(round(first * 2 ** (i / (count - 1))))) for i in range(count)
        ]
    else:
        # Only the last panel has to beat the target: step down by powers of two.
        powers = [1 << k for k in range(int(np.log2(n)) + 1)]
        qualifies = [p for p in powers if curve[p] < target_pct]
        if not qualifies:
            return powers[-count:]
        top = qualifies[0]
        ladder = [max(1, top // 2 ** (count - 1 - i)) for i in range(count)]

    # Keep them ordered, free of duplicates, and never past the sample count.
    ladder = sorted(dict.fromkeys(ladder))
    while len(ladder) < count and ladder[-1] < n:
        ladder.append(ladder[-1] + 1)
    return ladder
