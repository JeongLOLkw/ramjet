"""U.S. Standard Atmosphere 1976, geopotential altitude 0-32 km (three lowest layers).

Source: U.S. Standard Atmosphere, 1976 (NOAA/NASA/USAF, NOAA-S/T 76-1562):
  - eq. (18) geopotential altitude H = r0 Z / (r0 + Z),
  - eq. (23) molecular-scale temperature T = T_b + L_b (H - H_b) (Table 4 lapse rates),
  - eqs. (33a)/(33b) pressure for L_b != 0 / L_b = 0.
Defining constants (Table 2/3): g0' = 9.80665 m2/(s2 m'), R* = 8314.32 J/(kmol K),
M0 = 28.9644 kg/kmol, r0 = 6356.766 km, P0 = 101325 Pa, T0 = 288.15 K.
The equation numbers were not re-read from the report in this session; the formulas are the ones
used in docs/exercises.md problem 1 (I1), whose 25 km values the tests reproduce.

Used in I5 only to size the first cell height on a provisional constant-dynamic-pressure
trajectory (decisions.md D-016). The trajectory itself is an I7 decision.
"""
import math

from src import constants as C

G0 = 9.80665            # [m/s2]
R_STAR = 8314.32        # [J/(kmol K)] (the 1976 standard's value, not OpenFOAM's RR)
M0 = 28.9644            # [kg/kmol]
R0_EARTH = 6356766.0    # [m]
GMR = G0 * M0 / R_STAR  # 0.0341632 K/m

# (base geopotential altitude [m], base temperature [K], lapse rate [K/m])
_LAYERS = ((0.0, 288.15, -6.5e-3), (11000.0, 216.65, 0.0), (20000.0, 216.65, 1.0e-3))
H_MAX = 32000.0
P_SEA_LEVEL = 101325.0


def geopotential_altitude(z):
    """Geopotential altitude H [m] from geometric altitude Z [m] (eq. 18)."""
    return R0_EARTH * z / (R0_EARTH + z)


def _layer_pressure(Tb, pb, L, dh):
    if L == 0.0:
        return pb * math.exp(-GMR * dh / Tb)              # eq. 33b
    return pb * (Tb / (Tb + L * dh)) ** (GMR / L)         # eq. 33a


def _bases():
    """[(H_b, T_b, L_b, p_b)] with the base pressures chained from sea level."""
    out, pb = [], P_SEA_LEVEL
    for i, (hb, Tb, L) in enumerate(_LAYERS):
        out.append((hb, Tb, L, pb))
        h_next = _LAYERS[i + 1][0] if i + 1 < len(_LAYERS) else H_MAX
        pb = _layer_pressure(Tb, pb, L, h_next - hb)
    return out


_BASES = _bases()


def state(h):
    """(T [K], p [Pa]) at geopotential altitude h [m], 0 <= h <= 32000."""
    if not 0.0 <= h <= H_MAX:
        raise ValueError(f"geopotential altitude {h} m outside 0..{H_MAX:g} m")
    hb, Tb, L, pb = [b for b in _BASES if b[0] <= h][-1]
    return Tb + L * (h - hb), _layer_pressure(Tb, pb, L, h - hb)


def altitude_from_pressure(p):
    """Geopotential altitude [m] at which the standard pressure equals p."""
    p_top = state(H_MAX)[1]
    if not p_top <= p <= P_SEA_LEVEL:
        raise ValueError(f"pressure {p} Pa outside {p_top:.4g}..{P_SEA_LEVEL:g} Pa (0-32 km)")
    hb, Tb, L, pb = [b for b in _BASES if b[3] >= p][-1]
    if L == 0.0:
        return hb + Tb / GMR * math.log(pb / p)
    return hb + Tb / L * ((pb / p) ** (L / GMR) - 1.0)


def constant_q_point(M, q, g=C.GAMMA_AIR):
    """Free-stream static state on a constant-dynamic-pressure trajectory, q = (g/2) p M^2.

    If q would need a pressure above sea level (low Mach), the point is clamped to sea level and
    the actual (lower) dynamic pressure is returned with sea_level_clamped = True.
    """
    p = q / (0.5 * g * M**2)
    clamped = p > P_SEA_LEVEL
    if clamped:
        p = P_SEA_LEVEL
    h = 0.0 if clamped else altitude_from_pressure(p)
    T, p = state(h)
    return dict(M=M, h=h, T=T, p=p, q=0.5 * g * p * M**2, sea_level_clamped=clamped)
