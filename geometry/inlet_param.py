"""Parametric 2D mixed-compression inlet (I5): two external ramps, horizontal cowl with a blunt lip,
sharp shoulder, constant-area isolator.  Default values = decisions.md D-016 (approved 2026-11-11).

Coordinates: origin at the (sharp) leading edge of ramp 1, x along the free stream, y up, metres.

Design procedure (inviscid, calorically perfect gas, gamma from src/constants.py):
  1. Ramp shocks from the weak oblique-shock relations, NACA Report 1135 eq. (138) and following
     (src/gasdynamics.oblique_shock).
  2. Shock-on-lip: the cowl lip is put where the two ramp shocks intersect at the design Mach number
     (procedure of docs/i5_geometry_literature.md §2a, steps 1-5; Sanders & Weir, NASA/CR-2008-215214).
  3. Internal contraction cr_int = A_i / A_th, with A_i the distance from the lip to the ramp-2
     surface measured normal to the ramp (the flow-normal section ahead of the cowl shock) and
     A_th the isolator height.  The shoulder is the point of ramp 2 that gives this throat height.
     Self-starting limit: Kantrowitz & Donaldson (1945), src/gasdynamics.kantrowitz_limit.
All numbers are inviscid; boundary-layer displacement is not included (lip_dy lets the cowl be raised).
"""
from dataclasses import asdict, dataclass, fields, replace

import numpy as np
from scipy.optimize import brentq

from src import constants as C
from src import gasdynamics as gd

G = C.GAMMA_AIR


@dataclass(frozen=True)
class InletParams:
    M_design: float = 5.0         # shock-on-lip Mach number
    delta1_deg: float = 8.0       # ramp 1 angle
    delta2_deg: float = 10.0      # ramp 2 additional angle (total = delta1 + delta2)
    H_capture: float = 0.100      # height of the shock focus above the leading edge [m]
    cr_int: float = 1.30          # internal contraction A_i / A_th
    iso_L_over_H: float = 10.0    # isolator length / throat height (constant area)
    lip_radius: float = 0.5e-3    # cowl lip radius [m]
    lip_dy: float = 0.0           # cowl raised above the inviscid focus [m] (viscous correction, default none)
    cowl_ext_deg: float = 10.0    # cowl outer surface angle
    cowl_thickness: float = 0.010  # cowl thickness downstream of the outer wedge [m]
    T_wall: float = 300.0         # isothermal wall temperature [K] (plan §5)
    x_up: float = 0.05            # domain: distance of the inflow boundary upstream of the leading edge [m]
    y_top: float = 0.40           # domain: height of the top boundary above the leading edge [m]


def as_dict(p):
    return asdict(p)


def with_overrides(p, assignments):
    """New parameter set from ['name=value', ...] (command-line --set)."""
    names = {f.name for f in fields(p)}
    kw = {}
    for a in assignments:
        k, _, v = a.partition("=")
        if k not in names:
            raise ValueError(f"unknown inlet parameter '{k}' (known: {', '.join(sorted(names))})")
        kw[k] = float(v)
    return replace(p, **kw)


def _shock(M, theta):
    """Oblique shock or None if detached."""
    try:
        return gd.oblique_shock(M, theta, G)
    except ValueError:
        return None


def _ramp_states(p, Minf):
    """(shock 1, shock 2) at free-stream Mach Minf for the fixed ramp angles; None where detached."""
    s1 = _shock(Minf, np.radians(p.delta1_deg)) if Minf > 1 else None
    s2 = _shock(s1["M2"], np.radians(p.delta2_deg)) if s1 and s1["M2"] > 1 else None
    return s1, s2


