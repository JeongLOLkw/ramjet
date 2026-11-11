from pathlib import Path

import numpy as np
import pytest

from src import boundary_layer as bl
from src import constants as C

DATA = Path(__file__).resolve().parents[1] / "docs/validation_data"


def tmr_zones(path):
    zones, cur = {}, None
    for line in open(path):
        if line.startswith("ZONE"):
            cur = line.split('"')[1]
            zones[cur] = []
        elif cur and line.strip() and line[0] not in "#V":
            zones[cur].append([float(v) for v in line.split()])
    return {k: np.array(v) for k, v in zones.items()}


def test_sutherland_reference_point_and_openfoam_form():
    assert bl.mu_sutherland(C.SUTHERLAND_T_REF) == pytest.approx(C.SUTHERLAND_MU_REF, rel=1e-12)
    T = 100.3
    direct = C.SUTHERLAND_MU_REF * (T / C.SUTHERLAND_T_REF) ** 1.5 * (C.SUTHERLAND_T_REF + C.SUTHERLAND_S) / (T + C.SUTHERLAND_S)
    assert bl.mu_sutherland(T) == pytest.approx(direct, rel=1e-12)


def test_eucken_prandtl_is_constant():
    for T in (55.0, 300.0, 1500.0):
        assert C.CP_AIR * bl.mu_sutherland(T) / bl.kappa_eucken(T) == pytest.approx(C.PRANDTL_LAMINAR, rel=1e-12)
    # gamma = 1.4: Cv = 2.5 R  ->  Pr = 3.5 / (2.5*1.32 + 1.77) = 0.69033...
    assert C.PRANDTL_LAMINAR == pytest.approx(3.5 / (2.5 * 1.32 + 1.77), rel=1e-12)


def test_recovery_temperature_tmr_ratios():
    # TMR 2DZPH: M 2 -> Taw/T = 1.712, M 5 -> 5.450
    assert bl.recovery_temperature(1.0, 2.0) == pytest.approx(1.712, abs=5e-4)
    assert bl.recovery_temperature(1.0, 5.0) == pytest.approx(5.450, abs=5e-4)


def test_van_driest_ii_reproduces_tmr_file():
    zones = tmr_zones(DATA / "cf_vandriestII.dat")
    conds = [(2.0, 1.712), (5.0, 1.090), (5.0, 2.725), (5.0, 5.450)]
    assert len(zones) == 4
    for (name, v), (M, tw) in zip(zones.items(), conds):
        assert f"M={M:.1f}" in name and f"{tw:.3f}" in name
        cf = bl.cf_van_driest_ii(v[:, 0], M, tw, T_e=300.0)
        assert np.max(np.abs(cf / v[:, 1] - 1)) < 1e-5


def test_van_driest_ii_incompressible_limit():
    re = np.array([2e3, 1e4])
    assert bl.cf_van_driest_ii(re, 1e-3, 1.0) == pytest.approx(bl.cf_karman_schoenherr(re), rel=1e-5)


def test_integral_thicknesses_power_law():
    # incompressible u/ue = (y/delta)^(1/7): delta*/delta = 1/8, theta/delta = 7/72
    d = 0.01
    y = d * (np.linspace(0, 1, 4001)[1:]) ** 2  # clustered to the wall
    u = 100.0 * (y / d) ** (1 / 7)
    ds, th = bl.integral_thicknesses(y, np.ones_like(y), u, 1.0, 100.0)
    assert ds == pytest.approx(d / 8, rel=2e-3)
    assert th == pytest.approx(d * 7 / 72, rel=2e-3)
    # y_max cut-off: beyond the edge the integrand is zero
    y2 = np.concatenate([y, [2 * d, 3 * d]])
    u2 = np.concatenate([u, [100.0, 100.0]])
    assert bl.integral_thicknesses(y2, np.ones_like(y2), u2, 1.0, 100.0)[1] == pytest.approx(th, rel=1e-12)
    assert bl.integral_thicknesses(y2, np.ones_like(y2), u2, 1.0, 100.0, y_max=d)[1] == pytest.approx(th, rel=1e-12)


def test_integral_thicknesses_variable_density():
    # linear u, rho = 2 rho_e inside: theta = int 2 s (1 - s) dy = delta/3, delta* = int (1 - 2 s) = 0
    y = np.linspace(0, 1, 2001)[1:]
    ds, th = bl.integral_thicknesses(y, np.full_like(y, 2.0), y, 1.0, 1.0)
    assert th == pytest.approx(1 / 3, rel=1e-5)
    assert ds == pytest.approx(0.0, abs=1e-6)


def test_delta99():
    y = np.linspace(0.1, 2.0, 20)
    assert bl.delta99(y, np.minimum(y, 1.0), 1.0) == pytest.approx(0.99, rel=1e-12)
    with pytest.raises(ValueError):
        bl.delta99(y, 0.5 * np.minimum(y, 1.0), 1.0)


