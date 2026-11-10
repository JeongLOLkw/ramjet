"""Analytic compressible-flow relations used as validation references (I3).

Calorically perfect gas, angles in radians. Sources are cited per function
(CLAUDE.md rule 11):
- NACA Report 1135 (Ames Research Staff, 1953): eqs. (93)-(100) normal shock,
  (99) Rayleigh pitot, (138)-(150) oblique shock, (171) Prandtl-Meyer.
- Toro, E. F. (2009), Riemann Solvers and Numerical Methods for Fluid Dynamics,
  3rd ed., Ch. 4: eqs. (4.5)-(4.9) star pressure function, (4.18) PVRS guess,
  §4.5 sampling (eqs. 4.53-4.56).
"""
import numpy as np
from scipy.optimize import brentq


# --- isentropic -------------------------------------------------------------

def p_p0(M, g):
    """Static/total pressure, isentropic (NACA 1135 eq. 44)."""
    return (1 + 0.5 * (g - 1) * M**2) ** (-g / (g - 1))


# --- normal shock -----------------------------------------------------------

def normal_shock(M1, g):
    """Normal-shock jump relations (NACA 1135 eqs. 93, 94, 96, 99)."""
    M1s = M1**2
    p21 = (2 * g * M1s - (g - 1)) / (g + 1)                                  # eq. 93
    r21 = (g + 1) * M1s / ((g - 1) * M1s + 2)                                # eq. 94
    M2 = np.sqrt(((g - 1) * M1s + 2) / (2 * g * M1s - (g - 1)))              # eq. 96
    p0r = r21 ** (g / (g - 1)) * (1 / p21) ** (1 / (g - 1))                   # eq. 99
    return {"M2": M2, "p2_p1": p21, "rho2_rho1": r21, "T2_T1": p21 / r21, "p02_p01": p0r}


def rayleigh_pitot(M1, g):
    """Pitot (stagnation) pressure / free-stream static pressure.

    Supersonic: Rayleigh pitot formula (NACA 1135 eq. 100). Subsonic: isentropic.
    """
    if M1 <= 1:
        return 1 / p_p0(M1, g)
    a = ((g + 1) / 2 * M1**2) ** (g / (g - 1))
    b = ((g + 1) / (2 * g * M1**2 - (g - 1))) ** (1 / (g - 1))
    return a * b


# --- oblique shock ----------------------------------------------------------

def _theta_of_beta(M1, b, g):
    """theta-beta-M relation (NACA 1135 eq. 138)."""
    return np.arctan(2 / np.tan(b) * (M1**2 * np.sin(b) ** 2 - 1)
                     / (M1**2 * (g + np.cos(2 * b)) + 2))


def theta_max(M1, g):
    """Maximum attached-shock deflection and its shock angle (numerical max of eq. 138)."""
    mu = np.arcsin(1 / M1)
    from scipy.optimize import minimize_scalar
    r = minimize_scalar(lambda b: -_theta_of_beta(M1, b, g), bounds=(mu, np.pi / 2),
                        method="bounded", options={"xatol": 1e-12})
    return _theta_of_beta(M1, r.x, g), r.x


def oblique_shock(M1, theta, g):
    """Weak attached oblique shock for deflection theta (NACA 1135 eqs. 138-150)."""
    th_max, b_max = theta_max(M1, g)
    if theta > th_max:
        raise ValueError(f"theta {np.degrees(theta):.3f} deg > theta_max {np.degrees(th_max):.3f} deg (detached)")
    mu = np.arcsin(1 / M1)
    b = brentq(lambda b: _theta_of_beta(M1, b, g) - theta, mu + 1e-14, b_max, xtol=1e-15)
    Mn1 = M1 * np.sin(b)
    ns = normal_shock(Mn1, g)
    M2 = ns["M2"] / np.sin(b - theta)                                         # eq. 132 form
    return {"beta": b, "M2": M2, "p2_p1": ns["p2_p1"], "rho2_rho1": ns["rho2_rho1"],
            "T2_T1": ns["T2_T1"], "p02_p01": ns["p02_p01"]}


# --- Prandtl-Meyer ----------------------------------------------------------

def prandtl_meyer(M, g):
    """Prandtl-Meyer function nu(M) (NACA 1135 eq. 171)."""
    k = np.sqrt((g + 1) / (g - 1))
    return k * np.arctan(np.sqrt((M**2 - 1) / k**2)) - np.arctan(np.sqrt(M**2 - 1))


def prandtl_meyer_inverse(nu, g):
    """M such that prandtl_meyer(M) = nu (root find, M in [1, 1e4])."""
    return brentq(lambda M: prandtl_meyer(M, g) - nu, 1.0, 1e4, xtol=1e-14, rtol=1e-15)


def expansion_corner(M1, theta, g):
    """Isentropic turn by theta (expansion): nu(M2) = nu(M1) + theta, p2/p1 isentropic."""
    M2 = prandtl_meyer_inverse(prandtl_meyer(M1, g) + theta, g)
    return {"M2": M2, "p2_p1": p_p0(M2, g) / p_p0(M1, g)}