def design(p):
    """Design-point flow states and outline points of the inlet. Raises ValueError for an invalid set."""
    d1, d2, te = np.radians(p.delta1_deg), np.radians(p.delta2_deg), np.radians(p.cowl_ext_deg)
    dt = d1 + d2
    R = p.lip_radius
    if p.M_design <= 1 or min(p.delta1_deg, p.delta2_deg) <= 0:
        raise ValueError("M_design must be supersonic and both ramp angles positive")
    if min(p.H_capture, p.iso_L_over_H, R, p.cr_int) <= 0 or not 0 < p.cowl_ext_deg < 45:
        raise ValueError("H_capture, iso_L_over_H, lip_radius, cr_int must be positive; 0 < cowl_ext_deg < 45")
    s1, s2 = _ramp_states(p, p.M_design)
    if s1 is None or s2 is None:
        raise ValueError("a ramp shock is detached at the design Mach number")
    b1, b2abs = s1["beta"], d1 + s2["beta"]
    if not b2abs > b1:
        raise ValueError("ramp shocks do not intersect downstream (need delta1 + beta2 > beta1)")

    # shock-on-lip: focus F on shock 1 at height H_capture; kink K on ramp 1 such that shock 2 passes F
    xF, yF = p.H_capture / np.tan(b1), p.H_capture
    xK = (yF - xF * np.tan(b2abs)) / (np.tan(d1) - np.tan(b2abs))
    K = (xK, xK * np.tan(d1))

    # cowl: inner surface y = y_cowl, lip circle tangent to it, foremost point at x = xF
    y_cowl = yF + p.lip_dy
    Cn = (xF + R, y_cowl + R)
    ang = lambda phi: (Cn[0] + R * np.cos(phi), Cn[1] + R * np.sin(phi))  # noqa: E731
    P_in, P_nose, P_out = ang(1.5 * np.pi), ang(np.pi), ang(0.5 * np.pi + te)
    y_top_cowl = y_cowl + p.cowl_thickness
    if y_top_cowl <= P_out[1] + R:
        raise ValueError("cowl_thickness too small for the lip radius and outer angle")
    Tc = (P_out[0] + (y_top_cowl - P_out[1]) / np.tan(te), y_top_cowl)

    # internal contraction: A_i normal to ramp 2 from the lip station point (xF, y_cowl)
    A_i = (y_cowl - K[1]) * np.cos(dt) - (xF - K[0]) * np.sin(dt)
    if p.cr_int <= 1 / np.cos(dt):
        raise ValueError(f"cr_int must exceed 1/cos(delta1+delta2) = {1 / np.cos(dt):.4f} "
                         "(shoulder downstream of the lip normal)")
    H_th = A_i / p.cr_int
    yS = y_cowl - H_th
    S = (K[0] + (yS - K[1]) / np.tan(dt), yS)
    L_iso = p.iso_L_over_H * H_th
    E0 = (S[0] + L_iso, yS)
    if Tc[0] >= E0[0]:
        raise ValueError("cowl outer wedge ends downstream of the isolator exit")
    if not (p.y_top > y_top_cowl + 5 * p.cowl_thickness and p.x_up > 0):
        raise ValueError("domain too small (y_top, x_up)")

    # cowl shock (flow turned back by delta1 + delta2 to the horizontal cowl)
    tmax2 = gd.theta_max(s2["M2"], G)[0]
    s3 = _shock(s2["M2"], dt)
    nan = float("nan")
    p2 = s1["p2_p1"] * s2["p2_p1"]
    pt2 = s1["p02_p01"] * s2["p02_p01"]
    eq = brentq(lambda t: gd.oblique_shock(s1["M2"], t, G)["p2_p1"] - s1["p2_p1"], 1e-6,
                gd.theta_max(s1["M2"], G)[0] - 1e-9)
    return dict(
        beta1=b1, beta2=s2["beta"], beta2_abs=b2abs, M1=s1["M2"], M2=s2["M2"], p1=s1["p2_p1"], p2=p2, pt2=pt2,
        beta3=s3["beta"] if s3 else nan, M3=s3["M2"] if s3 else nan, p3=p2 * s3["p2_p1"] if s3 else nan,
        pt3=pt2 * s3["p02_p01"] if s3 else nan, cowl_pressure_ratio=s3["p2_p1"] if s3 else nan,
        cowl_margin_deg=float(np.degrees(tmax2 - dt)),
        delta2_equal_strength_deg=float(np.degrees(eq)),
        cr_kantrowitz=1 / gd.kantrowitz_limit(s2["M2"], G), cr_isentropic=1 / gd.isentropic_limit(s2["M2"], G),
        cr_shock_on_shoulder=(np.sin(s3["beta"]) / np.sin(s3["beta"] - dt)) if s3 else nan,
        LE=(0.0, 0.0), K=K, F=(xF, yF), S=S, E0=E0, x_exit=E0[0], L1=float(np.hypot(*K)),
        A_i=A_i, H_th=H_th, L_iso=L_iso, y_cowl=y_cowl, delta_tot=dt,
        Cn=Cn, P_in=P_in, P_nose=P_nose, P_out=P_out, Tc=Tc, Eo=(E0[0], y_top_cowl), E_in=(E0[0], y_cowl),
    )


