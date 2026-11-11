"""Tests for src.gasdynamics (analytic compressible-flow relations, I3).

Reference values are taken from published tables, not from the code under test:
- NACA Report 1135 (Ames Research Staff, 1953), normal/oblique-shock and
  Prandtl-Meyer tables, gamma = 1.4.
- Toro, E. F. (2009), Riemann Solvers and Numerical Methods for Fluid Dynamics,
  3rd ed., Table 4.2 (tests) and Table 4.3 (exact star-region values).
- docs/exercises.md problem 2-3 (I1, values cross-checked with NACA 1135).
"""
import numpy as np
import pytest

from src import constants as c
from src import gasdynamics as gd

G = 1.4


# --- constants -------------------------------------------------------------

def test_constants_consistent():
    assert c.GAMMA_AIR == 1.4
    assert c.R_AIR == pytest.approx(c.RR_OPENFOAM / c.MOLWEIGHT_AIR, rel=1e-15)
    assert c.R_AIR == pytest.approx(287.05, abs=0.01)
    assert c.CP_AIR / (c.CP_AIR - c.R_AIR) == pytest.approx(1.4, rel=1e-12)


# --- normal shock (NACA 1135 Table II) ---------------------------------------

@pytest.mark.parametrize(
    "M1, M2, p21, r21, p0ratio",
    [
        (2.0, 0.57735, 4.5000, 2.6667, 0.72087),
        (3.0, 0.47519, 10.333, 3.8571, 0.32834),
        (5.0, 0.41523, 29.000, 5.0000, 0.06172),
    ],
)
def test_normal_shock(M1, M2, p21, r21, p0ratio):
    ns = gd.normal_shock(M1, G)
    assert ns["M2"] == pytest.approx(M2, rel=1e-4)
    assert ns["p2_p1"] == pytest.approx(p21, rel=1e-4)
    assert ns["rho2_rho1"] == pytest.approx(r21, rel=1e-4)
    assert ns["p02_p01"] == pytest.approx(p0ratio, rel=1e-3)


def test_rayleigh_pitot_M3():
    # NACA 1135 Table II, M1 = 3: p02/p1 = 12.061
    assert gd.rayleigh_pitot(3.0, G) == pytest.approx(12.061, rel=1e-4)


def test_rayleigh_pitot_subsonic_is_isentropic():
    M = 0.5
    assert gd.rayleigh_pitot(M, G) == pytest.approx((1 + 0.2 * M**2) ** 3.5, rel=1e-12)


# --- oblique shock -----------------------------------------------------------

@pytest.mark.parametrize(
    "M1, theta, beta, p21, M2",
    [
        # docs/exercises.md problem 3 (checked vs NACA 1135 chart)
        (2.5, 15.0, 36.94, 2.468, 1.874),
        # Anderson, Modern Compressible Flow, Example 4.1-type textbook case
        (2.0, 10.0, 39.31, 1.7066, 1.6405),
    ],
)
def test_oblique_shock_weak(M1, theta, beta, p21, M2):
    os_ = gd.oblique_shock(M1, np.radians(theta), G)
    assert np.degrees(os_["beta"]) == pytest.approx(beta, abs=0.01)
    assert os_["p2_p1"] == pytest.approx(p21, rel=1e-3)
    assert os_["M2"] == pytest.approx(M2, rel=1e-3)


def test_oblique_shock_satisfies_theta_beta_M():
    M1, th = 5.0, np.radians(10.0)
    b = gd.oblique_shock(M1, th, G)["beta"]
    rhs = 2 / np.tan(b) * (M1**2 * np.sin(b) ** 2 - 1) / (M1**2 * (G + np.cos(2 * b)) + 2)
    assert np.tan(th) == pytest.approx(rhs, rel=1e-10)


def test_theta_max_M25():
    # docs/exercises.md problem 3: theta_max = 29.80 deg at beta = 64.78 deg
    th, b = gd.theta_max(2.5, G)
    assert np.degrees(th) == pytest.approx(29.80, abs=0.01)
    assert np.degrees(b) == pytest.approx(64.78, abs=0.05)