def test_wall_shear_yplus_cf():
    T_w, d, u = 300.0, 1e-6, 0.5
    tau = bl.wall_shear(u, d, T_w)
    assert tau == pytest.approx(bl.mu_sutherland(T_w) * u / d)
    rho = 0.5
    nu = bl.mu_sutherland(T_w) / rho
    assert bl.y_plus(d, tau, rho, T_w) == pytest.approx(d * np.sqrt(tau / rho) / nu, rel=1e-12)
    assert bl.y_plus(d, -tau, rho, T_w) == pytest.approx(bl.y_plus(d, tau, rho, T_w))
    assert bl.skin_friction(tau, 0.1, 800.0) == pytest.approx(tau / (0.5 * 0.1 * 800.0**2))


def test_stanton_and_bq_signs():
    # cold wall (T_w < T_aw), heat into the wall: q > 0 -> St > 0, -B_q > 0
    q, rho_e, u_e, T_w, T_aw = 1e4, 0.043, 870.4, 300.0, 394.0
    assert bl.stanton(q, rho_e, u_e, T_w, T_aw) == pytest.approx(q / (rho_e * u_e * C.CP_AIR * 94.0))
    rho_w, tau = 0.01, 20.0
    assert bl.minus_b_q(q, rho_w, tau, T_w) == pytest.approx(q / (rho_w * C.CP_AIR * np.sqrt(tau / rho_w) * T_w))
    assert bl.minus_b_q(-q, rho_w, tau, T_w) < 0


def test_sign_changes():
    x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    f = np.array([1.0, -1.0, -2.0, 2.0, 3.0])
    assert bl.sign_changes(x, f) == [(0.5, "sep"), (2.5, "reatt")]
    assert bl.sign_changes(x, np.abs(f)) == []
    # exact zero at a node is reported once
    assert bl.sign_changes(x, np.array([1.0, 0.0, -1.0, -1.0, -1.0])) == [(1.0, "sep")]


# --- separation extent on the ramp wall (I4): tests written before the implementation (rule 10) ---
def _tau(x, bubbles):
    """+1 everywhere except -1 inside the given (start, end) intervals."""
    t = np.ones_like(x)
    for a, b in bubbles:
        t[(x > a) & (x < b)] = -1.0
    return t


def test_separation_extent_attached():
    x = np.linspace(-1.0, 0.2, 1201)
    r = bl.separation_extent(x, np.ones_like(x), x_min=-0.9)
    assert r == dict(sep=None, reatt=None, L_sep=0.0, open=False)


def test_separation_extent_closed_bubble():
    x = np.linspace(-1.0, 0.2, 1201)                      # spacing 1e-3
    r = bl.separation_extent(x, _tau(x, [(-0.0205, 0.0305)]), x_min=-0.9)
    assert r["open"] is False
    assert abs(r["sep"] + 0.0205) < 1e-3 and abs(r["reatt"] - 0.0305) < 1e-3
    assert abs(r["L_sep"] - 0.051) < 2e-3


def test_separation_extent_merges_attached_island():
    # small attached spot at the corner inside one bubble (seen in the SST ramp solution)
    x = np.linspace(-1.0, 0.2, 1201)
    r = bl.separation_extent(x, _tau(x, [(-0.0205, 0.0005), (0.0025, 0.0305)]), x_min=-0.9)
    assert abs(r["sep"] + 0.0205) < 1e-3 and abs(r["reatt"] - 0.0305) < 1e-3 and r["open"] is False


def test_separation_extent_open_at_outlet():
    # reversed flow reaches the end of the wall: no reattachment inside the domain
    x = np.linspace(-1.0, 0.2, 1201)
    r = bl.separation_extent(x, _tau(x, [(-0.8305, 0.0005), (0.0025, 1.0)]), x_min=-0.9)
    assert r["open"] is True and r["reatt"] is None and np.isnan(r["L_sep"])
    assert abs(r["sep"] + 0.8305) < 1e-3                 # found although it is far from the corner


def test_separation_extent_ignores_leading_edge_region():
    x = np.linspace(-1.0, 0.2, 1201)
    r = bl.separation_extent(x, _tau(x, [(-0.995, -0.985), (-0.0205, 0.0305)]), x_min=-0.9)
    assert abs(r["sep"] + 0.0205) < 1e-3 and abs(r["reatt"] - 0.0305) < 1e-3


def test_peak_heat_flux_signed_largest_magnitude():
    assert bl.peak_heat_flux([1.0, 3.0, 2.0]) == (3.0, 1)                      # all positive: max
    assert bl.peak_heat_flux([-1.0, -3.0, -2.0]) == (-3.0, 1)                  # all negative: most negative
    assert bl.peak_heat_flux([2.0, -5.0, 4.0]) == (-5.0, 1)                    # mixed signs
    assert bl.peak_heat_flux([2.0, -1.0, 4.0]) == (4.0, 2)
    v, i = bl.peak_heat_flux(np.array([-2.0, 2.0, 1.0]))                       # tie in magnitude: first index
    assert (v, i) == (-2.0, 0)
    assert isinstance(v, float) and isinstance(i, int)


@pytest.mark.parametrize("bad", [[], [1.0, float("nan")], [float("inf"), 1.0], [-float("inf")]])
def test_peak_heat_flux_rejects_empty_and_nonfinite(bad):
    with pytest.raises(ValueError):
        bl.peak_heat_flux(np.array(bad))