def _first_positive(f, a, b, n=600):
    """Smallest root in [a, b] where f changes from <= 0 to > 0 (scan + brentq); NaN if none."""
    xs = np.linspace(a, b, n)
    prev, fprev = xs[0], f(xs[0])
    if fprev > 0:
        return float(a)
    for x in xs[1:]:
        fx = f(x)
        if fx > 0 >= fprev:
            return float(brentq(f, prev, x, xtol=1e-12))
        prev, fprev = x, fx
    return float("nan")


def detachment_machs(p):
    """Lowest free-stream Mach numbers at which (ramp 1, ramp 2, horizontal cowl) shocks are attached
    (inviscid, fixed geometry). Below each value that shock is detached."""
    d2, dt = np.radians(p.delta2_deg), np.radians(p.delta1_deg + p.delta2_deg)
    m1 = gd.mach_min_attached(np.radians(p.delta1_deg), G)

    def f2(M):
        s1, _ = _ramp_states(p, M)
        return -1.0 if s1 is None or s1["M2"] <= 1 else gd.theta_max(s1["M2"], G)[0] - d2

    def f3(M):
        _, s2 = _ramp_states(p, M)
        return -1.0 if s2 is None or s2["M2"] <= 1 else gd.theta_max(s2["M2"], G)[0] - dt

    m2 = _first_positive(f2, m1 + 1e-6, 20.0)
    m3 = _first_positive(f3, m2 + 1e-6, 30.0)
    return m1, m2, m3


def kantrowitz_start_mach(p):
    """Lowest free-stream Mach number (cowl shock attached) at which the Kantrowitz limit at the cowl
    entrance Mach number allows cr_int, i.e. kantrowitz_limit(M2) <= 1/cr_int. NaN if never (up to M 30)."""
    m3 = detachment_machs(p)[2]

    def f(M):
        _, s2 = _ramp_states(p, M)
        return -1.0 if s2 is None else 1 / p.cr_int - gd.kantrowitz_limit(s2["M2"], G)

    return _first_positive(f, m3, 30.0)


def off_design(p, Minf):
    """Inviscid ramp/cowl states at free-stream Mach Minf (geometry fixed). Values are NaN where a
    shock is detached. y_shock1_at_lip = height of the ramp-1 shock at the lip station."""
    d = design(p)
    s1, s2 = _ramp_states(p, Minf)
    s3 = _shock(s2["M2"], d["delta_tot"]) if s2 else None
    nan = float("nan")
    return dict(M1=s1["M2"] if s1 else nan, M2=s2["M2"] if s2 else nan, M3=s3["M2"] if s3 else nan,
                p2=s1["p2_p1"] * s2["p2_p1"] if s2 else nan,
                p3=s1["p2_p1"] * s2["p2_p1"] * s3["p2_p1"] if s3 else nan,
                y_shock1_at_lip=d["F"][0] * np.tan(s1["beta"]) if s1 else nan,
                kantrowitz_cr=1 / gd.kantrowitz_limit(s2["M2"], G) if s2 else nan)