def test_oblique_detached_raises():
    with pytest.raises(ValueError):
        gd.oblique_shock(2.5, np.radians(31.0), G)


# --- Prandtl-Meyer -----------------------------------------------------------

@pytest.mark.parametrize("M, nu", [(2.0, 26.380), (3.0, 49.757), (5.0, 76.920)])
def test_prandtl_meyer(M, nu):
    # NACA 1135 Table II
    assert np.degrees(gd.prandtl_meyer(M, G)) == pytest.approx(nu, abs=1e-3)


def test_prandtl_meyer_inverse_roundtrip():
    for M in (1.2, 2.0, 2.5, 4.0, 7.0):
        assert gd.prandtl_meyer_inverse(gd.prandtl_meyer(M, G), G) == pytest.approx(M, rel=1e-10)


def test_expansion_corner_isentropic():
    M1, th = 2.5, np.radians(15.0)
    ex = gd.expansion_corner(M1, th, G)
    assert gd.prandtl_meyer(ex["M2"], G) - gd.prandtl_meyer(M1, G) == pytest.approx(th, rel=1e-10)
    iso = lambda M: (1 + 0.5 * (G - 1) * M**2) ** (-G / (G - 1))
    assert ex["p2_p1"] == pytest.approx(iso(ex["M2"]) / iso(M1), rel=1e-12)


def test_fan_mach_at_ray_endpoints_and_monotone():
    M1, th = 2.5, np.radians(15.0)
    M2 = gd.expansion_corner(M1, th, G)["M2"]
    mu = lambda M: np.arcsin(1 / M)
    # leading ray at +mu1 above the upstream flow direction, trailing ray at mu2 - theta
    assert gd.fan_mach_at_ray(mu(M1), M1, th, G) == pytest.approx(M1, rel=1e-8)
    assert gd.fan_mach_at_ray(mu(M2) - th, M1, th, G) == pytest.approx(M2, rel=1e-8)
    psi = np.linspace(mu(M2) - th, mu(M1), 20)
    Ms = [gd.fan_mach_at_ray(p, M1, th, G) for p in psi]
    assert np.all(np.diff(Ms) < 0)  # Mach drops as the ray tilts up toward the leading line
    # outside the fan: uniform states
    assert gd.fan_mach_at_ray(mu(M1) + 0.1, M1, th, G) == pytest.approx(M1)
    assert gd.fan_mach_at_ray(mu(M2) - th - 0.1, M1, th, G) == pytest.approx(M2)


# --- exact Riemann solver (Toro 2009, Tables 4.2-4.3) -------------------------

@pytest.mark.parametrize(
    "left, right, pstar, ustar, rhoL, rhoR",
    [
        # Test 1 (Sod)
        ((1.0, 0.0, 1.0), (0.125, 0.0, 0.1), 0.30313, 0.92745, 0.42632, 0.26557),
        # Test 2 (123 problem, two rarefactions)
        ((1.0, -2.0, 0.4), (1.0, 2.0, 0.4), 0.00189, 0.00000, 0.02185, 0.02185),
        # Test 3 (strong left rarefaction / right shock)
        ((1.0, 0.0, 1000.0), (1.0, 0.0, 0.01), 460.894, 19.5975, 0.57506, 5.99924),
    ],
)
def test_riemann_star_state(left, right, pstar, ustar, rhoL, rhoR):
    st = gd.riemann_star(left, right, G)
    assert st["p"] == pytest.approx(pstar, rel=2e-4, abs=1e-5)
    assert st["u"] == pytest.approx(ustar, rel=2e-4, abs=1e-5)
    assert st["rhoL"] == pytest.approx(rhoL, rel=2e-4, abs=1e-5)
    assert st["rhoR"] == pytest.approx(rhoR, rel=2e-4, abs=1e-5)


