"""Tests for src.validation_tools (post-processing helpers for I3).

All checks use synthetic data with a known answer.
"""
import numpy as np
import pytest

from src import validation_tools as vt


def test_crossing_linear_interpolation():
    s = np.array([0.0, 1.0, 2.0, 3.0])
    q = np.array([1.0, 1.0, 3.0, 3.0])
    assert vt.crossing(s, q, 2.0) == pytest.approx(1.5)
    # decreasing profile, first crossing from the start
    assert vt.crossing(s, q[::-1], 2.0) == pytest.approx(1.5)


def test_crossing_none_when_absent():
    assert vt.crossing(np.arange(3.0), np.ones(3), 2.0) is None


def test_shock_angle_from_smeared_field():
    # pressure field with a tanh shock along y = x tan(beta) through (0, 0)
    beta = np.radians(36.94)
    xs = np.linspace(0.2, 1.0, 9)
    ys = np.linspace(0.0, 1.0, 401)
    locs = []
    for x0 in xs:
        d = (ys - x0 * np.tan(beta)) * np.cos(beta)  # signed normal distance
        p = 1.0 + 0.5 * 1.468 * (1 - np.tanh(d / 0.01))  # p2 below the shock, p1 above
        locs.append(vt.crossing(ys, p, 1.0 + 0.5 * 1.468))
    ang, x_int, resid = vt.fit_line_angle(xs, np.array(locs))
    # linear interpolation of a sampled tanh (4 points across the shock) costs
    # ~3e-4 deg; the I3 tolerance (1 % of beta) is ~0.37 deg.
    assert np.degrees(ang) == pytest.approx(36.94, abs=2e-3)
    assert x_int == pytest.approx(0.0, abs=1e-3)
    assert resid < 1e-3


def test_l1_error_and_order():
    # error ~ C h^p must give back p
    h = np.array([0.04, 0.02, 0.01, 0.005])
    err = 3.0 * h**0.8
    p = vt.observed_order(h, err)
    np.testing.assert_allclose(p, 0.8, rtol=1e-12)
    x = np.linspace(0, 1, 11)
    assert vt.l1_error(np.ones(11), np.zeros(11), x[1] - x[0]) == pytest.approx(1.1)


def test_relative_change_window():
    # metric history: settles to 2.0 with a decaying wiggle
    it = np.arange(0, 10001, 100)
    m = 2.0 * (1 + 0.1 * np.exp(-it / 500.0))
    # last 2000 iterations: max |m - m_last| / |m_last|
    rc = vt.relative_change(it, m, window=2000)
    expected = (m[it >= it[-1] - 2000] - m[-1]).__abs__().max() / m[-1]
    assert rc == pytest.approx(expected)
    assert rc < 2e-3
    with pytest.raises(ValueError):
        vt.relative_change(it[:5], m[:5], window=2000)  # history shorter than window


def test_mass_imbalance():
    assert vt.mass_imbalance({"inlet": -10.0, "outlet": 9.97, "top": 0.0}) == pytest.approx(0.003)


# --------------------------------------------------------------------------- grid convergence (Celik et al. 2008)

def _phi(h, phi0, C, p):
    return phi0 + C * np.asarray(h, float) ** p


def _cells_from_h(h, dim=2):
    return (1.0 / np.asarray(h, float)) ** dim


@pytest.mark.parametrize("p_true,h", [
    (2.0, [4.0, 2.0, 1.0]),                      # constant r = 2
    (2.0, [3.7, 2.1, 1.0]),                      # r21 = 2.1, r32 = 1.76 (non-constant)
    (1.5, [1.0 * 1.9 * 1.4, 1.0 * 1.4, 1.0]),    # r21 = 1.4, r32 = 1.9
    (1.5, [0.04, 0.02, 0.01]),
    (0.8, [2.9, 1.7, 1.0]),
])
def test_grid_convergence_recovers_order_and_extrapolation(p_true, h):
    phi0, C = 3.25, 0.7
    phi = _phi(h, phi0, C, p_true)                 # ordered coarse -> fine
    r = vt.grid_convergence(phi, _cells_from_h(h), dim=2)
    assert r["status"] == "monotone"
    assert r["p"] == pytest.approx(p_true, rel=1e-9)
    assert r["phi_ext"] == pytest.approx(phi0, rel=1e-10)
    assert r["r21"] == pytest.approx(h[1] / h[2])
    assert r["r32"] == pytest.approx(h[0] / h[1])
    # e_a21 = |(phi1-phi2)/phi1|, GCI21 = 1.25 e_a21 / (r21^p - 1)
    ea = abs((phi[2] - phi[1]) / phi[2])
    assert r["e_a21"] == pytest.approx(ea)
    assert r["e_ext21"] == pytest.approx(abs((phi0 - phi[2]) / phi0), rel=1e-8)
    assert r["gci21"] == pytest.approx(1.25 * ea / (r["r21"] ** p_true - 1), rel=1e-8)
    # asymptotic-range indicator GCI32 / (r21^p GCI21): for an exact power law the eps's cancel and only the
    # different normalisations of e_a32 (by phi2) and e_a21 (by phi1) remain -> phi1/phi2
    assert r["asymptotic_ratio"] == pytest.approx(phi[2] / phi[1], rel=1e-8)


