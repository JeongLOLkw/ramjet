"""Compressible boundary-layer relations and wall quantities (I4 onward).

Gas properties come from src/constants.py only (CLAUDE.md rule 4).
Sign convention for heat flux: positive INTO the wall (CLAUDE.md rule 3); the
heat flux itself is computed only in scripts/heatflux.py.
"""
import numpy as np

from src import constants as C

RECOVERY_FACTOR = 0.89  # turbulent recovery factor used by TMR 2DZPH and by Zhang, Duan & Choudhari (2018)


# --------------------------------------------------------------------------- gas properties

def mu_sutherland(T):
    """Dynamic viscosity [Pa s], Sutherland's law with the coefficients of src/constants.py."""
    T = np.asarray(T, float)
    return C.SUTHERLAND_AS * np.sqrt(T) / (1.0 + C.SUTHERLAND_TS / T)


def kappa_eucken(T):
    """Laminar thermal conductivity [W/(m K)] exactly as the solver computes it.

    Modified Eucken relation of OpenFOAM v2512 `sutherlandTransport::kappa`
    (src/thermophysicalModels/specie/transport/sutherland/sutherlandTransportI.H):
    kappa = mu Cv (1.32 + 1.77 R/Cv).
    """
    return mu_sutherland(T) * C.CV_AIR * (1.32 + 1.77 * C.R_AIR / C.CV_AIR)


def recovery_temperature(T_e, M_e, r=RECOVERY_FACTOR, g=C.GAMMA_AIR):
    """Adiabatic-wall (recovery) temperature T_aw = T_e [1 + r (g-1)/2 M_e^2]."""
    return T_e * (1.0 + r * (g - 1.0) / 2.0 * M_e**2)


# --------------------------------------------------------------------------- skin-friction theory

def cf_karman_schoenherr(re_theta):
    """Incompressible flat-plate C_f(Re_theta).

    Karman-Schoenherr relation in the explicit Re_theta form used by the NASA
    Turbulence Modeling Resource (2DZPH page; Schoenherr 1932, Trans. SNAME 40:279-313):
    C_f = 1 / (17.08 (log10 Re_theta)^2 + 25.11 log10 Re_theta + 6.012).
    Equation number in the primary source not checked; the form is verified
    numerically against TMR's cf_vandriestII.dat (tests/test_boundary_layer.py).
    """
    L = np.log10(np.asarray(re_theta, float))
    return 1.0 / (17.08 * L * L + 25.11 * L + 6.012)


def cf_van_driest_ii(re_theta, M_e, Tw_over_Te, T_e=300.0, r=RECOVERY_FACTOR, g=C.GAMMA_AIR):
    """Compressible flat-plate C_f(Re_theta) by the Van Driest II transformation.

    C_f = C_f,inc(F_theta Re_theta) / F_c with
      F_c     = (T_aw/T_e - 1) / (asin A + asin B)^2
      F_theta = mu_e / mu_w (Sutherland)
      a = sqrt(r (g-1)/2 M_e^2 T_e/T_w),  b = T_aw/T_w - 1
      A = (2a^2 - b)/sqrt(b^2 + 4a^2),    B = b/sqrt(b^2 + 4a^2)
    Source: van Driest (1956) as written on the TMR 2DZPH page, which refers to
    White (1974) "Viscous Fluid Flow" pp. 632 ff. Equation numbers in the primary
    sources not checked; the implementation reproduces TMR's cf_vandriestII.dat
    (T_e = 300 K) to 1e-6 relative (tests/test_boundary_layer.py).
    Re_theta = rho_e u_e theta / mu_e.
    """
    T_w = Tw_over_Te * T_e
    T_aw = recovery_temperature(T_e, M_e, r, g)
    a = np.sqrt(r * (g - 1.0) / 2.0 * M_e**2 * T_e / T_w)
    b = T_aw / T_w - 1.0
    den = np.sqrt(b * b + 4.0 * a * a)
    F_c = (T_aw / T_e - 1.0) / (np.arcsin((2.0 * a * a - b) / den) + np.arcsin(b / den)) ** 2
    F_theta = mu_sutherland(T_e) / mu_sutherland(T_w)
    return cf_karman_schoenherr(F_theta * np.asarray(re_theta, float)) / F_c


