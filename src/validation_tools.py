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


def grid_convergence(phi, n_cells, dim=2, safety=1.25, tol=1e-12, max_iter=500):
    """Grid-convergence index of a scalar on three grids, after Celik et al. (2008).

    Celik, Ghia, Roache, Freitas, Coleman, Raad, "Procedure for Estimation and Reporting of Uncertainty Due to
    Discretization in CFD Applications", J. Fluids Eng. 130(7):078001, 2008.  The equations below are written
    from the well-known procedure; the equation numbers quoted are from memory
    (eq. numbers not verified against the original).

    phi, n_cells: values and cell counts on three grids ordered COARSE -> FINE (n_cells strictly increasing).
    The paper numbers the grids fine -> coarse (grid 1 = finest): phi1 = phi[2], phi2 = phi[1], phi3 = phi[0].

    Procedure:
      representative grid size  h = (1/N)^(1/dim)  (paper eq. 1-2 with equal cell volumes/areas; only ratios matter)
      refinement ratios         r21 = h2/h1,  r32 = h3/h2
      eps32 = phi3 - phi2,  eps21 = phi2 - phi1,  s = sign(eps32/eps21)                      (paper eq. 3)
      p = (1/ln r21) * | ln|eps32/eps21| + q(p) |,  q(p) = ln((r21^p - s)/(r32^p - s))     (paper eq. 4-5)
          solved by fixed-point iteration, started from the constant-ratio value
      phi_ext21 = (r21^p phi1 - phi2)/(r21^p - 1)                                           (paper eq. 6)
      e_a21 = |(phi1 - phi2)/phi1|,  e_ext21 = |(phi_ext21 - phi1)/phi_ext21|              (paper eq. 7-8)
      GCI21_fine = safety * e_a21 / (r21^p - 1),  safety = 1.25                             (paper eq. 9)
      Asymptotic-range check (paper step 6): GCI32 / (r21^p GCI21) ~ 1.

    Returns a dict with keys status, p, phi_ext, e_a21, e_ext21, gci21, gci32, asymptotic_ratio, r21, r32,
    eps21, eps32, s, band.  `status` is one of
      "monotone"     s > 0 and p > 0: everything above is defined;
      "oscillatory"  s < 0 (phi2 is not between phi1 and phi3): the procedure gives no order; p, phi_ext, gci are
                     NaN and `band` = (min, max) of the three values is reported instead;
      "zero_change"  eps21 == 0 or eps32 == 0: ln|eps32/eps21| undefined, no division is attempted; e_a21 is still
                     reported (0.0 when phi1 == phi2);
      "diverging"    monotone but |eps32| <= |eps21| (p <= 0) or the iteration did not converge: no extrapolation.
    Undefined quantities are NaN.
    """
    phi = np.asarray(phi, float)
    n = np.asarray(n_cells, float)
    if phi.shape != (3,) or n.shape != (3,):
        raise ValueError("need exactly three grid levels")
    if not np.all(np.isfinite(phi)):
        raise ValueError("phi must be finite")
    if not (n[0] < n[1] < n[2]):
        raise ValueError("n_cells must increase strictly from coarse to fine")
    phi3, phi2, phi1 = phi
    h3, h2, h1 = (1.0 / n) ** (1.0 / dim)
    r21, r32 = h2 / h1, h3 / h2
    eps32, eps21 = phi3 - phi2, phi2 - phi1
    nan = float("nan")
    e_a21 = abs((phi1 - phi2) / phi1) if phi1 != 0 else nan
    out = dict(status=None, p=nan, phi_ext=nan, e_a21=e_a21, e_ext21=nan, gci21=nan, gci32=nan,
               asymptotic_ratio=nan, r21=float(r21), r32=float(r32), eps21=float(eps21), eps32=float(eps32),
               s=0, band=(float(phi.min()), float(phi.max())))
    if eps21 == 0 or eps32 == 0:
        out["status"] = "zero_change"
        return out
    s = 1 if eps32 / eps21 > 0 else -1
    out["s"] = s
    if s < 0:
        out["status"] = "oscillatory"
        return out
    ratio = abs(eps32 / eps21)
    p = abs(np.log(ratio)) / np.log(r21)        # constant-ratio start value (q = 0)
    converged = False
    for _ in range(max_iter):
        q = np.log((r21 ** p - s) / (r32 ** p - s))
        p_new = abs(np.log(ratio) + q) / np.log(r21)
        if abs(p_new - p) < tol * max(1.0, p):
            p, converged = p_new, True
            break
        p = p_new
    # p <= 0 (|eps32| <= |eps21|): the fine-level change is not smaller than the coarse-level one, so the
    # fixed point (which uses |.|) would report a positive "order" for a non-asymptotic sequence -> diverging.
    if not converged or ratio <= 1.0 or not np.isfinite(p) or p <= 0:
        out["status"] = "diverging"
        return out
    out["status"] = "monotone"
    out["p"] = float(p)
    out["phi_ext"] = float((r21 ** p * phi1 - phi2) / (r21 ** p - 1))
    if out["phi_ext"] != 0:
        out["e_ext21"] = float(abs((out["phi_ext"] - phi1) / out["phi_ext"]))
    if phi1 != 0:
        out["gci21"] = float(safety * e_a21 / (r21 ** p - 1))
    if phi2 != 0 and phi1 != 0:
        e_a32 = abs((phi2 - phi3) / phi2)
        out["gci32"] = float(safety * e_a32 / (r32 ** p - 1))
        out["asymptotic_ratio"] = float(out["gci32"] / (r21 ** p * out["gci21"]))
    return out
