"""Post-processing helpers for solver validation (I3).

Generic numerics only; physics references live in src/gasdynamics.py.
"""
import numpy as np


def crossing(s, q, level):
    """First position along s where q crosses `level` (linear interpolation), or None."""
    s, q = np.asarray(s, float), np.asarray(q, float)
    d = q - level
    idx = np.nonzero(np.sign(d[:-1]) * np.sign(d[1:]) <= 0)[0]
    idx = [i for i in idx if d[i] != d[i + 1]]
    if not idx:
        return None
    i = idx[0]
    return s[i] + (s[i + 1] - s[i]) * (-d[i]) / (d[i + 1] - d[i])


def fit_line_angle(x, y):
    """Least-squares line y = a (x - x0). Returns (angle atan(a), x-intercept x0, rms residual)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    a, b = np.polyfit(x, y, 1)
    resid = np.sqrt(np.mean((y - (a * x + b)) ** 2))
    return np.arctan(a), -b / a, resid


def l1_error(num, exact, dx):
    """Discrete L1 norm sum |num - exact| dx."""
    return float(np.sum(np.abs(np.asarray(num) - np.asarray(exact)) * dx))


def observed_order(h, err):
    """Observed order between successive grid levels: log(e_i/e_{i+1}) / log(h_i/h_{i+1})."""
    h, err = np.asarray(h, float), np.asarray(err, float)
    return np.log(err[:-1] / err[1:]) / np.log(h[:-1] / h[1:])


def relative_change(it, m, window):
    """max |m - m_last| / |m_last| over iterations it >= it_last - window.

    Raises ValueError if the history does not span the window (cannot judge).
    """
    it, m = np.asarray(it, float), np.asarray(m, float)
    if it[-1] - it[0] < window:
        raise ValueError(f"history spans {it[-1] - it[0]:g} < window {window:g}")
    sel = it >= it[-1] - window
    return float(np.max(np.abs(m[sel] - m[-1])) / abs(m[-1]))


def mass_imbalance(patch_flux):
    """|net mass flux| / inflow, from patch-integrated mass fluxes (outflow positive)."""
    f = np.array(list(patch_flux.values()), float)
    inflow = -f[f < 0].sum()
    return float(abs(f.sum()) / inflow)
