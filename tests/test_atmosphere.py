"""Tests for src.atmosphere (U.S. Standard Atmosphere 1976, 0-32 km geopotential).

Reference values are from the published standard, not from the code under test:
- layer base values T, p at 0, 11, 20, 32 km geopotential (U.S. Standard Atmosphere 1976, Table 4 /
  defining constants in Table 3);
- docs/exercises.md problem 1 (I1, cross-checked there with the standard table): geometric 25 km ->
  geopotential 24902.1 m, T = 221.55 K, p = 2549.2 Pa, M 6 dynamic pressure 64.2 kPa.
"""
import pytest

from src import atmosphere as atm


@pytest.mark.parametrize("h, T, p", [
    (0.0, 288.15, 101325.0),
    (11000.0, 216.65, 22632.06),
    (20000.0, 216.65, 5474.889),
    (32000.0, 228.65, 868.0187),
])
def test_layer_base_values(h, T, p):
    Tm, pm = atm.state(h)
    assert Tm == pytest.approx(T, abs=1e-9)
    assert pm == pytest.approx(p, rel=2e-5)


def test_exercise_1_25km():
    h = atm.geopotential_altitude(25000.0)
    assert h == pytest.approx(24902.1, abs=0.1)
    T, p = atm.state(h)
    assert T == pytest.approx(221.55, abs=0.01)
    assert p == pytest.approx(2549.2, abs=0.2)
    assert 0.5 * 1.4 * p * 6.0**2 == pytest.approx(64.2e3, rel=2e-3)


def test_troposphere_midpoint():
    # 5 km geopotential: T = 288.15 - 6.5*5 = 255.65 K; p from the standard table 5.4020e4 Pa
    T, p = atm.state(5000.0)
    assert T == pytest.approx(255.65, abs=1e-9)
    assert p == pytest.approx(5.4020e4, rel=1e-4)


def test_altitude_from_pressure_roundtrip():
    for h in (0.0, 3000.0, 11000.0, 15000.0, 20000.0, 27000.0, 32000.0):
        _, p = atm.state(h)
        assert atm.altitude_from_pressure(p) == pytest.approx(h, abs=1e-6 * max(h, 1.0) + 1e-6)


def test_out_of_range_raises():
    with pytest.raises(ValueError):
        atm.state(-1.0)
    with pytest.raises(ValueError):
        atm.state(32000.1)
    with pytest.raises(ValueError):
        atm.altitude_from_pressure(800.0)      # above 32 km


def test_constant_q_point_is_consistent():
    fs = atm.constant_q_point(5.0, 50e3)
    assert not fs["sea_level_clamped"]
    assert 0.5 * 1.4 * fs["p"] * 25.0 == pytest.approx(50e3, rel=1e-12)
    T, p = atm.state(fs["h"])
    assert (T, p) == (pytest.approx(fs["T"]), pytest.approx(fs["p"]))
    assert 24000.0 < fs["h"] < 24500.0          # p = 2857 Pa lies between 24 and 24.5 km


def test_constant_q_point_clamps_at_sea_level():
    # q = 50 kPa at M 0.6 would need p = 198 kPa > sea-level pressure: clamp and report the actual q
    fs = atm.constant_q_point(0.6, 50e3)
    assert fs["sea_level_clamped"]
    assert fs["h"] == 0.0 and fs["p"] == pytest.approx(101325.0)
    assert fs["q"] == pytest.approx(0.5 * 1.4 * 101325.0 * 0.36)
    assert fs["q"] < 50e3