# --------------------------------------------------------------------------- profile integrals

def _trapz(f, y):
    return float(np.sum(0.5 * (f[1:] + f[:-1]) * np.diff(y)))


def integral_thicknesses(y, rho, u, rho_e, u_e, y_max=None):
    """(delta*, theta) of a wall-normal profile.

    delta* = int (1 - rho u/(rho_e u_e)) dy,  theta = int rho u/(rho_e u_e) (1 - u/u_e) dy,
    from the wall (y = 0, u = 0, rho = rho[0] assumed — isobaric sublayer) to y_max
    (default: last point). y are cell-centre wall distances, ascending.
    """
    y, rho, u = (np.asarray(v, float) for v in (y, rho, u))
    if y_max is not None:
        sel = y <= y_max
        y, rho, u = y[sel], rho[sel], u[sel]
    y = np.concatenate(([0.0], y))
    ru = np.concatenate(([0.0], rho * u)) / (rho_e * u_e)
    uu = np.concatenate(([0.0], u)) / u_e
    return _trapz(1.0 - ru, y), _trapz(ru * (1.0 - uu), y)


def delta99(y, u, u_e):
    """Wall distance where u first reaches 0.99 u_e (linear interpolation)."""
    y, u = np.asarray(y, float), np.asarray(u, float)
    i = np.nonzero(u >= 0.99 * u_e)[0]
    if len(i) == 0:
        raise ValueError("profile never reaches 0.99 u_e")
    i = i[0]
    if i == 0:
        return float(y[0] * 0.99 * u_e / u[0])
    return float(y[i - 1] + (0.99 * u_e - u[i - 1]) * (y[i] - y[i - 1]) / (u[i] - u[i - 1]))


# --------------------------------------------------------------------------- wall quantities

def wall_shear(u_t_cell, d, T_wall):
    """tau_w = mu(T_w) u_t / d: one-sided difference between the first cell centre
    (tangential speed u_t_cell, wall distance d) and the no-slip wall."""
    return mu_sutherland(T_wall) * np.asarray(u_t_cell, float) / np.asarray(d, float)


def y_plus(d, tau_w, rho_w, T_wall):
    """y+ = d u_tau / nu_w of the first cell centre, u_tau = sqrt(|tau_w|/rho_w)."""
    rho_w = np.asarray(rho_w, float)
    return np.asarray(d, float) * np.sqrt(np.abs(tau_w) / rho_w) * rho_w / mu_sutherland(T_wall)


def skin_friction(tau_w, rho_e, u_e):
    return np.asarray(tau_w, float) / (0.5 * rho_e * u_e**2)


def stanton(q_w, rho_e, u_e, T_w, T_aw):
    """St = q_w / (rho_e u_e cp (T_aw - T_w)), q_w positive into the wall."""
    return np.asarray(q_w, float) / (rho_e * u_e * C.CP_AIR * (T_aw - T_w))


def minus_b_q(q_w, rho_w, tau_w, T_w):
    """-B_q = q_w / (rho_w cp u_tau T_w) with q_w positive into the wall.

    Zhang, Duan & Choudhari (2018) define B_q = q_w/(rho_w C_p u_tau T_w) (data-file
    header of M6Tw076_Stat.dat) with q_w from wall to fluid, and tabulate -B_q > 0 for
    cold walls; with this project's sign (into the wall) the same number is +q_w/(...).
    """
    u_tau = np.sqrt(np.abs(tau_w) / rho_w)
    return np.asarray(q_w, float) / (rho_w * C.CP_AIR * u_tau * T_w)


def sign_changes(x, f):
    """Positions where f changes sign along x (linear interpolation).

    Returns [(x0, kind)], kind = 'sep' for + -> - (separation when f = tau_w along
    the flow direction) and 'reatt' for - -> +. A zero exactly at a node counts once,
    for the interval that ends there.
    """
    x, f = np.asarray(x, float), np.asarray(f, float)
    out = []
    for i in range(len(x) - 1):
        a, b = f[i], f[i + 1]
        if (a > 0 >= b) or (a < 0 <= b):
            x0 = x[i] - a * (x[i + 1] - x[i]) / (b - a)
            out.append((float(x0), "sep" if a > 0 else "reatt"))
    return out
