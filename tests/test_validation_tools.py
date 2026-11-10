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