def test_riemann_profile_conserves_mass_and_energy():
    # Sod on [-0.5, 0.5] at t = 0.2: waves stay inside, so integrals are conserved.
    left, right = (1.0, 0.0, 1.0), (0.125, 0.0, 0.1)
    x = np.linspace(-0.5, 0.5, 200001)
    rho, u, p = gd.riemann_profile(x, 0.2, left, right, G, x0=0.0)
    E = p / (G - 1) + 0.5 * rho * u**2
    dx = x[1] - x[0]
    assert np.trapezoid(rho, dx=dx) == pytest.approx(0.5 * (1.0 + 0.125), rel=1e-4)
    assert np.trapezoid(E, dx=dx) == pytest.approx(0.5 * (1.0 + 0.1) / (G - 1), rel=1e-4)
    # momentum: initial 0; d/dt = p_L - p_R = 0.9 -> 0.18 at t = 0.2
    assert np.trapezoid(rho * u, dx=dx) == pytest.approx(0.9 * 0.2, rel=1e-4)


def test_riemann_profile_far_field_and_dimensional_scaling():
    left, right = (1.0, 0.0, 1.0), (0.125, 0.0, 0.1)
    rho, u, p = gd.riemann_profile(np.array([-10.0, 10.0]), 0.2, left, right, G)
    np.testing.assert_allclose([rho[0], u[0], p[0]], left)
    np.testing.assert_allclose([rho[1], u[1], p[1]], right)
    # scaling invariance: rho*a, p*a^2*... -> same self-similar profile in x/t
    s = 316.0
    x = np.linspace(-0.4, 0.4, 41)
    r1, u1, p1 = gd.riemann_profile(x, 0.2, left, right, G)
    L2, R2 = (1.0, 0.0, s**2), (0.125, 0.0, 0.1 * s**2)
    r2, u2, p2 = gd.riemann_profile(x, 0.2 / s, L2, R2, G)
    np.testing.assert_allclose(r2, r1, rtol=1e-8)
    np.testing.assert_allclose(u2, u1 * s, rtol=1e-8, atol=1e-10)
    np.testing.assert_allclose(p2, p1 * s**2, rtol=1e-8)


# --- area ratio, starting limits (I5) ----------------------------------------
# Reference: docs/exercises.md problem 4 (I1; A/A* = 1.6875 at M 2 is the isentropic-table value).

def test_area_ratio_table_values():
    assert gd.area_ratio(1.0, G) == pytest.approx(1.0, abs=1e-14)
    assert gd.area_ratio(2.0, G) == pytest.approx(1.6875, rel=1e-12)
    assert gd.area_ratio(3.0, G) == pytest.approx(4.2346, rel=2e-5)      # NACA 1135 Table II


@pytest.mark.parametrize("M, isen, kant", [(2.0, 0.5926, 0.8220), (4.0, 0.0933, 0.6724), (6.0, 0.0188, 0.6342)])
def test_starting_limits_exercise_4(M, isen, kant):
    assert gd.isentropic_limit(M, G) == pytest.approx(isen, abs=6e-5)
    assert gd.kantrowitz_limit(M, G) == pytest.approx(kant, abs=6e-5)


def test_kantrowitz_second_form_and_asymptote():
    # same value from (A*/A)(M) / (p02/p01)  (docs/exercises.md problem 4b)
    for M in (1.5, 2.5, 3.432, 7.0):
        alt = 1 / gd.area_ratio(M, G) / gd.normal_shock(M, G)["p02_p01"]
        assert gd.kantrowitz_limit(M, G) == pytest.approx(alt, rel=1e-12)
    assert gd.kantrowitz_limit(1.0, G) == pytest.approx(1.0, abs=1e-12)
    assert gd.kantrowitz_limit(1e4, G) == pytest.approx(0.600, abs=1e-3)


def test_mach_min_attached_is_inverse_of_theta_max():
    for M in (1.3, 2.0, 3.5):
        th = gd.theta_max(M, G)[0]
        assert gd.mach_min_attached(th, G) == pytest.approx(M, rel=1e-7)
    # docs/i5/detach_mach_two_ramp.csv (Science, independent implementation): 8 deg -> 1.348, 12 deg -> 1.496
    assert gd.mach_min_attached(np.radians(8.0), G) == pytest.approx(1.348, abs=6e-4)
    assert gd.mach_min_attached(np.radians(12.0), G) == pytest.approx(1.496, abs=6e-4)