def fan_mach_at_ray(psi, M1, theta, g):
    """Mach number on a ray from a centred expansion corner.

    Wall horizontal upstream, turning down by theta at the corner; psi is the ray
    angle measured from +x (upward positive). Inside the fan the ray is a Mach line
    of the locally turned flow: psi = mu(M) - delta, delta = nu(M) - nu(M1)
    (simple-wave relation, e.g. Anderson, Modern Compressible Flow, §4.14).
    """
    nu1 = prandtl_meyer(M1, g)
    M2 = expansion_corner(M1, theta, g)["M2"]
    mu = lambda M: np.arcsin(1 / M)
    if psi >= mu(M1):
        return M1
    if psi <= mu(M2) - theta:
        return M2
    f = lambda M: mu(M) - (prandtl_meyer(M, g) - nu1) - psi
    return brentq(f, M1, M2, xtol=1e-14, rtol=1e-14)


# --- exact Riemann solver (Toro 2009, Ch. 4) --------------------------------

def _fK(p, rhoK, pK, aK, g):
    """Pressure function f_K and derivative (Toro 2009 eqs. 4.6-4.7, 4.37)."""
    if p > pK:  # shock
        A = 2 / ((g + 1) * rhoK)
        B = (g - 1) / (g + 1) * pK
        sq = np.sqrt(A / (p + B))
        return (p - pK) * sq, sq * (1 - 0.5 * (p - pK) / (p + B))
    # rarefaction
    r = (p / pK) ** ((g - 1) / (2 * g))
    return 2 * aK / (g - 1) * (r - 1), 1 / (rhoK * aK) * (p / pK) ** (-(g + 1) / (2 * g))


def riemann_star(left, right, g):
    """Star-region state for primitive (rho, u, p) left/right states (Toro 2009 §4.3)."""
    rL, uL, pL = left
    rR, uR, pR = right
    aL, aR = np.sqrt(g * pL / rL), np.sqrt(g * pR / rR)
    du = uR - uL
    if 2 * (aL + aR) / (g - 1) <= du:
        raise ValueError("vacuum generated (Toro 2009 eq. 4.40)")
    # PVRS initial guess (Toro 2009 eq. 4.47)
    p = max(1e-12, 0.5 * (pL + pR) - 0.125 * du * (rL + rR) * (aL + aR))
    for _ in range(100):  # Newton-Raphson on f(p) = fL + fR + du (eq. 4.5)
        fL, dL = _fK(p, rL, pL, aL, g)
        fR, dR = _fK(p, rR, pR, aR, g)
        pn = max(1e-14, p - (fL + fR + du) / (dL + dR))
        if abs(pn - p) / (0.5 * (pn + p)) < 1e-14:
            p = pn
            break
        p = pn
    fL, _ = _fK(p, rL, pL, aL, g)
    fR, _ = _fK(p, rR, pR, aR, g)
    u = 0.5 * (uL + uR) + 0.5 * (fR - fL)                                     # eq. 4.9

    def rho_star(rK, pK):  # eqs. 4.50 (shock) / 4.53 (rarefaction)
        if p > pK:
            q = p / pK
            gr = (g - 1) / (g + 1)
            return rK * (q + gr) / (gr * q + 1)
        return rK * (p / pK) ** (1 / g)

    return {"p": p, "u": u, "rhoL": rho_star(rL, pL), "rhoR": rho_star(rR, pR)}


def riemann_profile(x, t, left, right, g, x0=0.0):
    """Exact solution (rho, u, p) at positions x and time t > 0 (Toro 2009 §4.5)."""
    rL, uL, pL = left
    rR, uR, pR = right
    aL, aR = np.sqrt(g * pL / rL), np.sqrt(g * pR / rR)
    st = riemann_star(left, right, g)
    ps, us = st["p"], st["u"]
    S = (np.asarray(x, float) - x0) / t
    rho, u, p = np.empty_like(S), np.empty_like(S), np.empty_like(S)
    gm, gp = g - 1, g + 1
    for i, s in enumerate(S):
        if s <= us:  # left of contact
            if ps > pL:  # left shock, eq. 4.52
                SL = uL - aL * np.sqrt(gp / (2 * g) * ps / pL + gm / (2 * g))
                st_ = (rL, uL, pL) if s <= SL else (st["rhoL"], us, ps)
            else:        # left rarefaction, eqs. 4.54-4.56
                aLs = aL * (ps / pL) ** (gm / (2 * g))
                SHL, STL = uL - aL, us - aLs
                if s <= SHL:
                    st_ = (rL, uL, pL)
                elif s >= STL:
                    st_ = (st["rhoL"], us, ps)
                else:
                    c = 2 / gp + gm / (gp * aL) * (uL - s)
                    st_ = (rL * c ** (2 / gm), 2 / gp * (aL + gm / 2 * uL + s), pL * c ** (2 * g / gm))
        else:        # right of contact
            if ps > pR:  # right shock, eq. 4.59
                SR = uR + aR * np.sqrt(gp / (2 * g) * ps / pR + gm / (2 * g))
                st_ = (rR, uR, pR) if s >= SR else (st["rhoR"], us, ps)
            else:        # right rarefaction, eqs. 4.61-4.63
                aRs = aR * (ps / pR) ** (gm / (2 * g))
                SHR, STR = uR + aR, us + aRs
                if s >= SHR:
                    st_ = (rR, uR, pR)
                elif s <= STR:
                    st_ = (st["rhoR"], us, ps)
                else:
                    c = 2 / gp - gm / (gp * aR) * (uR - s)
                    st_ = (rR * c ** (2 / gm), 2 / gp * (-aR + gm / 2 * uR + s), pR * c ** (2 * g / gm))
        rho[i], u[i], p[i] = st_
    return rho, u, p