def test_grid_convergence_constant_ratio_closed_form():
    # constant r: p = ln(eps32/eps21) / ln r  (Celik 2008 eq. 4 with q = 0)
    phi = np.array([10.0, 6.0, 4.0])               # eps32 = 4 (phi3 - phi2 -> coarse-medium), eps21 = 2
    # cells coarse -> fine: N = 100, 400, 1600 -> h ratio 2 in 2D
    r = vt.grid_convergence(phi, [100, 400, 1600], dim=2)
    assert r["r21"] == pytest.approx(2.0) and r["r32"] == pytest.approx(2.0)
    assert r["eps32"] == pytest.approx(4.0) and r["eps21"] == pytest.approx(2.0)
    assert r["p"] == pytest.approx(np.log(2.0) / np.log(2.0))
    assert r["p"] == pytest.approx(1.0)
    assert r["phi_ext"] == pytest.approx((2.0 * 4.0 - 6.0) / (2.0 - 1.0))     # = 2.0
    assert r["gci21"] == pytest.approx(1.25 * abs((4.0 - 6.0) / 4.0) / (2.0 - 1.0))


def test_grid_convergence_dim_changes_h_not_the_order_definition():
    # same N ratio, 3D: h ~ N^(-1/3); p recovered for h-power-law data
    h = np.array([2.0, 1.4, 1.0])
    phi = _phi(h, 1.0, 1.0, 2.0)
    r = vt.grid_convergence(phi, _cells_from_h(h, dim=3), dim=3)
    assert r["p"] == pytest.approx(2.0, rel=1e-9)


def test_grid_convergence_oscillatory_flagged_no_division():
    r = vt.grid_convergence([1.0, 1.3, 1.2], [100, 400, 1600])      # eps32 = phi3-phi2 = -0.3, eps21 = phi2-phi1 = +0.1 -> s < 0
    assert r["status"] == "oscillatory"
    assert np.isnan(r["p"]) and np.isnan(r["phi_ext"]) and np.isnan(r["gci21"])
    assert r["band"] == pytest.approx((1.0, 1.3))                    # min, max of the three values
    assert r["e_a21"] == pytest.approx(abs((1.2 - 1.3) / 1.2))       # still reported


def test_grid_convergence_zero_change_flagged():
    for phi in ([2.0, 2.0, 2.0], [2.0, 2.0, 2.5], [2.0, 2.5, 2.5]):
        r = vt.grid_convergence(phi, [100, 400, 1600])
        assert r["status"] == "zero_change", phi
        assert np.isnan(r["p"]) and np.isnan(r["phi_ext"]) and np.isnan(r["gci21"])
    assert vt.grid_convergence([2.0, 2.0, 2.0], [100, 400, 1600])["e_a21"] == 0.0


def test_grid_convergence_diverging_flagged():
    # monotone but the fine-level change is larger than the coarse-level change: p < 0
    r = vt.grid_convergence([1.0, 1.1, 1.5], [100, 400, 1600])
    assert r["status"] == "diverging"
    assert np.isnan(r["gci21"])


def test_grid_convergence_validates_input():
    with pytest.raises(ValueError):
        vt.grid_convergence([1.0, 2.0], [100, 400])
    with pytest.raises(ValueError):
        vt.grid_convergence([1.0, 2.0, 3.0], [400, 100, 1600])      # cells must increase coarse -> fine
    with pytest.raises(ValueError):
        vt.grid_convergence([1.0, 2.0, float("nan")], [100, 400, 1600])
